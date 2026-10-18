"""EX01: revelar arquivos no Explorer; somente workspace e contas fictícios."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


class ExplorerFixture:
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="cpj-explorer-ex01-")
        cls.ws = Path(cls.temp.name)
        cls.env = {k: os.environ.get(k) for k in ("CPJ_WORKSPACE", "CPJ_WORKSPACES")}
        os.environ["CPJ_WORKSPACE"] = str(cls.ws)
        os.environ.pop("CPJ_WORKSPACES", None)
        modelo = cls.ws / "casos" / "_MODELO-CASO"
        for pasta in ("00-originais", "01-extracao", "02-analise", "03-relatorios"):
            (modelo / pasta).mkdir(parents=True)
        (modelo / "caso.json").write_text(json.dumps({
            "datas": {}, "financeiro": {}, "ip": {}, "resultado": {}, "relatorios": []
        }), encoding="utf-8")
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        import servidor
        from rotas import casos
        cls.s, cls.rotas = servidor, casos
        assert Path(servidor.WS).resolve() == cls.ws.resolve()
        servidor.app.config.update(TESTING=True)
        servidor.auth.salvar_usuario("admin_ex01", "Admin ficticio", "admin", "Ficticia123")
        cls.id = servidor.C.novo("901/2099")["id"]
        cls.pasta = Path(servidor.C.caminho(cls.id))
        cls.docx = "03-relatorios/relatório final (revisão), v01.DOCX"
        for rel in (cls.docx, "03-relatorios/minuta-v01.md", "02-analise/fluxo financeiro.csv"):
            (cls.pasta / rel).write_text("Conteudo ficticio", encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()
        for k, v in cls.env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def setUp(self):
        self.client = self.s.app.test_client()
        r = self.client.post("/api/entrar", json={"login": "admin_ex01", "senha": "Ficticia123"},
                             headers={"X-CPJ": "1"})
        self.assertEqual(r.status_code, 200)
        self.explorer = self.enterContext(patch("subprocess.Popen"))
        self.abrir = self.enterContext(patch.object(os, "startfile", create=True))

    def post(self, body, **kwargs):
        return self.client.post(f"/api/casos/{self.id}/abrir", json=body,
                                headers={"X-CPJ": "1"}, **kwargs)


class ExplorerEX01(ExplorerFixture, unittest.TestCase):
    def test_selecionar_docx_abre_explorer_sem_executar_arquivo(self):
        r = self.post({"sub": self.docx, "selecionar": True})
        self.assertEqual(r.status_code, 200)
        self.explorer.assert_called_once_with(["explorer.exe", "/select,", str((self.pasta / self.docx).resolve())])
        self.abrir.assert_not_called()

    def test_selecionar_csv_da_analise(self):
        r = self.post({"sub": "02-analise/fluxo financeiro.csv", "selecionar": True})
        self.assertEqual(r.status_code, 200)
        self.explorer.assert_called_once_with(["explorer.exe", "/select,", str((self.pasta / "02-analise/fluxo financeiro.csv").resolve())])
        self.abrir.assert_not_called()

    def test_abertura_existente_de_arquivo_e_pasta_preservada(self):
        for rel in ("", "03-relatorios", self.docx):
            with self.subTest(rel=rel):
                self.abrir.reset_mock()
                self.assertEqual(self.post({"sub": rel}).status_code, 200)
                self.abrir.assert_called_once_with(str((self.pasta / rel).resolve()))
        self.explorer.assert_not_called()

    def test_rede_nao_pode_abrir_explorer(self):
        self.assertEqual(self.post({"sub": self.docx, "selecionar": True},
                                  environ_overrides={"REMOTE_ADDR": "203.0.113.2"}).status_code, 403)
        self.explorer.assert_not_called()
        self.abrir.assert_not_called()

    def test_arquivos_ausentes_e_caminhos_fora_do_caso_bloqueados(self):
        for rel in ("03-relatorios/ausente.docx", "../_MODELO-CASO/caso.json", str(self.ws / "config" / "usuarios.json")):
            with self.subTest(rel=rel):
                self.assertEqual(self.post({"sub": rel, "selecionar": True}).status_code, 404)
        self.explorer.assert_not_called()
        self.abrir.assert_not_called()

    def test_selecao_de_diretorio_recusada(self):
        self.assertEqual(self.post({"sub": "03-relatorios", "selecionar": True}).status_code, 400)
        self.explorer.assert_not_called()
        self.abrir.assert_not_called()

    def test_erro_do_explorer_informado_ao_usuario(self):
        self.explorer.side_effect = OSError("Explorer indisponivel")
        r = self.post({"sub": self.docx, "selecionar": True})
        self.assertEqual(r.status_code, 400)
        self.assertIn("erro", r.json)

    def test_sem_permissao_sem_sessao_e_sem_csrf_bloqueados(self):
        self.s.auth.salvar_usuario("escrivao_ex01", "Ficticio", "escrivao", "Ficticia123")
        outro = self.s.app.test_client()
        self.assertEqual(outro.post(f"/api/casos/{self.id}/abrir", json={}, headers={"X-CPJ": "1"}).status_code, 401)
        outro.post("/api/entrar", json={"login": "escrivao_ex01", "senha": "Ficticia123"}, headers={"X-CPJ": "1"})
        self.assertEqual(outro.post(f"/api/casos/{self.id}/abrir", json={"sub": self.docx, "selecionar": True}, headers={"X-CPJ": "1"}).status_code, 403)
        self.assertEqual(self.client.post(f"/api/casos/{self.id}/abrir", json={"sub": self.docx, "selecionar": True}).status_code, 403)
        self.explorer.assert_not_called()
        self.abrir.assert_not_called()

    def test_ficha_informa_se_acesso_e_local(self):
        for ip, local in (("127.0.0.1", True), ("203.0.113.2", False)):
            with self.subTest(ip=ip):
                r = self.client.get(f"/api/casos/{self.id}", environ_overrides={"REMOTE_ADDR": ip})
                self.assertEqual(r.status_code, 200)
                self.assertIs(r.json.get("local"), local)


if __name__ == "__main__":
    unittest.main(verbosity=2)
