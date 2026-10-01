#!/usr/bin/env python3
"""Registra o progresso de uma tarefa de IA do caso (lido pela Central CPJ para a barra de progresso).
Uso: progresso.py <ID> <percentual 0-100> "<etapa>"
"""
import datetime, json, os, sys

def ws_padrao():
    """Workspace CPJ: CPJ_WORKSPACE > 1ª pasta acima deste script com casos/ e modelos/ > cwd com casos/ > erro."""
    if os.environ.get("CPJ_WORKSPACE"):
        return os.environ["CPJ_WORKSPACE"]
    d = os.path.dirname(os.path.abspath(__file__))
    while True:
        if os.path.isdir(os.path.join(d, "casos")) and os.path.isdir(os.path.join(d, "modelos")):
            return d
        if os.path.dirname(d) == d:
            break
        d = os.path.dirname(d)
    if os.path.isdir(os.path.join(os.getcwd(), "casos")):
        return os.getcwd()
    raise SystemExit("Workspace CPJ não encontrado: defina CPJ_WORKSPACE ou execute a partir da pasta do workspace "
                     "(a que contém as pastas casos e modelos).")


WS = ws_padrao()
if len(sys.argv) < 4: raise SystemExit('Uso: progresso.py <ID> <percentual> "<etapa>"')
id_, pct, etapa = sys.argv[1], max(0, min(100, int(float(sys.argv[2])))), " ".join(sys.argv[3:])
d = os.path.join(WS, "casos", id_)
if not os.path.isdir(d): raise SystemExit(f"Caso inexistente: {id_}")
p = os.path.join(d, "ia-progresso.json")
json.dump({"pct": pct, "etapa": etapa, "ts": datetime.datetime.now().isoformat(timespec="seconds")},
          open(p, "w", encoding="utf-8"), ensure_ascii=False)
print(f"{id_}: {pct}% — {etapa}")
