#!/usr/bin/env python3
"""K01 (+ RV06): comparativo local minuta x FINAL, proposta genérica e gravação só do que o investigador aprova.
Workspace temporário e dados fictícios; nada é gravado em calibracao/ sem aprovação, e nunca com dados de caso."""
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP.parent / "skills" / "relatorio-ip-fraude" / "scripts"))
import calibrar_versoes as CV  # noqa: E402

PARAGRAFO = ("O investigado realizou transferências conforme consta nos autos (pág. 3 do PDF; fls. 12) no valor de R$ 1.000,00 "
             "e depois R$ 2.000,00 para a conta intermediária, e a vítima relatou o prejuízo total apurado. ")
MINUTA = ("---\nordem_servico: OS 1/2099\n---\n\n## RESUMO DOS FATOS\n\n" + (PARAGRAFO * 8) + "\n\n"
          "- primeiro tópico do resumo dos fatos\n- segundo tópico do resumo dos fatos\n- terceiro tópico do resumo dos fatos\n\n"
          "{PREENCHER local}\n\n## CONCLUSÃO\n\nTexto de conclusão da minuta fictícia para o teste.\n")
FINAL = ("Resumo dos fatos. Em tese, há indícios de que o investigado agiu. Em tese, o investigado recebeu valores. "
         "Há indícios de que a conta serviu de passagem para o dinheiro da vítima nos autos. "
         "Conclusão curta e objetiva do investigador sobre o caso fictício apresentado neste teste unitário.")


