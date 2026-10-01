#!/usr/bin/env python3
"""Varre transcricao.md e lista candidatos a dados críticos com a página de origem.
Uso: entidades.py extracao/transcricao.md  -> gera entidades.csv na mesma pasta.
São CANDIDATOS por padrão de texto: conferir cada um na imagem da página antes de usar.
"""
import csv, os, re, sys

PADROES = {
    "CPF": r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b",
    "CNPJ": r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b",
    "PLACA": r"\b[A-Z]{3}-?\d[A-Z0-9]\d{2}\b",
    "TELEFONE": r"\(?\b\d{2}\)?\s?9?\d{4}-?\d{4}\b",
    "VALOR": r"R\$\s?\d{1,3}(?:\.\d{3})*(?:,\d{2})?",
    "DATA": r"\b\d{2}/\d{2}/\d{2,4}\b",
    "EMAIL": r"\b[\w.+-]+@[\w-]+\.[\w.]+\b",
    "FLS": r"\bfls?\.?\s*(\d{1,5})\b",
    "IMEI": r"\b\d{15}\b",
    "CHASSI": r"\b(?=[A-HJ-NPR-Z0-9]*[A-HJ-NPR-Z])[A-HJ-NPR-Z0-9]{17}\b",  # VIN: exige ao menos 1 letra (sem I/O/Q)
}
arq = sys.argv[1]
linhas, pag = [], None
for ln in open(arq, encoding="utf-8"):
    m = re.match(r"## Página (\d+)", ln)
    if m: pag = int(m.group(1)); continue
    if pag is None or ln.startswith("<!--"): continue
    for tipo, rx in PADROES.items():
        for achado in re.finditer(rx, ln, flags=re.I if tipo in ("FLS", "CHASSI") else 0):
            valor = achado.group(1) if tipo == "FLS" else achado.group(0)
            if tipo == "TELEFONE" and re.fullmatch(PADROES["CPF"], valor): continue
            linhas.append({"tipo": tipo, "valor": valor.strip(), "pagina_pdf": pag,
                           "trecho": ln.strip()[:160], "status": "pendente de conferência"})
saida = os.path.join(os.path.dirname(arq), "entidades.csv")
with open(saida, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=["tipo", "valor", "pagina_pdf", "trecho", "status"], delimiter=";")
    w.writeheader(); w.writerows(linhas)
from collections import Counter
print(f"{len(linhas)} candidatos -> {saida}")
print(dict(Counter(l["tipo"] for l in linhas)))
