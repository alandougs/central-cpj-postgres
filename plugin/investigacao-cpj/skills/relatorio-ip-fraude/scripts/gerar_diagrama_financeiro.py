#!/usr/bin/env python3
"""Geração de fluxograma visual do caminho do dinheiro (PNG 300 DPI) a partir de fluxo-financeiro.csv.

Compila graficamente as camadas de repasse bancário (Vítima -> 1ª Camada -> 2ª Camada -> Destino Final),
com valores, datas, bancos, contas e chaves Pix em alta resolução (300 DPI) para inserção no DOCX oficial.

Uso CLI:
  gerar_diagrama_financeiro.py <fluxo.csv> --saida <fluxograma.png> [--titulo TITULO] [--caso CASO_ID] [--dpi DPI]
"""
import argparse
import csv
import math
import os
import re
import sys
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

# Resolução padrão forense para documentos de impressão
DPI_PADRAO = 300


def _carregar_fonte(nome: str, tamanho: int) -> ImageFont.FreeTypeFont:
    """Tenta carregar fonte TrueType do Windows; caso indisponível, usa padrão."""
    windir = os.environ.get("WINDIR", r"C:\Windows")
    candidatos = [
        os.path.join(windir, "Fonts", nome),
        os.path.join(windir, "Fonts", "arial.ttf"),
        os.path.join(windir, "Fonts", "calibri.ttf"),
        os.path.join(windir, "Fonts", "segoeui.ttf"),
    ]
    for p in candidatos:
        if os.path.isfile(p):
            try:
                return ImageFont.truetype(p, tamanho)
            except Exception:
                pass
    return ImageFont.load_default()


def _formatar_moeda(val_str: str) -> str:
    """Formata valor em padrão brasileiro: R$ 1.234,56."""
    try:
        s = str(val_str or "").strip().replace("R$", "").replace(" ", "")
        if "," in s and "." in s:
            s = s.replace(".", "").replace(",", ".")
        elif "," in s:
            s = s.replace(",", ".")
        v = float(s)
        inteiro = f"{int(v):,}".replace(",", ".")
        centavos = f"{v - int(v):0.2f}".split(".")[1]
        return f"R$ {inteiro},{centavos}"
    except (ValueError, TypeError):
        return str(val_str or "R$ 0,00").strip()


def _parse_valor(val_str: str) -> float:
    try:
        s = str(val_str or "").strip().replace("R$", "").replace(" ", "")
        if "," in s and "." in s:
            s = s.replace(".", "").replace(",", ".")
        elif "," in s:
            s = s.replace(",", ".")
        return float(s)
    except Exception:
        return 0.0


def carregar_transacoes(caminho_csv: str) -> List[Dict[str, str]]:
    """Lê fluxo-financeiro.csv suportando delimitador ';' ou ',' e UTF-8 com/sem BOM."""
    if not os.path.isfile(caminho_csv):
        return []
    with open(caminho_csv, "r", encoding="utf-8-sig", errors="replace") as f:
        linhas = [ln for ln in f.readlines() if ln.strip()]
    if not linhas:
        return []

    cabecalho = linhas[0]
    sep = ";" if ";" in cabecalho else ","
    leitor = csv.DictReader(linhas, delimiter=sep)
    transacoes = []
    for r in leitor:
        t = {str(k).strip(): str(v).strip() for k, v in r.items() if k}
        if any(t.values()):
            transacoes.append(t)
    return transacoes


class Node:
    def __init__(self, key: str, titular: str, banco: str, conta: str, chave: str, camada: int, papel: str):
        self.key = key
        self.titular = titular or "TITULAR NÃO IDENTIFICADO"
        self.banco = banco or ""
        self.conta = conta or ""
        self.chave = chave or ""
        self.camada = camada
        self.papel = papel
        self.x = 0
        self.y = 0
        self.w = 0
        self.h = 0

    @property
    def center_y(self) -> float:
        return self.y + self.h / 2

    @property
    def left(self) -> float:
        return self.x

    @property
    def right(self) -> float:
        return self.x + self.w


class Edge:
    def __init__(self, u: str, v: str, valor: str, data: str, hora: str, meio: str, id_tx: str, camada: int):
        self.u = u  # node key origem
        self.v = v  # node key destino
        self.valor = valor
        self.data = data
        self.hora = hora
        self.meio = meio
        self.id_tx = id_tx
        self.camada = camada


