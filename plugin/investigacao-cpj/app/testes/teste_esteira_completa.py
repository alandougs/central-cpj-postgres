#!/usr/bin/env python3
"""Suíte de testes da Esteira Completa 1-Clique (Tarefa EC01).

Valida:
1. Registro da ação 'esteira' e orquestração de squad em plantao.py.
2. Rota HTTP POST /api/casos/<id>/esteira (permissões, validação de caso, enfileiramento).
3. Sequenciamento das etapas assíncronas (analisar -> financeiro -> relatorio -> revisar).
4. Pós-processamento com garantia de DOCX e reindexação RAG.
5. Presença do botão visual da Esteira Completa 1-Clique na interface index.html.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(AQUI)
PLUGIN = os.path.dirname(APP_DIR)
RAIZ = os.path.dirname(os.path.dirname(PLUGIN))
S_BASE = os.path.join(PLUGIN, "skills", "base-cpj", "scripts")

sys.path.insert(0, S_BASE)
sys.path.insert(0, APP_DIR)

from plantao import ACOES, Plantao, pos_processar  # noqa: E402
import caso as C  # noqa: E402
from auth import Auth  # noqa: E402
from tarefas import Tarefas  # noqa: E402
import rotas.comum as comum  # noqa: E402
import servidor  # noqa: E402


class TesteEsteiraCompleta(unittest.TestCase):
    def setUp(self):
        self.orig_ws = C.WS
        self.orig_casos = C.CASOS
        self.orig_modelo = C.MODELO
        self.orig_env = os.environ.get("CPJ_WORKSPACE")

        self.tmp = tempfile.mkdtemp(prefix="cpj-teste-ec01-")
        os.environ["CPJ_WORKSPACE"] = self.tmp
        os.environ["CPJ_SEM_AGENTE_EMBUTIDO"] = "1"
        os.makedirs(os.path.join(self.tmp, "casos"), exist_ok=True)
        C.WS = self.tmp
        C.CASOS = os.path.join(self.tmp, "casos")
        C.MODELO = os.path.join(RAIZ, "casos", "_MODELO-CASO")
        self.auth = Auth(self.tmp)
        self.auth.salvar_usuario("investigador.teste", "Investigador Teste", "investigador", "SenhaForte123!")
        self.auth.salvar_usuario("delegado.teste", "Delegado Teste", "delegado", "SenhaForte123!")
        self.pl = Plantao(self.tmp)

        # Configura cliente de teste do Flask e rotas compartilhadas
        comum._auth_inst = self.auth
        comum.WS = self.tmp
        comum.C = C
        comum._tarefas_inst = Tarefas(self.tmp, C, self.auth, iniciar_agente=False)

        servidor.WS = self.tmp
        servidor.C = C
        servidor.auth = self.auth
        servidor.tarefas = comum._tarefas_inst
        servidor.app.config["TESTING"] = True
        servidor.app.config["SECRET_KEY"] = "segredo-teste-ec01"
        self.client = servidor.app.test_client()

    def tearDown(self):
        C.WS = self.orig_ws
        C.CASOS = self.orig_casos
        C.MODELO = self.orig_modelo
        if self.orig_env is not None:
            os.environ["CPJ_WORKSPACE"] = self.orig_env
        else:
            os.environ.pop("CPJ_WORKSPACE", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _login(self, login, senha="SenhaForte123!"):
        return self.client.post("/api/entrar", json={"login": login, "senha": senha}, headers={"X-CPJ": "1"})

    def test_01_registro_acao_esteira(self):
        """Ação 'esteira' deve estar devidamente catalogada em ACOES com descrição completa."""
        self.assertIn("esteira", ACOES)
        titulo, tarefa, marcos = ACOES["esteira"]
        self.assertIn("Esteira Completa", titulo)
        self.assertIn("100", marcos)

    def test_02_enfileiramento_squad_esteira(self):
        """Enfileirar 'esteira' deve gerar o fluxo sequencial completo com todas as etapas."""
        caso_id = "OS-101-2026"
        c = C.novo(os_num="101/2026", id_=caso_id)
        pid = self.pl.enfileirar(caso_id, "esteira", "investigador.teste", "Caso prioritário")
        self.assertTrue(pid.startswith("ia-"))

        pedidos = self.pl.pedidos()
        # Deve ter gerado 4 etapas sequenciais ligadas por grupo
        pedidos_caso = [p for p in pedidos if p["caso"] == caso_id]
        self.assertEqual(len(pedidos_caso), 4)

        acoes_esperadas = ["analisar", "financeiro", "relatorio", "revisar"]
        acoes_geradas = [p["acao"] for p in sorted(pedidos_caso, key=lambda x: x.get("ordem") or 0)]
        self.assertEqual(acoes_geradas, acoes_esperadas)

        # Primeira etapa deve estar pendente aguardando agente; demais aguardando etapa anterior
        pri = pedidos_caso[0]
        self.assertIn("aguardando agente", pri["etapa"])
        self.assertIsNone(pri["depende_de"])

        seg = pedidos_caso[1]
        self.assertEqual(seg["depende_de"], pri["id"])

    def test_03_bloqueio_duplicidade_caso(self):
        """Não pode permitir enfileirar nova IA se já houver esteira em andamento para o caso."""
        caso_id = "OS-102-2026"
        C.novo(os_num="102/2026", id_=caso_id)
        self.pl.enfileirar(caso_id, "esteira", "investigador.teste")

        with self.assertRaises(ValueError) as ctx:
            self.pl.enfileirar(caso_id, "esteira", "investigador.teste")
        self.assertIn("Já existe uma tarefa de IA em andamento", str(ctx.exception))

    def test_04_rota_http_esteira(self):
        """Valida rota POST /api/casos/<id>/esteira via cliente HTTP com controle de acesso."""
        caso_id = "OS-103-2026"
        C.novo(os_num="103/2026", id_=caso_id)

        # Não autenticado -> 401
        res = self.client.post(f"/api/casos/{caso_id}/esteira", json={}, headers={"X-CPJ": "1"})
        self.assertEqual(res.status_code, 401)

        # Logado como delegado (por padrão não tem perm 'ia' sem alteração) -> 403
        self._login("delegado.teste")
        res_del = self.client.post(f"/api/casos/{caso_id}/esteira", json={}, headers={"X-CPJ": "1"})
        self.assertEqual(res_del.status_code, 403)

        # Logado como investigador -> 200
        self._login("investigador.teste")
        res_inv = self.client.post(
            f"/api/casos/{caso_id}/esteira",
            json={"observacoes": "Esteira teste"},
            headers={"X-CPJ": "1"},
        )
        self.assertEqual(res_inv.status_code, 200)
        dados = res_inv.get_json()
        self.assertTrue(dados["ok"])
        self.assertEqual(dados["caso"], caso_id)
        self.assertIn("tarefa", dados)
        self.assertIn("etapas", dados)

        # Caso inexistente -> 404
        res_404 = self.client.post("/api/casos/OS-999-9999/esteira", json={}, headers={"X-CPJ": "1"})
        self.assertEqual(res_404.status_code, 404)

    def test_05_pos_processamento_esteira(self):
        """pos_processar com acao 'esteira' deve assegurar geração do DOCX e índice."""
        caso_id = "OS-104-2026"
        C.novo(os_num="104/2026", id_=caso_id)
        pasta_rel = os.path.join(self.tmp, "casos", caso_id, "03-relatorios")
        os.makedirs(pasta_rel, exist_ok=True)
        # Cria uma minuta simples
        minuta_path = os.path.join(pasta_rel, "minuta-v01.md")
        with open(minuta_path, "w", encoding="utf-8") as f:
            f.write("# RELATÓRIO DE INVESTIGAÇÃO\n\nResumo dos fatos.\n")

        resultado = pos_processar(self.tmp, caso_id, "esteira")
        self.assertIn("minuta", resultado)
        self.assertEqual(resultado["minuta"], "minuta-v01.md")
        self.assertIn("docx", resultado)
        self.assertEqual(resultado["docx"], f"RELATORIO-{caso_id}-v01.docx")
        self.assertTrue(os.path.exists(os.path.join(pasta_rel, f"RELATORIO-{caso_id}-v01.docx")))

    def test_06_botao_na_interface(self):
        """index.html deve conter o botão visual da Esteira Completa 1-Clique."""
        index_path = os.path.join(APP_DIR, "static", "index.html")
        self.assertTrue(os.path.exists(index_path))
        with open(index_path, "r", encoding="utf-8") as f:
            conteudo = f.read()

        self.assertIn('data-ia="esteira"', conteudo)
        self.assertIn("Esteira Completa 1-Clique", conteudo)


if __name__ == "__main__":
    unittest.main()
