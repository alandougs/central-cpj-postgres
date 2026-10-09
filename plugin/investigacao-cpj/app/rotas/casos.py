#!/usr/bin/env python3
"""Rotas de O.S., casos, pendências, arquivos do caso e fila de processamento."""
import csv
import datetime
import html
import json
import os
import re
import tempfile
import time
import zipfile
from flask import Blueprint, abort, jsonify, request, send_file, url_for
from werkzeug.exceptions import HTTPException
from rotas.comum import (
    C,
    D_OS,
    EDITAVEIS,
    EDITAVEIS_GESTAO,
    EXT_OK,
    TEXTO_BUSCA,
    WS,
    ambiente_ocr,
    arquivos_relatorio,
    arvore,
    auditar,
    auth,
    eh_local,
    enfileirar,
    idioma_ocr,
    ler_proc,
    nome_seguro,
    pode_alterar_os,
    requer,
    resumo,
    sha256,
    tarefas,
    visiveis,
)

bp_casos = Blueprint("casos", __name__)


@bp_casos.get("/api/pendencias")
@requer("casos")
def api_pendencias():
    u = request.usuario
    cs = [resumo(c) for c in visiveis(u)]
    abertos = [c for c in cs if c["status"] not in ("entregue", "arquivado")]
    grupo = lambda s: sorted([c for c in abertos if c["situacao_prazo"] == s], key=lambda c: c["prazo"] or "")
    hoje = C.hoje()
    mes = hoje[:7]
    return jsonify({
        "novas": (
            [c for c in abertos if not c["visto"] and (c.get("responsavel") or "") in ("", u["login"])]
            if auth.pode(u["perfil"], "trabalho")
            else []
        ),
        "meus": [c for c in abertos if c.get("responsavel") == u["login"]],
        "vencidos": grupo("vencido"),
        "hoje": grupo("hoje"),
        "proximos": grupo("proximo"),
        "sem_prazo": [c for c in abertos if not c["prazo"]],
        "em_andamento": {s: sum(1 for c in abertos if c["status"] == s) for s in C.STATUS[:5] + ["devolvido"]},
        "minhas": [c for c in cs if c["criado_por"] == u["login"]][:30],
        "entregues_hoje": sum(1 for c in cs if c["entregue"] == hoje),
        "entregues_mes": sum(1 for c in cs if (c["entregue"] or "").startswith(mes)),
        "processando": [c for c in cs if c["processando"]],
    })


@bp_casos.get("/api/casos")
@requer("casos")
def api_casos():
    q = (request.args.get("q") or "").strip().lower()
    st = request.args.get("status") or ""
    pz = request.args.get("prazo") or ""
    meus = request.args.get("meus") == "1"
    out = []
    for c in visiveis(request.usuario):
        r = resumo(c)
        if st and c.get("status") != st:
            continue
        if pz and r["situacao_prazo"] != pz:
            continue
        if meus and c.get("responsavel") != request.usuario["login"] and c.get("criado_por") != request.usuario["login"]:
            continue
        if q:
            alvo = (
                " ".join(str(c.get(k) or "") for k in TEXTO_BUSCA)
                + " "
                + " ".join(c.get("vitimas") or [])
                + " "
                + " ".join(c.get("investigados") or [])
            )
            q_dig = re.sub(r"\D", "", q)
            if q not in alvo.lower() and not (len(q_dig) >= 3 and q_dig in re.sub(r"\D", "", alvo)):
                continue
        out.append(r)
    out.sort(
        key=lambda r: (
            {"vencido": 0, "hoje": 1, "proximo": 2}.get(r["situacao_prazo"], 3),
            r.get("prazo") or "9",
            r["id"],
        )
    )
    return jsonify(out)


@bp_casos.get("/api/casos/<id_>")
@requer("casos")
def api_caso(id_):
    try:
        c = C.carregar(id_)
    except (FileNotFoundError, ValueError):
        abort(404)
    u = request.usuario
    trabalho = auth.pode(u["perfil"], "trabalho")
    if trabalho and not c.get("visto"):
        with C.transacao(id_) as c_tr:
            c_tr["visto"] = True
        c = C.carregar(id_)
    rels = arquivos_relatorio(id_)
    out = {
        "caso": (
            c
            if trabalho
            else {
                k: c.get(k)
                for k in (
                    "id", "ordem_servico", "bo", "inquerito", "processo", "natureza", "status", "prazo",
                    "requisitante", "escrivao", "prioridade", "determinacao", "criado_por", "datas",
                    "observacoes", "documentos", "preenchimento_os"
                )
            }
        ),
        "resumo": resumo(c),
        "processamento": ler_proc(id_),
        "relatorios": rels if trabalho else [r for r in rels if r["tipo"] == "final"],
        "trabalho": trabalho,
    }
    if trabalho:
        out["arquivos"] = arvore(C.caminho(id_))
        out["ia"] = [t for t in tarefas.listar(todas=True) if t["caso"] == id_][:5]
    else:
        out["arquivos"] = [a for a in arvore(C.caminho(id_)) if a["caminho"].startswith("00-originais/")]
    return jsonify(out)


