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
No terminal o termo casado sai entre » «; colchete no trecho é conteúdo dos autos, não marcador.
"""
import argparse, json, os, re, sqlite3, sys, threading

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
DB = os.path.join(WS, "rag", "cpj.sqlite")


def conectar():
    if not os.path.exists(DB): raise FileNotFoundError("Índice inexistente. Rode indexar.py")
    return sqlite3.connect(DB)


def norm(v, tipo=None):
    v = (v or "").strip()
    if (tipo or "").upper() == "PLACA": return re.sub(r"[^A-Z0-9]", "", v.upper())
    if re.fullmatch(r"[\d.\-/() ]+", v): return re.sub(r"\D", "", v)
    return v.lower()


MODOS = ("auto", "lexical", "semantico", "hibrido")
RRF_K = 60  # constante usual da fusão por posto recíproco; amortece o topo de cada lista
# Fração mínima de trechos com vetor para o modo `auto` usar a híbrida. Abaixo disso a parte
# semântica cobriria só um pedaço da base e desordenaria o resultado textual, que cobre tudo.
COBERTURA_MINIMA = 0.90
# Cosseno mínimo para um trecho entrar no pool semântico. Medido com o modelo do projeto em
# frases sintéticas em português: trecho do mesmo assunto da consulta 0,56 a 0,87 (0,69 no par
# do teste LC01); assunto diferente -0,11 a 0,09; mesmo domínio e outro assunto 0,14 a 0,17.
# 0,30 fica 0,13 acima do maior irrelevante medido e 0,26 abaixo do menor relevante medido.
SIMILARIDADE_MINIMA = 0.30
# Sentinelas do snippet do FTS. Não podem ser colchete: colchete em trecho de autos é
# determinação das regras 3 e 17 (`[dígito incerto]`, `[PESQUISAR: CNPJ]`) e não é termo casado —
# quem lê o resultado não tem como distinguir um do outro. Nunca saem de `buscar`: `_desmarcar`
# troca a sentinela por posição antes de devolver o trecho.
MARCA_I, MARCA_F = "\x02", "\x03"


def _filtros(caso, tipo, modalidade):
    sql, vals = "", []
    for campo, v in (("t.caso", caso), ("t.tipo", tipo), ("t.modalidade", modalidade)):
        if v: sql += f" AND {campo} = ?"; vals.append(v)
    return sql, vals


def _resumo(texto, limite=240):
    t = re.sub(r"\s+", " ", texto or "").strip()
    return t[:limite] + (" …" if len(t) > limite else "")


def _desmarcar(s):
    """(texto sem sentinela, [[inicio, fim], ...]) — o protocolo de marcação da busca.

    O destaque vai em posições, separado do texto, para quem exibe não precisar interpretar o
    próprio conteúdo: nada no trecho é marcador, então colchete dos autos chega literal e não
    vira destaque. Sentinela sem par é descartada sem gerar marca.

    As posições contam unidades UTF-16, que é como o navegador fatia a string. Em caractere fora
    do plano básico (emoji) isso difere do índice de ponto de código do Python, e usar o do Python
    deslocaria todo destaque seguinte."""
    texto, marcas, aberto, tam = [], [], None, 0
    for ch in (s or ""):
        if ch == MARCA_I:
            if aberto is None: aberto = tam
        elif ch == MARCA_F:
            if aberto is not None and tam > aberto: marcas.append([aberto, tam])
            aberto = None
        else:
            texto.append(ch); tam += 1 if ch <= "￿" else 2
    return "".join(texto), marcas


def _realcar(trecho, marcas, abre="»", fecha="«"):
    """Reaplica as marcas para leitura no terminal, com delimitador próprio em vez de colchete.

    Corta em unidade UTF-16, a mesma de `_desmarcar`."""
    u = (trecho or "").encode("utf-16-le")
    partes, fim = [], 0
    for i, j in marcas or []:
        partes += [u[fim * 2:i * 2], abre.encode("utf-16-le"),
                   u[i * 2:j * 2], fecha.encode("utf-16-le")]
        fim = j
    partes.append(u[fim * 2:])
    return b"".join(partes).decode("utf-16-le")


def _lexical(db, q, caso, tipo, modalidade, n, fts):
    """(ids por bm25, {id: snippet com sentinela}, aviso)."""
    termos = ['"' + t.replace('"', "") + '"' for t in re.findall(r"[\w@.\-/]+", q)]
    if not termos and not fts: return [], {}, None
    extra, filtros = _filtros(caso, tipo, modalidade)
    sql = ("SELECT trechos_fts.rowid, snippet(trechos_fts, 0, char(2), char(3), ' … ', 24) "
           "FROM trechos_fts JOIN trechos t ON t.id = trechos_fts.rowid "
           "WHERE trechos_fts MATCH ?" + extra + " ORDER BY bm25(trechos_fts) LIMIT ?")

    def roda(expr):
        try: return db.execute(sql, [expr] + filtros + [n]).fetchall()
        except sqlite3.OperationalError as e: raise ValueError(f"Consulta inválida: {e}")

    aviso = None
    res = roda(q if fts else " ".join(termos))
    if not res and not fts and len(termos) > 1:
        res = roda(" OR ".join(termos))
        if res: aviso = "Nenhum trecho contém todos os termos; mostrando trechos com parte deles (o OCR pode ter unido/alterado palavras)."
    return [r[0] for r in res], {r[0]: r[1] for r in res}, aviso


# Cache por processo: uma única matriz de vetores e uma única contagem de cobertura, válidas
# enquanto os arquivos do banco não mudarem. O COUNT de cobertura varre a tabela (~0,5 s na base
# real) e a leitura dos vetores custa ~1,2 s; sem isso cada requisição da Pesquisa pagaria de novo.
_CACHE = {"chave": None, "cobertura": None, "ids": None, "mat": None, "sentinela": None}
_TRAVA = threading.RLock()  # a Central é multi-thread; o cache e a sentinela são compartilhados


def _sentinela():
    """Conexão só-leitura de vida longa, usada apenas para ler `PRAGMA data_version`.

    Precisa ser de vida longa: numa conexão nova o `data_version` não acusa commit de outra
    conexão (medido: fica no mesmo valor). Numa conexão viva, ele incrementa a cada commit
    alheio e custa 0,003 ms."""
    c = _CACHE.get("sentinela")
    if c is None:
        try:
            c = sqlite3.connect("file:" + DB + "?mode=ro", uri=True, check_same_thread=False)
        except sqlite3.Error:
            return None
        _CACHE["sentinela"] = c
    return c


def _chave_base():
    """Assinatura do estado do banco: (mtime e tamanho do arquivo, `data_version`).

    NÃO usa `-wal`/`-shm`: eles são criados ao abrir a conexão e apagados ao fechar a última, e
    `buscar` abre e fecha uma por chamada — a chave oscilava entre ausente e presente e descartava
    o cache em toda consulta. `data_version` cobre o commit que ainda está no WAL, sem checkpoint;
    o stat do arquivo cobre a troca do banco inteiro (restauração de backup, reindexação)."""
    try:
        s = os.stat(DB)
        arquivo = (s.st_mtime_ns, s.st_size)
    except OSError:
        arquivo = None
    versao = None
    c = _sentinela()
    if c is not None:
        try:
            versao = c.execute("PRAGMA data_version").fetchone()[0]
        except sqlite3.Error:
            try: c.close()
            except Exception: pass
            _CACHE["sentinela"] = None
            return (arquivo, None, os.urandom(8))  # sem sentinela, não arrisca servir matriz velha
    return (arquivo, versao)


def _cache_atual():
    """Zera o cache se o banco mudou desde a última carga."""
    with _TRAVA:
        chave = _chave_base()
        if _CACHE["chave"] != chave:
            _CACHE.update(chave=chave, cobertura=None, ids=None, mat=None)


def cobertura_vetores(db):
    """(trechos com vetor, total de trechos). (0, 0) em índice legado, sem a coluna `embedding`.

    Memorizado por processo enquanto o banco não muda: o COUNT de não-nulos não tem índice e
    varre a tabela inteira."""
    with _TRAVA:
        _cache_atual()
        if _CACHE["cobertura"] is None:
            try:
                com_vetor, total = db.execute("SELECT COUNT(embedding), COUNT(*) FROM trechos").fetchone()
            except sqlite3.OperationalError:
                return 0, 0
            _CACHE["cobertura"] = (int(com_vetor or 0), int(total or 0))
        return _CACHE["cobertura"]


def _modulo_embeddings():
    """Importa `embeddings` inserindo a pasta dos scripts em sys.path no máximo uma vez.

    Rodado como script a pasta já é sys.path[0]; importado pelo app ela entra uma só vez, para a
    lista não crescer por busca (e esta pasta tem homônimos de módulos do app)."""
    d = os.path.dirname(os.path.abspath(__file__))
    if d not in sys.path:
        sys.path.insert(0, d)
    import embeddings as EMB
    return EMB


def _empilhar(db, EMB, np, extra, filtros):
    """(ids, matriz empilhada|None) dos vetores que casam com o filtro SQL recebido.

    Pula linha cujo BLOB esteja corrompido: uma linha ruim não derruba a busca."""
    ids, vetores = [], []
    for ident, blob in db.execute(
            "SELECT t.id, t.embedding FROM trechos t WHERE t.embedding IS NOT NULL" + extra, filtros):
        try:
            v = EMB.desempacotar(blob)
        except (ValueError, TypeError):
            continue
        if v.size == EMB.DIM:
            ids.append(ident); vetores.append(v)
    return ids, (np.vstack(vetores) if vetores else None)


def _matriz(db, EMB, np):
    """Matriz de TODOS os vetores da base, carregada uma vez por processo (uma por processo, não
    por consulta). Vale só para consulta SEM filtro: com filtro de caso/tipo/modalidade a leitura
    continua indo ao SQL com o filtro, para o filtro não sair do banco."""
    with _TRAVA:  # serializa a carga: dois pedidos simultâneos não montam 74 MB cada
        _cache_atual()
        if _CACHE["ids"] is None:
            _CACHE["ids"], _CACHE["mat"] = _empilhar(db, EMB, np, "", [])
        return _CACHE["ids"], _CACHE["mat"]


def _semantico(db, q, caso, tipo, modalidade, n):
    """([(id, similaridade)] por cosseno, causa de indisponibilidade|None).

    Causa: `ambiente` (fastembed/numpy ausentes), `modelo` (modelo local ainda não baixado — a
    consulta não dispara download), `sem_vetores` (nenhum trecho vetorizado no escopo) ou
    `leitura` (falha ao ler/montar ou consultar os vetores). Descarta candidatos abaixo de SIMILARIDADE_MINIMA."""
    try:
        EMB = _modulo_embeddings()
    except Exception:
        return [], "ambiente"
    extra, filtros = _filtros(caso, tipo, modalidade)
    try:
        tem_vetor = (bool(db.execute("SELECT 1 FROM trechos t WHERE t.embedding IS NOT NULL" + extra + " LIMIT 1",
                                     filtros).fetchone())
                     if extra else cobertura_vetores(db)[0] > 0)
    except sqlite3.OperationalError:
        tem_vetor = False
    if not tem_vetor: return [], "sem_vetores"
    if not EMB.disponivel(): return [], "ambiente"
    try:
        import numpy as np
    except Exception:
        return [], "ambiente"
    em_cache = getattr(EMB, "modelo_em_cache", None)
    if em_cache is not None and not em_cache(): return [], "modelo"
    try:
        ids, mat = _empilhar(db, EMB, np, extra, filtros) if extra else _matriz(db, EMB, np)
    except Exception:
        return [], "leitura"  # consulta nunca cai por causa da leitura dos vetores
    if not ids or mat is None: return [], "sem_vetores"
    try:
        alvo = EMB.vetor(q)
        if alvo is None: return [], None
        sims = mat @ EMB.desempacotar(alvo)
    except Exception:
        return [], "leitura"
    return [(ids[k], float(sims[k])) for k in np.argsort(-sims)[:n]
            if float(sims[k]) >= SIMILARIDADE_MINIMA], None


def buscar(q, caso=None, tipo=None, modalidade=None, n=10, fts=False, modo="auto"):
    """Retorna (lista de dicts, aviso|None).

    Modos: `auto` (padrão) usa a híbrida só quando a base tem vetor em pelo menos
    COBERTURA_MINIMA dos trechos e cai para a textual abaixo disso; `lexical` só FTS;
    `semantico` só vetores; `hibrido` funde as duas listas por RRF.
    `fts=True` (expressão FTS crua) impõe a busca textual em QUALQUER modo — se `hibrido` ou
    `semantico` foi pedido junto, o modo é ignorado e o aviso diz isso.
    O `aviso` informa ainda: resultado exibido que entrou só por semântica, cobertura parcial de
    vetores quando o chamador pediu semântica, modo semântico indisponível (ambiente sem
    fastembed/numpy, modelo local não baixado, base sem vetores ou falha de leitura dos vetores)
    e o recuo para OR do FTS.
    """
    db = conectar()
    try:
        modo = (modo or "auto").lower()
        if modo not in MODOS: raise ValueError(f"Modo inválido: {modo}")
        pedido, avisos = modo, []
        if fts:
            if pedido in ("hibrido", "semantico"):
                avisos.append(f"A expressão FTS crua impõe busca textual: o modo {pedido} pedido foi ignorado.")
            modo = "lexical"
        elif modo != "lexical":  # a cobertura varre a tabela: só é lida onde o modo depende dela
            com_vetor, total = cobertura_vetores(db)
            cobertura = com_vetor / total if total else 0.0
            if modo == "auto":
                modo = "hibrido" if total and cobertura >= COBERTURA_MINIMA else "lexical"
            elif 0 < cobertura < COBERTURA_MINIMA:
                avisos.append(f"A base tem vetor em {cobertura * 100:.0f}% dos trechos; "
                              "o resultado semântico cobre só essa parte.")
        candidatos = max(n * 4, 20)

        ids_lex, snippets = [], {}
        if modo in ("lexical", "hibrido"):
            ids_lex, snippets, aviso_lex = _lexical(
                db, q, caso, tipo, modalidade, n if modo == "lexical" else candidatos, fts)
            if aviso_lex: avisos.append(aviso_lex)
        sem, causa = _semantico(db, q, caso, tipo, modalidade, candidatos) \
            if modo in ("semantico", "hibrido") else ([], None)

        if causa:
            if causa == "ambiente":
                avisos.append("Busca semântica indisponível neste ambiente: fastembed/numpy não estão "
                              "instalados. Use --modo lexical.")
            elif causa == "modelo":
                avisos.append("Busca semântica indisponível: o modelo local de embedding ainda não foi "
                              "baixado. A geração é feita por indexar.py --embeddings.")
            elif causa == "sem_vetores":
                avisos.append("Busca semântica indisponível: a base não tem vetores gerados neste escopo. "
                              "Gere-os com indexar.py --embeddings.")
            elif causa == "leitura":
                avisos.append("Busca semântica indisponível: falha ao consultar os vetores da base. "
                              "Use --modo lexical.")
            if modo == "hibrido":
                avisos.append("A pesquisa ficou limitada à busca textual; não foi possível conferir "
                              "correspondências semânticas.")

        if modo == "lexical":
            ordem = ids_lex[:n]
        elif modo == "semantico":
            ordem = [i for i, _ in sem][:n]
        else:
            pontos = {}
            for posto, i in enumerate(ids_lex): pontos[i] = pontos.get(i, 0.0) + 1.0 / (RRF_K + posto + 1)
            for posto, (i, _) in enumerate(sem): pontos[i] = pontos.get(i, 0.0) + 1.0 / (RRF_K + posto + 1)
            ordem = [i for i, _ in sorted(pontos.items(), key=lambda kv: -kv[1])][:n]
            if ordem and not ids_lex:
                avisos.append("Nenhum trecho contém os termos; resultado por proximidade de sentido. "
                              "Confira o texto nos autos.")
            elif any(i in ordem for i, _ in sem if i not in ids_lex):
                avisos.append("Parte dos resultados exibidos entrou só por proximidade de sentido, sem "
                              "conter os termos. Confira o texto nos autos.")
        aviso = " ".join(avisos) or None
        if not ordem: return [], aviso

        lugares = ",".join("?" * len(ordem))
        linhas = {r[0]: r for r in db.execute(
            f"SELECT id, caso, arquivo, tipo, pagina, fls, secao, texto FROM trechos WHERE id IN ({lugares})", ordem)}
        saida = []
        for i in ordem:
            r = linhas.get(i)
            if not r: continue
            bruto = snippets.get(i)
            if bruto:
                trecho, marcas = _desmarcar(bruto)
            else:  # entrou só por semântica: excerto cru, sem termo casado para destacar
                trecho, marcas = _desmarcar(_resumo(r[7]))[0], []
            saida.append(dict(zip(("caso", "arquivo", "tipo", "pagina", "fls", "secao", "trecho", "marcas"),
                                  (r[1], r[2], r[3], r[4], r[5], r[6], trecho, marcas))))
        return saida, aviso
    finally:
        db.close()


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
      FROM entidades e JOIN entidades o ON o.valor_norm = e.valor_norm AND upper(o.tipo) = upper(e.tipo) AND o.caso <> e.caso
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


CAMPOS_TEXTO = {"nome": "nome_n", "mae": "mae_n", "pai": "pai_n", "endereco": "end_n", "empresa": "emp_n", "texto": "tudo_n",
                # objeto/local/data não têm coluna própria: buscam no texto geral do registro (inclui "extras",
                # onde ficam colunas extra de bases importadas e do pessoas.csv, ex.: objeto, local_fatos, data_fatos).
                "objeto": "tudo_n", "local": "tudo_n", "data": "tudo_n"}
CAMPOS_DIGITO = {"cpf": "cpf_d", "telefone": "tel_d", "cnpj": "cnpj_d", "rg": "rg_d"}


def pesquisa_relacional(filtros, origem=None, limite=200):
    """filtros: dict com qualquer combinação de nome, mae, pai, endereco, empresa, texto, cpf, telefone, cnpj, rg,
    objeto, local, data (estes três buscam em todo o registro, inclusive campos extras importados).
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


