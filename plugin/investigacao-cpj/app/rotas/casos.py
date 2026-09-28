#!/usr/bin/env python3
"""Rotas de O.S., casos, pendências, arquivos do caso e fila de processamento."""
import datetime
import json
import os
import re
import tempfile
import time
from flask import Blueprint, abort, jsonify, request, send_file
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
        c["visto"] = True
        C.salvar(c)
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
        return jsonify({"erro": "conflito_concorrencia", "mensagem": str(e)}), 409
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
    alvo = os.path.normpath(os.path.join(C.caminho(id_), sub))
    if not alvo.startswith(os.path.normpath(C.caminho(id_))) or not os.path.exists(alvo):
        abort(404)
    if hasattr(os, "startfile"):
        os.startfile(alvo)
    return jsonify({"ok": True})


@bp_casos.get("/arquivo/<id_>/<path:rel>")
@requer("casos")
def api_arquivo(id_, rel):
    base = os.path.normpath(C.caminho(id_))
    alvo = os.path.normpath(os.path.join(base, rel))
    if not alvo.startswith(base + os.sep) or not os.path.isfile(alvo):
        abort(404)
    u = request.usuario
    if not auth.pode(u["perfil"], "trabalho"):
        r = rel.replace("\\", "/")
        final = r.startswith("03-relatorios/") and "final" in r.lower()
        if not (final or r.startswith("00-originais/")):
            abort(403)
    auditar("download", f"{id_}/{rel}")
    ext = os.path.splitext(alvo)[1].lower()
    if ext in (".md", ".csv", ".json", ".log", ".txt", ".jsonl"):
        return send_file(alvo, mimetype="text/plain; charset=utf-8")
    return send_file(alvo, as_attachment=ext in (".docx", ".xlsx"))


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

