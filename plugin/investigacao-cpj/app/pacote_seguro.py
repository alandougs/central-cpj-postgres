"""CPJENC v1: ZIP em fluxo, Scrypt e blocos AES-256-GCM autenticados.

Não cria ZIP temporário em claro. Cabeçalho, ordem, tamanho e fim do fluxo
são autenticados. O leitor valida TODO o pacote antes de expor bytes ao ZIP.
RAM limitada a poucos blocos de 1 MiB, inclusive em pacotes de 2 GiB.
"""
import bisect
import io
import os
import struct
from pathlib import Path
import re
import shutil
import subprocess

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

MAGIC = b"CPJENC\x01\x00"
BLOCO = 1 << 20
LIMITE = 2 * 1024**3 + 16 * 1024**2  # dados + diretório ZIP/manifesto
MAX_LEITURA = 16 * 1024**2


def proteger_preparacao(pasta):
    """ACL quando suportada; exFAT depende da proteção do volume do workspace.

Preparação contém os arquivos que serão os casos finais, nunca ZIP em claro.
Falha/erro limpa imediatamente; queda abrupta limpa órfãos no próximo início.
Não promete apagamento físico nem recuperação atômica de vários casos juntos.
"""
    p = Path(pasta)
    if p.is_symlink() or getattr(p, "is_junction", lambda: False)(): raise ValueError("Preparação não aceita links.")
    p.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name != "nt": p.chmod(0o700); return
    import ctypes
    import csv
    volume = ctypes.create_unicode_buffer(261)
    flags = ctypes.c_ulong()
    if not ctypes.windll.kernel32.GetVolumePathNameW(str(p.resolve()), volume, len(volume)):
        raise ValueError("Não foi possível verificar o volume de preparação.")
    if not ctypes.windll.kernel32.GetVolumeInformationW(volume.value, None, 0, None, None, ctypes.byref(flags), None, 0):
        raise ValueError("Não foi possível verificar a proteção do volume.")
    if not flags.value & 8: return  # FILE_PERSISTENT_ACLS: exFAT não suporta ACL
    sid = next(csv.reader([subprocess.check_output(["whoami", "/user", "/fo", "csv", "/nh"], text=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).strip()]))[1]
    r = subprocess.run(["icacls", str(p), "/inheritance:r", "/grant:r", f"*{sid}:(OI)(CI)F", "*S-1-5-18:(OI)(CI)F"], capture_output=True,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if r.returncode: raise ValueError("Não foi possível restringir a pasta de preparação.")


def limpar_preparacao_orfa(ws):
    raiz = Path(ws) / "exportacoes/_importando"
    if not raiz.exists(): return
    proteger_preparacao(raiz)
    for p in raiz.iterdir():
        m = re.fullmatch(r"(\d+)-[a-f0-9]{12}", p.name)
        if not m or not p.is_dir() or p.is_symlink() or getattr(p, "is_junction", lambda: False)(): continue
        pid = int(m[1])
        if pid == os.getpid(): continue
        if os.name == "nt":
            import ctypes
            k = ctypes.WinDLL("kernel32", use_last_error=True)
            k.OpenProcess.restype = ctypes.c_void_p
            h = k.OpenProcess(0x1000, False, pid)
            if h:
                k.CloseHandle(ctypes.c_void_p(h)); continue
            if ctypes.get_last_error() != 87: continue  # acesso negado = preserve
        else:
            try: os.kill(pid, 0); continue
            except ProcessLookupError: pass
            except PermissionError: continue
        # Nome de diretório e alvo resolvido confinados à preparação.
        if p.resolve().parent == raiz.resolve(): shutil.rmtree(p)


class LeituraLimitada:
    """Limita alocações do parser ZIP também para pacotes legados hostis."""
    def __init__(self, arquivo): self.arquivo = arquivo
    def read(self, tamanho=-1):
        if tamanho < 0 or tamanho > MAX_LEITURA: raise ValueError("Estrutura ZIP excede o limite permitido.")
        return self.arquivo.read(tamanho)
    def seek(self, *args): return self.arquivo.seek(*args)
    def tell(self): return self.arquivo.tell()
    def seekable(self): return True


def validar_senha(senha):
    if not isinstance(senha, str) or not 12 <= len(senha) <= 1024:
        raise ValueError("Informe uma senha de 12 a 1024 caracteres para o pacote.")


def _cifra(senha, salt):
    validar_senha(senha)
    return AESGCM(Scrypt(salt=salt, length=32, n=2**15, r=8, p=1).derive(senha.encode("utf-8")))


class Escritor(io.RawIOBase):
    """Destino não seekable aceito por zipfile; o disco recebe somente cifra."""
    def __init__(self, arquivo, senha, cancelar=lambda: None):
        salt = os.urandom(16)
        self.cab = MAGIC + salt + os.urandom(8)
        self.cifra = _cifra(senha, salt)
        self.arquivo, self.cancelar = arquivo, cancelar
        self.indice, self.pos, self.buffer = 0, 0, bytearray()
        self.finalizado = False
        arquivo.write(self.cab)

    def writable(self): return True
    def seekable(self): return False
    def tell(self): return self.pos

    def _bloco(self, dados):
        self.cancelar()
        tamanho = struct.pack(">I", len(dados))
        idx = struct.pack(">I", self.indice)
        self.arquivo.write(tamanho)
        self.arquivo.write(self.cifra.encrypt(self.cab[-8:] + idx, dados, self.cab + idx + tamanho))
        self.indice += 1

    def write(self, dados):
        if self.finalizado: raise ValueError("Pacote já finalizado.")
        if self.pos + len(dados) > LIMITE: raise ValueError("Pacote excede o limite de 2 GiB de dados.")
        self.pos += len(dados)
        # zipfile escreve blocos pequenos; fragmentar também chamadas grandes.
        for inicio in range(0, len(dados), BLOCO):
            self.buffer.extend(dados[inicio:inicio+BLOCO])
            while len(self.buffer) >= BLOCO:
                bloco = bytes(self.buffer[:BLOCO]); del self.buffer[:BLOCO]
                self._bloco(bloco)
        return len(dados)

    def finalizar(self):
        if not self.finalizado:
            if self.buffer: self._bloco(bytes(self.buffer)); self.buffer.clear()
            self._bloco(b"")  # autenticador obrigatório do fim, impede truncamento
            self.finalizado = True
            self.arquivo.flush()


class Leitor(io.RawIOBase):
    """Verificação integral seguida de acesso aleatório a blocos autenticados."""
    def __init__(self, arquivo, senha, cancelar=lambda: None):
        self.arquivo, self.cancelar = arquivo, cancelar
        self.cab = arquivo.read(32)
        if len(self.cab) != 32 or self.cab[:8] != MAGIC:
            raise ValueError("Formato de pacote cifrado inválido.")
        self.cifra = _cifra(senha, self.cab[8:24])
        self.blocos, self.inicios, self.pos, self.total = [], [], 0, 0
        self.cache = (-1, b"")
        indice, curto = 0, False
        try:
            while True:
                cancelar()
                tamanho_bytes = arquivo.read(4)
                if len(tamanho_bytes) != 4: raise ValueError("Pacote cifrado truncado.")
                tamanho = struct.unpack(">I", tamanho_bytes)[0]
                if tamanho > BLOCO or (curto and tamanho): raise ValueError("Bloco cifrado inválido.")
                offset = arquivo.tell()
                dados = arquivo.read(tamanho + 16)
                if len(dados) != tamanho + 16: raise ValueError("Pacote cifrado truncado.")
                idx = struct.pack(">I", indice)
                self.cifra.decrypt(self.cab[-8:] + idx, dados, self.cab + idx + tamanho_bytes)
                if not tamanho:
                    if arquivo.read(1): raise ValueError("Dados após o fim do pacote cifrado.")
                    break
                self.inicios.append(self.total)
                self.blocos.append((offset, tamanho))
                self.total += tamanho
                if self.total > LIMITE: raise ValueError("Pacote excede o limite permitido.")
                curto = tamanho < BLOCO
                indice += 1
        except InvalidTag:
            raise ValueError("Senha incorreta ou pacote cifrado adulterado.") from None

    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.pos

    def seek(self, offset, whence=0):
        pos = offset + (self.pos if whence == 1 else self.total if whence == 2 else 0)
        if whence not in (0, 1, 2) or pos < 0: raise ValueError("Posição inválida no pacote.")
        self.pos = pos
        return pos

    def read(self, tamanho=-1):
        # zipfile pede o diretório central de uma vez; a contagem/manifesto
        # também são limitados pelo consumidor, sem alocar o pacote inteiro.
        if tamanho < 0: tamanho = self.total - self.pos
        if tamanho > MAX_LEITURA: raise ValueError("Estrutura ZIP excede o limite permitido.")
        tamanho = min(tamanho, max(0, self.total - self.pos))
        partes = []
        while tamanho:
            self.cancelar()
            i = bisect.bisect_right(self.inicios, self.pos) - 1
            offset, quantidade = self.blocos[i]
            if self.cache[0] != i:
                self.arquivo.seek(offset)
                idx, n = struct.pack(">I", i), struct.pack(">I", quantidade)
                try: dados = self.cifra.decrypt(self.cab[-8:] + idx, self.arquivo.read(quantidade + 16), self.cab + idx + n)
                except InvalidTag: raise ValueError("Pacote cifrado adulterado.") from None
                self.cache = (i, dados)
            inicio = self.pos - self.inicios[i]
            n = min(tamanho, quantidade - inicio)
            partes.append(self.cache[1][inicio:inicio+n])
            self.pos += n; tamanho -= n
        return b"".join(partes)