@bp_casos.post("/api/casos/<id_>")
@requer("casos")
def api_caso_salvar(id_):
    u = request.usuario
    d = request.get_json(force=True) or {}
    permitidos = EDITAVEIS if auth.pode(u["perfil"], "trabalho") else EDITAVEIS_GESTAO
    try:
        c = C.carregar(id_)
        if not pode_alterar_os(u, c):
            return jsonify({"erro": "Só quem cadastrou a O.S. (ou o delegado) pode alterá-la."}), 403
        revisao_esperada = d.pop("revisao", None) or d.pop("revisao_esperada", None)
        if revisao_esperada is not None:
            try:
                revisao_esperada = int(revisao_esperada)
            except ValueError:
                revisao_esperada = None
        novo_status = d.pop("status", None) if auth.pode(u["perfil"], "trabalho") else None
        pares = {k: v for k, v in d.items() if k in permitidos}
        if pares:
            C.set_campos(id_, pares, revisao_esperada=revisao_esperada)
            c_manual = C.carregar(id_)
            if "preenchimento_os" in c_manual:
                registro = c_manual["preenchimento_os"]
                for k in pares:
                    registro.get("fontes", {}).pop(k, None)
                    registro.get("conflitos", {}).pop(k, None)
                registro["pendentes"] = [k for k in D_OS.CAMPOS if not c_manual.get(k)]
                C.salvar(c_manual)
        if novo_status and novo_status != c.get("status"):
            C.status(id_, novo_status, origem="central")
        auditar("caso_editado", f"{id_}: {', '.join(pares) or ''}{' status→' + novo_status if novo_status else ''}")
        return jsonify(resumo(C.carregar(id_)))
    except C.ConcorrenciaErro as e:
        return jsonify({"conflito": True, "erro": "conflito_concorrencia", "mensagem": str(e)}), 409
    except (FileNotFoundError, ValueError) as e:
        return jsonify({"erro": str(e)}), 400


@bp_casos.post("/api/os/detectar")
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
            try:
                valores, ambiguos = D_OS.extrair(D_OS.ler_original(p), arquivo.filename)
            except Exception:
                continue  # PDF protegido/sem texto seguirá para OCR no caso
        for k, item in valores.items():
            if k in conflitos:
                conflitos[k].append(item)
            elif k in encontrados and encontrados[k]["valor"] != item["valor"]:
                conflitos[k] = [encontrados.pop(k), item]
            else:
                encontrados[k] = item
        for k, itens in ambiguos.items():
            conflitos.setdefault(k, []).extend(itens)
            if k in encontrados:
                conflitos[k].append(encontrados.pop(k))
    return jsonify({
        "campos": encontrados,
        "conflitos": conflitos,
        "pendentes": [k for k in D_OS.CAMPOS if k not in encontrados],
    })


@bp_casos.get("/api/os/ia-local")
@requer("usuarios")
def api_os_ia_local():
    return jsonify({"modelo": D_OS.modelo_local(), "ambiente": "CPJ_IA_LOCAL_MODELO" in os.environ})


@bp_casos.post("/api/os/ia-local")
@requer("usuarios")
def api_os_ia_local_salvar():
    modelo = (request.get_json(force=True) or {}).get("modelo", "")
    if not isinstance(modelo, str) or len(modelo) > 160 or not re.fullmatch(r"[\w./:@-]*", modelo, re.A):
        return jsonify({"erro": "Informe o nome do modelo local instalado no Ollama."}), 400
    if "CPJ_IA_LOCAL_MODELO" in os.environ:
        return jsonify({"erro": "Modelo definido pelo ambiente. Altere CPJ_IA_LOCAL_MODELO e reinicie a Central."}), 409
    config = os.path.join(WS, "config")
    os.makedirs(config, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".ia-local-", dir=config)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"modelo": modelo}, f)
        os.replace(tmp, os.path.join(config, "ia-local-os.json"))
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    auditar("ia_local_os_configurada", modelo or "desativada")
    return jsonify({"modelo": modelo})