def montar_grafo(transacoes: List[Dict[str, str]]) -> Tuple[Dict[str, Node], List[Edge]]:
    nodes: Dict[str, Node] = {}
    edges: List[Edge] = []

    def _ent_key(tit: str, bco: str, cta: str) -> str:
        return f"{tit.strip().upper()}::{bco.strip().upper()}::{cta.strip().upper()}"

    for t in transacoes:
        orig_tit = t.get("origem_titular") or "VÍTIMA"
        orig_banco = t.get("origem_banco") or ""
        orig_conta = t.get("origem_ag_conta") or ""
        orig_chave = t.get("origem_chave") or ""

        dest_tit = t.get("destino_titular") or "DESTINATÁRIO"
        dest_banco = t.get("destino_banco") or ""
        dest_conta = t.get("destino_ag_conta") or ""
        dest_chave = t.get("destino_chave") or ""

        try:
            camada_num = int(re.findall(r"\d+", t.get("camada") or "1")[0])
        except Exception:
            camada_num = 1

        u_key = _ent_key(orig_tit, orig_banco, orig_conta)
        v_key = _ent_key(dest_tit, dest_banco, dest_conta)

        if u_key not in nodes:
            orig_camada = 0 if camada_num <= 1 else camada_num - 1
            papel = "VÍTIMA / CONTA ORIGEM" if orig_camada == 0 else f"CONTA DE PASSAGEM ({orig_camada}ª CAMADA)"
            nodes[u_key] = Node(u_key, orig_tit, orig_banco, orig_conta, orig_chave, orig_camada, papel)

        if v_key not in nodes:
            papel = f"CONTA DE PASSAGEM ({camada_num}ª CAMADA)" if camada_num == 1 else f"REPASSE / DESTINO ({camada_num}ª CAMADA)"
            nodes[v_key] = Node(v_key, dest_tit, dest_banco, dest_conta, dest_chave, camada_num, papel)
        else:
            if nodes[v_key].camada < camada_num:
                nodes[v_key].camada = camada_num
                nodes[v_key].papel = f"REPASSE / DESTINO ({camada_num}ª CAMADA)"

        edges.append(
            Edge(
                u_key,
                v_key,
                t.get("valor") or "0",
                t.get("data") or "",
                t.get("hora") or "",
                t.get("meio") or "Pix",
                t.get("id_transacao") or "",
                camada_num,
            )
        )

    return nodes, edges


