#!/usr/bin/env python3
"""Gate de entrega da minuta: confere a minuta do relatório contra a transcrição do próprio caso.

Uso (a partir da raiz do workspace):
  conferir_minuta.py <ID> [--versao NN] [--modo diagnostico|entrega]
  conferir_minuta.py [<ID>] --minuta <minuta.md> --extracao <pasta> [--fluxo <csv>] [--modo ...]

Entradas (casos\\<ID>\\):
  03-relatorios\\minuta-vNN.md            (a mais recente, se --versao não for indicada)
  01-extracao\\<doc>\\transcricao.md       (páginas marcadas "## Página N")
  01-extracao\\<doc>\\relatorio_extracao.json  (pendentes_transcricao_visual, conferir_visualmente)
  02-analise\\fluxo-financeiro.csv         (opcional: só reconhece totais calculados)

Saída: 03-relatorios\\conferencia-vNN.md (tabela legível) e conferencia-vNN.json (ao lado da minuta).
Código de saída: diagnostico -> sempre 0; entrega -> 1 se houver achado BLOQUEIA, senão 0;
                 2 -> erro de entrada (caso, minuta ou pasta inexistente), em qualquer modo.

BLOQUEIA
  PENDENTE            texto-guia do modelo / campo pendente ({...}, [local, Estado], PREENCHER, XXX, [PENDENTE])
  CABECALHO_AUSENTE   campo do cabeçalho lido pelo gerar_docx.py vazio ou ausente
  REFERENCIA_INVALIDA referencia com BO ou IP local, ou sem IPe/Processo (regra 13: só "IPe nº … / Processo nº …")
  SECAO_AUSENTE       "## RESUMO DOS FATOS", "## DILIGÊNCIAS REALIZADAS" ou "## CONCLUSÃO" ausente ou vazia
  PAGINA_INEXISTENTE  "pág. N" que não existe em nenhum documento extraído do caso
  NAO_LOCALIZADO      CPF/CNPJ, chave Pix, agência/conta, telefone, placa, ID de transação ou valor R$
                      que não aparece em nenhuma página
  OUTRA_PAGINA        o dado aparece, mas só em página diferente da citada
  SEM_REFERENCIA      frase (ou linha de tabela) com dado verificável sem nenhuma citação de pág./fls.
  SEM_EXTRACAO        o caso não tem transcricao.md: nada pode ser conferido
REVISAR (não bloqueia)
  PAGINA_PENDENTE / PAGINA_CONFERIR   cita página pendente de transcrição visual / a conferir na imagem
  DIGITO_INCERTO      "[dígito incerto]" ou dado com "?"
  AUTORIA_AFIRMATIVA  linguagem de autoria/culpa afirmativa sem "em tese", "investigado(a)", "há indícios"
  APROXIMADO          dado só confere depois de normalizar confusões típicas de OCR (O/0, I/1, S/5, B/8)
  CALCULO             valor que não está nos autos, mas é soma/diferença de valores citados ou total do fluxo
  CITA_SO_FLS         dado citado só por fls. (sem pág.): existe nos autos, mas a folha não é mapeável
  SECAO_DESCONHECIDA  "## Título" fora das três seções: o gerar_docx.py descarta esse conteúdo
  GENERO_DELEGADO     delegado_genero ausente ou diferente de M/F (regra 10)
  CABECALHO_INCOMPLETO  data_rodape ausente (o rodapé do DOCX fica com a data do modelo)

Comparação: números só pelos dígitos (máscara * e dígito incerto ? valem como curinga); valores em
Decimal a partir de "R$ 1.234,56". O script nunca completa, deduz ou corrige dado e nunca altera a minuta
(o SHA-256 é conferido antes e depois). É a primeira passagem, automática: não substitui a leitura humana
nem a conferência da imagem da página.
"""
import argparse
import csv
import datetime
import hashlib
import json
import os
import re
import sys
import unicodedata
from decimal import Decimal, InvalidOperation

# ---------- workspace (mesma lógica do V01) ----------


def ws_padrao():
    """Workspace CPJ: CPJ_WORKSPACE > 1ª pasta acima deste script com casos/ e modelos/ > cwd com casos/ > erro."""
    if os.environ.get("CPJ_WORKSPACE"):
        return os.environ["CPJ_WORKSPACE"]
    d = os.path.dirname(os.path.abspath(__file__))
    while True:
        if os.path.isdir(os.path.join(d, "casos")) and os.path.isdir(os.path.join(d, "modelos")):
            return d
        if os.path.dirname(d) == d:
            break
        d = os.path.dirname(d)
    if os.path.isdir(os.path.join(os.getcwd(), "casos")):
        return os.getcwd()
    raise SystemExit("Workspace CPJ não encontrado: defina CPJ_WORKSPACE ou execute a partir da pasta do workspace "
                     "(a que contém as pastas casos e modelos).")


# ---------- regras ----------
SECOES = ["RESUMO DOS FATOS", "DILIGÊNCIAS REALIZADAS", "CONCLUSÃO"]  # como no gerar_docx.py
CABECALHO = ["ordem_servico", "referencia", "natureza", "investigados", "vitimas", "local", "data_fatos",
             "local_data", "delegado"]

