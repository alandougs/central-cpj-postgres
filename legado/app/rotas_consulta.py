from servidor import *
from flask import jsonify, request, abort, send_file, session, send_from_directory
import os, json, re, time, datetime, threading, shutil, subprocess, tempfile

# ================================================================== bases de consulta, referências e pesquisa
@app.get("/api/consulta/bases")
@requer("dados")
def api_bases(): return jsonify(Q.listar())


@app.post("/api/consulta/importar")
@requer("dados")
def api_bases_importar():
    try: p, nome = salvar_upload("arquivo", Q.FORMATOS)
    except ValueError as e: return jsonify({"erro": str(e)}), 400
    rotulo = (request.form.get("nome") or os.path.splitext(nome)[0]).strip()
    tid = tarefas.nova("consulta", f"Base de consulta: {rotulo}", request.usuario["login"])
    tarefas.rodar(tid, tarefas.importar_consulta, p, rotulo); auditar("base_consulta_importada", rotulo); return jsonify({"tarefa": tid})


@app.post("/api/consulta/colar")
@requer("dados")
def api_bases_colar():
    d = request.get_json(force=True) or {}
    texto = (d.get("texto") or "").strip()
    if not texto: return jsonify({"erro": "Cole o texto a importar."}), 400
    if len(texto) > 2_000_000: return jsonify({"erro": "Texto grande demais; envie como arquivo."}), 400
    rotulo = (d.get("nome") or "Texto colado").strip()
    dest = os.path.join(WS, "exportacoes", "_recebidos"); os.makedirs(dest, exist_ok=True)
    p = os.path.join(dest, f"{time.time_ns()}-colado.txt"); open(p, "w", encoding="utf-8").write(texto)
    tid = tarefas.nova("consulta", f"Base de consulta (texto colado): {rotulo}", request.usuario["login"])
    tarefas.rodar(tid, tarefas.importar_consulta, p, rotulo); auditar("base_consulta_colada", rotulo); return jsonify({"tarefa": tid})


@app.get("/api/vinculos")
@requer("pesquisa")
def api_vinculos():
    tipo, valor = request.args.get("tipo") or "PESSOA", request.args.get("valor") or ""
    try: niveis = max(1, min(3, int(request.args.get("niveis") or 2)))
    except ValueError: niveis = 2
    try: g = R.vinculos(tipo, valor, niveis)
    except FileNotFoundError: g = {"nos": [], "arestas": []}
    auditar("pesquisa_vinculos", f"{tipo}: {valor[:80]}"); return jsonify(g)


@app.post("/api/consulta/bases/<bid>/remover")
@requer("dados")
def api_bases_remover(bid):
    try: Q.remover(bid)
    except FileNotFoundError: abort(404)
    threading.Thread(target=tarefas.indexar, daemon=True).start(); auditar("base_consulta_removida", bid); return jsonify({"ok": True})


@app.get("/api/referencias")
@requer("dados")
def api_refs(): return jsonify(RF.listar(request.args.get("autor") or None))


@app.post("/api/referencias/importar")
@requer("dados")
def api_refs_importar():
    try: p, nome = salvar_upload("arquivo", (".docx", ".pdf", ".md"))
    except ValueError as e: return jsonify({"erro": str(e)}), 400
    f = request.form
    if not (f.get("autor") or "").strip(): return jsonify({"erro": "Informe o autor."}), 400
    dados = {k: f.get(k) for k in ("autor", "modalidade", "natureza", "peso", "obs")} | {"enviado_por": request.usuario["login"]}
    tid = tarefas.nova("referencia", f"Referência: {nome} ({dados['autor']})", request.usuario["login"])
    tarefas.rodar(tid, tarefas.importar_referencia, p, dados); auditar("referencia_importada", f"{nome} — {dados['autor']}")
    return jsonify({"tarefa": tid})


@app.post("/api/referencias/<rid>")
@requer("dados")
def api_refs_atualizar(rid):
    d = request.get_json(force=True) or {}
    try: m = RF.atualizar(rid, **{k: d.get(k) for k in ("autor", "modalidade", "natureza", "peso", "obs")})
    except FileNotFoundError: abort(404)
    threading.Thread(target=tarefas.indexar, daemon=True).start(); auditar("referencia_atualizada", rid); return jsonify(m)


@app.post("/api/referencias/<rid>/remover")
@requer("dados")
def api_refs_remover(rid):
    try: RF.remover(rid)
    except FileNotFoundError: abort(404)
    threading.Thread(target=tarefas.indexar, daemon=True).start(); auditar("referencia_removida", rid); return jsonify({"ok": True})


@app.get("/api/pesquisa/pessoas")
@requer("pesquisa")
def api_pesquisa_pessoas():
    f = {k: request.args.get(k) for k in ("nome", "mae", "pai", "cpf", "rg", "telefone", "cnpj", "empresa", "endereco", "texto",
                                          "processo", "bo", "placa", "mandado", "cautelar", "mandado_estado", "cautelar_estado")}
    try: ps, oc = R.pesquisa_relacional(f, origem=request.args.get("origem") or None)
    except FileNotFoundError: return jsonify({"pessoas": [], "ocorrencias": [], "aviso": "Base ainda vazia."})
    except ValueError as e: return jsonify({"erro": str(e)}), 400
    auditar("pesquisa_pessoas", json.dumps({k: v for k, v in f.items() if v}, ensure_ascii=False)[:300])
    return jsonify({"pessoas": ps, "ocorrencias": oc, "aviso": None if ps or oc else "Nenhum resultado."})


