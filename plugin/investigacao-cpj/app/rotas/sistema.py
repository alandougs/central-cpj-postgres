#!/usr/bin/env python3
"""Rotas do sistema: página inicial, IA, agentes de plantão, tarefas, importação/exportação e painel."""
import json
import os
import subprocess
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
    resp = send_from_directory(current_app.static_folder, "index.html")
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


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


@bp_sistema.get("/api/painel/pdf")
@bp_sistema.get("/painel.pdf")
@requer("estatisticas")
def painel_pdf():
    chave = comum.assinatura_painel()
    html_p = os.path.join(WS, "producao", "painel.html")
    pdf_p = os.path.join(WS, "producao", "painel.pdf")
    if not os.path.isfile(html_p):
        comum.atualizar_painel(chave)
    edge = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    if not os.path.isfile(edge):
        edge = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
    if not os.path.isfile(edge):
        return jsonify({"erro": "Navegador Microsoft Edge não encontrado para conversão em PDF."}), 500
    file_url = "file:///" + os.path.abspath(html_p).replace("\\", "/")
    cmd = [edge, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={pdf_p}", file_url]
    subprocess.run(cmd, timeout=30, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if os.path.isfile(pdf_p):
        auditar("estatisticas_pdf_baixado")
        return send_file(pdf_p, as_attachment=True, download_name=f"Estatisticas-SIP-Fraudes-{C.hoje()}.pdf")
    return jsonify({"erro": "Falha ao gerar PDF das estatísticas."}), 500


CONFIG_LLM = os.path.join(WS, "config", "chaves_llm.json")


def _carregar_cfg_llm():
    padrao = {
        "openai": {"nome": "OpenAI (GPT)", "chave": "", "modelo": "gpt-4o", "ativo": False},
        "anthropic": {"nome": "Anthropic (Claude)", "chave": "", "modelo": "claude-3-7-sonnet-latest", "ativo": False},
        "gemini": {"nome": "Google (Gemini)", "chave": "", "modelo": "gemini-2.0-flash", "ativo": False},
        "deepseek": {"nome": "DeepSeek", "chave": "", "modelo": "deepseek-chat", "ativo": False},
        "copilot": {"nome": "GitHub Copilot", "chave": "", "modelo": "copilot", "ativo": False}
    }
    if os.path.isfile(CONFIG_LLM):
        try:
            with open(CONFIG_LLM, "r", encoding="utf-8") as f:
                d = json.load(f)
                for k, v in d.items():
                    if k in padrao and isinstance(v, dict):
                        padrao[k].update(v)
        except Exception:
            pass
    return padrao


@bp_sistema.get("/api/sistema/llm")
@requer("ia")
def api_sistema_llm_get():
    cfg = _carregar_cfg_llm()
    saida = {}
    for prov, d in cfg.items():
        ch = d.get("chave") or ""
        mascarada = (ch[:4] + "*" * (len(ch) - 8) + ch[-4:]) if len(ch) >= 12 else ("*" * len(ch) if ch else "")
        saida[prov] = {
            "nome": d.get("nome", prov),
            "modelo": d.get("modelo", ""),
            "ativo": bool(d.get("ativo", False)),
            "chave_mascarada": mascarada,
            "tem_chave": bool(ch)
        }
    return jsonify(saida)


@bp_sistema.post("/api/sistema/llm")
@requer("usuarios")
def api_sistema_llm_post():
    dados = request.get_json(force=True) or {}
    prov = dados.get("provedor")
    if not prov:
        return jsonify({"erro": "Provedor não informado."}), 400
    cfg = _carregar_cfg_llm()
    if prov not in cfg:
        cfg[prov] = {"nome": prov, "chave": "", "modelo": "", "ativo": False}
    nova_chave = (dados.get("chave") or "").strip()
    if nova_chave and not nova_chave.startswith("*"):
        cfg[prov]["chave"] = nova_chave
    if "modelo" in dados:
        cfg[prov]["modelo"] = (dados["modelo"] or "").strip()
    if "ativo" in dados:
        cfg[prov]["ativo"] = bool(dados["ativo"])
    os.makedirs(os.path.dirname(CONFIG_LLM), exist_ok=True)
    with open(CONFIG_LLM, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    auditar("chaves_llm_atualizadas", prov)
    return jsonify({"ok": True, "provedor": prov})


@bp_sistema.get("/api/sistema")
@requer("dados")
def api_sistema():
    return jsonify({
        "idioma_ocr": idioma_ocr(ambiente_ocr()),
        "pdf_automatico": bool(soffice()),
        "workspace": WS,
    })
