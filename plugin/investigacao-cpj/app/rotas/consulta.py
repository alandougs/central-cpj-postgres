#!/usr/bin/env python3
"""Rotas de bases de consulta, referências, pesquisa textual/relacional e cruzamento de dados."""
import json
import os
import re
import threading
import time
from flask import Blueprint, abort, jsonify, request
from rotas.comum import (
    Q,
    R,
    RF,
    WS,
    auditar,
    requer,
    salvar_upload,
    tarefas,
)

bp_consulta = Blueprint("consulta", __name__)


@bp_consulta.get("/api/consulta/bases")
@requer("dados")
def api_bases():
    return jsonify(Q.listar())


@bp_consulta.post("/api/consulta/importar")
@requer("dados")
def api_bases_importar():
    try:
        p, nome = salvar_upload("arquivo", Q.FORMATOS)
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    rotulo = (request.form.get("nome") or os.path.splitext(nome)[0]).strip()
    tid = tarefas.nova("consulta", f"Base de consulta: {rotulo}", request.usuario["login"])
    tarefas.rodar(tid, tarefas.importar_consulta, p, rotulo)
    auditar("base_consulta_importada", rotulo)
    return jsonify({"tarefa": tid})


@bp_consulta.post("/api/consulta/colar")
@requer("dados")
def api_bases_colar():
    d = request.get_json(force=True) or {}
    texto = (d.get("texto") or "").strip()
    if not texto:
        return jsonify({"erro": "Cole o texto a importar."}), 400
    if len(texto) > 2_000_000:
        return jsonify({"erro": "Texto grande demais; envie como arquivo."}), 400
    rotulo = (d.get("nome") or "Texto colado").strip()
    dest = os.path.join(WS, "exportacoes", "_recebidos")
    os.makedirs(dest, exist_ok=True)
    p = os.path.join(dest, f"{time.time_ns()}-colado.txt")
    with open(p, "w", encoding="utf-8") as f:
        f.write(texto)
    tid = tarefas.nova("consulta", f"Base de consulta (texto colado): {rotulo}", request.usuario["login"])
    tarefas.rodar(tid, tarefas.importar_consulta, p, rotulo)
    auditar("base_consulta_colada", rotulo)
    return jsonify({"tarefa": tid})


@bp_consulta.get("/api/vinculos")
@requer("pesquisa")
def api_vinculos():
    tipo = request.args.get("tipo") or "PESSOA"
    valor = request.args.get("valor") or ""
    try:
        niveis = max(1, min(3, int(request.args.get("niveis") or 2)))
    except ValueError:
        niveis = 2
    try:
        g = R.vinculos(tipo, valor, niveis)
    except FileNotFoundError:
        g = {"nos": [], "arestas": []}
    auditar("pesquisa_vinculos", f"{tipo}: {valor[:80]}")
    return jsonify(g)


