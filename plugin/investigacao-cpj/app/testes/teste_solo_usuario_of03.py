"""OF03: entrada solo vinculada a um administrador, em workspace fictício isolado."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest


class SoloUsuarioOF03(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="cpj-solo-of03-")
        cls.ws = Path(cls.temp.name)
        cls.env = {k: os.environ.get(k) for k in ("CPJ_WORKSPACE", "CPJ_SEM_AGENTE_EMBUTIDO")}
        os.environ.update(CPJ_WORKSPACE=str(cls.ws), CPJ_SEM_AGENTE_EMBUTIDO="1")
        modelo = cls.ws / "casos" / "_MODELO-CASO"
        for pasta in ("00-originais", "01-extracao", "02-analise", "03-relatorios"):
            (modelo / pasta).mkdir(parents=True, exist_ok=True)
        (modelo / "caso.json").write_text(json.dumps({
            "datas": {}, "financeiro": {}, "ip": {}, "resultado": {}, "relatorios": []
        }), encoding="utf-8")
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        import servidor
        cls.s = servidor
        assert Path(servidor.WS).resolve() == cls.ws.resolve(), "Execute em processo isolado."
        servidor.app.config.update(TESTING=True)
        servidor.auth.salvar_usuario("admin_ficticio", "Administrador fictício", "admin", "SenhaFicticia123")
        servidor.auth.salvar_usuario("operador_ficticio", "Operador fictício", "admin", "SenhaFicticia123")
        cls.solo = cls.ws / "config" / "solo.json"

    @classmethod
    def tearDownClass(cls):
        for arquivo in cls.ws.rglob("*"):
            if arquivo.is_file():
                arquivo.chmod(0o600)
        cls.temp.cleanup()
        for chave, valor in cls.env.items():
            if valor is None:
                os.environ.pop(chave, None)
            else:
                os.environ[chave] = valor

    def setUp(self):
        self.s.auth.salvar_usuario("operador_ficticio", "Operador fictício", "admin", ativo=True)
        self.configurar({"ativo": True, "usuario": "operador_ficticio"})

    def configurar(self, dados):
        self.solo.write_text(json.dumps(dados), encoding="utf-8")

    def sessao(self, host="localhost:8765", remoto="127.0.0.1"):
        return self.s.app.test_client().get(
            "/api/sessao", base_url=f"http://{host}", environ_base={"REMOTE_ADDR": remoto}
        ).get_json()

    def test_dois_administradores_entra_como_operador_configurado(self):
        sessao = self.sessao()
        self.assertIsNotNone(sessao["usuario"])
        self.assertEqual(sessao["usuario"]["login"], "operador_ficticio")
        self.assertTrue(sessao["solo"])
        self.assertIn("trabalho", sessao["permissoes"])
        self.assertEqual(self.s.app.test_client().get("/api/casos").status_code, 200)

    def test_configuracao_invalida_nao_escolhe_unico_admin_restante(self):
        self.s.auth.salvar_usuario("operador_ficticio", "Operador fictício", "admin", ativo=False)
        for login in ("inexistente", "operador_ficticio", "", None, 42, [], {}):
            with self.subTest(login=login):
                self.configurar({"ativo": True, "usuario": login})
                sessao = self.sessao()
                self.assertIsNone(sessao["usuario"])
                self.assertFalse(sessao["solo"])

    def test_usuario_configurado_precisa_ser_administrador(self):
        self.s.auth.salvar_usuario("operador_ficticio", "Operador fictício", "investigador")
        self.assertIsNone(self.sessao()["usuario"])
        self.assertFalse(self.sessao()["solo"])

    def test_sem_usuario_configurado_preserva_regra_de_admin_unico(self):
        self.configurar({"ativo": True})
        self.assertIsNone(self.sessao()["usuario"])
        self.s.auth.salvar_usuario("operador_ficticio", "Operador fictício", "admin", ativo=False)
        self.assertEqual(self.sessao()["usuario"]["login"], "admin_ficticio")

    def test_desativado_ausente_ou_json_invalido_exige_login(self):
        self.configurar({"ativo": False, "usuario": "operador_ficticio"})
        self.assertIsNone(self.sessao()["usuario"])
        self.solo.unlink()
        self.assertIsNone(self.sessao()["usuario"])
        for conteudo in ("{", "[]", "null"):
            self.solo.write_text(conteudo, encoding="utf-8")
            self.assertIsNone(self.sessao()["usuario"])

    def test_rede_e_host_externo_nao_recebem_entrada_direta(self):
        for host, remoto in (("localhost:8765", "192.168.0.20"),
                             ("exemplo.invalido:8765", "127.0.0.1"),
                             ("127.0.0.1.exemplo.invalido:8765", "127.0.0.1")):
            with self.subTest(host=host, remoto=remoto):
                sessao = self.sessao(host, remoto)
                self.assertIsNone(sessao["usuario"])
                self.assertFalse(sessao["solo"])

    def test_solo_continua_exigindo_anti_csrf(self):
        client = self.s.app.test_client()
        self.assertEqual(client.post("/api/os", data={}).status_code, 403)


if __name__ == "__main__":
    unittest.main(verbosity=2)