COLUNAS_GRAFO = ('a_tipo','a_valor','b_tipo','b_valor','relacao','origem','fonte','localizador')
ORDEM_GRAFO='a_tipo,a_valor,b_tipo,b_valor,relacao:asc'
INDICES_GRAFO_SQL=(
    'CREATE INDEX IF NOT EXISTS ix_ar_relacao ON arestas(a_tipo,a_valor,b_tipo,b_valor,relacao,origem,fonte)',
    'CREATE INDEX IF NOT EXISTS ix_ar_fonte ON arestas(fonte,a_tipo,a_valor,b_tipo,b_valor,relacao)',
    'CREATE INDEX IF NOT EXISTS ix_ar_origem ON arestas(origem)',
)


def metadados_pagina(total,pagina,limite,retornadas):
    return {'total':total,'pagina':pagina,'limite':limite,'total_retornado':retornadas,
            'proxima_pagina':pagina+1 if pagina*limite<total else None,
            'truncado':total>retornadas,'ordem':ORDEM_GRAFO,
            'completude':'parcial' if total>retornadas else 'completa_no_escopo',
            'limites':{'relacoes':limite}}


def _rotulos_cte(db,manuais,nos=None,busca=False):
    if nos not in (None,'nos','selecionados'):raise ValueError('Escopo interno de rótulos inválido.')
    join=f' JOIN {nos} n ON n.tipo=r.tipo AND n.valor=r.valor' if nos else ''
    if manuais is None:return 'rotulos_efetivos AS (SELECT r.tipo,r.valor,r.rotulo FROM rotulos r'+join+')',[]
    rot={(a[lado+'_tipo'],a[lado+'_valor']):a[lado+'_rotulo'] for a in manuais for lado in ('a','b') if a.get(lado+'_rotulo')}
    rastreada=db.execute("SELECT 1 FROM sqlite_master WHERE name='grafo_rotulos_manuais' AND type='table'").fetchone()
    base=("SELECT r.tipo,r.valor,CASE WHEN r.rotulo IS m.rotulo THEN m.anterior ELSE r.rotulo END rotulo "
          "FROM rotulos r"+join+" LEFT JOIN grafo_rotulos_manuais m ON m.tipo=r.tipo AND m.valor=r.valor" if rastreada
          else 'SELECT r.tipo,r.valor,r.rotulo FROM rotulos r'+join)
    if not rot and not rastreada:return 'rotulos_efetivos AS ('+base+')',[]
    efetivos=("SELECT tipo,valor,rotulo FROM rotulos_base UNION SELECT tipo,valor,rotulo FROM rotulos_ativos" if busca else
            "SELECT r.tipo,r.valor,coalesce(m.rotulo,r.rotulo) rotulo FROM rotulos_base r "
            "LEFT JOIN rotulos_ativos m ON m.tipo=r.tipo AND m.valor=r.valor UNION ALL "
            "SELECT m.tipo,m.valor,m.rotulo FROM rotulos_ativos m WHERE NOT EXISTS "
            "(SELECT 1 FROM rotulos_base r WHERE r.tipo=m.tipo AND r.valor=m.valor)")
    return ("rotulos_ativos AS (SELECT json_extract(value,'$[0]') tipo,json_extract(value,'$[1]') valor,"
            "json_extract(value,'$[2]') rotulo FROM json_each(?)),rotulos_base AS ("+base+"),"
            "rotulos_efetivos AS ("+efetivos+")",
            [json.dumps([[t,v,r] for (t,v),r in rot.items()],ensure_ascii=False)])


