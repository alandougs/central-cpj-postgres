"""Proteção local de segredos. DPAPI por conta Windows; falha fechada.

Não protege contra quem controla a mesma conta ou a máquina inteira. Fora do
Windows exige chave externa explícita CPJ_LOCAL_SECRET_KEY (base64, 32 bytes).
"""
import base64
import copy
import ctypes
import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading
import time
from contextlib import contextmanager


class SegurancaLocalErro(RuntimeError):
    pass


_trava = threading.RLock()
_SCHEMA = "cpj-local-secret/1"
_locks_auditoria = {}
_locks_thread = threading.local()


def _dpapi(dados, desfazer=False):
    from ctypes import wintypes
    class Blob(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]
    origem = ctypes.create_string_buffer(dados)
    entrada = Blob(len(dados), ctypes.cast(origem, ctypes.POINTER(ctypes.c_ubyte)))
    saida = Blob()
    crypt = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    if desfazer:
        fn = crypt.CryptUnprotectData
        fn.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
        ok = fn(ctypes.byref(entrada), None, None, None, None, 1, ctypes.byref(saida))
    else:
        fn = crypt.CryptProtectData
        fn.argtypes = [ctypes.POINTER(Blob), wintypes.LPCWSTR, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
        ok = fn(ctypes.byref(entrada), "Central CPJ", None, None, None, 1, ctypes.byref(saida))
    if not ok: raise SegurancaLocalErro("Proteção local indisponível para esta conta.")
    try: return ctypes.string_at(saida.pbData, saida.cbData)
    finally: kernel.LocalFree(saida.pbData)


def _chave_externa():
    chave = base64.b64decode(os.environ.get("CPJ_LOCAL_SECRET_KEY", ""), validate=True)
    if len(chave) != 32: raise SegurancaLocalErro("Configure uma chave externa de proteção local de 32 bytes.")
    return chave


def proteger(dados):
    try:
        if os.name == "nt": metodo, cifrado = "dpapi-user", _dpapi(dados)
        else:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            nonce = os.urandom(12)
            metodo, cifrado = "aesgcm-external", nonce + AESGCM(_chave_externa()).encrypt(nonce, dados, _SCHEMA.encode())
        return {"schema": _SCHEMA, "metodo": metodo, "dados": base64.b64encode(cifrado).decode("ascii")}
    except Exception:
        raise SegurancaLocalErro("Não foi possível proteger os segredos locais; nenhum segredo foi substituído.") from None


def desproteger(envelope):
    try:
        if envelope.get("schema") != _SCHEMA: raise ValueError()
        raw = base64.b64decode(envelope["dados"], validate=True)
        if envelope["metodo"] == "dpapi-user" and os.name == "nt": return _dpapi(raw, True)
        if envelope["metodo"] == "aesgcm-external":
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            return AESGCM(_chave_externa()).decrypt(raw[:12], raw[12:], _SCHEMA.encode())
        raise ValueError()
    except Exception:
        raise SegurancaLocalErro("Não foi possível abrir os segredos locais nesta conta; arquivo preservado.") from None


def suporta_acl(caminho):
    if os.name != "nt": return True
    from ctypes import wintypes
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    volume = ctypes.create_unicode_buffer(1024)
    getpath = kernel.GetVolumePathNameW
    getpath.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
    flags = wintypes.DWORD()
    info = kernel.GetVolumeInformationW
    info.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD, ctypes.c_void_p,
                     ctypes.c_void_p, ctypes.POINTER(wintypes.DWORD), wintypes.LPWSTR, wintypes.DWORD]
    if not getpath(str(Path(caminho).absolute()), volume, len(volume)) or not info(volume, None, 0, None, None, ctypes.byref(flags), None, 0):
        raise SegurancaLocalErro("Não foi possível conferir a proteção do volume local.")
    return bool(flags.value & 8)  # FILE_PERSISTENT_ACLS