def desenhar_diagrama(
    transacoes: List[Dict[str, str]],
    saida_png: str,
    titulo: str = "FLUXOGRAMA DO CAMINHO DO DINHEIRO — RASTREABILIDADE BANCÁRIA",
    caso_id: str = "",
    dpi: int = DPI_PADRAO,
) -> str:
    """Renderiza imagem PNG de alta resolução (300 DPI) com o fluxograma financeiro."""
    nodes, edges = montar_grafo(transacoes)

    # Agrupa nós por camada (coluna)
    camadas_dict: Dict[int, List[Node]] = {}
    for node in nodes.values():
        camadas_dict.setdefault(node.camada, []).append(node)

    cols = sorted(camadas_dict.keys()) if camadas_dict else [0]
    total_cols = len(cols)
    max_linhas = max((len(camadas_dict.get(c, [])) for c in cols), default=1)

    node_w = 520
    node_h = 160
    col_gap = 260
    row_gap = 80
    pad_x = 100
    pad_top = 220
    pad_bottom = 140

    total_w = max(2400, pad_x * 2 + total_cols * node_w + max(0, total_cols - 1) * col_gap)
    total_h = max(1300, pad_top + max_linhas * (node_h + row_gap) + pad_bottom)

    img = Image.new("RGB", (total_w, total_h), color=(248, 250, 252))
    draw = ImageDraw.Draw(img)

    font_titulo = _carregar_fonte("arialbd.ttf", 34)
    font_sub = _carregar_fonte("arial.ttf", 20)
    font_badge = _carregar_fonte("arialbd.ttf", 15)
    font_titular = _carregar_fonte("arialbd.ttf", 20)
    font_info = _carregar_fonte("arial.ttf", 16)
    font_valor = _carregar_fonte("arialbd.ttf", 18)
    font_tx = _carregar_fonte("arial.ttf", 14)
    font_rodape = _carregar_fonte("arial.ttf", 16)
    font_rodape_bold = _carregar_fonte("arialbd.ttf", 17)

    # 1. CABEÇALHO / BANNER OFICIAL (Polícia Civil - DEINTER 8)
    draw.rectangle([(0, 0), (total_w, 140)], fill=(15, 23, 42))  # Slate 900
    draw.rectangle([(0, 140), (total_w, 146)], fill=(217, 119, 6))  # Dourado / Âmbar CPJ

    draw.text((pad_x, 32), titulo, fill=(255, 255, 255), font=font_titulo)
    sub = "DEINTER 8 — CENTRAL DE POLÍCIA JUDICIÁRIA DE PRESIDENTE PRUDENTE / SP"
    if caso_id:
        sub += f" | CASO: {caso_id}"
    draw.text((pad_x, 82), sub, fill=(148, 163, 184), font=font_sub)

    # 2. RÓTULOS DE COLUNA / CAMADAS
    col_x_map = {}
    for idx, c in enumerate(cols):
        cx = pad_x + idx * (node_w + col_gap)
        col_x_map[c] = cx
        rotulo_col = "ORIGEM / VÍTIMA" if c == 0 else f"{c}ª CAMADA (PASSAGEM)" if c == 1 else f"{c}ª CAMADA (REPASSE)"
        cor_tag = (30, 58, 138) if c == 0 else (194, 65, 12) if c == 1 else (185, 28, 28)
        draw.rounded_rectangle([(cx, 165), (cx + node_w, 200)], radius=6, fill=cor_tag)
        draw.text((cx + 16, 172), rotulo_col, fill=(255, 255, 255), font=font_badge)

    # 3. POSICIONAMENTO E DESENHO DOS NÓS
    for c in cols:
        nodes_col = camadas_dict.get(c, [])
        h_ocupada = len(nodes_col) * node_h + (len(nodes_col) - 1) * row_gap
        offset_y = (pad_top + (max_linhas * (node_h + row_gap) - row_gap - h_ocupada) / 2)
        cx = col_x_map[c]

        for i, node in enumerate(nodes_col):
            node.x = cx
            node.y = offset_y + i * (node_h + row_gap)
            node.w = node_w
            node.h = node_h

            cor_borda = (30, 58, 138) if c == 0 else (217, 119, 6) if c == 1 else (220, 38, 38)
            cor_fundo = (255, 255, 255)
            cor_faixa = (239, 246, 255) if c == 0 else (255, 251, 235) if c == 1 else (254, 242, 242)

            draw.rounded_rectangle([(node.x + 3, node.y + 3), (node.x + node.w + 3, node.y + node.h + 3)], radius=8, fill=(226, 232, 240))
            draw.rounded_rectangle([(node.x, node.y), (node.x + node.w, node.y + node.h)], radius=8, fill=cor_fundo, outline=cor_borda, width=2)
            draw.rounded_rectangle([(node.x + 2, node.y + 2), (node.x + node.w - 2, node.y + 36)], radius=6, fill=cor_faixa)

            draw.text((node.x + 14, node.y + 8), node.papel.upper(), fill=cor_borda, font=font_badge)

            tit_truncado = node.titular[:36] + ("..." if len(node.titular) > 36 else "")
            draw.text((node.x + 14, node.y + 44), tit_truncado.upper(), fill=(15, 23, 42), font=font_titular)

            banco_txt = f"Banco: {node.banco}" if node.banco else "Banco não informado"
            if node.conta:
                banco_txt += f" | Ag/Conta: {node.conta}"
            draw.text((node.x + 14, node.y + 82), banco_txt, fill=(71, 85, 105), font=font_info)

            if node.chave:
                draw.text((node.x + 14, node.y + 114), f"Chave Pix: {node.chave}", fill=(30, 41, 59), font=font_info)
            else:
                draw.text((node.x + 14, node.y + 114), "Vínculo documentado nos autos", fill=(148, 163, 184), font=font_info)

    # 4. CONECTORES E SETAS (TRANSAÇÕES)
    for edge in edges:
        u_node = nodes.get(edge.u)
        v_node = nodes.get(edge.v)
        if not u_node or not v_node:
            continue

        x1 = u_node.right
        y1 = u_node.center_y
        x2 = v_node.left
        y2 = v_node.center_y

        cor_linha = (100, 116, 139)
        cor_seta = (30, 41, 59)

        draw.line([(x1, y1), (x2, y2)], fill=cor_linha, width=3)

        tam_seta = 14
        angulo = math.atan2(y2 - y1, x2 - x1)
        px1 = x2 - tam_seta * math.cos(angulo - math.pi / 6)
        py1 = y2 - tam_seta * math.sin(angulo - math.pi / 6)
        px2 = x2 - tam_seta * math.cos(angulo + math.pi / 6)
        py2 = y2 - tam_seta * math.sin(angulo + math.pi / 6)
        draw.polygon([(x2, y2), (px1, py1), (px2, py2)], fill=cor_seta)

        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2

        valor_fmt = _formatar_moeda(edge.valor)
        data_meio = f"{edge.meio}"
        if edge.data:
            data_meio += f" • {edge.data}"
            if edge.hora:
                data_meio += f" {edge.hora}"

        pill_w = 210
        pill_h = 58
        pill_x1 = mid_x - pill_w / 2
        pill_y1 = mid_y - pill_h / 2
        pill_x2 = mid_x + pill_w / 2
        pill_y2 = mid_y + pill_h / 2

        draw.rounded_rectangle([(pill_x1, pill_y1), (pill_x2, pill_y2)], radius=8, fill=(255, 255, 255), outline=(148, 163, 184), width=1)
        draw.text((pill_x1 + 12, pill_y1 + 8), valor_fmt, fill=(185, 28, 28), font=font_valor)
        draw.text((pill_x1 + 12, pill_y1 + 32), data_meio, fill=(71, 85, 105), font=font_tx)

    # 5. RODAPÉ DE AUDITORIA E TOTAIS
    rodape_y = total_h - 90
    draw.rectangle([(0, rodape_y), (total_w, total_h)], fill=(241, 245, 249))
    draw.line([(0, rodape_y), (total_w, rodape_y)], fill=(203, 213, 225), width=2)

    total_movimentado = sum(_parse_valor(t.get("valor") or "0") for t in transacoes)
    str_total = _formatar_moeda(str(total_movimentado))
    qtd_tx = len(transacoes)
    qtd_camadas = len([c for c in cols if c > 0])

    resumo_esq = f"TOTAL RASTREADO DOCUMENTADO: {str_total}  |  TRANSAÇÕES: {qtd_tx}  |  CAMADAS BANCÁRIAS: {qtd_camadas}"
    draw.text((pad_x, rodape_y + 32), resumo_esq, fill=(15, 23, 42), font=font_rodape_bold)

    resumo_dir = "POLÍCIA CIVIL DO ESTADO DE SÃO PAULO — SISTEMA CENTRAL CPJ"
    w_dir = font_rodape.getlength(resumo_dir) if hasattr(font_rodape, "getlength") else 500
    draw.text((total_w - pad_x - w_dir, rodape_y + 34), resumo_dir, fill=(100, 116, 139), font=font_rodape)

    os.makedirs(os.path.dirname(os.path.abspath(saida_png)), exist_ok=True)
    img.save(saida_png, format="PNG", dpi=(dpi, dpi))
    return saida_png


