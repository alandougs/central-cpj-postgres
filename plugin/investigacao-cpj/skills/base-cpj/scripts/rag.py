#!/usr/bin/env python3
"""Consulta o índice RAG local do workspace CPJ (rag\\cpj.sqlite). Rode indexar.py antes.

Uso (CLI):
  rag.py buscar "texto" [--caso ID] [--tipo transcricao|analise|relatorio|minuta|calibracao|acervo]
                        [--modalidade COD] [-n 10] [--fts]     (--fts: consulta FTS5 crua, ex.: pix NEAR/5 conta)
  rag.py entidade VALOR [--tipo CPF|CNPJ|TELEFONE|PLACA|CHAVE_PIX|CONTA|TITULAR|EMAIL]
  rag.py cruzar ID        -> entidades do caso que aparecem em OUTROS casos (conexões entre IPs)
  rag.py exemplos MODALIDADE [-n 3]  -> relatórios FINAL de casos da mesma modalidade
  rag.py stats
Cada resultado traz caso, arquivo, página e fls. para citação e conferência no original.
"""
import argparse, os, re, sqlite3, sys

WS = os.environ.get("CPJ_WORKSPACE", r"C:\CPJ - TRABALHO")
DB = os.path.join(WS, "rag", "cpj.sqlite")


def conectar():
    if not os.path.exists(DB): raise FileNotFoundError("Índice inexistente. Rode indexar.py")
    return sqlite3.connect(DB)


def norm(v, tipo=None):
    v = (v or "").strip()
    if (tipo or "").upper() == "PLACA": return re.sub(r"[^A-Z0-9]", "", v.upper())
    if re.fullmatch(r"[\d.\-/() ]+", v): return re.sub(r"\D", "", v)
    return v.lower()


def buscar(q, caso=None, tipo=None, modalidade=None, n=10, fts=False):
    """Retorna (lista de dicts, aviso|None)."""
    db = conectar()
    termos = ['"' + t.replace('"', "") + '"' for t in re.findall(r"[\w@.\-/]+", q)]
    if not termos and not fts: return [], None
    sql = ("SELECT t.caso, t.arquivo, t.tipo, t.pagina, t.fls, t.secao, "
           "snippet(trechos_fts, 0, '[', ']', ' … ', 24) FROM trechos_fts JOIN trechos t ON t.id = trechos_fts.rowid "
           "WHERE trechos_fts MATCH ?")
    filtros = []
    for campo, v in (("t.caso", caso), ("t.tipo", tipo), ("t.modalidade", modalidade)):
        if v: sql += f" AND {campo} = ?"; filtros.append(v)
    sql += " ORDER BY bm25(trechos_fts) LIMIT ?"

    def roda(expr):
        try: return db.execute(sql, [expr] + filtros + [n]).fetchall()
        except sqlite3.OperationalError as e: raise ValueError(f"Consulta inválida: {e}")

    aviso = None
    try:
        res = roda(q if fts else " ".join(termos))
        if not res and not fts and len(termos) > 1:
            res = roda(" OR ".join(termos))
            if res: aviso = "Nenhum trecho contém todos os termos; mostrando trechos com parte deles (o OCR pode ter unido/alterado palavras)."
    finally:
        db.close()  # também na consulta inválida: conexão esquecida prende cpj.sqlite no Windows
    return [dict(zip(("caso", "arquivo", "tipo", "pagina", "fls", "secao", "trecho"), r)) for r in res], aviso


def entidade(valor, tipo=None):
    db = conectar()
    sql = "SELECT caso, tipo, valor, pagina, arquivo FROM entidades WHERE valor_norm = ?"
    par = [norm(valor, tipo)]
    if re.fullmatch(r"\d{4,}", par[0]):  # contas são guardadas como banco|dígitos: aceita qualquer banco
        sql = sql.replace("WHERE valor_norm = ?", "WHERE (valor_norm = ? OR valor_norm LIKE ?)"); par.append(f"%|{par[0]}")
    if tipo: sql += " AND upper(tipo) = ?"; par.append(tipo.upper())
    res = db.execute(sql + " ORDER BY caso, pagina", par).fetchall(); db.close()
    return [dict(zip(("caso", "tipo", "valor", "pagina", "arquivo"), r)) for r in res]


def cruzar(id_):
    db = conectar()
    res = db.execute("""
      SELECT e.tipo, e.valor, o.caso, group_concat(DISTINCT o.pagina)
      FROM entidades e JOIN entidades o ON o.valor_norm = e.valor_norm AND o.caso <> e.caso
      WHERE e.caso = ? AND length(e.valor_norm) >= 6 AND e.tipo NOT IN ('DATA','FLS','VALOR')
      GROUP BY e.tipo, e.valor_norm, o.caso ORDER BY e.tipo""", (id_,)).fetchall(); db.close()
    return [dict(zip(("tipo", "valor", "outro_caso", "paginas"), r)) for r in res]


