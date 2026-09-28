#!/usr/bin/env python3
"""Preenche o MODELO RELATÓRIO DE INVESTIGAÇÃO - CPJ (DOCX com timbre, rodapé e assinatura)
a partir de uma minuta Markdown.

Uso:
  gerar_docx.py minuta.md --saida RELATORIO.docx [--modelo modelo.docx] [--sem-assinatura]

Minuta (UTF-8):
  ---
  ordem_servico: 123/2026
  referencia: IP nº 1234567-89.2026 / BO nº AB1234/2026
  natureza: Estelionato (art. 171, CP)
  investigados: FULANO DE TAL
  vitimas: BELTRANA DE TAL
  local: Rua X, 100, Presidente Prudente/SP
  data_fatos: 10/03/2026
  local_data: Presidente Prudente, SP, 27 de setembro de 2026
  data_rodape: 27/09/2026
  delegado: Dr. Nome do Delegado
  ---
  ## RESUMO DOS FATOS
  ...
  ## DILIGÊNCIAS REALIZADAS
  ...
  ## CONCLUSÃO
  ...

Markdown aceito no corpo: parágrafos, **negrito**, `### subtítulo` (negrito), listas `- ` / `1. `,
tabelas `| a | b |` (viram tabela Word), `<!-- notas internas -->` (removidas).
Campo ausente/vazio na minuta: o texto-guia do modelo é mantido para preenchimento manual.
Timbre (cabeçalho), rodapé com paginação automática e imagem de assinatura são preservados.
"""
import argparse, copy, os, re, sys
import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, Twips

MODELO_PADRAO = os.path.join(
    os.environ.get("CPJ_WORKSPACE", r"C:\CPJ - TRABALHO"),
    "modelos", "MODELO RELATORIO DE INVESTIGACAO - CPJ 2026.docx",
)
FONTE, TAM = "Arial", 12

CAMPOS_CABECALHO = [  # (chave da minuta, rótulo no modelo)
    ("ordem_servico", "Ordem de Serviço:"),
    ("referencia", "Referência:"),
    ("natureza", "Natureza:"),
    ("investigados", "Investigado (s):"),
    ("vitimas", "Vítima(s):"),
    ("local", "Local:"),
    ("data_fatos", "Data dos Fatos:"),
]
SECOES = {  # seção da minuta -> prefixos dos parágrafos-guia do modelo que ela substitui
    "RESUMO DOS FATOS": ["{Resumir"],
    "DILIGÊNCIAS REALIZADAS": ["{Elencar"],
    "CONCLUSÃO": ["{breve descrição", "{Sugestão de providências"],
}

ap = argparse.ArgumentParser()
ap.add_argument("minuta"); ap.add_argument("--saida", required=True)
ap.add_argument("--modelo", default=MODELO_PADRAO)
ap.add_argument("--sem-assinatura", action="store_true", help="remove a imagem da assinatura (rascunho)")
a = ap.parse_args()


# ---------- leitura da minuta ----------
bruto = open(a.minuta, encoding="utf-8-sig").read()
bruto = re.sub(r"<!--.*?-->", "", bruto, flags=re.S)
meta, corpo = {}, bruto
m = re.match(r"\s*---\s*\n(.*?)\n---\s*\n(.*)", bruto, flags=re.S)
if m:
    for ln in m.group(1).splitlines():
        if ":" in ln:
            k, v = ln.split(":", 1)
            meta[k.strip().lower()] = v.strip()
    corpo = m.group(2)

secoes, atual = {}, None
for ln in corpo.splitlines():
    t = re.match(r"^##\s+(.+?)\s*$", ln)
    if t and not ln.startswith("###"):
        nome = t.group(1).strip().upper()
        atual = next((s for s in SECOES if s in nome or nome in s), nome)
        secoes[atual] = []
        continue
    if atual:
        secoes[atual].append(ln)


def blocos(linhas):
    """Agrupa linhas em blocos: ('p', texto) | ('h', texto) | ('li', texto) | ('tab', [[...]])."""
    out, par, tab = [], [], []

    def fecha_par():
        if par: out.append(("p", " ".join(x.strip() for x in par))); par.clear()

    def fecha_tab():
        if tab:
            linhas_t = [[c.strip() for c in r.strip().strip("|").split("|")] for r in tab
                        if not re.fullmatch(r"\|?[\s:\-|]+\|?", r.strip())]
            if linhas_t: out.append(("tab", linhas_t))
            tab.clear()

    for ln in linhas:
        s = ln.strip()
        if s.startswith("|"):
            fecha_par(); tab.append(s); continue
        fecha_tab()
        if not s:
            fecha_par(); continue
        if s.startswith("###"):
            fecha_par(); out.append(("h", s.lstrip("#").strip())); continue
        if re.match(r"^([-*•]|\d+[.)])\s+", s):
            fecha_par(); out.append(("li", s)); continue
        par.append(s)
    fecha_par(); fecha_tab()
    return out


# ---------- utilitários DOCX ----------
def add_runs(p, texto, negrito_base=False):
    for i, parte in enumerate(re.split(r"\*\*(.+?)\*\*", texto)):
        if not parte: continue
        r = p.add_run(parte)
        r.bold = negrito_base or (i % 2 == 1)
        r.font.name = FONTE; r.font.size = Pt(TAM)
        r._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), FONTE)


def limpa_runs(p):
    for r in list(p._element):
        if r.tag != qn("w:pPr"): p._element.remove(r)


