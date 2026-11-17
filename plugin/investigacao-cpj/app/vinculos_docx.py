"""Atesta a emissão local de um DOCX vinculado aos bytes da minuta."""
import hashlib
import hmac
import json
import re

from auth import Auth

SCHEMA = "cpj-vinculo-docx/1"
_CAMPOS = ("schema", "caso", "minuta", "docx", "sha256_minuta", "sha256_docx", "gerado_em")
_DOMINIO_SUBCHAVE = b"CPJ\x00vinculo-docx\x00subchave\x001"


def _conteudo(registro):
    if (not isinstance(registro, dict) or registro.get("schema") != SCHEMA
            or set(registro) - set(_CAMPOS) - {"hmac_sha256"}
            or any(not isinstance(registro.get(k), str) or not registro[k] for k in _CAMPOS)
            or any(not re.fullmatch(r"[0-9a-f]{64}", registro[k]) for k in ("sha256_minuta", "sha256_docx"))):
        raise ValueError("Vínculo de emissão do DOCX inválido.")
    return json.dumps({k: registro[k] for k in _CAMPOS}, ensure_ascii=False,
                      sort_keys=True, separators=(",", ":")).encode("utf-8")


def _chave(ws):
    segredo = Auth(ws).segredo().encode("utf-8")
    return hmac.new(segredo, _DOMINIO_SUBCHAVE, hashlib.sha256).digest()


def emitir(ws, caso, minuta, docx, sha256_minuta, sha256_docx, gerado_em):
    registro = {"schema": SCHEMA, "caso": caso, "minuta": minuta, "docx": docx,
                "sha256_minuta": sha256_minuta, "sha256_docx": sha256_docx, "gerado_em": gerado_em}
    registro["hmac_sha256"] = hmac.new(_chave(ws), _conteudo(registro), hashlib.sha256).hexdigest()
    return registro


def verificar(ws, registro, caso):
    try:
        conteudo = _conteudo(registro)
        assinatura = registro.get("hmac_sha256")
        if registro["caso"] != caso or not isinstance(assinatura, str) or not re.fullmatch(r"[0-9a-f]{64}", assinatura):
            return False
        esperada = hmac.new(_chave(ws), conteudo, hashlib.sha256).hexdigest()
        return hmac.compare_digest(assinatura, esperada)
    except (OSError, ValueError, TypeError, UnicodeError):
        return False
