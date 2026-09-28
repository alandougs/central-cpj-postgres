#!/usr/bin/env python3
"""Testes de modularização de rotas (A01) para a Central CPJ."""
import os
import shutil
import sys
import tempfile
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(AQUI)
PLUGIN_DIR = os.path.dirname(APP_DIR)
sys.path.insert(0, os.path.join(PLUGIN_DIR, "skills", "base-cpj", "scripts"))
sys.path.insert(0, APP_DIR)


class TesteModularizacao(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="cpj-teste-mod-")
        cls.tmp = cls.temp.name
        cls.env_anterior = os.environ.get("CPJ_WORKSPACE")
        os.environ["CPJ_WORKSPACE"] = cls.tmp
        for pasta in ("config", "usuarios", "casos", "producao", "exportacoes", "modelos"):
            os.makedirs(os.path.join(cls.tmp, pasta), exist_ok=True)

        modelo = os.path.join(cls.tmp, "casos", "_MODELO-CASO")
        for pasta in ("00-originais", "01-extracao", "02-analise", "03-relatorios"):
            os.makedirs(os.path.join(modelo, pasta), exist_ok=True)
        with open(os.path.join(modelo, "caso.json"), "w", encoding="utf-8") as f:
            f.write('{"datas": {}, "financeiro": {}, "ip": {}, "resultado": {}, "relatorios": []}')

        import servidor as S
        cls.servidor = S
        cls.app = S.app
        cls.app.config.update(TESTING=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()
        if cls.env_anterior is None:
            os.environ.pop("CPJ_WORKSPACE", None)
        else:
            os.environ["CPJ_WORKSPACE"] = cls.env_anterior

    def setUp(self):
        self.client = self.app.test_client()

    def test_01_blueprints_registrados(self):
        """Todos os 5 blueprints modulares devem estar registrados no app."""
        esperados = {"usuarios", "casos", "relatorios", "consulta", "sistema"}
        registrados = set(self.app.blueprints.keys())
        self.assertTrue(esperados.issubset(registrados), f"Faltando blueprints: {esperados - registrados}")

    def test_02_rotas_mapeadas_sem_alteracao_de_url(self):
        """Verifica se todas as URLs essenciais estão mapeadas com seus respectivos métodos."""
        regras = {}
        for r in self.app.url_map.iter_rules():
            metodos = {m for m in r.methods if m not in ("HEAD", "OPTIONS")}
            regras.setdefault(r.rule, set()).update(metodos)

        rotas_obrigatorias = {
            "/": {"GET"},
            "/painel": {"GET"},
            "/api/sessao": {"GET"},
            "/api/configurar": {"POST"},
            "/api/entrar": {"POST"},
            "/api/minha-conta": {"POST"},
            "/api/sair": {"POST"},
            "/api/minha-senha": {"POST"},
            "/api/usuarios": {"GET", "POST"},
            "/api/usuarios/<login>/remover": {"POST"},
            "/api/auditoria": {"GET"},
            "/api/perfis": {"GET", "POST"},
            "/api/responsaveis": {"GET"},
            "/api/minha-pasta": {"GET"},
            "/minha-pasta/<path:rel>": {"GET"},
            "/api/minha-pasta/abrir": {"POST"},
            "/api/rede": {"GET", "POST"},
            "/api/pendencias": {"GET"},
            "/api/casos": {"GET"},
            "/api/casos/<id_>": {"GET", "POST"},
            "/api/os/detectar": {"POST"},
            "/api/os/ia-local": {"GET", "POST"},
            "/api/os": {"POST"},
            "/api/casos/<id_>/reprocessar/<doc>": {"POST"},
            "/api/casos/<id_>/baixa": {"POST"},
            "/api/casos/<id_>/abrir": {"POST"},
            "/arquivo/<id_>/<path:rel>": {"GET"},
            "/api/fila": {"GET"},
            "/api/casos/<id_>/minuta": {"GET", "POST"},
            "/api/casos/<id_>/docx": {"POST"},
            "/api/casos/<id_>/pdf": {"POST"},
            "/api/casos/<id_>/final": {"POST"},
            "/api/consulta/bases": {"GET"},
            "/api/consulta/importar": {"POST"},
            "/api/consulta/colar": {"POST"},
            "/api/vinculos": {"GET"},
            "/api/consulta/bases/<bid>/remover": {"POST"},
            "/api/referencias": {"GET"},
            "/api/referencias/importar": {"POST"},
            "/api/referencias/<rid>": {"POST"},
            "/api/referencias/<rid>/remover": {"POST"},
            "/api/pesquisa/pessoas": {"GET"},
            "/api/busca": {"GET"},
            "/api/cruzar/<id_>": {"GET"},
            "/api/ia/status": {"GET"},
            "/api/ia/login": {"POST"},
            "/api/casos/<id_>/ia": {"POST"},
            "/api/plantao/agentes": {"GET"},
            "/api/plantao/agentes/<nome>/aprovacao": {"POST"},
            "/api/tarefas": {"GET"},
            "/api/tarefas/<tid>/cancelar": {"POST"},
            "/api/exportar": {"POST"},
            "/api/exportacoes": {"GET"},
            "/exportacoes/<nome>": {"GET"},
            "/api/planilha": {"GET"},
            "/api/importar": {"POST"},
            "/api/sistema": {"GET"},
        }

        for rota, metodos_esperados in rotas_obrigatorias.items():
            self.assertIn(rota, regras, f"Rota ausente no url_map: {rota}")
            self.assertTrue(
                metodos_esperados.issubset(regras[rota]),
                f"Métodos incorretos para rota {rota}: esperado {metodos_esperados}, obtido {regras[rota]}",
            )

    def test_03_protecao_csrf_global(self):
        """Qualquer POST sem cabeçalho X-CPJ: 1 deve receber 403."""
        r = self.client.post("/api/entrar", json={"login": "x", "senha": "y"})
        self.assertEqual(r.status_code, 403)

        r2 = self.client.post("/api/entrar", json={"login": "x", "senha": "y"}, headers={"X-CPJ": "1"})
        self.assertNotEqual(r2.status_code, 403)

    def test_04_cabecalhos_seguranca_depois_do_request(self):
        """Todas as respostas devem incluir os cabeçalhos de segurança configurados no after_request."""
        r = self.client.get("/api/sessao")
        self.assertEqual(r.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(r.headers.get("X-Frame-Options"), "SAMEORIGIN")
        self.assertEqual(r.headers.get("Referrer-Policy"), "no-referrer")
        self.assertEqual(r.headers.get("Cache-Control"), "no-store")

    def test_05_fluxo_autenticacao_e_permissoes(self):
        """Verifica endpoints de sessão, configuração inicial de admin e permissões."""
        # 1. Sessão inicial sem usuários
        r = self.client.get("/api/sessao")
        self.assertEqual(r.status_code, 200)
        dados = r.get_json()
        self.assertFalse(dados["configurado"])
        self.assertIsNone(dados["usuario"])

        # 2. Configurar admin inicial
        r_cfg = self.client.post(
            "/api/configurar",
            json={"login": "admin_teste", "nome": "Admin Teste", "senha": "senha-segura-123"},
            headers={"X-CPJ": "1"},
        )
        self.assertEqual(r_cfg.status_code, 200)

        # 3. Sessão agora autenticada
        r_sess = self.client.get("/api/sessao")
        self.assertEqual(r_sess.status_code, 200)
        self.assertTrue(r_sess.get_json()["configurado"])
        self.assertEqual(r_sess.get_json()["usuario"]["login"], "admin_teste")

        # 4. Acesso a endpoint protegido por admin
        r_usr = self.client.get("/api/usuarios")
        self.assertEqual(r_usr.status_code, 200)
        logins = [u["login"] for u in r_usr.get_json()]
        self.assertIn("admin_teste", logins)

    def test_06_compatibilidade_simbolos_servidor(self):
        """Garante que servidor.py continue reexportando todos os símbolos esperados."""
        esperados = [
            "WS", "app", "auth", "tarefas", "trabalhador", "C", "Q", "R", "D_OS", "RF",
            "Auth", "fila", "trava", "resumo", "visiveis", "arvore", "arquivos_relatorio",
            "ler_minuta", "CAMPOS_MINUTA", "ultima_minuta", "salvar_upload"
        ]
        for s in esperados:
            self.assertTrue(hasattr(self.servidor, s), f"Símbolo {s} não reexportado por servidor.py")


if __name__ == "__main__":
    unittest.main()
