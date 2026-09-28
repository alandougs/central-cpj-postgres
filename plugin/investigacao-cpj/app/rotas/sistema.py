#!/usr/bin/env python3
"""Rotas do sistema: página inicial, IA, agentes de plantão, tarefas, importação/exportação e painel."""
import os
import threading
import time
from flask import Blueprint, abort, current_app, jsonify, request, send_file, send_from_directory
import rotas.comum as comum
from rotas.comum import (
    C,
    WS,
    _painel_cache,
    _painel_trava,
    ambiente_ocr,
    assinatura_painel,
    atualizar_painel,
    auditar,
    auth,
    eh_local,
    idioma_ocr,
    requer,
    salvar_upload,
    soffice,
    tarefas,
)

bp_sistema = Blueprint("sistema", __name__)


@bp_sistema.get("/")
def inicio():
    return send_from_directory(current_app.static_folder, "index.html")


@bp_sistema.get("/api/ia/status")
@requer("ia")
def api_ia_status():
    return jsonify(tarefas.claude_status())


@bp_sistema.post("/api/ia/login")
@requer("ia")
def api_ia_login():
    if not eh_local():
        return jsonify({"erro": "Faça o login do Claude no computador da Central."}), 403
    try:
        tarefas.claude_login()
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    return jsonify({"ok": True})


@bp_sistema.post("/api/casos/<id_>/ia")
@requer("ia")
def api_ia(id_):
    d = request.get_json(force=True) or {}
    if not C.existe(id_):
        abort(404)
    agente = (d.get("agente") or "").strip() or None  # vazio = qualquer agente ocioso e aprovado
    if agente and not any(a["nome"] == agente and a["aprovado"] for a in tarefas.plantao.agentes()):
        return jsonify({"erro": f"Agente '{agente}' não existe ou não está aprovado."}), 400
    try:
        tid = tarefas.enfileirar_ia(id_, d.get("acao"), request.usuario["login"], d.get("observacoes") or "", agente)
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    auditar("ia_acionada", f"{id_}: {d.get('acao')}" + (f" → {agente}" if agente else ""))
    return jsonify({"tarefa": tid})


@bp_sistema.get("/api/plantao/agentes")
@requer("ia")
def api_plantao_agentes():
    ags = tarefas.plantao.agentes()
    campos = ("nome", "tipo", "modo", "estado", "aprovado", "job", "detalhe", "silencio_s", "host", "visto_em")
    return jsonify({
        "agentes": [{k: a.get(k) for k in campos} for a in ags],
        "ociosos": sum(1 for a in ags if a["estado"] == "ocioso"),
        "ocupados": sum(1 for a in ags if a["estado"] == "ocupado"),
        "pendentes": sum(1 for p in tarefas.plantao.pedidos() if p["estado"] == "pendente"),
    })


@bp_sistema.post("/api/plantao/agentes/<nome>/aprovacao")
@requer("usuarios")
def api_plantao_aprovacao(nome):
    aprovar = bool((request.get_json(silent=True) or {}).get("aprovar"))
    try:
        tarefas.plantao.aprovar(nome, aprovar)
    except ValueError as e:
        return jsonify({"erro": str(e)}), 404
    auditar("agente_aprovado" if aprovar else "agente_revogado", nome)
    return jsonify({"ok": True})


@bp_sistema.get("/api/tarefas")
@requer()
def api_tarefas():
    u = request.usuario
    return jsonify(tarefas.listar(u["login"], todas=auth.pode(u["perfil"], "trabalho")))


@bp_sistema.post("/api/tarefas/<tid>/cancelar")
@requer()
def api_tarefa_cancelar(tid):
    t = tarefas.obter(tid)
    u = request.usuario
    if not t:
        abort(404)
    if t["usuario"] != u["login"] and not auth.pode(u["perfil"], "trabalho"):
        abort(403)
    ok = tarefas.cancelar(tid)
    auditar("tarefa_cancelada", t["titulo"])
    return jsonify({"ok": ok})


@bp_sistema.post("/api/exportar")
@requer("dados")
def api_exportar():
    d = request.get_json(force=True) or {}
    modo = "completo" if d.get("modo") == "completo" else "dados"
    tid = tarefas.nova("exportacao", f"Exportação ({modo})", request.usuario["login"])
    tarefas.rodar(tid, tarefas.exportar, modo, bool(d.get("incluir_modelo")))
    auditar("exportacao", modo)
    return jsonify({"tarefa": tid})


@bp_sistema.get("/api/exportacoes")
@requer("dados")
def api_exportacoes():
    d = os.path.join(WS, "exportacoes")
    fs = sorted((f for f in os.listdir(d) if f.endswith(".zip")), reverse=True) if os.path.isdir(d) else []
    return jsonify([
        {"arquivo": f, "mb": round(os.path.getsize(os.path.join(d, f)) / 1048576, 1), "url": f"/exportacoes/{f}"}
        for f in fs
    ])


@bp_sistema.get("/exportacoes/<nome>")
@requer("dados")
def api_exportacao_baixar(nome):
    p = os.path.join(WS, "exportacoes", os.path.basename(nome))
    if not os.path.isfile(p):
        abort(404)
    auditar("exportacao_baixada", nome)
    return send_file(p, as_attachment=True)


@bp_sistema.get("/api/planilha")
@requer("estatisticas")
def api_planilha():
    tarefas.indexar()
    p = os.path.join(WS, "producao", "base.csv")
    if not os.path.exists(p):
        return jsonify({"erro": "Ainda não há dados."}), 404
    auditar("planilha_baixada")
    return send_file(p, as_attachment=True, download_name=f"CPJ-producao-{C.hoje()}.csv")


@bp_sistema.post("/api/importar")
@requer("dados")
def api_importar():
    try:
        p, nome = salvar_upload("arquivo", (".zip",))
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    tid = tarefas.nova("importacao", f"Importação de {nome}", request.usuario["login"])
    tarefas.rodar(tid, tarefas.importar, p)
    auditar("importacao", nome)
    return jsonify({"tarefa": tid})


@bp_sistema.get("/painel")
@requer("estatisticas")
def painel():
    chave = comum.assinatura_painel()
    p = os.path.join(WS, "producao", "painel.html")
    with comum._painel_trava:
        pronto = comum._painel_cache["chave"] == chave and os.path.isfile(p)
        if not pronto and not comum._painel_cache["gerando"] and time.monotonic() >= comum._painel_cache["retentar_apos"]:
            comum._painel_cache.update(gerando=True, erro=False)
            threading.Thread(target=comum.atualizar_painel, args=(chave,), daemon=True).start()
        erro = comum._painel_cache["erro"]
    if pronto:
        r = send_file(p)
        r.headers["X-CPJ-Painel"] = "pronto"
        return r
    if erro:
        return (
            "<p>Não foi possível atualizar as estatísticas. Tente abrir o painel novamente em alguns instantes.</p>",
            503,
            {"X-CPJ-Painel": "erro", "Retry-After": "30"},
        )
    return (
        "<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'>"
        "<meta http-equiv='refresh' content='2'><title>Estatísticas</title></head>"
        "<body><p>Atualizando as estatísticas… O painel aparecerá automaticamente.</p></body></html>",
        200,
        {"X-CPJ-Painel": "atualizando", "Retry-After": "2"},
    )


@bp_sistema.get("/api/sistema")
@requer("dados")
def api_sistema():
    return jsonify({
        "idioma_ocr": idioma_ocr(ambiente_ocr()),
        "pdf_automatico": bool(soffice()),
        "workspace": WS,
    })
