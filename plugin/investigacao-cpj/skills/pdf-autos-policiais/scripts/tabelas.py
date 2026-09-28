#!/usr/bin/env python3
"""Extrai tabelas para CSV com rastreabilidade de página.

Uso:
  tabelas.py arquivo.pdf  [--saida pasta]   -> tabelas das páginas digitais (pdfplumber)
  tabelas.py arquivo.md   [--saida pasta]   -> tabelas Markdown de uma transcrição (## Página N)

Saída em <saida>/tabelas/: um CSV por tabela (tNNN_pagPPPP.csv, separador ';', UTF-8 com BOM
para abrir no Excel) + indice_tabelas.csv. Toda célula é transcrição provisória: conferir
valores, sinais e datas contra a imagem da página antes de usar.
"""
import argparse, csv, os, re, sys

ap = argparse.ArgumentParser()
ap.add_argument("arquivo"); ap.add_argument("--saida", default=None)
a = ap.parse_args()

saida = a.saida or os.path.dirname(os.path.abspath(a.arquivo))
dir_t = os.path.join(saida, "tabelas"); os.makedirs(dir_t, exist_ok=True)
tabelas = []  # (pagina, origem, linhas)


def normalizar_linhas(linhas):
    normalizadas = [
        [re.sub(r"\s+", " ", (celula or "").replace("\n", " ")).strip() for celula in linha]
        for linha in linhas
    ]
    normalizadas = [linha for linha in normalizadas if any(linha)]
    if not normalizadas:
        return []

    cabecalho = normalizadas[0]
    coluna_descricao = next(
        (i for i, valor in enumerate(cabecalho)
         if re.search(r"hist[oó]rico|descri[cç][aã]o|lan[cç]amento|detalhe", valor, re.I)),
        None,
    )
    if coluna_descricao is None:
        return normalizadas

    resultado = [cabecalho]
    for linha in normalizadas[1:]:
        continuacao = (
            resultado
            and coluna_descricao < len(linha)
            and linha[coluna_descricao]
            and all(not valor for i, valor in enumerate(linha) if i != coluna_descricao)
        )
        if continuacao:
            anterior = resultado[-1]
            while len(anterior) < len(linha):
                anterior.append("")
            anterior[coluna_descricao] = f"{anterior[coluna_descricao]} {linha[coluna_descricao]}".strip()
        else:
            resultado.append(linha)
    return resultado


def de_pdf(caminho):
    try:
        import pdfplumber
    except ImportError:
        raise SystemExit("pdfplumber ausente: python -m pip install pdfplumber")
    with pdfplumber.open(caminho) as pdf:
        for i, pg in enumerate(pdf.pages, 1):
            extraidas = pg.extract_tables() or []
            origem = "pdfplumber (camada de texto)"
            if not extraidas:
                extraidas = pg.extract_tables(table_settings={
                    "vertical_strategy": "text",
                    "horizontal_strategy": "text",
                    "min_words_vertical": 2,
                    "text_x_tolerance": 1,
                    "text_y_tolerance": 5,
                }) or []
                origem = "pdfplumber (colunas alinhadas, sem bordas)"
            for t in extraidas:
                linhas = normalizar_linhas(t)
                if len(linhas) >= 2 and any(any(c for c in ln) for ln in linhas):
                    tabelas.append((i, origem, linhas))


def de_markdown(caminho):
    pag, bloco = None, []

    def fecha():
        if len(bloco) >= 2:
            linhas = [[c.strip() for c in ln.strip().strip("|").split("|")] for ln in bloco
                      if not re.fullmatch(r"\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?", ln.strip())]
            if linhas:
                tabelas.append((pag, "tabela markdown da transcrição", linhas))
        bloco.clear()

    for ln in open(caminho, encoding="utf-8"):
        m = re.match(r"##\s*P[áa]gina\s+(\d+)", ln)
        if m:
            fecha(); pag = int(m.group(1)); continue
        if ln.lstrip().startswith("|"):
            bloco.append(ln.rstrip("\n"))
        else:
            fecha()
    fecha()


if a.arquivo.lower().endswith(".pdf"):
    de_pdf(a.arquivo)
else:
    de_markdown(a.arquivo)

indice = []
for k, (pag, origem, linhas) in enumerate(tabelas, 1):
    nome = f"t{k:03d}_pag{(pag or 0):04d}.csv"
    with open(os.path.join(dir_t, nome), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["pagina_pdf"] + [f"col{j+1}" for j in range(max(len(x) for x in linhas))])
        for ln in linhas:
            w.writerow([pag if pag is not None else ""] + ln)
    indice.append({"arquivo": nome, "pagina_pdf": pag if pag is not None else "",
                   "linhas": len(linhas), "colunas": max(len(x) for x in linhas),
                   "cabecalho_provavel": " | ".join(linhas[0])[:200], "origem": origem,
                   "status": "pendente de conferência"})

with open(os.path.join(dir_t, "indice_tabelas.csv"), "w", newline="", encoding="utf-8-sig") as f:
    campos = ["arquivo", "pagina_pdf", "linhas", "colunas", "cabecalho_provavel", "origem", "status"]
    w = csv.DictWriter(f, fieldnames=campos, delimiter=";"); w.writeheader(); w.writerows(indice)

print(f"{len(indice)} tabela(s) -> {dir_t}")
for t in indice:
    print(f"  {t['arquivo']}: pág. {t['pagina_pdf']}, {t['linhas']}x{t['colunas']} — {t['cabecalho_provavel'][:80]}")
if not indice and a.arquivo.lower().endswith(".pdf"):
    print("Nenhuma tabela na camada de texto. Em páginas escaneadas, transcreva a tabela em Markdown "
          "(transcrição visual) e rode este script sobre o transcricao.md.")
