#!/usr/bin/env python3
"""Rotas de sessão, usuários, auditoria, perfis, pasta pessoal e rede."""
import json
import os
from flask import Blueprint, abort, current_app, jsonify, request, send_file, session
from rotas.comum import (
    DESCRICAO,
    PERFIS,
    REDE_ARQ,
    TODAS,
    arvore,
    auditar,
    auth,
    eh_local,
    ips_locais,
    modo_solo,
    pasta_usuario,
    rede_cfg,
    requer,
    usuario,
    vincular_sessao,
)

bp_usuarios = Blueprint("usuarios", __name__)


@bp_usuarios.get("/api/sessao")
def api_sessao():
    u = usuario()
    solo_ativo = bool(
        u
        and modo_solo()
        and request.remote_addr in ("127.0.0.1", "::1")
        and request.host.rsplit(":", 1)[0] in ("127.0.0.1", "localhost", "[::1]")
        and auth.usuario_solo()
    )
    return jsonify({
        "usuario": u,
        "permissoes": auth.permissoes(u["perfil"]) if u else [],
        "configurado": auth.tem_usuarios(),
        "local": eh_local(),
        "perfis": PERFIS,
        "solo": solo_ativo,
    })


@bp_usuarios.post("/api/configurar")
def api_configurar():
    """Primeiro uso: cria o administrador. Só no próprio computador e só se não houver usuários."""
    if auth.tem_usuarios():
        return jsonify({"erro": "Sistema já configurado."}), 400
    if not eh_local():
        return jsonify({"erro": "A configuração inicial só pode ser feita no computador da Central."}), 403
    d = request.get_json(force=True) or {}
    try:
        u = auth.salvar_usuario(
            d.get("login"),
            d.get("nome"),
            "admin",
            d.get("senha"),
            cpf=d.get("cpf") or "",
            email=d.get("email") or "",
            cargo=d.get("cargo") or "",
        )
        u = auth.autenticar(u["login"], d.get("senha"))
    except (ValueError, PermissionError) as e:
        return jsonify({"erro": str(e)}), 400
    vincular_sessao(u)
    pasta_usuario(u["login"])
    auth.auditar(u["login"], request.remote_addr, "configuracao_inicial")
    return jsonify({"ok": True})


@bp_usuarios.post("/api/entrar")
def api_entrar():
    d = request.get_json(force=True) or {}
    try:
        u = auth.autenticar(d.get("login"), d.get("senha"))
    except PermissionError as e:
        auth.auditar((d.get("login") or "")[:40], request.remote_addr, "login_falhou")
        return jsonify({"erro": str(e)}), 401
    vincular_sessao(u)
    auth.auditar(u["login"], request.remote_addr, "login")
    return jsonify({"ok": True, "trocar_senha": u["trocar_senha"]})


@bp_usuarios.post("/api/minha-conta")
@requer()
def api_minha_conta():
    d = request.get_json(force=True) or {}
    try:
        u = auth.atualizar_contato(request.usuario["login"], email=d.get("email"), cargo=d.get("cargo"))
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    auditar("conta_atualizada")
    return jsonify(u)


@bp_usuarios.post("/api/sair")
def api_sair():
    u = usuario()
    if u:
        auth.auditar(u["login"], request.remote_addr, "logout")
    session.clear()
    return jsonify({"ok": True})


@bp_usuarios.post("/api/minha-senha")
@requer()
def api_minha_senha():
    d = request.get_json(force=True) or {}
    try:
        u = auth.trocar_senha(request.usuario["login"], d.get("atual"), d.get("nova"))
    except (PermissionError, ValueError) as e:
        return jsonify({"erro": str(e)}), 400
    vincular_sessao(u)
    auditar("troca_senha")
    return jsonify({"ok": True})


@bp_usuarios.get("/api/usuarios")
@requer("usuarios")
def api_usuarios():
    return jsonify(auth.listar())


