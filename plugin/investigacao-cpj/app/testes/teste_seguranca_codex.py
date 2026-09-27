"""Regressões C01/C02: python -X utf8 app/testes/teste_seguranca_codex.py.

Usa somente workspace temporário e dados fictícios; não inicia IA nem servidor de rede.
"""
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest


class SegurancaCPJ(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="cpj-seguranca-codex-")
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
        cls.numero = 0

    @classmethod
    def tearDownClass(cls):
        # Só excluir o diretório temporário criado por este teste. Uploads são readonly.
        for arquivo in cls.ws.rglob("*"):
            if arquivo.is_file(): arquivo.chmod(0o600)
        cls.temp.cleanup()
        if cls.env_anterior is None: os.environ.pop("CPJ_WORKSPACE", None)
        else: os.environ["CPJ_WORKSPACE"] = cls.env_anterior

    def setUp(self):
        type(self).numero += 1
        self.prefixo = f"t{self.numero}"
        self.criador = self.cadastrar("criador", "escrivao")
        self.outro = self.cadastrar("outro", "escrivao")
        self.os = f"{900 + self.numero}/2099"
        self.caso = self.s.C.novo(self.os, extras={
            "criado_por": self.criador, "determinacao": "ORIGINAL FICTICIA"
        })["id"]

    def cadastrar(self, sufixo, perfil, senha="SenhaFicticia123", **kw):
        login = f"{self.prefixo}_{sufixo}"
        self.s.auth.salvar_usuario(login, f"Usuario ficticio {login}", perfil, senha, **kw)
        return login

    def entrar(self, login, senha="SenhaFicticia123"):
        client = self.s.app.test_client()
        resposta = client.post("/api/entrar", json={"login": login, "senha": senha}, headers={"X-CPJ": "1"})
        self.assertEqual(resposta.status_code, 200)
        return client

    def post(self, client, url, **kw):
        return client.post(url, headers={"X-CPJ": "1"}, **kw)

    def test_escrivao_alheio_bloqueado_nas_duas_rotas_sem_gravar_upload(self):
        client = self.entrar(self.outro)
        pasta = Path(self.s.C.caminho(self.caso))
        antes = (pasta / "caso.json").read_bytes()
        fila = self.s.fila.qsize()
        self.assertEqual(self.post(client, f"/api/casos/{self.caso}", json={"determinacao": "NEGADA"}).status_code, 403)
        self.assertEqual(self.post(client, "/api/os", data={
            "os": self.os, "determinacao": "NEGADA", "arquivos": (io.BytesIO(b"ficticio"), "negado.md")
        }).status_code, 403)
        self.assertEqual((pasta / "caso.json").read_bytes(), antes)
        self.assertEqual(list((pasta / "00-originais").iterdir()), [])
        self.assertEqual(self.s.fila.qsize(), fila)

    def test_criador_pode_atualizar_e_acrescentar_documento(self):
        client = self.entrar(self.criador)
        r = self.post(client, "/api/os", data={
            "os": self.os, "determinacao": "NOVA FICTICIA", "arquivos": (io.BytesIO(b"documento ficticio"), "permitido.md")
        })
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json["recebidos"], ["permitido.md"])
        self.assertEqual(self.s.C.carregar(self.caso)["determinacao"], "NOVA FICTICIA")

    def test_delegado_e_investigador_mantem_acesso_permitido(self):
        for perfil in ("delegado", "investigador"):
            client = self.entrar(self.cadastrar(perfil, perfil))
            self.assertEqual(self.post(client, "/api/os", data={"os": self.os, "determinacao": perfil}).status_code, 200)
            self.assertEqual(self.post(client, f"/api/casos/{self.caso}", json={"determinacao": perfil}).status_code, 200)

    def test_redefinicao_por_admin_revoga_cookie_antigo(self):
        client = self.entrar(self.criador)
        admin = self.entrar(self.cadastrar("admin", "admin"))
        r = self.post(admin, "/api/usuarios", json={
            "login": self.criador, "nome": "Usuario ficticio", "perfil": "escrivao", "senha": "NovaFicticia123"
        })
        self.assertEqual(r.status_code, 200)
        self.assertEqual(client.get("/api/casos").status_code, 401)
        self.assertIsNone(client.get("/api/sessao").json["usuario"])
        self.assertEqual(self.entrar(self.criador, "NovaFicticia123").get("/api/casos").status_code, 200)

    def test_troca_propria_preserva_sessao_atual_e_revoga_outra(self):
        atual, outra = self.entrar(self.criador), self.entrar(self.criador)
        r = self.post(atual, "/api/minha-senha", json={"atual": "SenhaFicticia123", "nova": "NovaFicticia123"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(atual.get("/api/casos").status_code, 200)
        self.assertEqual(outra.get("/api/casos").status_code, 401)

    def test_senha_temporaria_exige_troca(self):
        login = self.cadastrar("temporario", "escrivao", "123", temporaria=True)
        client = self.entrar(login, "123")
        self.assertEqual(client.get("/api/casos").status_code, 428)
        self.assertEqual(self.post(client, "/api/minha-senha", json={"atual": "123", "nova": "NovaFicticia123"}).status_code, 200)
        self.assertEqual(client.get("/api/casos").status_code, 200)
        self.assertFalse(client.get("/api/sessao").json["usuario"]["trocar_senha"])

    def test_desativar_e_reativar_nao_restaura_cookie(self):
        client = self.entrar(self.criador)
        self.s.auth.salvar_usuario(self.criador, "Ficticio", "escrivao", ativo=False)
        self.s.auth.salvar_usuario(self.criador, "Ficticio", "escrivao", ativo=True)
        self.assertEqual(client.get("/api/casos").status_code, 401)

    def test_remover_e_recriar_nao_restaura_cookie(self):
        client = self.entrar(self.criador)
        self.s.auth.remover_usuario(self.criador)
        self.s.auth.salvar_usuario(self.criador, "Ficticio", "escrivao", "SenhaFicticia123")
        self.assertEqual(client.get("/api/casos").status_code, 401)

    def test_contato_nao_revoga_sessao_nem_expoe_token(self):
        client = self.entrar(self.criador)
        r = self.post(client, "/api/minha-conta", json={"email": f"{self.prefixo}@exemplo.invalid", "cargo": "Ficticio"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(client.get("/api/casos").status_code, 200)
        for dados in (r.json, client.get("/api/sessao").json["usuario"], self.s.auth.listar()[0]):
            self.assertTrue({"sessao_id", "_sessao_id", "hash", "sal"}.isdisjoint(dados))

    def test_usuario_legado_migra_no_login_e_cookie_sem_vinculo_expira(self):
        dados = self.s.auth._ler()
        dados["usuarios"][self.criador].pop("sessao_id")
        self.s.auth._gravar(dados)
        legado = self.s.app.test_client()
        with legado.session_transaction() as sessao: sessao["u"] = self.criador
        self.assertEqual(legado.get("/api/casos").status_code, 401)
        self.assertEqual(self.entrar(self.criador).get("/api/casos").status_code, 200)

    def test_ultimo_admin_ativo_protegido_mesmo_com_admin_inativo(self):
        # Teste em cadastro separado para não depender dos admins de outros métodos.
        from auth import Auth
        with tempfile.TemporaryDirectory(prefix="cpj-admin-ficticio-") as ws:
            auth = Auth(ws)
            auth.salvar_usuario("ativo", "Ficticio", "admin", "SenhaFicticia123")
            auth.salvar_usuario("inativo", "Ficticio", "admin", "SenhaFicticia123", ativo=False)
            with self.assertRaises(ValueError): auth.remover_usuario("ativo")
            with self.assertRaises(ValueError): auth.salvar_usuario("ativo", "Ficticio", "escrivao")
            with self.assertRaises(ValueError): auth.salvar_usuario("ativo", "Ficticio", "admin", ativo=False)
            auth.remover_usuario("inativo")
            self.assertIsNotNone(auth.obter("ativo"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