def rotulos_em_lote(db,chaves,manuais=None):
    """Rótulos por pares (tipo,valor), sem SELECT individual nem importação de app."""
    chaves=list(dict.fromkeys(tuple(k) for k in chaves));rot={}
    if not chaves:return rot
    cte,params=_rotulos_cte(db,manuais,'selecionados')
    for inicio in range(0,len(chaves),150):
        lote=chaves[inicio:inicio+150];valores=','.join('(?,?)' for _ in lote)
        rows=db.execute(f'WITH {cte},selecionados(tipo,valor) AS (VALUES {valores}) '
                        'SELECT r.tipo,r.valor,r.rotulo FROM rotulos_efetivos r JOIN selecionados s '
                        'ON r.tipo IS s.tipo AND r.valor IS s.valor',params+[v for k in lote for v in k]).fetchall()
        rot.update({(t,v):r for t,v,r in rows if r})
    pessoas=[v for t,v in chaves if t=='PESSOA' and (t,v) not in rot]
    for inicio in range(0,len(pessoas),150):
        lote=pessoas[inicio:inicio+150]
        rows=db.execute('SELECT a_valor,min(b_valor) FROM arestas WHERE a_tipo=? AND b_tipo=? AND a_valor IN ('+
                        ','.join('?' for _ in lote)+') GROUP BY a_valor',['PESSOA','NOME']+lote).fetchall()
        rot.update({('PESSOA',v):n.title() for v,n in rows if n})
    return rot