def caminho_ancora_auditoria(ws):
    """Em exFAT a âncora fica fora do volume de dados, em perfil com ACL."""
    config = Path(ws) / "config"
    if suporta_acl(config): return config / "auditoria.estado"
    perfil = os.environ.get("LOCALAPPDATA")
    if not perfil or not suporta_acl(perfil):
        raise SegurancaLocalErro("Auditoria exige armazenamento local por usuário com ACL para a âncora.")
    namespace = hashlib.sha256(os.path.normcase(str(Path(ws).resolve())).encode()).hexdigest()
    return Path(perfil) / "Central-CPJ" / "seguranca-local" / namespace / "auditoria.estado"


@contextmanager
def trava_auditoria(ws, timeout=10):
    """Serializa processos, além das threads; arquivo fica no volume da âncora."""
    caminho = caminho_ancora_auditoria(ws).with_suffix(".lock")
    chave = str(caminho.resolve())
    with _trava: lock = _locks_auditoria.setdefault(chave, threading.RLock())
    if not lock.acquire(timeout=timeout): raise SegurancaLocalErro("Auditoria ocupada; tente novamente.")
    fd, adquirido = None, False
    ativos = getattr(_locks_thread, "ativos", set())
    try:
        if chave in ativos:
            yield
            return
        caminho.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(caminho, os.O_RDWR | os.O_CREAT, 0o600)
        if not restringir_arquivo(caminho): raise SegurancaLocalErro("Trava da auditoria exige ACL.")
        if not os.fstat(fd).st_size: os.write(fd, b"\0")
        inicio = time.monotonic()
        while True:
            try:
                os.lseek(fd, 0, os.SEEK_SET)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                adquirido = True
                break
            except OSError:
                if time.monotonic() - inicio >= timeout:
                    raise SegurancaLocalErro("Auditoria ocupada por outro processo; tente novamente.") from None
                time.sleep(0.025)
        _locks_thread.ativos = ativos | {chave}
        yield
    finally:
        if adquirido:
            _locks_thread.ativos = ativos
            os.lseek(fd, 0, os.SEEK_SET)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(fd, fcntl.LOCK_UN)
        if fd is not None: os.close(fd)
        lock.release()


def restringir_arquivo(caminho):
    if not suporta_acl(caminho): return False
    if os.name != "nt":
        os.chmod(caminho, 0o600)
        return True
    from ctypes import wintypes
    adv = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    sd = ctypes.c_void_p()
    conv = adv.ConvertStringSecurityDescriptorToSecurityDescriptorW
    conv.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p]
    setsec = adv.SetFileSecurityW
    setsec.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_void_p]
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    # DACL protegida: proprietário do arquivo e SYSTEM; sem permissões herdadas.
    if not conv("D:P(A;;FA;;;OW)(A;;FA;;;SY)", 1, ctypes.byref(sd), None):
        raise SegurancaLocalErro("Não foi possível restringir o arquivo local.")
    try:
        if not setsec(str(caminho), 0x80000004, sd):
            raise SegurancaLocalErro("Não foi possível restringir o arquivo local.")
    finally: kernel.LocalFree(sd)
    return True


def gravar_atomico_restrito(caminho, dados, exigir_acl=True):
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".cpj-seguro-", dir=caminho.parent)
    try:
        if not restringir_arquivo(tmp) and exigir_acl:
            raise SegurancaLocalErro("Arquivo protegido exige volume com ACL.")
        with os.fdopen(fd, "wb") as f:
            fd = None
            f.write(dados)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, caminho)
    finally:
        if fd is not None: os.close(fd)
        if os.path.exists(tmp): os.unlink(tmp)


def salvar_cfg_llm(caminho, cfg):
    with _trava:
        try:
            d = copy.deepcopy(cfg)
            if not isinstance(d, dict): raise ValueError()
            for prov in d.values():
                if not isinstance(prov, dict): raise ValueError()
                chave = prov.get("chave", "")
                if not isinstance(chave, str): raise ValueError()
                if chave: prov["chave"] = proteger(chave.encode("utf-8"))
            # No exFAT os segredos já estão cifrados; não prometer ACL inexistente.
            gravar_atomico_restrito(caminho, json.dumps(d, ensure_ascii=False, indent=2).encode("utf-8"), exigir_acl=False)
        except Exception:
            raise SegurancaLocalErro("Falha ao salvar configuração protegida; configuração anterior preservada.") from None


