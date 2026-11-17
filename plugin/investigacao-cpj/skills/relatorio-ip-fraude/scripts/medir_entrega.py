#!/usr/bin/env python3
"""MQ01 — mede quanto da minuta da IA foi mantido no relatório efetivamente entregue.

Convenção: o PDF do relatório é a versão entregue. Só números: o script nunca imprime nem grava trecho de
texto, nome de pessoa ou dado do caso (apenas versões, percentuais, nome do arquivo PDF e hash).

Uso (a partir da raiz do workspace, ou com CPJ_WORKSPACE definida):
  medir_entrega.py <ID> [--pdf <arquivo.pdf>] [--gravar]
  medir_entrega.py --todos [--gravar]

Entradas:
  casos\\<ID>\\03-relatorios\\minuta-vNN.md   (sem o cabeçalho YAML)
  PDF entregue = o mais recente (mtime) entre os PDFs de casos\\<ID>\\03-relatorios e os PDFs da pasta da
  O.S. correspondente (PASTA_OS, como em ferramentas\\fila-os.py: CPJ_PASTA_OS > <workspace>\\ordens-de-servico
  > E:\\ORDENS DE SERVIÇO CPJ) cujo início traga "RELATÓRIO DE INVESTIGAÇÃO". PDF com mais de 40 páginas
  (os autos) é ignorado, assim como PDF cujo nome indique pedido de dilação de prazo. --pdf substitui a busca.

Método: corpo = do primeiro "RESUMO DOS FATOS" em diante (senão, o texto inteiro); tokens em minúsculas, sem
* = # | _ `; difflib.SequenceMatcher(autojunk=False). mantido = tokens iguais / tokens da minuta; novo = tokens
do PDF que não vieram da minuta / tokens do PDF. Calculado para a primeira minuta e para a última gravada antes
do PDF (mtime <= mtime do PDF + 120 s).

--gravar: grava casos\\<ID>\\03-relatorios\\medicao-entrega.json (schema cpj-medicao-entrega/1), de forma
atômica. Sem --gravar nada é gravado.
Código de saída: 0 ok; 2 erro de entrada, caso sem minuta ou sem PDF (no modo de um caso).
"""
import argparse
import datetime
import difflib
import hashlib
import json
import os
import re
import sys

from pypdf import PdfReader

from calibrar_versoes import _corpo as sem_frontmatter
from conferir_minuta import ws_padrao

TOL = 120  # segundos de tolerância entre gravações da mesma operação
MAX_PAGINAS = 40  # acima disso o PDF são os autos, não o relatório
MIN_TOKENS = 100
LIMIAR = 80.0
SECAO = re.compile(r"\s*".join("RESUMODOSFATOS"), re.I)  # tolera título com letras espaçadas no PDF
SCHEMA = "cpj-medicao-entrega/1"
# Documento que usa o timbre do relatório, mas não é o relatório entregue (ex.: PEDIDO-DILACAO-PRAZO-OS-...pdf).
NAO_RELATORIO = re.compile(r"pedido|dila[cç][aã]o", re.I)


def erro(msg):
    print(f"ERRO: {msg}", file=sys.stderr)
    sys.exit(2)


def tokens(t):
    return re.findall(r"\w+", re.sub(r"[*=#|_`]", " ", t.lower()))


def corpo(t):
    m = SECAO.search(t)
    return t[m.start():] if m else t


def versao(caminho):
    return int(re.search(r"minuta-v(\d+)\.md$", caminho, re.I).group(1))


# ---------- O.S. (mesma regra de ferramentas\fila-os.py) ----------


def numeros_os(nome):
    """Pares (número, ano) de O.S. no nome da pasta; ignora IP, BO e Processo."""
    texto = re.sub(r"\b(?:IP|BO|PROC|PROCESSO|INQU[ÉE]RITO)\s*n?[º°o.]*\s*\d{1,7}\s*[-./_]\s*\d{2,4}\b", " ", nome, flags=re.I)
    achados = [(m.group(1).lstrip("0") or "0", "20" + m.group(2) if len(m.group(2)) == 2 else m.group(2))
               for m in re.finditer(r"\b(?:OS|O\.S\.|ORDEM(?:\s+DE\s+SERVI[ÇC]O)?)\s*n?[º°o.]*\s*(\d{3,5})\s*[-./_]\s*(\d{2,4})\b",
                                    texto, re.I)]
    if not achados:
        achados = [(m.group(1).lstrip("0") or "0", "20" + m.group(2) if len(m.group(2)) == 2 else m.group(2))
                   for m in re.finditer(r"\b(\d{3,5})\s*[-./_]\s*(\d{2,4})\b", texto)]
    return list(dict.fromkeys(achados))


