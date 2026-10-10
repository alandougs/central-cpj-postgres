#!/usr/bin/env python3
"""Fallback de provedores de API em ordem de preferência, com configuração fictícia."""
import json
import os
import sys
import tempfile

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, APP)
import executores_llm as EL  # noqa: E402

# A saúde dos provedores é uma fronteira externa; o fallback é exercitado
# com todos disponíveis, sem consultar catálogos reais com chaves fictícias.
EL.verificar_saude = lambda provedor, chave: True


falhas = []


def ok(cond, msg):
    print(("OK   " if cond else "FALHA ") + msg)
    if not cond:
        falhas.append(msg)


with tempfile.TemporaryDirectory(dir=APP) as ws:
    os.makedirs(os.path.join(ws, "config"))
    provedores = ("openrouter", "nvidia", "deepseek", "gemini", "groq", "openai", "anthropic", "xai")
    with open(os.path.join(ws, "config", "chaves_llm.json"), "w", encoding="utf-8") as f:
        json.dump({p: {"ativo": True, "chave": "chave-ficticia-" + p, "modelo": "modelo-ficticio-" + p}
                   for p in provedores}, f)

    ok(EL.PROVEDORES_API == {"openai", "anthropic", "gemini", "deepseek", "xai", "openrouter", "groq", "nvidia"},
       "Groq e NVIDIA são reconhecidos como provedores de API")
    ok([p for p, _ in EL.provedores_api_configurados(ws)] ==
       ["anthropic", "openai", "gemini", "deepseek", "xai", "openrouter", "groq", "nvidia"],
       "modo automático respeita Claude, GPT, Gemini e depois os demais")
    EL.salvar_config_ia(ws, {"modo_padrao": "api"})
    ok(EL.agente_padrao(ws) == "Central-Anthropic API",
       "modo API automático inicia pelo Claude quando está habilitado")
    import plantao as PL  # noqa: E402
    ok({prov for _, prov in PL.provedores_api_ativos(ws)} == set(provedores),
       "plantão inicia os oito provedores API habilitados")

    tentativas = []

    def executar_falso(provedor, cfg):
        tentativas.append(provedor)
        if provedor in ("anthropic", "openai"):
            raise RuntimeError("provedor indisponível (HTTP 402)")
        return {"provedor": provedor, "modelo": cfg["modelo"]}

    resultado = EL.executar_com_fallback(ws, "", executar_falso, destinos_aceitos=list(provedores))
    ok(tentativas == ["anthropic", "openai", "gemini"],
       "falha sem créditos avança até o primeiro provedor funcional")
    ok(resultado == {"provedor": "gemini", "modelo": "modelo-ficticio-gemini"},
       "resultado informa o provedor que concluiu a execução")

    def falhar_com_chave(provedor, cfg):
        raise RuntimeError(f"resposta recusada para {cfg['chave']}")

    try:
        EL.executar_com_fallback(ws, "", falhar_com_chave, destinos_aceitos=list(provedores))
        ok(False, "falha de todos os provedores deve ser informada")
    except RuntimeError as e:
        ok(all(cfg["chave"] not in str(e) for _, cfg in EL.provedores_api_configurados(ws)),
           "erro consolidado não expõe nenhuma chave de API")

    tentativas.clear()
    resultado = EL.executar_com_fallback(ws, "openrouter", executar_falso, destinos_aceitos=list(provedores))
    ok(tentativas == ["openrouter"], "provedor escolhido explicitamente é tentado primeiro")
    ok(resultado["provedor"] == "openrouter", "provedor explícito funcional conclui sem tentativas extras")

    with open(os.path.join(ws, "config", "chaves_llm.json"), "w", encoding="utf-8") as f:
        json.dump({"anthropic": {"ativo": False, "chave": "x", "modelo": "m"},
                   "openai": {"ativo": True, "chave": "chave-ficticia", "modelo": "modelo-ficticio"}}, f)
    ok([p for p, _ in EL.provedores_api_configurados(ws)] == ["openai"],
       "provedor desativado não entra na cadeia de fallback")

    # O adaptador real monta a chamada OpenAI-compatible, sem abrir conexão externa.
    os.makedirs(os.path.join(ws, "casos", "OS-FICTICIA-2026"), exist_ok=True)
    chamadas = []
    http_original = EL._http_json

    def http_falso(url, headers, body=None, timeout=90):
        chamadas.append((url, headers, body))
        return {"choices": [{"message": {"content": "execução fictícia concluída"}}]}

    class PlantaoFalso:
        def progresso(self, *args, **kwargs):
            return True

        def pedido(self, _):
            return {"cancelar": False}

    EL._http_json = http_falso
    try:
        for provedor, endpoint in (("groq", "https://api.groq.com/openai/v1/chat/completions"),
                                   ("nvidia", "https://integrate.api.nvidia.com/v1/chat/completions")):
            resultado_api = EL.executar(ws, {"id": "ia-ficticia", "caso": "OS-FICTICIA-2026", "acao": "analisar",
                                              "solicitante": "teste", "consentimento": EL.criar_consentimento("teste", list(provedores))}, "Central-Teste API", provedor,
                                       {"chave": "chave-ficticia", "modelo": "modelo-ficticio"}, PlantaoFalso())
            ok(resultado_api["provedor"] == provedor, f"executor identifica o provedor {provedor}")
            ok(chamadas[-1][0] == endpoint and chamadas[-1][1]["Authorization"] == "Bearer chave-ficticia",
               f"executor envia ao endpoint autenticado de {provedor}")
    finally:
        EL._http_json = http_original

print("TUDO OK" if not falhas else f"{len(falhas)} FALHA(S)")
sys.exit(1 if falhas else 0)
