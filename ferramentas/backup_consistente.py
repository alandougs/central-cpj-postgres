#!/usr/bin/env python
"""Backup consistente e restauração segura do workspace CPJ (UN10).

- Bancos SQLite são copiados pela API de backup do SQLite (inclui o conteúdo do
  WAL); `-wal`/`-shm`/`-journal` nunca são copiados "crus".
- A fonte é aberta somente para leitura e nada é apagado nem alterado nela.
- Cada backup vai para uma pasta nova com `manifesto.json` (SHA-256 por arquivo).
- A restauração verifica o manifesto antes de escrever e nunca sobrescreve
  arquivo existente que difira do backup: a versão do backup é gravada em
  `_restauracao/<id-do-backup>/` e o conflito é informado.

Uso:
  python ferramentas/backup_consistente.py backup --origem <workspace> --destino <pasta>
  python ferramentas/backup_consistente.py verificar <pasta-do-backup>
  python ferramentas/backup_consistente.py restaurar <pasta-do-backup> --destino <pasta>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

PASTAS = ("casos", "calibracao", "producao", "modelos", "consulta", "referencias", "config", "usuarios")
EXT_SQLITE = (".sqlite", ".sqlite3", ".db")
SUFIXOS_AUXILIARES = ("-wal", "-shm", "-journal")
IGNORAR_DIRS = {"__pycache__"}
MANIFESTO = "manifesto.json"


class BackupInvalido(Exception):
    """Backup ausente, sem manifesto ou com arquivo adulterado/ausente."""


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for bloco in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloco)
    return h.hexdigest()


def _eh_sqlite(p: Path) -> bool:
    if p.suffix.lower() not in EXT_SQLITE:
        return False
    try:
        with p.open("rb") as f:
            return f.read(16) == b"SQLite format 3\x00"
    except OSError:
        return False


def _auxiliar_sqlite(p: Path) -> bool:
    return p.name.endswith(SUFIXOS_AUXILIARES)


def _copiar_sqlite(origem: Path, destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    src = sqlite3.connect(f"{origem.resolve().as_uri()}?mode=ro", uri=True, timeout=30)
    try:
        dst = sqlite3.connect(destino)
        try:
            src.backup(dst)
            if dst.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise BackupInvalido(f"integrity_check falhou na cópia de {origem.name}")
        finally:
            dst.close()
    finally:
        src.close()


def _arquivos(raiz: Path, pasta: str):
    base = raiz / pasta
    if not base.is_dir():
        return
    for p in sorted(base.rglob("*")):
        if p.is_file() and not IGNORAR_DIRS.intersection(p.relative_to(base).parts):
            yield p


def _novo_id(destino: Path) -> str:
    agora = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    n = 0
    while (destino / f"backup-{agora}{'' if not n else f'-{n}'}").exists():
        n += 1
    return f"backup-{agora}{'' if not n else f'-{n}'}"


def criar_backup(origem: Path, destino: Path, pastas=PASTAS) -> Path:
    origem, destino = Path(origem), Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    bid = _novo_id(destino)
    raiz = destino / bid
    raiz.mkdir()
    arquivos, avisos = {}, []
    for pasta in pastas:
        for p in _arquivos(origem, pasta):
            if _auxiliar_sqlite(p):
                continue
            rel = p.relative_to(origem)
            alvo = raiz / rel
            if _eh_sqlite(p):
                _copiar_sqlite(p, alvo)
                tipo = "sqlite"
            else:
                alvo.parent.mkdir(parents=True, exist_ok=True)
                antes = _sha256(p)
                shutil.copy2(p, alvo)
                if _sha256(alvo) != antes:
                    avisos.append(f"{rel.as_posix()}: alterado durante a cópia")
                tipo = "arquivo"
            arquivos[rel.as_posix()] = {"sha256": _sha256(alvo), "bytes": alvo.stat().st_size, "tipo": tipo}
    manifesto = {"schema": "cpj-backup/1", "id": bid, "criado_em": datetime.now().isoformat(timespec="seconds"),
                 "pastas": list(pastas), "arquivos": arquivos, "avisos": avisos}
    (raiz / MANIFESTO).write_text(json.dumps(manifesto, ensure_ascii=False, indent=1), encoding="utf-8")
    return raiz


def _ler_manifesto(backup: Path) -> dict:
    m = Path(backup) / MANIFESTO
    if not m.is_file():
        raise BackupInvalido(f"manifesto ausente em {backup}")
    return json.loads(m.read_text(encoding="utf-8"))


def verificar_backup(backup: Path) -> list[str]:
    """Lista de problemas; vazia quando o backup confere com o manifesto."""
    backup = Path(backup)
    try:
        man = _ler_manifesto(backup)
    except (BackupInvalido, ValueError) as e:
        return [str(e)]
    problemas = []
    for rel, info in man["arquivos"].items():
        p = backup / rel
        if not p.is_file():
            problemas.append(f"{rel}: ausente")
        elif _sha256(p) != info["sha256"]:
            problemas.append(f"{rel}: hash divergente")
        elif info.get("tipo") == "sqlite":
            con = sqlite3.connect(f"{p.resolve().as_uri()}?mode=ro", uri=True)
            try:
                if con.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    problemas.append(f"{rel}: integrity_check falhou")
            finally:
                con.close()
    return problemas


def restaurar(backup: Path, destino: Path) -> dict:
    backup, destino = Path(backup), Path(destino)
    problemas = verificar_backup(backup)
    if problemas:
        raise BackupInvalido("; ".join(problemas))
    man = _ler_manifesto(backup)
    restaurados, iguais, conflitos = [], [], []
    for rel, info in man["arquivos"].items():
        origem, alvo = backup / rel, destino / rel
        if alvo.exists():
            if _sha256(alvo) == info["sha256"]:
                iguais.append(rel)
                continue
            copia = destino / "_restauracao" / man["id"] / rel
            copia.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(origem, copia)
            conflitos.append({"arquivo": rel, "copia_backup": str(copia)})
            continue
        alvo.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origem, alvo)
        restaurados.append(rel)
    return {"backup": man["id"], "restaurados": restaurados, "iguais": iguais, "conflitos": conflitos}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("backup")
    b.add_argument("--origem", required=True)
    b.add_argument("--destino", required=True)
    v = sub.add_parser("verificar")
    v.add_argument("backup")
    r = sub.add_parser("restaurar")
    r.add_argument("backup")
    r.add_argument("--destino", required=True)
    a = ap.parse_args(argv)
    try:
        if a.cmd == "backup":
            print(criar_backup(Path(a.origem), Path(a.destino)))
        elif a.cmd == "verificar":
            problemas = verificar_backup(Path(a.backup))
            print("\n".join(problemas) if problemas else "ok")
            return 1 if problemas else 0
        else:
            print(json.dumps(restaurar(Path(a.backup), Path(a.destino)), ensure_ascii=False, indent=1))
    except BackupInvalido as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