RE_PENDENTES = [
    (re.compile(r"\{[^{}\n]{1,200}\}"), "texto-guia do modelo entre chaves"),
    (re.compile(r"\[\s*local,\s*Estado\s*\]", re.I), "texto-guia [local, Estado]"),
    (re.compile(r"\[\s*PENDENTE[^\]\n]*\]", re.I), "marcação [PENDENTE]"),
    (re.compile(r"\bPREENCHER\b"), "campo a preencher"),
    (re.compile(r"(?<!\d[.\-])\bX{3,}\b(?![.\-]\d)"), "marcador XXX"),  # não pega máscara XXX.456.789-XX
    (re.compile(r"Nome do Delegado", re.I), "texto-guia Nome do Delegado"),
    (re.compile(r"<(?!/?(?:br|b|i|u|p|sup|sub)\s*/?>)[^<>\n]{2,80}>"), "espaço reservado <...>"),
    (re.compile(r"\bDD/MM/AAAA\b|\bAAAA-MM-DD\b"), "data em formato de modelo"),
]
RE_PREENCHER_MIN = re.compile(r"[\[(]\s*preencher[^\])\n]*[\])]", re.I)

D = r"[\d?*]"  # dígito, dígito incerto (?) ou máscara (*)
PADROES = [  # (tipo, regex, grupo com o dado)
    ("id_transacao", re.compile(r"\b(E\d{8}[0-9A-Za-z]{23})\b"), 1),
    ("chave_pix", re.compile(r"(?<![\w.+-])([\w.+-]+@[\w-]+(?:\.[\w-]+)+)"), 1),
    ("chave_pix", re.compile(r"\b([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})\b"), 1),
    ("cnpj", re.compile(rf"(?<![\d?*])({D}{{2}}\.{D}{{3}}\.{D}{{3}}/{D}{{4}}-{D}{{2}})(?![\d?*])"), 1),
    ("cnpj", re.compile(r"\bCNPJ\s*(?:n[º°o.]\s*)?(?:[:\-]\s*)?(\d{14})\b"), 1),
    ("cpf", re.compile(rf"(?<![\d?*.])({D}{{3}}\.{D}{{3}}\.{D}{{3}}-{D}{{2}})(?![\d?*])"), 1),
    ("cpf", re.compile(r"\bCPF\s*(?:n[º°o.]\s*)?(?:[:\-]\s*)?(\d{11})\b"), 1),
    ("telefone", re.compile(rf"((?:\+?55\s?)?\({D}{{2}}\)\s?{D}{{4,5}}[-\s]?{D}{{4}})(?![\d?*])"), 1),
    ("telefone", re.compile(rf"\b(?:telefones?|celular(?:es)?|fones?|whats(?:app)?|tel\.)\s*(?:n[º°o.]\s*)?(?:[:\-]\s*)?"
                            rf"((?:\+?55\s?)?(?:{D}{{2}}\s?)?{D}{{4,5}}-?{D}{{4}})(?![\d?*])", re.I), 1),
    ("agencia", re.compile(rf"\b(?:ag[êe]ncia|ag\.)\s*(?:n[º°o.]\s*)?(?:[:\-]\s*)?({D}[\d?*.\-]*{D})", re.I), 1),
    ("conta", re.compile(rf"\b(?:conta(?:[\s-]+(?:corrente|poupan[çc]a|(?:de\s+)?pagamento|digital))?|c/c|c\.c\.)\s*"
                         rf"(?:n[º°o.]\s*)?(?:[:\-]\s*)?({D}[\d?*.\-/]*{D})", re.I), 1),
    ("placa", re.compile(r"\b([A-Z]{3}-?\d[A-Z0-9]\d{2})\b"), 1),
    ("valor", re.compile(r"R\$\s*(-?\s*(?:\d{1,3}(?:\.\d{3})+|\d+),[\d?]{2})(?!\d)"), 1),
]
NUMERICOS = {"cnpj", "cpf", "telefone", "agencia", "conta"}

RE_PAG = re.compile(
    r"(?<![\w])(?:p[áa]g(?:inas?|s)?\.?|p\.(?=\s*\d{1,5}[^()\n;]{0,20}?\bdo\s+(?:PDF|arquivo)))\s*(\d{1,5})"
    r"((?:\s*(?:,|-|–|\ba\b|\be\b)\s*\d{1,5}(?!\d|,\d))*)", re.I)
RE_FLS = re.compile(r"(?<![\w])fls?\.?\s*(\d{1,5})((?:\s*(?:,|-|–|/|\ba\b|\be\b)\s*\d{1,5}(?!\d|,\d))*)", re.I)
RE_LISTA = re.compile(r"(,|-|–|/|\ba\b|\be\b)\s*(\d{1,5})", re.I)

RE_INCERTO = re.compile(r"\[\s*d[íi]gito\s+incerto\s*\]", re.I)
RE_CALCULO = re.compile(r"c[áa]lculo|calculad|\bsoma(?:d[oa]s?|m|ndo)?\b|somat[óo]rio|totaliz|diferen[çc]a|subtra", re.I)
AUTORIA = [re.compile(x, re.I) for x in (
    r"\b(?:é|foi|seria|era)\s+(?:o|a)\s+autor(?:a)?\b",
    r"\bautor(?:a|es|as)?\s+d[oa]s?\s+(?:crime|golpe|fato|delito|estelionato|fraude)s?\b",
    r"\b(?:praticou|praticaram|cometeu|cometeram|aplicou|aplicaram|perpetrou|perpetraram)\b",
    r"\b(?:restou|ficou|est[áa]|foi|resta)\s+comprovad[oa]s?\b",
    r"\bsem\s+d[úu]vida\b", r"\b(?:certamente|obviamente|indubitavelmente|claramente)\b",
    r"\bculpad[oa]s?\b",
)]
PEJORATIVOS = [re.compile(x, re.I) for x in (
    r"\bcriminos[oa]s?\b", r"\bgolpistas?\b", r"\bestelionat[áa]ri[oa]s?\b", r"\blaranjas?\b", r"\bmeliantes?\b",
)]
RE_RESSALVA = re.compile(r"\bem tese\b|\binvestigad[oa]s?\b|\bind[íi]cios?\b|\bsupost[oa]s?\b|\bsupostamente\b"
                         r"|\bn[ãa]o\b|\bposs[íi]vel\b|\bprov[áa]vel\b", re.I)

