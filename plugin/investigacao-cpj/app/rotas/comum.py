#!/usr/bin/env python3
"""Utilitários compartilhados, autenticação, controle de fila e painel da Central CPJ."""
import datetime
import functools
import hashlib
import ipaddress
import json
import os
import queue
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from flask import abort, jsonify, request, session

AQUI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGIN = os.path.dirname(AQUI)
S_PDF = os.path.join(PLUGIN, "skills", "pdf-autos-policiais", "scripts")
S_BASE = os.path.join(PLUGIN, "skills", "base-cpj", "scripts")
sys.path.insert(0, S_BASE)
sys.path.insert(0, AQUI)

import caso as C  # noqa: E402
import consulta as Q  # noqa: E402
import dados_os as D_OS  # noqa: E402
import rag as R  # noqa: E402
import referencias as RF  # noqa: E402
from auth import Auth, DESCRICAO, PERFIS, TODAS  # noqa: E402
from tarefas import SEM_JANELA, Tarefas, gerar_docx, gerar_pdf, soffice  # noqa: E402

WS = C.WS
PY = sys.executable
def _achar_tesseract():
    """Pasta do tesseract.exe: CPJ_TESSERACT, instalação padrão, a que vem com o PDF24 ou o PATH."""
    candidatos = [os.environ.get("CPJ_TESSERACT", ""), r"C:\Program Files\Tesseract-OCR", r"C:\Program Files\PDF24\tesseract"]
    for d in candidatos:
        if d and os.path.isfile(os.path.join(d, "tesseract.exe")):
            return d
    exe = shutil.which("tesseract")
    return os.path.dirname(exe) if exe else candidatos[1]


TESS_DIR = _achar_tesseract()
TESSDATA_LOCAL = next(
    (d for d in (os.path.join(WS, "ferramentas", "tessdata"), os.path.join(os.path.dirname(os.path.dirname(PLUGIN)), "ferramentas", "tessdata"))
     if os.path.exists(os.path.join(d, "por.traineddata"))),
    os.path.join(WS, "ferramentas", "tessdata"),
)
EXT_OK = {".pdf", ".md", ".csv"}

_auth_inst = Auth(WS)


class _AuthProxy:
    def __getattr__(self, name):
        return getattr(_auth_inst, name)

    def __setattr__(self, name, value):
        if name == "_inst":
            globals()["_auth_inst"] = value
        else:
            setattr(_auth_inst, name, value)

    def __repr__(self):
        return repr(_auth_inst)

    def __bool__(self):
        return bool(_auth_inst)


auth = _AuthProxy()
tarefas = Tarefas(WS, C, auth)
fila = queue.Queue()
trava = threading.Lock()
REDE_ARQ = os.path.join(WS, "config", "rede.json")

_ocr_trava = threading.Lock()
_ocr_cache = {"chave": None, "idioma": None, "expira": 0}
_painel_trava = threading.Lock()
_painel_cache = {"chave": None, "gerando": False, "erro": False, "retentar_apos": 0}


# ================================================================== utilidades básicas
def agora():
    return datetime.datetime.now().isoformat(timespec="seconds")


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def nome_seguro(n):
    base, ext = os.path.splitext(os.path.basename(n or "arquivo"))
    base = re.sub(r"[^\w\-. ]+", "_", base, flags=re.U).strip(" ._") or "arquivo"
    return base[:80], ext.lower()


def rede_cfg():
    d = {"compartilhar": False, "porta": 8765, "https": True}
    if os.path.exists(REDE_ARQ):
        d.update(json.load(open(REDE_ARQ, encoding="utf-8")))
    return d


def ips_locais():
    ips = set()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.add(info[4][0])
    except OSError:
        pass
    return sorted(i for i in ips if not i.startswith("127."))


def eh_local():
    remoto = request.remote_addr or ""
    if remoto in ("127.0.0.1", "::1"):
        return True
    if os.environ.get("CPJ_DOCKER") == "1":
        try:
            return ipaddress.ip_address(remoto).is_private
        except ValueError:
            return False
    return False


