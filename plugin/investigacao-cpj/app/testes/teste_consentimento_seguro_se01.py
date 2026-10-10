"""SE01: gate real por HTTP local de teste, sem rede/CLI ou casos reais."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
BASE = tempfile.TemporaryDirectory(prefix="cpj-se01-import-")
os.environ.update(CPJ_WORKSPACE=BASE.name, CPJ_SEM_AGENTE_EMBUTIDO="1")
import auth
import executores_llm as EL
import plantao as PL
import rotas.comum as comum
import rotas.sistema as sistema
import rotas.usuarios as usuarios
import servidor
import tarefas as T


class Consentimento(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="cpj-se01-")
        self.addCleanup(self.tmp.cleanup)
        self.ws = self.tmp.name
        self.caso = "OS-777-2099"
        c = Path(self.ws) / "casos" / self.caso
        c.mkdir(parents=True)
        (c / "caso.json").write_text(json.dumps({"id": self.caso, "status": "recebido"}))
        self.auth = auth.Auth(self.ws)
        self.auth.salvar_usuario("operador", "Operador fictício", "admin", "Senha1234", temporaria=False)
        self.t = T.Tarefas(self.ws, comum.C, self.auth, iniciar_agente=False)
        for obj, campo, valor in ((comum, "WS", self.ws), (sistema, "WS", self.ws),
            (comum.C, "CASOS", str(Path(self.ws) / "casos")), (comum, "tarefas", self.t),
            (sistema, "tarefas", self.t), (comum, "_auth_inst", self.auth)):
            p = patch.object(obj, campo, valor); p.start(); self.addCleanup(p.stop)
        self.saude = patch.object(EL, "verificar_saude", return_value=True)
        self.saude.start(); self.addCleanup(self.saude.stop)
        self.rede = patch.object(EL, "_http_json", side_effect=AssertionError("HTTP externo proibido neste teste"))
        self.rede.start(); self.addCleanup(self.rede.stop)
        servidor.app.config["TESTING"] = True
        self.cli = servidor.app.test_client()
        self.cli.post("/api/entrar", json={"login": "operador", "senha": "Senha1234"}, headers={"X-CPJ": "1"})
        (Path(self.ws) / "config" / "chaves_llm.json").write_text(json.dumps({
            p: {"ativo": True, "chave": "ficticia", "modelo": "ficticio"} for p in ("openai", "gemini")
        }))

    def post(self, **dados):
        return self.cli.post(f"/api/casos/{self.caso}/ia", json={"acao": "completo", **dados}, headers={"X-CPJ": "1"})

    def registrar(self, nome, tipo, modo="auto"):
        self.t.plantao.registrar(nome, tipo, modo, aprovado=True)

    def test_padrao_api_requer_aceite_antes_de_enfileirar(self):
        EL.salvar_config_ia(self.ws, {"modo_padrao": "api", "provedor_api": "auto"})
        r = self.post().get_json()
        self.assertTrue(r["requer_consentimento"])
        self.assertEqual(set(r["destinos"]), {"openai", "gemini"})
        self.assertEqual(self.t.plantao.pedidos(), [])

    def test_cli_auto_requer_e_chat_manual_nao(self):
        self.registrar("Codex automático", "codex")
        r = self.post(agente="Codex automático").get_json()
        self.assertTrue(r["requer_consentimento"])
        self.assertEqual(r["destinos"], ["cli:codex"])
        self.registrar("Chat manual", "codex", "chat")
        r = self.post(agente="Chat manual").get_json()
        self.assertIn("tarefa", r)
        self.assertIsNone(self.t.plantao.pedido(r["tarefa"])["consentimento"])

    def test_identidade_data_servidor_e_aceite_atomico_todos_filhos(self):
        self.registrar("API teste", "openai-api")
        original = self.t.plantao.enfileirar
        visto = []
        def reservar_imediatamente(*a, **kw):
            pid = original(*a, **kw)
            visto.append(self.t.plantao.reivindicar("API teste"))
            return pid
        with patch.object(self.t.plantao, "enfileirar", side_effect=reservar_imediatamente):
            r = self.post(agente="API teste", consentimento_externo={"aceito": True, "destinos": ["openai"], "usuario": "FORJADO", "data_hora": "1900"}).get_json()
        self.assertIn("tarefa", r)
        self.assertIsNotNone(visto[0]["consentimento"])
        jobs = self.t.plantao.pedidos()
        self.assertEqual(len(jobs), 4)
        for j in jobs:
            c = json.loads(j["consentimento"])
            self.assertEqual(c["usuario"], "operador")
            self.assertNotEqual(c["data_hora"], "1900")
            self.assertEqual(c["destinos"], ["openai"])
            self.assertEqual(c["escopo"], "api_ia")

    def test_vazio_malformado_destino_falso_nao_enfileira(self):
        self.registrar("API teste", "openai-api")
        for c in (None, {}, [], "sim", {"destinos": ["openai"]}, {"aceito": None, "destinos": ["openai"]},
                  {"aceito": 0, "destinos": ["openai"]}, {"destinos": []}, {"destinos": ["evil"]},
                  {"destinos": "openai"}, {"destinos": ["openai", 42]},
                  {"destinos": ["openai"], "escopo": "outro"},
                  {"destinos": ["openai"], "aceito": "não"},
                  {"destinos": ["openai"], "recusado": "true"}):
            with self.subTest(cons=c):
                r = self.post(agente="API teste", consentimento_externo=c)
                self.assertEqual(r.status_code, 400)
                self.assertEqual(self.t.plantao.pedidos(), [])

    def test_recusa_nao_enfileira_e_e_auditada(self):
        self.registrar("API teste", "openai-api")
        r = self.post(agente="API teste", consentimento_externo={"recusado": True}).get_json()
        self.assertTrue(r["ok"])
        self.assertNotIn("tarefa", r)
        self.assertEqual(self.t.plantao.pedidos(), [])
        self.assertIn("consentimento_recusado", (Path(self.ws) / "config" / "auditoria.log").read_text())

    def test_executor_historico_sem_aceite_bloqueia_antes_prompt_http_cli(self):
        self.registrar("API teste", "openai-api")
        self.t.plantao.enfileirar(self.caso, "financeiro", "operador")
        job = self.t.plantao.reivindicar("API teste")
        for c in (None, "{}", "null", "[]", "invalido"):
            with self.subTest(cons=c), patch.object(PL, "montar_prompt") as prompt:
                with self.assertRaisesRegex(EL.ConsentimentoNecessario, "consentimento"):
                    EL.executar(self.ws, dict(job, consentimento=c), "API teste", "openai", {"modelo": "ficticio", "chave": "ficticia"}, self.t.plantao)
                prompt.assert_not_called()
        with patch.object(PL.subprocess, "Popen") as proc:
            with self.assertRaises(EL.ConsentimentoNecessario):
                PL._executar_sessao(self.t.plantao, job, "API teste", "codex")
        proc.assert_not_called()

    def test_fallback_sem_lista_e_sem_aceite_nao_tenta_provedor(self):
        for d in (None, [], "openai"):
            tentativas = []
            with self.assertRaises(EL.ConsentimentoNecessario):
                EL.executar_com_fallback(self.ws, "openai", lambda *a: tentativas.append(a), d)
            self.assertEqual(tentativas, [])


if __name__ == "__main__":
    try: unittest.main(verbosity=2)
    finally: BASE.cleanup()
