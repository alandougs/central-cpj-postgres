#!/usr/bin/env python3
"""Rotas do sistema: página inicial, IA, agentes de plantão, tarefas, importação/exportação e painel."""
import json
import os
import re
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import datetime
from flask import Blueprint, abort, current_app, jsonify, request, send_file, send_from_directory
from relatorio_producao import preparar, html_relatorio, csv_relatorio
import plantao as PL
from fluxo_execucao import ConflitoVersao, TransicaoInvalida
import rotas.comum as comum
from rotas.comum import (
    C,
    WS,
    _painel_cache,
    _painel_trava,
    ambiente_ocr,
    assinatura_painel,
    atualizar_painel,
    auditar,
    auth,
    eh_local,
    idioma_ocr,
    requer,
    salvar_upload,
    soffice,
    tarefas,
)

bp_sistema = Blueprint("sistema", __name__)


@bp_sistema.get("/")
def inicio():
    resp = send_from_directory(current_app.static_folder, "index.html")
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


@bp_sistema.get("/api/ia/status")
@requer("ia")
def api_ia_status():
    return jsonify(tarefas.claude_status())


@bp_sistema.post("/api/ia/login")
@requer("ia")
def api_ia_login():
    if not eh_local():
        return jsonify({"erro": "Faça o login do Claude no computador da Central."}), 403
    try:
        tarefas.claude_login()
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    return jsonify({"ok": True})


@bp_sistema.post("/api/casos/<id_>/ia")
@requer("ia")
def api_ia(id_):
    d = request.get_json(force=True) or {}
    if not isinstance(d, dict): return jsonify({"erro": "Pedido de IA inválido."}), 400
    if not C.existe(id_):
        abort(404)
    if d.get("agente") is not None and not isinstance(d["agente"], str):
        return jsonify({"erro": "Agente inválido."}), 400
    agente = (d.get("agente") or "").strip() or None
    
    import executores_llm as EL
    ag_res = agente or EL.agente_padrao(WS)
    if agente and not any(a["nome"] == agente and a["aprovado"] for a in tarefas.plantao.agentes()):
        return jsonify({"erro": f"Agente '{agente}' não existe ou não está aprovado."}), 400
    destinos = PL.destinos_externos(WS, tarefas.plantao, ag_res)
    consentimento = None
    if destinos:
        if "consentimento_externo" not in d:
            return jsonify({"requer_consentimento": True, "destinos": destinos, "escopo": "api_ia"})
        cons = d["consentimento_externo"]
        if not isinstance(cons, dict): return jsonify({"erro": "Consentimento inválido."}), 400
        if any(k in cons and not isinstance(cons[k], bool) for k in ("aceito", "recusado")):
            return jsonify({"erro": "Consentimento inválido."}), 400
        if cons.get("recusado") is True or cons.get("aceito") is False:
            auditar("consentimento_recusado", f"{id_}: recusa para api_ia")
            comum.registrar_tratamento(id_, [f"- Consentimento externo: Usuário recusou envio para nuvem em {comum.agora()}."])
            return jsonify({"ok": True, "mensagem": "Envio recusado pelo usuário."})
        aceitos = cons.get("destinos")
        if (cons.get("aceito") is not True or cons.get("escopo", "api_ia") != "api_ia" or not isinstance(aceitos, list) or not aceitos or
            not all(isinstance(x, str) and x in destinos for x in aceitos)):
            return jsonify({"erro": "Informe consentimento válido para os destinos apresentados."}), 400
        consentimento = EL.criar_consentimento(request.usuario["login"], aceitos)
    try:
        tid = tarefas.enfileirar_ia(id_, d.get("acao"), request.usuario["login"], d.get("observacoes") or "", ag_res,
                                  consentimento=json.dumps(consentimento) if consentimento else None)
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    except RuntimeError as e:
        return jsonify({"erro": str(e)}), 503
    if consentimento:
        auditar("consentimento_aceito", f"{id_}: aceite para {consentimento['destinos']}")
        comum.registrar_tratamento(id_, [f"- Consentimento externo: Usuário {consentimento['usuario']} autorizou envio para {consentimento['destinos']} em {consentimento['data_hora']}."])
    auditar("ia_acionada", f"{id_}: {d.get('acao')}" + (f" -> {agente}" if agente else ""))
    return jsonify({"tarefa": tid, "execucao_id": tarefas.plantao.execucao_id(tid)})


