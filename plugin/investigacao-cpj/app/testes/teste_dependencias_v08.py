#!/usr/bin/env python3
"""V08/RV05: manifestos de dependências e verificar-ambiente.ps1 lendo o requirements.txt. Sem rede."""
import os
import re
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
falhas = []


def ok(cond, msg):
    print(("OK   " if cond else "FALHA ") + msg)
    if not cond:
        falhas.append(msg)


def ler(rel):
    with open(os.path.join(RAIZ, rel), encoding="utf-8") as f:
        return f.read()


def pacotes(txt):
    return [re.split(r"[\[<>=!~; ]", ln.strip())[0].lower() for ln in txt.splitlines()
            if ln.strip() and not ln.strip().startswith(("#", "-"))]


base, dev, opc = ler("requirements.txt"), ler("requirements-dev.txt"), ler("requirements-opcional.txt")
ok("psycopg" not in base.lower(), "psycopg fora do requirements.txt (Postgres congelado)")
ok("psycopg" in opc.lower(), "psycopg em requirements-opcional.txt")
ok("-r requirements.txt" in dev and "playwright" in dev.lower(), "requirements-dev.txt inclui a base e o Playwright")
ok(len(pacotes(base)) >= 9 and "flask" in pacotes(base), "requirements.txt lista as dependências de execução")
ok(all(re.search(r"[<>=]", ln) for ln in base.splitlines() if ln.strip() and not ln.startswith("#")),
   "todas as dependências da base têm faixa de versão")

ps = ler("ferramentas/verificar-ambiente.ps1")
ok("Get-Content -LiteralPath $req" in ps, "verificar-ambiente.ps1 lê o requirements.txt")
ok("$modulos = @(" not in ps, "sem lista fixa de módulos no verificar-ambiente.ps1")
ok("'pillow' = 'PIL'" in ps and "'python-docx' = 'docx'" in ps, "mapa pacote -> módulo cobre pillow e python-docx")

# cada pacote da base é importável com o mapa usado no script
mapa = {"pillow": "PIL", "python-docx": "docx"}
falt = []
for p in pacotes(base):
    mod = mapa.get(p, p.replace("-", "_"))
    if subprocess.run([sys.executable, "-c", f"import {mod}"], capture_output=True).returncode:
        falt.append(p)
ok(not falt, "pacotes do requirements.txt importáveis neste ambiente" + (f" (faltam: {falt})" if falt else ""))

print("TUDO OK" if not falhas else f"{len(falhas)} FALHA(S)")
sys.exit(1 if falhas else 0)
