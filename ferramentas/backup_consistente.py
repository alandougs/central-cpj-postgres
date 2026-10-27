"""Snapshots locais versionados; nunca espelha exclusões nem restaura sobre dados.

Uso: python ferramentas/backup_consistente.py criar --origem WORKSPACE
 --destino MIDIA --offline --midia-protegida
Restaurar: ... restaurar --snapshot SNAPSHOT --destino PASTA_NOVA --midia-protegida
Verificar: ... verificar --snapshot SNAPSHOT

Pare Central, agentes, editores e outros escritores ANTES de --offline. A opção
é declaração do operador: não pausa processos. Inventários SHA-256 antes/depois
detectam alterações durante a cópia e abortam. Sem escritores parados não há
garantia transacional entre arquivos/bancos; SQLite usa a API de backup e inclui
WAL confirmado. A mídia deve ser autorizada e cifrada/protegida pelo órgão
(ex.: BitLocker desbloqueado somente durante a cópia); ACL não cifra mídia.
Nenhum snapshot antigo é apagado. Interrupção pode deixar .parcial protegido:
nunca o restaure; repita a cópia e remova-o manualmente após conferência.
"""
import argparse
from contextlib import closing
import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import sqlite3
import subprocess
import tempfile
import time
import uuid
import sys

# Mesmo contrato de proteção da Central, sem inicializar servidor ou agentes.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "plugin/investigacao-cpj/app"))
import seguranca_local as SEGURANCA

EXCLUIR = {".git", ".venv", "__pycache__", ".pytest_cache", "node_modules", "exportacoes", ".parcial"}


def _proteger(pasta):
    pasta.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name == "nt":
        import ctypes
        volume = ctypes.create_unicode_buffer(261)
        flags = ctypes.c_ulong()
        if not ctypes.windll.kernel32.GetVolumePathNameW(str(pasta.resolve()), volume, len(volume)) or not ctypes.windll.kernel32.GetVolumeInformationW(volume.value, None, 0, None, None, ctypes.byref(flags), None, 0):
            raise ValueError("Não foi possível verificar o sistema de arquivos do destino.")
        # Mídia cifrada/protegida foi declarada pelo operador; exFAT não tem ACL.
        if not flags.value & 8: return False
        # SID evita problemas com contas contendo espaço/domínio localizado.
        import csv
        sid = next(csv.reader([subprocess.check_output(["whoami", "/user", "/fo", "csv", "/nh"], text=True).strip()]))[1]
        r = subprocess.run(["icacls", str(pasta), "/inheritance:r", "/grant:r", f"*{sid}:(OI)(CI)F", "*S-1-5-18:(OI)(CI)F"], capture_output=True,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if r.returncode: raise ValueError("Não foi possível proteger a pasta de backup/restauração.")
    else: pasta.chmod(0o700)
    return True


def _sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024**2), b""): h.update(b)
    return h.hexdigest()


def _inventario(raiz):
    itens = {}
    for pasta, dirs, nomes in os.walk(raiz, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUIR)
        for nome in dirs + nomes:
            p = Path(pasta) / nome
            if p.is_symlink() or getattr(p, "is_junction", lambda: False)():
                raise ValueError("Backup não aceita links ou junções.")
        for nome in sorted(nomes):
            if nome.endswith(("-shm", ".pyc")) or nome.startswith("~$"): continue
            if nome == ".caso.lock": raise ValueError("Há caso reservado/em alteração; pare os escritores antes do backup.")
            p = Path(pasta) / nome
            st = p.stat()
            itens[p.relative_to(raiz).as_posix()] = {"tamanho": st.st_size, "mtime_ns": st.st_mtime_ns, "sha256": _sha(p)}
    return itens


def _sqlite(path):
    with path.open("rb") as f: return f.read(16) == b"SQLite format 3\x00"


def _integridade_sqlite(path):
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)) as c:
        if c.execute("pragma integrity_check").fetchall() != [("ok",)]:
            raise ValueError("Banco SQLite com falha de integridade.")