def pasta_os(ws):
    if os.environ.get("CPJ_PASTA_OS"):
        return os.environ["CPJ_PASTA_OS"]
    interna = os.path.join(ws, "ordens-de-servico")
    return interna if os.path.isdir(interna) else r"E:\ORDENS DE SERVIÇO CPJ"


def pastas_da_os(ws, caso):
    """Pastas da O.S. do caso (casos nomeados OS-<número>-<ano>...)."""
    m = re.match(r"OS-(\d+)-(\d{4})", caso)
    base = pasta_os(ws)
    if not m or not os.path.isdir(base):
        return []
    chave = (m.group(1).lstrip("0") or "0", m.group(2))
    return [os.path.join(base, d) for d in sorted(os.listdir(base))
            if os.path.isdir(os.path.join(base, d)) and chave in numeros_os(d)]


# ---------- leitura ----------


def texto_minuta(p):
    with open(p, encoding="utf-8", errors="replace") as f:
        return sem_frontmatter(f.read())


def ler_pdf(p, exigir_titulo=False, limitar=True):
    """(texto, páginas) se o PDF for um relatório de investigação legível; senão None."""
    try:
        r = PdfReader(str(p))
        n = len(r.pages)
        if limitar and n > MAX_PAGINAS:
            return None
        if exigir_titulo:
            ini = re.sub(r"\s+", "", "".join((pg.extract_text() or "") for pg in r.pages[:2]).upper())
            if not re.search(r"RELAT[OÓ]RIODEINVESTIGA", ini):
                return None
        t = "\n".join((pg.extract_text() or "") for pg in r.pages)
    except Exception:
        return None
    return (t, n) if len(tokens(t)) >= MIN_TOKENS else None


def achar_pdf(ws, caso, rel):
    """PDF mais recente (mtime) entre os candidatos: (caminho, texto, páginas) ou None."""
    cand = []
    if os.path.isdir(rel):
        cand += [(os.path.join(rel, f), False) for f in os.listdir(rel) if f.lower().endswith(".pdf")]
    for pasta in pastas_da_os(ws, caso):
        for raiz, _, arqs in os.walk(pasta):
            cand += [(os.path.join(raiz, f), True) for f in arqs if f.lower().endswith(".pdf")]
    lidos = []
    for caminho, titulo in cand:
        if NAO_RELATORIO.search(os.path.basename(caminho)):
            continue
        x = ler_pdf(caminho, exigir_titulo=titulo)
        if x:
            lidos.append((caminho, *x))
    return max(lidos, key=lambda x: os.stat(x[0]).st_mtime) if lidos else None


# ---------- medição ----------


def comparar(texto_base, alvo):
    """(mantido %, novo %) da minuta em relação aos tokens do PDF."""
    ta = tokens(corpo(texto_base))
    if not ta or not alvo:
        return 0.0, 0.0
    sm = difflib.SequenceMatcher(None, ta, alvo, autojunk=False)
    iguais = sum(b.size for b in sm.get_matching_blocks())
    return 100 * iguais / len(ta), 100 * (len(alvo) - iguais) / len(alvo)


def medir(ws, caso, pdf_arg=None):
    """Mede um caso. Devolve (resultado, None) ou (None, motivo)."""
    rel = os.path.join(ws, "casos", caso, "03-relatorios")
    minutas = sorted((os.path.join(rel, f) for f in (os.listdir(rel) if os.path.isdir(rel) else [])
                      if re.fullmatch(r"minuta-v\d+\.md", f, re.I)), key=versao)
    if not minutas:
        return None, "sem minuta"
    if pdf_arg:
        x = ler_pdf(pdf_arg, limitar=False)
        achado = (os.path.abspath(pdf_arg), *x) if x else None
    else:
        achado = achar_pdf(ws, caso, rel)
    if not achado:
        return None, "sem PDF"
    caminho, texto, paginas = achado
    tp = os.stat(caminho).st_mtime
    alvo = tokens(corpo(texto))
    med = [(versao(m), os.stat(m).st_mtime <= tp + TOL, *comparar(texto_minuta(m), alvo)) for m in minutas]
    antes = [x for x in med if x[1]]
    v1, ult = med[0], (antes[-1] if antes else None)
    with open(caminho, "rb") as f:
        sha = hashlib.sha256(f.read()).hexdigest()
    return {
        "schema": SCHEMA,
        "caso": caso,
        "pdf": {"nome": os.path.basename(caminho), "sha256": sha, "paginas": paginas, "palavras": len(alvo),
                "data": datetime.datetime.fromtimestamp(tp).isoformat(timespec="seconds")},
        "primeira": {"versao": v1[0], "mantido": round(v1[2], 1)},
        "ultima": {"versao": ult[0], "mantido": round(ult[2], 1), "novo": round(ult[3], 1)} if ult else None,
        "versoes_antes_da_entrega": len(antes),
        "minutas": len(med),
        "secao_resumo_no_pdf": bool(SECAO.search(texto)),
        "gerado_em": datetime.datetime.now().isoformat(timespec="seconds"),
    }, None


