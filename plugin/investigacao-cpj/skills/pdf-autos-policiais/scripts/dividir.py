#!/usr/bin/env python3
"""Divide PDF em partes de até N páginas (ou em cortes informados) e gera manifesto com SHA-256.
Uso: dividir.py arquivo.pdf [--max 100] [--cortes "1-95,96-190,191-230"] [--saida pasta]
"""
import argparse, hashlib, json, os, datetime
from pypdf import PdfReader, PdfWriter

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()

ap = argparse.ArgumentParser()
ap.add_argument("pdf"); ap.add_argument("--max", type=int, default=100)
ap.add_argument("--cortes", default=""); ap.add_argument("--saida", default="partes")
a = ap.parse_args()

r = PdfReader(a.pdf); n = len(r.pages)
if a.cortes:
    faixas = [tuple(map(int, x.split("-"))) for x in a.cortes.replace(" ", "").split(",")]
else:
    faixas = [(i, min(i + a.max - 1, n)) for i in range(1, n + 1, a.max)]
cobertas = sorted(p for ini, fim in faixas for p in range(ini, fim + 1))
if cobertas != list(range(1, n + 1)):
    raise SystemExit("ERRO: os cortes não cobrem todas as páginas exatamente uma vez.")
if any(fim - ini + 1 > 100 for ini, fim in faixas):
    print("AVISO: há parte com mais de 100 páginas; no Claude.ai ela será lida só como texto.")

os.makedirs(a.saida, exist_ok=True)
base = os.path.splitext(os.path.basename(a.pdf))[0]
man = {"original": os.path.basename(a.pdf), "sha256_original": sha(a.pdf), "paginas": n,
       "gerado_em": datetime.datetime.now().isoformat(timespec="seconds"),
       "ferramenta": "pypdf (cópia de páginas, sem recompressão)", "partes": []}
tot = len(faixas)
for k, (ini, fim) in enumerate(faixas, 1):
    w = PdfWriter()
    for p in range(ini - 1, fim): w.add_page(r.pages[p])
    nome = f"{base}_parte{k:02d}de{tot:02d}_pags{ini:04d}-{fim:04d}.pdf"
    caminho = os.path.join(a.saida, nome)
    with open(caminho, "wb") as f: w.write(f)
    mb = os.path.getsize(caminho) / 1_048_576
    man["partes"].append({"arquivo": nome, "paginas_do_original": f"{ini}-{fim}",
                          "qtd": fim - ini + 1, "tamanho_mb": round(mb, 1), "sha256": sha(caminho)})
    if mb > 30: print(f"AVISO: {nome} tem {mb:.1f} MB (limite de 30 MB para arquivos de Projeto).")

with open(os.path.join(a.saida, "MANIFESTO.json"), "w", encoding="utf-8") as f:
    json.dump(man, f, ensure_ascii=False, indent=2)
print(json.dumps(man, ensure_ascii=False, indent=2))
