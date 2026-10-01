#!/usr/bin/env python3
"""V05/RV04: POST /api/casos/<id>/final roda o gate (conferir_minuta.py --modo entrega).
Reprovada -> 409 com os achados e sem baixa; 'forcar' exige justificativa de 15+ caracteres, grava a ressalva em
caso.json (baixa.ressalva) e em auditoria.log; aprovada -> 200 sem ressalva. Workspace temporário, dados fictícios."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
from teste_gate_v04 import LIMPA, RELATORIO_EXTRACAO, TRANSCRICAO  # noqa: E402

H = {"X-CPJ": "1"}
RUIM = LIMPA.replace("R$ 1.500,00 para a chave", "R$ 7.777,77 para a chave")  # valor que não existe nos autos


class GateCentralV05(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="cpj-gate-v05-", ignore_cleanup_errors=True)
        cls.ws = Path(cls.temp.name)
        cls.env = os.environ.get("CPJ_WORKSPACE")
        os.environ["CPJ_WORKSPACE"] = str(cls.ws)
        modelo = cls.ws / "casos" / "_MODELO-CASO"
        for pasta in ("00-originais", "01-extracao", "02-analise", "03-relatorios"):
            (modelo / pasta).mkdir(parents=True, exist_ok=True)
        (modelo / "caso.json").write_text(json.dumps({"datas": {}, "financeiro": {}, "ip": {}, "resultado": {}, "relatorios": []}),
                                          encoding="utf-8")
        sys.path.insert(0, str(AQUI.parent))
        import servidor
        cls.s = servidor
        servidor.app.config.update(TESTING=True)
        servidor.auth.salvar_usuario("inv_v05", "Investigador ficticio", "investigador", "SenhaFicticia123")
        cls.c = servidor.app.test_client()
        assert cls.c.post("/api/entrar", json={"login": "inv_v05", "senha": "SenhaFicticia123"}, headers=H).status_code == 200

    @classmethod
    def tearDownClass(cls):
        import time
        time.sleep(1.5)  # a indexação em segundo plano ainda pode estar fechando o SQLite do RAG
        for a in cls.ws.rglob("*"):
            if a.is_file():
                a.chmod(0o600)
        cls.temp.cleanup()
        if cls.env is None:
            os.environ.pop("CPJ_WORKSPACE", None)
        else:
            os.environ["CPJ_WORKSPACE"] = cls.env

    def novo_caso(self, minuta):
        import docx
        self.__class__.n = getattr(self.__class__, "n", 0) + 1
        id_ = self.s.C.novo(f"{910 + self.n}/2099", extras={"criado_por": "inv_v05"})["id"]
        p = Path(self.s.C.caminho(id_))
        ext = p / "01-extracao" / "ip-ficticio"
        ext.mkdir(parents=True)
        (ext / "transcricao.md").write_text(TRANSCRICAO, encoding="utf-8")
        (ext / "relatorio_extracao.json").write_text(json.dumps(RELATORIO_EXTRACAO), encoding="utf-8")
        (p / "03-relatorios" / "minuta-v01.md").write_text(minuta, encoding="utf-8")
        d = docx.Document()
        d.add_paragraph("Relatório fictício para o teste do gate de entrega.")
        d.save(str(p / "03-relatorios" / f"RELATORIO-{id_}-v01.docx"))
        return id_, p

    def final(self, id_, **corpo):
        return self.c.post(f"/api/casos/{id_}/final", headers=H, json={"docx": f"RELATORIO-{id_}-v01.docx", **corpo})

    def test_01_reprovada_devolve_409_sem_baixa(self):
        id_, p = self.novo_caso(RUIM)
        r = self.final(id_)
        self.assertEqual(r.status_code, 409, r.get_data(as_text=True))
        j = r.get_json()
        self.assertTrue(j["bloqueado"] and j["bloqueios"] >= 1 and j["achados"])
        self.assertTrue(any(a["nivel"] == "BLOQUEIA" for a in j["achados"]))
        self.assertFalse((p / "03-relatorios" / f"RELATORIO-{id_}-FINAL.docx").exists(), "sem FINAL copiado")
        c = self.s.C.carregar(id_)
        self.assertFalse(c.get("baixa"), "sem baixa")
        self.assertNotEqual(c.get("status"), "entregue")

    def test_02_forcar_exige_justificativa(self):
        id_, p = self.novo_caso(RUIM)
        self.assertEqual(self.final(id_, forcar=True).status_code, 400)
        self.assertEqual(self.final(id_, forcar=True, justificativa="curta").status_code, 400)
        self.assertEqual(self.final(id_, forcar=True, justificativa="               ").status_code, 400)
        self.assertFalse((p / "03-relatorios" / f"RELATORIO-{id_}-FINAL.docx").exists())

    def test_03_forcar_com_justificativa_grava_ressalva_e_auditoria(self):
        id_, p = self.novo_caso(RUIM)
        just = "Valor conferido manualmente na imagem da pagina."
        r = self.final(id_, forcar=True, justificativa=just)
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
        self.assertEqual(r.get_json()["ressalva"], just)
        self.assertTrue((p / "03-relatorios" / f"RELATORIO-{id_}-FINAL.docx").exists())
        c = self.s.C.carregar(id_)
        self.assertEqual(c["baixa"]["ressalva"], just)
        log = (self.ws / "config" / "auditoria.log").read_text(encoding="utf-8")
        self.assertIn("relatorio_final_ressalva", log)
        self.assertIn(just, log)

    def test_04_aprovada_da_baixa_sem_ressalva(self):
        id_, p = self.novo_caso(LIMPA)
        r = self.final(id_)
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
        self.assertNotIn("ressalva", r.get_json())
        c = self.s.C.carregar(id_)
        self.assertTrue(c["baixa"] and not c["baixa"].get("ressalva"))
        self.assertTrue((p / "03-relatorios" / f"RELATORIO-{id_}-FINAL.docx").exists())

    def test_05_docx_inexistente_400(self):
        id_, _ = self.novo_caso(LIMPA)
        r = self.c.post(f"/api/casos/{id_}/final", headers=H, json={"docx": "nao-existe.docx"})
        self.assertEqual(r.status_code, 400)


if __name__ == "__main__":
    unittest.main(verbosity=2)