@bp_casos.post("/api/os")
@requer("os")
def api_os():
    """Cadastro de O.S. + upload dos arquivos (PDF do IP, MD ou CSV)."""
    f, u = request.form, request.usuario
    os_num = (f.get("os") or "").strip()
    id_informado = (f.get("caso_id") or "").strip()
    somente_cadastro = f.get("somente_cadastro") == "1"
    arquivos = [a for a in request.files.getlist("arquivos") if a and a.filename]
    if somente_cadastro:
        arquivos = []
    tem_campos = any(
        (f.get(k) or "").strip()
        for k in ("bo", "inquerito", "processo", "escrivao", "natureza", "determinacao")
    )
    if (
        not os_num
        and not id_informado
        and not (somente_cadastro and tem_campos)
        and not any(os.path.splitext(a.filename)[1].lower() in EXT_OK for a in arquivos)
    ):
        return jsonify({"erro": "Informe a O.S. ou envie o IP/processo para preenchimento automático."}), 400
    if id_informado:
        try:
            if not C.existe(id_informado):
                return jsonify({"erro": "Cadastro não encontrado. Inicie um novo cadastro."}), 400
        except ValueError:
            return jsonify({"erro": "Identificador de cadastro inválido."}), 400
    id_ = id_informado or (C.id_de_os(os_num) if os_num else "RECEBIDO-" + os.urandom(12).hex())
    criado = False
    extras = {
        "prazo": f.get("prazo") or None,
        "requisitante": (f.get("requisitante") or "").strip(),
        "escrivao": (f.get("escrivao") or "").strip(),
        "prioridade": f.get("prioridade") or "normal",
        "determinacao": (f.get("determinacao") or "").strip()[:4000],
        "criado_por": u["login"],
        "visto": u["perfil"] in ("investigador",),
        "responsavel": u["login"] if auth.pode(u["perfil"], "trabalho") and u["perfil"] != "admin" else "",
    }
    if not C.existe(id_):
        C.novo(
            os_num,
            f.get("bo", "").strip(),
            f.get("inquerito", "").strip(),
            f.get("processo", "").strip(),
            f.get("natureza", "").strip(),
            f.get("recebido") or None,
            id_=id_,
            extras=extras,
        )
        criado = True
    else:
        if not pode_alterar_os(u, C.carregar(id_)):
            return jsonify({"erro": "Só quem cadastrou a O.S. (ou o delegado) pode alterá-la."}), 403
        upd = {k: (f.get(k) or "").strip() for k in ("bo", "inquerito", "processo") if (f.get(k) or "").strip()}
        upd |= {k: v for k, v in extras.items() if k in ("prazo", "requisitante", "escrivao", "determinacao") and v}
        if somente_cadastro:
            upd = {
                k: (f.get(k) or "").strip()
                for k in ("bo", "inquerito", "processo", "requisitante", "escrivao", "determinacao", "prazo", "prioridade")
                if k in f
            }
            if "os" in f:
                upd["ordem_servico"] = os_num
            if "natureza" in f and auth.pode(u["perfil"], "trabalho"):
                upd["natureza"] = f.get("natureza", "").strip()
        if upd:
            C.set_campos(id_, upd)
        c_atual = C.carregar(id_)
        if "preenchimento_os" in c_atual:
            registro = c_atual["preenchimento_os"]
            for k in upd:
                registro.get("fontes", {}).pop(k, None)
                registro.get("conflitos", {}).pop(k, None)
            registro["pendentes"] = [k for k in D_OS.CAMPOS if not c_atual.get(k)]
            c_atual["referencia"] = " / ".join(
                f"{rotulo} {c_atual[k]}"
                for k, rotulo in (("bo", "BO"), ("inquerito", "IP"), ("processo", "Processo"))
                if c_atual.get(k)
            )
            C.salvar(c_atual)
        if u["perfil"] != "investigador":
            C.set_campos(id_, {"visto": "false"})
    orig_dir = os.path.join(C.caminho(id_), "00-originais")
    os.makedirs(orig_dir, exist_ok=True)
    recebidos, ignorados = [], []
    for a in arquivos:
        base, ext = nome_seguro(a.filename)
        if ext not in EXT_OK:
            ignorados.append(f"{a.filename} (tipo não aceito)")
            continue
        tmp = os.path.join(orig_dir, f".upload-{time.time_ns()}{ext}")
        a.save(tmp)
        h = sha256(tmp)
        rep = next(
            (x for x in os.listdir(orig_dir) if not x.startswith(".") and sha256(os.path.join(orig_dir, x)) == h),
            None,
        )
        if rep:
            os.remove(tmp)
            ignorados.append(f"{a.filename} (idêntico a {rep})")
            continue
        nome, k = f"{base}{ext}", 2
        while os.path.exists(os.path.join(orig_dir, nome)):
            nome, k = f"{base}_{k}{ext}", k + 1
        os.replace(tmp, os.path.join(orig_dir, nome))
        try:
            os.chmod(os.path.join(orig_dir, nome), 0o444)
        except Exception:
            pass
        enfileirar(id_, os.path.splitext(nome)[0], nome)
        recebidos.append(nome)
    auditar("os_cadastrada" if criado else "os_atualizada", f"{id_}: {len(recebidos)} arquivo(s)")
    return jsonify({"caso": id_, "criado": criado, "recebidos": recebidos, "ignorados": ignorados})