def paragrafo_antes(ref, texto="", negrito=False, recuo_lista=False):
    novo = copy.deepcopy(ref._element)
    ref._element.addprevious(novo)
    p = docx.text.paragraph.Paragraph(novo, ref._parent)
    limpa_runs(p)
    if recuo_lista:
        p.paragraph_format.left_indent = Pt(18); p.paragraph_format.first_line_indent = Pt(-12)
    if texto: add_runs(p, texto, negrito)
    return p


def tabela_antes(doc, ref, linhas):
    ncol = max(len(r) for r in linhas)
    t = doc.add_table(rows=len(linhas), cols=ncol)
    tblPr = t._tbl.tblPr
    secao = doc.sections[0]
    largura_total = int(round((secao.page_width - secao.left_margin - secao.right_margin) / 635))
    pesos = [min(max(max((len(r[j]) if j < len(r) else 0) for r in linhas), 8), 48) for j in range(ncol)]
    larguras = [largura_total * peso // sum(pesos) for peso in pesos]
    larguras[-1] += largura_total - sum(larguras)
    tbl_w = tblPr.find(qn("w:tblW"))
    tbl_w.set(qn("w:w"), str(largura_total)); tbl_w.set(qn("w:type"), "dxa")
    t.autofit = False
    for coluna, largura in zip(t.columns, larguras):
        coluna.width = Twips(largura)
    bordas = OxmlElement("w:tblBorders")
    for b in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = OxmlElement(f"w:{b}"); e.set(qn("w:val"), "single"); e.set(qn("w:sz"), "4"); e.set(qn("w:color"), "000000")
        bordas.append(e)
    tblPr.append(bordas)
    trPr = t.rows[0]._tr.get_or_add_trPr()
    cabecalho = OxmlElement("w:tblHeader"); cabecalho.set(qn("w:val"), "true")
    trPr.append(cabecalho)
    colunas_monetarias = {
        j for j, cabecalho in enumerate(linhas[0])
        if re.search(r"(?:^|[^a-z])(valor|saldo|montante|total)(?:$|[^a-z])|r\$", cabecalho.lower())
    }
    for i, r in enumerate(linhas):
        for j in range(ncol):
            cel = t.cell(i, j); cel.text = ""
            cp = cel.paragraphs[0]
            if i > 0 and j in colunas_monetarias:
                cp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            for k, parte in enumerate(re.split(r"\*\*(.+?)\*\*", r[j] if j < len(r) else "")):
                if not parte: continue
                run = cp.add_run(parte); run.font.name = FONTE; run.font.size = Pt(9)
                run._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), FONTE)
                run.bold = (i == 0) or (k % 2 == 1)
    ref._element.addprevious(t._tbl)


def remove(p):
    p._element.getparent().remove(p._element)


# ---------- preenchimento ----------
if not os.path.exists(a.modelo):
    raise SystemExit(f"Modelo não encontrado: {a.modelo}")
doc = docx.Document(a.modelo)
pars = list(doc.paragraphs)
pendentes = []

for chave, rotulo in CAMPOS_CABECALHO:
    p = next((x for x in pars if x.text.strip().startswith(rotulo)), None)
    if p is None: continue
    v = meta.get(chave, "")
    if v:
        limpa_runs(p); add_runs(p, f"{rotulo} {v}", negrito_base=True)
    else:
        pendentes.append(rotulo.rstrip(":"))

for secao, prefixos in SECOES.items():
    guias = [x for x in pars if any(x.text.strip().startswith(pr) for pr in prefixos)]
    if not guias: continue
    conteudo = blocos(secoes.get(secao, []))
    if not conteudo:
        pendentes.append(secao); continue
    ref = guias[0]
    for n, (tipo, val) in enumerate(conteudo):
        if n: paragrafo_antes(ref)  # linha em branco entre blocos, como no modelo
        if tipo == "tab": tabela_antes(doc, ref, val)
        elif tipo == "h": paragrafo_antes(ref, val, negrito=True)
        elif tipo == "li": paragrafo_antes(ref, val, recuo_lista=True)
        else: paragrafo_antes(ref, val)
    for g in guias: remove(g)

for chave, prefixo in (("local_data", "[local, Estado]"), ("delegado", "{Nome do Delegado")):
    p = next((x for x in doc.paragraphs if x.text.strip().startswith(prefixo)), None)
    if p is None: continue
    if meta.get(chave):
        limpa_runs(p); add_runs(p, meta[chave], negrito_base=(chave == "delegado"))
    else:
        pendentes.append(chave)

if meta.get("data_rodape"):
    for sec in doc.sections:
        for par in [q for t in sec.footer.tables for c in t._cells for q in c.paragraphs] + list(sec.footer.paragraphs):
            for r in par.runs:
                if re.fullmatch(r"\s*\d{2}/\d{2}/\d{4}\s*", r.text or ""):
                    r.text = meta["data_rodape"]

if a.sem_assinatura:
    for p in doc.paragraphs:
        if p._element.xpath(".//pic:pic") and not p.text.strip():
            remove(p)

for indice, p in enumerate(doc.paragraphs):
    if p._element.xpath(".//pic:pic"):
        p.paragraph_format.page_break_before = True
        p.paragraph_format.keep_with_next = True
        if indice + 1 < len(doc.paragraphs):
            doc.paragraphs[indice + 1].paragraph_format.keep_with_next = True
        break

os.makedirs(os.path.dirname(os.path.abspath(a.saida)), exist_ok=True)
doc.save(a.saida)
print(f"OK -> {a.saida}")
if pendentes:
    print("Campos mantidos com texto-guia do modelo (preencher):", ", ".join(pendentes))