def pagina_grafo(db,caso=None,termo='',manuais=(),pagina=1,limite=400,seeds=None,niveis=2,caso_cadastrado=True):
    """Paginação de tuplas lógicas, com universo exato e sem cortar sementes/fontes.

    O chamador fornece as linhas manuais já conciliadas com a fonte autoritativa.
    Todo acesso usa a mesma conexão/transação de leitura do chamador.
    """
    campos=','.join(COLUNAS_GRAFO[:5]);escopo,params=escopo_grafo(caso)
    filtro="origem IS NOT 'manual' AND "+escopo
    if caso:
        # Localizador nativo determina o caso da referência. Consulta não vira autos.
        filtro+=(" AND CASE WHEN json_valid(localizador) THEN CASE WHEN json_extract(localizador,'$.schema')='astra-evidencia/1' "
                 "THEN json_extract(localizador,'$.caso') ELSE CASE WHEN origem IS NOT 'consulta' AND (origem='caso' OR ?) "
                 "THEN fonte END END ELSE CASE WHEN origem IS NOT 'consulta' AND (origem='caso' OR ?) THEN fonte END END=?")
        params.extend([bool(caso_cadastrado),bool(caso_cadastrado),caso])
    elif not termo and seeds is None:filtro+=" AND relacao IS NOT 'consta nos autos'"
    manual_keys=list(dict.fromkeys(tuple(a[k] for k in COLUNAS_GRAFO[:5]) for a in manuais))
    extrair=','.join(f"json_extract(value,'$[{i}]') {c}" for i,c in enumerate(COLUNAS_GRAFO[:5]))
    ctes=[f'documentais AS (SELECT {campos} FROM arestas WHERE {filtro} GROUP BY {campos})',
          f'manuais AS (SELECT {extrair} FROM json_each(?))',
          f'relacoes AS (SELECT {campos} FROM documentais UNION SELECT {campos} FROM manuais)']
    params.append(json.dumps(manual_keys,ensure_ascii=False))
    if termo or seeds is not None:
        rot,par=_rotulos_cte(db,manuais,'nos',busca=True);ctes.append(rot);params.extend(par)
        ctes.append('nos AS (SELECT a_tipo tipo,a_valor valor FROM relacoes UNION SELECT b_tipo,b_valor FROM relacoes)')
        if seeds is None:
            tipos=[t for t in TIPOS_NO if t!='CASO' and (t!='PESSOA' or termo.startswith('P:'))]
            numerico=bool(re.fullmatch(r'[\d.\-/() +]+',termo))
            tipos=[t for t in tipos if t not in ('CPF','CNPJ','TELEFONE','RG','PROCESSO','BO','CONTA')
                   or numerico or (t=='CONTA' and '|' in termo)]
            chaves=[(t,chave_no(t,termo).lower()) for t in tipos if chave_no(t,termo)]
            filtros=' OR '.join('(n.tipo=? AND instr(lower(n.valor),?)>0)' for _ in chaves)
            params.extend([v for k in chaves for v in k]+[termo.lower()])
            busca=_n(termo)
            adicionais=[(a[lado+'_tipo'],a[lado+'_valor']) for a in manuais for lado in ('a','b')
                        if busca in _n(' '.join(str(a.get(k,'')) for k in ('a_valor','b_valor','a_rotulo','b_rotulo','relacao')))]
            ctes.append(f"sementes AS (SELECT n.tipo,n.valor FROM nos n LEFT JOIN rotulos_efetivos r ON r.tipo=n.tipo AND r.valor=n.valor "
                        f"WHERE ({filtros or '0'}) OR (n.tipo!='CASO' AND instr(lower(coalesce(r.rotulo,'')),?)>0) UNION "
                        "SELECT json_extract(value,'$[0]'),json_extract(value,'$[1]') FROM json_each(?))")
            params.append(json.dumps(adicionais,ensure_ascii=False))
        else:
            t,v=seeds
            ctes.append("sementes AS (SELECT tipo,valor FROM nos WHERE tipo=? AND "+
                        ("substr(valor,-length(?)-1)='|'||?" if t=='CONTA' and '|' not in v else 'valor=?')+")")
            params.extend([t,v,v] if t=='CONTA' and '|' not in v else [t,v])
        ctes.append("alcance(tipo,valor,nivel) AS (SELECT tipo,valor,0 FROM sementes UNION "
                    "SELECT a.b_tipo,a.b_valor,n.nivel+1 FROM alcance n JOIN relacoes a ON a.a_tipo=n.tipo AND a.a_valor=n.valor "
                    "WHERE n.nivel<? AND (n.tipo!='NOME' OR n.nivel=0) UNION "
                    "SELECT a.a_tipo,a.a_valor,n.nivel+1 FROM alcance n JOIN relacoes a ON a.b_tipo=n.tipo AND a.b_valor=n.valor "
                    "WHERE n.nivel<? AND (n.tipo!='NOME' OR n.nivel=0))")
        params.extend([niveis,niveis])
        ctes.append('niveis_nos AS (SELECT tipo,valor,min(nivel) nivel FROM alcance GROUP BY tipo,valor)')
        ctes.append("expansiveis AS (SELECT tipo,valor FROM niveis_nos WHERE nivel<? AND (tipo!='NOME' OR nivel=0))")
        params.append(niveis)
        ctes.append("elegiveis AS (SELECT r.* FROM relacoes r JOIN expansiveis n ON r.a_tipo=n.tipo AND r.a_valor=n.valor UNION "
                    "SELECT r.* FROM relacoes r JOIN expansiveis n ON r.b_tipo=n.tipo AND r.b_valor=n.valor)")
    else:ctes.append('elegiveis AS (SELECT * FROM relacoes)')
    niveis_colunas='0,0';niveis_joins=''
    if termo or seeds is not None:
        niveis_colunas='na.nivel,nb.nivel'
        niveis_joins=(' LEFT JOIN niveis_nos na ON na.tipo IS p.a_tipo AND na.valor IS p.a_valor '
                      'LEFT JOIN niveis_nos nb ON nb.tipo IS p.b_tipo AND nb.valor IS p.b_valor')
    sql=('WITH RECURSIVE '+','.join(ctes)+f',pagina AS (SELECT {campos},1 presente FROM elegiveis '
         f'ORDER BY {campos} LIMIT ? OFFSET ?) SELECT t.total,p.*,'+niveis_colunas+' FROM (SELECT count(*) total FROM elegiveis) t '
         'LEFT JOIN pagina p ON 1'+niveis_joins+' ORDER BY '+','.join('p.'+c for c in COLUNAS_GRAFO[:5]))
    rows=db.execute(sql,params+[limite,(pagina-1)*limite]).fetchall()
    chaves=[tuple(r[1:6]) for r in rows if r[6] is not None]
    niveis_nos={(r[i],r[i+1]):r[7 if i==1 else 8] for r in rows if r[6] is not None for i in (1,3)}
    return {'chaves':chaves,'niveis_nos':niveis_nos,**metadados_pagina(rows[0][0],pagina,limite,len(chaves))}


