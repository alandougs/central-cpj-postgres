"""Helper exclusivo dos testes: expande recursos locais na ordem do HTML.

Nao e runtime da aplicacao. Mantem cada bloco e sua ordem; nao fabrica script unico.
Usar caminho local para testes QuickJS; callback HTTP para as duas suites HTTP.
"""
from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit, urljoin


def recurso_local(url):
    parts = urlsplit(url)
    path = unquote(parts.path)
    if parts.scheme or parts.netloc or not path.startswith("/static/"):
        raise ValueError(f"Recurso nao local: {url}")
    relative = path[len("/static/"):]
    if not relative or "\\" in relative or any(p in ("", ".", "..") for p in relative.split("/")):
        raise ValueError(f"Recurso inseguro: {url}")
    return relative


class Attributes(HTMLParser):
    def __init__(self, tag):
        super().__init__()
        self.attrs = {}
        self.feed(tag)

    def handle_starttag(self, tag, attrs):
        self.attrs = dict(attrs)


def expandir(html, carregar):
    def substitute_script(match):
        attrs = Attributes(match[1]).attrs
        if "src" not in attrs:
            return match[0]
        if any(k in attrs for k in ("async", "defer")) or attrs.get("type") == "module":
            raise ValueError("Scripts devem manter ordem classica; atualizar teste se o contrato mudar")
        recurso_local(attrs["src"])
        body = carregar(attrs["src"])
        if not isinstance(body, str):
            raise TypeError("O carregador deve retornar texto UTF-8 e falhar para HTTP != 200")
        return "<script>" + body + "</script>"

    def substitute_style(match):
        attrs = Attributes(match[0]).attrs
        if "stylesheet" not in attrs.get("rel", "").split():
            return match[0]
        recurso_local(attrs["href"])
        return "<style>" + carregar(attrs["href"]) + "</style>"

    html = re.sub(r'(<script\b[^>]*>)(.*?)</script>', substitute_script, html, flags=re.S | re.I)
    return re.sub(r'<link\b[^>]*>', substitute_style, html, flags=re.I)


def ler_interface(index):
    index = Path(index).resolve()

    def read(url):
        path = (index.parent / recurso_local(url)).resolve()
        if index.parent not in path.parents:
            raise ValueError("Recurso fora de static")
        return path.read_text(encoding="utf-8")  # Ausente deve reprovar; nunca retornar vazio.

    return expandir(index.read_text(encoding="utf-8"), read)


def javascript(html):
    # Compilar TODO o JS junto preserva o teste anterior de sintaxe e duplicacao lexical.
    return "".join(re.findall(r'<script(?:[^>]*)>(.*?)</script>', html, re.S))


def expandir_http(html, base_url, opener):
    """Usa o mesmo servidor e cookie jar da suite HTTP; um 404 nunca vira fonte vazio."""
    def read(url):
        recurso_local(url)
        with opener.open(urljoin(base_url, url), timeout=30) as response:
            if response.status != 200:
                raise AssertionError(f"Recurso HTTP indisponivel: {url}: {response.status}")
            mime = response.headers.get_content_type()
            expected = ("text/css",) if urlsplit(url).path.endswith(".css") else ("text/javascript", "application/javascript")
            if mime not in expected:
                raise AssertionError(f"MIME incorreto: {url}: {mime}")
            return response.read().decode("utf-8")
    return expandir(html, read)
