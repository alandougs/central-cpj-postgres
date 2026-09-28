#!/usr/bin/env python3
"""Registro modular de rotas da Central CPJ."""
from rotas.casos import bp_casos
from rotas.consulta import bp_consulta
from rotas.relatorios import bp_relatorios
from rotas.sistema import bp_sistema
from rotas.usuarios import bp_usuarios


def registrar_rotas(app):
    """Registra todos os blueprints de rotas no aplicativo Flask."""
    app.register_blueprint(bp_usuarios)
    app.register_blueprint(bp_casos)
    app.register_blueprint(bp_relatorios)
    app.register_blueprint(bp_consulta)
    app.register_blueprint(bp_sistema)