ABREVIACOES = {"dr", "dra", "sr", "sra", "srs", "art", "arts", "n", "nº", "fl", "fls", "pág", "págs", "pag", "p",
               "ag", "av", "r", "prof", "exmo", "exma", "ltda", "s.a", "c", "cc", "inc", "tel", "ref", "doc", "obs"}
OCR = str.maketrans({"O": "0", "o": "0", "D": "0", "Q": "0", "I": "1", "l": "1", "|": "1", "S": "5", "s": "5",
                     "B": "8", "Z": "2", "z": "2", "G": "6"})


def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


RE_REF_BO = re.compile(r"\b(?:b\.?\s?o\.?|boletim|rdo|registro\s+digital)\b", re.I)
RE_REF_IP_LOCAL = re.compile(r"\bIP\b(?!\s*e)|inqu[ée]rito\s+policial(?!\s+eletr)", re.I)
RE_REF_IPE = re.compile(r"\bIPe\b\s*(?:n[º°o.]*\s*)?\S*\d", re.I)
RE_REF_PROC = re.compile(r"\bprocesso\b\s*(?:n[º°o.]*\s*)?\S*\d", re.I)


def problemas_referencia(ref):
    """Regra 13 (determinação de 30/09/2026): só IPe e Processo; nunca BO nem IP local."""
    r = sem_acento(ref)
    p = []
    if RE_REF_BO.search(r):
        p.append("referência com número de BO: usar somente 'IPe nº … / Processo nº …'")
    if RE_REF_IP_LOCAL.search(r):
        p.append("referência com número de IP local: usar somente 'IPe nº … / Processo nº …'")
    if not RE_REF_IPE.search(r):
        p.append("referência sem número do IPe")
    if not RE_REF_PROC.search(r):
        p.append("referência sem número do Processo Judicial")
    return p


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 16), b""):
            h.update(bloco)
    return h.hexdigest()


def dec_brl(s):
    try:
        return abs(Decimal(re.sub(r"[^\d,]", "", s).replace(",", ".")))
    except InvalidOperation:
        return None


def fmt_brl(v):
    return "R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ---------- transcrição ----------
RE_TOKEN_NUM = re.compile(r"[\d*?(](?:[\d*?.\-/()]|\s(?=[\d*?(]))*")
RE_MOEDA_PAG = re.compile(r"(?<![\d.,])((?:\d{1,3}(?:[.\s]\d{3})+|\d+),\d{2})(?!\d)")


def indexar_pagina(texto):
    """Formas normalizadas do texto de uma página: exata e com correção de confusões típicas de OCR."""
    formas = {}
    for nome, t in (("exato", texto), ("ocr", texto.translate(OCR))):
        nums = ["".join(c for c in m.group(0) if c.isdigit() or c in "*?") for m in RE_TOKEN_NUM.finditer(t)]
        valores = {v for v in (dec_brl(m.group(1)) for m in RE_MOEDA_PAG.finditer(t)) if v is not None}
        formas[nome] = {"nums": [n for n in nums if n], "valores": valores,
                        "alnum": re.sub(r"[^0-9A-Z]", "", sem_acento(t).upper()),
                        "min": re.sub(r"\s+", "", t.lower())}
    return formas


def carregar_documentos(pasta):
    """Lê <pasta>\\<doc>\\transcricao.md (ou <pasta>\\transcricao.md). Retorna lista de documentos."""
    alvos = []
    if os.path.isfile(os.path.join(pasta, "transcricao.md")):
        alvos.append(pasta)
    if os.path.isdir(pasta):
        for nome in sorted(os.listdir(pasta)):
            sub = os.path.join(pasta, nome)
            if os.path.isfile(os.path.join(sub, "transcricao.md")):
                alvos.append(sub)
    docs = []
    for d in alvos:
        paginas, pendentes, conferir, atual, buf = {}, set(), set(), None, []

        def fecha():
            if atual is not None:
                bruto = "\n".join(buf)
                if re.search(r"pendente-transcricao-visual|\[PENDENTE: transcri", bruto):
                    pendentes.add(atual)
                if re.search(r"CONFERIR", "\n".join(re.findall(r"<!--.*?-->", bruto, flags=re.S))):
                    conferir.add(atual)
                limpo = re.sub(r"<!--.*?-->", " ", bruto, flags=re.S)
                limpo = re.sub(r"^\s*---\s*$", " ", limpo, flags=re.M)
                paginas[atual] = limpo

        for ln in open(os.path.join(d, "transcricao.md"), encoding="utf-8-sig"):
            m = re.match(r"^##\s+P[áa]gina\s+(\d+)\b", ln)
            if m:
                fecha()
                atual, buf = int(m.group(1)), []
                continue
            buf.append(ln.rstrip("\n"))
        fecha()
        rel = os.path.join(d, "relatorio_extracao.json")
        if os.path.isfile(rel):
            try:
                r = json.load(open(rel, encoding="utf-8-sig"))
                pendentes.update(int(x) for x in r.get("pendentes_transcricao_visual", []) or [])
                conferir.update(int(x) for x in r.get("conferir_visualmente", []) or [])
            except (ValueError, TypeError):
                pass
        docs.append({"doc": os.path.basename(os.path.normpath(d)), "paginas": paginas,
                     "indice": {n: indexar_pagina(t) for n, t in paginas.items()},
                     "pendentes": pendentes, "conferir": conferir})
    return docs


