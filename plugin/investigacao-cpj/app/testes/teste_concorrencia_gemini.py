#!/usr/bin/env python3
"""Teste de proteção contra concorrência e reserva atômica de versões de minuta (C05).
Executa testes em workspace isolado e dados fictícios.
"""
import concurrent.futures
import json
import os
import shutil
import tempfile
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(AQUI)
PLUGIN = os.path.dirname(APP)
S_BASE = os.path.join(PLUGIN, "skills", "base-cpj", "scripts")
import sys
sys.path.insert(0, S_BASE)
sys.path.insert(0, APP)

import caso as C
import servidor


class ConcorrenciaGemini(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ws_temp = tempfile.mkdtemp(prefix="cpj-concorrencia-")
        os.environ["CPJ_WORKSPACE"] = cls.ws_temp
        C.WS = cls.ws_temp
        C.CASOS = os.path.join(cls.ws_temp, "casos")
        C.MODELO = os.path.join(C.CASOS, "_MODELO-CASO")
        
        # Cria estrutura mínima do workspace de teste
        os.makedirs(C.MODELO, exist_ok=True)
        with open(os.path.join(C.MODELO, "caso.json"), "w", encoding="utf-8") as f:
            json.dump({
                "schema": "cpj-caso/1", "id": "", "ordem_servico": "", "bo": "", "inquerito": "", "processo": "",
                "referencia": "", "natureza": "Estelionato", "modalidade": "", "status": "recebido",
                "datas": {"recebido": "2026-09-27"}, "ip": {"paginas": 0, "sha256": "", "metodos": {}, "pendentes": 0, "conferir": 0},
                "vitimas": [], "investigados": [], "relatorios": [], "revisao": 1
            }, f, indent=2)

        os.makedirs(os.path.join(cls.ws_temp, "config"), exist_ok=True)
        os.makedirs(os.path.join(cls.ws_temp, "usuarios"), exist_ok=True)
        
        # Configura servidor
        servidor.WS = cls.ws_temp
        servidor.auth = servidor.Auth(cls.ws_temp)
        servidor.auth.salvar_usuario("admin", "Admin", "admin", "Admin12345")
        servidor.auth.salvar_usuario("investigador", "Investigador", "investigador", "Inv12345")
        cls.client = servidor.app.test_client()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.ws_temp, ignore_errors=True)

    def test_01_escrita_concorrente_threads(self):
        """20 threads alterando simultaneamente o mesmo caso não causam perda nem corrupção."""
        c = C.novo("OS-CONC-1/2026", id_="OS-CONC-1")
        
        def worker(idx):
            C.set_campos("OS-CONC-1", {f"vitimas": f"Vitima {idx}"})
            return idx

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            futs = [ex.submit(worker, i) for i in range(20)]
            resultados = [f.result() for f in futs]

        self.assertEqual(len(resultados), 20)
        c_final = C.carregar("OS-CONC-1")
        self.assertGreater(c_final.get("revisao", 0), 10)
        self.assertTrue(os.path.exists(os.path.join(C.caminho("OS-CONC-1"), "caso.json")))

    def test_02_reserva_concorrente_minutas(self):
        """10 threads tentando criar minutas simultaneamente criam versões estritamente consecutivas sem colisão."""
        cid = "OS-CONC-MINUTAS"
        C.novo("OS-CONC-MIN/2026", id_=cid)

        def worker(idx):
            def fmt(v, nome):
                return f"---\ncaso: {cid}\nversao: {v:02d}\n---\n\n## RESUMO DOS FATOS\n\nTexto thread {idx}\n"
            return C.reservar_proxima_minuta(cid, fmt)

        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
            futs = [ex.submit(worker, i) for i in range(10)]
            res = [f.result() for f in futs]

        versoes_geradas = sorted([r["versao"] for r in res])
        self.assertEqual(versoes_geradas, list(range(1, 11)))
        
        d_rels = os.path.join(C.caminho(cid), "03-relatorios")
        arquivos = sorted([f for f in os.listdir(d_rels) if f.startswith("minuta-v") and f.endswith(".md")])
        self.assertEqual(len(arquivos), 10)
        self.assertEqual(arquivos[0], "minuta-v01.md")
        self.assertEqual(arquivos[-1], "minuta-v10.md")

    def test_03_conflito_versao_base_defasada(self):
        """Gravar com versao_base defasada levanta ConcorrenciaErro."""
        cid = "OS-CONC-BASE"
        C.novo("OS-CONC-BASE/2026", id_=cid)
        
        # Cria v01 e v02
        C.reservar_proxima_minuta(cid, "conteudo v01")
        C.reservar_proxima_minuta(cid, "conteudo v02")

        # Tentar salvar informando que base era v01 deve falhar porque disco já está em v02
        with self.assertRaises(C.ConcorrenciaErro):
            C.reservar_proxima_minuta(cid, "conteudo v03 concorrente", versao_base=1)

    def test_04_conflito_revisao_esperada(self):
        """Salvar caso com revisao_esperada defasada levanta ConcorrenciaErro."""
        cid = "OS-CONC-REV"
        c = C.novo("OS-CONC-REV/2026", id_=cid)
        rev_inicial = c.get("revisao", 1)

        # Atualiza uma vez -> revisão avança
        C.set_campos(cid, {"bo": "1234/2026"})
        
        # Tenta salvar passando a revisão inicial defasada
        with self.assertRaises(C.ConcorrenciaErro):
            C.set_campos(cid, {"bo": "5678/2026"}, revisao_esperada=rev_inicial)

    def test_05_api_minuta_concorrencia_http_409(self):
        """API /api/casos/<id>/minuta retorna HTTP 409 quando há conflito de concorrência."""
        # Login como investigador
        r_login = self.client.post("/api/entrar", json={"login": "investigador", "senha": "Inv12345"}, headers={"X-CPJ": "1"})
        self.assertEqual(r_login.status_code, 200)

        cid = "OS-CONC-API-MIN"
        C.novo("OS-CONC-API-MIN/2026", id_=cid)

        # Salva v01
        r1 = self.client.post(f"/api/casos/{cid}/minuta", json={
            "meta": {"caso": cid}, "secoes": {"RESUMO DOS FATOS": "Fato inicial"}, "gerar_docx": False
        }, headers={"X-CPJ": "1"})
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.get_json()["arquivo"], "minuta-v01.md")

        # Salva v02
        r2 = self.client.post(f"/api/casos/{cid}/minuta", json={
            "meta": {"caso": cid}, "secoes": {"RESUMO DOS FATOS": "Fato v02"}, "gerar_docx": False
        }, headers={"X-CPJ": "1"})
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.get_json()["arquivo"], "minuta-v02.md")

        # Tenta salvar passando versao_base=1 (defasada)
        r3 = self.client.post(f"/api/casos/{cid}/minuta", json={
            "versao_base": 1,
            "meta": {"caso": cid},
            "secoes": {"RESUMO DOS FATOS": "Fato conflitante"},
            "gerar_docx": False
        }, headers={"X-CPJ": "1"})
        self.assertEqual(r3.status_code, 409)
        self.assertEqual(r3.get_json()["erro"], "conflito_concorrencia")

    def test_06_api_caso_salvar_concorrencia_http_409(self):
        """API /api/casos/<id> retorna HTTP 409 quando revisao_esperada é defasada."""
        cid = "OS-CONC-API-CASO"
        c = C.novo("OS-CONC-API-CASO/2026", id_=cid, extras={"criado_por": "investigador"})

        # Tenta salvar enviando revisao_esperada errada
        r = self.client.post(f"/api/casos/{cid}", json={
            "natureza": "Fraude Eletrônica",
            "revisao_esperada": 9999
        }, headers={"X-CPJ": "1"})
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.get_json()["erro"], "conflito_concorrencia")


if __name__ == "__main__":
    unittest.main()
