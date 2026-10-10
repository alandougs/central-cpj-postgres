#!/usr/bin/env python3
"""Regressões da API do grafo, exclusivamente com cadastro e SQLite fictícios."""
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch


class GrafoAPIGF01(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="cpj-grafo-gf01-")
        cls.ws = Path(cls.temp.name)
        cls.env = {k: os.environ.get(k) for k in ("CPJ_WORKSPACE", "CPJ_SEM_AGENTE_EMBUTIDO")}
        os.environ["CPJ_WORKSPACE"] = str(cls.ws)
        os.environ["CPJ_SEM_AGENTE_EMBUTIDO"] = "1"
        for numero in (10, 2, 3):
            pasta = cls.ws / "casos" / f"OS-{numero}-2099"
            pasta.mkdir(parents=True)
            (pasta / "caso.json").write_text(json.dumps({
                "id": pasta.name, "ordem_servico": f"{numero}/2099", "status": "recebido",
                "vitimas": ["Nome cadastral fictício que não deve sair nos metadados"],
            }), encoding="utf-8")
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        import servidor
        import rotas.consulta as consulta
        cls.s = servidor
        cls.consulta = consulta
        assert Path(servidor.WS).resolve() == cls.ws.resolve(), "Execute em processo isolado."
        cls.s.app.config.update(TESTING=True)
        (cls.ws / "rag").mkdir()
        cls.db_path = cls.ws / "rag" / "cpj.sqlite"
        db = sqlite3.connect(cls.db_path)
        db.executescript("""
            CREATE TABLE arestas(a_tipo TEXT,a_valor TEXT,b_tipo TEXT,b_valor TEXT,
                                 relacao TEXT,origem TEXT,fonte TEXT,localizador TEXT);
            CREATE TABLE rotulos(tipo TEXT,valor TEXT,rotulo TEXT,PRIMARY KEY(tipo,valor));
        """)
        for numero, cpf in ((2, "11111111111"), (10, "22222222222")):
            fonte = f"OS-{numero}-2099"
            pessoa = f"P:ficticio-{numero}"
            for tipo, valor, relacao in (
                ("NOME", "ana ficticia", "nome (homônimos possíveis — conferir)"),
                ("CPF", cpf, "CPF conforme fonte fictícia"),
                ("CASO", fonte, "vítima"),
            ):
                db.execute("INSERT INTO arestas VALUES(?,?,?,?,?,?,?,?)",
                           ("PESSOA", pessoa, tipo, valor, relacao, "caso", fonte, "pág. 1 fictícia"))
            db.execute("INSERT INTO rotulos VALUES(?,?,?)", ("PESSOA", pessoa, f"Registro fictício {numero}"))
        for a_tipo, a, b_tipo, b, relacao in (
            ("PESSOA", "P:ficticio-2", "CONTA", "banco ficticio|001234", "titular conforme autos fictícios"),
            ("CONTA", "banco ficticio|001234", "CHAVE_PIX", "chave@pix.invalid", "chave Pix vinculada"),
            ("PESSOA", "P:ficticio-2", "TELEFONE", "18999990000", "telefone"),
        ):
            db.execute("INSERT INTO arestas VALUES(?,?,?,?,?,?,?,?)",
                       (a_tipo, a, b_tipo, b, relacao, "caso", "OS-2-2099", "pág. 2 fictícia"))
        db.execute("INSERT INTO rotulos VALUES(?,?,?)", ("CONTA", "banco ficticio|001234", "Banco Ficticio 001234"))
        db.commit()
        cls.num_arestas = db.execute("SELECT count(*) FROM arestas").fetchone()[0]
        db.close()

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()
        for nome, valor in cls.env.items():
            if valor is None:
                os.environ.pop(nome, None)
            else:
                os.environ[nome] = valor

    def setUp(self):
        self.cliente = self.s.app.test_client()
        self.auth = patch("rotas.comum.usuario", return_value={"login": "ficticio", "perfil": "investigador"})
        self.auth.start()
        self.addCleanup(self.auth.stop)

    def grafo(self, **parametros):
        resposta = self.cliente.get("/api/grafo", query_string=parametros)
        self.assertEqual(resposta.status_code, 200)
        return resposta.get_json()

    @staticmethod
    def pessoas(g):
        return {n["valor"] for n in g["nos"] if n["tipo"] == "PESSOA"}

    def test_metadados_vem_do_cadastro_em_ordem_numerica(self):
        g = self.grafo()
        self.assertEqual(g["casos"], ["OS-2-2099", "OS-3-2099", "OS-10-2099"])
        self.assertEqual(g["ordens_servico"], [
            {"id": "OS-2-2099", "ordem_servico": "2/2099"},
            {"id": "OS-3-2099", "ordem_servico": "3/2099"},
            {"id": "OS-10-2099", "ordem_servico": "10/2099"},
        ])
        self.assertTrue(g["indice_disponivel"])
        self.assertNotIn("Nome cadastral", json.dumps(g))

    def test_caso_sem_arestas_continua_selecionavel(self):
        g = self.grafo(caso="OS-3-2099")
        self.assertIn("OS-3-2099", g["casos"])
        self.assertEqual(g["nos"], [])
        self.assertEqual(g["arestas"], [])
        self.assertTrue(g["indice_disponivel"])

    def test_nome_parcial_com_acento_e_homonimos_separados(self):
        g = self.grafo(q="Ána")
        self.assertEqual(self.pessoas(g), {"P:ficticio-2", "P:ficticio-10"})
        self.assertGreater(len(g["arestas"]), 0)

    def test_cpf_formatado_e_parcial_encontram_registro_sem_fundir_homonimo(self):
        for termo in ("111.111.111-11", "111111"):
            with self.subTest(termo=termo):
                g = self.grafo(q=termo)
                self.assertEqual(self.pessoas(g), {"P:ficticio-2"})

    def test_conta_por_digitos_parciais_ou_rotulo(self):
        for termo in ("1234", "Banco Ficticio"):
            with self.subTest(termo=termo):
                g = self.grafo(q=termo)
                self.assertIn("banco ficticio|001234", {n["valor"] for n in g["nos"]})
                self.assertGreater(len(g["arestas"]), 0)

    def test_pix_e_telefone_por_identificador_parcial(self):
        for termo, valor in (("@pix.invalid", "chave@pix.invalid"), ("999990000", "18999990000")):
            with self.subTest(termo=termo):
                g = self.grafo(q=termo)
                self.assertIn(valor, {n["valor"] for n in g["nos"]})

    def test_busca_com_caso_respeita_ambos_filtros(self):
        g = self.grafo(q="ana", caso="OS-2-2099")
        self.assertEqual(self.pessoas(g), {"P:ficticio-2"})
        self.assertTrue(all(a["fonte"] == "OS-2-2099" for a in g["arestas"]))
        self.assertEqual(self.grafo(q="222222", caso="OS-2-2099")["arestas"], [])
        self.assertEqual(self.grafo(q="ana", caso="OS-3-2099")["nos"], [])

    def test_busca_sem_resultados_nao_cria_nos_nem_vinculos(self):
        for termo in ("zzzz-ficticio-inexistente", "%", "' OR 1=1 --"):
            with self.subTest(termo=termo):
                g = self.grafo(q=termo)
                self.assertEqual(g["nos"], [])
                self.assertEqual(g["arestas"], [])
        db = sqlite3.connect(self.db_path)
        self.assertEqual(db.execute("SELECT count(*) FROM arestas").fetchone()[0], self.num_arestas)
        db.close()

    def test_sem_indice_informa_indisponibilidade_e_lista_os(self):
        with patch.object(self.consulta.R, "conectar", side_effect=FileNotFoundError):
            g = self.grafo(caso="OS-3-2099")
        self.assertFalse(g["indice_disponivel"])
        self.assertEqual(g["casos"], ["OS-2-2099", "OS-3-2099", "OS-10-2099"])
        self.assertEqual(g["arestas"], [])

    def test_indice_antigo_sem_schema_grafo_informa_indisponibilidade(self):
        incompleto = self.ws / "rag" / "incompleto.sqlite"
        sqlite3.connect(incompleto).close()
        with patch.object(self.consulta.R, "DB", str(incompleto)):
            g = self.grafo()
        self.assertFalse(g["indice_disponivel"])
        self.assertEqual(len(g["ordens_servico"]), 3)

    def test_grafo_preserva_autorizacao_por_perfil(self):
        with patch("rotas.comum.usuario", return_value={"login": "ficticio", "perfil": "escrivao"}):
            self.assertEqual(self.cliente.get("/api/grafo").status_code, 403)
        with patch("rotas.comum.usuario", return_value=None):
            self.assertEqual(self.cliente.get("/api/grafo").status_code, 401)


if __name__ == "__main__":
    unittest.main(verbosity=2)
