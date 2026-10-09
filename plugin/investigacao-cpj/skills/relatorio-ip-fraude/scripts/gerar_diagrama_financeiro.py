#!/usr/bin/env python3
"""Fluxograma do caminho do dinheiro (PNG, 300 DPI) a partir de 02-analise\\fluxo-financeiro.csv.

Totalmente local (Pillow, sem rede). Só desenha o que está no CSV: não completa nome, banco, valor, camada nem
vínculo. Linha sem valor documentado é ignorada. A figura é transcrição provisória do CSV, não prova autônoma:
cada seta traz a página/folha de origem para conferência.

Uso: gerar_diagrama_financeiro.py <fluxo-financeiro.csv> <saida.png> [--caso OS-...-2026] [--dpi 300]
Uso como módulo (gerar_docx.py): carregar_transacoes(csv) -> list[dict]; desenhar_diagrama(txs, saida, ...) -> caminho.
"""
import argparse
import csv
import os
import re
import sys
import unicodedata
from decimal import Decimal, InvalidOperation

from PIL import Image, ImageDraw, ImageFont

COR_FUNDO, COR_TEXTO, COR_LINHA = (255, 255, 255), (30, 30, 30), (90, 90, 90)
COR_NO = {"vitima": ((232, 245, 233), (46, 125, 50)), "passagem": ((227, 242, 253), (21, 101, 192)),
          "destino": ((255, 243, 224), (230, 81, 0)), "origem": ((238, 238, 238), (97, 97, 97))}
COR_PENDENTE = (198, 40, 40)