def pasta_usuario(login):
    d = os.path.join(WS, "usuarios", login)
    for s in ("", "relatorios", "documentos"):
        os.makedirs(os.path.join(d, s), exist_ok=True)
    return d


def ambiente_ocr():
    env = dict(os.environ, CPJ_WORKSPACE=WS, PYTHONIOENCODING="utf-8", PYTHONWARNINGS="ignore")
    if os.path.isdir(TESS_DIR) and TESS_DIR not in env.get("PATH", ""):
        env["PATH"] = env.get("PATH", "") + ";" + TESS_DIR
    if os.path.exists(os.path.join(TESSDATA_LOCAL, "por.traineddata")):
        env["TESSDATA_PREFIX"] = TESSDATA_LOCAL
    return env


def assinatura_arquivo(p):
    try:
        st = os.stat(p)
        return st.st_mtime_ns, st.st_size
    except FileNotFoundError:
        return None


def idioma_ocr(env):
    exe = os.path.join(TESS_DIR, "tesseract.exe")
    tessdata = env.get("TESSDATA_PREFIX") or os.path.join(TESS_DIR, "tessdata")
    chave = (
        exe,
        assinatura_arquivo(exe),
        env.get("PATH"),
        tessdata,
        assinatura_arquivo(os.path.join(tessdata, "por.traineddata")),
        assinatura_arquivo(os.path.join(tessdata, "eng.traineddata")),
    )
    with _ocr_trava:
        if _ocr_cache["chave"] == chave and time.monotonic() < _ocr_cache["expira"]:
            return _ocr_cache["idioma"]
        idioma = None
        try:
            r = subprocess.run(
                [exe, "--list-langs"],
                env=env,
                capture_output=True,
                text=True,
                timeout=20,
                creationflags=SEM_JANELA,
            )
            langs = r.stdout.split() if r.returncode == 0 else []
            idioma = "por" if "por" in langs else ("eng" if "eng" in langs else None)
        except (OSError, subprocess.SubprocessError):
            pass
        _ocr_cache.update(
            chave=chave, idioma=idioma, expira=time.monotonic() + (300 if idioma else 30)
        )
        return idioma


# ================================================================== autenticação e permissões
def modo_solo():
    """Operação solo (config\\solo.json {"ativo": true}): no próprio computador entra direto, sem senha."""
    try:
        with open(os.path.join(WS, "config", "solo.json"), encoding="utf-8") as f:
            return bool(json.load(f).get("ativo"))
    except (OSError, ValueError, AttributeError):
        return False


def usuario():
    u = session.get("u")
    atual = auth.obter_sessao(u, session.get("v")) if u else None
    if u and atual is None:
        session.clear()
    # Modo solo: só loopback e só pelo endereço local (evita DNS rebinding); acesso pela rede continua com senha.
    if (atual is None and request.remote_addr in ("127.0.0.1", "::1")
            and request.host.rsplit(":", 1)[0] in ("127.0.0.1", "localhost", "[::1]") and modo_solo()):
        atual = auth.usuario_solo()
    return atual


def vincular_sessao(u):
    session.clear()
    session.permanent = True
    session["u"] = u["login"]
    session["v"] = u["_sessao_id"]


def requer(*perms):
    def deco(fn):
        @functools.wraps(fn)
        def w(*a, **k):
            u = usuario()
            if not u:
                return jsonify({"erro": "Sessão expirada. Entre novamente.", "login": True}), 401
            if u.get("trocar_senha") and request.endpoint not in ("usuarios.api_minha_senha", "api_minha_senha"):
                return jsonify({"erro": "Troque a senha temporária para continuar.", "trocar_senha": True}), 428
            if perms and not any(auth.pode(u["perfil"], p) for p in perms):
                return jsonify({"erro": "Sem permissão."}), 403
            request.usuario = u
            return fn(*a, **k)
        return w
    return deco


