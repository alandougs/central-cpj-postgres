from servidor import *
from flask import jsonify, request, abort, send_file, session, send_from_directory
import os, json, re, time, datetime, threading, shutil, subprocess, tempfile

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