def carregar_cfg_llm(caminho):
    with _trava:
        try:
            caminho = Path(caminho)
            if not caminho.exists(): return {}
            d = json.loads(caminho.read_text(encoding="utf-8"))
            if not isinstance(d, dict): raise ValueError()
            legado = False
            for prov in d.values():
                if not isinstance(prov, dict): raise ValueError()
                chave = prov.get("chave", "")
                if isinstance(chave, dict): prov["chave"] = desproteger(chave).decode("utf-8")
                elif isinstance(chave, str): legado = legado or bool(chave)
                else: raise ValueError()
            if legado: salvar_cfg_llm(caminho, d)
            return d
        except Exception:
            raise SegurancaLocalErro("Configuração de IA protegida indisponível; arquivo preservado.") from None


def exportar_estado_auditoria(ws):
    """Snapshot offline: envelope cifrado e vínculo ao log, sem criar/migrar nada."""
    import auth
    with auth._trava:
        try:
            log = Path(ws) / "config" / "auditoria.log"
            raw = log.read_bytes() if log.exists() else b""
            ancora = caminho_ancora_auditoria(ws)
            envelope = json.loads(ancora.read_text(encoding="utf-8")) if ancora.exists() else None
            if envelope is not None:
                a = auth.Auth.__new__(auth.Auth)
                a.dir, a.log = str(log.parent), str(log)
                a._estado_auditoria(estado_importado=json.loads(desproteger(envelope)))
            elif any("_integridade" in json.loads(linha) for linha in raw.splitlines() if linha.strip()):
                raise ValueError()
            return {"schema": "cpj-auditoria-backup/1", "envelope": envelope, "log_sha256": hashlib.sha256(raw).hexdigest()}
        except Exception:
            raise SegurancaLocalErro("Não foi possível exportar a âncora íntegra da auditoria; mantenha log e armazenamento protegido.") from None


def restaurar_estado_auditoria(ws_destino, dados, *, ws_validacao=None):
    """Remapeia snapshot para pasta nova na mesma conta; não reinicia a cadeia.

ws_validacao é o stage ainda não publicado. Em NTFS a âncora acompanha seu
rename; em exFAT fica no perfil, com namespace do destino definitivo.
"""
    import auth
    with auth._trava:
        try:
            if not isinstance(dados, dict) or dados.get("schema") != "cpj-auditoria-backup/1": raise ValueError()
            log = Path(ws_validacao or ws_destino) / "config" / "auditoria.log"
            raw = log.read_bytes() if log.exists() else b""
            if hashlib.sha256(raw).hexdigest() != dados.get("log_sha256"): raise ValueError()
            envelope = dados.get("envelope")
            if envelope is None:
                if any("_integridade" in json.loads(linha) for linha in raw.splitlines() if linha.strip()): raise ValueError()
                return
            estado = json.loads(desproteger(envelope))
            a = auth.Auth.__new__(auth.Auth)
            a.dir, a.log = str(log.parent), str(log)
            a._estado_auditoria(estado_importado=estado)
            ancora = caminho_ancora_auditoria(ws_destino)
            if ancora == Path(ws_destino) / "config" / "auditoria.estado" and ws_validacao:
                ancora = Path(ws_validacao) / "config" / "auditoria.estado"
            if ancora.exists():
                if json.loads(ancora.read_text(encoding="utf-8")) != envelope: raise ValueError()
            else:
                gravar_atomico_restrito(ancora, json.dumps(envelope).encode("utf-8"))
        except Exception:
            raise SegurancaLocalErro("Restauração da auditoria recusada: confira log/âncora e use a mesma conta Windows; "
                                     "outra conta exige migração explícita, nunca reinicialização silenciosa.") from None
