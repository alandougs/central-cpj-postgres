"""Regressões RV17: concorrência e gate de entrega, apenas dados fictícios."""
import concurrent.futures
import errno
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))


class RelatoriosRV17(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="cpj-rv17-")
        cls.ws = Path(cls.temp.name)
        cls.env = os.environ.get("CPJ_WORKSPACE")
        os.environ["CPJ_WORKSPACE"] = str(cls.ws)
        modelo = cls.ws / "casos" / "_MODELO-CASO"
        modelo.mkdir(parents=True)
        (modelo / "caso.json").write_text(json.dumps({
            "datas": {}, "financeiro": {}, "ip": {}, "resultado": {}, "relatorios": []
        }), encoding="utf-8")
        import servidor
        from rotas import relatorios
        cls.s, cls.r = servidor, relatorios
        servidor.app.config.update(TESTING=True)
        servidor.auth.salvar_usuario("admin_rv17", "Admin fictício", "admin", "SenhaFicticia123")
        (cls.ws / "config" / "solo.json").write_text('{"ativo": true}', encoding="utf-8")
        cls.indexar = patch.object(relatorios, "tarefas", SimpleNamespace(indexar=lambda: None))
        cls.indexar.start()

    @classmethod
    def tearDownClass(cls):
        cls.indexar.stop()
        cls.temp.cleanup()
        if cls.env is None:
            os.environ.pop("CPJ_WORKSPACE", None)
        else:
            os.environ["CPJ_WORKSPACE"] = cls.env

    def novo_caso(self):
        self.__class__.n = getattr(self.__class__, "n", 0) + 1
        cid = self.s.C.novo(f"{self.n}/2099")["id"]
        p = Path(self.s.C.caminho(cid)) / "03-relatorios"
        p.mkdir(exist_ok=True)
        return cid, p

    def post(self, cid, acao, dados):
        with self.s.app.test_client() as cli:
            return cli.post(f"/api/casos/{cid}/{acao}", headers={"X-CPJ": "1"}, json=dados)

    def test_gravacao_simultanea_na_mesma_base_aceita_so_um_editor(self):
        cid, pasta = self.novo_caso()
        original = self.r.ultima_minuta
        inicio = threading.Barrier(6)

        def ler_lentamente(id_):
            valor = original(id_)
            time.sleep(0.03)
            return valor

        def salvar(i):
            inicio.wait(timeout=5)
            return self.post(cid, "minuta", {
                "versao_base": 0, "gerar_docx": False,
                "secoes": {"RESUMO DOS FATOS": f"Editor fictício {i}"},
            }).status_code

        with patch.object(self.r, "ultima_minuta", side_effect=ler_lentamente):
            with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
                codigos = list(pool.map(salvar, range(6)))
        self.assertEqual(sorted(codigos), [200, 409, 409, 409, 409, 409])
        self.assertEqual(len(list(pasta.glob("minuta-v*.md"))), 1)
        self.assertTrue((pasta / "minuta-v01.md").read_text(encoding="utf-8"))

    def test_versao_nova_nao_reutiliza_lacuna(self):
        cid, pasta = self.novo_caso()
        (pasta / "minuta-v03.md").write_text("Versão fictícia 3", encoding="utf-8")
        r = self.post(cid, "minuta", {"gerar_docx": False, "versao_base": 3})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["arquivo"], "minuta-v04.md")

    def test_versao_invalida_recusada_sem_gravar(self):
        for versao in ("inválida", -1, [], 1.5, True):
            with self.subTest(versao=versao):
                cid, pasta = self.novo_caso()
                r = self.post(cid, "minuta", {"gerar_docx": False, "versao_base": versao})
                self.assertEqual(r.status_code, 400)
                self.assertEqual(list(pasta.glob("minuta-v*.md")), [])

    def test_ultima_vista_continua_com_contrato_409(self):
        cid, pasta = self.novo_caso()
        (pasta / "minuta-v02.md").write_text("Texto fictício", encoding="utf-8")
        r = self.post(cid, "minuta", {"gerar_docx": False, "ultima_vista": "minuta-v01.md"})
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.get_json()["erro"], "minuta_atualizada")

    def test_conferencia_antiga_nao_aprova_execucao_que_falhou(self):
        cid, pasta = self.novo_caso()
        (pasta / "conferencia-v01.json").write_text(json.dumps({"aprovado": True, "achados": []}), encoding="utf-8")
        falha = subprocess.CompletedProcess([], 1, "", "Falha fictícia do conferidor")
        with patch.object(self.r.subprocess, "run", return_value=falha):
            conf = self.r.conferir_minuta_gate(cid, "minuta-v01.md")
        self.assertFalse(conf["aprovado"])
        self.assertTrue(any(a["nivel"] == "BLOQUEIA" for a in conf["achados"]))

    def test_conferencia_sem_resultado_ou_com_timeout_bloqueia(self):
        for resultado in (subprocess.CompletedProcess([], 0, "", ""), subprocess.TimeoutExpired([], 180)):
            cid, _ = self.novo_caso()
            config = {"side_effect": resultado} if isinstance(resultado, Exception) else {"return_value": resultado}
            with patch.object(self.r.subprocess, "run", **config):
                conf = self.r.conferir_minuta_gate(cid, "minuta-v01.md")
            self.assertFalse(conf["aprovado"])
            self.assertEqual(conf["resumo"]["BLOQUEIA"], 1)

    def test_ids_nao_podem_referenciar_pasta_pai(self):
        for cid in (".", ".."):
            with self.assertRaises(ValueError):
                self.s.C.caminho(cid)

    def test_definir_final_novamente_nao_copia_o_arquivo_sobre_si(self):
        cid, pasta = self.novo_caso()
        nome = f"RELATORIO-{cid}-FINAL.docx"
        (pasta / nome).write_bytes(b"DOCX ficticio")
        (pasta / "minuta-v01.md").write_text("Minuta fictícia", encoding="utf-8")
        with patch.object(self.r, "conferir_minuta_gate", return_value={"aprovado": True, "achados": []}):
            r = self.post(cid, "final", {"docx": nome})
        self.assertEqual(r.status_code, 200)
        self.assertEqual((pasta / nome).read_bytes(), b"DOCX ficticio")

    def test_final_nao_confere_minuta_de_outra_versao(self):
        cid, pasta = self.novo_caso()
        docx = f"RELATORIO-{cid}-v01.docx"
        (pasta / docx).write_bytes(b"DOCX ficticio")
        (pasta / "minuta-v02.md").write_text("Minuta fictícia", encoding="utf-8")
        with patch.object(self.r, "conferir_minuta_gate", return_value={"aprovado": True, "achados": []}) as gate:
            r = self.post(cid, "final", {"docx": docx, "minuta": "minuta-v02.md"})
        self.assertEqual(r.status_code, 400)
        gate.assert_not_called()
        self.assertFalse((pasta / f"RELATORIO-{cid}-FINAL.docx").exists())
        self.assertNotEqual(self.s.C.carregar(cid)["status"], "entregue")

    def test_final_sem_minuta_da_versao_nao_usa_a_mais_recente(self):
        cid, pasta = self.novo_caso()
        docx = f"RELATORIO-{cid}-v01.docx"
        (pasta / docx).write_bytes(b"DOCX ficticio")
        (pasta / "minuta-v02.md").write_text("Minuta fictícia", encoding="utf-8")
        with patch.object(self.r, "conferir_minuta_gate", return_value={"aprovado": True, "achados": []}) as gate:
            r = self.post(cid, "final", {"docx": docx})
        self.assertEqual(r.status_code, 409)
        gate.assert_not_called()

    def test_reserva_propaga_erro_de_io_sem_loop(self):
        _, pasta = self.novo_caso()
        chamadas = [0]

        def negar(*args, **kwargs):
            chamadas[0] += 1
            if chamadas[0] > 2:
                raise RuntimeError("Sentinela: loop indevido")
            raise PermissionError(errno.EACCES, "Falha fictícia de permissão")

        with patch.object(self.s.C.os, "open", side_effect=negar):
            with self.assertRaises(PermissionError):
                with self.s.C.reservar_arquivo_versao(str(pasta)):
                    self.fail("Reserva não deve ocorrer")
        self.assertEqual(chamadas[0], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
