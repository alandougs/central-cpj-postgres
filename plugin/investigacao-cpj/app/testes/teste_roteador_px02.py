import json
import os
import sys
import tempfile
import shutil

AQUI = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(AQUI)
PLUGIN = os.path.dirname(APP)
ROOT = os.path.dirname(os.path.dirname(PLUGIN))

if APP not in sys.path:
    sys.path.insert(0, APP)

falhas = []
def ok(cond, msg):
    if not cond:
        print(f"FALHA: {msg}")
        falhas.append(msg)
    else:
        print(f"OK: {msg}")

def testar():
    T = tempfile.mkdtemp(prefix="cpj-px02-")
    try:
        ws_test = os.path.join(T, "ws")
        os.makedirs(os.path.join(ws_test, "config"), exist_ok=True)
        
        import rotas.comum as comum
        comum.C.ws = ws_test
        comum.WS = ws_test
        
        import executores_llm as EL
        
        # Configure ia.json for order and timeout
        with open(os.path.join(ws_test, "config", "ia.json"), "w", encoding="utf-8") as f:
            json.dump({"ordem_provedores": ["openai", "gemini", "anthropic"], "timeout": 1}, f)
            
        # Configure chaves_llm.json
        with open(os.path.join(ws_test, "config", "chaves_llm.json"), "w", encoding="utf-8") as f:
            json.dump({
                "openai": {"chave": "sk-openai", "modelo": "gpt-4", "ativo": True},
                "gemini": {"chave": "AIza-gemini", "modelo": "gemini-1.5", "ativo": True},
                "anthropic": {"chave": "sk-ant", "modelo": "claude-3", "ativo": True}
            }, f)
            
        # Mock saude caching so openai is unhealthy
        EL._saude_cache["openai"] = (False, 99999999999) # Future timestamp so it's fresh
        EL._saude_cache["gemini"] = (True, 99999999999)
        EL._saude_cache["anthropic"] = (True, 99999999999)
        
        # 1. Provedor sem saude e pulado para o fim
        chamadas = []
        def exec_mock(prov, cfg):
            chamadas.append(prov)
            if prov != "openai": raise RuntimeError("erro qualquer")
            return True
            
        EL.rotear(ws_test, executor=exec_mock)
        ok(chamadas[0] == "gemini", "Gemini foi chamado primeiro porque OpenAI esta sem saude")
        ok("openai" in chamadas, "OpenAI foi chamado no final (lista de doentes)")
        
        # 2. Selecao por capacidade
        chamadas.clear()
        def exec_pdf(prov, cfg):
            chamadas.append(prov)
            if prov == "gemini": raise RuntimeError("erro gemini")
            return True
            
        EL.rotear(ws_test, capacidades=["pdf"], executor=exec_pdf)
        ok(chamadas[0] == "gemini", "Gemini atende a pdf")
        ok("anthropic" in chamadas, "Anthropic atende a pdf e foi chamado apois falha do gemini")
        ok("openai" not in chamadas, "OpenAI nao atende a pdf")
        
        # 3. Nova tentativa em erro 500, timeout
        chamadas.clear()
        def exec_retry(prov, cfg):
            chamadas.append(prov)
            if chamadas.count(prov) == 1:
                if prov == "gemini": raise RuntimeError("HTTP 500 server error")
                if prov == "anthropic": raise TimeoutError("Timeout")
            return prov
            
        res = EL.rotear(ws_test, capacidades=["pdf"], executor=exec_retry)
        ok(res == "gemini", "Retornou gemini apois retry")
        ok(chamadas.count("gemini") == 2, "Fez nova tentativa para 500 no gemini")
        
        # 4. Sem nova tentativa em erro 400
        chamadas.clear()
        def exec_no_retry(prov, cfg):
            chamadas.append(prov)
            if prov == "gemini": raise RuntimeError("HTTP 400 bad request AIza-gemini")
            return prov
            
        EL._saude_cache["gemini"] = (True, 99999999999)
        try:
            EL.rotear(ws_test, executor=exec_no_retry, destinos_aceitos=["gemini"])
            ok(False, "Deveria ter falhado")
        except RuntimeError as e:
            msg = str(e)
            ok("AIza-gemini" not in msg, "Chave nao aparece na mensagem")
            ok("[chave ocultada]" in msg or "chave" in msg.lower(), "Chave foi ocultada")
        ok(chamadas.count("gemini") == 1, "Nao retentou em 400")

    finally:
        shutil.rmtree(T, ignore_errors=True)
    if falhas:
        sys.exit(1)

if __name__ == "__main__":
    testar()