def totais_fluxo(caminho):
    """Valores reconhecidos como cálculo a partir do fluxo-financeiro.csv (totais, não fatos)."""
    if not caminho or not os.path.isfile(caminho):
        return set()
    try:
        linhas = list(csv.DictReader(open(caminho, encoding="utf-8-sig"), delimiter=";"))
    except (OSError, csv.Error):
        return set()
    grupos = {}
    for ln in linhas:
        bruto = (ln.get("valor") or "").strip().replace("R$", "").strip()
        if not bruto:
            continue
        try:
            v = abs(Decimal(bruto.replace(".", "").replace(",", ".")) if "," in bruto else Decimal(bruto))
        except InvalidOperation:
            continue
        grupos.setdefault(("geral",), []).append(v)
        for col in ("camada", "destino_titular", "origem_titular", "meio", "data"):
            if (ln.get(col) or "").strip():
                grupos.setdefault((col, ln[col].strip()), []).append(v)
    return {sum(vs) for vs in grupos.values() if len(vs) > 1}


# ---------- minuta ----------


def ler_minuta(caminho):
    bruto = open(caminho, encoding="utf-8-sig").read()
    # comentários <!-- --> são removidos pelo gerar_docx.py; preserva as quebras para manter a numeração de linhas
    texto = re.sub(r"<!--.*?-->", lambda m: "\n" * m.group(0).count("\n"), bruto, flags=re.S)
    linhas = texto.split("\n")
    meta, inicio_corpo, tem_frontmatter = {}, 0, False
    m = re.match(r"\s*---\s*\n(.*?)\n---\s*\n", texto, flags=re.S)
    if m:
        tem_frontmatter = True
        for ln in m.group(1).splitlines():
            if ":" in ln:
                k, v = ln.split(":", 1)
                meta[k.strip().lower()] = v.strip()
        inicio_corpo = texto[:m.end()].count("\n")
    return linhas, meta, inicio_corpo, tem_frontmatter


def secoes_da_minuta(linhas, inicio):
    """Replica o gerar_docx.py: '## Nome' abre seção; '###' é subtítulo. Retorna [(secao, [(nº linha, texto)])]."""
    out, atual, cabecalhos = [], None, []
    for i in range(inicio, len(linhas)):
        ln = linhas[i]
        t = re.match(r"^##\s+(.+?)\s*$", ln)
        if t and not ln.startswith("###"):
            nome = t.group(1).strip().upper()
            atual = next((s for s in SECOES if s in nome or nome in s), nome)
            cabecalhos.append((i + 1, t.group(1).strip(), atual))
            out.append((atual, []))
            continue
        if atual is not None:
            out[-1][1].append((i + 1, ln))
    return out, cabecalhos


def blocos(linhas_num):
    """Agrupa como o gerar_docx.py: (tipo, linha, texto, marcos) com tipo 'p'|'li'|'h' e ('tab', linha, [(linha,
    texto)], None). marcos = [(deslocamento no texto, nº da linha)] para localizar cada frase do parágrafo."""
    out, par, tab = [], [], []

    def fecha_par():
        if par:
            texto, marcos = "", []
            for n, s in par:
                if texto:
                    texto += " "
                marcos.append((len(texto), n))
                texto += s.strip()
            out.append(("p", par[0][0], texto, marcos))
            par.clear()

    def fecha_tab():
        if tab:
            rows = [(n, s) for n, s in tab if not re.fullmatch(r"\|?[\s:\-|]+\|?", s)]
            if rows:
                out.append(("tab", rows[0][0], rows, None))
            tab.clear()

    for n, ln in linhas_num:
        s = ln.strip()
        if s.startswith("|"):
            fecha_par(); tab.append((n, s)); continue
        fecha_tab()
        if not s:
            fecha_par(); continue
        if s.startswith("###"):
            fecha_par(); out.append(("h", n, s.lstrip("#").strip(), None)); continue
        if re.match(r"^([-*•]|\d+[.)])\s+", s):
            fecha_par(); out.append(("li", n, s, [(0, n)])); continue
        par.append((n, s))
    fecha_par(); fecha_tab()
    return out


def frases(texto):
    """Divide em frases sem quebrar abreviações (pág., fls., Dr., art., nº...). Retorna [(deslocamento, frase)]."""
    partes, ini = [], 0
    for m in re.finditer(r"(?<=[.;!])\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ(\"“])", texto):
        antes = texto[ini:m.start()]
        ult = re.search(r"([\w.º]+)[.;!]$", antes)
        if ult and ult.group(1).lower().rstrip(".") in ABREVIACOES:
            continue
        partes.append((ini, antes))
        ini = m.end()
    partes.append((ini, texto[ini:]))
    return [(i, p.strip()) for i, p in partes if p.strip()]


def expandir(primeiro, resto):
    out, ant = [int(primeiro)], int(primeiro)
    for sep, n in RE_LISTA.findall(resto or ""):
        n = int(n)
        if sep.lower() in ("-", "–", "a", "/") and ant < n <= ant + 200:
            out += list(range(ant + 1, n + 1))
        else:
            out.append(n)
        ant = n
    return out


def citacoes(txt):
    pags, fls = [], []
    for m in RE_PAG.finditer(txt):
        pags += expandir(m.group(1), m.group(2))
    for m in RE_FLS.finditer(txt):
        fls += expandir(m.group(1), m.group(2))
    return sorted(set(pags)), sorted(set(fls))


def extrair_dados(txt):
    t = RE_PAG.sub(lambda m: " " * len(m.group(0)), txt)
    t = RE_FLS.sub(lambda m: " " * len(m.group(0)), t)
    usados, out = [], []
    for tipo, rx, g in PADROES:
        for m in rx.finditer(t):
            a, b = m.span(g)
            if any(a < y and x < b for x, y in usados):
                continue
            dado = m.group(g).strip()
            if tipo == "valor":
                dado = "R$ " + re.sub(r"\s+", "", dado)
            if tipo in NUMERICOS and sum(c.isdigit() for c in dado) < 4:
                continue
            usados.append((a, b))
            out.append((a, tipo, dado))
    out.sort()
    return [(tipo, dado) for _, tipo, dado in out]


