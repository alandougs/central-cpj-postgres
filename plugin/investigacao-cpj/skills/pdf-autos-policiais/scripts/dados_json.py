#!/usr/bin/env python3
"""Consolida os derivados da extração em dados_extraidos.json rastreável.

Uso: dados_json.py pasta-da-extracao
"""
import csv
import datetime
import json
import os
import re
import sys
from pathlib import Path


def ler_json(caminho):
    try:
        with caminho.open(encoding="utf-8") as arquivo:
            valor = json.load(arquivo)
        return valor if isinstance(valor, dict) else {}
    except (OSError, ValueError):
        return {}


def ler_paginas(caminho):
    if not caminho.is_file():
        return []
    paginas, atual, linhas = [], None, []

    def concluir():
        if atual is not None:
            paginas.append({
                "pagina_pdf": atual["pagina_pdf"],
                "metodo": atual["metodo"],
                "texto": "\n".join(linhas).strip(),
            })

    for linha in caminho.read_text(encoding="utf-8").splitlines():
        cabecalho = re.match(r"##\s*P[áa]gina\s+(\d+)\s*$", linha)
        if cabecalho:
            concluir()
            atual = {"pagina_pdf": int(cabecalho.group(1)), "metodo": ""}
            linhas = []
            continue
        if atual is None or linha == "---":
            continue
        metodo = re.fullmatch(r"<!--\s*método:\s*([^|>]+)(?:\|.*)?-->", linha.strip())
        if metodo:
            atual["metodo"] = metodo.group(1).strip()
            continue
        linhas.append(linha)
    concluir()
    return paginas


def ler_csv(caminho):
    try:
        with caminho.open(newline="", encoding="utf-8-sig") as arquivo:
            return list(csv.DictReader(arquivo, delimiter=";"))
    except (OSError, csv.Error):
        return []


def ler_tabelas(pasta):
    diretorio = pasta / "tabelas"
    if not diretorio.is_dir():
        return []
    resultado = []
    for caminho in sorted(diretorio.glob("*.csv")):
        if caminho.name.casefold() == "indice_tabelas.csv":
            continue
        linhas = ler_csv(caminho)
        pagina = None
        if linhas:
            valor = linhas[0].get("pagina_pdf", "")
            pagina = int(valor) if valor.isdigit() else valor or None
        resultado.append({"arquivo": caminho.name, "pagina_pdf": pagina, "linhas": linhas})
    return resultado


def gravar_json(caminho, dados):
    temporario = caminho.with_suffix(caminho.suffix + ".tmp")
    with temporario.open("w", encoding="utf-8") as arquivo:
        json.dump(dados, arquivo, ensure_ascii=False, indent=2)
        arquivo.write("\n")
    os.replace(temporario, caminho)


def main(argv):
    if len(argv) != 2:
        raise SystemExit("Uso: dados_json.py pasta-da-extracao")
    pasta = Path(argv[1])
    if not pasta.is_dir():
        raise SystemExit(f"Pasta de extração inexistente: {pasta}")
    dados = {
        "schema": "cpj-dados-extraidos/1",
        "gerado_em": datetime.datetime.now().isoformat(timespec="seconds"),
        "extracao": ler_json(pasta / "relatorio_extracao.json"),
        "paginas": ler_paginas(pasta / "transcricao.md"),
        "tabelas": ler_tabelas(pasta),
        "entidades": ler_csv(pasta / "entidades.csv"),
    }
    destino = pasta / "dados_extraidos.json"
    gravar_json(destino, dados)
    print(f"{len(dados['paginas'])} página(s), {len(dados['tabelas'])} tabela(s), "
          f"{len(dados['entidades'])} entidade(s) -> {destino}")


if __name__ == "__main__":
    main(sys.argv)