def auditar(acao, alvo=""):
    u = getattr(request, "usuario", None) or usuario() or {}
    auth.auditar(u.get("login", "-"), request.remote_addr, acao, alvo)


# ================================================================== processamento de documentos
def proc_path(id_):
    return os.path.join(C.caminho(id_), "processamento.json")


def ler_proc(id_):
    with trava:
        p = proc_path(id_)
        if not os.path.exists(p):
            return {"trabalhos": []}
        with open(p, encoding="utf-8") as f:
            return json.load(f)


def gravar_proc(id_, dados):
    with trava:
        p = proc_path(id_)
        tmp = p + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=1)
        for tentativa in range(3):
            try:
                os.replace(tmp, p)
                break
            except OSError as erro:
                if not isinstance(erro, PermissionError) and getattr(erro, "winerror", None) != 5:
                    raise
                if tentativa == 2:
                    raise
                time.sleep(0.02 * (tentativa + 1))


def atualizar_trabalho(id_, doc, **campos):
    d = ler_proc(id_)
    for t in d["trabalhos"]:
        if t["doc"] == doc:
            t.update(campos)
    gravar_proc(id_, d)


def registrar_tratamento(id_, linhas):
    with open(os.path.join(C.caminho(id_), "registro-tratamento.md"), "a", encoding="utf-8") as f:
        f.write("\n" + "\n".join(linhas) + "\n")


def rodar(cmd, env, log, progresso=None):
    with open(log, "a", encoding="utf-8") as lg:
        lg.write(f"\n[{agora()}] $ {' '.join(cmd)}\n")
        lg.flush()
        p = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=SEM_JANELA,
        )
        saida = []
        for ln in p.stdout:
            m = re.match(r"progresso (\d+)/(\d+)", ln)
            if m and progresso:
                progresso(int(m.group(1)), int(m.group(2)))
                continue
            saida.append(ln)
            lg.write(ln)
        p.wait()
        if p.returncode != 0:
            raise RuntimeError(f"falhou ({p.returncode}): {os.path.basename(cmd[1])} — ver log")
        return "".join(saida)