def criar_snapshot(origem, destino, *, offline=False, midia_protegida=False):
    if not offline or not midia_protegida:
        raise ValueError("Pare todos os escritores e confirme --offline e --midia-protegida (mídia autorizada/cifrada).")
    origem, destino = Path(origem).resolve(), Path(destino).resolve()
    if not origem.is_dir(): raise ValueError("Origem inexistente.")
    if destino == origem or origem in destino.parents: raise ValueError("Destino deve ficar fora da origem.")
    acl = _proteger(destino)
    antes = _inventario(origem)
    auditoria = SEGURANCA.exportar_estado_auditoria(origem)
    nome = "CPJ-" + datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid.uuid4().hex[:12]
    parcial, final = destino / (".parcial-" + nome), destino / nome
    _proteger(parcial)
    try:
        dados = parcial / "dados"
        dados.mkdir()
        arquivos = []
        bancos = {r for r in antes if _sqlite(origem / r)}
        for r, meta in antes.items():
            if any(r == db + sufixo for db in bancos for sufixo in ("-wal", "-shm", "-journal")): continue
            fonte, alvo = origem / r, dados / r
            alvo.parent.mkdir(parents=True, exist_ok=True)
            banco = r in bancos
            if banco:
                inicio = time.monotonic()
                def progresso(status, restantes, total):
                    if time.monotonic() - inicio > 60: raise ValueError("Banco ocupado; backup abortado sem publicar snapshot.")
                with closing(sqlite3.connect(fonte.as_uri() + "?mode=ro", uri=True, timeout=5)) as src, closing(sqlite3.connect(alvo)) as dst:
                    src.backup(dst, pages=256, progress=progresso, sleep=0.05)
                    dst.execute("pragma journal_mode=delete")
                _integridade_sqlite(alvo)
            else:
                shutil.copy2(fonte, alvo)
                if _sha(alvo) != meta["sha256"]: raise ValueError("Fonte mudou durante a cópia; snapshot descartado.")
            arquivos.append({"caminho": r, "tamanho": alvo.stat().st_size, "sha256": _sha(alvo), "sqlite": banco})
        if antes != _inventario(origem): raise ValueError("Fonte mudou durante o backup; pare os escritores e repita.")
        if auditoria != SEGURANCA.exportar_estado_auditoria(origem): raise ValueError("Âncora de auditoria mudou durante o backup; repita offline.")
        manifesto = {"schema": "cpj-backup/1", "gerado_em": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                     "consistencia": "offline declarado; inventários SHA-256 estáveis; SQLite backup API",
                     "protecao": {"midia_protegida": "declarada pelo operador; não verificada pelo script", "acl_aplicada": acl,
                                  "portabilidade": "DPAPI exige a mesma conta e máquina Windows; outra conta falha sem reiniciar cadeia."},
                     "auditoria": auditoria, "arquivos": arquivos}
        (parcial / "manifest.json").write_text(json.dumps(manifesto, ensure_ascii=False, indent=2), encoding="utf-8")
        verificar_snapshot(parcial)
        parcial.rename(final)
        return final
    finally:
        if parcial.exists(): shutil.rmtree(parcial)


def verificar_snapshot(snapshot):
    snapshot = Path(snapshot).resolve()
    man = json.loads((snapshot / "manifest.json").read_text(encoding="utf-8"))
    if man.get("schema") != "cpj-backup/1" or not isinstance(man.get("arquivos"), list): raise ValueError("Manifesto de backup inválido.")
    esperados = set()
    for a in man["arquivos"]:
        r = a.get("caminho", "")
        partes = PurePosixPath(r).parts
        if not r or "\\" in r or ":" in r or r.startswith("/") or any(p in (".", "..") for p in r.split("/")) or r in esperados:
            raise ValueError("Caminho inválido no backup.")
        esperados.add(r)
        p = snapshot / "dados" / Path(*partes)
        if p.is_symlink() or not p.resolve().is_relative_to(snapshot / "dados") or not p.is_file(): raise ValueError("Caminho inválido no backup.")
        if p.stat().st_size != a["tamanho"] or _sha(p) != a["sha256"]: raise ValueError("Backup com falha de integridade.")
        if a.get("sqlite"): _integridade_sqlite(p)
    reais = set(_inventario(snapshot / "dados"))
    if reais != esperados: raise ValueError("Arquivos fora do manifesto do backup.")
    return man


def restaurar_snapshot(snapshot, destino, *, midia_protegida=False):
    if not midia_protegida: raise ValueError("Confirme mídia autorizada e protegida para restaurar.")
    snapshot, destino = Path(snapshot).resolve(), Path(destino).absolute()
    # Nunca sobrepor nem mesclar estado posterior, mesmo com flag --force.
    if destino.exists() or destino.is_symlink(): raise ValueError("Restaure somente em pasta NOVA; destino existente pode conter dados mais novos.")
    man = verificar_snapshot(snapshot)
    destino.parent.mkdir(parents=True, exist_ok=True)
    parcial = Path(tempfile.mkdtemp(prefix=".cpj-restore-", dir=destino.parent))
    try:
        _proteger(parcial)
        for a in man["arquivos"]:
            fonte, alvo = snapshot / "dados" / a["caminho"], parcial / a["caminho"]
            alvo.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(fonte, alvo)
            if _sha(alvo) != a["sha256"]: raise ValueError("Integridade divergente na restauração.")
            if a.get("sqlite"): _integridade_sqlite(alvo)
        if destino.exists(): raise ValueError("Destino foi criado durante a restauração; operação abortada.")
        if "auditoria" not in man: raise ValueError("Backup sem estado protegido da auditoria; restauração automática recusada.")
        SEGURANCA.restaurar_estado_auditoria(destino, man["auditoria"], ws_validacao=parcial)
        parcial.rename(destino)
        return destino
    finally:
        if parcial.exists(): shutil.rmtree(parcial)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="acao", required=True)
    criar = sub.add_parser("criar")
    criar.add_argument("--origem", required=True); criar.add_argument("--destino", required=True)
    criar.add_argument("--offline", action="store_true"); criar.add_argument("--midia-protegida", action="store_true")
    verificar = sub.add_parser("verificar"); verificar.add_argument("--snapshot", required=True)
    restaurar = sub.add_parser("restaurar")
    restaurar.add_argument("--snapshot", required=True); restaurar.add_argument("--destino", required=True)
    restaurar.add_argument("--midia-protegida", action="store_true")
    args = p.parse_args()
    try:
        if args.acao == "criar": print(criar_snapshot(args.origem, args.destino, offline=args.offline, midia_protegida=args.midia_protegida))
        elif args.acao == "verificar": verificar_snapshot(args.snapshot); print("Integridade verificada.")
        else: print(restaurar_snapshot(args.snapshot, args.destino, midia_protegida=args.midia_protegida))
        return 0
    except (ValueError, OSError, sqlite3.Error) as e:
        print(str(e), file=__import__("sys").stderr); return 1


if __name__ == "__main__": raise SystemExit(main())