@bp_casos.post("/api/casos/<id_>/reprocessar/<doc>")
@requer("trabalho")
def api_reprocessar(id_, doc):
    t = next((t for t in ler_proc(id_).get("trabalhos", []) if t["doc"] == doc), None)
    if not t:
        abort(404)
    enfileirar(id_, doc, t["arquivo"])
    auditar("reprocessar", f"{id_}/{doc}")
    return jsonify({"ok": True})


@bp_casos.post("/api/casos/<id_>/baixa")
@requer("trabalho")
def api_baixa(id_):
    d = request.get_json(silent=True) or {}
    try:
        with C.trava(id_):
            if d.get("desfazer"):
                C.status(id_, "minuta")
                auditar("baixa_desfeita", id_)
            else:
                fs = C.finais(id_)
                c = C.status(id_, "entregue", data=d.get("data") or None, origem="central", arquivo=fs[-1] if fs else None)
                if fs and not any(r.get("arquivo") == fs[-1] for r in c.get("relatorios", [])):
                    C.registrar_relatorio(id_, fs[-1], data=c["datas"]["entregue"])
                auditar("baixa", id_)
            return jsonify(resumo(C.carregar(id_)))
    except (FileNotFoundError, ValueError) as e:
        return jsonify({"erro": str(e)}), 400


@bp_casos.post("/api/casos/<id_>/abrir")
@requer("trabalho")
def api_abrir(id_):
    if not eh_local():
        return jsonify({"erro": "Disponível apenas no computador da Central."}), 403
    sub = (request.get_json(silent=True) or {}).get("sub", "")
    alvo = _caminho_do_caso(id_, sub)
    if not os.path.exists(alvo):
        abort(404)
    if hasattr(os, "startfile"):
        os.startfile(alvo)
    return jsonify({"ok": True})


def _caminho_do_caso(id_, rel):
    try:
        if not isinstance(rel, str) or "\x00" in rel or os.path.isabs(rel) or os.path.splitdrive(rel)[0]:
            abort(404)
        base = os.path.realpath(C.caminho(id_))
        casos = os.path.realpath(C.CASOS)
        if base == casos or os.path.normcase(os.path.commonpath((casos, base))) != os.path.normcase(casos):
            abort(404)
        alvo = os.path.realpath(os.path.join(base, rel))
        if os.path.normcase(os.path.commonpath((base, alvo))) != os.path.normcase(base):
            abort(404)
    except (OSError, ValueError):
        abort(404)
    return alvo


def _autorizar_arquivo(rel):
    u = request.usuario
    if not auth.pode(u["perfil"], "trabalho"):
        r = rel.replace("\\", "/")
        final = r.startswith("03-relatorios/") and "final" in r.lower()
        if not (final or r.startswith("00-originais/")):
            abort(403)


@bp_casos.get("/arquivo/<id_>/<path:rel>")
@requer("casos")
def api_arquivo(id_, rel):
    alvo = _caminho_do_caso(id_, rel)
    if not os.path.isfile(alvo):
        abort(404)
    _autorizar_arquivo(os.path.relpath(alvo, os.path.realpath(C.caminho(id_))))
    auditar("download", f"{id_}/{rel}")
    ext = os.path.splitext(alvo)[1].lower()
    if ext in (".md", ".csv", ".json", ".log", ".txt", ".jsonl"):
        return send_file(alvo, mimetype="text/plain; charset=utf-8")
    return send_file(alvo, as_attachment=ext in (".docx", ".xlsx"))


PREVIA_DOCX_BYTES = 20 * 1024 * 1024
PREVIA_DOCX_EXPANDIDO = 64 * 1024 * 1024
PREVIA_DOCX_XML = 4 * 1024 * 1024
PREVIA_DOCX_HTML = 1024 * 1024