def processar(trab, app_logger=None):
    id_, doc, arq = trab["caso"], trab["doc"], trab["arquivo"]
    base = C.caminho(id_)
    orig = os.path.join(base, "00-originais", arq)
    dest = os.path.join(base, "01-extracao", doc)
    os.makedirs(dest, exist_ok=True)
    log = os.path.join(dest, "processamento.log")
    env = ambiente_ocr()
    ext = os.path.splitext(arq)[1].lower()
    etapa = lambda nome, **x: atualizar_trabalho(id_, doc, etapa=nome, **x)
    atualizar_trabalho(id_, doc, status="processando", inicio=agora(), erro=None, progresso=0)
    try:
        etapa("dados da O.S. (texto original)", progresso=1)
        try:
            D_OS.aplicar(C, id_, D_OS.ler_original(orig), arq)
        except Exception:
            if app_logger:
                app_logger.exception("Falha no preenchimento inicial da O.S. %s", id_)
        if ext == ".pdf":
            etapa("diagnóstico", progresso=2)
            saida_diag = rodar([PY, os.path.join(S_PDF, "diagnostico.py"), orig], env, log)
            json_str = saida_diag[saida_diag.find("{") : saida_diag.rfind("}") + 1]
            diag = json.loads(json_str)
            json.dump(diag, open(os.path.join(dest, "diagnostico.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            if "erro" in diag:
                raise RuntimeError(diag["erro"])
            lang = idioma_ocr(env) or "por"
            etapa("extração/OCR", paginas=diag["paginas"], pagina_atual=0, idioma_ocr=lang, progresso=5)
            ultimo = [0.0]

            def prog(i, n):
                if time.time() - ultimo[0] > 1.2 or i == n:
                    ultimo[0] = time.time()
                    atualizar_trabalho(id_, doc, pagina_atual=i, paginas=n, progresso=5 + int(85 * i / n))

            rodar([PY, os.path.join(S_PDF, "extrair.py"), orig, "--saida", dest, "--lang", lang], env, log, prog)
            etapa("tabelas (CSV)", progresso=91)
            rodar([PY, os.path.join(S_PDF, "tabelas.py"), orig, "--saida", dest], env, log)
            rodar([PY, os.path.join(S_PDF, "tabelas.py"), os.path.join(dest, "transcricao.md"), "--saida", dest], env, log)
        elif ext == ".md":
            etapa("importação do Markdown", progresso=30)
            shutil.copyfile(orig, os.path.join(dest, "transcricao.md"))
            etapa("tabelas (CSV)", progresso=60)
            rodar([PY, os.path.join(S_PDF, "tabelas.py"), os.path.join(dest, "transcricao.md"), "--saida", dest], env, log)
        elif ext == ".csv":
            etapa("importação do CSV", progresso=50)
            os.makedirs(os.path.join(dest, "tabelas"), exist_ok=True)
            shutil.copyfile(orig, os.path.join(dest, "tabelas", arq))
        if os.path.exists(os.path.join(dest, "transcricao.md")):
            etapa("dados críticos", progresso=94)
            rodar([PY, os.path.join(S_PDF, "entidades.py"), os.path.join(dest, "transcricao.md")], env, log)
        etapa("registro", progresso=96)
        rel = os.path.join(dest, "relatorio_extracao.json")
        if os.path.exists(rel):
            C.importar_ip(id_, rel)
            r = json.load(open(rel, encoding="utf-8"))
            registrar_tratamento(
                id_,
                [
                    f"### {agora()} — {arq} (Central CPJ)",
                    f"- SHA-256: `{r.get('sha256_original')}` · páginas: {r.get('paginas')}",
                    f"- Métodos: {r.get('metodos')} · OCR: {r.get('ferramentas', {}).get('ocr')}",
                    f"- Pendentes de transcrição visual: {len(r.get('pendentes_transcricao_visual', []))} · a conferir: {len(r.get('conferir_visualmente', []))}",
                    f"- Saída: `01-extracao\\{doc}\\`",
                ],
            )
        else:
            c = C.carregar(id_)
            c["documentos"] = [d for d in c.get("documentos", []) if d.get("arquivo") != arq] + [{"arquivo": arq, "pasta": doc, "tipo": ext.lstrip(".")}]
            if c["status"] == "recebido":
                c["status"] = "extraido"
                c["datas"]["extraido"] = C.hoje()
            C.salvar(c)
            registrar_tratamento(id_, [f"### {agora()} — {arq} (importado pela Central CPJ, SHA-256 `{sha256(orig)}`)"])
        transcricao = os.path.join(dest, "transcricao.md")
        if os.path.isfile(transcricao):
            etapa("dados da O.S. após OCR / IA local", progresso=97)
            with open(transcricao, encoding="utf-8") as f:
                D_OS.aplicar(C, id_, f.read(), arq, usar_ia=True)
        etapa("indexação", progresso=98)
        rodar([PY, os.path.join(S_BASE, "indexar.py")], env, log)
        atualizar_trabalho(id_, doc, status="concluido", etapa="concluído", fim=agora(), progresso=100)
    except Exception as e:
        atualizar_trabalho(id_, doc, status="erro", erro=str(e), fim=agora())
        with open(log, "a", encoding="utf-8") as lg:
            lg.write(f"\n[{agora()}] ERRO: {e}\n")


def trabalhador():
    while True:
        trab = fila.get()
        try:
            processar(trab)
        finally:
            fila.task_done()


def enfileirar(id_, doc, arquivo):
    d = ler_proc(id_)
    d["trabalhos"] = [t for t in d["trabalhos"] if t["doc"] != doc]
    d["trabalhos"].append({
        "doc": doc, "arquivo": arquivo, "status": "na_fila", "etapa": "na fila", "enfileirado": agora(), "progresso": 0
    })
    gravar_proc(id_, d)
    fila.put({"caso": id_, "doc": doc, "arquivo": arquivo})


def retomar_pendentes():
    for c in C.listar():
        for t in ler_proc(c["id"]).get("trabalhos", []):
            if t.get("status") in ("na_fila", "processando"):
                enfileirar(c["id"], t["doc"], t["arquivo"])


# ================================================================== casos helpers
TEXTO_BUSCA = (
    "id", "ordem_servico", "bo", "inquerito", "processo", "referencia", "natureza", "modalidade", "status",
    "observacoes", "requisitante", "escrivao", "determinacao"
)


def resumo(c):
    proc = ler_proc(c["id"]).get("trabalhos", [])
    pend = [t for t in proc if t.get("status") in ("na_fila", "processando")]
    datas = c.get("datas") or {}
    return {
        k: c.get(k)
        for k in (
            "id", "ordem_servico", "bo", "inquerito", "processo", "natureza", "modalidade", "status",
            "prazo", "requisitante", "escrivao", "prioridade", "criado_por", "responsavel", "visto"
        )
    } | {
        "vitimas": c.get("vitimas") or [],
        "investigados": c.get("investigados") or [],
        "paginas": (c.get("ip") or {}).get("paginas"),
        "recebido": datas.get("recebido"),
        "entregue": datas.get("entregue"),
        "documentos": len(c.get("documentos") or []),
        "prejuizo_declarado": (c.get("financeiro") or {}).get("prejuizo_declarado"),
        "valor_rastreado": (c.get("financeiro") or {}).get("valor_rastreado"),
        "situacao_prazo": C.situacao_prazo(c),
        "processando": bool(pend),
        "progresso_proc": min([t.get("progresso", 0) for t in pend]) if pend else None,
        "etapa_proc": pend[0].get("etapa") if pend else None,
        "erro": any(t.get("status") == "erro" for t in proc),
        "tem_final": bool(C.finais(c["id"])),
        "revisao": c.get("revisao", 1),
    }


def visiveis(u):
    """Delegado e escrivão veem todas as O.S. da unidade na lista (apenas dados de gestão)."""
    return C.listar()


def arvore(base):
    out = []
    for raiz, dirs, arqs in os.walk(base):
        dirs[:] = sorted(d for d in dirs if d not in ("paginas_visao", "ia-logs"))
        for a in sorted(arqs):
            if a.endswith(".tmp") or a.startswith("~$"):
                continue
            p = os.path.join(raiz, a)
            out.append({"caminho": os.path.relpath(p, base).replace("\\", "/"), "tamanho": os.path.getsize(p)})
    return out


def arquivos_relatorio(id_):
    d = os.path.join(C.caminho(id_), "03-relatorios")
    if not os.path.isdir(d):
        return []
    out = []
    for f in sorted(os.listdir(d), key=lambda f: os.path.getmtime(os.path.join(d, f)), reverse=True):
        if f.startswith("~$"):
            continue
        tipo = (
            "final" if "final" in f.lower() else "minuta" if f.startswith("minuta-") else "revisao" if f.startswith("revisao-")
            else "rastreabilidade" if f.startswith("rastreabilidade-") else "docx" if f.endswith(".docx") else "pdf" if f.endswith(".pdf") else "outro"
        )
        out.append({
            "arquivo": f,
            "tipo": tipo,
            "modificado": datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(d, f))).isoformat(timespec="minutes"),
        })
    return out


EDITAVEIS = {
    "ordem_servico", "bo", "inquerito", "processo", "natureza", "modalidade", "vitimas", "investigados", "observacoes",
    "prazo", "requisitante", "escrivao", "prioridade", "determinacao", "responsavel", "financeiro.prejuizo_declarado",
    "financeiro.prejuizo_documentado", "financeiro.valor_rastreado", "resultado.autoria", "horas_trabalho"
}
EDITAVEIS_GESTAO = {
    "ordem_servico", "prazo", "requisitante", "escrivao", "prioridade", "determinacao", "observacoes", "bo", "inquerito", "processo"
}


def pode_alterar_os(u, c):
    return (
        auth.pode(u["perfil"], "trabalho")
        or c.get("criado_por") == u["login"]
        or u["perfil"] == "delegado"
    )


def salvar_upload(campo, exts):
    a = request.files.get(campo)
    if not a or not a.filename:
        raise ValueError("Envie um arquivo.")
    base, ext = nome_seguro(a.filename)
    if ext not in exts:
        raise ValueError(f"Formato não aceito ({', '.join(exts)}).")
    d = os.path.join(WS, "exportacoes", "_recebidos")
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, f"{time.time_ns()}-{base}{ext}")
    a.save(p)
    return p, a.filename


