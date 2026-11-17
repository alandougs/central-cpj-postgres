"""Contratos HTTP de segurança, somente com dados e credenciais fictícios."""
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch


class SegurancaIntegrada(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="cpj-sec24-")
        cls.ws = Path(cls.temp.name)
        os.environ["CPJ_WORKSPACE"] = str(cls.ws)
        os.environ["CPJ_SEM_AGENTE_EMBUTIDO"] = "1"
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        import servidor
        cls.s = servidor
        assert Path(servidor.WS).resolve() == cls.ws.resolve()
        servidor.app.config.update(TESTING=True)
        servidor.auth.salvar_usuario("auditor", "AUDITOR FICTICIO", "admin", "SenhaFicticia123")
        cls.client = servidor.app.test_client()
        with cls.client.post("/api/entrar", json={"login": "auditor", "senha": "SenhaFicticia123"},
                             headers={"X-CPJ": "1"}) as r:
            assert r.status_code == 200

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def post(self, url, **kwargs):
        return self.client.post(url, headers={"X-CPJ": "1"}, **kwargs)

    def test_chave_nova_nao_fica_no_arquivo_nem_na_resposta(self):
        chave = "CHAVE-FICTICIA-SEC24-SEM-VALIDADE"
        with self.post("/api/sistema/llm", json={"provedor": "openai", "chave": chave,
                                              "modelo": "modelo-ficticio", "ativo": False}) as r:
            self.assertEqual(r.status_code, 200)
        self.assertNotIn(chave, (self.ws / "config/chaves_llm.json").read_text(encoding="utf-8"))
        with self.client.get("/api/sistema/llm") as r:
            self.assertEqual(r.status_code, 200)
            self.assertTrue(r.json["openai"]["tem_chave"])
            self.assertNotIn(chave, r.get_data(as_text=True))

    def test_config_corrompida_nao_e_silenciosamente_substituida(self):
        arquivo = self.ws / "config/chaves_llm.json"
        antes = arquivo.read_bytes() if arquivo.exists() else None
        danificado = b'{"openai":'
        arquivo.write_bytes(danificado)
        try:
            with self.post("/api/sistema/llm", json={"provedor": "openai", "modelo": "novo"}) as r:
                self.assertEqual(r.status_code, 503)
            self.assertEqual(arquivo.read_bytes(), danificado)
            with self.client.get("/api/sistema/llm") as r:
                self.assertEqual(r.status_code, 503)
        finally:
            if antes is None:
                arquivo.unlink()
            else:
                arquivo.write_bytes(antes)

    def test_salvamentos_simultaneos_preservam_os_dois_provedores(self):
        import rotas.sistema as sistema
        from flask import request
        clientes = []
        for _ in range(2):
            client = self.s.app.test_client()
            with client.post("/api/entrar", json={"login": "auditor", "senha": "SenhaFicticia123"},
                             headers={"X-CPJ": "1"}) as r:
                self.assertEqual(r.status_code, 200)
            clientes.append(client)
        leu_primeiro, liberar_primeiro, segundo_terminou = threading.Event(), threading.Event(), threading.Event()
        carregar = sistema._carregar_cfg_llm
        resultados = []
        def leitura_controlada():
            cfg = carregar()
            if request.get_json().get("modelo") == "modelo-primeiro":
                leu_primeiro.set()
                if not liberar_primeiro.wait(6):
                    raise RuntimeError("Teste não liberou gravação sintética.")
            return cfg
        def salvar(indice, prov, modelo):
            try:
                with clientes[indice].post("/api/sistema/llm", json={"provedor": prov, "modelo": modelo},
                                          headers={"X-CPJ": "1"}) as r:
                    resultados.append(r.status_code)
            finally:
                if indice == 1: segundo_terminou.set()
        a = threading.Thread(target=salvar, args=(0, "openai", "modelo-primeiro"))
        b = threading.Thread(target=salvar, args=(1, "anthropic", "modelo-segundo"))
        with patch.object(sistema, "_carregar_cfg_llm", side_effect=leitura_controlada):
            a.start()
            self.assertTrue(leu_primeiro.wait(3))
            b.start()
            segundo_terminou.wait(1)
            liberar_primeiro.set()
            a.join(6); b.join(6)
        self.assertFalse(a.is_alive() or b.is_alive())
        self.assertEqual(sorted(resultados), [200, 200])
        with self.client.get("/api/sistema/llm") as r:
            self.assertEqual(r.json["openai"]["modelo"], "modelo-primeiro")
            self.assertEqual(r.json["anthropic"]["modelo"], "modelo-segundo")

    def test_exportacao_sem_senha_nao_cria_tarefa(self):
        antes = set(self.s.tarefas.t)
        for senha in (None, "curta", 123, []):
            with self.subTest(senha=senha):
                with self.post("/api/exportar", json={"modo": "completo", "senha": senha}) as r:
                    self.assertEqual(r.status_code, 400)
                self.assertEqual(set(self.s.tarefas.t), antes)

    def test_importacao_zip_exige_aceite_positivo_antes_de_enfileirar(self):
        antes = set(self.s.tarefas.t)
        with self.post("/api/importar", data={"arquivo": (io.BytesIO(b"ZIP FICTICIO"), "antigo.zip")}) as r:
            self.assertEqual(r.status_code, 400)
        self.assertEqual(set(self.s.tarefas.t), antes)

    def test_auditoria_expoe_estado_de_integridade_sem_segredos(self):
        with self.client.get("/api/auditoria/integridade") as r:
            self.assertEqual(r.status_code, 200)
            self.assertTrue(r.json["integra"])
            self.assertNotIn("chave", json.dumps(r.json).lower())

    def test_auditoria_adulterada_da_diagnostico_e_lista_falha_com_json(self):
        log = Path(self.s.auth.log)
        original = log.read_bytes()
        log.write_bytes(original + b'{"registro":"FICTICIO ALTERADO"}\n')
        try:
            with self.client.get("/api/auditoria/integridade") as r:
                self.assertEqual(r.status_code, 200)
                self.assertFalse(r.json["integra"])
            with self.client.get("/api/auditoria") as r:
                self.assertEqual(r.status_code, 503)
                self.assertIn("erro", r.json)
                self.assertNotIn("FICTICIO ALTERADO", r.get_data(as_text=True))
        finally:
            log.write_bytes(original)

    def aguardar(self, tid):
        limite = time.monotonic() + 15
        while time.monotonic() < limite:
            with self.client.get("/api/tarefas") as r:
                self.assertEqual(r.status_code, 200)
                tarefa = next((t for t in r.json if t["id"] == tid), None)
            if tarefa and tarefa["status"] in ("concluida", "erro", "cancelada"):
                return tarefa
            time.sleep(0.05)
        self.fail("Tarefa sintética não encerrou no limite de 15 segundos.")

    def test_exportar_baixar_importar_http_com_senha_sem_vazar(self):
        caso = self.ws / "casos/OS-99024-2099"
        caso.mkdir(parents=True, exist_ok=True)
        (caso / "caso.json").write_text(json.dumps({
            "id": caso.name, "ordem_servico": "99024/2099", "datas": {}, "status": "recebido"
        }), encoding="utf-8")
        senha = "SENHA-FICTICIA-SEC24-1234"
        with self.post("/api/exportar", json={"modo": "completo", "senha": senha}) as r:
            self.assertEqual(r.status_code, 200)
            tid = r.json["tarefa"]
        tarefa = self.aguardar(tid)
        self.assertEqual(tarefa["status"], "concluida", tarefa.get("erro"))
        self.assertNotIn(senha, json.dumps(self.s.tarefas.t))
        nome = tarefa["resultado"]["arquivo"]
        self.assertTrue(nome.endswith(".cpjenc"))
        with self.client.get("/api/exportacoes") as r:
            registro = next(x for x in r.json if x["arquivo"] == nome)
            self.assertTrue(registro["criptografado"])
            self.assertFalse(registro["legado"])
        with self.client.get(tarefa["resultado"]["url"]) as r:
            self.assertEqual(r.status_code, 200)
            pacote = r.data
        self.assertFalse(pacote.startswith(b"PK"))
        with self.post("/api/importar", data={"senha": senha,
                      "arquivo": (io.BytesIO(pacote), nome)}) as r:
            self.assertEqual(r.status_code, 200)
            importacao = r.json["tarefa"]
        resultado = self.aguardar(importacao)
        self.assertEqual(resultado["status"], "concluida", resultado.get("erro"))
        self.assertIn(caso.name, resultado["resultado"]["casos_ja_existentes"])
        self.assertNotIn(senha, json.dumps(self.s.tarefas.t))

    def test_conta_sem_permissao_nao_acessa_diagnostico_nem_exporta(self):
        self.s.auth.salvar_usuario("leitor_sec24", "LEITOR FICTICIO", "escrivao", "SenhaFicticia123")
        client = self.s.app.test_client()
        with client.post("/api/entrar", json={"login": "leitor_sec24", "senha": "SenhaFicticia123"},
                         headers={"X-CPJ": "1"}) as r:
            self.assertEqual(r.status_code, 200)
        with client.get("/api/auditoria/integridade") as r:
            self.assertEqual(r.status_code, 403)
        with client.post("/api/exportar", json={"senha": "FICTICIA-123456789"}, headers={"X-CPJ": "1"}) as r:
            self.assertEqual(r.status_code, 403)


if __name__ == "__main__":
    unittest.main(verbosity=2)