def _fonte(tam, negrito=False):
    nomes = (["arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf"] if negrito else ["arial.ttf", "Arial.ttf", "DejaVuSans.ttf"])
    for pasta in (os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts"), "/usr/share/fonts/truetype/dejavu", ""):
        for n in nomes:
            try:
                return ImageFont.truetype(os.path.join(pasta, n) if pasta else n, tam)
            except OSError:
                continue
    return ImageFont.load_default()


def _valor(txt):
    """'1.234,56' | '1234,56' | '1500.00' | '3593' -> Decimal; vazio/inválido -> None. Nunca estima."""
    s = str(txt or "").replace("R$", "").strip()
    if not s:
        return None
    s = s.replace(".", "").replace(",", ".") if "," in s else s
    try:
        v = Decimal(s)
    except InvalidOperation:
        return None
    return v if v > 0 else None


def _brl(v):
    return "R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _inteiro(txt):
    m = re.search(r"\d+", str(txt or ""))
    return int(m.group()) if m else None


def carregar_transacoes(caminho):
    """Lê o CSV (UTF-8, com ou sem BOM, separador ';' ou ','). Mantém só linhas com valor documentado."""
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        amostra = f.read(4096)
        f.seek(0)
        delim = ";" if amostra.count(";") >= amostra.count(",") else ","
        out = []
        for ln in csv.DictReader(f, delimiter=delim):
            ln = {(k or "").strip().lower(): (v or "").strip() for k, v in ln.items() if k}
            v = _valor(ln.get("valor"))
            if v is None:
                continue
            ln["_valor"] = v
            out.append(ln)
    return out


def _chave(nome):
    s = unicodedata.normalize("NFD", nome or "").encode("ascii", "ignore").decode().upper()
    return re.sub(r"\s+", " ", s).strip()


def _conta(txt):
    """Agência/conta só com letras e dígitos, para comparar '0001/12345-6' com '0001 12345 6'."""
    return re.sub(r"[^0-9A-Z]", "", _chave(txt))


def _contas_conhecidas(refs):
    """refs: (escopo, nome, conta). Devolve {(escopo, chave do nome): {contas informadas}}."""
    out = {}
    for escopo, nome, conta in refs:
        if _conta(conta):
            out.setdefault((escopo, _chave(nome)), set()).add(_conta(conta))
    return out


def _identidade(escopo, nome, conta, conhecidas):
    """Identidade do nó = titular + conta. Sem conta, só se liga ao titular quando ele tem UMA conta conhecida no
    escopo; havendo várias (ou nenhuma), a linha fica num nó próprio: não se escolhe conta por dedução."""
    k = _chave(nome) or "NAO INFORMADO"
    c = _conta(conta)
    if not c:
        cs = conhecidas.get((escopo, k), ())
        c = next(iter(cs)) if len(cs) == 1 else ""
    return (k, c)


def _camadas(txs):
    """(camada de cada transação, calculada). A do CSV se todas tiverem (calculada=False); senão a profundidade no
    grafo pelo encadeamento titular+conta (sem ciclos), que é posição calculada e não fato documentado."""
    cam = [_inteiro(t.get("camada")) for t in txs]
    if all(c for c in cam):
        return cam, False
    conhecidas = _contas_conhecidas([("g", t.get(f"{l}_titular"), t.get(f"{l}_ag_conta")) for t in txs for l in ("origem", "destino")])

    def ident(t, lado):
        return _identidade("g", t.get(f"{lado}_titular"), t.get(f"{lado}_ag_conta"), conhecidas)
    prof, destinos = {}, {ident(t, "destino") for t in txs}
    raizes = {ident(t, "origem") for t in txs} - destinos or {ident(txs[0], "origem")}
    for r in raizes:
        prof[r] = 0
    for _ in range(len(txs) + 1):
        mudou = False
        for t in txs:
            o, d = ident(t, "origem"), ident(t, "destino")
            if o in prof and prof[o] + 1 > prof.get(d, 0) and prof[o] + 1 <= len(txs):
                prof[d] = prof[o] + 1
                mudou = True
        if not mudou:
            break
    return [max(1, prof.get(ident(t, "origem"), 0) + 1) for t in txs], True


def montar_grafo(txs):
    """Nós por coluna e arestas. Devolve dict(colunas, nos, arestas, cams, calculada). Só estrutura, sem desenho."""
    cams, calculada = _camadas(txs)
    conhecidas = _contas_conhecidas(
        [(c - 1, t.get("origem_titular"), t.get("origem_ag_conta")) for t, c in zip(txs, cams)]
        + [(c, t.get("destino_titular"), t.get("destino_ag_conta")) for t, c in zip(txs, cams)])
    colunas, nos, arestas = {}, {}, []

    def no(col, nome, banco, conta, tipo):
        k = (col,) + _identidade(col, nome, conta, conhecidas)
        n = colunas.setdefault(col, {}).setdefault(k, {"nome": nome or "Não informado", "banco": banco or "", "tipo": tipo, "entra": Decimal(0), "sai": Decimal(0), "conta": conta or ""})
        if not n["banco"] and banco:
            n["banco"] = banco
        if not n["conta"] and conta:
            n["conta"] = conta
        nos[k] = n
        return k

    # sem camada documentada não se afirma "vítima": a origem é só "origem" (posição calculada)
    tipo_origem = "origem" if calculada else "vitima"
    for t, c in zip(txs, cams):
        o = no(c - 1, t.get("origem_titular"), t.get("origem_banco"), t.get("origem_ag_conta"), tipo_origem if c == 1 else "passagem")
        d = no(c, t.get("destino_titular"), t.get("destino_banco"), t.get("destino_ag_conta"), "destino")
        nos[o]["sai"] += t["_valor"]
        nos[d]["entra"] += t["_valor"]
        arestas.append((o, d, t))
    # nó que repassa adiante é de passagem; o último destino é só "destino" (sem afirmar beneficiário final)
    for n in nos.values():
        if n["tipo"] == "destino" and n["sai"] > 0:
            n["tipo"] = "passagem"
    return {"colunas": colunas, "nos": nos, "arestas": arestas, "cams": cams, "calculada": calculada}


def _quebra_total(draw, texto, fonte, largura):
    linhas, atual = [], ""
    for p in (texto or "").split():
        teste = (atual + " " + p).strip()
        if draw.textlength(teste, font=fonte) <= largura or not atual:
            atual = teste
        else:
            linhas.append(atual)
            atual = p
    return linhas + ([atual] if atual else [])


def _quebra(draw, texto, fonte, largura):
    palavras, linhas, atual = (texto or "").split(), [], ""
    for p in palavras:
        teste = (atual + " " + p).strip()
        if draw.textlength(teste, font=fonte) <= largura or not atual:
            atual = teste
        else:
            linhas.append(atual)
            atual = p
    if atual:
        linhas.append(atual)
    return linhas[:3] + (["…"] if len(linhas) > 3 else [])


def desenhar_diagrama(transacoes, saida, titulo="FLUXOGRAMA DO CAMINHO DO DINHEIRO", caso_id="", dpi=300):
    """Desenha o fluxograma e grava o PNG em `saida` (com metadado de DPI). Devolve o caminho."""
    if not transacoes:
        raise ValueError("Sem transações com valor documentado para desenhar.")
    saida = str(saida)
    g = montar_grafo(transacoes)
    colunas, nos, arestas, cams, calculada = g["colunas"], g["nos"], g["arestas"], g["cams"], g["calculada"]

    k = dpi / 100.0
    LARG_NO, ALT_NO, GAP_X, GAP_Y, MARGEM, TOPO = int(520 * k * 0.6), int(210 * k * 0.6), int(640 * k * 0.6), int(70 * k * 0.6), int(90 * k * 0.6), int(260 * k * 0.6)
    f_tit, f_no, f_peq = _fonte(int(34 * k * 0.6), True), _fonte(int(28 * k * 0.6), True), _fonte(int(24 * k * 0.6))
    ncols = max(colunas) + 1
    maxn = max(len(v) for v in colunas.values())
    larg = MARGEM * 2 + ncols * LARG_NO + (ncols - 1) * GAP_X
    alt = TOPO + maxn * ALT_NO + (maxn - 1) * GAP_Y + MARGEM + int(230 * k * 0.6)
    img = Image.new("RGB", (max(larg, 1400), alt), COR_FUNDO)
    d = ImageDraw.Draw(img)
    d.text((MARGEM, int(40 * k * 0.6)), titulo + (f" — {caso_id}" if caso_id else ""), font=f_tit, fill=COR_TEXTO)
    total_v = sum(t["_valor"] for t, c in zip(transacoes, cams) if c == 1)
    rot_total = "Total da 1ª posição calculada (origem não confirmada como vítima)" if calculada else "Total que saiu da(s) vítima(s) (camada 1)"
    d.text((MARGEM, int(110 * k * 0.6)), f"{rot_total}: {_brl(total_v)} · {len(transacoes)} transação(ões)",
           font=f_peq, fill=COR_LINHA)

    pos = {}
    for col in sorted(colunas):
        x = MARGEM + col * (LARG_NO + GAP_X)
        rot_col = ("Origem (posição calculada)" if calculada else "Vítima / origem") if col == 0 else f"Camada {col}" + (" (calculada)" if calculada else "")
        d.text((x, TOPO - int(60 * k * 0.6)), rot_col, font=f_peq, fill=COR_LINHA)
        altura_col = len(colunas[col]) * ALT_NO + (len(colunas[col]) - 1) * GAP_Y
        y0 = TOPO + (maxn * ALT_NO + (maxn - 1) * GAP_Y - altura_col) // 2
        for i, (chave, n) in enumerate(colunas[col].items()):
            y = y0 + i * (ALT_NO + GAP_Y)
            pos[chave] = (x, y)

    def centro(k_no, lado):
        x, y = pos[k_no]
        return (x + (LARG_NO if lado == "dir" else 0), y + ALT_NO // 2)

    rotulos = []
    # arestas por baixo dos nós
    for o, dst, t in arestas:
        x1, y1 = centro(o, "dir")
        x2, y2 = centro(dst, "esq")
        d.line([(x1, y1), (x2, y2)], fill=COR_LINHA, width=max(2, int(dpi / 100)))
        ang = (x2 - x1, y2 - y1)
        comp = (ang[0] ** 2 + ang[1] ** 2) ** 0.5 or 1
        ux, uy = ang[0] / comp, ang[1] / comp
        s = int(18 * k * 0.6)
        d.polygon([(x2, y2), (x2 - ux * s - uy * s / 2, y2 - uy * s + ux * s / 2), (x2 - ux * s + uy * s / 2, y2 - uy * s - ux * s / 2)], fill=COR_LINHA)
        rotulos.append(((x1 + x2) / 2, (y1 + y2) / 2, t))

    for chave, (x, y) in pos.items():
        n = nos[chave]
        fundo, borda = COR_NO[n["tipo"]]
        d.rounded_rectangle([x, y, x + LARG_NO, y + ALT_NO], radius=int(18 * k * 0.6), fill=fundo, outline=borda, width=max(3, int(dpi / 60)))
        ty = y + int(14 * k * 0.6)
        for ln in _quebra(d, n["nome"], f_no, LARG_NO - 30):
            d.text((x + 15, ty), ln, font=f_no, fill=COR_TEXTO)
            ty += int(34 * k * 0.6)
        det = " · ".join(x for x in (n["banco"], n["conta"]) if x)
        if det:
            d.text((x + 15, ty), _quebra(d, det, f_peq, LARG_NO - 30)[0], font=f_peq, fill=COR_LINHA)
            ty += int(30 * k * 0.6)
        if n["entra"] > 0:
            d.text((x + 15, y + ALT_NO - int(42 * k * 0.6)), "recebeu " + _brl(n["entra"]), font=f_peq, fill=COR_TEXTO)

    # rótulos por cima de tudo: valor, data e origem (pág./fls.) em linhas curtas
    for mx, my, t in rotulos:
        pag, fls = t.get("fonte_pag") or "", t.get("fls") or ""
        origem = (f"pág./fls. {pag}" if pag and pag == fls else " · ".join(x for x in (f"pág. {pag}" if pag else "", f"fls. {fls}" if fls else "") if x))
        linhas = [_brl(t["_valor"])] + _quebra(d, " · ".join(x for x in (t.get("data"), origem) if x), f_peq, GAP_X - 70)
        pendente = (t.get("status_conferencia") or "").lower() in ("pendente", "divergente")
        passo = int(30 * k * 0.6)
        y_txt = my - len(linhas) * passo // 2
        for j, texto in enumerate(linhas):
            w = d.textlength(texto, font=f_peq)
            d.rectangle([mx - w / 2 - 6, y_txt + j * passo - 2, mx + w / 2 + 6, y_txt + (j + 1) * passo - 2], fill=COR_FUNDO)
            d.text((mx - w / 2, y_txt + j * passo), texto, font=f_peq, fill=COR_PENDENTE if (j == 0 and pendente) else COR_TEXTO)

    ly = alt - int(180 * k * 0.6)
    for i, (rotulo, tipo) in enumerate(((("origem (posição calculada)", "origem") if calculada else ("origem (vítima)", "vitima")), ("conta de passagem", "passagem"), ("último destino documentado", "destino"))):
        lx = MARGEM + i * int(520 * k * 0.6)
        d.rounded_rectangle([lx, ly, lx + 40, ly + 28], radius=6, fill=COR_NO[tipo][0], outline=COR_NO[tipo][1], width=3)
        d.text((lx + 54, ly), rotulo, font=f_peq, fill=COR_TEXTO)
    nota = ("Transcrição provisória do fluxo-financeiro.csv; não é prova autônoma. Conferir cada valor nas páginas citadas. "
            "\"Último destino documentado\" não significa beneficiário final.")
    if calculada:
        nota += (" A coluna de cada nó foi CALCULADA pelo encadeamento titular/conta do CSV, que não traz a camada: não indica "
                 "que a origem seja a vítima nem que o repasse esteja documentado.")
    for j, ln in enumerate(_quebra_total(d, nota, f_peq, img.width - 2 * MARGEM)):
        d.text((MARGEM, ly + int(50 * k * 0.6) + j * int(30 * k * 0.6)), ln, font=f_peq, fill=COR_LINHA)
    os.makedirs(os.path.dirname(os.path.abspath(saida)), exist_ok=True)
    img.save(saida, "PNG", dpi=(dpi, dpi))
    return saida


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv")
    ap.add_argument("saida")
    ap.add_argument("--caso", default="")
    ap.add_argument("--dpi", type=int, default=300)
    a = ap.parse_args()
    txs = carregar_transacoes(a.csv)
    if not txs:
        raise SystemExit("Nenhuma transação com valor documentado no CSV.")
    print(desenhar_diagrama(txs, a.saida, caso_id=a.caso, dpi=a.dpi))


if __name__ == "__main__":
    main()