# ================================================================== painel helpers
def assinatura_painel():
    arquivos = [
        os.path.join(WS, "producao", "config.json"),
        os.path.join(S_BASE, "indexar.py"),
        os.path.join(S_BASE, "gerar_painel.py"),
    ]
    plantao_db = os.path.join(WS, "config", "plantao.sqlite")
    if os.path.isfile(plantao_db):
        arquivos.append(plantao_db)
    if os.path.isdir(C.CASOS):
        for nome in sorted(os.listdir(C.CASOS)):
            if nome.startswith("_"):
                continue
            caso = os.path.join(C.CASOS, nome, "caso.json")
            if not os.path.isfile(caso):
                continue
            arquivos.append(caso)
            rels = os.path.join(C.CASOS, nome, "03-relatorios")
            if os.path.isdir(rels):
                arquivos.extend(
                    os.path.join(rels, f)
                    for f in sorted(os.listdir(rels))
                    if not f.startswith("~$")
                    and (
                        "final" in f.lower()
                        or f.lower().startswith("minuta-")
                        or f.lower().startswith("revisao-")
                    )
                    and f.lower().endswith((".md", ".pdf", ".docx"))
                )
    return (
        WS,
        datetime.date.today().isoformat(),
        tuple((p, assinatura_arquivo(p)) for p in arquivos),
    )


