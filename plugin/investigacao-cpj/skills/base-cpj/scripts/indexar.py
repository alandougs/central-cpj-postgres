#!/usr/bin/env python3
"""Indexa o workspace CPJ: base consolidada de casos (estatística) + índice RAG local (SQLite FTS5).

Uso:  indexar.py [--tudo]        (--tudo reindexa mesmo arquivos sem alteração)

Saídas:
  producao\\base.json, producao\\base.csv   — uma linha por caso (a partir de casos\\*\\caso.json)
  rag\\cpj.sqlite                           — trechos pesquisáveis com metadados + entidades cruzáveis

Indexa (incremental, por SHA-256 do arquivo):
  casos\\*\\01-extracao\\<doc>\\transcricao.md tipo=transcricao  (1 trecho por página; páginas longas em janelas)
  casos\\*\\02-analise\\*.md                tipo=analise      (por título)
  casos\\*\\03-relatorios\\*.md             tipo=relatorio (…-FINAL.md) | minuta | revisao
  calibracao\\*.md                          tipo=calibracao
  acervo\\**\\*.md                          tipo=acervo
  casos\\*\\01-extracao\\<doc>\\entidades.csv e 02-analise\\fluxo-financeiro.csv -> tabela entidades
Tudo local; nenhum dado sai do computador.
"""
import argparse, csv, glob, hashlib, json, os, re, sqlite3, datetime

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


WS = ws_padrao()
CASOS = os.path.join(WS, "casos"); PROD = os.path.join(WS, "producao"); RAGD = os.path.join(WS, "rag")
JANELA, SOBREPOE = 2500, 250

ap = argparse.ArgumentParser()
ap.add_argument("--tudo", action="store_true")
ap.add_argument("--so-base", action="store_true", help="Atualiza somente base.json e base.csv sem reindexar RAG")
a = ap.parse_args()
os.makedirs(PROD, exist_ok=True); os.makedirs(RAGD, exist_ok=True)

# ------------------------------------------------------------ baixa automática (relatório FINAL na pasta)
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import caso as C  # noqa: E402
for d in (sorted(os.listdir(CASOS)) if os.path.isdir(CASOS) else []):
    if d.startswith("_") or not os.path.exists(os.path.join(CASOS, d, "caso.json")): continue
    try:
        if C.baixa_automatica(d): print(f"Baixa automática: {d} (relatório FINAL encontrado em 03-relatorios)")
    except Exception as e:
        print(f"AVISO: baixa automática de {d} falhou: {e}")


# ------------------------------------------------------------ base de casos
def dias(d1, d2):
    try: return (datetime.date.fromisoformat(d2) - datetime.date.fromisoformat(d1)).days
    except Exception: return None


casos = {}
for p in sorted(glob.glob(os.path.join(CASOS, "*", "caso.json"))):
    if os.path.basename(os.path.dirname(p)).startswith("_"): continue
    try: c = json.load(open(p, encoding="utf-8"))
    except Exception as e: print(f"AVISO: {p} ilegível ({e})"); continue
    casos[c.get("id") or os.path.basename(os.path.dirname(p))] = c