def escopo_grafo(caso=None, alias=''):
    p=alias+'.' if alias else ''
    return ((f"({p}fonte=? OR ({p}a_tipo='CASO' AND {p}a_valor=?) OR ({p}b_tipo='CASO' AND {p}b_valor=?))", [caso]*3)
            if caso else ('1',[]))


def referencias_relacoes(db, chaves, caso=None, interno=True):
    """Todas as referências das relações selecionadas; corte ocorre antes delas."""
    chaves=list(dict.fromkeys(tuple(k) for k in chaves)); saida=[]
    for inicio in range(0,len(chaves),150):
        lote=chaves[inicio:inicio+150]
        valores=','.join('(?,?,?,?,?)' for _ in lote)
        campos=','.join(COLUNAS_GRAFO[:5])
        join=' AND '.join(f'a.{k} IS s.{k}' for k in COLUNAS_GRAFO[:5])
        escopo,params=escopo_grafo(caso,'a')
        rows=db.execute(f'WITH selecionadas({campos}) AS (VALUES {valores}) '
                        f"SELECT a.rowid,{','.join('a.'+k for k in COLUNAS_GRAFO)} FROM arestas a "
                        f'JOIN selecionadas s ON {join} WHERE {escopo} ORDER BY a.rowid',
                        [v for k in lote for v in k]+params).fetchall()
        for row in rows:
            a=dict(zip(COLUNAS_GRAFO,row[1:]))
            if interno:a['_rowid']=row[0]
            saida.append(a)
    return saida


