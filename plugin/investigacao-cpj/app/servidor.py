#!/usr/bin/env python3
"""Central CPJ — sistema local de gestão de O.S./IPs de fraude e estelionato.

Perfis: admin, investigador, delegado, escrivão (login com senha; auditoria de ações).
Painéis: Início (pendências e prazos) · Nova O.S. (cadastro + upload) · Casos · Pesquisa (relacional e textual)
· Estatísticas · Sistema (exportar/importar, bases de consulta, referências, IA, usuários, rede).

Por padrão atende só este computador (127.0.0.1). O admin pode habilitar o acesso pela rede local (HTTPS).
Uso: python servidor.py [--porta 8765] [--sem-navegador] [--workspace PASTA]
"""
import sys, os
if "--workspace" in sys.argv:  # precisa valer antes de importar os módulos de dados
    os.environ["CPJ_WORKSPACE"] = sys.argv[sys.argv.index("--workspace") + 1]

import argparse, datetime, functools, hashlib, ipaddress, json, re, shutil, socket, subprocess, tempfile, threading, time, webbrowser, queue

AQUI = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(AQUI)
S_PDF = os.path.join(PLUGIN, "skills", "pdf-autos-policiais", "scripts")
S_BASE = os.path.join(PLUGIN, "skills", "base-cpj", "scripts")
sys.path.insert(0, S_BASE); sys.path.insert(0, AQUI)
import caso as C         # noqa: E402
import rag as R          # noqa: E402
import consulta as Q     # noqa: E402
import referencias as RF  # noqa: E402
from auth import Auth, PERFIS, DESCRICAO, TODAS  # noqa: E402
from tarefas import Tarefas, gerar_docx, gerar_pdf, soffice, SEM_JANELA  # noqa: E402
import dados_os as D_OS  # noqa: E402
from flask import Flask, abort, jsonify, request, send_file, send_from_directory, session  # noqa: E402

WS = C.WS
PY = sys.executable
TESS_DIR = r"C:\Program Files\Tesseract-OCR"
TESSDATA_LOCAL = os.path.join(WS, "ferramentas", "tessdata")
EXT_OK = {".pdf", ".md", ".csv"}

auth = Auth(WS)
app = Flask(__name__, static_folder=os.path.join(AQUI, "static"), static_url_path="/static")
app.config.update(MAX_CONTENT_LENGTH=2 * 1024 ** 3, SECRET_KEY=auth.segredo(), SESSION_COOKIE_HTTPONLY=True,
                  SESSION_COOKIE_SAMESITE="Strict", PERMANENT_SESSION_LIFETIME=datetime.timedelta(hours=12))
tarefas = Tarefas(WS, C, auth)
fila = queue.Queue()
trava = threading.Lock()
REDE_ARQ = os.path.join(WS, "config", "rede.json")
_ocr_trava = threading.Lock()
_ocr_cache = {"chave": None, "idioma": None, "expira": 0}
_painel_trava = threading.Lock()
_painel_cache = {"chave": None, "gerando": False, "erro": False, "retentar_apos": 0}


# ================================================================== utilidades
def agora(): return datetime.datetime.now().isoformat(timespec="seconds")


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def nome_seguro(n):
    base, ext = os.path.splitext(os.path.basename(n or "arquivo"))
    base = re.sub(r"[^\w\-. ]+", "_", base, flags=re.U).strip(" ._") or "arquivo"
    return base[:80], ext.lower()


def rede_cfg():
    d = {"compartilhar": False, "porta": 8765, "https": True}
    if os.path.exists(REDE_ARQ): d.update(json.load(open(REDE_ARQ, encoding="utf-8")))
    return d


def ips_locais():
    ips = set()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET): ips.add(info[4][0])
    except OSError: pass
    return sorted(i for i in ips if not i.startswith("127."))


def eh_local(): return (request.remote_addr or "") in ("127.0.0.1", "::1")


def pasta_usuario(login):
    """Pasta pessoal de cada usuário: usuarios/<login>/ (relatorios/ recebe cópia dos FINAL das O.S. que ele cadastrou)."""
    d = os.path.join(WS, "usuarios", login)
    for s in ("", "relatorios", "documentos"): os.makedirs(os.path.join(d, s), exist_ok=True)
    return d


def ambiente_ocr():
    env = dict(os.environ, CPJ_WORKSPACE=WS, PYTHONIOENCODING="utf-8")
    if os.path.isdir(TESS_DIR) and TESS_DIR not in env.get("PATH", ""): env["PATH"] = env.get("PATH", "") + ";" + TESS_DIR
    if os.path.exists(os.path.join(TESSDATA_LOCAL, "por.traineddata")): env["TESSDATA_PREFIX"] = TESSDATA_LOCAL
    return env


def assinatura_arquivo(p):
    try:
        st = os.stat(p)
        return st.st_mtime_ns, st.st_size
    except FileNotFoundError:
        return None


def idioma_ocr(env):
    """Compartilha o diagnóstico entre requests; instalação/idiomas invalidam o cache."""
    exe = os.path.join(TESS_DIR, "tesseract.exe")
    tessdata = env.get("TESSDATA_PREFIX") or os.path.join(TESS_DIR, "tessdata")
    chave = (exe, assinatura_arquivo(exe), env.get("PATH"), tessdata,
             assinatura_arquivo(os.path.join(tessdata, "por.traineddata")),
             assinatura_arquivo(os.path.join(tessdata, "eng.traineddata")))
    with _ocr_trava:
        if _ocr_cache["chave"] == chave and time.monotonic() < _ocr_cache["expira"]:
            return _ocr_cache["idioma"]
        idioma = None
        try:
            r = subprocess.run([exe, "--list-langs"], env=env, capture_output=True,
                               text=True, timeout=20, creationflags=SEM_JANELA)
            langs = r.stdout.split() if r.returncode == 0 else []
            idioma = "por" if "por" in langs else ("eng" if "eng" in langs else None)
        except (OSError, subprocess.SubprocessError):
            pass
        _ocr_cache.update(chave=chave, idioma=idioma, expira=time.monotonic() + (300 if idioma else 30))
        return idioma


# ================================================================== autenticação e permissões
def usuario():
    u = session.get("u")
    atual = auth.obter_sessao(u, session.get("v")) if u else None
    if u and atual is None: session.clear()
    return atual


def vincular_sessao(u):
    session.clear(); session.permanent = True
    session["u"] = u["login"]; session["v"] = u["_sessao_id"]


def requer(*perms):
    def deco(fn):
        @functools.wraps(fn)
        def w(*a, **k):
            u = usuario()
            if not u: return jsonify({"erro": "Sessão expirada. Entre novamente.", "login": True}), 401
            if u.get("trocar_senha") and request.endpoint not in ("api_minha_senha",):
                return jsonify({"erro": "Troque a senha temporária para continuar.", "trocar_senha": True}), 428
            if perms and not any(auth.pode(u["perfil"], p) for p in perms): return jsonify({"erro": "Sem permissão."}), 403
            request.usuario = u
            return fn(*a, **k)
        return w
    return deco


def auditar(acao, alvo=""):
    u = getattr(request, "usuario", None) or usuario() or {}
    auth.auditar(u.get("login", "-"), request.remote_addr, acao, alvo)


@app.before_request
def protege_post():
    # mitigação de CSRF: toda escrita exige o cabeçalho enviado pela própria interface
    if request.method == "POST" and request.headers.get("X-CPJ") != "1": abort(403)


@app.after_request
def cabecalhos(r):
    r.headers["X-Content-Type-Options"] = "nosniff"; r.headers["X-Frame-Options"] = "SAMEORIGIN"
    r.headers["Referrer-Policy"] = "no-referrer"; r.headers["Cache-Control"] = "no-store"
    return r


@app.get("/")
def inicio(): return send_from_directory(app.static_folder, "index.html")


@app.get("/api/sessao")
def api_sessao():
    u = usuario()
    return jsonify({"usuario": u, "permissoes": auth.permissoes(u["perfil"]) if u else [], "configurado": auth.tem_usuarios(),
                    "local": eh_local(), "perfis": PERFIS})


