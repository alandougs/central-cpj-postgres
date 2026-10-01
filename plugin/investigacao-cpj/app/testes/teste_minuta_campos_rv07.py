#!/usr/bin/env python3
"""RV07 (regras 10 e 13): o editor da minuta preserva delegado_genero e escrivao, e a minuta nova monta a referência
somente com IPe e Processo (nunca BO nem IP local), deixando [PENDENTE] no campo ausente. Dados fictícios."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

AQUI = Path(__file__).resolve().parent
H = {"X-CPJ": "1"}


class MinutaCamposRV07(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="cpj-minuta-rv07-", ignore_cleanup_errors=True)
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
        servidor.auth.salvar_usuario("inv_rv07", "Investigador ficticio", "investigador", "SenhaFicticia123")
        cls.c = servidor.app.test_client()
        assert cls.c.post("/api/entrar", json={"login": "inv_rv07", "senha": "SenhaFicticia123"}, headers=H).status_code == 200
        cls.n = 0

    @classmethod
    def tearDownClass(cls):
        import time
        time.sleep(1.0)
        for a in cls.ws.rglob("*"):
            if a.is_file():
                a.chmod(0o600)
        cls.temp.cleanup()
        if cls.env is None:
            os.environ.pop("CPJ_WORKSPACE", None)
        else:
            os.environ["CPJ_WORKSPACE"] = cls.env

    def caso(self, inquerito="", processo="", bo="", **outros):
        type(self).n += 1
        id_ = self.s.C.novo(f"{920 + self.n}/2099", bo=bo, inquerito=inquerito, processo=processo,
                            extras={"criado_por": "inv_rv07"})["id"]
        if outros:
            self.s.C.atualizar(id_, lambda c: c.update(outros))
        return id_

    def meta_inicial(self, id_):
        r = self.c.get(f"/api/casos/{id_}/minuta", headers=H)
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
        return r.get_json()["meta"]

    def test_01_referencia_so_com_ipe_e_processo(self):
        id_ = self.caso(inquerito="Inquérito Policial Eletrônico nº 123456/2026", processo="Processo nº 0001234-56.2026.8.26.0000",
                        bo="BO 555/2026")
        ref = self.meta_inicial(id_)["referencia"]
        self.assertEqual(ref, "IPe nº 123456/2026 / Processo nº 0001234-56.2026.8.26.0000")
        self.assertNotIn("BO", ref)
        self.assertNotIn("555", ref)

    def test_02_ignora_referencia_antiga_com_bo(self):
        id_ = self.caso(inquerito="654321/2026", processo="0009999-00.2026.8.26.0000")
        self.s.C.atualizar(id_, lambda c: c.update(referencia="BO 1/2026 / IP 9/2026"))
        ref = self.meta_inicial(id_)["referencia"]
        self.assertNotIn("BO", ref)
        self.assertNotIn("IP 9", ref)
        self.assertEqual(ref, "IPe nº 654321/2026 / Processo nº 0009999-00.2026.8.26.0000")

    def test_03_campo_ausente_fica_pendente_sem_inventar(self):
        ref = self.meta_inicial(self.caso(inquerito="777777/2026"))["referencia"]
        self.assertEqual(ref, "IPe nº 777777/2026 / Processo nº [PENDENTE]")
        ref = self.meta_inicial(self.caso())["referencia"]
        self.assertEqual(ref, "IPe nº [PENDENTE] / Processo nº [PENDENTE]")

    def test_04_genero_e_escrivao_do_caso_vao_para_a_minuta(self):
        id_ = self.caso(inquerito="111111/2026", processo="2222222-00.2026.8.26.0000", delegado_genero="F", escrivao="Escrivao Ficticio")
        m = self.meta_inicial(id_)
        self.assertEqual(m["delegado_genero"], "F")
        self.assertEqual(m["escrivao"], "Escrivao Ficticio")

    def test_05_genero_nao_e_inferido_do_nome(self):
        id_ = self.caso(inquerito="111111/2026", processo="2222222-00.2026.8.26.0000", requisitante="Maria Ficticia")
        self.assertEqual(self.meta_inicial(id_)["delegado_genero"], "", "sem M/F e sem título (Dr./Dra.), fica vazio")

    def test_06_salvar_pelo_editor_nao_apaga_genero_nem_escrivao(self):
        id_ = self.caso(inquerito="111111/2026", processo="2222222-00.2026.8.26.0000")
        meta = {"ordem_servico": "OS 1/2099", "referencia": "IPe nº 111111/2026 / Processo nº 2222222-00.2026.8.26.0000",
                "natureza": "Estelionato", "delegado": "Dra. Ficticia", "delegado_genero": "F", "escrivao": "Escrivao Ficticio"}
        secoes = {"RESUMO DOS FATOS": "Texto.", "DILIGÊNCIAS REALIZADAS": "Texto.", "CONCLUSÃO": "Texto."}
        r = self.c.post(f"/api/casos/{id_}/minuta", headers=H, json={"meta": meta, "secoes": secoes, "gerar_docx": False})
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
        m = self.c.get(f"/api/casos/{id_}/minuta", headers=H).get_json()["meta"]
        self.assertEqual(m["delegado_genero"], "F")
        self.assertEqual(m["escrivao"], "Escrivao Ficticio")
        self.assertEqual(m["referencia"], meta["referencia"])
        arq = Path(self.s.C.caminho(id_)) / "03-relatorios" / "minuta-v01.md"
        self.assertIn("delegado_genero: F", arq.read_text(encoding="utf-8"))

    def test_07_interface_expoe_os_campos(self):
        html = (AQUI.parent / "static" / "index.html").read_text(encoding="utf-8")
        self.assertIn('["delegado_genero","Gênero Delegado(a) (M/F)"]', html)
        self.assertIn('["escrivao","Escrivão(ã) do feito"]', html)

    def test_08_leitor_aceita_titulos_com_dois_ou_tres_hashes(self):
        from rotas.relatorios import ler_minuta
        _, sec = ler_minuta("---\ncaso: X\n---\n### Resumo dos Fatos\n\nA.\n\n## DILIGENCIAS REALIZADAS\n\nB.\n\n### Conclusão\n\nC.\n")
        self.assertEqual((sec["RESUMO DOS FATOS"], sec["DILIGÊNCIAS REALIZADAS"], sec["CONCLUSÃO"]), ("A.", "B.", "C."))


if __name__ == "__main__":
    unittest.main(verbosity=2)
