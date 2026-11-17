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
def iter_candidatos(texto):
    """Candidatos por padrão, em memória; página/linha são da transcrição.

    Não confere identidade nem completa dígitos. A CLI legada e o indexador
    compartilham os mesmos padrões sem gerar arquivos durante importação.
    """
    texto = re.sub(r"<!--.*?-->", lambda m: "\n" * m.group(0).count("\n"), texto, flags=re.S)
    pag = None
    for numero, ln in enumerate(texto.splitlines(), 1):
        m = re.fullmatch(r"##\s*P[áa]gina\s+(\d+)\s*", ln)
        if m:
            pag = int(m.group(1)) or None
            continue
        if pag is None:
            continue
        incertos = [m.span() for m in re.finditer(
            r"\S*[?\ufffd]\S*|\S+\s+\[(?:d[ií]gito incerto|ileg[ií]vel|incerto)[^\]]*\]", ln, re.I)]
        documentos = [m.span() for tipo in ("CPF", "CNPJ") for m in re.finditer(PADROES[tipo], ln)]
        for tipo, rx in PADROES.items():
            for achado in re.finditer(rx, ln, flags=re.I if tipo in ("FLS", "CHASSI") else 0):
                inicio, fim = achado.span()
                if any(inicio < b and fim > a for a, b in incertos):
                    continue
                # Onze dígitos sem rótulo são ambíguos: manter CPF candidato,
                # sem fabricar também um telefone pela mesma sequência.
                if tipo == "TELEFONE" and any(inicio < b and fim > a for a, b in documentos):
                    continue
                valor = achado.group(1) if tipo == "FLS" else achado.group(0)
                yield {"tipo": tipo, "valor": valor.strip(), "pagina_pdf": pag,
                       "linha": numero, "trecho": ln.strip()[:160],
                       "status": "pendente de conferência"}


def main(argv=None):
    from collections import Counter
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        raise SystemExit("Uso: entidades.py extracao/transcricao.md")
    arq = args[0]
    with open(arq, encoding="utf-8") as f:
        linhas = list(iter_candidatos(f.read()))
    saida = os.path.join(os.path.dirname(arq), "entidades.csv")
    with open(saida, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["tipo", "valor", "pagina_pdf", "trecho", "status"],
                           delimiter=";", extrasaction="ignore")
        w.writeheader(); w.writerows(linhas)
    print(f"{len(linhas)} candidatos -> {saida}")
    print(dict(Counter(l["tipo"] for l in linhas)))


if __name__ == "__main__":
    main()