@app.post("/api/configurar")
def api_configurar():
    """Primeiro uso: cria o administrador. Só no próprio computador e só se não houver usuários."""
    if auth.tem_usuarios(): return jsonify({"erro": "Sistema já configurado."}), 400
    if not eh_local(): return jsonify({"erro": "A configuração inicial só pode ser feita no computador da Central."}), 403
    d = request.get_json(force=True) or {}
    try:
        u = auth.salvar_usuario(d.get("login"), d.get("nome"), "admin", d.get("senha"), cpf=d.get("cpf") or "",
                                email=d.get("email") or "", cargo=d.get("cargo") or "")
        u = auth.autenticar(u["login"], d.get("senha"))
    except (ValueError, PermissionError) as e:
        return jsonify({"erro": str(e)}), 400
    vincular_sessao(u); pasta_usuario(u["login"])
    auth.auditar(u["login"], request.remote_addr, "configuracao_inicial")
    return jsonify({"ok": True})


@app.post("/api/entrar")
def api_entrar():
    d = request.get_json(force=True) or {}
    try: u = auth.autenticar(d.get("login"), d.get("senha"))
    except PermissionError as e:
        auth.auditar((d.get("login") or "")[:40], request.remote_addr, "login_falhou"); return jsonify({"erro": str(e)}), 401
    vincular_sessao(u)
    auth.auditar(u["login"], request.remote_addr, "login")
    return jsonify({"ok": True, "trocar_senha": u["trocar_senha"]})


@app.post("/api/minha-conta")
@requer()
def api_minha_conta():
    d = request.get_json(force=True) or {}
    try: u = auth.atualizar_contato(request.usuario["login"], email=d.get("email"), cargo=d.get("cargo"))
    except ValueError as e: return jsonify({"erro": str(e)}), 400
    auditar("conta_atualizada"); return jsonify(u)


@app.post("/api/sair")
def api_sair():
    u = usuario()
    if u: auth.auditar(u["login"], request.remote_addr, "logout")
    session.clear(); return jsonify({"ok": True})


@app.post("/api/minha-senha")
@requer()
def api_minha_senha():
    d = request.get_json(force=True) or {}
    try: u = auth.trocar_senha(request.usuario["login"], d.get("atual"), d.get("nova"))
    except (PermissionError, ValueError) as e: return jsonify({"erro": str(e)}), 400
    vincular_sessao(u)
    auditar("troca_senha"); return jsonify({"ok": True})


# ================================================================== usuários, auditoria e rede (admin)
@app.get("/api/usuarios")
@requer("usuarios")
def api_usuarios(): return jsonify(auth.listar())


@app.post("/api/usuarios")
@requer("usuarios")
def api_usuarios_salvar():
    d = request.get_json(force=True) or {}
    try: u = auth.salvar_usuario(d.get("login"), d.get("nome"), d.get("perfil"), d.get("senha") or None, d.get("ativo", True),
                                 cpf=d.get("cpf"), email=d.get("email"), cargo=d.get("cargo"), temporaria=bool(d.get("temporaria")))
    except ValueError as e: return jsonify({"erro": str(e)}), 400
    pasta_usuario(u["login"]); auditar("usuario_salvo", f"{u['login']} ({u['perfil']})"); return jsonify(u)


@app.post("/api/usuarios/<login>/remover")
@requer("usuarios")
def api_usuarios_remover(login):
    try: auth.remover_usuario(login)
    except ValueError as e: return jsonify({"erro": str(e)}), 400
    auditar("usuario_removido", login); return jsonify({"ok": True})


@app.get("/api/auditoria")
@requer("usuarios")
def api_auditoria(): return jsonify(auth.auditoria(300))


@app.get("/api/perfis")
@requer("usuarios")
def api_perfis():
    m = auth.matriz()
    return jsonify({"matriz": {k: sorted(v) for k, v in m.items()}, "descricao": DESCRICAO, "perfis": PERFIS,
                    "editaveis": sorted(TODAS - {"usuarios", "rede"})})


@app.post("/api/perfis")
@requer("usuarios")
def api_perfis_salvar():
    m = auth.salvar_matriz((request.get_json(force=True) or {}).get("matriz") or {})
    auditar("perfis_alterados", json.dumps(m, ensure_ascii=False)[:300]); return jsonify(m)


@app.get("/api/responsaveis")
@requer("trabalho")
def api_responsaveis(): return jsonify([{"login": u["login"], "nome": u["nome"]} for u in auth.por_permissao("trabalho")])


@app.get("/api/minha-pasta")
@requer()
def api_minha_pasta():
    d = pasta_usuario(request.usuario["login"])
    return jsonify({"pasta": d if eh_local() else None, "arquivos": arvore(d)})


@app.get("/minha-pasta/<path:rel>")
@requer()
def api_minha_pasta_arquivo(rel):
    base = os.path.normpath(pasta_usuario(request.usuario["login"])); alvo = os.path.normpath(os.path.join(base, rel))
    if not alvo.startswith(base + os.sep) or not os.path.isfile(alvo): abort(404)
    auditar("download_pasta_pessoal", rel); return send_file(alvo, as_attachment=True)


@app.post("/api/minha-pasta/abrir")
@requer()
def api_minha_pasta_abrir():
    if not eh_local(): return jsonify({"erro": "Disponível apenas no computador da Central. Baixe os arquivos pelo navegador."}), 403
    os.startfile(pasta_usuario(request.usuario["login"])); return jsonify({"ok": True})


@app.get("/api/rede")
@requer("usuarios")
def api_rede():
    cfg = rede_cfg(); proto = "https" if cfg["https"] else "http"
    return jsonify(cfg | {"enderecos": [f"{proto}://{ip}:{cfg['porta']}" for ip in ips_locais()], "ativo_agora": app.config.get("REDE_ATIVA", False)})


@app.post("/api/rede")
@requer("rede")
def api_rede_salvar():
    d = request.get_json(force=True) or {}
    if d.get("compartilhar") and auth.ha_senha_temporaria():
        return jsonify({"erro": "Há usuários com senha temporária (" + ", ".join(auth.ha_senha_temporaria()) +
                        "). Eles precisam trocá-la antes de liberar o acesso pela rede."}), 400
    cfg = rede_cfg(); cfg.update(compartilhar=bool(d.get("compartilhar")), https=bool(d.get("https", True)))
    os.makedirs(os.path.dirname(REDE_ARQ), exist_ok=True)
    json.dump(cfg, open(REDE_ARQ, "w", encoding="utf-8"), indent=2)
    auditar("rede_alterada", json.dumps(cfg)); return jsonify(cfg | {"reiniciar": True})


# ================================================================== processamento de documentos (OCR/extração)
def proc_path(id_): return os.path.join(C.caminho(id_), "processamento.json")


def ler_proc(id_):
    p = proc_path(id_)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {"trabalhos": []}


def gravar_proc(id_, dados):
    with trava:
        p = proc_path(id_); tmp = p + ".tmp"
        json.dump(dados, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1); os.replace(tmp, p)


def atualizar_trabalho(id_, doc, **campos):
    d = ler_proc(id_)
    for t in d["trabalhos"]:
        if t["doc"] == doc: t.update(campos)
    gravar_proc(id_, d)


def registrar_tratamento(id_, linhas):
    with open(os.path.join(C.caminho(id_), "registro-tratamento.md"), "a", encoding="utf-8") as f:
        f.write("\n" + "\n".join(linhas) + "\n")


def rodar(cmd, env, log, progresso=None):
    with open(log, "a", encoding="utf-8") as lg:
        lg.write(f"\n[{agora()}] $ {' '.join(cmd)}\n"); lg.flush()
        p = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                             encoding="utf-8", errors="replace", creationflags=SEM_JANELA)
        saida = []
        for ln in p.stdout:
            m = re.match(r"progresso (\d+)/(\d+)", ln)
            if m and progresso: progresso(int(m.group(1)), int(m.group(2))); continue
            saida.append(ln); lg.write(ln)
        p.wait()
        if p.returncode != 0: raise RuntimeError(f"falhou ({p.returncode}): {os.path.basename(cmd[1])} — ver log")
        return "".join(saida)