def exemplos(modalidade=None, n=3, autor=None):
    """Relatórios-modelo para estilo/estrutura: FINAL aprovados no sistema + referências importadas,
    priorizando mesma modalidade, autor preferido e maior peso."""
    db = conectar()
    try:
        res = db.execute("""
          SELECT arquivo, caso, tipo, MAX(COALESCE(peso,3)) AS p, MAX(autor), MAX(modalidade)
          FROM trechos WHERE tipo IN ('relatorio','referencia') GROUP BY arquivo
          ORDER BY (MAX(modalidade) = ?) DESC, (MAX(autor) LIKE ?) DESC, p DESC LIMIT ?""",
                         (modalidade or "", f"%{autor}%" if autor else "\x00", n)).fetchall()
    except sqlite3.OperationalError:
        res = []
    db.close()
    return [{"arquivo": os.path.join(WS, a), "caso": c, "tipo": t, "peso": p, "autor": au, "modalidade": m}
            for a, c, t, p, au, m in res]


def _n(s):
    import unicodedata
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9@/ -]+", " ", s).replace("-", " ").strip()


CAMPOS_TEXTO = {"nome": "nome_n", "mae": "mae_n", "pai": "pai_n", "endereco": "end_n", "empresa": "emp_n", "texto": "tudo_n"}
CAMPOS_DIGITO = {"cpf": "cpf_d", "telefone": "tel_d", "cnpj": "cnpj_d", "rg": "rg_d"}


def pesquisa_relacional(filtros, origem=None, limite=200):
    """filtros: dict com qualquer combinação de nome, mae, pai, endereco, empresa, texto, cpf, telefone, cnpj, rg.
    Texto: todas as palavras precisam aparecer no campo (qualquer ordem, sem acento). Números: só dígitos, trecho.
    Retorna (pessoas, ocorrencias_nos_autos)."""
    db = conectar()
    try: db.execute("SELECT 1 FROM pessoas LIMIT 1")
    except sqlite3.OperationalError: db.close(); return [], []
    where, par = [], []
    for k, col in CAMPOS_TEXTO.items():
        for tok in _n(filtros.get(k)).split():
            where.append(f"{col} LIKE ?"); par.append(f"%{tok}%")
    for k, col in CAMPOS_DIGITO.items():
        d = re.sub(r"\D", "", str(filtros.get(k) or ""))
        if d:
            if len(d) < 4: raise ValueError(f"{k}: informe ao menos 4 dígitos")
            where.append(f"{col} LIKE ?"); par.append(f"%{d}%")
    for k, col in (("processo", "proc"), ("bo", "proc")):
        v = str(filtros.get(k) or "").strip()
        if v:
            d = re.sub(r"\D", "", v)
            if len(d) >= 4: where.append(f"{col}_d LIKE ?"); par.append(f"%{d}%")
            else:
                for tok in _n(v).split(): where.append(f"{col}_n LIKE ?"); par.append(f"%{tok}%")
    if filtros.get("placa"):
        where.append("placa_n LIKE ?"); par.append("%" + re.sub(r"[^A-Z0-9]", "", str(filtros["placa"]).upper()) + "%")
    # mandado/cautelar = "1": tem ou teve (confirmado, indeterminado ou histórico) — NEGADO nunca entra.
    # mandado_estado/cautelar_estado: estado exato (confirmado|indeterminado|historico|negado).
    if str(filtros.get("mandado") or "") in ("1", "true", "sim"): where.append("tem_mandado = 1")
    if str(filtros.get("cautelar") or "") in ("1", "true", "sim"): where.append("tem_cautelar = 1")
    for k, col in (("mandado_estado", "mandado_estado"), ("cautelar_estado", "cautelar_estado")):
        v = str(filtros.get(k) or "").strip().lower()
        if v in ("confirmado", "indeterminado", "historico", "negado"): where.append(f"{col} = ?"); par.append(v)
    if not where: db.close(); return [], []
    if origem: where.append("origem = ?"); par.append(origem)
    cols = ("id", "origem", "fonte", "arquivo", "localizador", "nome", "mae", "pai", "cpf", "rg", "nascimento",
            "telefones", "enderecos", "empresas", "cnpj", "emails", "placas", "veiculos", "processos", "bos",
            "mandados", "cautelares", "condicao", "extras", "texto", "mandado_estado", "cautelar_estado",
            "antecedentes_itens", "no_id")
    rows = db.execute(f"SELECT {','.join(cols)} FROM pessoas WHERE {' AND '.join(where)} "
                      f"ORDER BY origem, nome LIMIT ?", par + [limite]).fetchall()
    pessoas = [dict(zip(cols, r)) for r in rows]
    # ocorrências nos autos (entidades extraídas das transcrições/fluxo financeiro) para CPF/telefone/CNPJ
    ocorr = []
    for k in ("cpf", "telefone", "cnpj"):
        d = re.sub(r"\D", "", str(filtros.get(k) or ""))
        if len(d) >= 8:
            ocorr += [dict(zip(("caso", "tipo", "valor", "pagina", "arquivo"), r)) for r in db.execute(
                "SELECT caso, tipo, valor, pagina, arquivo FROM entidades WHERE valor_norm LIKE ? LIMIT 100", (f"%{d}%",))]
    db.close()
    return pessoas, ocorr