@app.get("/api/busca")
@requer("pesquisa")
def api_busca():
    q = (request.args.get("q") or "").strip()
    if not q: return jsonify({"trechos": [], "entidades": [], "aviso": None})
    try:
        tipo = request.args.get("tipo") or None
        trechos, aviso = R.buscar(q, caso=request.args.get("caso") or None, tipo=tipo, n=int(request.args.get("n") or 25))
        ents = R.entidade(q) if (len(re.sub(r"\D", "", q)) >= 6 or "@" in q or re.fullmatch(r"[A-Za-z]{3}-?\d[A-Za-z0-9]\d{2}", q)) else []
        auditar("pesquisa_texto", q[:200]); return jsonify({"trechos": trechos, "entidades": ents, "aviso": aviso})
    except FileNotFoundError:
        return jsonify({"trechos": [], "entidades": [], "aviso": "Índice ainda não criado — processe um caso primeiro."})
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400


@app.get("/api/cruzar/<id_>")
@requer("trabalho")
def api_cruzar(id_):
    try: return jsonify(R.cruzar(id_))
    except FileNotFoundError: return jsonify([])


def assinatura_painel():
    """Somente metadados das fontes dos indicadores; não lê PDFs nem recalcula hashes."""
    arquivos = [os.path.join(WS, "producao", "config.json"),
                os.path.join(S_BASE, "indexar.py"), os.path.join(S_BASE, "gerar_painel.py")]
    if os.path.isdir(C.CASOS):
        for nome in sorted(os.listdir(C.CASOS)):
            if nome.startswith("_"): continue
            caso = os.path.join(C.CASOS, nome, "caso.json")
            if not os.path.isfile(caso): continue
            arquivos.append(caso)
            rels = os.path.join(C.CASOS, nome, "03-relatorios")
            if os.path.isdir(rels):
                arquivos.extend(os.path.join(rels, f) for f in sorted(os.listdir(rels))
                                if not f.startswith("~$") and "final" in f.lower()
                                and f.lower().endswith((".md", ".pdf", ".docx")))
    return (WS, datetime.date.today().isoformat(),
            tuple((p, assinatura_arquivo(p)) for p in arquivos))


def atualizar_painel(chave):
    """Reconstrói uma vez por mudança, fora do request, e publica o HTML atomicamente."""
    try:
        env = ambiente_ocr()
        subprocess.run([PY, os.path.join(S_BASE, "indexar.py")], env=env, capture_output=True,
                       check=True, timeout=300, creationflags=SEM_JANELA)
        prod = os.path.join(WS, "producao")
        os.makedirs(prod, exist_ok=True)
        # O gerador lê o snapshot e escreve fora do arquivo que está sendo servido.
        with tempfile.TemporaryDirectory(prefix=".painel-", dir=prod) as stage:
            out = os.path.join(stage, "producao"); os.makedirs(out)
            shutil.copyfile(os.path.join(prod, "base.json"), os.path.join(out, "base.json"))
            cfg = os.path.join(prod, "config.json")
            if os.path.isfile(cfg): shutil.copyfile(cfg, os.path.join(out, "config.json"))
            subprocess.run([PY, os.path.join(S_BASE, "gerar_painel.py")],
                           env=dict(env, CPJ_WORKSPACE=stage), capture_output=True,
                           check=True, timeout=90, creationflags=SEM_JANELA)
            os.replace(os.path.join(out, "painel.html"), os.path.join(prod, "painel.html"))
        with _painel_trava:
            _painel_cache.update(chave=chave, erro=False, retentar_apos=0)
    except Exception:
        app.logger.exception("Falha ao atualizar painel de produção")
        with _painel_trava:
            _painel_cache.update(erro=True, retentar_apos=time.monotonic() + 30)
    finally:
        with _painel_trava: _painel_cache["gerando"] = False


@app.get("/painel")
@requer("estatisticas")
def painel():
    chave = assinatura_painel()
    p = os.path.join(WS, "producao", "painel.html")
    with _painel_trava:
        pronto = _painel_cache["chave"] == chave and os.path.isfile(p)
        if not pronto and not _painel_cache["gerando"] and time.monotonic() >= _painel_cache["retentar_apos"]:
            _painel_cache.update(gerando=True, erro=False)
            threading.Thread(target=atualizar_painel, args=(chave,), daemon=True).start()
        erro = _painel_cache["erro"]
    if pronto:
        r = send_file(p); r.headers["X-CPJ-Painel"] = "pronto"; return r
    if erro:
        return ("<p>Não foi possível atualizar as estatísticas. Tente abrir o painel novamente em alguns instantes.</p>",
                503, {"X-CPJ-Painel": "erro", "Retry-After": "30"})
    return ("<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'>"
            "<meta http-equiv='refresh' content='2'><title>Estatísticas</title></head>"
            "<body><p>Atualizando as estatísticas… O painel aparecerá automaticamente.</p></body></html>",
            200, {"X-CPJ-Painel": "atualizando", "Retry-After": "2"})


@app.get("/api/sistema")
@requer("dados")
def api_sistema():
    return jsonify({"idioma_ocr": idioma_ocr(ambiente_ocr()), "pdf_automatico": bool(soffice()), "workspace": WS})


