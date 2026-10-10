"""Produz normalização conservadora por página sem escrever na transcrição fonte."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

PAGINA = re.compile(r"^## Página (\d+)\s*$")
COMPLEMENTOS = {"[OCR da imagem da página]", "[Transcrição visual complementar]"}
FINANCEIRO = re.compile(r"\b(pix|conta|valor|saldo|transfer\w*|dep[oó]s\w*|saque|cr[eé]dito|d[eé]bito|pagamento|lan[cç]amento|extrato|banco|devolu[cç][aã]o|preju[ií]zo|reais|dinheiro)\b|R\$", re.I)
CARIMBO = re.compile(r"^(carimbo\s*:|documento assinado|assinado digitalmente|assinatura digital)", re.I)
PALAVRA = r"[^\W\d_]"


def protegida(linha):
    return (any(c.isdigit() for c in linha) or "|" in linha or "\t" in linha
            or "  " in linha or bool(FINANCEIRO.search(linha))
            or linha.startswith(("#", "<!--", "[", "---", "```", "~~~")))


def normalizar(texto):
    linhas = texto.splitlines()
    saida, alteracoes, paginas = [], [], []
    pagina, complemento, bloco = None, False, False
    nativas, carimbos = set(), set()
    i = 0
    while i < len(linhas):
        linha = linhas[i]
        marca = PAGINA.fullmatch(linha)
        if marca:
            pagina = int(marca[1]); paginas.append(pagina)
            complemento, bloco = False, False
            nativas, carimbos = set(), set()
        if linha.startswith(("```", "~~~")):
            bloco = not bloco
        regra, usadas = None, [i + 1]
        if pagina is not None and not bloco:
            if linha in COMPLEMENTOS:
                complemento = True
            elif not linha.strip() and saida and not saida[-1].strip():
                regra = "linha_vazia"
            elif not protegida(linha) and linha:
                if complemento and linha in nativas:
                    regra = "duplicata_complemento"
                elif CARIMBO.match(linha) and linha in carimbos:
                    regra = "carimbo_repetido"
                else:
                    if CARIMBO.match(linha): carimbos.add(linha)
                    if not complemento: nativas.add(linha)
                    if (i + 1 < len(linhas) and not protegida(linhas[i + 1])
                            and re.search(PALAVRA + r"-$", linha)
                            and re.match(r"^[a-záàâãéêíóôõúüç]" + PALAVRA + "*", linhas[i + 1])):
                        usadas.append(i + 2)
                        linha = linha[:-1] + linhas[i + 1]
                        i += 1
                        regra = "hifenizacao"
        if regra:
            alteracoes.append({"pagina": pagina, "linhas_fonte": usadas, "regra": regra})
        if regra not in ("linha_vazia", "duplicata_complemento", "carimbo_repetido"):
            saida.append(linha)
        i += 1
    return "\n".join(saida) + ("\n" if texto.endswith(("\n", "\r")) else ""), paginas, alteracoes


def gravar(destino, dados):
    fd, nome = tempfile.mkstemp(prefix=destino.name + ".", suffix=".tmp", dir=destino.parent)
    try:
        with os.fdopen(fd, "wb") as arquivo: arquivo.write(dados)
        os.replace(nome, destino)
    finally:
        if os.path.exists(nome): os.unlink(nome)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("transcricao", type=Path)
    fonte = ap.parse_args().transcricao.resolve()
    derivado = fonte.with_name("transcricao-normalizada.md")
    registro = fonte.with_name("normalizacao.json")
    if fonte in (derivado.resolve(), registro.resolve()):
        ap.error("A fonte deve ser a transcrição original, distinta das saídas derivadas.")
    original = fonte.read_bytes()
    texto, paginas, alteracoes = normalizar(original.decode("utf-8"))
    dados = texto.encode("utf-8")
    metadados = {"schema": "cpj-normalizacao/1", "fonte": fonte.name,
                 "derivado": derivado.name, "sha256_fonte": hashlib.sha256(original).hexdigest(),
                 "sha256_derivado": hashlib.sha256(dados).hexdigest(),
                 "paginas": paginas, "alteracoes": alteracoes}
    gravar(derivado, dados)
    gravar(registro, (json.dumps(metadados, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    print(f"Derivado gerado: {derivado.name}; {len(alteracoes)} alteração(ões).")


if __name__ == "__main__":
    main()
