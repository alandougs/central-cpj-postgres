"""Modo solo e detecção do Tesseract: python -X utf8 app/testes/teste_solo_claude.py.

Usa somente workspace temporário e dados fictícios; não inicia IA nem servidor de rede.
"""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest


class ModoSoloCPJ(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="cpj-solo-claude-")
        cls.ws = Path(cls.temp.name)
        cls.env_anterior = os.environ.get("CPJ_WORKSPACE")
        os.environ["CPJ_WORKSPACE"] = str(cls.ws)
        modelo = cls.ws / "casos" / "_MODELO-CASO"
        for pasta in ("00-originais", "01-extracao", "02-analise", "03-relatorios"):
            (modelo / pasta).mkdir(parents=True, exist_ok=True)
        (modelo / "caso.json").write_text(json.dumps({
            "datas": {}, "financeiro": {}, "ip": {}, "resultado": {}, "relatorios": []
        }), encoding="utf-8")
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        import servidor
        cls.s = servidor
        assert Path(servidor.WS).resolve() == cls.ws.resolve(), "Teste deve iniciar em processo isolado."
        servidor.app.config.update(TESTING=True)
        servidor.auth.salvar_usuario("admin_ficticio", "Admin Ficticio", "admin", "SenhaFicticia123")
        cls.solo = cls.ws / "config" / "solo.json"

    @classmethod
    def tearDownClass(cls):
        for arquivo in cls.ws.rglob("*"):
            if arquivo.is_file(): arquivo.chmod(0o600)
        cls.temp.cleanup()
        if cls.env_anterior is None: os.environ.pop("CPJ_WORKSPACE", None)
        else: os.environ["CPJ_WORKSPACE"] = cls.env_anterior

    def tearDown(self):
        self.solo.unlink(missing_ok=True)

    def ativar(self, valor=True):
        self.solo.write_text(json.dumps({"ativo": valor}), encoding="utf-8")

    def sessao(self, host="127.0.0.1:8765", remoto="127.0.0.1"):
        c = self.s.app.test_client()
        return c.get("/api/sessao", base_url=f"http://{host}", environ_base={"REMOTE_ADDR": remoto}).get_json()

    def test_sem_arquivo_exige_login(self):
        self.assertIsNone(self.sessao()["usuario"])

    def test_desligado_exige_login(self):
        self.ativar(False)
        self.assertIsNone(self.sessao()["usuario"])

    def test_ligado_entra_como_unico_admin_e_acessa_rota_protegida(self):
        self.ativar()
        s = self.sessao()
        self.assertEqual(s["usuario"]["login"], "admin_ficticio")
        c = self.s.app.test_client()
        r = c.get("/api/casos", base_url="http://localhost:8765", environ_base={"REMOTE_ADDR": "127.0.0.1"})
        self.assertEqual(r.status_code, 200)

    def test_ligado_nao_vale_pela_rede_nem_com_host_estranho(self):
        self.ativar()
        self.assertIsNone(self.sessao(host="192.168.0.10:8765", remoto="192.168.0.20")["usuario"])
        self.assertIsNone(self.sessao(host="exemplo.invalido:8765")["usuario"])

    def test_post_continua_exigindo_cabecalho_anti_csrf(self):
        self.ativar()
        c = self.s.app.test_client()
        r = c.post("/api/os", base_url="http://127.0.0.1:8765", environ_base={"REMOTE_ADDR": "127.0.0.1"}, data={})
        self.assertEqual(r.status_code, 403)

    def test_dois_admins_desliga_entrada_direta(self):
        self.ativar()
        self.s.auth.salvar_usuario("admin_ficticio2", "Admin Ficticio 2", "admin", "SenhaFicticia123")
        try:
            self.assertIsNone(self.sessao()["usuario"])
        finally:
            self.s.auth.remover_usuario("admin_ficticio2")

    def test_tesseract_detectado_por_variavel(self):
        import rotas.comum as comum
        pasta = self.ws / "tess-ficticio"
        pasta.mkdir(exist_ok=True)
        (pasta / "tesseract.exe").write_bytes(b"")
        anterior = os.environ.get("CPJ_TESSERACT")
        os.environ["CPJ_TESSERACT"] = str(pasta)
        try:
            self.assertEqual(comum._achar_tesseract(), str(pasta))
        finally:
            if anterior is None: os.environ.pop("CPJ_TESSERACT", None)
            else: os.environ["CPJ_TESSERACT"] = anterior


if __name__ == "__main__":
    unittest.main(verbosity=2)
