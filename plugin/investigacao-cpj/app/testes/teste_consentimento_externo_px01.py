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
    T = tempfile.mkdtemp(prefix="cpj-px01-")
    try:
        ws_test = os.path.join(T, "ws")
        os.makedirs(os.path.join(ws_test, "casos", "OS-999-2026"), exist_ok=True)
        os.makedirs(os.path.join(ws_test, "config"), exist_ok=True)
        
        # Seta o ws no sys
        import rotas.comum as comum
        import servidor as central
        central.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        
        # Moca comum.C.ws
        # Moca comum.C.ws e comum.C.CASOS
        import rotas.comum as comum
        comum.C.ws = ws_test
        print("C.ws is", comum.C.ws)
        comum.C.CASOS = os.path.join(ws_test, "casos")
        comum.WS = ws_test
        
        import rotas.sistema as sistema
        sistema.WS = ws_test
        
        # Cria o caso.json falso para C.existe retornar True
        with open(os.path.join(ws_test, "casos", "OS-999-2026", "caso.json"), "w", encoding="utf-8") as f:
            json.dump({"id": "OS-999-2026", "status": "em_analise"}, f)

        
        # Moca o plantão config DB
        import plantao
        plantao_db = os.path.join(ws_test, "config", "plantao.db")
        plant = plantao.Plantao(plantao_db)
        
        import tarefas
        tarefas.plantao = plant
        tarefas.ws = ws_test
        import tarefas as modulo_tarefas
        comum.tarefas.plantao = plant
        comum.tarefas.ws = ws_test
        
        import auth
        a = auth.Auth(os.path.join(ws_test, "config", "usuarios.db"))
        a.salvar_usuario("alan", "Alan Douglas Silva", "admin", "Senha123", cargo="Inv")
        central.auth = a
        
        cliente = central.app.test_client()
        cliente.post("/api/entrar", json={"login": "alan", "senha": "Senha123"}, headers={"X-CPJ": "1"})
        
        # Moca os provedores ativos (OpenAI e Gemini)
        import executores_llm as EL
        cfg_ia = {"openai": {"chave": "sk-123", "modelo": "gpt-4"}, "gemini": {"chave": "AIza", "modelo": "gemini-1.5"}, "ordem_fallback": ["openai", "gemini"]}
        with open(os.path.join(ws_test, "config", "ia.json"), "w", encoding="utf-8") as f:
        cfg_ia = {"openai": {"chave": "sk-123", "modelo": "gpt-4", "ativo": True}, "gemini": {"chave": "AIza", "modelo": "gemini-1.5", "ativo": True}}
        with open(os.path.join(ws_test, "config", "chaves_llm.json"), "w", encoding="utf-8") as f:
            json.dump(cfg_ia, f)
            
        with plant._c() as c:
            c.execute("INSERT INTO agentes(nome, tipo, modo, aprovado) VALUES('api-openai', 'api', 'manual', 1)")
            
        print("a) Pedido em modo API sem aceite -> recusado e retorna requer_consentimento")
        r = cliente.post("/api/casos/OS-999-2026/ia", json={"acao": "analisar", "agente": "api-openai"}, headers={"X-CPJ": "1"})
        print(r.status_code, r.data)
        d = r.get_json()
        ok(d.get("requer_consentimento") is True, "Retorna requer_consentimento")
        ok("openai" in d.get("destinos", []), "Destinos incluem openai")
        ok("gemini" in d.get("destinos", []), "Destinos incluem gemini")
        
        print("b) Com aceite -> cria o pedido na fila")
        r = cliente.post("/api/casos/OS-999-2026/ia", json={"acao": "analisar", "agente": "api-openai", "consentimento_externo": {"usuario": "Teste", "data_hora": "2026", "destinos": ["openai", "gemini"]}}, headers={"X-CPJ": "1"})
        d = r.get_json()
        ok("tarefa" in d, "Tarefa enfileirada com sucesso")
        tid = d["tarefa"]
        tid = d.get("tarefa", 0)
        
        # Verifica se gravou no banco
        with plant._c() as c:
            ped = c.execute("SELECT consentimento FROM pedidos WHERE id=?", (tid,)).fetchone()
            cons = json.loads(ped["consentimento"]) if ped and ped["consentimento"] else None
            ok(cons and "openai" in cons["destinos"], "Consentimento gravado no banco")
            
        print("c) Execução respeita o consentimento (fallback não aceito é pulado)")
        # Para simular, vamos usar o EL.executar_com_fallback diretamente
        chamadas = []
        def tentar(prov, cfg):
            if prov == "openai": raise RuntimeError("Erro no openai")
            chamadas.append(prov)
            return True
            
        try:
            EL.executar_com_fallback(ws_test, "api-openai", tentar, destinos_aceitos=["openai"])
        except Exception as e:
            msg = str(e)
            ok("destino recusado pelo usuario" in msg or "gemini: destino recusado" in msg, "Gemini recusado e falha final")
        ok("gemini" not in chamadas, "Gemini não foi chamado porque não estava nos destinos aceitos")
        
        print("d) Recusa é registrada e não enfileira")
        r = cliente.post("/api/casos/OS-999-2026/ia", json={"acao": "analisar", "agente": "api-openai", "consentimento_externo": {"recusado": True}}, headers={"X-CPJ": "1"})
        d = r.get_json()
        ok(d.get("ok") is True and "tarefa" not in d, "Recusa confirmada sem enfileirar")
        
        # Verifica log
        aud_log = os.path.join(ws_test, "config", "auditoria.log")
        if os.path.exists(aud_log):
            log_txt = open(aud_log, "r", encoding="utf-8").read()
            ok("consentimento_recusado" in log_txt, "Auditoria registra a recusa")
            
        print("e) Modo agente local/scripts -> sem aviso")
        with plant._c() as c:
            c.execute("UPDATE pedidos SET estado='concluido' WHERE id=?", (tid,))
        # Criar agente fictício aprovado
        with plant._c() as c:
            c.execute("INSERT INTO agentes(nome, tipo, modo, aprovado) VALUES('Local-1', 'cli', 'auto', 1)")
        r = cliente.post("/api/casos/OS-999-2026/ia", json={"acao": "analisar", "agente": "Local-1"}, headers={"X-CPJ": "1"})
        d = r.get_json()
        ok("tarefa" in d and not d.get("requer_consentimento"), "Local não pede consentimento")
        
        print("f) Modal no index.html")
        html_path = os.path.join(APP, "static", "index.html")
        html = open(html_path, "r", encoding="utf-8").read()
        ok('id="modal-consentimento"' in html, "Modal está no HTML")
        ok('id="b-cons-recusar"' in html and 'id="b-cons-aceitar"' in html, "Botões estão no HTML")
        ok("http://" not in html.split('id="modal-consentimento"')[1].split("</div")[0], "Sem URL externa no modal")
        
    finally:
        shutil.rmtree(T, ignore_errors=True)
    if falhas:
        sys.exit(1)

if __name__ == "__main__":
    testar()