def atualizar_painel(chave, app_logger=None):
    if app_logger is None:
        try:
            import servidor
            app_logger = servidor.app.logger
        except Exception:
            pass
    try:
        env = ambiente_ocr()
        subprocess.run(
            [PY, os.path.join(S_BASE, "indexar.py")],
            env=env,
            capture_output=True,
            check=True,
            timeout=300,
            creationflags=SEM_JANELA,
        )
        prod = os.path.join(WS, "producao")
        os.makedirs(prod, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".painel-", dir=prod) as stage:
            out = os.path.join(stage, "producao")
            os.makedirs(out)
            shutil.copyfile(os.path.join(prod, "base.json"), os.path.join(out, "base.json"))
            cfg = os.path.join(prod, "config.json")
            if os.path.isfile(cfg):
                shutil.copyfile(cfg, os.path.join(out, "config.json"))
            subprocess.run(
                [PY, os.path.join(S_BASE, "gerar_painel.py")],
                env=dict(env, CPJ_WORKSPACE=stage, CPJ_WORKSPACE_DADOS=WS),
                capture_output=True,
                check=True,
                timeout=90,
                creationflags=SEM_JANELA,
            )
            os.replace(os.path.join(out, "painel.html"), os.path.join(prod, "painel.html"))
        with _painel_trava:
            _painel_cache.update(chave=chave, erro=False, retentar_apos=0)
    except Exception:
        if app_logger:
            app_logger.exception("Falha ao atualizar painel de produção")
        with _painel_trava:
            _painel_cache.update(erro=True, retentar_apos=time.monotonic() + 30)
    finally:
        with _painel_trava:
            _painel_cache["gerando"] = False