@bp_usuarios.post("/api/usuarios")
@requer("usuarios")
def api_usuarios_salvar():
    d = request.get_json(force=True) or {}
    try:
        u = auth.salvar_usuario(
            d.get("login"),
            d.get("nome"),
            d.get("perfil"),
            d.get("senha") or None,
            d.get("ativo", True),
            cpf=d.get("cpf"),
            email=d.get("email"),
            cargo=d.get("cargo"),
            temporaria=bool(d.get("temporaria")),
        )
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    pasta_usuario(u["login"])
    auditar("usuario_salvo", f"{u['login']} ({u['perfil']})")
    return jsonify(u)


@bp_usuarios.post("/api/usuarios/<login>/remover")
@requer("usuarios")
def api_usuarios_remover(login):
    try:
        auth.remover_usuario(login)
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    auditar("usuario_removido", login)
    return jsonify({"ok": True})


@bp_usuarios.get("/api/auditoria")
@requer("usuarios")
def api_auditoria():
    return jsonify(auth.auditoria(300))


@bp_usuarios.get("/api/perfis")
@requer("usuarios")
def api_perfis():
    m = auth.matriz()
    return jsonify({
        "matriz": {k: sorted(v) for k, v in m.items()},
        "descricao": DESCRICAO,
        "perfis": PERFIS,
        "editaveis": sorted(TODAS - {"usuarios", "rede"}),
    })


@bp_usuarios.post("/api/perfis")
@requer("usuarios")
def api_perfis_salvar():
    m = auth.salvar_matriz((request.get_json(force=True) or {}).get("matriz") or {})
    auditar("perfis_alterados", json.dumps(m, ensure_ascii=False)[:300])
    return jsonify(m)


@bp_usuarios.get("/api/responsaveis")
@requer("trabalho")
def api_responsaveis():
    return jsonify([{"login": u["login"], "nome": u["nome"]} for u in auth.por_permissao("trabalho")])


@bp_usuarios.get("/api/minha-pasta")
@requer()
def api_minha_pasta():
    d = pasta_usuario(request.usuario["login"])
    return jsonify({"pasta": d if eh_local() else None, "arquivos": arvore(d)})


@bp_usuarios.get("/minha-pasta/<path:rel>")
@requer()
def api_minha_pasta_arquivo(rel):
    base = os.path.normpath(pasta_usuario(request.usuario["login"]))
    alvo = os.path.normpath(os.path.join(base, rel))
    if not alvo.startswith(base + os.sep) or not os.path.isfile(alvo):
        abort(404)
    auditar("download_pasta_pessoal", rel)
    return send_file(alvo, as_attachment=True)


@bp_usuarios.post("/api/minha-pasta/abrir")
@requer()
def api_minha_pasta_abrir():
    if not eh_local():
        return jsonify({"erro": "Disponível apenas no computador da Central. Baixe os arquivos pelo navegador."}), 403
    if hasattr(os, "startfile"):
        os.startfile(pasta_usuario(request.usuario["login"]))
    return jsonify({"ok": True})


@bp_usuarios.get("/api/rede")
@requer("usuarios")
def api_rede():
    cfg = rede_cfg()
    proto = "https" if cfg["https"] else "http"
    return jsonify(
        cfg | {
            "enderecos": [f"{proto}://{ip}:{cfg['porta']}" for ip in ips_locais()],
            "ativo_agora": current_app.config.get("REDE_ATIVA", False),
        }
    )


@bp_usuarios.post("/api/rede")
@requer("rede")
def api_rede_salvar():
    d = request.get_json(force=True) or {}
    if d.get("compartilhar") and auth.ha_senha_temporaria():
        return jsonify({
            "erro": (
                "Há usuários com senha temporária ("
                + ", ".join(auth.ha_senha_temporaria())
                + "). Eles precisam trocá-la antes de liberar o acesso pela rede."
            )
        }), 400
    cfg = rede_cfg()
    cfg.update(compartilhar=bool(d.get("compartilhar")), https=bool(d.get("https", True)))
    os.makedirs(os.path.dirname(REDE_ARQ), exist_ok=True)
    with open(REDE_ARQ, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    auditar("rede_alterada", json.dumps(cfg))
    return jsonify(cfg | {"reiniciar": True})