def linha(r):
    u = r["ultima"]
    return (f"{r['caso']}: PDF {r['pdf']['paginas']} pág., {r['pdf']['palavras']} palavras"
            f"{'' if r['secao_resumo_no_pdf'] else ' [sem RESUMO DOS FATOS: texto inteiro]'}"
            f" | {r['minutas']} minutas ({r['versoes_antes_da_entrega']} antes do PDF)"
            f" | 1ª v{r['primeira']['versao']:02d} mantida {r['primeira']['mantido']:.1f}%"
            + (f" | última antes do PDF v{u['versao']:02d} mantida {u['mantido']:.1f}%, novo no PDF {u['novo']:.1f}%"
               if u else " | nenhuma minuta antes do PDF"))


def gravar(ws, r):
    destino = os.path.join(ws, "casos", r["caso"], "03-relatorios", "medicao-entrega.json")
    dados = {k: v for k, v in r.items() if k not in ("minutas", "secao_resumo_no_pdf")}
    tmp = destino + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, destino)


def media(v):
    return f"{sum(v) / len(v):.1f}%" if v else "n/d"


def main():
    ap = argparse.ArgumentParser(description="Mede quanto da minuta da IA foi mantido no PDF entregue (só números).")
    ap.add_argument("id", nargs="?", help="ID do caso (pasta em casos\\)")
    ap.add_argument("--todos", action="store_true", help="todos os casos com minuta e PDF, mais o agregado")
    ap.add_argument("--pdf", help="PDF entregue (substitui a busca; só com um caso)")
    ap.add_argument("--gravar", action="store_true", help="grava casos\\<ID>\\03-relatorios\\medicao-entrega.json")
    a = ap.parse_args()
    if bool(a.id) == a.todos:
        erro("informe o ID do caso ou --todos (um dos dois)")
    if a.pdf and a.todos:
        erro("--pdf vale só para um caso")
    ws = ws_padrao()

    if a.id:
        if not re.fullmatch(r"[\w.\-]+", a.id):
            erro(f"ID de caso inválido: {a.id}")
        if not os.path.isdir(os.path.join(ws, "casos", a.id)):
            erro(f"caso não encontrado: {a.id}")
        if a.pdf and not os.path.isfile(a.pdf):
            erro(f"PDF não encontrado: {a.pdf}")
        r, motivo = medir(ws, a.id, a.pdf)
        if not r:
            erro(f"{a.id}: {motivo}" + (" de relatório de investigação (casos\\<ID>\\03-relatorios ou pasta da O.S.)"
                                         if motivo == "sem PDF" else " em 03-relatorios"))
        print(linha(r))
        if a.gravar:
            gravar(ws, r)
        return 0

    pasta = os.path.join(ws, "casos")
    res, sem_pdf = [], 0
    for caso in sorted(os.listdir(pasta) if os.path.isdir(pasta) else []):
        if not os.path.isdir(os.path.join(pasta, caso)):
            continue
        r, motivo = medir(ws, caso)
        if r:
            print(linha(r))
            res.append(r)
            if a.gravar:
                gravar(ws, r)
        elif motivo == "sem PDF":
            sem_pdf += 1
    print("\n=== AGREGADO (PDF = entregue) ===")
    print(f"casos com minuta e PDF: {len(res)} | casos com minuta e sem PDF: {sem_pdf}")
    # A meta vale para o relatório no modelo; documento sem "RESUMO DOS FATOS" é contado à parte.
    for rotulo, grupo in (("relatórios no modelo", [r for r in res if r["secao_resumo_no_pdf"]]),
                          ("outros documentos (sem RESUMO DOS FATOS)", [r for r in res if not r["secao_resumo_no_pdf"]])):
        if not grupo:
            continue
        pri = [r["primeira"]["mantido"] for r in grupo]
        ult = [r["ultima"]["mantido"] for r in grupo if r["ultima"]]
        print(f"{rotulo}: {len(grupo)}")
        print(f"  1ª minuta: média {media(pri)} | >= {LIMIAR:.0f}%: {sum(v >= LIMIAR for v in pri)} de {len(pri)}")
        print(f"  última antes do PDF: média {media(ult)} | >= {LIMIAR:.0f}%: {sum(v >= LIMIAR for v in ult)} de {len(ult)}")
    return 0


if __name__ == "__main__":
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8")
        except (ValueError, OSError):
            pass
    sys.exit(main())
