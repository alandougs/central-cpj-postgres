#!/usr/bin/env python3
"""Rotas de geração e gestão de relatórios: minuta, DOCX, PDF e relatório FINAL."""
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import unicodedata
from flask import Blueprint, abort, jsonify, request
from rotas.comum import (
    C,
    RF,
    WS,
    auditar,
    auth,
    gerar_docx,
    gerar_pdf,
    pasta_usuario,
    requer,
    tarefas,
)

bp_relatorios = Blueprint("relatorios", __name__)

CAMPOS_MINUTA = [
    "caso", "versao", "ordem_servico", "referencia", "natureza", "investigados", "vitimas", "local",
    "data_fatos", "local_data", "data_rodape", "delegado", "delegado_genero", "escrivao"
]


def _remover_acentos(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def ler_minuta(txt):
    meta, corpo = {}, txt
    m = re.match(r"\s*---\s*\n(.*?)\n---\s*\n(.*)", txt, flags=re.S)
    if m:
        for ln in m.group(1).splitlines():
            if ":" in ln:
                k, v = ln.split(":", 1)
                meta[k.strip()] = v.strip()
        corpo = m.group(2)
    secoes, atual = {"RESUMO DOS FATOS": [], "DILIGÊNCIAS REALIZADAS": [], "CONCLUSÃO": []}, None
    for ln in corpo.splitlines():
        t = re.match(r"^(#{2,3})\s+(.+?)\s*$", ln)
        if t:
            nivel_hashes, titulo_bruto = t.group(1), t.group(2).strip()
            norm = _remover_acentos(titulo_bruto).upper()
            s_match = None
            for s in secoes:
                s_norm = _remover_acentos(s).upper()
                if s_norm in norm or norm in s_norm:
                    s_match = s
                    break
            if s_match:
                atual = s_match
                continue
            elif nivel_hashes == "##":
                atual = None
                continue
        if atual:
            secoes[atual].append(ln)
    return meta, {k: "\n".join(v).strip() for k, v in secoes.items()}


def ultima_minuta(id_):
    d = os.path.join(C.caminho(id_), "03-relatorios")
    ms = (
        sorted(
            (f for f in os.listdir(d) if re.match(r"minuta-v\d+\.md$", f)),
            key=lambda f: int(re.findall(r"\d+", f)[0]),
        )
        if os.path.isdir(d)
        else []
    )
    return ms[-1] if ms else None


@bp_relatorios.get("/api/casos/<id_>/minuta")
@requer("trabalho")
def api_minuta(id_):
    ult = ultima_minuta(id_)
    nome = request.args.get("arquivo") or ult
    if not nome:
        c = C.carregar(id_)
        dp = {}
        pp = os.path.join(WS, "modelos", "dados-padrao.json")
        if os.path.exists(pp):
            dp = json.load(open(pp, encoding="utf-8"))
        hoje = datetime.date.today()
        meses = [
            "janeiro", "fevereiro", "março", "abril", "maio", "junho",
            "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"
        ]
        inq = str(c.get("inquerito") or c.get("ipe") or "").strip()
        proc = str(c.get("processo") or "").strip()
        num_ipe = re.sub(
            r"^(?:inquérito\s*policial\s*eletr[ôo]nico|inquerito\s*policial\s*eletr[oô]nico|inquérito\s*policial|inquerito\s*policial|inquérito|inquerito|ipe|ip)\s*(?:n[º°o.]*\s*)?",
            "",
            inq,
            flags=re.I,
        ).strip()
        num_proc = re.sub(
            r"^(?:processo\s*judicial|processo)\s*(?:n[º°o.]*\s*)?",
            "",
            proc,
            flags=re.I,
        ).strip()

        parte_ipe = f"IPe nº {num_ipe}" if num_ipe else "IPe nº [PENDENTE]"
        parte_proc = f"Processo nº {num_proc}" if num_proc else "Processo nº [PENDENTE]"
        referencia_montada = f"{parte_ipe} / {parte_proc}"

        gen = str(c.get("delegado_genero") or "").strip().upper()[:1]
        del_nome = dp.get("delegado_padrao") or c.get("requisitante") or c.get("delegado") or ""
        if gen not in ("M", "F"):
            if re.search(r"\b(?:dra\.?|doutora)\b", del_nome, re.I):
                gen = "F"
            elif re.search(r"\b(?:dr\.?|doutor)\b", del_nome, re.I):
                gen = "M"
            else:
                gen = ""

        meta = {
            "caso": id_,
            "versao": "01",
            "ordem_servico": c.get("ordem_servico") or "",
            "referencia": referencia_montada,
            "natureza": c.get("natureza") or "",
            "investigados": ", ".join(c.get("investigados") or []),
            "vitimas": ", ".join(c.get("vitimas") or []),
            "local": "",
            "data_fatos": "",
            "delegado": del_nome,
            "delegado_genero": gen,
            "escrivao": c.get("escrivao") or "",
            "local_data": f"{dp.get('cidade_uf', 'Presidente Prudente, SP')}, {hoje.day} de {meses[hoje.month - 1]} de {hoje.year}",
            "data_rodape": hoje.strftime("%d/%m/%Y"),
        }
        return jsonify({
            "arquivo": None,
            "versao_num": 0,
            "meta": meta,
            "secoes": {"RESUMO DOS FATOS": "", "DILIGÊNCIAS REALIZADAS": "", "CONCLUSÃO": ""},
            "ultima": None,
        })
    p = os.path.join(C.caminho(id_), "03-relatorios", os.path.basename(nome))
    if not os.path.exists(p):
        abort(404)
    c = C.carregar(id_)
    meta, sec = ler_minuta(open(p, encoding="utf-8").read())
    meta.setdefault("delegado_genero", c.get("delegado_genero") or "")
    meta.setdefault("escrivao", c.get("escrivao") or "")
    m_v = re.findall(r"\d+", os.path.basename(nome))
    versao_num = int(m_v[0]) if m_v else 1
    return jsonify({
        "arquivo": os.path.basename(nome),
        "versao_num": versao_num,
        "meta": meta,
        "secoes": sec,
        "ultima": ult,
    })


@bp_relatorios.post("/api/casos/<id_>/minuta")
@requer("trabalho")
def api_minuta_salvar(id_):
    d = request.get_json(force=True) or {}
    ultima_vista = d.get("ultima_vista")
    versao_base = d.get("versao_base")
    forcar = d.get("forcar", False)
    if versao_base is not None:
        if isinstance(versao_base, bool) or not re.fullmatch(r"\d+", str(versao_base)):
            return jsonify({"erro": "versao_base deve ser um inteiro não negativo."}), 400
        versao_base = int(versao_base)

    meta_in = {k: str((d.get("meta") or {}).get(k) or "").replace("\n", " ").strip() for k in CAMPOS_MINUTA}
    sec = d.get("secoes") or {}

    def _formatar(v, nome_arq):
        meta = dict(meta_in)
        meta.update(caso=id_, versao=f"{v:02d}", gerado_em=C.hoje(), editado_por=request.usuario["login"])
        return (
            "---\n"
            + "\n".join(f"{k}: {val}" for k, val in meta.items())
            + "\n---\n\n"
            + "\n\n".join(
                f"## {s}\n\n{(sec.get(s) or '').strip()}"
                for s in ("RESUMO DOS FATOS", "DILIGÊNCIAS REALIZADAS", "CONCLUSÃO")
            )
            + "\n"
        )

    try:
        # A leitura da base e a publicação da nova versão formam uma única operação.
        with C.trava(id_):
            ult = ultima_minuta(id_)
            v_atual = int(re.search(r"minuta-v(\d+)", ult).group(1)) if ult else 0
            if not forcar:
                if versao_base is not None and v_atual > versao_base:
                    return jsonify({
                        "conflito": True, "erro": "conflito_concorrencia", "ultima": ult,
                        "versao_atual": v_atual, "versao_base": versao_base,
                        "mensagem": f"Conflito de concorrência: a minuta já está na versão {v_atual} (base era {versao_base}).",
                    }), 409
                if ultima_vista and ult != ultima_vista:
                    return jsonify({
                        "conflito": True, "erro": "minuta_atualizada", "ultima": ult,
                        "mensagem": f"A minuta foi atualizada para {ult} por outro usuário ou processo.",
                    }), 409
            res = C.reservar_proxima_minuta(id_, _formatar, versao_base=None if forcar else versao_base)
            nome, v = res["arquivo"], res["versao"]
    except C.ConcorrenciaErro as e:
        return jsonify({"conflito": True, "erro": "conflito_concorrencia", "mensagem": str(e)}), 409

    try:
        c = C.carregar(id_)
        if c["status"] in ("recebido", "extraido", "em_analise", "analisado"):
            C.status(id_, "minuta")
    except Exception:
        pass
    out = {"arquivo": nome, "versao": v}
    if d.get("gerar_docx", True):
        try:
            out |= gerar_docx(WS, id_, nome)
        except RuntimeError as e:
            out["erro_docx"] = str(e)
    auditar("minuta_salva", f"{id_}/{nome}")
    return jsonify(out)


@bp_relatorios.post("/api/casos/<id_>/docx")
@requer("trabalho")
def api_docx(id_):
    nome = (request.get_json(silent=True) or {}).get("minuta") or ultima_minuta(id_)
    if not nome:
        return jsonify({"erro": "Não há minuta."}), 400
    try:
        out = gerar_docx(WS, id_, os.path.basename(nome))
    except RuntimeError as e:
        return jsonify({"erro": str(e)}), 400
    auditar("docx_gerado", f"{id_}/{out['docx']}")
    return jsonify(out)


@bp_relatorios.post("/api/casos/<id_>/pdf")
@requer("trabalho")
def api_pdf(id_):
    nome = os.path.basename((request.get_json(silent=True) or {}).get("docx") or "")
    if not nome.endswith(".docx"):
        return jsonify({"erro": "Informe o DOCX."}), 400
    try:
        out = gerar_pdf(WS, id_, nome)
    except RuntimeError as e:
        return jsonify({"erro": str(e)}), 400
    auditar("pdf_gerado", f"{id_}/{out['pdf']}")
    return jsonify(out)


def conferir_minuta_gate(id_, minuta_nome):
    """Executa conferir_minuta.py em modo entrega para o caso e minuta indicados."""
    with C.trava(id_):
        try:
            return _conferir_minuta_gate(id_, minuta_nome)
        except (OSError, subprocess.TimeoutExpired):
            return _erro_conferencia("Não foi possível executar a conferência da minuta. Tente novamente.")


def _conferir_minuta_gate(id_, minuta_nome):
    caminho_caso = C.caminho(id_)
    d_rel = os.path.join(caminho_caso, "03-relatorios")
    caminho_minuta = os.path.join(d_rel, minuta_nome)
    d_ext = os.path.join(caminho_caso, "01-extracao")
    d_ana = os.path.join(caminho_caso, "02-analise")
    caminho_fluxo = os.path.join(d_ana, "fluxo-financeiro.csv")

    app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    plugin_dir = os.path.dirname(app_dir)
    s_rel = os.path.join(plugin_dir, "skills", "relatorio-ip-fraude", "scripts")
    script_conf = os.path.join(s_rel, "conferir_minuta.py")

    cmd = [
        sys.executable,
        script_conf,
        id_,
        "--minuta", caminho_minuta,
        "--extracao", d_ext,
        "--modo", "entrega",
    ]
    if os.path.isfile(caminho_fluxo):
        cmd.extend(["--fluxo", caminho_fluxo])

    env = dict(os.environ, CPJ_WORKSPACE=getattr(C, "WS", WS), PYTHONIOENCODING="utf-8")
    sem_janela = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    m_v = re.search(r"minuta-v(\d+)", minuta_nome)
    versao = m_v.group(1) if m_v else None
    nome_json = f"conferencia-v{versao}.json" if versao else f"conferencia-{os.path.splitext(minuta_nome)[0]}.json"
    caminho_json = os.path.join(d_rel, nome_json)
    # Um arquivo de uma execução anterior nunca pode aprovar uma execução que falhou.
    if os.path.exists(caminho_json):
        os.remove(caminho_json)
    proc = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
        creationflags=sem_janela, env=env, timeout=180,
    )

    if os.path.isfile(caminho_json):
        try:
            with open(caminho_json, "r", encoding="utf-8") as f:
                conf = json.load(f)
            if isinstance(conf, dict) and isinstance(conf.get("aprovado"), bool):
                if not conf["aprovado"] or proc.returncode == 0:
                    return conf
        except (OSError, ValueError):
            pass
    return _erro_conferencia((proc.stderr or proc.stdout).strip() or "A execução não produziu uma conferência válida.")


