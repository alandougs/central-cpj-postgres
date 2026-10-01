from servidor import *
from flask import jsonify, request, abort, send_file, session, send_from_directory
import os, json, re, time, datetime, threading, shutil, subprocess, tempfile

# ================================================================== relatório: minuta, DOCX, PDF, FINAL
def ler_minuta(txt):
    meta, corpo = {}, txt
    m = re.match(r"\s*---\s*\n(.*?)\n---\s*\n(.*)", txt, flags=re.S)
    if m:
        for ln in m.group(1).splitlines():
            if ":" in ln: k, v = ln.split(":", 1); meta[k.strip()] = v.strip()
        corpo = m.group(2)
    secoes, atual = {"RESUMO DOS FATOS": [], "DILIGÊNCIAS REALIZADAS": [], "CONCLUSÃO": []}, None
    for ln in corpo.splitlines():
        t = re.match(r"^##\s+(.+?)\s*$", ln)
        if t and not ln.startswith("###"):
            nome = t.group(1).strip().upper(); atual = next((s for s in secoes if s in nome or nome in s), None); continue
        if atual: secoes[atual].append(ln)
    return meta, {k: "\n".join(v).strip() for k, v in secoes.items()}


CAMPOS_MINUTA = ["caso", "versao", "ordem_servico", "referencia", "natureza", "investigados", "vitimas", "local", "data_fatos",
                 "local_data", "data_rodape", "delegado"]


def ultima_minuta(id_):
    d = os.path.join(C.caminho(id_), "03-relatorios")
    ms = sorted((f for f in os.listdir(d) if re.match(r"minuta-v\d+\.md$", f)), key=lambda f: int(re.findall(r"\d+", f)[0])) if os.path.isdir(d) else []
    return ms[-1] if ms else None


@app.get("/api/casos/<id_>/minuta")
@requer("trabalho")
def api_minuta(id_):
    nome = request.args.get("arquivo") or ultima_minuta(id_)
    if not nome:
        c = C.carregar(id_); dp = {}
        pp = os.path.join(WS, "modelos", "dados-padrao.json")
        if os.path.exists(pp): dp = json.load(open(pp, encoding="utf-8"))
        hoje = datetime.date.today()
        meses = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
        meta = {"caso": id_, "versao": "01", "ordem_servico": c.get("ordem_servico"), "referencia": c.get("referencia"),
                "natureza": c.get("natureza"), "investigados": ", ".join(c.get("investigados") or []), "vitimas": ", ".join(c.get("vitimas") or []),
                "local": "", "data_fatos": "", "local_data": f"{dp.get('cidade_uf', 'Presidente Prudente, SP')}, {hoje.day} de {meses[hoje.month - 1]} de {hoje.year}",
                "data_rodape": hoje.strftime("%d/%m/%Y"), "delegado": dp.get("delegado_padrao") or c.get("requisitante") or ""}
        return jsonify({"arquivo": None, "meta": meta, "secoes": {"RESUMO DOS FATOS": "", "DILIGÊNCIAS REALIZADAS": "", "CONCLUSÃO": ""},
                        "ultima": None})
    p = os.path.join(C.caminho(id_), "03-relatorios", os.path.basename(nome))
    if not os.path.exists(p): abort(404)
    meta, sec = ler_minuta(open(p, encoding="utf-8").read())
    return jsonify({"arquivo": os.path.basename(nome), "meta": meta, "secoes": sec, "ultima": ultima_minuta(id_)})