@bp_sistema.post("/api/casos/<id_>/transcricao-visual")
@requer("ia")
def api_transcricao_visual(id_):
    if not auth.pode(request.usuario["perfil"], "casos"): abort(403)
    try: C.carregar(id_)
    except (ValueError, FileNotFoundError): abort(404)
    d = request.get_json(force=True) or {}
    if not isinstance(d, dict) or set(d) - {"consentimento_externo"}:
        return jsonify({"erro": "Pedido inválido; páginas são selecionadas pelo diagnóstico local."}), 400
    import executores_llm as EL
    try: plano = comum.plano_transcricao_visual(id_)
    except (ValueError, OSError) as e: return jsonify({"erro": str(e)}), 400
    if not plano: return jsonify({"erro": "Nenhuma página indicada para transcrição visual."}), 400
    destinos = [p for p, _ in EL.provedores_api_configurados(WS) if "vision" in EL.CAPACIDADES_PROVEDOR.get(p, set())]
    if not destinos: return jsonify({"erro": "Ative um provedor com modelo de visão em Sistema → Provedores e modelos de IA."}), 400
    if "consentimento_externo" not in d:
        return jsonify({"requer_consentimento": True, "destinos": destinos, "escopo": "transcricao_visual",
                        "paginas": sum(len(x["paginas"]) for x in plano)})
    c = d["consentimento_externo"]
    if not isinstance(c, dict) or any(k in c and not isinstance(c[k], bool) for k in ("aceito", "recusado")):
        return jsonify({"erro": "Consentimento inválido."}), 400
    if c.get("recusado") is True or c.get("aceito") is False:
        auditar("consentimento_recusado", f"{id_}: transcricao_visual")
        comum.registrar_tratamento(id_, [f"- Transcrição visual: envio externo recusado em {comum.agora()}."])
        return jsonify({"ok": True, "mensagem": "Envio recusado pelo usuário."})
    aceitos = c.get("destinos")
    if c.get("aceito") is not True or c.get("escopo", "transcricao_visual") != "transcricao_visual" or not isinstance(aceitos, list) or not aceitos or not all(isinstance(p, str) and p in destinos for p in aceitos):
        return jsonify({"erro": "Confirme os destinos apresentados para transcrição visual."}), 400
    cons = EL.criar_consentimento(request.usuario["login"], aceitos, escopo="transcricao_visual")
    tid = tarefas.nova("ia", "Transcrição visual de páginas a conferir", request.usuario["login"], caso=id_, consentimento=cons)
    auditar("consentimento_aceito", f"{id_}: transcricao_visual; destinos {cons['destinos']}")
    comum.registrar_tratamento(id_, [f"- Consentimento externo: {cons['usuario']} autorizou transcrição visual para {cons['destinos']} em {cons['data_hora']}."])
    tarefas.rodar(tid, comum.transcricao_visual, id_, plano, cons)
    return jsonify({"tarefa": tid})


@bp_sistema.get("/api/plantao/agentes")
@requer("ia")
def api_plantao_agentes():
    ags = tarefas.plantao.agentes()
    campos = ("nome", "tipo", "modo", "estado", "aprovado", "job", "detalhe", "silencio_s", "host", "visto_em")
    locais = [{"tipo": x["tipo"], "disponivel": True, "motivo": "CLI instalado; o agente confirma o login"}
              for x in PL.executaveis_locais()]
    return jsonify({
        "agentes": [{k: a.get(k) for k in campos} for a in ags],
        "executaveis_locais": locais,
        "ociosos": sum(1 for a in ags if a["estado"] == "ocioso"),
        "ocupados": sum(1 for a in ags if a["estado"] == "ocupado"),
        "pendentes": sum(1 for p in tarefas.plantao.pedidos() if p["estado"] == "pendente"),
    })


@bp_sistema.post("/api/plantao/agentes/<nome>/aprovacao")
@requer("usuarios")
def api_plantao_aprovacao(nome):
    aprovar = bool((request.get_json(silent=True) or {}).get("aprovar"))
    try:
        tarefas.plantao.aprovar(nome, aprovar)
    except ValueError as e:
        return jsonify({"erro": str(e)}), 404
    auditar("agente_aprovado" if aprovar else "agente_revogado", nome)
    return jsonify({"ok": True})


@bp_sistema.get("/api/tarefas")
@requer()
def api_tarefas():
    u = request.usuario
    return jsonify(tarefas.listar(u["login"], todas=auth.pode(u["perfil"], "trabalho")))


@bp_sistema.post("/api/tarefas/<tid>/cancelar")
@requer()
def api_tarefa_cancelar(tid):
    t = tarefas.obter(tid)
    u = request.usuario
    if not t:
        abort(404)
    if t["usuario"] != u["login"] and not auth.pode(u["perfil"], "trabalho"):
        abort(403)
    ok = tarefas.cancelar(tid)
    auditar("tarefa_cancelada", t["titulo"])
    return jsonify({"ok": ok})