def gerar_diagrama_para_caso(pasta_caso: str, dpi: int = DPI_PADRAO) -> Optional[str]:
    """Descobre fluxo-financeiro.csv no caso e compila o diagrama PNG em 03-relatorios."""
    csv_path = os.path.join(pasta_caso, "02-analise", "fluxo-financeiro.csv")
    if not os.path.isfile(csv_path):
        return None

    transacoes = carregar_transacoes(csv_path)
    if not transacoes:
        return None

    caso_id = os.path.basename(pasta_caso)
    saida_png = os.path.join(pasta_caso, "03-relatorios", f"FLUXO-FINANCEIRO-{caso_id}.png")
    return desenhar_diagrama(
        transacoes,
        saida_png,
        titulo=f"FLUXOGRAMA DO CAMINHO DO DINHEIRO — RASTREABILIDADE BANCÁRIA",
        caso_id=caso_id,
        dpi=dpi,
    )


def main():
    p = argparse.ArgumentParser(description="Gera fluxograma PNG 300 DPI do caminho do dinheiro a partir de fluxo-financeiro.csv.")
    p.add_argument("csv", help="Caminho do arquivo fluxo-financeiro.csv")
    p.add_argument("--saida", "-o", required=True, help="Caminho do arquivo PNG de saída")
    p.add_argument("--titulo", default="FLUXOGRAMA DO CAMINHO DO DINHEIRO — RASTREABILIDADE BANCÁRIA")
    p.add_argument("--caso", default="", help="Identificador do caso/O.S. para inclusão no cabeçalho")
    p.add_argument("--dpi", type=int, default=DPI_PADRAO, help="Resolução DPI da imagem (padrão 300)")
    args = p.parse_args()

    txs = carregar_transacoes(args.csv)
    if not txs:
        print(f"Aviso: Nenhuma transação encontrada em {args.csv}.", file=sys.stderr)
        sys.exit(1)

    out = desenhar_diagrama(txs, args.saida, titulo=args.titulo, caso_id=args.caso, dpi=args.dpi)
    print(f"OK -> {out}")


if __name__ == "__main__":
    main()
