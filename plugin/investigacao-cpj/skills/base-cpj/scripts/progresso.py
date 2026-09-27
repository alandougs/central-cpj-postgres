#!/usr/bin/env python3
"""Registra o progresso de uma tarefa de IA do caso (lido pela Central CPJ para a barra de progresso).
Uso: progresso.py <ID> <percentual 0-100> "<etapa>"
"""
import datetime, json, os, sys

WS = os.environ.get("CPJ_WORKSPACE", r"C:\CPJ - TRABALHO")
if len(sys.argv) < 4: raise SystemExit('Uso: progresso.py <ID> <percentual> "<etapa>"')
id_, pct, etapa = sys.argv[1], max(0, min(100, int(float(sys.argv[2])))), " ".join(sys.argv[3:])
d = os.path.join(WS, "casos", id_)
if not os.path.isdir(d): raise SystemExit(f"Caso inexistente: {id_}")
p = os.path.join(d, "ia-progresso.json")
json.dump({"pct": pct, "etapa": etapa, "ts": datetime.datetime.now().isoformat(timespec="seconds")},
          open(p, "w", encoding="utf-8"), ensure_ascii=False)
print(f"{id_}: {pct}% — {etapa}")