def vinculos(tipo, valor, niveis=2, limite=400, caso=None, interno=False):
    """Grafo de vínculos (registros de pessoa, nomes, telefones, veículos, endereços, empresas, processos, contas,
    chaves Pix, casos) a partir do nó informado, até `niveis` saltos. Retorna {nos, arestas} com rótulos.
    Identidade: PESSOA é o registro de origem (id 'P:...'); o nome é apenas um nó NOME (candidato a conferir) e
    não é atravessado — homônimos aparecem como candidatos, sem trazer os vínculos uns dos outros."""
    db=conectar()
    try:
        try:db.execute('SELECT 1 FROM arestas LIMIT 1')
        except sqlite3.OperationalError:return {'nos':[],'arestas':[],'truncado':None,'completude':'indice_indisponivel'}
        t0=(tipo or '').upper()
        if t0=='PESSOA' and not str(valor or '').startswith('P:'):t0='NOME'
        k0=chave_no(t0,valor)
        if not k0:return {'nos':[],'arestas':[],'truncado':False,'completude':'completa_no_escopo'}
        inicios=[(t0,k0)];truncado=False
        if t0=='CONTA' and '|' not in k0:
            escopo,params=escopo_grafo(caso)
            rows=db.execute("SELECT a_valor FROM arestas WHERE a_tipo='CONTA' AND a_valor LIKE ? AND "+escopo+
                            " UNION SELECT b_valor FROM arestas WHERE b_tipo='CONTA' AND b_valor LIKE ? AND "+escopo+
                            ' ORDER BY 1 LIMIT ?', [f'%|{k0}']+params+[f'%|{k0}']+params+[limite+1]).fetchall()
            truncado=len(rows)>limite
            inicios=[('CONTA',r[0]) for r in rows[:limite]] or inicios
        vistos={i:0 for i in inicios};fronteira=list(inicios);chaves={}
        escopo,params=escopo_grafo(caso)
        campos=','.join(COLUNAS_GRAFO[:5])
        for nivel in range(1,niveis+1):
            prox=[]
            for t,v in fronteira:
                if t in NAO_EXPANDIR and vistos[t,v]!=0:continue
                rows=db.execute(f'SELECT {campos} FROM arestas WHERE ((a_tipo=? AND a_valor=?) OR '
                                f'(b_tipo=? AND b_valor=?)) AND {escopo} GROUP BY {campos} ORDER BY {campos} LIMIT ?',
                                [t,v,t,v]+params+[limite+1]).fetchall()
                if len(rows)>limite:truncado=True
                for r in rows[:limite]:
                    novos={no for no in ((r[0],r[1]),(r[2],r[3])) if no not in vistos}
                    if len(vistos)+len(novos)>limite:truncado=True;continue
                    chaves[tuple(r)]=None
                    for no in novos:vistos[no]=nivel;prox.append(no)
            fronteira=prox
        arestas=referencias_relacoes(db,chaves,caso,interno=interno)
        rot={}
        try:
            rot=rotulos_em_lote(db,vistos)
        except sqlite3.OperationalError:pass
        return {'nos':[{'tipo':t,'valor':v,'nivel':n,'rotulo':rot.get((t,v),v)} for (t,v),n in vistos.items()],
                'arestas':arestas,'truncado':truncado,'completude':'parcial' if truncado else 'completa_no_escopo',
                'limites':{'nos':limite,'relacoes_por_no':limite,'niveis':niveis}}
    finally:db.close()