def canon_num(s):
    return "".join(c for c in s if c.isdigit() or c in "*?")


def rx_curinga(canon):
    return re.compile("".join(re.escape(c) if c.isdigit() else r"[\d*?]" for c in canon))


def variantes_num(tipo, dado):
    c = canon_num(dado)
    vs = [c]
    if tipo == "telefone" and len(c) in (12, 13) and c.startswith("55"):
        vs.append(c[2:])
    return vs


def procura(tipo, dado, formas, ocr=False):
    """True se o dado aparece na forma normalizada da página (ocr=True: forma com confusões de OCR corrigidas)."""
    if tipo == "valor":
        if "?" in dado:
            rx = rx_curinga(canon_num(dado))
            return any(rx.search(canon_num(fmt_brl(v))) for v in formas["valores"])
        v = dec_brl(dado)
        return v is not None and v in formas["valores"]
    if tipo in NUMERICOS:
        for c in variantes_num(tipo, dado):
            rx = rx_curinga(c)
            if any(rx.search(n) for n in formas["nums"]):
                return True
        return False
    if ocr:
        dado = dado.translate(OCR)
    if tipo == "chave_pix" and "@" in dado:
        return re.sub(r"\s+", "", dado.lower()) in formas["min"]
    alvo = re.sub(r"[^0-9A-Z]", "", sem_acento(dado).upper())
    return bool(alvo) and alvo in formas["alnum"]


# ---------- conferência ----------


def conferir(caminho_minuta, docs, totais):
    linhas, meta, inicio, tem_fm = ler_minuta(caminho_minuta)
    achados, conferidos = [], []
    existentes = {}
    for d in docs:
        for n in d["paginas"]:
            existentes.setdefault(n, []).append(d)

    def add(nivel, codigo, linha, detalhe, secao="", tipo="", dado="", citado="", paginas=None, localizado=None, trecho=""):
        reg = {"nivel": nivel, "codigo": codigo, "linha": linha, "secao": secao, "tipo": tipo, "dado": dado,
               "citado": citado, "paginas_citadas": paginas or [], "localizado_em": localizado or [],
               "detalhe": detalhe, "trecho": (trecho[:200] + ("…" if len(trecho) > 200 else "")) if trecho else ""}
        (conferidos if nivel == "OK" else achados).append(reg)

    # 1. texto-guia / campos pendentes (minuta inteira, fora de comentários)
    for i, ln in enumerate(linhas, 1):
        vistos = []
        for rx, desc in RE_PENDENTES + [(RE_PREENCHER_MIN, "campo a preencher")]:
            for m in rx.finditer(ln):
                a0, b0 = m.span()
                if any(a0 < y and x < b0 for x, y in vistos) or RE_INCERTO.fullmatch(m.group(0)):
                    continue
                vistos.append((a0, b0))
                add("BLOQUEIA", "PENDENTE", i, f"{desc}: preencher com dado dos autos ou retirar", dado=m.group(0),
                    trecho=ln.strip())

    # 2. cabeçalho
    if not tem_fm:
        add("BLOQUEIA", "CABECALHO_AUSENTE", 1, "minuta sem cabeçalho YAML (--- ... ---): o DOCX sairia com os "
            "textos-guia do modelo", dado=", ".join(CABECALHO))
    else:
        for k in CABECALHO:
            v = meta.get(k, "")
            if not v or v in ("...", "…", "-", "—"):
                add("BLOQUEIA", "CABECALHO_AUSENTE", 1, f"campo '{k}' vazio ou ausente: o DOCX manteria o texto-guia do modelo",
                    dado=k)
        if not meta.get("data_rodape"):
            add("REVISAR", "CABECALHO_INCOMPLETO", 1, "data_rodape ausente: o rodapé do DOCX fica com a data do modelo",
                dado="data_rodape")
        ref = meta.get("referencia", "")
        if ref and ref not in ("...", "…", "-", "—"):
            for problema in problemas_referencia(ref):
                add("BLOQUEIA", "REFERENCIA_INVALIDA", 1, problema, dado=ref)
        if str(meta.get("delegado_genero", "")).strip().upper() not in ("M", "F"):
            add("REVISAR", "GENERO_DELEGADO", 1, "delegado_genero ausente ou diferente de M/F: saudação e "
                "endereçamento ficam pendentes (informar M ou F; não inferir pelo nome)", dado="delegado_genero")

    # 3. seções obrigatórias
    secoes, cabecalhos = secoes_da_minuta(linhas, inicio)
    for s in SECOES:
        conteudo = [ln for sec, lns in secoes if sec == s for _, ln in lns if ln.strip()]
        if conteudo:
            continue
        if any(sec == s for sec, _ in secoes):
            add("BLOQUEIA", "SECAO_AUSENTE", 0, f"seção '## {s}' sem conteúdo: o DOCX manteria o texto-guia do modelo",
                dado=s)
            continue
        dica = ""
        alvo = sem_acento(s)
        for i, ln in enumerate(linhas[inicio:], inicio + 1):
            if alvo in sem_acento(ln.upper()) and ln.lstrip().startswith("#"):
                dica = (f" (linha {i}: '{ln.strip()}' não é reconhecido pelo gerar_docx.py; use '## {s}', nível 2 e "
                        "com acento)")
                break
        add("BLOQUEIA", "SECAO_AUSENTE", 0, f"seção obrigatória '## {s}' ausente{dica}", dado=s)
    for n, titulo, sec in cabecalhos:
        if sec not in SECOES:
            add("REVISAR", "SECAO_DESCONHECIDA", n, f"'## {titulo}' não é seção do modelo: o gerar_docx.py descarta o "
                "conteúdo dela", dado=titulo)

    # 4. conferência de dados contra as páginas
    if not docs:
        add("BLOQUEIA", "SEM_EXTRACAO", 0, "nenhuma transcricao.md em 01-extracao: citações e dados não podem ser "
            "conferidos; processe os documentos do caso antes")
    for sec, lns in secoes:
        if sec not in SECOES:
            continue
        bls = blocos(lns)
        for k, (tipo_b, n0, val, marcos) in enumerate(bls):
            if tipo_b == "h":
                continue
            unidades = []  # (linha, texto, citações herdadas, valores do contexto para cálculo)
            if tipo_b == "tab":
                herdada = ""
                if k > 0 and bls[k - 1][0] in ("p", "li"):
                    herdada += " " + bls[k - 1][2]
                if k + 1 < len(bls) and bls[k + 1][0] in ("p", "li") and re.match(r"^\W*fonte", bls[k + 1][2], re.I):
                    herdada += " " + bls[k + 1][2]
                cab = val[0][1]
                vals_tab = [dec_brl(x) for _, r in val for x in re.findall(r"R\$\s*-?\s*((?:\d{1,3}(?:\.\d{3})+|\d+),\d{2})", r)]
                for j, (nl, row) in enumerate(val):
                    if j == 0 and not extrair_dados(row):
                        continue
                    unidades.append((nl, row, cab + " " + herdada, [v for v in vals_tab if v is not None]))
            else:
                for pos, fr in frases(val):
                    linha = max((n for o, n in marcos if o <= pos), default=n0)
                    unidades.append((linha, fr, "", None))
            for nl, u, herdada, ctx_vals in unidades:
                avaliar(u, nl, sec, herdada, ctx_vals, docs, existentes, totais, add)

    # página pendente / a conferir: um achado por página, com todas as linhas que a citam
    agrupados, final = {}, []
    for a in achados:
        if a["codigo"] in ("PAGINA_PENDENTE", "PAGINA_CONFERIR") and not a["tipo"]:
            chave = (a["codigo"], a["dado"], a["detalhe"])
            if chave in agrupados:
                agrupados[chave]["linhas"].append(a["linha"])
                continue
            a["linhas"] = [a["linha"]]
            agrupados[chave] = a
        final.append(a)
    for a in agrupados.values():
        linhas_cit = sorted(set(a.pop("linhas")))
        if len(linhas_cit) > 1:
            a["detalhe"] += f" — citada nas linhas {', '.join(map(str, linhas_cit))}"
    achados[:] = final
    ordem = {"BLOQUEIA": 0, "REVISAR": 1}
    achados.sort(key=lambda a: (ordem.get(a["nivel"], 9), a["linha"]))
    return meta, achados, conferidos