TIPOS_NO = ("PESSOA", "NOME", "CPF", "RG", "TELEFONE", "PLACA", "CNPJ", "EMPRESA", "EMAIL", "ENDERECO", "PROCESSO", "BO",
            "CONTA", "CHAVE_PIX", "CASO")
# Nós que não devem ser atravessados para chegar a outros registros (evita "fusão" por nome em 2º nível):
# a partir de um NOME mostramos os registros homônimos (candidatos), mas não seguimos adiante por eles.
NAO_EXPANDIR = ("NOME",)


def chave_no(tipo, v):
    """Mesma normalização do indexar.py. PESSOA = id de registro ('P:...'). CONTA = 'banco|dígitos'."""
    tipo = (tipo or "").upper()
    if tipo in ("CPF", "CNPJ", "TELEFONE", "RG"): return re.sub(r"\D", "", v or "")
    if tipo == "PLACA": return re.sub(r"[^A-Z0-9]", "", (v or "").upper())
    if tipo in ("PROCESSO", "BO"):
        m = re.search(r"\d[\d./-]{4,}\d", v or ""); return re.sub(r"\D", "", m.group(0)) if m else ""
    if tipo in ("CASO", "PESSOA"): return (v or "").strip()
    if tipo == "EMAIL": return (v or "").strip().lower()
    if tipo == "CHAVE_PIX":
        v = (v or "").strip()
        if "@" in v: return v.lower()
        if re.fullmatch(r"[\d.\-/() +]+", v): return re.sub(r"\D", "", v)
        return re.sub(r"\s+", "", v.lower())
    if tipo == "CONTA":
        v = (v or "").strip()
        return v if "|" in v else re.sub(r"\D", "", v)
    return _n(v)


def vinculos(tipo, valor, niveis=2, limite=400):
    """Grafo de vínculos (registros de pessoa, nomes, telefones, veículos, endereços, empresas, processos, contas,
    chaves Pix, casos) a partir do nó informado, até `niveis` saltos. Retorna {nos, arestas} com rótulos.
    Identidade: PESSOA é o registro de origem (id 'P:...'); o nome é apenas um nó NOME (candidato a conferir) e
    não é atravessado — homônimos aparecem como candidatos, sem trazer os vínculos uns dos outros."""
    db = conectar()
    try: db.execute("SELECT 1 FROM arestas LIMIT 1")
    except sqlite3.OperationalError: db.close(); return {"nos": [], "arestas": []}
    t0 = (tipo or "").upper()
    if t0 == "PESSOA" and not str(valor or "").startswith("P:"): t0 = "NOME"   # compatibilidade: busca por nome
    k0 = chave_no(t0, valor)
    if not k0: db.close(); return {"nos": [], "arestas": []}
    inicios = [(t0, k0)]
    if t0 == "CONTA" and "|" not in k0:   # conta sem banco: todos os bancos com esses dígitos
        inicios = [("CONTA", r[0]) for r in db.execute(
            "SELECT DISTINCT a_valor FROM arestas WHERE a_tipo='CONTA' AND a_valor LIKE ? UNION "
            "SELECT DISTINCT b_valor FROM arestas WHERE b_tipo='CONTA' AND b_valor LIKE ?", (f"%|{k0}", f"%|{k0}"))] or inicios
    vistos, fronteira, arestas = {i: 0 for i in inicios}, list(inicios), []
    for nivel in range(1, niveis + 1):
        prox = []
        for t, v in fronteira:
            if t in NAO_EXPANDIR and vistos.get((t, v)) != 0: continue   # nome só expande quando é o ponto de partida
            for r in db.execute("SELECT a_tipo,a_valor,b_tipo,b_valor,relacao,origem,fonte,localizador FROM arestas "
                                "WHERE (a_tipo=? AND a_valor=?) OR (b_tipo=? AND b_valor=?) LIMIT ?", (t, v, t, v, limite)):
                arestas.append(dict(zip(("a_tipo", "a_valor", "b_tipo", "b_valor", "relacao", "origem", "fonte", "localizador"), r)))
                for no in ((r[0], r[1]), (r[2], r[3])):
                    if no not in vistos and len(vistos) < limite: vistos[no] = nivel; prox.append(no)
        fronteira = prox
    rot = {}
    try:
        for t, v in vistos:
            x = db.execute("SELECT rotulo FROM rotulos WHERE tipo=? AND valor=?", (t, v)).fetchone()
            if x: rot[(t, v)] = x[0]
    except sqlite3.OperationalError:
        pass
    db.close()
    unicas = {tuple(a.values()): a for a in arestas}
    return {"nos": [{"tipo": t, "valor": v, "nivel": n, "rotulo": rot.get((t, v), v)} for (t, v), n in vistos.items()],
            "arestas": list(unicas.values())}