linhas = []
for id_, c in casos.items():
    d, ip, fin, res = c.get("datas", {}), c.get("ip", {}), c.get("financeiro", {}), c.get("resultado", {})
    rel = c.get("relatorios", [])
    linhas.append({
        "id": id_, "ordem_servico": c.get("ordem_servico"), "bo": c.get("bo"), "inquerito": c.get("inquerito"),
        "processo": c.get("processo"), "referencia": c.get("referencia"),
        "vitimas": "; ".join(c.get("vitimas") or []), "investigados": "; ".join(c.get("investigados") or []),
        "natureza": c.get("natureza"), "modalidade": c.get("modalidade"), "status": c.get("status"),
        "recebido": d.get("recebido"), "extraido": d.get("extraido"), "analisado": d.get("analisado"),
        "minuta": d.get("minuta"), "entregue": d.get("entregue"),
        "dias_ate_entrega": dias(d.get("recebido"), d.get("entregue")) if d.get("entregue") else None,
        "baixa_origem": (c.get("baixa") or {}).get("origem"),
        "prazo": c.get("prazo"), "situacao_prazo": C.situacao_prazo(c),
        "no_prazo": (d.get("entregue") <= c["prazo"]) if (d.get("entregue") and c.get("prazo")) else None,
        "prioridade": c.get("prioridade"), "requisitante": c.get("requisitante"),
        "paginas_ip": ip.get("paginas"), "paginas_ocr": (ip.get("metodos") or {}).get("ocr-tesseract"),
        "paginas_visual": (ip.get("metodos") or {}).get("transcricao-visual-llm"),
        "n_vitimas": len(c.get("vitimas") or []), "n_investigados": len(c.get("investigados") or []),
        "prejuizo_declarado": fin.get("prejuizo_declarado"), "prejuizo_documentado": fin.get("prejuizo_documentado"),
        "valor_rastreado": fin.get("valor_rastreado"), "transacoes": fin.get("transacoes"),
        "contas_destino": fin.get("contas_destino"), "camadas": fin.get("camadas"),
        "autoria": res.get("autoria"), "sugestoes_providencias": res.get("sugestoes_providencias"),
        "n_relatorios": len(rel), "versoes_ultimo": (rel[-1].get("versoes") if rel else None),
        "horas_trabalho": c.get("horas_trabalho"),
    })

