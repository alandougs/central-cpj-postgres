"""Fronteiras HTTP da Central: documentos não confiáveis e escuta local/TLS."""
import ipaddress
import os
import re
import ssl
from urllib.parse import urlsplit

from flask import current_app, jsonify, request, send_file


CSP_INTERFACE = (
    "default-src 'self'; script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
    "connect-src 'self'; frame-src 'self'; object-src 'self'; "
    "base-uri 'none'; form-action 'self'; frame-ancestors 'self'"
)
CSP_ARQUIVO = "default-src 'none'; sandbox; base-uri 'none'; frame-ancestors 'self'"
MIMES_PREVIA = {
    ".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp", ".bmp": "image/bmp",
    **{ext: "text/plain; charset=utf-8" for ext in (".md", ".csv", ".json", ".log", ".txt", ".jsonl")},
}


def enviar_arquivo_caso(alvo):
    mime = MIMES_PREVIA.get(os.path.splitext(alvo)[1].lower())
    resposta = send_file(alvo, mimetype=mime or "application/octet-stream", as_attachment=mime is None)
    resposta.headers["Content-Security-Policy"] = CSP_ARQUIVO
    return resposta


def host_local(host):
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _origem(url):
    if any(c.isspace() for c in url) or "\\" in url:
        raise ValueError("Origem inválida")
    partes = urlsplit(url)
    if (partes.scheme not in ("http", "https") or not partes.hostname
            or partes.username is not None or partes.password is not None
            or partes.path or partes.query or partes.fragment):
        raise ValueError("Origem inválida")
    porta = partes.port if partes.port is not None else (443 if partes.scheme == "https" else 80)
    if not 1 <= porta <= 65535:
        raise ValueError("Porta inválida")
    return partes.scheme, partes.hostname, porta


def proteger_requisicao():
    def negar(erro, status):
        # /api/sessao mantém os campos usados para apresentar a tela de entrada.
        return jsonify(erro=erro, usuario=None, solo=False, permissoes=[]), status

    host = request.host
    if not re.fullmatch(r"(?:\[[0-9a-fA-F:]+\]|[A-Za-z0-9.-]+)(?::[0-9]{1,5})?", host):
        return negar("Host inválido.", 400)
    try:
        origem_atual = _origem(f"{request.scheme}://{host}")
    except ValueError:
        return negar("Host inválido.", 400)
    rede = current_app.config.get("REDE_ATIVA", False)
    if not (host_local(origem_atual[1]) or (
            rede and origem_atual[1] in current_app.config.get("CPJ_HOSTS_REDE", ()))):
        return negar("Host não autorizado para esta Central.", 400)
    if ((rede and not request.is_secure) or (not host_local(request.remote_addr or "")
            and (not rede or not request.is_secure))):
        return negar("Acesso pela rede exige compartilhamento ativo e HTTPS.", 403)
    origem = request.headers.get("Origin")
    if origem is not None:
        try:
            if _origem(origem) != origem_atual:
                return negar("Origem não autorizada.", 403)
        except ValueError:
            return negar("Origem não autorizada.", 403)
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        if request.headers.get("Sec-Fetch-Site") == "cross-site":
            return negar("Origem não autorizada.", 403)
        if request.headers.get("X-CPJ") != "1":
            return negar("Cabeçalho X-CPJ obrigatório.", 403)


def configurar_escuta(cfg, host, somente_local=False, senha_temporaria=False):
    rede = bool(cfg.get("compartilhar")) and not somente_local
    if rede and cfg.get("https") is not True:
        raise ValueError("Compartilhamento pela rede exige HTTPS. Corrija a configuração ou use --somente-local.")
    if senha_temporaria:
        rede = False
    if not rede and not host_local(host):
        raise ValueError("--host não local exige compartilhamento autorizado com HTTPS e senhas definitivas.")
    return ("0.0.0.0" if rede else host), rede


def drenar_corpo_de_erro(resposta):
    """Permite enviar a resposta negada antes de fechar conexoes HTTP com JSON pequeno."""
    tamanho = request.content_length
    if (resposta.status_code >= 400 and tamanho is not None and 0 < tamanho <= 65536
            and request.mimetype == "application/json"):
        from werkzeug.exceptions import HTTPException

        try:
            # Nao interpreta JSON nem altera autorizacao; uploads e corpos sem limite ficam fora.
            request.get_data(cache=False)
        except (OSError, HTTPException):
            # A decisao ja foi tomada; desconexao do cliente nao deve virar autorizacao ou 500.
            pass
    return resposta


def criar_servidor_wsgi(app, host, porta, certificado=None):
    if ((not host_local(host) and not app.config.get("REDE_ATIVA"))
            or ((not host_local(host) or app.config.get("REDE_ATIVA")) and not certificado)):
        raise ValueError("Escuta pela rede exige modo autorizado e HTTPS.")
    from cheroot.wsgi import Server

    servidor = Server((host, porta), app, numthreads=10)
    servidor.max_request_body_size = app.config["MAX_CONTENT_LENGTH"]
    if certificado:
        from cheroot.ssl.builtin import BuiltinSSLAdapter

        servidor.ssl_adapter = BuiltinSSLAdapter(*certificado)
        servidor.ssl_adapter.context.minimum_version = ssl.TLSVersion.TLSv1_2
    return servidor