@bp_consulta.get("/api/grafo")
@requer("pesquisa")
def api_grafo():
    caso = request.args.get("caso") or ""
    termo = (request.args.get("q") or "").strip()
    try:
        db = R.conectar()
    except FileNotFoundError:
        return jsonify({"nos": [], "arestas": [], "casos": []})

    casos_rows = db.execute("SELECT DISTINCT b_valor FROM arestas WHERE b_tipo='CASO' UNION SELECT DISTINCT a_valor FROM arestas WHERE a_tipo='CASO'").fetchall()
    casos_disp = sorted([r[0] for r in casos_rows if r[0]])

    arestas = []
    if caso:
        p_rows = db.execute("""
            SELECT DISTINCT a_tipo, a_valor, b_tipo, b_valor, relacao, origem, fonte, localizador
            FROM arestas
            WHERE (b_tipo='CASO' AND b_valor=?) OR (a_tipo='CASO' AND a_valor=?)
            ORDER BY (CASE WHEN relacao != 'consta nos autos' THEN 0 ELSE 1 END)
            LIMIT 60
        """, (caso, caso)).fetchall()
        arestas.extend([dict(zip(("a_tipo", "a_valor", "b_tipo", "b_valor", "relacao", "origem", "fonte", "localizador"), r)) for r in p_rows])

        p_ids = [r["a_valor"] if r["a_tipo"] == "PESSOA" else r["b_valor"] for r in arestas if r["a_tipo"] == "PESSOA" or r["b_tipo"] == "PESSOA"]
        if p_ids:
            ph = ",".join(["?"] * len(p_ids))
            v_rows = db.execute(f"""
                SELECT DISTINCT a_tipo, a_valor, b_tipo, b_valor, relacao, origem, fonte, localizador
                FROM arestas
                WHERE (a_tipo='PESSOA' AND a_valor IN ({ph}))
                   OR (b_tipo='PESSOA' AND b_valor IN ({ph}))
            """, p_ids + p_ids).fetchall()
            arestas.extend([dict(zip(("a_tipo", "a_valor", "b_tipo", "b_valor", "relacao", "origem", "fonte", "localizador"), r)) for r in v_rows])

        tr_rows = db.execute("""
            SELECT DISTINCT a_tipo, a_valor, b_tipo, b_valor, relacao, origem, fonte, localizador
            FROM arestas
            WHERE fonte=? AND (relacao LIKE '%transferiu%' OR relacao LIKE '%Pix%' OR relacao LIKE '%TED%' OR relacao LIKE '%titular%')
        """, (caso,)).fetchall()
        arestas.extend([dict(zip(("a_tipo", "a_valor", "b_tipo", "b_valor", "relacao", "origem", "fonte", "localizador"), r)) for r in tr_rows])

        man_rows = db.execute("""
            SELECT DISTINCT a_tipo, a_valor, b_tipo, b_valor, relacao, origem, fonte, localizador
            FROM arestas
            WHERE origem='manual' AND (fonte=? OR a_valor=? OR b_valor=?)
        """, (caso, caso, caso)).fetchall()
        arestas.extend([dict(zip(("a_tipo", "a_valor", "b_tipo", "b_valor", "relacao", "origem", "fonte", "localizador"), r)) for r in man_rows])

    elif termo:
        g = R.vinculos("PESSOA", termo, niveis=2, limite=300)
        if not g.get("nos"):
            g = R.vinculos("NOME", termo, niveis=2, limite=300)
        if not g.get("nos"):
            g = R.vinculos("CPF", termo, niveis=2, limite=300)
        if not g.get("nos"):
            g = R.vinculos("CONTA", termo, niveis=2, limite=300)
        if not g.get("nos"):
            g = R.vinculos("CHAVE_PIX", termo, niveis=2, limite=300)
        arestas = g.get("arestas", [])
    else:
        rows = db.execute("""
            SELECT DISTINCT a_tipo, a_valor, b_tipo, b_valor, relacao, origem, fonte, localizador
            FROM arestas
            WHERE relacao != 'consta nos autos'
            ORDER BY (CASE WHEN origem='manual' THEN 0 WHEN relacao LIKE '%transferiu%' THEN 1 WHEN a_tipo='PESSOA' OR b_tipo='PESSOA' THEN 2 ELSE 3 END)
            LIMIT 400
        """).fetchall()
        arestas = [dict(zip(("a_tipo", "a_valor", "b_tipo", "b_valor", "relacao", "origem", "fonte", "localizador"), r)) for r in rows]

    unicas = []
    vistos_arestas = set()
    vistos_nos = set()
    for a in arestas:
        chave_a = (a["a_tipo"], a["a_valor"], a["b_tipo"], a["b_valor"], a["relacao"])
        if chave_a not in vistos_arestas:
            vistos_arestas.add(chave_a)
            unicas.append(a)
            vistos_nos.add((a["a_tipo"], a["a_valor"]))
            vistos_nos.add((a["b_tipo"], a["b_valor"]))

    rot = {}
    for t, v in vistos_nos:
        x = db.execute("SELECT rotulo FROM rotulos WHERE tipo=? AND valor=?", (t, v)).fetchone()
        if x and x[0]:
            rot[(t, v)] = x[0]
        elif t == "PESSOA":
            n_row = db.execute("SELECT b_valor FROM arestas WHERE a_tipo='PESSOA' AND a_valor=? AND b_tipo='NOME' LIMIT 1", (v,)).fetchone()
            rot[(t, v)] = n_row[0].title() if n_row and n_row[0] else v
        else:
            rot[(t, v)] = v

    db.close()
    nos_saida = [{"tipo": t, "valor": v, "nivel": 0, "rotulo": rot.get((t, v), v)} for t, v in vistos_nos]
    g = {"nos": nos_saida, "arestas": unicas, "casos": casos_disp}
    auditar("grafo_consultado", f"caso={caso}; q={termo}")
    return jsonify(g)