def stats():
    db = conectar()
    out = {"trechos": dict(db.execute("SELECT tipo, COUNT(*) FROM trechos GROUP BY tipo").fetchall()),
           "documentos": db.execute("SELECT COUNT(*) FROM docs").fetchone()[0],
           "entidades": db.execute("SELECT COUNT(*) FROM entidades").fetchone()[0],
           "casos": db.execute("SELECT COUNT(DISTINCT caso) FROM trechos WHERE caso IS NOT NULL").fetchone()[0]}
    db.close(); return out


if __name__ == "__main__":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("buscar"); s.add_argument("q"); s.add_argument("--caso"); s.add_argument("--tipo")
    s.add_argument("--modalidade"); s.add_argument("-n", type=int, default=10); s.add_argument("--fts", action="store_true")
    s = sub.add_parser("entidade"); s.add_argument("valor"); s.add_argument("--tipo")
    s = sub.add_parser("cruzar"); s.add_argument("id")
    s = sub.add_parser("exemplos"); s.add_argument("modalidade", nargs="?"); s.add_argument("-n", type=int, default=3)
    s.add_argument("--autor")
    s = sub.add_parser("pessoas")
    for k in ("nome", "mae", "pai", "cpf", "rg", "telefone", "cnpj", "empresa", "endereco", "texto"): s.add_argument(f"--{k}")
    sub.add_parser("stats")
    a = ap.parse_args()
    try:
        if a.cmd == "buscar":
            res, aviso = buscar(a.q, a.caso, a.tipo, a.modalidade, a.n, a.fts)
            if aviso: print(f"({aviso})")
            if not res: print("Nada encontrado.")
            for r in res:
                loc = f"pág. {r['pagina']}" if r["pagina"] else (r["secao"] or "")
                loc += f"; fls. {r['fls']}" if r["fls"] else ""
                print(f"\n■ {r['caso'] or '-'} | {r['tipo']} | {loc}\n  {r['arquivo']}\n  {r['trecho'].strip()}")
        elif a.cmd == "entidade":
            res = entidade(a.valor, a.tipo)
            print(f"{len(res)} ocorrência(s) em {len({r['caso'] for r in res})} caso(s)")
            for r in res: print(f"  {r['caso']:<20} {r['tipo']:<10} {r['valor']:<28} pág. {r['pagina']}  ({r['arquivo']})")
        elif a.cmd == "cruzar":
            res = cruzar(a.id)
            if not res: print(f"Nenhuma entidade de {a.id} aparece em outros casos indexados.")
            for r in res: print(f"  {r['tipo']:<10} {r['valor']:<28} também em {r['outro_caso']} (págs. {r['paginas']})")
            if res: print("\nConexões são INDÍCIOS de vinculação a verificar nos originais — não conclusão.")
        elif a.cmd == "exemplos":
            res = exemplos(a.modalidade, a.n, a.autor)
            if not res: print("Nenhum relatório FINAL ou referência indexada.")
            for r in res: print(f"  [{r['tipo']}, peso {r['peso']}, {r['autor'] or '-'}, {r['modalidade'] or '-'}] {r['arquivo']}")
        elif a.cmd == "pessoas":
            f = {k: getattr(a, k) for k in ("nome", "mae", "pai", "cpf", "rg", "telefone", "cnpj", "empresa", "endereco", "texto")}
            ps, oc = pesquisa_relacional(f)
            print(f"{len(ps)} pessoa(s)")
            for p in ps:
                print(f"  [{p['origem']}: {p['fonte']} {p['localizador']}] {p['nome']} | mãe {p['mae'] or '-'} | CPF {p['cpf'] or '-'} | tel {p['telefones'] or '-'}")
            for o in oc: print(f"  nos autos: {o['caso']} pág. {o['pagina']} {o['tipo']} {o['valor']}")
        elif a.cmd == "stats":
            s = stats()
            for t, n in s["trechos"].items(): print(f"  trechos {t:<12} {n}")
            print(f"  documentos       {s['documentos']}\n  entidades        {s['entidades']}\n  casos no índice  {s['casos']}")
    except (FileNotFoundError, ValueError) as e:
        raise SystemExit(f"ERRO: {e}")