def stats():
    db = conectar()
    out = {"trechos": dict(db.execute("SELECT tipo, COUNT(*) FROM trechos GROUP BY tipo").fetchall()),
           "documentos": db.execute("SELECT COUNT(*) FROM docs").fetchone()[0],
           "entidades": db.execute("SELECT COUNT(*) FROM entidades").fetchone()[0],
           "casos": db.execute("SELECT COUNT(DISTINCT caso) FROM trechos WHERE caso IS NOT NULL").fetchone()[0]}
    try:
        out["vetores"] = db.execute("SELECT COUNT(*) FROM trechos WHERE embedding IS NOT NULL").fetchone()[0]
    except sqlite3.OperationalError:
        out["vetores"] = 0
    db.close(); return out


if __name__ == "__main__":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("buscar"); s.add_argument("q"); s.add_argument("--caso"); s.add_argument("--tipo")
    s.add_argument("--modalidade"); s.add_argument("-n", type=int, default=10); s.add_argument("--fts", action="store_true")
    s.add_argument("--modo", choices=MODOS, default="auto",
                   help="auto: híbrida se a base estiver vetorizada (>= 90%% dos trechos); lexical: só FTS; "
                        "semantico: só vetores. Com --fts a busca é sempre textual")
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
            res, aviso = buscar(a.q, a.caso, a.tipo, a.modalidade, a.n, a.fts, a.modo)
            if aviso: print(f"({aviso})")
            if not res: print("Nada encontrado.")
            for r in res:
                loc = f"pág. {r['pagina']}" if r["pagina"] else (r["secao"] or "")
                loc += f"; fls. {r['fls']}" if r["fls"] else ""
                texto = _realcar(r["trecho"], r["marcas"]).strip()
                print(f"\n■ {r['caso'] or '-'} | {r['tipo']} | {loc}\n  {r['arquivo']}\n  {texto}")
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
            print(f"  vetores (híbrida) {s['vetores']}")
    except (FileNotFoundError, ValueError) as e:
        raise SystemExit(f"ERRO: {e}")