def eh_calculo(dado, valores_unidade, ctx_vals, totais):
    """Valor ausente dos autos que confere com soma/diferença dos demais valores da frase ou da tabela,
    ou com um total do fluxo-financeiro.csv."""
    v = dec_brl(dado)
    if v is None:
        return False
    outros = [x for x in valores_unidade if x is not None and x != v]
    cands = set(totais)
    if len(outros) >= 2:
        cands.add(sum(outros))
    cands |= {abs(a - b) for a in outros for b in outros if a != b}
    outros_t = [x for x in (ctx_vals or []) if x != v]
    if len(outros_t) >= 2:
        cands.add(sum(outros_t))
    return v in cands


def avaliar(u, nl, sec, herdada, ctx_vals, docs, existentes, totais, add):
    pags, fls = citacoes(u)
    if not pags and not fls and herdada:
        pags, fls = citacoes(herdada)
    citado = "; ".join(([f"pág. {', '.join(map(str, pags))}"] if pags else []) +
                       ([f"fls. {', '.join(map(str, fls))}"] if fls else [])) or "—"
    comum = dict(secao=sec, citado=citado, trecho=u)
    # páginas citadas
    alvo = []
    for p in pags:
        if p not in existentes:
            add("BLOQUEIA", "PAGINA_INEXISTENTE", nl, f"pág. {p} não existe em nenhum documento extraído "
                f"({', '.join(d['doc'] + ': ' + str(max(d['paginas'] or [0])) + ' p.' for d in docs) or 'sem extração'})",
                dado=f"pág. {p}", paginas=[p], **comum)
            continue
        for d in existentes[p]:
            alvo.append((d, p))
            if p in d["pendentes"]:
                add("REVISAR", "PAGINA_PENDENTE", nl, f"pág. {p} ({d['doc']}) está pendente de transcrição visual: "
                    "conferir o trecho na imagem da página", dado=f"pág. {p}", paginas=[p], **comum)
            elif p in d["conferir"]:
                add("REVISAR", "PAGINA_CONFERIR", nl, f"pág. {p} ({d['doc']}) está marcada para conferência visual "
                    "(OCR de baixa confiança)", dado=f"pág. {p}", paginas=[p], **comum)
    # linguagem
    if not RE_RESSALVA.search(u):
        for rx in AUTORIA:
            m = rx.search(u)
            if m:
                add("REVISAR", "AUTORIA_AFIRMATIVA", nl, f"“{m.group(0)}” sem ressalva (“em tese”, “investigado(a)”, "
                    "“há indícios”): reescrever em linguagem condicional", dado=m.group(0), **comum)
                break
    for rx in PEJORATIVOS:
        m = rx.search(u)
        if m:
            add("REVISAR", "AUTORIA_AFIRMATIVA", nl, f"termo “{m.group(0)}”: usar investigado(a) / titular da conta "
                "recebedora", dado=m.group(0), **comum)
    # dados verificáveis
    dados = extrair_dados(u)
    incerto_marcado = False
    valores_unidade = [dec_brl(d) for t, d in dados if t == "valor" and "?" not in d]
    for tipo, dado in dados:
        base = dict(tipo=tipo, dado=dado, paginas=pags, **comum)
        if not pags and not fls:
            add("BLOQUEIA", "SEM_REFERENCIA", nl, "dado verificável sem citação de pág./fls.: indicar a página do PDF "
                "(e fls., se houver)", **base)
            continue
        achou = sorted({f"{d['doc']} p. {p}" for d, p in alvo if procura(tipo, dado, d["indice"][p]["exato"])})
        incerto = "?" in dado
        if achou:
            if incerto:
                incerto_marcado = True
                add("REVISAR", "DIGITO_INCERTO", nl, "dado com dígito incerto confere com a página só pelos dígitos "
                    "legíveis: conferir a imagem e manter a marcação", localizado=achou, **base)
            else:
                add("OK", "CONFIRMADO", nl, "", localizado=achou, **base)
            continue
        aprox = sorted({f"{d['doc']} p. {p}" for d, p in alvo if procura(tipo, dado, d["indice"][p]["ocr"], True)})
        if aprox:
            add("REVISAR", "APROXIMADO", nl, "confere só após normalizar confusões típicas de OCR: conferir a imagem",
                localizado=aprox, **base)
            continue
        visuais = [(d, p) for d, p in alvo if p in d["pendentes"] or p in d["conferir"]]
        outras = sorted({f"{d['doc']} p. {p}" for d in docs for p in d["paginas"]
                         if procura(tipo, dado, d["indice"][p]["exato"])
                         or procura(tipo, dado, d["indice"][p]["ocr"], True)})
        if tipo == "valor" and not outras and eh_calculo(dado, valores_unidade, ctx_vals, totais):
            add("REVISAR", "CALCULO", nl, "valor não consta dos autos, mas confere com soma/diferença de valores "
                "citados ou com total do fluxo-financeiro.csv: demonstrar o cálculo", **base)
            continue
        if visuais:
            d, p = visuais[0]
            cod = "PAGINA_PENDENTE" if p in d["pendentes"] else "PAGINA_CONFERIR"
            add("REVISAR", cod, nl, f"dado não está no texto da pág. {p}, pendente/a conferir: conferir na imagem",
                localizado=outras, **base)
            continue
        if outras and not pags:
            add("REVISAR", "CITA_SO_FLS", nl, "citado só por fls. (não mapeável para página do PDF); o dado existe em "
                + ", ".join(outras[:6]) + ": acrescentar a pág.", localizado=outras, **base)
            continue
        if outras:
            add("BLOQUEIA", "OUTRA_PAGINA", nl, "dado existe nos autos, mas não na página citada: corrigir a referência",
                localizado=outras, **base)
            continue
        if tipo == "valor" and RE_CALCULO.search(u):
            add("REVISAR", "CALCULO", nl, "valor declarado como cálculo, não conferido automaticamente: refazer em "
                "código a partir das páginas citadas", **base)
            continue
        add("BLOQUEIA", "NAO_LOCALIZADO", nl, "não aparece em nenhuma página extraída: verificar transcrição, OCR "
            "ou ausência de fonte (não completar nem corrigir por dedução)", **base)
    if RE_INCERTO.search(u) and not incerto_marcado:
        add("REVISAR", "DIGITO_INCERTO", nl, "trecho com [dígito incerto]: conferir na imagem da página",
            dado="[dígito incerto]", paginas=pags, secao=sec, citado=citado, trecho=u)
    elif not RE_INCERTO.search(u) and any("?" in d for _, d in dados):
        add("REVISAR", "DIGITO_INCERTO", nl, "dado com '?' sem a marcação [dígito incerto]", dado="?", paginas=pags,
            secao=sec, citado=citado, trecho=u)


