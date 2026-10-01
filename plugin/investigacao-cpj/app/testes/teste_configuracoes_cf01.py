#!/usr/bin/env python3
"""CF01: configurações de IA (modo agente x API), agente padrão e system prompt da via API. Só dados fictícios."""
import json
import os
import py_compile
import sys
import tempfile

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, APP)
import executores_llm as EL  # noqa: E402

falhas = []


def ok(cond, msg):
    print(("OK   " if cond else "FALHA ") + msg)
    if not cond:
        falhas.append(msg)


with tempfile.TemporaryDirectory() as ws:
    os.makedirs(os.path.join(ws, "config"))
    ok(EL.config_ia(ws) == EL.CONFIG_IA_PADRAO, "sem arquivo: modo padrão é agente")
    ok(EL.agente_padrao(ws) is None, "modo agente: nenhum agente forçado")

    ok(EL.salvar_config_ia(ws, {"modo_padrao": "api", "provedor_api": "anthropic"})["modo_padrao"] == "api", "salva modo api")
    ok(EL.agente_padrao(ws) is None, "modo api sem chave/modelo: não direciona (cai em qualquer agente)")

    with open(os.path.join(ws, "config", "chaves_llm.json"), "w", encoding="utf-8") as f:
        json.dump({"anthropic": {"ativo": True, "chave": "chave-ficticia", "modelo": "modelo-ficticio"}}, f)
    ok(EL.agente_padrao(ws) == "Central-Anthropic API", "modo api com provedor pronto: direciona ao agente de API")

    try:
        EL.salvar_config_ia(ws, {"provedor_api": "inexistente"})
        ok(False, "provedor desconhecido deve ser recusado")
    except ValueError:
        ok(True, "provedor desconhecido recusado")
    ok(EL.salvar_config_ia(ws, {"modo_padrao": "xyz"})["modo_padrao"] == "api", "modo inválido é ignorado")
    ok(len(EL.salvar_config_ia(ws, {"prompt_sistema": "x" * 9000})["prompt_sistema"]) == 8000, "prompt limitado a 8000")

    EL.salvar_config_ia(ws, {"prompt_sistema": "Priorize o caminho do dinheiro."})
    p = EL._instrucoes_locais(ws, "esteira")
    ok("Priorize o caminho do dinheiro." in p, "prompt do investigador entra no system prompt")
    for ag in ("analista-documental", "analista-financeiro", "revisor-de-relatorio"):
        ok(f"PAPEL (agente {ag})" in p, f"esteira inclui o papel {ag}")
    ok("SKILL analise-ip-fraude" in p and "SKILL relatorio-ip-fraude" in p, "esteira inclui as skills do plugin")
    ok("MODO API" in p, "explica que agentes/skills são papéis cumpridos com as ferramentas")
    ok("PAPEL (agente analista-financeiro)" not in EL._instrucoes_locais(ws, "analisar"), "analisar não carrega papéis alheios")

    cfg_antes = open(os.path.join(ws, "config", "chaves_llm.json"), encoding="utf-8").read()
    ok("chave-ficticia" not in json.dumps(EL.config_ia(ws)), "config_ia nunca expõe a chave")
    ok(open(os.path.join(ws, "config", "chaves_llm.json"), encoding="utf-8").read() == cfg_antes, "chaves_llm.json intacto")

for arq in ("rotas/sistema.py", "tarefas.py", "executores_llm.py"):
    try:
        py_compile.compile(os.path.join(APP, arq), doraise=True, cfile=os.path.join(tempfile.gettempdir(), "cf01.pyc"))
        ok(True, f"{arq} compila")
    except py_compile.PyCompileError as e:
        ok(False, f"{arq} não compila: {e}")

html = open(os.path.join(APP, "static", "index.html"), encoding="utf-8").read()
ok(all(x in html for x in ("cfgia-modo", "cfgia-prov", "cfgia-prompt", "b-cfgia", "carregarConfigIA();")), "interface CONFIGURAÇÕES presente")
rotas = open(os.path.join(APP, "rotas", "sistema.py"), encoding="utf-8").read()
ok('"/api/sistema/ia-config"' in rotas and rotas.count("ia-config") >= 2, "rotas GET/POST ia-config registradas")
ok('@requer("usuarios")\ndef api_sistema_ia_config_post' in rotas, "gravação restrita a quem gerencia usuários")

print("TUDO OK" if not falhas else f"{len(falhas)} FALHA(S)")
sys.exit(1 if falhas else 0)