def processar(trab):
    id_, doc, arq = trab["caso"], trab["doc"], trab["arquivo"]
    base = C.caminho(id_); orig = os.path.join(base, "00-originais", arq)
    dest = os.path.join(base, "01-extracao", doc); os.makedirs(dest, exist_ok=True)
    log = os.path.join(dest, "processamento.log"); env = ambiente_ocr(); ext = os.path.splitext(arq)[1].lower()
    etapa = lambda nome, **x: atualizar_trabalho(id_, doc, etapa=nome, **x)
    atualizar_trabalho(id_, doc, status="processando", inicio=agora(), erro=None, progresso=0)
    try:
        etapa("dados da O.S. (texto original)", progresso=1)
        try:
            D_OS.aplicar(C, id_, D_OS.ler_original(orig), arq)
        except Exception:
            app.logger.exception("Falha no preenchimento inicial da O.S. %s", id_)
        if ext == ".pdf":
            etapa("diagnóstico", progresso=2)
            diag = json.loads(rodar([PY, os.path.join(S_PDF, "diagnostico.py"), orig], env, log))
            json.dump(diag, open(os.path.join(dest, "diagnostico.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            if "erro" in diag: raise RuntimeError(diag["erro"])
            lang = idioma_ocr(env) or "por"
            etapa("extração/OCR", paginas=diag["paginas"], pagina_atual=0, idioma_ocr=lang, progresso=5)
            ultimo = [0.0]

            def prog(i, n):
                if time.time() - ultimo[0] > 1.2 or i == n:
                    ultimo[0] = time.time(); atualizar_trabalho(id_, doc, pagina_atual=i, paginas=n, progresso=5 + int(85 * i / n))
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
            os.makedirs(os.path.join(dest, "tabelas"), exist_ok=True); shutil.copyfile(orig, os.path.join(dest, "tabelas", arq))
        if os.path.exists(os.path.join(dest, "transcricao.md")):
            etapa("dados críticos", progresso=94)
            rodar([PY, os.path.join(S_PDF, "entidades.py"), os.path.join(dest, "transcricao.md")], env, log)
        etapa("registro", progresso=96)
        rel = os.path.join(dest, "relatorio_extracao.json")
        if os.path.exists(rel):
            C.importar_ip(id_, rel); r = json.load(open(rel, encoding="utf-8"))
            registrar_tratamento(id_, [f"### {agora()} — {arq} (Central CPJ)", f"- SHA-256: `{r.get('sha256_original')}` · páginas: {r.get('paginas')}",
                                       f"- Métodos: {r.get('metodos')} · OCR: {r.get('ferramentas', {}).get('ocr')}",
                                       f"- Pendentes de transcrição visual: {len(r.get('pendentes_transcricao_visual', []))} · a conferir: {len(r.get('conferir_visualmente', []))}",
                                       f"- Saída: `01-extracao\\{doc}\\`"])
        else:
            c = C.carregar(id_)
            c["documentos"] = [d for d in c.get("documentos", []) if d.get("arquivo") != arq] + [{"arquivo": arq, "pasta": doc, "tipo": ext.lstrip(".")}]
            if c["status"] == "recebido": c["status"] = "extraido"; c["datas"]["extraido"] = C.hoje()
            C.salvar(c); registrar_tratamento(id_, [f"### {agora()} — {arq} (importado pela Central CPJ, SHA-256 `{sha256(orig)}`)"])
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
        with open(log, "a", encoding="utf-8") as lg: lg.write(f"\n[{agora()}] ERRO: {e}\n")


def trabalhador():
    while True:
        trab = fila.get()
        try: processar(trab)
        finally: fila.task_done()


def enfileirar(id_, doc, arquivo):
    d = ler_proc(id_)
    d["trabalhos"] = [t for t in d["trabalhos"] if t["doc"] != doc]
    d["trabalhos"].append({"doc": doc, "arquivo": arquivo, "status": "na_fila", "etapa": "na fila", "enfileirado": agora(), "progresso": 0})
    gravar_proc(id_, d); fila.put({"caso": id_, "doc": doc, "arquivo": arquivo})


def retomar_pendentes():
    for c in C.listar():
        for t in ler_proc(c["id"]).get("trabalhos", []):
            if t.get("status") in ("na_fila", "processando"): enfileirar(c["id"], t["doc"], t["arquivo"])


# ================================================================== O.S., casos e pendências
TEXTO_BUSCA = ("id", "ordem_servico", "bo", "inquerito", "processo", "referencia", "natureza", "modalidade", "status",
               "observacoes", "requisitante", "escrivao", "determinacao")


def resumo(c):
    proc = ler_proc(c["id"]).get("trabalhos", [])
    pend = [t for t in proc if t.get("status") in ("na_fila", "processando")]
    return {k: c.get(k) for k in ("id", "ordem_servico", "bo", "inquerito", "processo", "natureza", "modalidade", "status",
                                  "prazo", "requisitante", "escrivao", "prioridade", "criado_por", "responsavel", "visto")} | {
        "vitimas": c.get("vitimas") or [], "investigados": c.get("investigados") or [],
        "paginas": (c.get("ip") or {}).get("paginas"), "recebido": c["datas"].get("recebido"), "entregue": c["datas"].get("entregue"),
        "documentos": len(c.get("documentos") or []), "situacao_prazo": C.situacao_prazo(c),
        "processando": bool(pend), "progresso_proc": min([t.get("progresso", 0) for t in pend]) if pend else None,
        "erro": any(t.get("status") == "erro" for t in proc), "tem_final": bool(C.finais(c["id"]))}


def visiveis(u):
    """Delegado e escrivão veem todas as O.S. da unidade na lista (apenas dados de gestão)."""
    return C.listar()


@app.get("/api/pendencias")
@requer("casos")
def api_pendencias():
    u = request.usuario; cs = [resumo(c) for c in visiveis(u)]
    abertos = [c for c in cs if c["status"] not in ("entregue", "arquivado")]
    grupo = lambda s: sorted([c for c in abertos if c["situacao_prazo"] == s], key=lambda c: c["prazo"] or "")
    hoje = C.hoje(); mes = hoje[:7]
    return jsonify({
        "novas": [c for c in abertos if not c["visto"] and (c.get("responsavel") or "") in ("", u["login"])] if auth.pode(u["perfil"], "trabalho") else [],
        "meus": [c for c in abertos if c.get("responsavel") == u["login"]],
        "vencidos": grupo("vencido"), "hoje": grupo("hoje"), "proximos": grupo("proximo"),
        "sem_prazo": [c for c in abertos if not c["prazo"]],
        "em_andamento": {s: sum(1 for c in abertos if c["status"] == s) for s in C.STATUS[:5] + ["devolvido"]},
        "minhas": [c for c in cs if c["criado_por"] == u["login"]][:30],
        "entregues_hoje": sum(1 for c in cs if c["entregue"] == hoje),
        "entregues_mes": sum(1 for c in cs if (c["entregue"] or "").startswith(mes)),
        "processando": [c for c in cs if c["processando"]],
    })


@app.get("/api/casos")
@requer("casos")
def api_casos():
    q = (request.args.get("q") or "").strip().lower(); st = request.args.get("status") or ""
    pz = request.args.get("prazo") or ""; meus = request.args.get("meus") == "1"; out = []
    for c in visiveis(request.usuario):
        r = resumo(c)
        if st and c.get("status") != st: continue
        if pz and r["situacao_prazo"] != pz: continue
        if meus and c.get("responsavel") != request.usuario["login"] and c.get("criado_por") != request.usuario["login"]: continue
        if q:
            alvo = " ".join(str(c.get(k) or "") for k in TEXTO_BUSCA) + " " + " ".join(c.get("vitimas") or []) + " " + " ".join(c.get("investigados") or [])
            q_dig = re.sub(r"\D", "", q)
            if q not in alvo.lower() and not (len(q_dig) >= 3 and q_dig in re.sub(r"\D", "", alvo)): continue
        out.append(r)
    out.sort(key=lambda r: ({"vencido": 0, "hoje": 1, "proximo": 2}.get(r["situacao_prazo"], 3), r.get("prazo") or "9", r["id"]))
    return jsonify(out)


def arvore(base):
    out = []
    for raiz, dirs, arqs in os.walk(base):
        dirs[:] = sorted(d for d in dirs if d not in ("paginas_visao", "ia-logs"))
        for a in sorted(arqs):
            if a.endswith(".tmp") or a.startswith("~$"): continue
            p = os.path.join(raiz, a)
            out.append({"caminho": os.path.relpath(p, base).replace("\\", "/"), "tamanho": os.path.getsize(p)})
    return out


def arquivos_relatorio(id_):
    d = os.path.join(C.caminho(id_), "03-relatorios")
    if not os.path.isdir(d): return []
    out = []
    for f in sorted(os.listdir(d), key=lambda f: os.path.getmtime(os.path.join(d, f)), reverse=True):
        if f.startswith("~$"): continue
        tipo = ("final" if "final" in f.lower() else "minuta" if f.startswith("minuta-") else "revisao" if f.startswith("revisao-")
                else "rastreabilidade" if f.startswith("rastreabilidade-") else "docx" if f.endswith(".docx") else "pdf" if f.endswith(".pdf") else "outro")
        out.append({"arquivo": f, "tipo": tipo, "modificado": datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(d, f))).isoformat(timespec="minutes")})
    return out


@app.get("/api/casos/<id_>")
@requer("casos")
def api_caso(id_):
    try: c = C.carregar(id_)
    except (FileNotFoundError, ValueError): abort(404)
    u = request.usuario; trabalho = auth.pode(u["perfil"], "trabalho")
    if trabalho and not c.get("visto"): c["visto"] = True; C.salvar(c)
    rels = arquivos_relatorio(id_)
    out = {"caso": c if trabalho else {k: c.get(k) for k in ("id", "ordem_servico", "bo", "inquerito", "processo", "natureza",
                                                           "status", "prazo", "requisitante", "escrivao", "prioridade", "determinacao",
                                                           "criado_por", "datas", "observacoes", "documentos", "preenchimento_os")},
           "resumo": resumo(c), "processamento": ler_proc(id_),
           "relatorios": rels if trabalho else [r for r in rels if r["tipo"] == "final"],
           "trabalho": trabalho}
    if trabalho:
        out["arquivos"] = arvore(C.caminho(id_))
        out["ia"] = [t for t in tarefas.listar(todas=True) if t["caso"] == id_][:5]
    else:
        out["arquivos"] = [a for a in arvore(C.caminho(id_)) if a["caminho"].startswith("00-originais/")]
    return jsonify(out)


EDITAVEIS = {"ordem_servico", "bo", "inquerito", "processo", "natureza", "modalidade", "vitimas", "investigados", "observacoes",
             "prazo", "requisitante", "escrivao", "prioridade", "determinacao", "responsavel", "financeiro.prejuizo_declarado",
             "financeiro.prejuizo_documentado", "financeiro.valor_rastreado", "resultado.autoria", "horas_trabalho"}
EDITAVEIS_GESTAO = {"ordem_servico", "prazo", "requisitante", "escrivao", "prioridade", "determinacao", "observacoes", "bo", "inquerito", "processo"}


def pode_alterar_os(u, c):
    """Mesma regra para edição, cadastro repetido e inclusão de documentos."""
    return (auth.pode(u["perfil"], "trabalho")
            or c.get("criado_por") == u["login"] or u["perfil"] == "delegado")


@app.post("/api/casos/<id_>")
@requer("casos")
def api_caso_salvar(id_):
    u = request.usuario; d = request.get_json(force=True) or {}
    permitidos = EDITAVEIS if auth.pode(u["perfil"], "trabalho") else EDITAVEIS_GESTAO
    try:
        c = C.carregar(id_)
        if not pode_alterar_os(u, c):
            return jsonify({"erro": "Só quem cadastrou a O.S. (ou o delegado) pode alterá-la."}), 403
        novo_status = d.pop("status", None) if auth.pode(u["perfil"], "trabalho") else None
        pares = {k: v for k, v in d.items() if k in permitidos}
        if pares:
            C.set_campos(id_, pares)
            c_manual = C.carregar(id_)
            if "preenchimento_os" in c_manual:
                registro = c_manual["preenchimento_os"]
                for k in pares:
                    registro.get("fontes", {}).pop(k, None)
                    registro.get("conflitos", {}).pop(k, None)
                registro["pendentes"] = [k for k in D_OS.CAMPOS if not c_manual.get(k)]
                C.salvar(c_manual)
        if novo_status and novo_status != c.get("status"): C.status(id_, novo_status, origem="central")
        auditar("caso_editado", f"{id_}: {', '.join(pares) or ''}{' status→' + novo_status if novo_status else ''}")
        return jsonify(resumo(C.carregar(id_)))
    except (FileNotFoundError, ValueError) as e:
        return jsonify({"erro": str(e)}), 400


@app.post("/api/os/detectar")
@requer("os")
def api_os_detectar():
    """Prévia local sem gravar originais nem criar caso; OCR ocorre após recebimento."""
    encontrados, conflitos = {}, {}
    for arquivo in request.files.getlist("arquivos"):
        ext = os.path.splitext(arquivo.filename or "")[1].lower()
        if ext not in (".pdf", ".md"):
            continue
        if arquivo.content_length and arquivo.content_length > 64 * 1024 ** 2:
            return jsonify({"erro": "Arquivo grande: envie para processamento completo."}), 413
        with tempfile.TemporaryDirectory(prefix="cpj-detectar-os-") as tmp:
            p = os.path.join(tmp, "documento" + ext)
            with open(p, "wb") as f:
                dados = arquivo.stream.read(64 * 1024 ** 2 + 1)
                if len(dados) > 64 * 1024 ** 2:
                    return jsonify({"erro": "Arquivo grande: envie para processamento completo."}), 413
                f.write(dados)
            try: valores, ambiguos = D_OS.extrair(D_OS.ler_original(p), arquivo.filename)
            except Exception: continue  # PDF protegido/sem texto seguirá para OCR no caso
        for k, item in valores.items():
            if k in conflitos: conflitos[k].append(item)
            elif k in encontrados and encontrados[k]["valor"] != item["valor"]:
                conflitos[k] = [encontrados.pop(k), item]
            else: encontrados[k] = item
        for k, itens in ambiguos.items():
            conflitos.setdefault(k, []).extend(itens)
            if k in encontrados: conflitos[k].append(encontrados.pop(k))
    return jsonify({"campos": encontrados, "conflitos": conflitos,
                    "pendentes": [k for k in D_OS.CAMPOS if k not in encontrados]})


@app.get("/api/os/ia-local")
@requer("usuarios")
def api_os_ia_local():
    return jsonify({"modelo": D_OS.modelo_local(), "ambiente": "CPJ_IA_LOCAL_MODELO" in os.environ})


@app.post("/api/os/ia-local")
@requer("usuarios")
def api_os_ia_local_salvar():
    modelo = (request.get_json(force=True) or {}).get("modelo", "")
    if not isinstance(modelo, str) or len(modelo) > 160 or not re.fullmatch(r"[\w./:@-]*", modelo, re.A):
        return jsonify({"erro": "Informe o nome do modelo local instalado no Ollama."}), 400
    if "CPJ_IA_LOCAL_MODELO" in os.environ:
        return jsonify({"erro": "Modelo definido pelo ambiente. Altere CPJ_IA_LOCAL_MODELO e reinicie a Central."}), 409
    config = os.path.join(WS, "config"); os.makedirs(config, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".ia-local-", dir=config)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f: json.dump({"modelo": modelo}, f)
        os.replace(tmp, os.path.join(config, "ia-local-os.json"))
    finally:
        if os.path.exists(tmp): os.remove(tmp)
    auditar("ia_local_os_configurada", modelo or "desativada")
    return jsonify({"modelo": modelo})


@app.post("/api/os")
@requer("os")
def api_os():
    """Cadastro de O.S. + upload dos arquivos (PDF do IP, MD ou CSV)."""
    f, u = request.form, request.usuario
    os_num = (f.get("os") or "").strip()
    id_informado = (f.get("caso_id") or "").strip()
    somente_cadastro = f.get("somente_cadastro") == "1"
    arquivos = [a for a in request.files.getlist("arquivos") if a and a.filename]
    if somente_cadastro: arquivos = []
    tem_campos = any((f.get(k) or "").strip() for k in ("bo", "inquerito", "processo", "escrivao", "natureza", "determinacao"))
    if not os_num and not id_informado and not (somente_cadastro and tem_campos) and not any(os.path.splitext(a.filename)[1].lower() in EXT_OK for a in arquivos):
        return jsonify({"erro": "Informe a O.S. ou envie o IP/processo para preenchimento automático."}), 400
    if id_informado:
        try:
            if not C.existe(id_informado): return jsonify({"erro": "Cadastro não encontrado. Inicie um novo cadastro."}), 400
        except ValueError:
            return jsonify({"erro": "Identificador de cadastro inválido."}), 400
    id_ = id_informado or (C.id_de_os(os_num) if os_num else "RECEBIDO-" + os.urandom(12).hex())
    criado = False
    extras = {"prazo": f.get("prazo") or None, "requisitante": (f.get("requisitante") or "").strip(),
              "escrivao": (f.get("escrivao") or "").strip(),
              "prioridade": f.get("prioridade") or "normal", "determinacao": (f.get("determinacao") or "").strip()[:4000],
              "criado_por": u["login"], "visto": u["perfil"] in ("investigador",),
              "responsavel": u["login"] if auth.pode(u["perfil"], "trabalho") and u["perfil"] != "admin" else ""}
    if not C.existe(id_):
        C.novo(os_num, f.get("bo", "").strip(), f.get("inquerito", "").strip(), f.get("processo", "").strip(),
               f.get("natureza", "").strip(), f.get("recebido") or None, id_=id_, extras=extras)
        criado = True
    else:
        if not pode_alterar_os(u, C.carregar(id_)):
            return jsonify({"erro": "Só quem cadastrou a O.S. (ou o delegado) pode alterá-la."}), 403
        upd = {k: (f.get(k) or "").strip() for k in ("bo", "inquerito", "processo") if (f.get(k) or "").strip()}
        upd |= {k: v for k, v in extras.items() if k in ("prazo", "requisitante", "escrivao", "determinacao") and v}
        if somente_cadastro:
            upd = {k: (f.get(k) or "").strip() for k in
                   ("bo", "inquerito", "processo", "requisitante", "escrivao", "determinacao", "prazo", "prioridade") if k in f}
            if "os" in f: upd["ordem_servico"] = os_num
            if "natureza" in f and auth.pode(u["perfil"], "trabalho"): upd["natureza"] = f.get("natureza", "").strip()
        if upd: C.set_campos(id_, upd)
        c_atual = C.carregar(id_)
        if "preenchimento_os" in c_atual:
            registro = c_atual["preenchimento_os"]
            for k in upd:
                registro.get("fontes", {}).pop(k, None)
                registro.get("conflitos", {}).pop(k, None)
            registro["pendentes"] = [k for k in D_OS.CAMPOS if not c_atual.get(k)]
            c_atual["referencia"] = " / ".join(f"{rotulo} {c_atual[k]}" for k, rotulo in
                                               (("bo", "BO"), ("inquerito", "IP"), ("processo", "Processo")) if c_atual.get(k))
            C.salvar(c_atual)
        if u["perfil"] != "investigador": C.set_campos(id_, {"visto": "false"})
    orig_dir = os.path.join(C.caminho(id_), "00-originais"); os.makedirs(orig_dir, exist_ok=True)
    recebidos, ignorados = [], []
    for a in arquivos:
        base, ext = nome_seguro(a.filename)
        if ext not in EXT_OK: ignorados.append(f"{a.filename} (tipo não aceito)"); continue
        tmp = os.path.join(orig_dir, f".upload-{time.time_ns()}{ext}"); a.save(tmp); h = sha256(tmp)
        rep = next((x for x in os.listdir(orig_dir) if not x.startswith(".") and sha256(os.path.join(orig_dir, x)) == h), None)
        if rep: os.remove(tmp); ignorados.append(f"{a.filename} (idêntico a {rep})"); continue
        nome, k = f"{base}{ext}", 2
        while os.path.exists(os.path.join(orig_dir, nome)): nome, k = f"{base}_{k}{ext}", k + 1
        os.replace(tmp, os.path.join(orig_dir, nome))
        try: os.chmod(os.path.join(orig_dir, nome), 0o444)
        except Exception: pass
        enfileirar(id_, os.path.splitext(nome)[0], nome); recebidos.append(nome)
    auditar("os_cadastrada" if criado else "os_atualizada", f"{id_}: {len(recebidos)} arquivo(s)")
    return jsonify({"caso": id_, "criado": criado, "recebidos": recebidos, "ignorados": ignorados})


@app.post("/api/casos/<id_>/reprocessar/<doc>")
@requer("trabalho")
def api_reprocessar(id_, doc):
    t = next((t for t in ler_proc(id_).get("trabalhos", []) if t["doc"] == doc), None)
    if not t: abort(404)
    enfileirar(id_, doc, t["arquivo"]); auditar("reprocessar", f"{id_}/{doc}"); return jsonify({"ok": True})


@app.post("/api/casos/<id_>/baixa")
@requer("trabalho")
def api_baixa(id_):
    d = request.get_json(silent=True) or {}
    try:
        if d.get("desfazer"): C.status(id_, "minuta"); auditar("baixa_desfeita", id_)
        else:
            fs = C.finais(id_)
            c = C.status(id_, "entregue", data=d.get("data") or None, origem="central", arquivo=fs[-1] if fs else None)
            if fs and not any(r.get("arquivo") == fs[-1] for r in c.get("relatorios", [])):
                C.registrar_relatorio(id_, fs[-1], data=c["datas"]["entregue"])
            auditar("baixa", id_)
        return jsonify(resumo(C.carregar(id_)))
    except (FileNotFoundError, ValueError) as e:
        return jsonify({"erro": str(e)}), 400


@app.post("/api/casos/<id_>/abrir")
@requer("trabalho")
def api_abrir(id_):
    if not eh_local(): return jsonify({"erro": "Disponível apenas no computador da Central."}), 403
    sub = (request.get_json(silent=True) or {}).get("sub", "")
    alvo = os.path.normpath(os.path.join(C.caminho(id_), sub))
    if not alvo.startswith(os.path.normpath(C.caminho(id_))) or not os.path.exists(alvo): abort(404)
    os.startfile(alvo); return jsonify({"ok": True})


@app.get("/arquivo/<id_>/<path:rel>")
@requer("casos")
def api_arquivo(id_, rel):
    base = os.path.normpath(C.caminho(id_)); alvo = os.path.normpath(os.path.join(base, rel))
    if not alvo.startswith(base + os.sep) or not os.path.isfile(alvo): abort(404)
    u = request.usuario
    if not auth.pode(u["perfil"], "trabalho"):
        r = rel.replace("\\", "/")
        final = r.startswith("03-relatorios/") and "final" in r.lower()
        if not (final or r.startswith("00-originais/")): abort(403)
    auditar("download", f"{id_}/{rel}")
    ext = os.path.splitext(alvo)[1].lower()
    if ext in (".md", ".csv", ".json", ".log", ".txt", ".jsonl"): return send_file(alvo, mimetype="text/plain; charset=utf-8")
    return send_file(alvo, as_attachment=ext in (".docx", ".xlsx"))


@app.get("/api/fila")
@requer("casos")
def api_fila():
    ts = []
    limite = (datetime.datetime.now() - datetime.timedelta(hours=12)).isoformat()
    for c in C.listar():
        for t in ler_proc(c["id"]).get("trabalhos", []):
            if t.get("status") in ("na_fila", "processando", "erro") or (t.get("fim") or "") >= limite: ts.append(t | {"caso": c["id"]})
    ordem = {"processando": 0, "na_fila": 1, "erro": 2, "concluido": 3}
    ts.sort(key=lambda t: (ordem.get(t.get("status"), 9), t.get("enfileirado") or ""))
    return jsonify({"trabalhos": ts, "idioma_ocr": idioma_ocr(ambiente_ocr())})


# ================================================================== relatório: minuta, DOCX, PDF, FINAL
def ler_minuta(txt):
    meta, corpo = {}, txt
    m = re.match(r"\s*---\s*\n(.*?)\n---\s*\n(.*)", txt, flags=re.S)
    if m:
        for ln in m.group(1).splitlines():
            if ":" in ln: k, v = ln.split(":", 1); meta[k.strip()] = v.strip()
        corpo = m.group(2)
    secoes, atual = {"RESUMO DOS FATOS": [], "DILIGÊNCIAS REALIZADAS": [], "CONCLUSÃO": []}, None
    for ln in corpo.splitlines():
        t = re.match(r"^##\s+(.+?)\s*$", ln)
        if t and not ln.startswith("###"):
            nome = t.group(1).strip().upper(); atual = next((s for s in secoes if s in nome or nome in s), None); continue
        if atual: secoes[atual].append(ln)
    return meta, {k: "\n".join(v).strip() for k, v in secoes.items()}


CAMPOS_MINUTA = ["caso", "versao", "ordem_servico", "referencia", "natureza", "investigados", "vitimas", "local", "data_fatos",
                 "local_data", "data_rodape", "delegado"]


def ultima_minuta(id_):
    d = os.path.join(C.caminho(id_), "03-relatorios")
    ms = sorted((f for f in os.listdir(d) if re.match(r"minuta-v\d+\.md$", f)), key=lambda f: int(re.findall(r"\d+", f)[0])) if os.path.isdir(d) else []
    return ms[-1] if ms else None


@app.get("/api/casos/<id_>/minuta")
@requer("trabalho")
def api_minuta(id_):
    nome = request.args.get("arquivo") or ultima_minuta(id_)
    if not nome:
        c = C.carregar(id_); dp = {}
        pp = os.path.join(WS, "modelos", "dados-padrao.json")
        if os.path.exists(pp): dp = json.load(open(pp, encoding="utf-8"))
        hoje = datetime.date.today()
        meses = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
        meta = {"caso": id_, "versao": "01", "ordem_servico": c.get("ordem_servico"), "referencia": c.get("referencia"),
                "natureza": c.get("natureza"), "investigados": ", ".join(c.get("investigados") or []), "vitimas": ", ".join(c.get("vitimas") or []),
                "local": "", "data_fatos": "", "local_data": f"{dp.get('cidade_uf', 'Presidente Prudente, SP')}, {hoje.day} de {meses[hoje.month - 1]} de {hoje.year}",
                "data_rodape": hoje.strftime("%d/%m/%Y"), "delegado": dp.get("delegado_padrao") or c.get("requisitante") or ""}
        return jsonify({"arquivo": None, "meta": meta, "secoes": {"RESUMO DOS FATOS": "", "DILIGÊNCIAS REALIZADAS": "", "CONCLUSÃO": ""}})
    p = os.path.join(C.caminho(id_), "03-relatorios", os.path.basename(nome))
    if not os.path.exists(p): abort(404)
    meta, sec = ler_minuta(open(p, encoding="utf-8").read())
    return jsonify({"arquivo": os.path.basename(nome), "meta": meta, "secoes": sec})


@app.post("/api/casos/<id_>/minuta")
@requer("trabalho")
def api_minuta_salvar(id_):
    d = request.get_json(force=True) or {}
    rels = os.path.join(C.caminho(id_), "03-relatorios"); os.makedirs(rels, exist_ok=True)
    ult = ultima_minuta(id_); v = (int(re.findall(r"\d+", ult)[0]) + 1) if ult else 1
    meta = {k: str((d.get("meta") or {}).get(k) or "").replace("\n", " ").strip() for k in CAMPOS_MINUTA}
    meta.update(caso=id_, versao=f"{v:02d}", gerado_em=C.hoje(), editado_por=request.usuario["login"])
    sec = d.get("secoes") or {}
    txt = "---\n" + "\n".join(f"{k}: {val}" for k, val in meta.items()) + "\n---\n\n" + "\n\n".join(
        f"## {s}\n\n{(sec.get(s) or '').strip()}" for s in ("RESUMO DOS FATOS", "DILIGÊNCIAS REALIZADAS", "CONCLUSÃO")) + "\n"
    nome = f"minuta-v{v:02d}.md"
    open(os.path.join(rels, nome), "w", encoding="utf-8").write(txt)
    c = C.carregar(id_)
    if c["status"] in ("recebido", "extraido", "em_analise", "analisado"): C.status(id_, "minuta")
    out = {"arquivo": nome}
    if d.get("gerar_docx", True):
        try: out |= gerar_docx(WS, id_, nome)
        except RuntimeError as e: out["erro_docx"] = str(e)
    auditar("minuta_salva", f"{id_}/{nome}"); return jsonify(out)


@app.post("/api/casos/<id_>/docx")
@requer("trabalho")
def api_docx(id_):
    nome = (request.get_json(silent=True) or {}).get("minuta") or ultima_minuta(id_)
    if not nome: return jsonify({"erro": "Não há minuta."}), 400
    try: out = gerar_docx(WS, id_, os.path.basename(nome))
    except RuntimeError as e: return jsonify({"erro": str(e)}), 400
    auditar("docx_gerado", f"{id_}/{out['docx']}"); return jsonify(out)


@app.post("/api/casos/<id_>/pdf")
@requer("trabalho")
def api_pdf(id_):
    nome = os.path.basename((request.get_json(silent=True) or {}).get("docx") or "")
    if not nome.endswith(".docx"): return jsonify({"erro": "Informe o DOCX."}), 400
    try: out = gerar_pdf(WS, id_, nome)
    except RuntimeError as e: return jsonify({"erro": str(e)}), 400
    auditar("pdf_gerado", f"{id_}/{out['pdf']}"); return jsonify(out)


@app.post("/api/casos/<id_>/final")
@requer("trabalho")
def api_final(id_):
    """Define um DOCX como relatório FINAL (gera também o .md para calibração/RAG) e dá baixa."""
    nome = os.path.basename((request.get_json(silent=True) or {}).get("docx") or "")
    d = os.path.join(C.caminho(id_), "03-relatorios"); p = os.path.join(d, nome)
    if not nome.endswith(".docx") or not os.path.exists(p): return jsonify({"erro": "DOCX não encontrado."}), 400
    final = os.path.join(d, f"RELATORIO-{id_}-FINAL.docx"); shutil.copyfile(p, final)
    try:
        texto = RF.extrair_texto(final); c = C.carregar(id_)
        open(os.path.join(d, f"RELATORIO-{id_}-FINAL.md"), "w", encoding="utf-8").write(
            f"---\ncaso: {id_}\ntipo: relatorio-final\nmodalidade: {c.get('modalidade') or ''}\norigem_docx: {nome}\n---\n\n{texto}")
    except Exception: pass
    c = C.status(id_, "entregue", origem="central", arquivo=os.path.basename(final))
    versoes = len([f for f in os.listdir(d) if re.match(r"minuta-v\d+\.md$", f)])
    C.registrar_relatorio(id_, os.path.basename(final), data=c["datas"]["entregue"], versoes=versoes or None)
    criador = c.get("criado_por")
    if criador and auth.obter(criador):
        shutil.copyfile(final, os.path.join(pasta_usuario(criador), "relatorios", f"RELATORIO-{id_}-FINAL.docx"))
    auditar("relatorio_final", f"{id_}/{nome}"); threading.Thread(target=tarefas.indexar, daemon=True).start()
    return jsonify({"ok": True, "final": os.path.basename(final)})


# ================================================================== IA
@app.get("/api/ia/status")
@requer("ia")
def api_ia_status(): return jsonify(tarefas.claude_status())


@app.post("/api/ia/login")
@requer("ia")
def api_ia_login():
    if not eh_local(): return jsonify({"erro": "Faça o login do Claude no computador da Central."}), 403
    try: tarefas.claude_login()
    except ValueError as e: return jsonify({"erro": str(e)}), 400
    return jsonify({"ok": True})


@app.post("/api/casos/<id_>/ia")
@requer("ia")
def api_ia(id_):
    d = request.get_json(force=True) or {}
    if not C.existe(id_): abort(404)
    agente = (d.get("agente") or "").strip() or None   # vazio = qualquer agente ocioso e aprovado
    if agente and not any(a["nome"] == agente and a["aprovado"] for a in tarefas.plantao.agentes()):
        return jsonify({"erro": f"Agente '{agente}' não existe ou não está aprovado."}), 400
    try: tid = tarefas.enfileirar_ia(id_, d.get("acao"), request.usuario["login"], d.get("observacoes") or "", agente)
    except ValueError as e: return jsonify({"erro": str(e)}), 400
    auditar("ia_acionada", f"{id_}: {d.get('acao')}" + (f" → {agente}" if agente else "")); return jsonify({"tarefa": tid})


# ================================================================== plantão de agentes (D02)
@app.get("/api/plantao/agentes")
@requer("ia")
def api_plantao_agentes():
    ags = tarefas.plantao.agentes()
    campos = ("nome", "tipo", "modo", "estado", "aprovado", "job", "detalhe", "silencio_s", "host", "visto_em")
    return jsonify({"agentes": [{k: a.get(k) for k in campos} for a in ags],
                    "ociosos": sum(1 for a in ags if a["estado"] == "ocioso"),
                    "ocupados": sum(1 for a in ags if a["estado"] == "ocupado"),
                    "pendentes": sum(1 for p in tarefas.plantao.pedidos() if p["estado"] == "pendente")})


@app.post("/api/plantao/agentes/<nome>/aprovacao")
@requer("usuarios")
def api_plantao_aprovacao(nome):
    aprovar = bool((request.get_json(silent=True) or {}).get("aprovar"))
    try: tarefas.plantao.aprovar(nome, aprovar)
    except ValueError as e: return jsonify({"erro": str(e)}), 404
    auditar("agente_aprovado" if aprovar else "agente_revogado", nome); return jsonify({"ok": True})


# ================================================================== tarefas, exportação e importação
@app.get("/api/tarefas")
@requer()
def api_tarefas():
    u = request.usuario
    return jsonify(tarefas.listar(u["login"], todas=auth.pode(u["perfil"], "trabalho")))


@app.post("/api/tarefas/<tid>/cancelar")
@requer()
def api_tarefa_cancelar(tid):
    t = tarefas.obter(tid); u = request.usuario
    if not t: abort(404)
    if t["usuario"] != u["login"] and not auth.pode(u["perfil"], "trabalho"): abort(403)
    ok = tarefas.cancelar(tid); auditar("tarefa_cancelada", t["titulo"]); return jsonify({"ok": ok})


@app.post("/api/exportar")
@requer("dados")
def api_exportar():
    d = request.get_json(force=True) or {}
    modo = "completo" if d.get("modo") == "completo" else "dados"
    tid = tarefas.nova("exportacao", f"Exportação ({modo})", request.usuario["login"])
    tarefas.rodar(tid, tarefas.exportar, modo, bool(d.get("incluir_modelo")))
    auditar("exportacao", modo); return jsonify({"tarefa": tid})


@app.get("/api/exportacoes")
@requer("dados")
def api_exportacoes():
    d = os.path.join(WS, "exportacoes")
    fs = sorted((f for f in os.listdir(d) if f.endswith(".zip")), reverse=True) if os.path.isdir(d) else []
    return jsonify([{"arquivo": f, "mb": round(os.path.getsize(os.path.join(d, f)) / 1048576, 1), "url": f"/exportacoes/{f}"} for f in fs])


@app.get("/exportacoes/<nome>")
@requer("dados")
def api_exportacao_baixar(nome):
    p = os.path.join(WS, "exportacoes", os.path.basename(nome))
    if not os.path.isfile(p): abort(404)
    auditar("exportacao_baixada", nome); return send_file(p, as_attachment=True)


@app.get("/api/planilha")
@requer("estatisticas")
def api_planilha():
    tarefas.indexar(); p = os.path.join(WS, "producao", "base.csv")
    if not os.path.exists(p): return jsonify({"erro": "Ainda não há dados."}), 404
    auditar("planilha_baixada"); return send_file(p, as_attachment=True, download_name=f"CPJ-producao-{C.hoje()}.csv")


def salvar_upload(campo, exts):
    a = request.files.get(campo)
    if not a or not a.filename: raise ValueError("Envie um arquivo.")
    base, ext = nome_seguro(a.filename)
    if ext not in exts: raise ValueError(f"Formato não aceito ({', '.join(exts)}).")
    d = os.path.join(WS, "exportacoes", "_recebidos"); os.makedirs(d, exist_ok=True)
    p = os.path.join(d, f"{time.time_ns()}-{base}{ext}"); a.save(p); return p, a.filename


@app.post("/api/importar")
@requer("dados")
def api_importar():
    try: p, nome = salvar_upload("arquivo", (".zip",))
    except ValueError as e: return jsonify({"erro": str(e)}), 400
    tid = tarefas.nova("importacao", f"Importação de {nome}", request.usuario["login"])
    tarefas.rodar(tid, tarefas.importar, p); auditar("importacao", nome); return jsonify({"tarefa": tid})


# ================================================================== bases de consulta, referências e pesquisa
@app.get("/api/consulta/bases")
@requer("dados")
def api_bases(): return jsonify(Q.listar())


@app.post("/api/consulta/importar")
@requer("dados")
def api_bases_importar():
    try: p, nome = salvar_upload("arquivo", Q.FORMATOS)
    except ValueError as e: return jsonify({"erro": str(e)}), 400
    rotulo = (request.form.get("nome") or os.path.splitext(nome)[0]).strip()
    tid = tarefas.nova("consulta", f"Base de consulta: {rotulo}", request.usuario["login"])
    tarefas.rodar(tid, tarefas.importar_consulta, p, rotulo); auditar("base_consulta_importada", rotulo); return jsonify({"tarefa": tid})


@app.post("/api/consulta/colar")
@requer("dados")
def api_bases_colar():
    d = request.get_json(force=True) or {}
    texto = (d.get("texto") or "").strip()
    if not texto: return jsonify({"erro": "Cole o texto a importar."}), 400
    if len(texto) > 2_000_000: return jsonify({"erro": "Texto grande demais; envie como arquivo."}), 400
    rotulo = (d.get("nome") or "Texto colado").strip()
    dest = os.path.join(WS, "exportacoes", "_recebidos"); os.makedirs(dest, exist_ok=True)
    p = os.path.join(dest, f"{time.time_ns()}-colado.txt"); open(p, "w", encoding="utf-8").write(texto)
    tid = tarefas.nova("consulta", f"Base de consulta (texto colado): {rotulo}", request.usuario["login"])
    tarefas.rodar(tid, tarefas.importar_consulta, p, rotulo); auditar("base_consulta_colada", rotulo); return jsonify({"tarefa": tid})


@app.get("/api/vinculos")
@requer("pesquisa")
def api_vinculos():
    tipo, valor = request.args.get("tipo") or "PESSOA", request.args.get("valor") or ""
    try: niveis = max(1, min(3, int(request.args.get("niveis") or 2)))
    except ValueError: niveis = 2
    try: g = R.vinculos(tipo, valor, niveis)
    except FileNotFoundError: g = {"nos": [], "arestas": []}
    auditar("pesquisa_vinculos", f"{tipo}: {valor[:80]}"); return jsonify(g)


@app.post("/api/consulta/bases/<bid>/remover")
@requer("dados")
def api_bases_remover(bid):
    try: Q.remover(bid)
    except FileNotFoundError: abort(404)
    threading.Thread(target=tarefas.indexar, daemon=True).start(); auditar("base_consulta_removida", bid); return jsonify({"ok": True})


@app.get("/api/referencias")
@requer("dados")
def api_refs(): return jsonify(RF.listar(request.args.get("autor") or None))


@app.post("/api/referencias/importar")
@requer("dados")
def api_refs_importar():
    try: p, nome = salvar_upload("arquivo", (".docx", ".pdf", ".md"))
    except ValueError as e: return jsonify({"erro": str(e)}), 400
    f = request.form
    if not (f.get("autor") or "").strip(): return jsonify({"erro": "Informe o autor."}), 400
    dados = {k: f.get(k) for k in ("autor", "modalidade", "natureza", "peso", "obs")} | {"enviado_por": request.usuario["login"]}
    tid = tarefas.nova("referencia", f"Referência: {nome} ({dados['autor']})", request.usuario["login"])
    tarefas.rodar(tid, tarefas.importar_referencia, p, dados); auditar("referencia_importada", f"{nome} — {dados['autor']}")
    return jsonify({"tarefa": tid})


@app.post("/api/referencias/<rid>")
@requer("dados")
def api_refs_atualizar(rid):
    d = request.get_json(force=True) or {}
    try: m = RF.atualizar(rid, **{k: d.get(k) for k in ("autor", "modalidade", "natureza", "peso", "obs")})
    except FileNotFoundError: abort(404)
    threading.Thread(target=tarefas.indexar, daemon=True).start(); auditar("referencia_atualizada", rid); return jsonify(m)


@app.post("/api/referencias/<rid>/remover")
@requer("dados")
def api_refs_remover(rid):
    try: RF.remover(rid)
    except FileNotFoundError: abort(404)
    threading.Thread(target=tarefas.indexar, daemon=True).start(); auditar("referencia_removida", rid); return jsonify({"ok": True})


@app.get("/api/pesquisa/pessoas")
@requer("pesquisa")
def api_pesquisa_pessoas():
    f = {k: request.args.get(k) for k in ("nome", "mae", "pai", "cpf", "rg", "telefone", "cnpj", "empresa", "endereco", "texto",
                                          "processo", "bo", "placa", "mandado", "cautelar", "mandado_estado", "cautelar_estado")}
    try: ps, oc = R.pesquisa_relacional(f, origem=request.args.get("origem") or None)
    except FileNotFoundError: return jsonify({"pessoas": [], "ocorrencias": [], "aviso": "Base ainda vazia."})
    except ValueError as e: return jsonify({"erro": str(e)}), 400
    auditar("pesquisa_pessoas", json.dumps({k: v for k, v in f.items() if v}, ensure_ascii=False)[:300])
    return jsonify({"pessoas": ps, "ocorrencias": oc, "aviso": None if ps or oc else "Nenhum resultado."})


@app.get("/api/busca")
@requer("pesquisa")
def api_busca():
    q = (request.args.get("q") or "").strip()
    if not q: return jsonify({"trechos": [], "entidades": [], "aviso": None})
    try:
        tipo = request.args.get("tipo") or None
        trechos, aviso = R.buscar(q, caso=request.args.get("caso") or None, tipo=tipo, n=int(request.args.get("n") or 25))
        ents = R.entidade(q) if (len(re.sub(r"\D", "", q)) >= 6 or "@" in q or re.fullmatch(r"[A-Za-z]{3}-?\d[A-Za-z0-9]\d{2}", q)) else []
        auditar("pesquisa_texto", q[:200]); return jsonify({"trechos": trechos, "entidades": ents, "aviso": aviso})
    except FileNotFoundError:
        return jsonify({"trechos": [], "entidades": [], "aviso": "Índice ainda não criado — processe um caso primeiro."})
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400


@app.get("/api/cruzar/<id_>")
@requer("trabalho")
def api_cruzar(id_):
    try: return jsonify(R.cruzar(id_))
    except FileNotFoundError: return jsonify([])


def assinatura_painel():
    """Somente metadados das fontes dos indicadores; não lê PDFs nem recalcula hashes."""
    arquivos = [os.path.join(WS, "producao", "config.json"),
                os.path.join(S_BASE, "indexar.py"), os.path.join(S_BASE, "gerar_painel.py")]
    if os.path.isdir(C.CASOS):
        for nome in sorted(os.listdir(C.CASOS)):
            if nome.startswith("_"): continue
            caso = os.path.join(C.CASOS, nome, "caso.json")
            if not os.path.isfile(caso): continue
            arquivos.append(caso)
            rels = os.path.join(C.CASOS, nome, "03-relatorios")
            if os.path.isdir(rels):
                arquivos.extend(os.path.join(rels, f) for f in sorted(os.listdir(rels))
                                if not f.startswith("~$") and "final" in f.lower()
                                and f.lower().endswith((".md", ".pdf", ".docx")))
    return (WS, datetime.date.today().isoformat(),
            tuple((p, assinatura_arquivo(p)) for p in arquivos))


def atualizar_painel(chave):
    """Reconstrói uma vez por mudança, fora do request, e publica o HTML atomicamente."""
    try:
        env = ambiente_ocr()
        subprocess.run([PY, os.path.join(S_BASE, "indexar.py")], env=env, capture_output=True,
                       check=True, timeout=300, creationflags=SEM_JANELA)
        prod = os.path.join(WS, "producao")
        os.makedirs(prod, exist_ok=True)
        # O gerador lê o snapshot e escreve fora do arquivo que está sendo servido.
        with tempfile.TemporaryDirectory(prefix=".painel-", dir=prod) as stage:
            out = os.path.join(stage, "producao"); os.makedirs(out)
            shutil.copyfile(os.path.join(prod, "base.json"), os.path.join(out, "base.json"))
            cfg = os.path.join(prod, "config.json")
            if os.path.isfile(cfg): shutil.copyfile(cfg, os.path.join(out, "config.json"))
            subprocess.run([PY, os.path.join(S_BASE, "gerar_painel.py")],
                           env=dict(env, CPJ_WORKSPACE=stage), capture_output=True,
                           check=True, timeout=90, creationflags=SEM_JANELA)
            os.replace(os.path.join(out, "painel.html"), os.path.join(prod, "painel.html"))
        with _painel_trava:
            _painel_cache.update(chave=chave, erro=False, retentar_apos=0)
    except Exception:
        app.logger.exception("Falha ao atualizar painel de produção")
        with _painel_trava:
            _painel_cache.update(erro=True, retentar_apos=time.monotonic() + 30)
    finally:
        with _painel_trava: _painel_cache["gerando"] = False


@app.get("/painel")
@requer("estatisticas")
def painel():
    chave = assinatura_painel()
    p = os.path.join(WS, "producao", "painel.html")
    with _painel_trava:
        pronto = _painel_cache["chave"] == chave and os.path.isfile(p)
        if not pronto and not _painel_cache["gerando"] and time.monotonic() >= _painel_cache["retentar_apos"]:
            _painel_cache.update(gerando=True, erro=False)
            threading.Thread(target=atualizar_painel, args=(chave,), daemon=True).start()
        erro = _painel_cache["erro"]
    if pronto:
        r = send_file(p); r.headers["X-CPJ-Painel"] = "pronto"; return r
    if erro:
        return ("<p>Não foi possível atualizar as estatísticas. Tente abrir o painel novamente em alguns instantes.</p>",
                503, {"X-CPJ-Painel": "erro", "Retry-After": "30"})
    return ("<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'>"
            "<meta http-equiv='refresh' content='2'><title>Estatísticas</title></head>"
            "<body><p>Atualizando as estatísticas… O painel aparecerá automaticamente.</p></body></html>",
            200, {"X-CPJ-Painel": "atualizando", "Retry-After": "2"})


@app.get("/api/sistema")
@requer("dados")
def api_sistema():
    return jsonify({"idioma_ocr": idioma_ocr(ambiente_ocr()), "pdf_automatico": bool(soffice()), "workspace": WS})


# ================================================================== HTTPS (certificado autoassinado para a rede local)
def certificado():
    d = os.path.join(WS, "config"); crt, key = os.path.join(d, "central.crt"), os.path.join(d, "central.key")
    if os.path.exists(crt) and os.path.exists(key): return crt, key
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID
    k = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    nome = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Central CPJ")])
    alt = [x509.DNSName("localhost"), x509.DNSName(socket.gethostname())] + \
          [x509.IPAddress(ipaddress.ip_address(i)) for i in ips_locais() + ["127.0.0.1"]]
    cert = (x509.CertificateBuilder().subject_name(nome).issuer_name(nome).public_key(k.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(datetime.datetime.utcnow() - datetime.timedelta(days=1))
            .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=3650))
            .add_extension(x509.SubjectAlternativeName(alt), critical=False).sign(k, hashes.SHA256()))
    open(key, "wb").write(k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL, serialization.NoEncryption()))
    open(crt, "wb").write(cert.public_bytes(serialization.Encoding.PEM))
    return crt, key


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--porta", type=int); ap.add_argument("--host", default="127.0.0.1"); ap.add_argument("--sem-navegador", action="store_true")
    ap.add_argument("--workspace"); ap.add_argument("--somente-local", action="store_true"); a = ap.parse_args()
    os.makedirs(C.CASOS, exist_ok=True)
    threading.Thread(target=trabalhador, daemon=True).start(); retomar_pendentes()
    cfg = rede_cfg(); porta = a.porta or cfg["porta"]
    rede = cfg["compartilhar"] and not a.somente_local
    if rede and auth.ha_senha_temporaria():
        print("AVISO: há usuários com senha temporária — acesso pela rede NÃO foi habilitado até que troquem a senha.")
        rede = False
    host, ssl = ("0.0.0.0", certificado() if cfg["https"] else None) if rede else (a.host, None)
    if ssl: app.config["SESSION_COOKIE_SECURE"] = True
    app.config["REDE_ATIVA"] = rede
    url = f"{'https' if ssl else 'http'}://127.0.0.1:{porta}/"
    print(f"Central CPJ em {url}  (workspace: {WS})")
    if rede:
        print("ACESSO PELA REDE LOCAL HABILITADO:", ", ".join(f"{'https' if ssl else 'http'}://{i}:{porta}" for i in ips_locais()))
    print("Feche esta janela para encerrar.")
    if not a.sem_navegador: threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    app.run(host=host, port=porta, threaded=True, debug=False, ssl_context=ssl)