# ---------- saída ----------


def celula(s):
    return str(s).strip().strip("|").strip().replace("|", "/").replace("\n", " ")


def gerar_md(res):
    r = res["resumo"]
    md = [f"# Conferência da minuta — {res['minuta']}", "",
          f"- Caso: {res.get('caso') or '—'} · modo: **{res['modo']}** · gerado em {res['gerado_em']}",
          f"- SHA-256 da minuta (inalterada): `{res['sha256_minuta']}`",
          f"- Documentos conferidos: " + (", ".join(f"{d['doc']} ({d['paginas']} p.; pendentes: "
                                                    f"{d['pendentes'] or '—'}; a conferir: {d['conferir'] or '—'})"
                                                    for d in res["documentos"]) or "nenhum"),
          "", f"**Resultado: {'APROVADA para entrega' if res['aprovado'] else 'BLOQUEADA'}** — "
          f"BLOQUEIA: {r['BLOQUEIA']} · REVISAR: {r['REVISAR']} · dados confirmados: {r['confirmados']}", ""]
    for nivel, titulo in (("BLOQUEIA", "Bloqueios (corrigir antes da entrega)"),
                          ("REVISAR", "Revisar (não bloqueia; decisão do investigador)")):
        itens = [a for a in res["achados"] if a["nivel"] == nivel]
        md += [f"## {titulo}", ""]
        if not itens:
            md += ["Nenhum.", ""]
            continue
        md += ["| Linha | Código | Dado | Tipo | Citado | Localizado em | Observação | Trecho |",
               "| --- | --- | --- | --- | --- | --- | --- | --- |"]
        for a in itens:
            md.append(f"| {a['linha'] or '—'} | **{a['codigo']}** | {celula(a['dado'])} | {a['tipo'] or '—'} | "
                      f"{celula(a['citado'] or '—')} | {celula(', '.join(a['localizado_em'][:6]) or '—')} | "
                      f"{celula(a['detalhe'])} | {celula(a['trecho'][:140])} |")
        md.append("")
    md += ["## Dados confirmados na página citada", ""]
    if res["conferidos"]:
        md += ["| Linha | Dado | Tipo | Citado | Localizado em |", "| --- | --- | --- | --- | --- |"]
        md += [f"| {c['linha']} | {celula(c['dado'])} | {c['tipo']} | {celula(c['citado'])} | "
               f"{celula(', '.join(c['localizado_em']))} |" for c in res["conferidos"]]
    else:
        md.append("Nenhum.")
    md += ["", "Primeira passagem automática. Não substitui a leitura humana nem a conferência na imagem da página "
           "dos dados críticos. A minuta não foi alterada."]
    return "\n".join(md) + "\n"


