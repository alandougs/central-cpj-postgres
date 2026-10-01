from servidor import *
from flask import jsonify, request, abort, send_file, session, send_from_directory
import os, json, re, time, datetime, threading, shutil, subprocess, tempfile

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