@app.post("/api/casos/<id_>/minuta")
@requer("trabalho")
def api_minuta_salvar(id_):
    d = request.get_json(force=True) or {}
    rels = os.path.join(C.caminho(id_), "03-relatorios"); os.makedirs(rels, exist_ok=True)
    # 'ultima_vista': a última minuta existente quando o editor foi aberto. Se outra versão foi salva nesse meio-tempo
    # (outra pessoa ou agente de IA), avisa em vez de empilhar silenciosamente; 'forcar' salva mesmo assim como nova versão.
    if "ultima_vista" in d and not d.get("forcar") and (d.get("ultima_vista") or None) != ultima_minuta(id_):
        return jsonify({"erro": f"Outra versão ({ultima_minuta(id_)}) foi salva enquanto você editava. Salvar mesmo assim "
                                "como nova versão, ou fechar e abrir a mais recente?", "conflito": True,
                        "ultima": ultima_minuta(id_)}), 409
    meta = {k: str((d.get("meta") or {}).get(k) or "").replace("\n", " ").strip() for k in CAMPOS_MINUTA}
    sec = d.get("secoes") or {}
    with C.reservar_arquivo_versao(rels, "minuta-v") as (nome, p):   # número reservado atomicamente (O_EXCL)
        v = int(re.findall(r"\d+", nome)[0])
        meta.update(caso=id_, versao=f"{v:02d}", gerado_em=C.hoje(), editado_por=request.usuario["login"])
        txt = "---\n" + "\n".join(f"{k}: {val}" for k, val in meta.items()) + "\n---\n\n" + "\n\n".join(
            f"## {s}\n\n{(sec.get(s) or '').strip()}" for s in ("RESUMO DOS FATOS", "DILIGÊNCIAS REALIZADAS", "CONCLUSÃO")) + "\n"
        with open(p, "w", encoding="utf-8") as f: f.write(txt)
    with C.trava(id_):
        if C.carregar(id_)["status"] in ("recebido", "extraido", "em_analise", "analisado"): C.status(id_, "minuta")
    out = {"arquivo": nome}
    if d.get("gerar_docx", True):
        try: out |= gerar_docx(WS, id_, nome)
        except RuntimeError as e: out["erro_docx"] = str(e)
    auditar("minuta_salva", f"{id_}/{nome}"); return jsonify(out)


@app.post("/api/casos/<id_>/docx")
@requer("trabalho")
def api_docx(id_):
    nome = (request.get_json(silent=True) or {}).get("minuta") or ultima_minuta(id_)
    if not nome: return jsonify({"erro": "Não há minuta."}), 400
    try: out = gerar_docx(WS, id_, os.path.basename(nome))
    except RuntimeError as e: return jsonify({"erro": str(e)}), 400
    auditar("docx_gerado", f"{id_}/{out['docx']}"); return jsonify(out)


@app.post("/api/casos/<id_>/pdf")
@requer("trabalho")
def api_pdf(id_):
    nome = os.path.basename((request.get_json(silent=True) or {}).get("docx") or "")
    if not nome.endswith(".docx"): return jsonify({"erro": "Informe o DOCX."}), 400
    try: out = gerar_pdf(WS, id_, nome)
    except RuntimeError as e: return jsonify({"erro": str(e)}), 400
    auditar("pdf_gerado", f"{id_}/{out['pdf']}"); return jsonify(out)


@app.post("/api/casos/<id_>/final")
@requer("trabalho")
def api_final(id_):
    """Define um DOCX como relatório FINAL (gera também o .md para calibração/RAG) e dá baixa."""
    nome = os.path.basename((request.get_json(silent=True) or {}).get("docx") or "")
    d = os.path.join(C.caminho(id_), "03-relatorios"); p = os.path.join(d, nome)
    if not nome.endswith(".docx") or not os.path.exists(p): return jsonify({"erro": "DOCX não encontrado."}), 400
    final = os.path.join(d, f"RELATORIO-{id_}-FINAL.docx"); shutil.copyfile(p, final)
    try:
        texto = RF.extrair_texto(final); c = C.carregar(id_)
        open(os.path.join(d, f"RELATORIO-{id_}-FINAL.md"), "w", encoding="utf-8").write(
            f"---\ncaso: {id_}\ntipo: relatorio-final\nmodalidade: {c.get('modalidade') or ''}\norigem_docx: {nome}\n---\n\n{texto}")
    except Exception: pass
    c = C.status(id_, "entregue", origem="central", arquivo=os.path.basename(final))
    versoes = len([f for f in os.listdir(d) if re.match(r"minuta-v\d+\.md$", f)])
    C.registrar_relatorio(id_, os.path.basename(final), data=c["datas"]["entregue"], versoes=versoes or None)
    criador = c.get("criado_por")
    if criador and auth.obter(criador):
        shutil.copyfile(final, os.path.join(pasta_usuario(criador), "relatorios", f"RELATORIO-{id_}-FINAL.docx"))
    auditar("relatorio_final", f"{id_}/{nome}"); threading.Thread(target=tarefas.indexar, daemon=True).start()
    return jsonify({"ok": True, "final": os.path.basename(final)})