@bp_consulta.post("/api/grafo/vinculo")
@requer("pesquisa")
def api_grafo_adicionar_vinculo():
    dados = request.get_json(force=True) or {}
    a_tipo = (dados.get("a_tipo") or "").strip().upper()
    a_valor = (dados.get("a_valor") or "").strip()
    b_tipo = (dados.get("b_tipo") or "").strip().upper()
    b_valor = (dados.get("b_valor") or "").strip()
    relacao = (dados.get("relacao") or "vinculado a").strip()
    obs = (dados.get("obs") or "").strip()
    caso = (dados.get("caso") or "").strip()

    if not (a_tipo and a_valor and b_tipo and b_valor and relacao):
        return jsonify({"erro": "Informe tipo e valor de origem e destino, além da relação."}), 400

    try:
        db = R.conectar()
        db.execute("""
            INSERT INTO arestas (a_tipo, a_valor, b_tipo, b_valor, relacao, origem, fonte, localizador)
            VALUES (?, ?, ?, ?, ?, 'manual', ?, ?)
        """, (a_tipo, a_valor, b_tipo, b_valor, relacao, caso or "investigador", obs or "Vínculo manual cadastrado pelo investigador"))

        if dados.get("a_rotulo"):
            db.execute("INSERT OR REPLACE INTO rotulos (tipo, valor, rotulo) VALUES (?, ?, ?)", (a_tipo, a_valor, dados["a_rotulo"]))
        if dados.get("b_rotulo"):
            db.execute("INSERT OR REPLACE INTO rotulos (tipo, valor, rotulo) VALUES (?, ?, ?)", (b_tipo, b_valor, dados["b_rotulo"]))

        db.commit()
        db.close()
        auditar("grafo_vinculo_criado", f"{a_tipo}:{a_valor} -> {relacao} -> {b_tipo}:{b_valor}")
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@bp_consulta.post("/api/grafo/vinculo/remover")
@requer("pesquisa")
def api_grafo_remover_vinculo():
    dados = request.get_json(force=True) or {}
    a_tipo = dados.get("a_tipo")
    a_valor = dados.get("a_valor")
    b_tipo = dados.get("b_tipo")
    b_valor = dados.get("b_valor")
    relacao = dados.get("relacao")

    if not (a_tipo and a_valor and b_tipo and b_valor and relacao):
        return jsonify({"erro": "Parâmetros insuficientes para remover vínculo."}), 400

    try:
        db = R.conectar()
        db.execute("""
            DELETE FROM arestas
            WHERE a_tipo=? AND a_valor=? AND b_tipo=? AND b_valor=? AND relacao=?
        """, (a_tipo, a_valor, b_tipo, b_valor, relacao))
        db.commit()
        db.close()
        auditar("grafo_vinculo_removido", f"{a_tipo}:{a_valor} -> {relacao} -> {b_tipo}:{b_valor}")
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500



@bp_consulta.post("/api/consulta/bases/<bid>/remover")
@requer("dados")
def api_bases_remover(bid):
    try:
        Q.remover(bid)
    except FileNotFoundError:
        abort(404)
    threading.Thread(target=tarefas.indexar, daemon=True).start()
    auditar("base_consulta_removida", bid)
    return jsonify({"ok": True})