class CalibracaoK01(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="cpj-calibracao-k01-")
        cls.ws = Path(cls.temp.name)
        cls.env = os.environ.get("CPJ_WORKSPACE")
        os.environ["CPJ_WORKSPACE"] = str(cls.ws)
        modelo = cls.ws / "casos" / "_MODELO-CASO"
        for pasta in ("00-originais", "01-extracao", "02-analise", "03-relatorios"):
            (modelo / pasta).mkdir(parents=True, exist_ok=True)
        (modelo / "caso.json").write_text(json.dumps({"datas": {}, "financeiro": {}, "ip": {}, "resultado": {}, "relatorios": []}),
                                          encoding="utf-8")
        cal = cls.ws / "calibracao"
        cal.mkdir()
        cls.licoes = "# Lições\n\n## 1. Ciclo\n\ntexto original\n"
        cls.hist = "# Histórico\n\n| Data | Caso | Dif | Apr | Rej | Mud |\n|---|---|---|---|---|---|\n"
        (cal / "licoes-aprendidas.md").write_text(cls.licoes, encoding="utf-8")
        (cal / "historico-calibracao.md").write_text(cls.hist, encoding="utf-8")
        sys.path.insert(0, str(APP))
        import servidor
        cls.s = servidor
        servidor.app.config.update(TESTING=True)
        servidor.auth.salvar_usuario("inv_k01", "Investigador ficticio", "investigador", "SenhaFicticia123")
        cls.caso = servidor.C.novo("901/2099", extras={"criado_por": "inv_k01"})["id"]
        (Path(servidor.C.caminho(cls.caso)) / "03-relatorios" / "minuta-v01.md").write_text(MINUTA, encoding="utf-8")
        cls.c = servidor.app.test_client()
        r = cls.c.post("/api/entrar", json={"login": "inv_k01", "senha": "SenhaFicticia123"}, headers={"X-CPJ": "1"})
        assert r.status_code == 200

    @classmethod
    def tearDownClass(cls):
        for a in cls.ws.rglob("*"):
            if a.is_file():
                a.chmod(0o600)
        cls.temp.cleanup()
        if cls.env is None:
            os.environ.pop("CPJ_WORKSPACE", None)
        else:
            os.environ["CPJ_WORKSPACE"] = cls.env

    def calibrar(self, nome, dados):
        return self.c.post(f"/api/casos/{self.caso}/calibrar", headers={"X-CPJ": "1"},
                           data={"final": (io.BytesIO(dados), nome)}, content_type="multipart/form-data")

    def lido(self, nome):
        return (self.ws / "calibracao" / nome).read_text(encoding="utf-8")

    # --- módulo
    def test_01_comparar_gera_licoes_genericas(self):
        res = CV.comparar(MINUTA, FINAL)
        ids = {x["id"] for x in res["licoes"]}
        for esperado in ("mais-conciso", "reforcar-cautela", "sem-topicos", "limpar-pendencias", "menos-valores"):
            self.assertIn(esperado, ids)
        self.assertTrue(all(x["texto"] == CV.CATALOGO[x["id"]] for x in res["licoes"]))
        self.assertEqual(CV.comparar(MINUTA, MINUTA)["licoes"], [], "textos iguais não geram lição")

    def test_02_proposta_nao_vaza_dados_do_caso(self):
        txt = json.dumps(CV.comparar(MINUTA, FINAL), ensure_ascii=False)
        for dado in ("OS 1/2099", "investigado realizou", "intermediária", "1.000,00", "pág. 3"):
            self.assertNotIn(dado, txt)

    # --- rota: proposta
    def test_03_rota_propoe_sem_gravar(self):
        r = self.calibrar("final.md", FINAL.encode("utf-8"))
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
        j = r.get_json()
        self.assertTrue(j["proposta"] and not j["gravado"] and j["licoes"])
        self.assertEqual(self.lido("licoes-aprendidas.md"), self.licoes, "RV06: nada gravado na proposta")
        self.assertEqual(self.lido("historico-calibracao.md"), self.hist)

    def test_04_aceita_docx(self):
        import docx
        d = docx.Document()
        for frase in FINAL.split(". "):
            d.add_paragraph(frase + ".")
        buf = io.BytesIO()
        d.save(buf)
        r = self.calibrar("FINAL.docx", buf.getvalue())
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
        self.assertIn("mais-conciso", {x["id"] for x in r.get_json()["licoes"]})

    def test_05_recusas(self):
        self.assertEqual(self.calibrar("final.exe", b"x" * 500).status_code, 400)
        self.assertEqual(self.calibrar("final.md", b"curto").status_code, 400)
        r = self.c.post(f"/api/casos/{self.caso}/calibrar", headers={"X-CPJ": "1"})
        self.assertEqual(r.status_code, 400, "sem arquivo FINAL enviado")

    # --- rota: aprovação
    def test_06_aprovar_grava_so_catalogo_sem_id_de_caso(self):
        r = self.c.post(f"/api/casos/{self.caso}/calibrar/aprovar", headers={"X-CPJ": "1"},
                        json={"ids": ["mais-conciso", "texto-livre-invalido", "sem-topicos"]})
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
        self.assertEqual(sorted(r.get_json()["gravadas"]), ["mais-conciso", "sem-topicos"])
        licoes, hist = self.lido("licoes-aprendidas.md"), self.lido("historico-calibracao.md")
        self.assertIn(CV.CATALOGO["mais-conciso"], licoes)
        self.assertIn(CV.SECAO, licoes)
        self.assertNotIn("texto-livre-invalido", licoes)
        for arq in (licoes, hist):
            self.assertNotIn(self.caso, arq, "regra 7: sem ID de caso em calibracao/")
            self.assertNotIn("901/2099", arq)
            self.assertNotIn("inv_k01", arq)
        r2 = self.c.post(f"/api/casos/{self.caso}/calibrar/aprovar", headers={"X-CPJ": "1"}, json={"ids": ["mais-conciso"]})
        self.assertEqual(r2.get_json()["ja_existentes"], ["mais-conciso"], "sem duplicar")
        self.assertEqual(self.lido("licoes-aprendidas.md").count(CV.CATALOGO["mais-conciso"]), 1)

    def test_07_aprovar_exige_ids_e_login(self):
        self.assertEqual(self.c.post(f"/api/casos/{self.caso}/calibrar/aprovar", headers={"X-CPJ": "1"}, json={"ids": []}).status_code, 400)
        anon = self.s.app.test_client()
        self.assertIn(anon.post(f"/api/casos/{self.caso}/calibrar/aprovar", headers={"X-CPJ": "1"}, json={"ids": ["mais-conciso"]}).status_code,
                      (401, 403))


if __name__ == "__main__":
    unittest.main(verbosity=2)
