#!/usr/bin/env python3
"""Rotas de bases de consulta, referências, pesquisa textual/relacional e cruzamento de dados."""
import json
import os
import re
import sqlite3
import threading
import time
from flask import Blueprint, abort, jsonify, request
from rotas.comum import (
    C,
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


def _fonte_manual(registro):
    evidencia = registro.get("evidencia") or {}
    localizador = " · ".join(str(v) for v in (evidencia.get("documento"), f"pág. {evidencia['pagina']}" if evidencia.get("pagina") else "", f"fls. {evidencia['fls']}" if evidencia.get("fls") else "", evidencia.get("observacao")) if v)
    return {**registro, "origem":"manual", "fonte":registro.get("caso", ""), "localizador":localizador}


def _manuais_grafo(caso, termo):
    import vinculos_manuais as VM
    todos = VM.listar(WS, incluir_excluidos=True)
    ativos = [r for r in todos if not r.get("excluido") and (not caso or r.get("caso") == caso)]
    if termo:
        busca = R._n(termo)
        ativos = [r for r in ativos if busca in R._n(" ".join(str(r.get(c, "")) for c in ("a_valor","b_valor","a_rotulo","b_rotulo","relacao")))]
    return [_fonte_manual(r) for r in ativos], {r["id"] for r in todos}


def _grafo_sem_indice(vazio, manuais):
    nos = {}
    for a in manuais:
        for lado in ("a", "b"):
            tipo, valor = a[f"{lado}_tipo"], a[f"{lado}_valor"]
            nos[tipo,valor] = {"tipo":tipo,"valor":valor,"nivel":0,"rotulo":a.get(f"{lado}_rotulo") or valor}
    return jsonify({**vazio,"nos":list(nos.values()),"arestas":manuais,
                    "aviso":"Vínculos manuais preservados; reindexe para recuperar as relações documentais." if manuais else ""})


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


def _ordens_servico_grafo():
    ordens = [{"id": c["id"], "ordem_servico": c.get("ordem_servico") or c["id"]}
              for c in C.listar() if c.get("id")]

    def ordem(c):
        numeros = re.findall(r"\d+", str(c["ordem_servico"]))
        return (0, tuple(int(n) for n in numeros), c["id"]) if numeros else (1, (), c["id"])

    return sorted(ordens, key=ordem)


def _arestas_busca_grafo(db, termo, caso):
    # Resolva apenas nós existentes; nomes continuam candidatos, com registros PESSOA separados.
    tipos = [t for t in R.TIPOS_NO if t != "CASO" and (t != "PESSOA" or termo.startswith("P:"))]
    numerico = bool(re.fullmatch(r"[\d.\-/() +]+", termo))
    tipos = [t for t in tipos if t not in ("CPF", "CNPJ", "TELEFONE", "RG", "PROCESSO", "BO", "CONTA")
             or numerico or (t == "CONTA" and "|" in termo)]
    chaves = [(t, R.chave_no(t, termo)) for t in tipos]
    chaves = [(t, v.lower()) for t, v in chaves if v]
    filtros = " OR ".join("(n.tipo=? AND instr(lower(n.valor),?)>0)" for _ in chaves)
    parametros = [v for par in chaves for v in par]
    escopo = "WHERE fonte=? OR (a_tipo='CASO' AND a_valor=?) OR (b_tipo='CASO' AND b_valor=?)" if caso else ""
    escopo_par = [caso] * 6 if caso else []
    seeds = db.execute(f"""
        WITH nos AS (
            SELECT a_tipo AS tipo,a_valor AS valor FROM arestas {escopo}
            UNION SELECT b_tipo,b_valor FROM arestas {escopo}
        )
        SELECT n.tipo,n.valor FROM nos n LEFT JOIN rotulos r ON r.tipo=n.tipo AND r.valor=n.valor
        WHERE ({filtros or '0'}) OR (n.tipo!='CASO' AND instr(lower(coalesce(r.rotulo,'')),?)>0)
        ORDER BY n.tipo,n.valor LIMIT 30
    """, escopo_par + parametros + [termo.lower()]).fetchall()
    arestas = []
    vistas = set()
    for tipo, valor in seeds:
        for a in R.vinculos(tipo, valor, niveis=2, limite=300).get("arestas", []):
            if caso and not (a["fonte"] == caso or (a["a_tipo"] == "CASO" and a["a_valor"] == caso)
                             or (a["b_tipo"] == "CASO" and a["b_valor"] == caso)):
                continue
            chave = (a["a_tipo"], a["a_valor"], a["b_tipo"], a["b_valor"], a["relacao"])
            if chave not in vistas:
                vistas.add(chave)
                arestas.append(a)
                if len(arestas) >= 400:
                    return arestas
    return arestas


@bp_consulta.get("/api/grafo")
@requer("pesquisa")
def api_grafo():
    caso = request.args.get("caso") or ""
    termo = (request.args.get("q") or "").strip()
    ordens = _ordens_servico_grafo()
    casos_disp = [c["id"] for c in ordens]
    vazio = {"nos": [], "arestas": [], "casos": casos_disp, "ordens_servico": ordens,
             "indice_disponivel": False}
    try:
        manuais, ids_manuais = _manuais_grafo(caso, termo)
    except (OSError, ValueError):
        return jsonify({"erro":"Não foi possível ler a fonte de vínculos manuais. Preserve os arquivos e confira a integridade."}),503
    try:
        db = R.conectar()
    except (OSError, sqlite3.Error):
        return _grafo_sem_indice(vazio, manuais)
    try:
        db.execute("SELECT 1 FROM arestas LIMIT 1")
        db.execute("SELECT 1 FROM rotulos LIMIT 1")
    except sqlite3.OperationalError:
        db.close()
        return _grafo_sem_indice(vazio, manuais)

    arestas = []
    if termo:
        arestas = _arestas_busca_grafo(db, termo, caso)
    elif caso:
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

    else:
        rows = db.execute("""
            SELECT DISTINCT a_tipo, a_valor, b_tipo, b_valor, relacao, origem, fonte, localizador
            FROM arestas
            WHERE relacao != 'consta nos autos'
            ORDER BY (CASE WHEN origem='manual' THEN 0 WHEN relacao LIKE '%transferiu%' THEN 1 WHEN a_tipo='PESSOA' OR b_tipo='PESSOA' THEN 2 ELSE 3 END)
            LIMIT 400
        """).fetchall()
        arestas = [dict(zip(("a_tipo", "a_valor", "b_tipo", "b_valor", "relacao", "origem", "fonte", "localizador"), r)) for r in rows]

    # O índice é cache: a fonte autoritativa prevalece, inclusive após exclusões.
    filtradas = []
    for a in arestas:
        if a["origem"] == "manual":
            try:
                meta = json.loads(a["localizador"])
            except (TypeError, ValueError):
                meta = {}
            if isinstance(meta,dict) and meta.get("id") in ids_manuais:
                continue
        filtradas.append(a)
    arestas = filtradas + manuais
    unicas = []
    vistos_arestas = set()
    vistos_nos = set()
    for a in arestas:
        if a["origem"] == "manual" and "evidencia" not in a:
            a["caso"] = a["fonte"]
            try:
                meta = json.loads(a["localizador"])
            except (TypeError, ValueError):
                meta = {}
            if isinstance(meta, dict) and meta.get("schema") == "astra-manual/1":
                a["evidencia"] = meta.get("evidencia") or {}
                e = a["evidencia"]
                a["localizador"] = " · ".join(str(v) for v in (e.get("documento"), f"pág. {e['pagina']}" if e.get("pagina") else "", f"fls. {e['fls']}" if e.get("fls") else "", e.get("observacao")) if v)
        chave_a = (a["a_tipo"], a["a_valor"], a["b_tipo"], a["b_valor"], a["relacao"], a.get("id"))
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
    for a in manuais:
        for lado in ("a", "b"):
            if a.get(f"{lado}_rotulo"):
                rot[a[f"{lado}_tipo"],a[f"{lado}_valor"]] = a[f"{lado}_rotulo"]

    db.close()
    nos_saida = [{"tipo": t, "valor": v, "nivel": 0, "rotulo": rot.get((t, v), v)} for t, v in vistos_nos]
    g = {"nos": nos_saida, "arestas": unicas, "casos": casos_disp, "ordens_servico": ordens,
         "indice_disponivel": True}
    auditar("grafo_consultado", f"caso={caso}; q={termo}")
    return jsonify(g)


@bp_consulta.post("/api/grafo/vinculo")
@requer("trabalho")
def api_grafo_adicionar_vinculo():
    dados = request.get_json(force=True) or {}
    if not isinstance(dados, dict):
        return jsonify({"erro": "Informe os campos do vínculo."}), 400
    def texto(chave, alias=None):
        valor = dados.get(chave, dados.get(alias, "") if alias else "")
        if not isinstance(valor, str) or len(valor) > 4000:
            raise ValueError("Campo textual inválido ou muito longo.")
        if alias and chave in dados and alias in dados and dados[chave] != dados[alias]:
            raise ValueError("Campos atual e legado divergem; confira os dados.")
        return valor.strip()
    try:
        a_tipo, b_tipo = texto("a_tipo").upper(), texto("b_tipo").upper()
        a_valor, b_valor = texto("a_valor"), texto("b_valor")
        relacao, caso = texto("relacao"), texto("caso", "caso_id")
        evidencia = {"documento": texto("documento", "fonte"), "pagina": dados.get("pagina"),
                     "fls": texto("fls"), "observacao": texto("observacao", "obs")}
        pagina = evidencia["pagina"]
        if pagina is not None and (type(pagina) is not int or pagina < 1):
            raise ValueError("Página deve ser um número inteiro positivo.")
        for tipo, valor in ((a_tipo,a_valor),(b_tipo,b_valor)):
            if tipo not in R.TIPOS_NO or (tipo == "PESSOA" and not valor.startswith("P:")):
                raise ValueError("Use um identificador de registro para Pessoa; para nome sem identidade confirmada, selecione Nome candidato.")
        a_valor, b_valor = R.chave_no(a_tipo,a_valor), R.chave_no(b_tipo,b_valor)
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400

    if not (a_valor and b_valor and relacao and caso):
        return jsonify({"erro": "Informe origem, destino, relação e O.S. associada."}), 400
    try:
        existente = os.path.isfile(os.path.join(C.caminho(caso), "caso.json"))
    except ValueError:
        existente = False
    if not existente:
        return jsonify({"erro": "O.S. não localizada no cadastro."}), 404
    import vinculos_manuais as VM
    # Capture a projeção legada antes de criar a nova fonte; falha de cache não impede salvar.
    db = None
    try:
        db = R.conectar()
    except (OSError, sqlite3.Error):
        pass
    if db is not None:
        try:
            db.execute("BEGIN IMMEDIATE")
            VM.migrar_legados(WS, db)
            db.commit()
        except (OSError, sqlite3.Error, ValueError):
            db.rollback()
            return jsonify({"erro":"Não foi possível preservar integralmente os vínculos anteriores. Nenhum vínculo novo foi salvo. Tente novamente; os dados anteriores foram mantidos."}),503
        finally:
            db.close()
    try:
        registro = VM.criar(WS, {"a_tipo":a_tipo,"a_valor":a_valor,"b_tipo":b_tipo,"b_valor":b_valor,
                                "relacao":relacao,"caso":caso,"evidencia":evidencia,
                                "a_rotulo":texto("a_rotulo"),"b_rotulo":texto("b_rotulo")}, request.usuario["login"])
    except VM.Conflito:
        return jsonify({"erro":"Este vínculo com esta fonte já foi registrado ou sofreu alteração concorrente."}),409
    except ValueError as e:
        return jsonify({"erro":str(e)}),400
    except OSError:
        return jsonify({"erro":"Falha ao salvar vínculo; tente novamente sem fechar o formulário."}),503
    pendente = _projetar_manuais()
    auditar("grafo_vinculo_criado", f"id={registro['id']}; caso={caso}")
    return jsonify({"ok":True,"id":registro["id"],"versao":registro["versao"],"indexacao_pendente":pendente,
                    "aviso":"Vínculo salvo. Índice pendente de atualização." if pendente else ""})


def _projetar_manuais():
    import vinculos_manuais as VM
    db = None
    try:
        db = R.conectar()
        db.execute("BEGIN IMMEDIATE")
        VM.projetar(WS, db)
        db.commit()
        return False
    except (OSError, sqlite3.Error, ValueError):
        if db is not None: db.rollback()
        return True
    finally:
        if db is not None: db.close()


@bp_consulta.post("/api/grafo/vinculo/remover")
@requer("trabalho")
def api_grafo_remover_vinculo():
    dados = request.get_json(force=True, silent=True)
    if not isinstance(dados, dict) or set(dados) != {"id", "caso", "versao"}:
        return jsonify({"erro": "Informe somente ID, O.S. e versão do vínculo manual."}), 400
    id_, caso, versao = dados["id"], dados["caso"], dados["versao"]
    if (not isinstance(id_, str) or not re.fullmatch(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", id_)
            or not isinstance(caso, str) or not caso or len(caso) > 4000
            or type(versao) is not int or versao < 1):
        return jsonify({"erro": "ID, O.S. ou versão inválidos."}), 400
    try:
        caminho = C.caminho(caso)
    except ValueError:
        return jsonify({"erro": "ID da O.S. inválido."}), 400
    if not os.path.isfile(os.path.join(caminho, "caso.json")):
        return jsonify({"erro": "Vínculo manual não localizado nesta O.S."}), 404
    import vinculos_manuais as VM
    try:
        registro = next((r for r in VM.listar(WS, incluir_excluidos=True)
                         if r["id"] == id_ and r["caso"] == caso), None)
    except (OSError, ValueError):
        return jsonify({"erro": "Não foi possível conferir a fonte dos vínculos. Nenhum vínculo foi excluído."}), 503
    if registro is None:
        return jsonify({"erro": "Vínculo manual não localizado nesta O.S."}), 404
    if registro["excluido"] or registro["versao"] != versao:
        return jsonify({"erro": "Vínculo já excluído ou alterado. Atualize o grafo antes de tentar novamente."}), 409
    try:
        excluido = VM.excluir(WS, id_, request.usuario["login"], versao=versao)
    except VM.Conflito:
        return jsonify({"erro": "Vínculo já excluído ou alterado. Atualize o grafo antes de tentar novamente."}), 409
    except KeyError:
        return jsonify({"erro": "Vínculo manual não localizado nesta O.S."}), 404
    except (OSError, ValueError):
        return jsonify({"erro": "Falha ao preservar a exclusão. Tente novamente; os dados anteriores foram mantidos."}), 503
    pendente = _projetar_manuais()
    auditar("grafo_vinculo_removido", f"id={id_}; caso={caso}")
    return jsonify({"ok": True, "id": id_, "versao": excluido["versao"],
                    "indexacao_pendente": pendente,
                    "aviso": "Vínculo excluído. Índice pendente de atualização." if pendente else ""})



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