@bp_consulta.get("/api/referencias")
@requer("dados")
def api_refs():
    return jsonify(RF.listar(request.args.get("autor") or None))


@bp_consulta.post("/api/referencias/importar")
@requer("dados")
def api_refs_importar():
    try:
        p, nome = salvar_upload("arquivo", (".docx", ".pdf", ".md"))
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    f = request.form
    if not (f.get("autor") or "").strip():
        return jsonify({"erro": "Informe o autor."}), 400
    dados = {k: f.get(k) for k in ("autor", "modalidade", "natureza", "peso", "obs")} | {
        "enviado_por": request.usuario["login"]
    }
    tid = tarefas.nova("referencia", f"Referência: {nome} ({dados['autor']})", request.usuario["login"])
    tarefas.rodar(tid, tarefas.importar_referencia, p, dados)
    auditar("referencia_importada", f"{nome} — {dados['autor']}")
    return jsonify({"tarefa": tid})


@bp_consulta.post("/api/referencias/<rid>")
@requer("dados")
def api_refs_atualizar(rid):
    d = request.get_json(force=True) or {}
    try:
        m = RF.atualizar(rid, **{k: d.get(k) for k in ("autor", "modalidade", "natureza", "peso", "obs")})
    except FileNotFoundError:
        abort(404)
    threading.Thread(target=tarefas.indexar, daemon=True).start()
    auditar("referencia_atualizada", rid)
    return jsonify(m)


@bp_consulta.post("/api/referencias/<rid>/remover")
@requer("dados")
def api_refs_remover(rid):
    try:
        RF.remover(rid)
    except FileNotFoundError:
        abort(404)
    threading.Thread(target=tarefas.indexar, daemon=True).start()
    auditar("referencia_removida", rid)
    return jsonify({"ok": True})


@bp_consulta.get("/api/pesquisa/pessoas")
@requer("pesquisa")
def api_pesquisa_pessoas():
    f = {
        k: request.args.get(k)
        for k in (
            "nome", "mae", "pai", "cpf", "rg", "telefone", "cnpj", "empresa", "endereco", "texto",
            "processo", "bo", "placa", "mandado", "cautelar", "mandado_estado", "cautelar_estado",
            "objeto", "local", "data"
        )
    }
    try:
        ps, oc = R.pesquisa_relacional(f, origem=request.args.get("origem") or None)
    except FileNotFoundError:
        return jsonify({"pessoas": [], "ocorrencias": [], "aviso": "Base ainda vazia."})
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    auditar("pesquisa_pessoas", json.dumps({k: v for k, v in f.items() if v}, ensure_ascii=False)[:300])
    return jsonify({"pessoas": ps, "ocorrencias": oc, "aviso": None if ps or oc else "Nenhum resultado."})


@bp_consulta.get("/api/busca")
@requer("pesquisa")
def api_busca():
    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify({"trechos": [], "entidades": [], "aviso": None})
    try:
        tipo = request.args.get("tipo") or None
        trechos, aviso = R.buscar(q, caso=request.args.get("caso") or None, tipo=tipo, n=int(request.args.get("n") or 25))
        ents = (
            R.entidade(q)
            if (len(re.sub(r"\D", "", q)) >= 6 or "@" in q or re.fullmatch(r"[A-Za-z]{3}-?\d[A-Za-z0-9]\d{2}", q))
            else []
        )
        auditar("pesquisa_texto", q[:200])
        return jsonify({"trechos": trechos, "entidades": ents, "aviso": aviso})
    except FileNotFoundError:
        return jsonify({"trechos": [], "entidades": [], "aviso": "Índice ainda não criado — processe um caso primeiro."})
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400


@bp_consulta.get("/api/cruzar/<id_>")
@requer("trabalho")
def api_cruzar(id_):
    try:
        return jsonify(R.cruzar(id_))
    except FileNotFoundError:
        return jsonify([])