def _previa_docx(alvo):
    from docx import Document
    from docx.oxml.ns import qn
    from docx.table import Table, _Cell
    from docx.text.paragraph import Paragraph
    from docx.text.run import Run

    if os.path.getsize(alvo) > PREVIA_DOCX_BYTES:
        abort(413, description="DOCX acima de 20 MB. Abra o arquivo original.")
    try:
        with zipfile.ZipFile(alvo) as pacote:
            partes = pacote.infolist()
            if (len(partes) > 2048 or sum(p.file_size for p in partes) > PREVIA_DOCX_EXPANDIDO
                    or any(p.file_size > 1024 * 1024 and p.file_size > 200 * max(p.compress_size, 1) for p in partes)
                    or pacote.getinfo("word/document.xml").file_size > PREVIA_DOCX_XML):
                abort(413, description="DOCX extenso demais para a prévia. Abra o arquivo original.")
        doc = Document(alvo)
    except HTTPException:
        raise
    except Exception:
        abort(422, description="Não foi possível ler este DOCX. Abra o arquivo original.")
    if len(doc.element.xpath(".//w:p|.//w:tc")) > 10000:
        abort(413, description="DOCX extenso demais para a prévia. Abra o arquivo original.")

    fragmentos = []
    tamanho = 0

    def adicionar(fragmento):
        nonlocal tamanho
        tamanho += len(fragmento)
        if tamanho > PREVIA_DOCX_HTML:
            abort(413, description="Texto extenso demais para a prévia. Abra o arquivo original.")
        fragmentos.append(fragmento)

    def blocos(elemento, pai, nivel=0):
        if nivel > 10:
            abort(413, description="Tabela complexa demais para a prévia. Abra o arquivo original.")
        for bloco in elemento.iterchildren():
            if bloco.tag == qn("w:p"):
                paragrafo = Paragraph(bloco, pai)
                adicionar("<p>")
                for item in paragrafo._p.xpath("./w:r|./w:hyperlink/w:r"):
                    trecho = Run(item, paragrafo)
                    texto = html.escape(trecho.text).replace("\n", "<br>")
                    if trecho.bold:
                        texto = "<strong>" + texto + "</strong>"
                    if trecho.italic:
                        texto = "<em>" + texto + "</em>"
                    adicionar(texto)
                adicionar("</p>")
            elif bloco.tag == qn("w:tbl"):
                tabela = Table(bloco, pai)
                adicionar("<table><tbody>")
                for linha in tabela._tbl.tr_lst:
                    adicionar("<tr>")
                    for celula in linha.tc_lst:
                        adicionar("<td>")
                        blocos(celula, _Cell(celula, tabela), nivel + 1)
                        adicionar("</td>")
                    adicionar("</tr>")
                adicionar("</tbody></table>")

    blocos(doc.element.body, doc)
    return "".join(fragmentos)


@bp_casos.get("/visualizar/<id_>/<path:rel>")
@requer("casos")
def api_visualizar(id_, rel):
    alvo = _caminho_do_caso(id_, rel)
    relativo = os.path.relpath(alvo, os.path.realpath(C.caminho(id_))).replace("\\", "/")
    if not relativo.startswith("03-relatorios/") or os.path.splitext(alvo)[1].lower() != ".docx" or not os.path.isfile(alvo):
        abort(404)
    _autorizar_arquivo(relativo)
    conteudo = _previa_docx(alvo)
    nome = html.escape(os.path.basename(alvo))
    original = html.escape(url_for("casos.api_arquivo", id_=id_, rel=relativo), quote=True)
    auditar("previa_relatorio", f"{id_}/{relativo}")
    pagina = ("<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'>"
              "<meta name='viewport' content='width=device-width,initial-scale=1'>"
              f"<title>{nome}</title><style>"
              "body{font:16px/1.6 system-ui,sans-serif;color:#202b3d;background:#f5f7fb;margin:0;padding:24px}"
              "header,main{max-width:900px;margin:auto}h1{font-size:18px;overflow-wrap:anywhere}"
              "header p{font-size:14px}main{background:white;padding:24px;box-sizing:border-box}"
              "main p{white-space:pre-wrap;overflow-wrap:anywhere;min-height:1em}"
              "table{border-collapse:collapse;width:100%;margin:16px 0;table-layout:fixed}"
              "td{border:1px solid #ccd3df;padding:8px;vertical-align:top;overflow-wrap:anywhere}"
              "a{color:#145cb7}</style></head><body>"
              f"<header><h1>{nome}</h1><p>Prévia de texto e tabelas. "
              "A formatação completa está no arquivo original.</p>"
              f"<p><a href='{original}'>Baixar arquivo original</a></p></header><main>{conteudo}</main></body></html>")
    return pagina, 200, {"Content-Type": "text/html; charset=utf-8",
                         "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'self'; base-uri 'none'"}


@bp_casos.get("/api/fila")
@requer("casos")
def api_fila():
    ts = []
    limite = (datetime.datetime.now() - datetime.timedelta(hours=12)).isoformat()
    for c in C.listar():
        for t in ler_proc(c["id"]).get("trabalhos", []):
            if t.get("status") in ("na_fila", "processando", "erro") or (t.get("fim") or "") >= limite:
                ts.append(t | {"caso": c["id"]})
    ordem = {"processando": 0, "na_fila": 1, "erro": 2, "concluido": 3}
    ts.sort(key=lambda t: (ordem.get(t.get("status"), 9), t.get("enfileirado") or ""))
    return jsonify({"trabalhos": ts, "idioma_ocr": idioma_ocr(ambiente_ocr())})