def _erro_conferencia(detalhe):
    return {
        "aprovado": False,
        "resumo": {"BLOQUEIA": 1, "REVISAR": 0},
        "achados": [
            {
                "nivel": "BLOQUEIA",
                "codigo": "ERRO_EXECUCAO",
                "linha": 1,
                "dado": "",
                "detalhe": detalhe,
            }
        ],
        "conferidos": [],
    }


@bp_relatorios.post("/api/casos/<id_>/final")
@requer("trabalho")
def api_final(id_):
    """Define um DOCX como relatório FINAL (gera também o .md para calibração/RAG) e dá baixa."""
    dados = request.get_json(silent=True) or {}
    nome = os.path.basename(dados.get("docx") or "")
    d = os.path.join(C.caminho(id_), "03-relatorios")
    p = os.path.join(d, nome)
    if not nome.endswith(".docx") or not os.path.exists(p):
        return jsonify({"erro": "DOCX não encontrado."}), 400

    forcar = bool(dados.get("forcar", False))
    justificativa = str(dados.get("justificativa") or "").strip()
    if forcar and len(justificativa) < 15:
        return jsonify({"erro": "Justificativa obrigatória (mínimo 15 caracteres) para forçar entrega com ressalva."}), 400

    minuta_req = os.path.basename(dados.get("minuta") or "")
    minuta_nome = None
    m_docx = re.search(r"-v(\d+)\.docx$", nome, re.IGNORECASE)
    if minuta_req:
        m_minuta = re.fullmatch(r"minuta-v(\d+)\.md", minuta_req)
        if not m_minuta or not os.path.isfile(os.path.join(d, minuta_req)):
            return jsonify({"erro": "Minuta informada não encontrada ou inválida."}), 400
        if m_docx and int(m_docx.group(1)) != int(m_minuta.group(1)):
            return jsonify({"erro": "A minuta informada não corresponde à versão do DOCX."}), 400
        minuta_nome = minuta_req
    else:
        if m_docx:
            v_num = int(m_docx.group(1))
            for f in (os.listdir(d) if os.path.isdir(d) else []):
                if re.match(rf"minuta-v0*{v_num}\.md$", f):
                    minuta_nome = f
                    break
        else:
            minuta_nome = ultima_minuta(id_)

    if not minuta_nome:
        if not forcar:
            achado_ausente = {
                "nivel": "BLOQUEIA",
                "codigo": "MINUTA_AUSENTE",
                "linha": 1,
                "dado": "",
                "detalhe": "Nenhuma minuta encontrada para conferência do relatório.",
            }
            return jsonify({
                "ok": False,
                "bloqueado": True,
                "bloqueios": 1,
                "conferencia": [achado_ausente],
                "achados": [achado_ausente],
                "mensagem": "Nenhuma minuta encontrada para conferência do relatório.",
            }), 409
    else:
        conf = conferir_minuta_gate(id_, minuta_nome)
        achados = conf.get("achados", [])
        bloqueios = sum(1 for a in achados if a.get("nivel") == "BLOQUEIA")
        if (bloqueios > 0 or not conf.get("aprovado", True)) and not forcar:
            return jsonify({
                "ok": False,
                "bloqueado": True,
                "bloqueios": bloqueios or 1,
                "conferencia": achados,
                "achados": achados,
                "mensagem": f"Conferência reprovada: {bloqueios or 1} item(ns) bloqueante(s).",
            }), 409

    final = os.path.join(d, f"RELATORIO-{id_}-FINAL.docx")
    if os.path.abspath(p) != os.path.abspath(final):
        shutil.copyfile(p, final)
    try:
        texto = RF.extrair_texto(final)
        c = C.carregar(id_)
        with open(os.path.join(d, f"RELATORIO-{id_}-FINAL.md"), "w", encoding="utf-8") as f:
            f.write(
                f"---\ncaso: {id_}\ntipo: relatorio-final\nmodalidade: {c.get('modalidade') or ''}\norigem_docx: {nome}\n---\n\n{texto}"
            )
    except Exception:
        pass
    c = C.status(id_, "entregue", origem="central", arquivo=os.path.basename(final))
    if forcar and justificativa:
        def _set_ressalva(caso_dict):
            if "baixa" in caso_dict:
                caso_dict["baixa"]["ressalva"] = justificativa
        c = C.atualizar(id_, _set_ressalva)
        auditar("relatorio_final_ressalva", f"{id_}/{nome}: {justificativa}")
    else:
        auditar("relatorio_final", f"{id_}/{nome}")

    versoes = len([f for f in os.listdir(d) if re.match(r"minuta-v\d+\.md$", f)])
    C.registrar_relatorio(id_, os.path.basename(final), data=c["datas"]["entregue"], versoes=versoes or None)
    criador = c.get("criado_por")
    if criador and auth.obter(criador):
        shutil.copyfile(final, os.path.join(pasta_usuario(criador), "relatorios", f"RELATORIO-{id_}-FINAL.docx"))
    threading.Thread(target=tarefas.indexar, daemon=True).start()
    resp = {"ok": True, "final": os.path.basename(final)}
    if forcar and justificativa:
        resp["ressalva"] = justificativa
    return jsonify(resp)