json.dump({"gerado_em": datetime.datetime.now().isoformat(timespec="seconds"), "casos": linhas},
          open(os.path.join(PROD, "base.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
if linhas:
    with open(os.path.join(PROD, "base.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0].keys()), delimiter=";"); w.writeheader(); w.writerows(linhas)
print(f"Base: {len(linhas)} caso(s) -> producao\\base.json / base.csv")
if a.so_base:
    sys.exit(0)

# ------------------------------------------------------------ RAG (SQLite FTS5)
db = sqlite3.connect(os.path.join(RAGD, "cpj.sqlite"))
db.executescript("""
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS docs(arquivo TEXT PRIMARY KEY, caso TEXT, tipo TEXT, sha TEXT, indexado_em TEXT);
CREATE TABLE IF NOT EXISTS trechos(id INTEGER PRIMARY KEY, arquivo TEXT, caso TEXT, tipo TEXT, pagina INTEGER,
  fls TEXT, secao TEXT, texto TEXT, modalidade TEXT, natureza TEXT, embedding BLOB);
CREATE INDEX IF NOT EXISTS ix_trechos_arq ON trechos(arquivo);
CREATE INDEX IF NOT EXISTS ix_trechos_caso ON trechos(caso);
CREATE VIRTUAL TABLE IF NOT EXISTS trechos_fts USING fts5(texto, secao, content='trechos', content_rowid='id',
  tokenize='unicode61 remove_diacritics 2');
CREATE TRIGGER IF NOT EXISTS trechos_ai AFTER INSERT ON trechos BEGIN
  INSERT INTO trechos_fts(rowid, texto, secao) VALUES (new.id, new.texto, new.secao); END;
CREATE TRIGGER IF NOT EXISTS trechos_ad AFTER DELETE ON trechos BEGIN
  INSERT INTO trechos_fts(trechos_fts, rowid, texto, secao) VALUES('delete', old.id, old.texto, old.secao); END;
CREATE TABLE IF NOT EXISTS entidades(caso TEXT, tipo TEXT, valor TEXT, valor_norm TEXT, pagina INTEGER,
  arquivo TEXT, contexto TEXT);
CREATE INDEX IF NOT EXISTS ix_ent_norm ON entidades(valor_norm);
CREATE INDEX IF NOT EXISTS ix_ent_caso ON entidades(caso);
""")


for col, tipo_col in (("autor", "TEXT"), ("peso", "INTEGER")):
    try: db.execute(f"ALTER TABLE trechos ADD COLUMN {col} {tipo_col}")
    except sqlite3.OperationalError: pass


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def janelas(txt):
    if len(txt) <= JANELA: return [txt]
    out, i = [], 0
    while i < len(txt):
        out.append(txt[i:i + JANELA]); i += JANELA - SOBREPOE
    return out


def fls_de(txt):
    m = re.search(r"\bfls?\.?\s*(\d{1,5})\b", txt, flags=re.I)
    return m.group(1) if m else None


def trechos_transcricao(txt):
    partes = re.split(r"^##\s*P[áa]gina\s+(\d+)\s*$", txt, flags=re.M)
    for k in range(1, len(partes), 2):
        pag, corpo = int(partes[k]), re.sub(r"<!--.*?-->", "", partes[k + 1], flags=re.S).strip().strip("-").strip()
        for j in janelas(corpo):
            if j.strip(): yield pag, fls_de(corpo), f"Página {pag}", j


def trechos_titulos(txt):
    txt = re.sub(r"^---\n.*?\n---\n", "", txt, flags=re.S)
    blocos = re.split(r"^(#{1,3}\s+.+)$", txt, flags=re.M)
    secao = ""
    for b in blocos:
        if re.match(r"^#{1,3}\s+", b): secao = b.lstrip("#").strip(); continue
        pag = re.search(r"p[áa]g\.?\s*(\d+)", b)
        for j in janelas(b.strip()):
            if j.strip(): yield (int(pag.group(1)) if pag else None), fls_de(j), secao, j


def tipo_de(rel):
    r = rel.replace("/", "\\").lower()
    if r.startswith("acervo\\"): return "acervo"
    if r.startswith("calibracao\\"): return "calibracao"
    if r.startswith("referencias\\"): return "referencia"
    if "\\01-extracao\\" in r: return "transcricao"
    if "\\02-analise\\" in r: return "analise"
    if "\\03-relatorios\\" in r:
        n = os.path.basename(r)
        return "relatorio" if "final" in n else ("revisao" if n.startswith("revisao") else "minuta")
    return "outro"


alvos = (glob.glob(os.path.join(CASOS, "*", "01-extracao", "**", "transcricao.md"), recursive=True)
         + glob.glob(os.path.join(CASOS, "*", "02-analise", "**", "*.md"), recursive=True)
         + glob.glob(os.path.join(CASOS, "*", "03-relatorios", "*.md"))
         + glob.glob(os.path.join(WS, "calibracao", "*.md"))
         + glob.glob(os.path.join(WS, "referencias", "*", "texto.md"))
         + glob.glob(os.path.join(WS, "acervo", "**", "*.md"), recursive=True))
alvos = [p for p in alvos if "\\_MODELO-CASO\\" not in p]
vistos, novos = set(), 0
for p in alvos:
    rel = os.path.relpath(p, WS); vistos.add(rel)
    h = sha(p)
    ant = db.execute("SELECT sha FROM docs WHERE arquivo=?", (rel,)).fetchone()
    if ant and ant[0] == h and not a.tudo: continue
    partes_rel = rel.split(os.sep)
    caso = partes_rel[1] if partes_rel[0] == "casos" else None
    c = casos.get(caso, {}) if caso else {}
    tipo = tipo_de(rel)
    db.execute("DELETE FROM trechos WHERE arquivo=?", (rel,))
    txt = open(p, encoding="utf-8", errors="replace").read()
    gerador = trechos_transcricao(txt) if tipo == "transcricao" else trechos_titulos(txt)
    autor = peso = None
    if tipo == "referencia":
        mp = os.path.join(os.path.dirname(p), "meta.json")
        m = json.load(open(mp, encoding="utf-8")) if os.path.exists(mp) else {}
        c = {"modalidade": m.get("modalidade"), "natureza": m.get("natureza")}; autor, peso = m.get("autor"), m.get("peso")
    elif tipo == "relatorio":
        autor, peso = "(aprovado no sistema)", 4
    db.executemany("INSERT INTO trechos(arquivo,caso,tipo,pagina,fls,secao,texto,modalidade,natureza,autor,peso) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                   [(rel, caso, tipo, pg, fl, sec, t, c.get("modalidade"), c.get("natureza"), autor, peso) for pg, fl, sec, t in gerador])
    db.execute("INSERT OR REPLACE INTO docs VALUES(?,?,?,?,?)", (rel, caso, tipo, h, datetime.datetime.now().isoformat(timespec="seconds")))
    novos += 1

for (rel,) in db.execute("SELECT arquivo FROM docs").fetchall():
    if rel not in vistos:
        db.execute("DELETE FROM trechos WHERE arquivo=?", (rel,)); db.execute("DELETE FROM docs WHERE arquivo=?", (rel,))

# modalidade/natureza/peso podem mudar sem mudar o arquivo
for mp in glob.glob(os.path.join(WS, "referencias", "*", "meta.json")):
    m = json.load(open(mp, encoding="utf-8"))
    db.execute("UPDATE trechos SET modalidade=?, natureza=?, autor=?, peso=? WHERE arquivo=?",
               (m.get("modalidade"), m.get("natureza"), m.get("autor"), m.get("peso"),
                os.path.relpath(os.path.join(os.path.dirname(mp), "texto.md"), WS)))
for id_, c in casos.items():
    db.execute("UPDATE trechos SET modalidade=?, natureza=? WHERE caso=?", (c.get("modalidade"), c.get("natureza"), id_))


# ------------------------------------------------------------ entidades (cruzamento entre casos)
import unicodedata  # noqa: E402


def _banco(b):
    """Banco normalizado para compor a identidade da conta (sem banco: '?')."""
    s = unicodedata.normalize("NFKD", str(b or "")).encode("ascii", "ignore").decode().lower()
    s = " ".join(re.sub(r"[^a-z0-9 ]+", " ", s).split())
    return s or "?"


def conta_chave(banco, ag_conta):
    d = re.sub(r"\D", "", ag_conta or "")
    return f"{_banco(banco)}|{d}" if d else ""


def pix_chave(v):
    """Chave Pix mantém o próprio tipo: e-mail em minúsculas; CPF/CNPJ/telefone só dígitos; aleatória sem espaços."""
    v = (v or "").strip()
    if not v: return ""
    if "@" in v: return v.lower()
    if re.fullmatch(r"[\d.\-/() +]+", v): return re.sub(r"\D", "", v)
    return re.sub(r"\s+", "", v.lower())


def norm(tipo, v):
    v = (v or "").strip()
    t = (tipo or "").upper()
    if t == "CHAVE_PIX": return pix_chave(v)
    if t == "EMAIL": return v.lower()
    if t in ("CPF", "CNPJ", "TELEFONE", "CONTA", "AGENCIA") or re.fullmatch(r"[\d.\-/() ]+", v):
        return re.sub(r"\D", "", v)
    if t == "PLACA": return re.sub(r"[^A-Z0-9]", "", v.upper())
    return v.lower()


db.execute("DELETE FROM entidades")
for id_ in casos:
    base = os.path.join(CASOS, id_)
    for ent in glob.glob(os.path.join(base, "01-extracao", "**", "entidades.csv"), recursive=True):
        for r in csv.DictReader(open(ent, encoding="utf-8-sig"), delimiter=";"):
            if r.get("tipo") in ("DATA", "FLS", "VALOR"): continue
            db.execute("INSERT INTO entidades VALUES(?,?,?,?,?,?,?)", (id_, r.get("tipo"), r.get("valor"),
                       norm(r.get("tipo"), r.get("valor")), int(r["pagina_pdf"]) if (r.get("pagina_pdf") or "").isdigit() else None,
                       os.path.relpath(ent, WS), (r.get("trecho") or "")[:200]))
    ff = os.path.join(base, "02-analise", "fluxo-financeiro.csv")
    if os.path.exists(ff):
        for r in csv.DictReader(open(ff, encoding="utf-8-sig"), delimiter=";"):
            pg = r.get("fonte_pag") or ""
            for lado in ("origem", "destino"):
                for col, tipo in ((f"{lado}_chave", "CHAVE_PIX"), (f"{lado}_ag_conta", "CONTA"), (f"{lado}_titular", "TITULAR")):
                    v = (r.get(col) or "").strip()
                    if not v: continue
                    banco = (r.get(f"{lado}_banco") or "").strip()
                    valor, vn = (f"{banco} {v}".strip(), conta_chave(banco, v)) if tipo == "CONTA" else (v, norm(tipo, v))
                    db.execute("INSERT INTO entidades VALUES(?,?,?,?,?,?,?)", (id_, tipo, valor, vn,
                               int(pg) if pg.isdigit() else None, os.path.relpath(ff, WS), f"{col} seq {r.get('seq','')}"))

# ------------------------------------------------------------ pessoas (pesquisa relacional)
# Fontes: casos\*\02-analise\pessoas.csv (qualificação extraída dos autos) e consulta\*\registros.jsonl
# (bases de consulta, ex. Muralha Paulista — somente pesquisa, nunca fonte de relatório).
import consulta as Q  # noqa: E402

db.executescript("""
CREATE TABLE IF NOT EXISTS pessoas(id INTEGER PRIMARY KEY, origem TEXT, fonte TEXT, arquivo TEXT, localizador TEXT,
  nome TEXT, mae TEXT, pai TEXT, cpf TEXT, rg TEXT, nascimento TEXT, telefones TEXT, enderecos TEXT,
  empresas TEXT, cnpj TEXT, emails TEXT, placas TEXT, veiculos TEXT, processos TEXT, bos TEXT, mandados TEXT,
  cautelares TEXT, condicao TEXT, extras TEXT, texto TEXT,
  nome_n TEXT, mae_n TEXT, pai_n TEXT, end_n TEXT, emp_n TEXT, proc_n TEXT, tudo_n TEXT,
  cpf_d TEXT, tel_d TEXT, cnpj_d TEXT, rg_d TEXT, proc_d TEXT, placa_n TEXT, tem_mandado INTEGER, tem_cautelar INTEGER,
  mandado_estado TEXT, cautelar_estado TEXT, antecedentes_itens TEXT, no_id TEXT);
CREATE TABLE IF NOT EXISTS arestas(a_tipo TEXT, a_valor TEXT, b_tipo TEXT, b_valor TEXT, relacao TEXT, origem TEXT, fonte TEXT, localizador TEXT);
CREATE TABLE IF NOT EXISTS rotulos(tipo TEXT, valor TEXT, rotulo TEXT, PRIMARY KEY(tipo, valor));
CREATE INDEX IF NOT EXISTS ix_pessoas_cpf ON pessoas(cpf_d);
CREATE INDEX IF NOT EXISTS ix_pessoas_nome ON pessoas(nome_n);
CREATE INDEX IF NOT EXISTS ix_pessoas_no ON pessoas(no_id);
CREATE INDEX IF NOT EXISTS ix_pessoas_origem ON pessoas(origem);
CREATE INDEX IF NOT EXISTS ix_pessoas_mandado ON pessoas(tem_mandado);
CREATE INDEX IF NOT EXISTS ix_pessoas_cautelar ON pessoas(tem_cautelar);
CREATE INDEX IF NOT EXISTS ix_ar_a ON arestas(a_tipo, a_valor);
CREATE INDEX IF NOT EXISTS ix_ar_b ON arestas(b_tipo, b_valor);
DELETE FROM pessoas;
DELETE FROM arestas;
DELETE FROM rotulos;
""")
# Estados que contam como "tem ou teve" (o negado nunca conta). Ver consulta.estado_antecedente.
ESTADOS_POSITIVOS = ("confirmado", "indeterminado", "historico")


def digitos(v):
    partes = [re.sub(r"\D", "", x) for x in re.split(r"[|;,/]", v or "")]
    return " " + " ".join(p for p in partes if p) + " "


def valores(v, sep=r"\s\|\s"):
    return [x.strip() for x in re.split(sep, v or "") if x.strip()]


def aresta(a_tipo, a_valor, b_tipo, b_valor, relacao, origem, fonte, loc=""):
    if a_valor and b_valor:
        db.execute("INSERT INTO arestas VALUES(?,?,?,?,?,?,?,?)", (a_tipo, a_valor, b_tipo, b_valor, relacao, origem, fonte, loc))


def chave(tipo, v):
    """Normalização dos nós do grafo de vínculos. CONTA usa conta_chave(banco, conta); PESSOA usa id do registro."""
    if tipo in ("CPF", "CNPJ", "TELEFONE", "RG"): return re.sub(r"\D", "", v or "")
    if tipo == "PLACA": return re.sub(r"[^A-Z0-9]", "", (v or "").upper())
    if tipo in ("PROCESSO", "BO"):
        m = re.search(r"\d[\d./-]{4,}\d", v or ""); return re.sub(r"\D", "", m.group(0)) if m else ""
    if tipo == "CHAVE_PIX": return pix_chave(v)
    if tipo == "EMAIL": return (v or "").strip().lower()
    return Q.norm(v)


def rotulo(tipo, valor, texto):
    if valor and texto: db.execute("INSERT OR IGNORE INTO rotulos VALUES(?,?,?)", (tipo, valor, texto[:160]))


def id_registro(origem, fonte, arquivo, localizador, nome, cpf):
    """Identidade de PESSOA = registro de origem (nunca o nome sozinho)."""
    base = "|".join([origem, fonte or "", arquivo or "", localizador or "", Q.norm(nome), re.sub(r"\D", "", cpf or "")])
    return "P:" + hashlib.sha1(base.encode("utf-8")).hexdigest()[:14]


def insere_pessoa(origem, fonte, arquivo, r):
    if (r.get("mandados") or r.get("cautelares")) and "antecedentes_itens" not in r: Q._itens(r)
    g = lambda k: (r.get(k) or "").strip()
    no = id_registro(origem, fonte, arquivo, g("localizador"), g("nome"), g("cpf"))
    extras = r.get("extras") or {}
    extras_txt = " ".join(f"{k} {v}" for k, v in extras.items()) if isinstance(extras, dict) else str(extras)
    tudo = " ".join([g(k) for k in Q.CAMPOS] + [g("condicao"), extras_txt, g("texto")])
    proc = " ".join([g("processos"), g("bos")])
    db.execute("INSERT INTO pessoas(origem,fonte,arquivo,localizador,nome,mae,pai,cpf,rg,nascimento,telefones,enderecos,"
               "empresas,cnpj,emails,placas,veiculos,processos,bos,mandados,cautelares,condicao,extras,texto,"
               "nome_n,mae_n,pai_n,end_n,emp_n,proc_n,tudo_n,cpf_d,tel_d,cnpj_d,rg_d,proc_d,placa_n,tem_mandado,tem_cautelar,"
               "mandado_estado,cautelar_estado,antecedentes_itens,no_id) "
               "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
               (origem, fonte, arquivo, g("localizador"), g("nome"), g("mae"), g("pai"), g("cpf"), g("rg"), g("nascimento"),
                g("telefones"), g("enderecos"), g("empresas"), g("cnpj"), g("emails"), g("placas"), g("veiculos"),
                g("processos"), g("bos"), g("mandados"), g("cautelares"), g("condicao"),
                json.dumps(extras, ensure_ascii=False) if extras else "", g("texto")[:20000],
                Q.norm(g("nome")), Q.norm(g("mae")), Q.norm(g("pai")), Q.norm(g("enderecos")), Q.norm(g("empresas")),
                Q.norm(proc), Q.norm(tudo), digitos(g("cpf")), digitos(g("telefones")), digitos(g("cnpj")), digitos(g("rg")),
                digitos(proc), " " + " ".join(chave("PLACA", p) for p in valores(g("placas"))) + " ",
                1 if g("mandados_estado") in ESTADOS_POSITIVOS else 0, 1 if g("cautelares_estado") in ESTADOS_POSITIVOS else 0,
                g("mandados_estado"), g("cautelares_estado"),
                json.dumps(r.get("antecedentes_itens") or [], ensure_ascii=False), no))
    # ---- grafo de vínculos: nó PESSOA = registro (id próprio); o nome liga a um nó NOME apenas como candidato
    if not (g("nome") or g("cpf")): return
    p = no
    loc = f"{arquivo} {g('localizador')}".strip()
    rotulo("PESSOA", p, " · ".join(x for x in (g("nome") or "(sem nome)", f"CPF {g('cpf')}" if g("cpf") else "",
                                                   f"{origem}: {fonte}") if x))
    if g("nome"):
        aresta("PESSOA", p, "NOME", chave("NOME", g("nome")), "nome (homônimos possíveis — conferir)", origem, fonte, loc)
        rotulo("NOME", chave("NOME", g("nome")), g("nome"))
    for campo, tipo, rel in (("cpf", "CPF", "tem CPF"), ("rg", "RG", "tem RG"), ("telefones", "TELEFONE", "usa telefone"),
                             ("placas", "PLACA", "ligado ao veículo"), ("cnpj", "CNPJ", "ligado ao CNPJ"),
                             ("empresas", "EMPRESA", "ligado à empresa"), ("emails", "EMAIL", "usa e-mail"),
                             ("processos", "PROCESSO", "figura em processo/IP/TC"), ("bos", "BO", "figura em BO")):
        for v in valores(g(campo)):
            aresta("PESSOA", p, tipo, chave(tipo, v), rel, origem, fonte, loc); rotulo(tipo, chave(tipo, v), v)
    for v in valores(g("enderecos"), r";\s|\s\|\s"):
        aresta("PESSOA", p, "ENDERECO", chave("ENDERECO", v), "reside/consta no endereço", origem, fonte, loc)
        rotulo("ENDERECO", chave("ENDERECO", v), v)
    for campo, rel in (("mae", "mãe (nome — conferir identidade)"), ("pai", "pai (nome — conferir identidade)")):
        if g(campo):
            aresta("PESSOA", p, "NOME", chave("NOME", g(campo)), rel, origem, fonte, loc); rotulo("NOME", chave("NOME", g(campo)), g(campo))
    if origem == "caso": aresta("PESSOA", p, "CASO", fonte, g("condicao") or "consta no caso", origem, fonte, loc)


n_p = 0
for id_ in casos:
    nomes_cadastrados = set()
    pc = os.path.join(CASOS, id_, "02-analise", "pessoas.csv")
    if os.path.exists(pc):
        for r in csv.DictReader(open(pc, encoding="utf-8-sig"), delimiter=";"):
            r["localizador"] = ("pág. " + r["paginas"]) if r.get("paginas") else (r.get("documento") or "")
            insere_pessoa("caso", id_, os.path.relpath(pc, WS), r); n_p += 1
            if r.get("nome"): nomes_cadastrados.add(Q.norm(r["nome"]))
    c_json = os.path.join(CASOS, id_, "caso.json")
    if os.path.exists(c_json):
        try:
            cj = json.load(open(c_json, encoding="utf-8"))
            for vit in cj.get("vitimas") or []:
                if vit and Q.norm(vit) not in nomes_cadastrados:
                    insere_pessoa("caso", id_, os.path.relpath(c_json, WS), {
                        "nome": vit,
                        "condicao": "vítima",
                        "localizador": f"caso.json (vítima do caso {id_})"
                    })
                    n_p += 1
                    nomes_cadastrados.add(Q.norm(vit))
            for inv in cj.get("investigados") or []:
                if inv and Q.norm(inv) not in nomes_cadastrados and inv.lower() not in ("autor desconhecido", "autoria a apurar"):
                    insere_pessoa("caso", id_, os.path.relpath(c_json, WS), {
                        "nome": inv,
                        "condicao": "investigado(a)",
                        "localizador": f"caso.json (investigado do caso {id_})"
                    })
                    n_p += 1
                    nomes_cadastrados.add(Q.norm(inv))
        except Exception: pass
for base in Q.listar():
    arq = os.path.join(Q.BASES, base["id"], "registros.jsonl")
    for ln in open(arq, encoding="utf-8"):
        insere_pessoa("consulta", base["nome"], os.path.relpath(arq, WS), json.loads(ln)); n_p += 1

# vínculos vindos dos autos: caso ↔ identificadores extraídos; caminho do dinheiro (conta/chave Pix)
MAPA_ENT = {"CPF": "CPF", "CNPJ": "CNPJ", "TELEFONE": "TELEFONE", "PLACA": "PLACA", "EMAIL": "EMAIL",
            "CHAVE_PIX": "CHAVE_PIX", "CONTA": "CONTA", "TITULAR": "NOME"}
for caso_, tipo, valor, vn, pag, arq in db.execute("SELECT caso, tipo, valor, valor_norm, pagina, arquivo FROM entidades").fetchall():
    t = MAPA_ENT.get((tipo or "").upper())
    if not t: continue
    k = vn if t == "CONTA" else chave(t, valor)
    aresta("CASO", caso_, t, k, "titular citado nos autos (nome — conferir)" if t == "NOME" else "consta nos autos",
           "caso", caso_, f"{arq} pág. {pag}" if pag else arq)
    rotulo(t, k, valor)


def lado_no(r, lado):
    """Nó de um lado da transação: CONTA (banco|agência/conta) ou, na falta, CHAVE_PIX — cada um com seu tipo."""
    c = conta_chave(r.get(f"{lado}_banco"), r.get(f"{lado}_ag_conta"))
    if c: return "CONTA", c, f"{(r.get(f'{lado}_banco') or '').strip()} {r.get(f'{lado}_ag_conta')}".strip()
    k = pix_chave(r.get(f"{lado}_chave"))
    return ("CHAVE_PIX", k, r.get(f"{lado}_chave")) if k else (None, None, None)


for id_ in casos:
    ff = os.path.join(CASOS, id_, "02-analise", "fluxo-financeiro.csv")
    if not os.path.exists(ff): continue
    rel_ff = os.path.relpath(ff, WS)
    for r in csv.DictReader(open(ff, encoding="utf-8-sig"), delimiter=";"):
        loc = f"{rel_ff} seq {r.get('seq') or '?'}; pág. {r.get('fonte_pag') or '?'}" + (f"; fls. {r['fls']}" if r.get("fls") else "")
        (to, o, ro), (td, d, rd) = lado_no(r, "origem"), lado_no(r, "destino")
        rel = f"transferiu R$ {r.get('valor') or '?'} em {r.get('data') or '?'} ({r.get('meio') or ''})".strip()
        if o and d: aresta(to, o, td, d, rel, "caso", id_, loc)
        for (t, k, rot), lado in (((to, o, ro), "origem"), ((td, d, rd), "destino")):
            if not k: continue
            rotulo(t, k, rot)
            # conta ↔ chave Pix do mesmo lado (quando ambas constam)
            kp = pix_chave(r.get(f"{lado}_chave"))
            if t == "CONTA" and kp:
                aresta("CONTA", k, "CHAVE_PIX", kp, "chave Pix vinculada (conforme autos)", "caso", id_, loc); rotulo("CHAVE_PIX", kp, r.get(f"{lado}_chave"))
            if r.get(f"{lado}_titular"):
                nm = chave("NOME", r[f"{lado}_titular"])
                aresta("NOME", nm, t, k, "titular (nome — conferir)", "caso", id_, loc); rotulo("NOME", nm, r[f"{lado}_titular"])
db.execute("CREATE INDEX IF NOT EXISTS ix_ar_a ON arestas(a_tipo, a_valor)")
db.execute("CREATE INDEX IF NOT EXISTS ix_ar_b ON arestas(b_tipo, b_valor)")

db.commit()
n_t = db.execute("SELECT COUNT(*) FROM trechos").fetchone()[0]
n_e = db.execute("SELECT COUNT(*) FROM entidades").fetchone()[0]
print(f"RAG: {novos} arquivo(s) (re)indexado(s); {n_t} trechos; {n_e} entidades; {n_p} pessoas -> rag\\cpj.sqlite")
db.close()