@bp_casos.get("/api/casos/<id_>/fluxograma")
@requer("casos")
def api_fluxograma(id_):
    pasta = C.caminho(id_)
    try:
        caso_json = C.carregar(id_)
    except FileNotFoundError:
        abort(404)
        
    fluxo_csv = os.path.join(pasta, "02-analise", "fluxo-financeiro.csv")
    transacoes = []
    
    def parse_val(v_str):
        v = re.sub(r"[^\d,.]", "", str(v_str or "").strip())
        if not v: return 0.0
        if "." in v and "," in v: v = v.replace(".", "").replace(",", ".")
        elif "," in v: v = v.replace(",", ".")
        try: return float(v)
        except: return 0.0

    if os.path.isfile(fluxo_csv):
        with open(fluxo_csv, "r", encoding="utf-8-sig", errors="replace") as f:
            first_line = f.readline()
            sep = ";" if ";" in first_line else ","
            f.seek(0)
            reader = csv.DictReader(f, delimiter=sep)
            for r in reader:
                row = {}
                for k, v in r.items():
                    if k is None:
                        continue
                    key = str(k).strip().lower()
                    if isinstance(v, list):
                        val = " ".join(str(x).strip() for x in v if x is not None)
                    elif v is not None:
                        val = str(v).strip()
                    else:
                        val = ""
                    row[key] = val

                val_raw = ""
                for vk in ("valor", "valor_brl", "valor (r$)"):
                    if vk in row and row[vk]:
                        val_raw = row[vk]
                        break
                val_float = parse_val(val_raw)
                
                camada = 1
                for ck in row:
                    if "camada" in ck and row[ck]:
                        m = re.search(r"\d+", row[ck])
                        if m:
                            camada = int(m.group(0))
                        elif "paralelo" in row[ck].lower():
                            camada = 99
                        break
                
                orig_tit = row.get("origem_titular") or row.get("origem") or (caso_json.get("vitimas") or ["Vítima"])[0]
                dest_tit = row.get("destino_titular") or row.get("destino") or (caso_json.get("investigados") or ["Investigado"])[0]
                
                transacoes.append({
                    "seq": row.get("seq") or str(len(transacoes) + 1),
                    "data": row.get("data") or "",
                    "hora": row.get("hora") or "",
                    "valor": val_float,
                    "valor_fmt": f"R$ {val_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                    "meio": row.get("meio") or "Pix",
                    "origem_titular": orig_tit,
                    "origem_banco": row.get("origem_banco") or "",
                    "origem_chave": row.get("origem_chave") or "",
                    "destino_titular": dest_tit,
                    "destino_banco": row.get("destino_banco") or "",
                    "destino_chave": row.get("destino_chave") or "",
                    "camada": camada,
                    "fls": row.get("fls") or "",
                    "obs": row.get("observacao") or row.get("observacoes") or row.get("status_conferencia") or ""
                })
    
    # Fallback estruturado se ainda não houver fluxo-financeiro.csv
    if not transacoes:
        vits = caso_json.get("vitimas") or ["Vítima dos autos"]
        invs = caso_json.get("investigados") or ["Investigado(a) identificado(a)"]
        fin = caso_json.get("financeiro") or {}
        val_str = str(fin.get("valor_rastreado") or "0")
        val_float = parse_val(val_str)
        for i, inv in enumerate(invs):
            part_val = val_float / max(1, len(invs))
            transacoes.append({
                "seq": str(i + 1),
                "data": (caso_json.get("datas") or {}).get("recebido") or "",
                "hora": "",
                "valor": part_val,
                "valor_fmt": f"R$ {part_val:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                "meio": "Pix",
                "origem_titular": vits[0] if vits else "Vítima",
                "origem_banco": "",
                "origem_chave": "",
                "destino_titular": inv,
                "destino_banco": "",
                "destino_chave": "",
                "camada": 1,
                "fls": "",
                "obs": "Valor obtido na fraude registrado nos autos"
            })
            
    # Agrupar por camada
    camadas_dict = {}
    for t in transacoes:
        c_num = t["camada"]
        if c_num not in camadas_dict:
            camadas_dict[c_num] = []
        camadas_dict[c_num].append(t)
        
    camadas_lista = []
    nomes_camadas = {
        1: "1ª Camada — Saída da Vítima / Contas de Passagem",
        2: "2ª Camada — Pulverização / Repasses Subsequentes",
        3: "3ª Camada — Destinatários Finais / Saques em Espécie",
        4: "4ª Camada — Escoamento Adicional",
        99: "Movimentações Paralelas / Análise"
    }
    for c_num in sorted(camadas_dict.keys()):
        camadas_lista.append({
            "camada": c_num,
            "titulo": nomes_camadas.get(c_num, f"{c_num}ª Camada"),
            "transacoes": camadas_dict[c_num],
            "subtotal": sum(t["valor"] for t in camadas_dict[c_num])
        })
        
    tot_fraude = sum(t["valor"] for t in transacoes if t["camada"] == 1) or sum(t["valor"] for t in transacoes)
    
    return jsonify({
        "caso": id_,
        "ordem_servico": caso_json.get("ordem_servico") or id_,
        "bo": caso_json.get("bo") or "",
        "inquerito": caso_json.get("inquerito") or "",
        "vitimas": caso_json.get("vitimas") or [],
        "investigados": caso_json.get("investigados") or [],
        "total_fraude": tot_fraude,
        "total_fraude_fmt": f"R$ {tot_fraude:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        "total_transacoes": len(transacoes),
        "camadas": camadas_lista
    })