# ------------------------------------------------------------------ fluxos por O.S. (contrato cpj-fluxos/1)
SCHEMA_FLUXOS = "cpj-fluxos/1"
_ID_FLUXO = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
_LIMITE_TEXTO = 300


def _param_inteiro(nome, padrao, minimo, maximo):
    bruto = request.args.get(nome)
    if bruto is None or bruto == "":
        return padrao
    if not re.fullmatch(r"[0-9]{1,6}", bruto) or not minimo <= int(bruto) <= maximo:
        raise ValueError(f"{nome} deve ser um inteiro entre {minimo} e {maximo}.")
    return int(bruto)


def _texto_operacional(valor, pode):
    """Texto de erro/diagnóstico só para quem trabalha nos casos; os demais veem apenas o tipo da pendência."""
    return str(valor or "")[:_LIMITE_TEXTO] if pode else ""


def _pendencia(p, pode):
    out = {"tipo": p.get("tipo"), "etapa": p.get("etapa"), "documento": p.get("documento"),
           "detalhe": _texto_operacional(p.get("detalhe"), pode), "execucao_id": p.get("execucao_id")}
    if pode:
        out["etapa_id"] = p.get("etapa_id")
        out["etapa_versao"] = p.get("etapa_versao")
    return out


def _item_fluxo(i, u, pode):
    acoes = [{"acao": "cancelar", "execucao_id": ex["execucao_id"], "versao": ex["versao"]}
             for ex in i["execucoes"] if pode or ex["solicitante"] == u["login"]]
    if pode:
        acoes += [{"acao": "reconciliar", "execucao_id": p["execucao_id"], "etapa_id": p["etapa_id"], "versao": p["etapa_versao"]}
                  for p in i["pendencias"] if p["tipo"] == "aguardando_operador" and p.get("etapa_id")]
    progresso = i["progresso"]
    return {"caso": i["caso"], "execucao_id": i["execucao_id"], "versao": i["versao"], "estado": i["estado"],
            "etapa": i["etapa"], "progresso": progresso if isinstance(progresso, (int, float)) and 0 <= progresso <= 100 else None,
            "atualizado_em": i["atualizado_em"], "pendencias": [_pendencia(p, pode) for p in i["pendencias"]],
            "documentos": i["documentos"], "acoes": acoes}


def _execucao_autorizada(execucao_id):
    """400 para identificador malformado; 404 para inexistente ou de O.S. fora da lista autorizada (sem distinguir)."""
    if not isinstance(execucao_id, str) or not _ID_FLUXO.fullmatch(execucao_id):
        abort(400)
    exe = comum.fluxos().obter(execucao_id)
    if exe is None or exe["caso"] not in {c["id"] for c in comum.visiveis(request.usuario)}:
        abort(404)
    return exe


@bp_sistema.get("/api/fluxos")
@requer("casos")
def api_fluxos():
    u = request.usuario
    try:
        limite = _param_inteiro("limite", 50, 1, 100)
        bruto = request.args.get("estado")
        estados = [x for x in bruto.split(",") if x] if bruto else None
        cursor = request.args.get("cursor") or None
        if cursor is not None and len(cursor) > 200:
            raise ValueError("Cursor inválido.")
        pagina = comum.fluxos().listar([c["id"] for c in comum.visiveis(u)], limite, cursor, estados)
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    pode = auth.pode(u["perfil"], "trabalho")
    resp = jsonify({"schema": SCHEMA_FLUXOS, "itens": [_item_fluxo(i, u, pode) for i in pagina["itens"]],
                    "proximo_cursor": pagina["proximo_cursor"]})
    resp.headers["Cache-Control"] = "no-store"
    return resp