def erro(msg):
    print(f"ERRO: {msg}", file=sys.stderr)
    sys.exit(2)


def main():
    ap = argparse.ArgumentParser(description="Gate de entrega da minuta (conferência contra a transcrição do caso).")
    ap.add_argument("id", nargs="?", help="ID do caso (pasta em casos\\)")
    ap.add_argument("--versao", help="versão da minuta (NN de minuta-vNN.md); padrão: a mais recente")
    ap.add_argument("--modo", choices=["diagnostico", "entrega"], default="diagnostico")
    ap.add_argument("--minuta", help="arquivo da minuta (dispensa o ID; uso em testes)")
    ap.add_argument("--extracao", help="pasta com <doc>\\transcricao.md (padrão: casos\\<ID>\\01-extracao)")
    ap.add_argument("--fluxo", help="fluxo-financeiro.csv (padrão: casos\\<ID>\\02-analise\\fluxo-financeiro.csv)")
    a = ap.parse_args()

    base = None
    if a.id:
        if not re.fullmatch(r"[\w.\-]+", a.id):
            erro(f"ID de caso inválido: {a.id}")
        if not (a.minuta and a.extracao):
            try:
                ws = ws_padrao()
            except SystemExit as e:
                erro(str(e))
            base = os.path.join(ws, "casos", a.id)
            if not os.path.isdir(base):
                erro(f"caso não encontrado: {base}")
    elif not (a.minuta and a.extracao):
        erro("informe o ID do caso ou --minuta e --extracao")

    if a.minuta:
        minuta = os.path.abspath(a.minuta)
    else:
        rel = os.path.join(base, "03-relatorios")
        ms = sorted(((int(m.group(1)), f) for f in (os.listdir(rel) if os.path.isdir(rel) else [])
                     for m in [re.fullmatch(r"minuta-v(\d+)\.md", f)] if m))
        if a.versao:
            n = re.sub(r"\D", "", a.versao)
            ms = [x for x in ms if n and x[0] == int(n)]
        if not ms:
            erro(f"minuta não encontrada em {rel}" + (f" (versão {a.versao})" if a.versao else ""))
        minuta = os.path.join(rel, ms[-1][1])
    if not os.path.isfile(minuta):
        erro(f"minuta não encontrada: {minuta}")
    extracao = a.extracao or os.path.join(base, "01-extracao")
    if a.extracao and not os.path.isdir(extracao):
        erro(f"pasta de extração não encontrada: {extracao}")
    fluxo = a.fluxo or (os.path.join(base, "02-analise", "fluxo-financeiro.csv") if base else None)

    hash_antes = sha256(minuta)
    docs = carregar_documentos(extracao)
    meta, achados, conferidos = conferir(minuta, docs, totais_fluxo(fluxo))
    if sha256(minuta) != hash_antes:  # salvaguarda: este script só lê a minuta
        erro("a minuta mudou durante a conferência; rode de novo")

    m = re.search(r"minuta-v(\d+)", os.path.basename(minuta))
    versao = m.group(1) if m else None
    nome = f"conferencia-v{versao}" if versao else "conferencia-" + os.path.splitext(os.path.basename(minuta))[0]
    pasta = os.path.dirname(minuta)
    cont = {}
    for x in achados:
        cont[x["codigo"]] = cont.get(x["codigo"], 0) + 1
    bloqueios = sum(1 for x in achados if x["nivel"] == "BLOQUEIA")
    res = {
        "schema": "cpj-conferencia/1",
        "caso": a.id or meta.get("caso", ""),
        "minuta": os.path.basename(minuta),
        "versao": versao,
        "sha256_minuta": hash_antes,
        "modo": a.modo,
        "gerado_em": datetime.datetime.now().isoformat(timespec="seconds"),
        "aprovado": bloqueios == 0,
        "resumo": {"BLOQUEIA": bloqueios, "REVISAR": len(achados) - bloqueios, "confirmados": len(conferidos),
                   "por_codigo": cont},
        "documentos": [{"doc": d["doc"], "paginas": len(d["paginas"]), "pendentes": sorted(d["pendentes"]),
                        "conferir": sorted(d["conferir"])} for d in docs],
        "arquivos": {"md": os.path.join(pasta, nome + ".md"), "json": os.path.join(pasta, nome + ".json")},
        "achados": achados,
        "conferidos": conferidos,
    }
    with open(res["arquivos"]["json"], "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    with open(res["arquivos"]["md"], "w", encoding="utf-8") as f:
        f.write(gerar_md(res))

    print(f"{'APROVADA' if res['aprovado'] else 'BLOQUEADA'}: {res['minuta']} — BLOQUEIA {bloqueios}, "
          f"REVISAR {len(achados) - bloqueios}, confirmados {len(conferidos)}")
    for x in achados:
        print(f"  [{x['nivel']}] {x['codigo']} (linha {x['linha'] or '—'}) {x['dado']}: {x['detalhe']}")
    print(f"Conferência: {res['arquivos']['md']}")
    sys.exit(1 if (a.modo == "entrega" and bloqueios) else 0)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except (ValueError, OSError):
            pass
    main()