@bp_casos.get("/api/casos/<id_>/fluxo-csv")
@requer("casos")
def api_fluxo_csv(id_):
    pasta = C.caminho(id_)
    fluxo_csv = os.path.join(pasta, "02-analise", "fluxo-financeiro.csv")
    if os.path.isfile(fluxo_csv):
        return send_file(fluxo_csv, as_attachment=True, download_name=f"rastreio-financeiro-{id_}.csv")
    abort(404)


@bp_casos.post("/api/casos/<id_>/esteira")
@requer("ia")
def api_caso_esteira(id_):
    """Executa a Esteira Completa 1-Clique: OCR -> RAG -> analistas -> redação -> revisor gauntlet -> DOCX."""
    if not C.existe(id_):
        abort(404)
    d = request.get_json(silent=True) or {}
    agente = (d.get("agente") or "").strip() or None
    obs = d.get("observacoes") or ""

    # Se houver documentos originais que ainda não foram extraídos, enfileira a extração determinística
    orig_dir = os.path.join(C.caminho(id_), "00-originais")
    proc_info = ler_proc(id_)
    if os.path.isdir(orig_dir):
        for arq in sorted(os.listdir(orig_dir)):
            if arq.lower().endswith((".pdf", ".md", ".csv")):
                doc_nome = os.path.splitext(arq)[0]
                ja_processado = any(
                    t.get("doc") == doc_nome and t.get("status") == "concluido"
                    for t in proc_info.get("trabalhos", [])
                )
                if not ja_processado:
                    enfileirar(id_, doc_nome, arq)

    try:
        tid = tarefas.enfileirar_ia(id_, "esteira", request.usuario["login"], obs, agente)
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400

    auditar("esteira_completa_acionada", f"{id_}: 1-clique" + (f" → {agente}" if agente else ""))
    return jsonify({
        "ok": True,
        "caso": id_,
        "tarefa": tid,
        "etapas": ["extração/ocr", "análise documental", "caminho do dinheiro", "minuta docx", "revisão independente"],
        "mensagem": "Esteira Completa 1-Clique iniciada com sucesso."
    })


def _calibrador():
    import sys
    s_rel = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                         "skills", "relatorio-ip-fraude", "scripts")
    if s_rel not in sys.path:
        sys.path.insert(0, s_rel)
    import calibrar_versoes
    return calibrar_versoes


@bp_casos.post("/api/casos/<id_>/calibrar")
@requer("trabalho")
def api_calibrar(id_):
    """K01: compara a última minuta com o FINAL enviado (PDF/DOCX/MD) e devolve proposta genérica.
    Não grava nada em calibracao/ (regra 7): a gravação só ocorre em /calibrar/aprovar, por id de lição."""
    if not C.existe(id_):
        abort(404)
    pasta_rel = os.path.join(C.caminho(id_), "03-relatorios")
    minutas = sorted((f for f in os.listdir(pasta_rel) if re.match(r"minuta-v\d+\.md$", f)),
                     key=lambda f: int(re.findall(r"\d+", f)[0])) if os.path.isdir(pasta_rel) else []
    if not minutas:
        return jsonify({"erro": "Este caso não tem minuta (minuta-vNN.md) para comparar."}), 400
    arq = request.files.get("final")
    if not arq or not arq.filename:
        return jsonify({"erro": "Envie o FINAL (PDF, DOCX ou MD) no campo 'final'."}), 400
    dados = arq.read(20 * 1024 * 1024 + 1)
    if len(dados) > 20 * 1024 * 1024:
        return jsonify({"erro": "Arquivo acima de 20 MB."}), 413
    cal = _calibrador()
    try:
        final = cal.ler_texto(arq.filename, dados)
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    except Exception:
        return jsonify({"erro": "Não foi possível ler o arquivo enviado."}), 400
    if len(final.split()) < 30:
        return jsonify({"erro": "O FINAL tem pouco texto legível (PDF escaneado?). Envie DOCX ou MD."}), 400
    with open(os.path.join(pasta_rel, minutas[-1]), encoding="utf-8", errors="replace") as f:
        minuta = f.read()
    res = cal.comparar(minuta, final)
    auditar("calibracao_proposta", f"{id_}: {len(res['licoes'])} sugestões")
    return jsonify({"ok": True, "proposta": True, "gravado": False, "minuta": minutas[-1],
                    "metricas": res["metricas"], "licoes": res["licoes"],
                    "mensagem": f"{len(res['licoes'])} lição(ões) genérica(s) proposta(s). Nada foi gravado em calibracao/; "
                                "aprove as que quiser."})