@bp_sistema.get("/api/fluxos/<execucao_id>")
@requer("casos")
def api_fluxo(execucao_id):
    _execucao_autorizada(execucao_id)
    u = request.usuario
    pode = auth.pode(u["perfil"], "trabalho")
    try:
        pagina = comum.fluxos().etapas_paginadas(execucao_id, _param_inteiro("limite", 50, 1, 100), request.args.get("cursor") or None)
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    if pagina is None:
        abort(404)
    ex = pagina["execucao"]
    etapas = [{"id": e["id"], "etapa": e["etapa"], "documento": e["documento"], "estado": e["estado"], "versao": e["versao"],
               "progresso": e["progresso"], "tentativa": e["tentativa"], "anterior_id": e["anterior_id"], "origem": e["origem"],
               "detalhe": _texto_operacional(e["detalhe"], pode), "criado_em": e["criado_em"], "atualizado_em": e["atualizado_em"]}
              for e in pagina["etapas"]]
    resp = jsonify({"schema": SCHEMA_FLUXOS, "execucao": {
        "execucao_id": ex["id"], "caso": ex["caso"], "versao": ex["versao"], "estado": ex["estado"], "etapa": ex["etapa"],
        "atualizado_em": ex["atualizado_em"], "documentos": ex["documentos"],
        "pendencias": [_pendencia(p, pode) for p in ex["pendencias"]]}, "etapas": etapas, "proximo_cursor": pagina["proximo_cursor"]})
    resp.headers["Cache-Control"] = "no-store"
    return resp


def _versao_do_corpo():
    corpo = request.get_json(silent=True)
    if not isinstance(corpo, dict):
        return None
    versao = corpo.get("versao")
    if type(versao) is not int or versao < 1:
        return None
    return versao


@bp_sistema.post("/api/fluxos/<execucao_id>/cancelar")
@requer()
def api_fluxo_cancelar(execucao_id):
    exe = _execucao_autorizada(execucao_id)
    u = request.usuario
    if not (auth.pode(u["perfil"], "trabalho") or exe["solicitante"] == u["login"]):
        abort(403)
    versao = _versao_do_corpo()
    if versao is None:
        return jsonify({"erro": "Informe a versão (inteira) da execução exibida."}), 400
    fx = comum.fluxos()
    try:
        res = fx.cancelar_execucao(execucao_id, versao, "cancelamento pelo painel")
    except ConflitoVersao:
        atual = fx.obter(execucao_id)
        return jsonify({"erro": "A execução mudou desde a última atualização. Confira o estado atual e tente de novo.",
                        "versao_atual": atual["versao"] if atual else None}), 409
    for e in res["etapas_canceladas"]:       # extração ainda na fila não deve ser processada depois
        if e["origem"] == "processamento" and e["estado_anterior"] == "na_fila":
            partes = e["origem_id"].split("|")
            if len(partes) >= 3:
                comum.atualizar_trabalho(partes[0], partes[1], status="cancelado", etapa="cancelado pelo painel de fluxos",
                                         fim=comum.agora())
    auditar("fluxo_cancelado", f"{exe['caso']}: {execucao_id}")
    return jsonify({"ok": True, "canceladas": res["canceladas"], "preservadas": res["preservadas"]})


@bp_sistema.post("/api/fluxos/<execucao_id>/etapas/<etapa_id>/reconciliar")
@requer("trabalho")
def api_fluxo_reconciliar(execucao_id, etapa_id):
    """Ação do operador sobre etapa `aguardando_operador`: só registra o que ele conferiu; não dispara nova chamada."""
    exe = _execucao_autorizada(execucao_id)
    if not isinstance(etapa_id, str) or not _ID_FLUXO.fullmatch(etapa_id):
        abort(400)
    etapa = next((e for e in exe["etapas"] if e["id"] == etapa_id), None)
    if etapa is None:
        abort(404)
    d = request.get_json(silent=True)
    if not isinstance(d, dict):
        return jsonify({"erro": "Informe um objeto JSON com versão, estado e motivo."}), 400
    versao, estado, motivo = d.get("versao"), d.get("estado"), d.get("motivo")
    if type(versao) is not int or versao < 1 or estado not in ("na_fila", "cancelada") \
            or not isinstance(motivo, str) or not 3 <= len(motivo.strip()) <= _LIMITE_TEXTO:
        return jsonify({"erro": "Informe versão, estado (na_fila ou cancelada) e o motivo conferido (3 a 300 caracteres)."}), 400
    try:
        nova = comum.fluxos().reconciliar(etapa_id, versao, estado, motivo.strip())
    except (ConflitoVersao, TransicaoInvalida) as e:
        return jsonify({"erro": str(e), "versao_atual": etapa["versao"]}), 409
    auditar("fluxo_reconciliado", f"{exe['caso']}: {etapa_id} -> {estado}")
    return jsonify({"ok": True, "estado": nova["estado"], "versao": nova["versao"]})


@bp_sistema.post("/api/exportar")
@requer("dados")
def api_exportar():
    d = request.get_json(force=True) or {}
    modo = "completo" if d.get("modo") == "completo" else "dados"
    tid = tarefas.nova("exportacao", f"Exportação ({modo})", request.usuario["login"])
    tarefas.rodar(tid, tarefas.exportar, modo, bool(d.get("incluir_modelo")))
    auditar("exportacao", modo)
    return jsonify({"tarefa": tid})


