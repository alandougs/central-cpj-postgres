#!/usr/bin/env python3
"""RV06 (governança, regra 7): /calibrar não grava em calibracao/ e nenhum ID de caso real consta de calibracao/.
O comportamento da proposta/aprovação em servidor isolado é coberto por teste_calibracao_final_copilot.py (K01)."""
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
falhas = []


def ok(cond, msg):
    print(("OK   " if cond else "FALHA ") + msg)
    if not cond:
        falhas.append(msg)


def ler(*partes):
    p = os.path.join(RAIZ, *partes)
    if not os.path.isfile(p):
        return ""
    with open(p, encoding="utf-8") as f:
        return f.read()


rota = ler("plugin", "investigacao-cpj", "app", "rotas", "casos.py")
i = rota.index('"/api/casos/<id_>/calibrar")')
j = rota.index('"/api/casos/<id_>/calibrar/aprovar")')
proposta = rota[i:j]
ok("registrar(" not in proposta and "open(" not in proposta.replace("open(os.path.join(pasta_rel", ""),
   "a rota de proposta não grava arquivo nenhum")
ok("licoes-aprendidas" not in proposta and "historico-calibracao" not in proposta, "a rota de proposta não toca em calibracao/")
ok('"gravado": False' in proposta, "a resposta da proposta declara gravado=False")
ok("_calibrador().registrar(" in rota[j:], "só a rota de aprovação grava (por id de lição)")

pasta_casos = os.path.join(RAIZ, "casos")
ids_reais = [d for d in os.listdir(pasta_casos) if re.match(r"OS-.*\d", d) and not d.startswith("_")] if os.path.isdir(pasta_casos) else []
calib = ler("calibracao", "licoes-aprendidas.md") + ler("calibracao", "historico-calibracao.md")
vazados = [d for d in ids_reais if d in calib]
ok(not vazados, f"nenhum ID de caso real em calibracao/ ({len(ids_reais)} casos conferidos)" + (f": {vazados}" if vazados else ""))

print("TUDO OK" if not falhas else f"{len(falhas)} FALHA(S)")
sys.exit(1 if falhas else 0)
