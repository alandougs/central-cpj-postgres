#!/usr/bin/env python
"""Importa casos existentes em JSON para o PostgreSQL principal.

Nao apaga nem altera os arquivos locais. A operacao e idempotente.

Uso:
    python ferramentas/migrar-json-postgres.py
    python ferramentas/migrar-json-postgres.py --dry-run
"""
import argparse
import json
import os
import sys
from pathlib import Path


RAIZ = Path(__file__).resolve().parent.parent
APP = RAIZ / "plugin" / "investigacao-cpj" / "app"
sys.path.insert(0, str(APP))
from db import Database  # noqa: E402


def casos(workspace):
    raiz = Path(workspace) / "casos"
    for arquivo in sorted(raiz.glob("*/caso.json")):
        if arquivo.parent.name.startswith("_"):
            continue
        try:
            yield arquivo, json.loads(arquivo.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Caso invalido: {arquivo} ({exc})") from exc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", default=os.environ.get("CPJ_WORKSPACE", str(RAIZ)))
    parser.add_argument("--dry-run", action="store_true", help="Lista os casos sem conectar ou gravar")
    args = parser.parse_args()
    encontrados = list(casos(args.workspace))
    print(f"Casos encontrados: {len(encontrados)}")
    for arquivo, case in encontrados:
        print(f"- {case.get('id') or arquivo.parent.name}: {arquivo}")
    if args.dry_run or not encontrados:
        return 0
    db = Database()
    if not db.health():
        raise RuntimeError("PostgreSQL nao respondeu")
    for _, case in encontrados:
        db.upsert_case(case)
    print(f"Casos sincronizados no PostgreSQL: {len(encontrados)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        raise SystemExit(1)