@bp_sistema.get("/api/exportacoes")
@requer("dados")
def api_exportacoes():
    d = os.path.join(WS, "exportacoes")
    fs = sorted((f for f in os.listdir(d) if f.endswith(".zip")), reverse=True) if os.path.isdir(d) else []
    return jsonify([
        {"arquivo": f, "mb": round(os.path.getsize(os.path.join(d, f)) / 1048576, 1), "url": f"/exportacoes/{f}"}
        for f in fs
    ])


@bp_sistema.get("/exportacoes/<nome>")
@requer("dados")
def api_exportacao_baixar(nome):
    p = os.path.join(WS, "exportacoes", os.path.basename(nome))
    if not os.path.isfile(p):
        abort(404)
    auditar("exportacao_baixada", nome)
    return send_file(p, as_attachment=True)


@bp_sistema.get("/api/planilha")
@requer("estatisticas")
def api_planilha():
    tarefas.indexar()
    p = os.path.join(WS, "producao", "base.csv")
    if not os.path.exists(p):
        return jsonify({"erro": "Ainda não há dados."}), 404
    auditar("planilha_baixada")
    return send_file(p, as_attachment=True, download_name=f"CPJ-producao-{C.hoje()}.csv")


@bp_sistema.get("/api/producao/relatorio")
@requer("estatisticas")
def relatorio_cumpridas():
    inicio, fim = request.args.get("inicio"), request.args.get("fim")
    formato = request.args.get("formato", "html")
    if formato not in ("html", "csv"):
        return jsonify({"erro": "Formato de relatório inválido."}), 400
    try:
        with open(os.path.join(WS, "producao", "config.json"), encoding="utf-8") as f:
            config = json.load(f)
    except (OSError, ValueError):
        config = {}
    try:
        dados = preparar(comum.visiveis(request.usuario), inicio, fim,
                         {u["login"]: u["nome"] for u in auth.listar()}, config)
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400
    auditar("relatorio_cumpridas", f"{inicio} a {fim}; {formato}; total={dados['total']}")
    if formato == "csv":
        return current_app.response_class(
            ("\ufeff" + csv_relatorio(dados)).encode("utf-8"), mimetype="text/csv",
            headers={"Content-Disposition": f'attachment; filename="OS-cumpridas-{inicio}-a-{fim}.csv"'})
    return current_app.response_class(html_relatorio(dados), mimetype="text/html")


@bp_sistema.post("/api/importar")
@requer("dados")
def api_importar():
    try:
        p, nome = salvar_upload("arquivo", (".zip",))
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    tid = tarefas.nova("importacao", f"Importação de {nome}", request.usuario["login"])
    tarefas.rodar(tid, tarefas.importar, p)
    auditar("importacao", nome)
    return jsonify({"tarefa": tid})


@bp_sistema.get("/painel")
@requer("estatisticas")
def painel():
    chave = comum.assinatura_painel()
    p = os.path.join(WS, "producao", "painel.html")
    with comum._painel_trava:
        pronto = comum._painel_cache["chave"] == chave and os.path.isfile(p)
        if not pronto and not comum._painel_cache["gerando"] and time.monotonic() >= comum._painel_cache["retentar_apos"]:
            comum._painel_cache.update(gerando=True, erro=False)
            threading.Thread(target=comum.atualizar_painel, args=(chave,), daemon=True).start()
        erro = comum._painel_cache["erro"]
    if pronto:
        r = send_file(p)
        r.headers["X-CPJ-Painel"] = "pronto"
        return r
    if erro:
        return (
            "<p>Não foi possível atualizar as estatísticas. Tente abrir o painel novamente em alguns instantes.</p>",
            503,
            {"X-CPJ-Painel": "erro", "Retry-After": "30"},
        )
    return (
        "<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'>"
        "<meta http-equiv='refresh' content='2'><title>Estatísticas</title></head>"
        "<body><p>Atualizando as estatísticas… O painel aparecerá automaticamente.</p></body></html>",
        200,
        {"X-CPJ-Painel": "atualizando", "Retry-After": "2"},
    )


