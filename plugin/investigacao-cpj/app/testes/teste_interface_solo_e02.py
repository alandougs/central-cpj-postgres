#!/usr/bin/env python3
"""Teste focado para a tarefa E02: modo solo na API de sessão e na interface."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(AQUI)
if APP not in sys.path:
    sys.path.insert(0, APP)


class TesteInterfaceSoloE02(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="cpj-e02-solo-")
        cls.ws = Path(cls.temp.name)
        cls.env_ant = os.environ.get("CPJ_WORKSPACE")
        os.environ["CPJ_WORKSPACE"] = str(cls.ws)

        modelo = cls.ws / "casos" / "_MODELO-CASO"
        for p in ("00-originais", "01-extracao", "02-analise", "03-relatorios"):
            (modelo / p).mkdir(parents=True, exist_ok=True)
        (modelo / "caso.json").write_text(json.dumps({"datas": {}, "financeiro": {}, "ip": {}, "resultado": {}, "relatorios": []}), encoding="utf-8")

        import servidor
        cls.servidor = servidor
        servidor.app.config.update(TESTING=True)
        servidor.auth.salvar_usuario("alan_teste", "Alan Douglas Silva", "admin", "SenhaTeste123", cargo="Investigador de Polícia")
        cls.solo_json = cls.ws / "config" / "solo.json"

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()
        if cls.env_ant is None:
            os.environ.pop("CPJ_WORKSPACE", None)
        else:
            os.environ["CPJ_WORKSPACE"] = cls.env_ant

    def tearDown(self):
        self.solo_json.unlink(missing_ok=True)

    def sessao(self, host="127.0.0.1:8765", remoto="127.0.0.1"):
        c = self.servidor.app.test_client()
        return c.get("/api/sessao", base_url=f"http://{host}", environ_base={"REMOTE_ADDR": remoto}).get_json()

    def test_api_sessao_devolve_campo_solo_false_quando_inativo(self):
        dados = self.sessao()
        self.assertIn("solo", dados)
        self.assertFalse(dados["solo"])
        self.assertIn("usuario", dados)
        self.assertIn("permissoes", dados)
        self.assertIn("configurado", dados)
        self.assertIn("local", dados)
        self.assertIn("perfis", dados)

    def test_api_sessao_devolve_campo_solo_true_quando_ativo_local(self):
        self.solo_json.write_text(json.dumps({"ativo": True}), encoding="utf-8")
        dados = self.sessao()
        self.assertIn("solo", dados)
        self.assertTrue(dados["solo"])
        self.assertIsNotNone(dados["usuario"])
        self.assertEqual(dados["usuario"]["nome"], "Alan Douglas Silva")
        self.assertEqual(dados["usuario"]["cargo"], "Investigador de Polícia")

    def test_api_sessao_devolve_campo_solo_false_pela_rede(self):
        self.solo_json.write_text(json.dumps({"ativo": True}), encoding="utf-8")
        dados = self.sessao(host="192.168.1.50:8765", remoto="192.168.1.50")
        self.assertFalse(dados["solo"])
        self.assertIsNone(dados["usuario"])

    def test_interface_html_contem_ids_e_regras_do_modo_solo(self):
        html_p = Path(APP) / "static" / "index.html"
        conteudo = html_p.read_text(encoding="utf-8")

        # Verifica ids dos cards ocultáveis
        self.assertIn('id="card-usuarios"', conteudo)
        self.assertIn('id="card-perfis"', conteudo)
        self.assertIn('id="card-rede"', conteudo)
        self.assertIn('id="b-sair"', conteudo)

        # Verifica tratamento de S.solo no script
        self.assertIn("solo:!!s.solo", conteudo)
        self.assertIn("#b-sair", conteudo)
        self.assertIn("#card-usuarios", conteudo)
        self.assertIn("#card-perfis", conteudo)
        self.assertIn("#card-rede", conteudo)
        self.assertIn("!S.solo", conteudo)


if __name__ == "__main__":
    unittest.main()

