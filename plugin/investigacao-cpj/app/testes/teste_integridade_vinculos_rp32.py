#!/usr/bin/env python3
"""RP32: integridade do índice/grafo com fontes exclusivamente sintéticas em TEMP."""
import csv
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "plugin/investigacao-cpj/skills/base-cpj/scripts"


class IntegridadeVinculosRP32(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="cpj-rp32-")
        cls.ws = Path(cls.tmp.name)
        cls.env = patch.dict(os.environ, {"CPJ_WORKSPACE": str(cls.ws), "CPJ_SEM_AGENTE_EMBUTIDO": "1"})
        cls.env.start()
        (cls.ws / "modelos").mkdir()
        for numero in (1, 2):
            caso = cls.ws / "casos" / f"OS-{numero}-2099"
            (caso / "01-extracao/doc").mkdir(parents=True)
            (caso / "02-analise").mkdir()
            (caso / "caso.json").write_text(json.dumps({
                "id": caso.name, "status": "recebido", "ordem_servico": f"{numero}/2099",
            }), encoding="utf-8")
        sys.path.insert(0, str(ROOT / "plugin/investigacao-cpj/app"))
        import servidor
        import rotas.consulta as consulta
        cls.s = servidor
        cls.r = consulta.R
        assert Path(servidor.WS).resolve() == cls.ws.resolve(), "Execute em processo isolado."
        cls.s.app.config.update(TESTING=True)

    @classmethod
    def tearDownClass(cls):
        cls.env.stop()
        cls.tmp.cleanup()

    def setUp(self):
        self.csv_ent(1, [])
        self.csv_ent(2, [])
        for path in (self.ws / "casos").glob("*/01-extracao/doc/transcricao.md"):
            path.unlink()
        self.indexar()

    def csv_ent(self, numero, rows):
        path = self.ws / "casos" / f"OS-{numero}-2099/01-extracao/doc/entidades.csv"
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["tipo", "valor", "pagina_pdf", "trecho"], delimiter=";")
            writer.writeheader()
            writer.writerows(rows)

    def indexar(self):
        result = subprocess.run([sys.executable, str(BASE / "indexar.py"), "--tudo"],
                                capture_output=True, text=True, env=dict(os.environ), timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_vinculo_manual_e_rotulo_persistem_apos_reindexacao(self):
        cliente = self.s.app.test_client()
        with patch("rotas.comum.usuario", return_value={"login": "investigador-ficticio", "perfil": "investigador"}):
            response = cliente.post("/api/grafo/vinculo", headers={"X-CPJ": "1"}, json={
                "caso": "OS-1-2099", "a_tipo": "EMAIL", "a_valor": "a@example.invalid",
                "b_tipo": "EMAIL", "b_valor": "b@example.invalid", "relacao": "vínculo sintético conferido",
                "obs": "Fls. 4 sintética", "a_rotulo": "Rótulo manual sintético",
            })
        self.assertEqual(response.status_code, 200, response.get_json())
        before = self.r.vinculos("EMAIL", "a@example.invalid")
        self.assertEqual(len(before["arestas"]), 1)
        self.indexar()
        after = self.r.vinculos("EMAIL", "a@example.invalid")
        self.assertEqual(after, before, "A reindexação apagou vínculo/rótulo confirmado pela API.")

    def test_cruzar_nao_associa_identificadores_de_tipos_distintos(self):
        self.csv_ent(1, [{"tipo": "CPF", "valor": "111.222.333-44", "pagina_pdf": "1"}])
        self.csv_ent(2, [{"tipo": "TELEFONE", "valor": "(11) 12223-3344", "pagina_pdf": "2"}])
        self.indexar()
        self.assertEqual(self.r.cruzar("OS-1-2099"), [], "CPF e telefone coincidentes não constituem o mesmo identificador.")

    def test_identificador_incerto_nao_cria_coincidencia_exata(self):
        for numero in (1, 2):
            self.csv_ent(numero, [{"tipo": "CPF", "valor": "111.222.33?-44 [dígito incerto]", "pagina_pdf": str(numero)}])
        self.indexar()
        self.assertEqual(self.r.cruzar("OS-1-2099"), [], "Remover '?' fabricou coincidência exata de CPF incompleto.")

    def test_remocao_manual_nao_apaga_aresta_documental(self):
        row = ("EMAIL", "origem@example.invalid", "EMAIL", "destino@example.invalid", "relação documental")
        with closing(sqlite3.connect(self.ws / "rag/cpj.sqlite")) as db:
            db.execute("INSERT INTO arestas VALUES(?,?,?,?,?,'caso','OS-1-2099','Fls. 5 sintética')", row)
            db.commit()
        with patch("rotas.comum.usuario", return_value={"login": "investigador-ficticio", "perfil": "investigador"}):
            response = self.s.app.test_client().post("/api/grafo/vinculo/remover", headers={"X-CPJ": "1"},
                json=dict(zip(("a_tipo", "a_valor", "b_tipo", "b_valor", "relacao"), row)))
        with closing(sqlite3.connect(self.ws / "rag/cpj.sqlite")) as db:
            count = db.execute("SELECT count(*) FROM arestas WHERE origem='caso' AND relacao=?", (row[4],)).fetchone()[0]
        self.assertEqual(count, 1, "Remover anotação manual apagou vínculo derivado de documento.")

    def test_grafo_nao_normaliza_cpf_incerto_como_identidade_exata(self):
        self.csv_ent(1, [{"tipo": "CPF", "valor": "111.222.33?-44 [dígito incerto]", "pagina_pdf": "1"}])
        self.indexar()
        with closing(sqlite3.connect(self.ws / "rag/cpj.sqlite")) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM arestas WHERE b_tipo='CPF'").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT valor FROM entidades WHERE tipo='CPF'").fetchone()[0],
                             "111.222.33?-44 [dígito incerto]")

    def test_exclusao_manual_e_duravel_e_preserva_documental_identica(self):
        import vinculos_manuais as VM
        row = ("EMAIL", "remover@example.invalid", "EMAIL", "destino@example.invalid", "relação igual sintética")
        payload = dict(zip(("a_tipo", "a_valor", "b_tipo", "b_valor", "relacao"), row), caso="OS-1-2099")
        cliente = self.s.app.test_client()
        with patch("rotas.comum.usuario", return_value={"login": "investigador-ficticio", "perfil": "investigador"}):
            criado = cliente.post("/api/grafo/vinculo", headers={"X-CPJ": "1"}, json=payload)
            self.assertEqual(criado.status_code, 200, criado.get_json())
            registro = criado.get_json()
            outro = cliente.post("/api/grafo/vinculo", headers={"X-CPJ": "1"}, json={**payload, "caso":"OS-2-2099"})
            self.assertEqual(outro.status_code, 200, outro.get_json())
            with closing(sqlite3.connect(self.ws / "rag/cpj.sqlite")) as db:
                db.execute("INSERT INTO arestas VALUES(?,?,?,?,?,'caso','OS-1-2099','Fls. 5 sintética')", row)
                db.commit()
            remover = {"id":registro["id"], "caso":payload["caso"], "versao":registro["versao"]}
            self.assertEqual(cliente.post("/api/grafo/vinculo/remover", headers={"X-CPJ":"1"}, json=payload).status_code, 400,
                             "Payload legado ambíguo não deve voltar ao contrato.")
            self.assertEqual(cliente.post("/api/grafo/vinculo/remover", headers={"X-CPJ":"1"}, json={**remover, "caso":"OS-2-2099"}).status_code, 404)
            self.assertEqual(cliente.post("/api/grafo/vinculo/remover", headers={"X-CPJ":"1"}, json={**remover, "versao":registro["versao"]+1}).status_code, 409)
            resposta = cliente.post("/api/grafo/vinculo/remover", headers={"X-CPJ":"1"}, json=remover)
        self.assertEqual(resposta.status_code, 200, resposta.get_json())
        vivos = [r for r in VM.listar(self.ws) if r["relacao"] == row[4]]
        self.assertEqual([(r["caso"],r["a_valor"],r["b_valor"]) for r in vivos], [("OS-2-2099",row[1],row[3])])
        with closing(sqlite3.connect(self.ws / "rag/cpj.sqlite")) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM arestas WHERE origem='caso' AND relacao=?", (row[4],)).fetchone()[0], 1)
        self.indexar()
        with closing(sqlite3.connect(self.ws / "rag/cpj.sqlite")) as db:
            restantes = db.execute("SELECT fonte,a_valor,b_valor FROM arestas WHERE origem='manual' AND relacao=?", (row[4],)).fetchall()
            self.assertEqual(restantes, [("OS-2-2099",row[1],row[3])])

    def test_mesmo_identificador_completo_conserva_cruzamento_e_fontes(self):
        for numero in (1, 2):
            self.csv_ent(numero, [{"tipo": "CPF", "valor": "111.222.333-44", "pagina_pdf": str(numero)}])
        self.indexar()
        self.assertEqual(self.r.cruzar("OS-1-2099"), [{"tipo": "CPF", "valor": "111.222.333-44", "outro_caso": "OS-2-2099", "paginas": "2"}])

    def test_remissao_no_corpo_nao_vira_folha_fisica(self):
        path = self.ws / "casos/OS-1-2099/01-extracao/doc/transcricao.md"
        path.write_text("## Página 1\nO despacho determina consultar as fls. 30 dos autos.\n\n## Página 2\nFls. 7\nConteúdo sintético.", encoding="utf-8")
        self.indexar()
        with closing(sqlite3.connect(self.ws / "rag/cpj.sqlite")) as db:
            rows = db.execute("SELECT pagina,fls,texto FROM trechos WHERE tipo='transcricao' ORDER BY pagina").fetchall()
        self.assertEqual([(r[0], r[1]) for r in rows], [(1, None), (2, "7")])
        self.assertIn("consultar as fls. 30", rows[0][2])

    def test_cadastro_manual_rejeita_identificador_incerto_sem_normalizar(self):
        import vinculos_manuais as VM
        antes = VM.exportar_eventos(self.ws)
        tipos = ("CPF","CNPJ","TELEFONE","RG","PLACA","CONTA","CHAVE_PIX","EMAIL","PROCESSO","BO")
        with patch("rotas.comum.usuario", return_value={"login":"investigador-ficticio", "perfil":"investigador"}):
            for tipo in tipos:
                for valor in ("111.222.33?-44", "11122233344 [dígito incerto]"):
                    for lado in ("a","b"):
                        with self.subTest(tipo=tipo, valor=valor, lado=lado):
                            dados = {"caso":"OS-1-2099", "a_tipo":"EMAIL", "a_valor":"origem@example.invalid",
                                     "b_tipo":"EMAIL", "b_valor":"destino@example.invalid", "relacao":"candidato sintético",
                                     lado+"_tipo":tipo, lado+"_valor":valor}
                            # Store e API devem rejeitar o mesmo valor bruto, antes de remover marcadores.
                            with self.assertRaisesRegex(ValueError, "incerto"):
                                VM.criar(self.ws, dados, "investigador-ficticio")
                            resposta = self.s.app.test_client().post("/api/grafo/vinculo", headers={"X-CPJ":"1"}, json=dados)
                            self.assertEqual(resposta.status_code, 400, resposta.get_json())
        self.assertEqual(VM.exportar_eventos(self.ws), antes, "Recusas não podem publicar eventos autoritativos.")

    def test_conta_extraida_sem_banco_nao_gera_cruzamento_exato(self):
        for numero in (1, 2):
            self.csv_ent(numero, [{"tipo": "CONTA", "valor": "Ag 0001 CC 12345-6", "pagina_pdf": str(numero)}])
        self.indexar()
        self.assertEqual(self.r.cruzar("OS-1-2099"), [])

    def test_reconstruir_indice_ausente_recupera_fonte_manual(self):
        payload = {"caso": "OS-1-2099", "a_tipo": "EMAIL", "a_valor": "reconstruir@example.invalid",
                   "b_tipo": "EMAIL", "b_valor": "destino@example.invalid", "relacao": "persistência sintética"}
        with patch("rotas.comum.usuario", return_value={"login": "investigador-ficticio", "perfil": "investigador"}):
            response = self.s.app.test_client().post("/api/grafo/vinculo", headers={"X-CPJ": "1"}, json=payload)
        self.assertEqual(response.status_code, 200, response.get_json())
        indice = self.ws / "rag/cpj.sqlite"
        self.assertTrue(indice.resolve().is_relative_to(self.ws.resolve()))
        indice.unlink()
        self.indexar()
        graph = self.r.vinculos("EMAIL", payload["a_valor"], niveis=1)
        self.assertEqual([a["relacao"] for a in graph["arestas"]], ["persistência sintética"])

    def test_migracao_legada_preserva_duplicatas_e_rotulo_sem_duplicar_eventos(self):
        row = ("EMAIL", "legado@example.invalid", "EMAIL", "destino@example.invalid", "relação legada sintética")
        with closing(sqlite3.connect(self.ws / "rag/cpj.sqlite")) as db:
            for _ in range(2):
                db.execute("INSERT INTO arestas VALUES(?,?,?,?,?,'manual','OS-1-2099','Fls. 6 sintética')", row)
            db.execute("INSERT INTO rotulos VALUES('EMAIL','legado@example.invalid','Rótulo legado')")
            db.commit()
        self.indexar()
        import vinculos_manuais as VM
        primeira = [r for r in VM.listar(str(self.ws)) if r["a_valor"] == row[1]]
        self.assertEqual(len(primeira), 2)
        self.assertTrue(all(r["a_rotulo"] == "Rótulo legado" for r in primeira))
        self.indexar()
        segunda = [r for r in VM.listar(str(self.ws)) if r["a_valor"] == row[1]]
        self.assertEqual(segunda, primeira)


if __name__ == "__main__":
    unittest.main(verbosity=2)