@bp_casos.post("/api/casos/<id_>/calibrar/aprovar")
@requer("trabalho")
def api_calibrar_aprovar(id_):
    """K01: grava em calibracao/ só as lições do catálogo aprovadas por id (sem ID de caso, sem dados)."""
    if not C.existe(id_):
        abort(404)
    ids = (request.get_json(silent=True) or {}).get("ids")
    if not isinstance(ids, list) or not ids:
        return jsonify({"erro": "Informe os ids das lições aprovadas."}), 400
    try:
        novas, existentes = _calibrador().registrar(WS, [str(i) for i in ids])
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    auditar("calibracao_aprovada", f"{len(novas)} lição(ões) gravada(s)")
    return jsonify({"ok": True, "gravadas": novas, "ja_existentes": existentes})


@bp_casos.get("/api/pendencias-ocr")
@requer("trabalho")
def api_pendencias_ocr():
    u = request.usuario
    pendentes = []
    for c in visiveis(u):
        orig_dir = os.path.join(C.caminho(c["id"]), "00-originais")
        if not os.path.isdir(orig_dir):
            continue
        
        proc_info = ler_proc(c["id"])
        trabalhos = proc_info.get("trabalhos", [])
        
        for arq in sorted(os.listdir(orig_dir)):
            if not arq.lower().endswith((".pdf", ".md", ".csv")):
                continue
                
            doc_nome = os.path.splitext(arq)[0]
            
            ext_dir = os.path.join(C.caminho(c["id"]), "01-extracao", doc_nome)
            tem_md = os.path.isfile(os.path.join(ext_dir, "transcricao.md"))
            tem_csv = arq.lower().endswith(".csv") and os.path.isfile(os.path.join(ext_dir, "tabelas", arq))
            
            if tem_md or tem_csv:
                continue
                
            trab_atual = next((t for t in trabalhos if t.get("doc") == doc_nome and t.get("arquivo") == arq), None)
            if trab_atual and trab_atual.get("status") in ("na_fila", "processando"):
                continue
                
            pendentes.append({
                "caso": c["id"],
                "os": c.get("ordem_servico") or c["id"],
                "arquivo": arq,
                "doc": doc_nome,
                "caminho_relativo": f"00-originais/{arq}",
                "status": trab_atual.get("status") if trab_atual else None,
                "erro": trab_atual.get("erro") if trab_atual else None
            })
            
    return jsonify({"pendentes": pendentes})


@bp_casos.post("/api/pendencias-ocr/processar")
@requer("trabalho")
def api_pendencias_ocr_processar():
    itens = request.get_json(silent=True) or []
    if not isinstance(itens, list):
        return jsonify({"erro": "Espera lista de itens"}), 400
        
    u = request.usuario
    vis = {c["id"]: c for c in visiveis(u)}
    
    resultados = []
    
    for item in itens:
        id_ = item.get("caso")
        arq = item.get("arquivo")
        doc = item.get("doc")
        
        if not id_ or not arq or not doc:
            resultados.append({"caso": id_, "arquivo": arq, "status": "erro", "motivo": "Dados incompletos"})
            continue
            
        if id_ not in vis:
            resultados.append({"caso": id_, "arquivo": arq, "status": "erro", "motivo": "Caso não visível ou não autorizado"})
            continue
            
        orig_dir = os.path.join(C.caminho(id_), "00-originais")
        base, ext = nome_seguro(arq)
        nome_validado = base + ext
        
        if arq != nome_validado:
            resultados.append({"caso": id_, "arquivo": arq, "status": "erro", "motivo": "Nome de arquivo inválido"})
            continue
            
        alvo = os.path.join(orig_dir, arq)
        if not os.path.isfile(alvo):
            resultados.append({"caso": id_, "arquivo": arq, "status": "erro", "motivo": "Arquivo não encontrado"})
            continue
            
        try:
            enfileirar(id_, doc, arq)
            resultados.append({"caso": id_, "arquivo": arq, "status": "enfileirado"})
        except Exception as e:
            resultados.append({"caso": id_, "arquivo": arq, "status": "erro", "motivo": str(e)})
            
    if resultados:
        auditar("processar_lote", f"{len([r for r in resultados if r['status'] == 'enfileirado'])} enfileirados")
        
    return jsonify({"resultados": resultados})
