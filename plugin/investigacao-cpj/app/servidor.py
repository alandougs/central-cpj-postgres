#!/usr/bin/env python3
"""Central CPJ — sistema local de gestão de O.S./IPs de fraude e estelionato.

Perfis: admin, investigador, delegado, escrivão (login com senha; auditoria de ações).
Painéis: Início (pendências e prazos) · Nova O.S. (cadastro + upload) · Casos · Pesquisa (relacional e textual)
· Estatísticas · Sistema (exportar/importar, bases de consulta, referências, IA, usuários, rede).

Por padrão atende só este computador (127.0.0.1). O admin pode habilitar o acesso pela rede local (HTTPS).
Uso: python servidor.py [--porta 8765] [--sem-navegador] [--workspace PASTA]
"""
import argparse
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
import webbrowser
from flask import Flask, abort, request, session

if "--workspace" in sys.argv:  # precisa valer antes de importar os módulos de dados
    os.environ["CPJ_WORKSPACE"] = sys.argv[sys.argv.index("--workspace") + 1]
elif not os.environ.get("CPJ_WORKSPACE"):  # sem caminho fixo: workspace = 3 níveis acima de app\ (<ws>\plugin\investigacao-cpj\app)
    os.environ["CPJ_WORKSPACE"] = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ["CPJ_WORKSPACE"] = os.path.abspath(os.environ["CPJ_WORKSPACE"])  # normaliza "<pasta>\." vindo do .bat

AQUI = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(AQUI)
S_PDF = os.path.join(PLUGIN, "skills", "pdf-autos-policiais", "scripts")
S_BASE = os.path.join(PLUGIN, "skills", "base-cpj", "scripts")
sys.path.insert(0, S_BASE)
sys.path.insert(0, AQUI)

# Re-exportações compatíveis para scripts e suítes de teste existentes
from rotas.comum import (  # noqa: E402
    C,
    D_OS,
    DESCRICAO,
    EDITAVEIS,
    EDITAVEIS_GESTAO,
    EXT_OK,
    PERFIS,
    PY,
    Q,
    R,
    REDE_ARQ,
    RF,
    SEM_JANELA,
    TESS_DIR,
    TESSDATA_LOCAL,
    TEXTO_BUSCA,
    TODAS,
    WS,
    Auth,
    Tarefas,
    _ocr_cache,
    _ocr_trava,
    _painel_cache,
    _painel_trava,
    agora,
    ambiente_ocr,
    arquivos_relatorio,
    arvore,
    assinatura_arquivo,
    assinatura_painel,
    atualizar_painel,
    atualizar_trabalho,
    auditar,
    auth,
    eh_local,
    enfileirar,
    fila,
    gerar_docx,
    gerar_pdf,
    gravar_proc,
    idioma_ocr,
    ips_locais,
    ler_proc,
    nome_seguro,
    pasta_usuario,
    pode_alterar_os,
    proc_path,
    processar,
    rede_cfg,
    registrar_tratamento,
    requer,
    resumo,
    retomar_pendentes,
    rodar,
    salvar_upload,
    sha256,
    soffice,
    tarefas,
    trabalhador,
    trava,
    usuario,
    vincular_sessao,
    visiveis,
)
from rotas.relatorios import CAMPOS_MINUTA, ler_minuta, ultima_minuta  # noqa: E402
from rotas import registrar_rotas  # noqa: E402

app = Flask(__name__, static_folder=os.path.join(AQUI, "static"), static_url_path="/static")
app.config.update(
    MAX_CONTENT_LENGTH=2 * 1024 ** 3,
    SECRET_KEY=auth.segredo(),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Strict",
    PERMANENT_SESSION_LIFETIME=datetime.timedelta(hours=12),
)


@app.before_request
def protege_post():
    # mitigação de CSRF: toda escrita exige o cabeçalho enviado pela própria interface
    if request.method == "POST" and request.headers.get("X-CPJ") != "1":
        abort(403)


@app.after_request
def cabecalhos(r):
    r.headers["X-Content-Type-Options"] = "nosniff"
    r.headers["X-Frame-Options"] = "SAMEORIGIN"
    r.headers["Referrer-Policy"] = "no-referrer"
    r.headers["Cache-Control"] = "no-store"
    return r


# Registra todos os módulos de rotas (usuarios, casos, relatorios, consulta, sistema)
registrar_rotas(app)