@bp_sistema.get("/api/painel/pdf")
@bp_sistema.get("/painel.pdf")
@requer("estatisticas")
def painel_pdf():
    chave = comum.assinatura_painel()
    html_p = os.path.join(WS, "producao", "painel.html")
    pdf_p = os.path.join(WS, "producao", "painel.pdf")
    if not os.path.isfile(html_p):
        comum.atualizar_painel(chave)
    edge = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    if not os.path.isfile(edge):
        edge = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
    if not os.path.isfile(edge):
        return jsonify({"erro": "Navegador Microsoft Edge não encontrado para conversão em PDF."}), 500
    file_url = "file:///" + os.path.abspath(html_p).replace("\\", "/")
    cmd = [edge, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={pdf_p}", file_url]
    subprocess.run(cmd, timeout=30, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if os.path.isfile(pdf_p):
        auditar("estatisticas_pdf_baixado")
        return send_file(pdf_p, as_attachment=True, download_name=f"Estatisticas-SIP-Fraudes-{C.hoje()}.pdf")
    return jsonify({"erro": "Falha ao gerar PDF das estatísticas."}), 500


CONFIG_LLM = os.path.join(WS, "config", "chaves_llm.json")


def _carregar_cfg_llm():
    padrao = {
        "openai": {"nome": "OpenAI API (GPT)", "chave": "", "modelo": "", "ativo": False},
        "anthropic": {"nome": "Anthropic API (Claude)", "chave": "", "modelo": "", "ativo": False},
        "gemini": {"nome": "Google AI API (Gemini)", "chave": "", "modelo": "", "ativo": False},
        "deepseek": {"nome": "DeepSeek API", "chave": "", "modelo": "", "ativo": False},
        "xai": {"nome": "xAI API (Grok)", "chave": "", "modelo": "", "ativo": False},
        "openrouter": {"nome": "OpenRouter", "chave": "", "modelo": "", "ativo": False},
        "groq": {"nome": "Groq API", "chave": "", "modelo": "", "ativo": False},
        "nvidia": {"nome": "NVIDIA NIM API", "chave": "", "modelo": "", "ativo": False},
        "copilot": {"nome": "GitHub Copilot CLI", "chave": "", "modelo": "", "ativo": False}
    }
    if os.path.isfile(CONFIG_LLM):
        try:
            with open(CONFIG_LLM, "r", encoding="utf-8") as f:
                d = json.load(f)
                for k, v in d.items():
                    if k in padrao and isinstance(v, dict):
                        padrao[k].update(v)
        except Exception:
            pass
    return padrao


MODELOS_COPILOT = [
    {"id": m, "nome": n, "recente": False}
    for m, n in (
        ("claude-sonnet-5.5", "Claude Sonnet 5.5 (padrão documentado do CLI)"),
        ("gpt-6.1-sol", "GPT-6.1 Sol (seleção explícita)"), ("gpt-6-astra", "GPT-6 Astra (seleção explícita)"),
        ("gpt-6-luna", "GPT-6 Luna (seleção explícita)"), ("claude-opus-5.5", "Claude Opus 5.5"),
        ("claude-haiku-5.5", "Claude Haiku 5.5"), ("gpt-5.4", "GPT-5.4"),
        ("gpt-5.3-codex", "GPT-5.3 Codex"), ("gemini-3.7-flash", "Gemini 3.7 Flash"),
    )
]

MODELOS_EQUILIBRADOS = {
    "openai": ("gpt-6.1-sol",), "anthropic": ("claude-sonnet-5-5",),
    "gemini": ("gemini-3.8-flash",), "deepseek": ("deepseek-flash",), "xai": ("grok-4.7",),
    "groq": ("openai/gpt-oss-120b",), "nvidia": ("nvidia/llama-3.3-nemotron-super-49b-v1.5",),
    "openrouter": ("openai/gpt-6.1-sol", "anthropic/claude-sonnet-5.5"),
}
MODELOS_GEMINI_RECENTES = {
    "gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash",
    "gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.1-pro-preview",
    "gemini-3-flash-preview", "gemini-omni-1.1-flash",
}


def _get_json_modelos(url, headers):
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read(8 * 1024 * 1024).decode("utf-8"))
    except urllib.error.HTTPError as e:
        # Não repassa corpo/URL: gateways e provedores podem ecoar credenciais.
        raise ValueError(f"O provedor recusou a consulta ao catálogo (HTTP {e.code}).") from None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        raise ValueError("Não foi possível consultar o catálogo do provedor. Confira a conexão e tente novamente.") from None


def _consultar_modelos(provedor, chave):
    """Consulta só o catálogo de modelos; não envia prompt nem conteúdo de O.S."""
    if provedor == "copilot":
        return {"modelos": MODELOS_COPILOT, "origem": "catálogo documentado do Copilot CLI", "dinamico": False,
                "modelo_equilibrado": "", "aviso": "Lista documental; confirme no CLI o acesso da sua conta. Escolha explicitamente e salve."}
    if not chave:
        raise ValueError("Informe e salve a chave da API antes de atualizar os modelos.")

    headers = {"Accept": "application/json", "User-Agent": "Central-CPJ/0.4"}
    if provedor == "openai":
        url = "https://api.openai.com/v1/models"
        headers["Authorization"] = "Bearer " + chave
    elif provedor == "anthropic":
        url = "https://api.anthropic.com/v1/models?limit=1000"
        headers.update({"x-api-key": chave, "anthropic-version": "2023-06-01"})
    elif provedor == "gemini":
        url = "https://generativelanguage.googleapis.com/v1beta/models?pageSize=1000"
        headers["x-goog-api-key"] = chave
    elif provedor == "deepseek":
        url = "https://api.deepseek.com/models"
        headers["Authorization"] = "Bearer " + chave
    elif provedor == "xai":
        url = "https://api.x.ai/v1/models"
        headers["Authorization"] = "Bearer " + chave
    elif provedor == "openrouter":
        url = "https://openrouter.ai/api/v1/models?output_modalities=text&sort=newest"
        headers["Authorization"] = "Bearer " + chave
    elif provedor == "groq":
        url = "https://api.groq.com/openai/v1/models"
        headers["Authorization"] = "Bearer " + chave
    elif provedor == "nvidia":
        url = "https://integrate.api.nvidia.com/v1/models"
        headers["Authorization"] = "Bearer " + chave
    else:
        raise ValueError("Provedor não reconhecido.")

    itens = []
    cursor = None
    vistos = set()
    for pagina in range(10):
        pagina_url = url
        if cursor:
            pagina_url += "&" + urllib.parse.urlencode({"after_id" if provedor == "anthropic" else "pageToken": cursor})
        bruto = _get_json_modelos(pagina_url, headers)
        campo = "models" if provedor == "gemini" else "data"
        if not isinstance(bruto, dict) or not isinstance(bruto.get(campo, []), list):
            raise ValueError("O provedor retornou um catálogo inválido. Tente novamente.")
        itens.extend(m for m in bruto.get(campo, []) if isinstance(m, dict))
        proximo = None
        if provedor == "anthropic" and bruto.get("has_more"):
            proximo = bruto.get("last_id")
            if not proximo:
                raise ValueError("Catálogo incompleto: cursor de paginação ausente.")
        elif provedor == "gemini":
            proximo = bruto.get("nextPageToken")
        if not proximo:
            break
        if not isinstance(proximo, str) or proximo in vistos or pagina == 9:
            raise ValueError("Catálogo incompleto: paginação repetida ou limite de páginas atingido.")
        vistos.add(proximo)
        cursor = proximo
    nao_textuais = ("embedding", "moderation", "whisper", "tts", "transcribe", "realtime", "image", "audio", "sora")
    incompativeis = set()
    for m in itens:
        saidas = m.get("output_modalities")
        parametros = m.get("supported_parameters")
        if (m.get("active") is False or m.get("lifecycle") in ("deprecated", "retired") or
                (isinstance(saidas, list) and "text" not in saidas) or
                (provedor == "openrouter" and isinstance(parametros, list) and "tools" not in parametros) or
                m.get("tool_calling") is False or m.get("function_calling") is False):
            mid = m.get("id") or m.get("name") or ""
            incompativeis.add(mid.removeprefix("models/") if provedor == "gemini" else mid)
    if provedor == "gemini":
        itens = [m for m in itens if "generateContent" in m.get("supportedGenerationMethods", [])
                 and not any(x in m.get("name", "").lower() for x in nao_textuais)]
        normalizados = [{"id": m.get("name", "").removeprefix("models/"), "nome": m.get("displayName") or m.get("name"), "criado": ""}
                        for m in itens]
    else:
        normalizados = []
        for m in itens:
            mid = m.get("id") or m.get("name") or ""
            if not mid:
                continue
            # As APIs OpenAI-compatible também listam áudio, embeddings e imagem;
            # este seletor é para os pedidos textuais do plantão.
            low = mid.lower()
            if any(x in low for x in nao_textuais) or m.get("lifecycle") == "retired":
                continue
            if provedor == "openrouter":
                mods = (m.get("architecture") or {}).get("output_modalities") or []
                if "text" not in mods:
                    continue
            criado = m.get("created") or m.get("created_at") or ""
            nome = m.get("name") or m.get("display_name") or mid
            normalizados.append({"id": mid, "nome": nome, "criado": criado})

    normalizados = list({m["id"]: m for m in normalizados if m["id"]}.values())
    agora_ts = time.time()
    for m in normalizados:
        try:
            data_ts = float(m["criado"])
            if data_ts > 10**12:
                data_ts /= 1000
        except (TypeError, ValueError):
            try:
                data_ts = datetime.datetime.fromisoformat(str(m["criado"]).replace("Z", "+00:00")).timestamp()
            except (TypeError, ValueError, OverflowError):
                data_ts = 0
        m["_sort_ts"] = data_ts
        # Gemini does not include a creation timestamp in its list response.
        m["recente"] = (agora_ts - data_ts <= 183 * 86400) if data_ts else (
            provedor == "gemini" and m["id"] in MODELOS_GEMINI_RECENTES)
    normalizados.sort(key=lambda m: (not m["recente"], -m["_sort_ts"], m["id"].lower()))
    for m in normalizados: m.pop("_sort_ts", None)
    ids = {m["id"] for m in normalizados}
    equilibrado = next((m for m in MODELOS_EQUILIBRADOS.get(provedor, ()) if m in ids and m not in incompativeis), "")
    return {"modelos": normalizados, "origem": "catálogo atual da API", "dinamico": True,
            "modelo_equilibrado": equilibrado}


@bp_sistema.get("/api/sistema/llm")
@requer("ia")
def api_sistema_llm_get():
    cfg = _carregar_cfg_llm()
    saida = {}
    for prov, d in cfg.items():
        ch = d.get("chave") or ""
        mascarada = (ch[:4] + "*" * (len(ch) - 8) + ch[-4:]) if len(ch) >= 12 else ("*" * len(ch) if ch else "")
        saida[prov] = {
            "nome": d.get("nome", prov),
            "modelo": d.get("modelo", ""),
            "ativo": bool(d.get("ativo", False)),
            "chave_mascarada": mascarada,
            "tem_chave": bool(ch)
        }
    return jsonify(saida)


@bp_sistema.post("/api/sistema/llm")
@requer("usuarios")
def api_sistema_llm_post():
    dados = request.get_json(force=True) or {}
    prov = dados.get("provedor")
    if not prov:
        return jsonify({"erro": "Provedor não informado."}), 400
    cfg = _carregar_cfg_llm()
    if prov not in cfg:
        cfg[prov] = {"nome": prov, "chave": "", "modelo": "", "ativo": False}
    nova_chave = (dados.get("chave") or "").strip()
    if nova_chave and not nova_chave.startswith("*"):
        cfg[prov]["chave"] = nova_chave
    if "modelo" in dados:
        cfg[prov]["modelo"] = (dados["modelo"] or "").strip()
    if "ativo" in dados:
        cfg[prov]["ativo"] = bool(dados["ativo"])
    os.makedirs(os.path.dirname(CONFIG_LLM), exist_ok=True)
    with open(CONFIG_LLM, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    tarefas.sincronizar_provedor(prov)
    auditar("chaves_llm_atualizadas", prov)
    return jsonify({"ok": True, "provedor": prov})


@bp_sistema.get("/api/sistema/ia-config")
@requer("ia")
def api_sistema_ia_config_get():
    import executores_llm as EL
    cfg = EL.config_ia(WS)
    cfg["provedores_prontos"] = [p for p in sorted(EL.PROVEDORES_API) if EL.configuracao(WS, p)]
    return jsonify(cfg)


@bp_sistema.post("/api/sistema/ia-config")
@requer("usuarios")
def api_sistema_ia_config_post():
    import executores_llm as EL
    dados = request.get_json(force=True) or {}
    try:
        cfg = EL.salvar_config_ia(WS, dados)
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    auditar("ia_config_atualizada", f"modo={cfg['modo_padrao']} provedor={cfg['provedor_api'] or '-'}")
    return jsonify(cfg)


@bp_sistema.post("/api/sistema/llm/modelos")
@requer("usuarios")
def api_sistema_llm_modelos():
    dados = request.get_json(force=True) or {}
    prov = (dados.get("provedor") or "").strip().lower()
    cfg = _carregar_cfg_llm()
    if prov not in cfg:
        return jsonify({"erro": "Provedor não reconhecido."}), 400
    chave = (dados.get("chave") or cfg[prov].get("chave") or "").strip()
    try:
        resultado = _consultar_modelos(prov, chave)
    except ValueError as e:
        return jsonify({"erro": str(e)}), 502
    return jsonify(resultado)


@bp_sistema.get("/api/sistema")
@requer("dados")
def api_sistema():
    return jsonify({
        "idioma_ocr": idioma_ocr(ambiente_ocr()),
        "pdf_automatico": bool(soffice()),
        "workspace": WS,
    })