class _ServidorModule(sys.modules[__name__].__class__):
    @property
    def auth(self):
        import rotas.comum as comum
        return comum._auth_inst

    @auth.setter
    def auth(self, val):
        import rotas.comum as comum
        comum._auth_inst = val
        if hasattr(comum, "tarefas") and hasattr(comum.tarefas, "auth"):
            comum.tarefas.auth = val

    @property
    def WS(self):
        import rotas.comum as comum
        return comum.WS

    @WS.setter
    def WS(self, val):
        import rotas.comum as comum
        comum.WS = val
        comum.C.WS = val

    @property
    def tarefas(self):
        import rotas.comum as comum
        return comum.tarefas

    @tarefas.setter
    def tarefas(self, val):
        import rotas.comum as comum
        comum._tarefas_inst = val

    @property
    def atualizar_painel(self):
        import rotas.comum as comum
        return comum.atualizar_painel

    @atualizar_painel.setter
    def atualizar_painel(self, val):
        import rotas.comum as comum
        comum.atualizar_painel = val

    @property
    def assinatura_painel(self):
        import rotas.comum as comum
        return comum.assinatura_painel

    @assinatura_painel.setter
    def assinatura_painel(self, val):
        import rotas.comum as comum
        comum.assinatura_painel = val

    @property
    def _painel_cache(self):
        import rotas.comum as comum
        return comum._painel_cache

    @_painel_cache.setter
    def _painel_cache(self, val):
        import rotas.comum as comum
        comum._painel_cache = val

    @property
    def _painel_trava(self):
        import rotas.comum as comum
        return comum._painel_trava

    @_painel_trava.setter
    def _painel_trava(self, val):
        import rotas.comum as comum
        comum._painel_trava = val


sys.modules[__name__].__class__ = _ServidorModule


# ================================================================== HTTPS (certificado autoassinado para a rede local)
def certificado():
    d = os.path.join(WS, "config")
    crt, key = os.path.join(d, "central.crt"), os.path.join(d, "central.key")
    if os.path.exists(crt) and os.path.exists(key):
        return crt, key
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    k = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    nome = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Central CPJ")])
    alt = [x509.DNSName("localhost"), x509.DNSName(socket.gethostname())] + [
        x509.IPAddress(ipaddress.ip_address(i)) for i in ips_locais() + ["127.0.0.1"]
    ]
    cert = (
        x509.CertificateBuilder()
        .subject_name(nome)
        .issuer_name(nome)
        .public_key(k.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow() - datetime.timedelta(days=1))
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=3650))
        .add_extension(x509.SubjectAlternativeName(alt), critical=False)
        .sign(k, hashes.SHA256())
    )
    open(key, "wb").write(
        k.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
    )
    open(crt, "wb").write(cert.public_bytes(serialization.Encoding.PEM))
    return crt, key


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--porta", type=int)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--sem-navegador", action="store_true")
    ap.add_argument("--workspace")
    ap.add_argument("--somente-local", action="store_true")
    a = ap.parse_args()

    os.makedirs(C.CASOS, exist_ok=True)
    threading.Thread(target=trabalhador, daemon=True).start()
    retomar_pendentes()
    cfg = rede_cfg()
    porta = a.porta or cfg["porta"]
    rede = cfg["compartilhar"] and not a.somente_local
    if rede and auth.ha_senha_temporaria():
        print("AVISO: há usuários com senha temporária — acesso pela rede NÃO foi habilitado até que troquem a senha.")
        rede = False
    host, ssl = ("0.0.0.0", certificado() if cfg["https"] else None) if rede else (a.host, None)
    if ssl:
        app.config["SESSION_COOKIE_SECURE"] = True
    app.config["REDE_ATIVA"] = rede
    url = f"{'https' if ssl else 'http'}://127.0.0.1:{porta}/"
    print(f"Central CPJ em {url}  (workspace: {WS})")
    if rede:
        print(
            "ACESSO PELA REDE LOCAL HABILITADO:",
            ", ".join(f"{'https' if ssl else 'http'}://{i}:{porta}" for i in ips_locais()),
        )
    print("Feche esta janela para encerrar.")
    if not a.sem_navegador:
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    app.run(host=host, port=porta, threaded=True, debug=False, ssl_context=ssl)
