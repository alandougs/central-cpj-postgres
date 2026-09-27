"""Regressões C04; execução isolada, sem autos reais ou chamadas de IA."""
import concurrent.futures
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch


class DesempenhoCPJ(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="cpj-desempenho-")
        cls.ws = Path(cls.temp.name)
        cls.env_anterior = os.environ.get("CPJ_WORKSPACE")
        os.environ["CPJ_WORKSPACE"] = str(cls.ws)
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        import servidor
        cls.s = servidor
        assert Path(servidor.WS).resolve() == cls.ws.resolve(), "Execute em processo isolado."
        servidor.app.config.update(TESTING=True)
        servidor.auth.salvar_usuario("admin_ficticio", "Teste", "admin", "SenhaFicticia123")

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()
        if cls.env_anterior is None:
            os.environ.pop("CPJ_WORKSPACE", None)
        else:
            os.environ["CPJ_WORKSPACE"] = cls.env_anterior

    def setUp(self):
        self.s._ocr_cache.update(chave=None, idioma=None, expira=0)
        self.s._painel_cache.update(chave=None, gerando=False, erro=False, retentar_apos=0)
        self.prod = self.ws / "producao"
        self.prod.mkdir(exist_ok=True)
        self.html = self.prod / "painel.html"
        self.html.write_text("PAINEL ANTERIOR FICTICIO", encoding="utf-8")
        self.client = self.s.app.test_client()
        self.assertEqual(self.client.post("/api/entrar", json={
            "login": "admin_ficticio", "senha": "SenhaFicticia123"
        }, headers={"X-CPJ": "1"}).status_code, 200)

    def aguardar(self):
        limite = time.monotonic() + 15
        while self.s._painel_cache["gerando"] and time.monotonic() < limite:
            time.sleep(.01)
        self.assertFalse(self.s._painel_cache["gerando"], "Atualização não terminou")

    def test_ocr_consultas_simultaneas_compartilham_diagnostico(self):
        resultado = subprocess.CompletedProcess([], 0, "por\neng\n", "")
        with patch.object(self.s.subprocess, "run", return_value=resultado) as run:
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                idiomas = list(pool.map(lambda _: self.s.idioma_ocr({}), range(16)))
            self.assertEqual(idiomas, ["por"] * 16)
            self.assertEqual(run.call_count, 1)

    def test_ocr_instalacao_de_idioma_invalida_cache(self):
        dados = self.ws / "tessdata-ficticio"
        dados.mkdir(exist_ok=True)
        por = dados / "por.traineddata"
        por.unlink(missing_ok=True)
        env = {"TESSDATA_PREFIX": str(dados)}
        with patch.object(self.s.subprocess, "run", side_effect=[
            subprocess.CompletedProcess([], 0, "eng\n", ""),
            subprocess.CompletedProcess([], 0, "por\neng\n", "")
        ]) as run:
            self.assertEqual(self.s.idioma_ocr(env), "eng")
            por.write_text("MODELO FICTICIO", encoding="utf-8")
            self.assertEqual(self.s.idioma_ocr(env), "por")
            self.assertEqual(run.call_count, 2)

    def test_ocr_falha_temporaria_expira_e_nao_aceita_saida_de_erro(self):
        with patch.object(self.s.time, "monotonic", return_value=100) as relogio:
            with patch.object(self.s.subprocess, "run", side_effect=[
                subprocess.CompletedProcess([], 1, "por\n", "erro ficticio"),
                subprocess.CompletedProcess([], 0, "por\n", "")
            ]) as run:
                self.assertIsNone(self.s.idioma_ocr({}))
                self.assertIsNone(self.s.idioma_ocr({}))
                self.assertEqual(run.call_count, 1)
                relogio.return_value = 131
                self.assertEqual(self.s.idioma_ocr({}), "por")

    def test_painel_request_nao_espera_e_nao_duplica_trabalho(self):
        iniciou, liberar = threading.Event(), threading.Event()
        chamadas = []

        def gerar(chave):
            chamadas.append(chave)
            iniciou.set()
            liberar.wait(5)
            self.html.write_text("PAINEL NOVO FICTICIO", encoding="utf-8")
            with self.s._painel_trava:
                self.s._painel_cache.update(chave=chave, gerando=False)

        with patch.object(self.s, "atualizar_painel", side_effect=gerar):
            try:
                antes = time.monotonic()
                r = self.client.get("/painel")
                self.assertLess(time.monotonic() - antes, 2)
                self.assertEqual(r.headers["X-CPJ-Painel"], "atualizando")
                self.assertIn(b"http-equiv='refresh'", r.data)
                self.assertTrue(iniciou.wait(1))
                for _ in range(5):
                    self.assertEqual(self.client.get("/painel").headers["X-CPJ-Painel"], "atualizando")
                self.assertEqual(len(chamadas), 1)
            finally:
                liberar.set()
                self.aguardar()
            with self.client.get("/painel") as pronto:
                self.assertEqual(pronto.headers["X-CPJ-Painel"], "pronto")
                self.assertEqual(pronto.data, b"PAINEL NOVO FICTICIO")
            self.assertEqual(len(chamadas), 1)

    def test_fontes_invalidate_painel_sem_considerar_derivados(self):
        caso = self.ws / "casos" / "OS-TESTE-2099"
        rels = caso / "03-relatorios"
        rels.mkdir(parents=True, exist_ok=True)
        meta = caso / "caso.json"
        meta.write_text('{}', encoding="utf-8")
        inicial = self.s.assinatura_painel()
        (self.prod / "base.json").write_text('{}', encoding="utf-8")
        self.assertEqual(inicial, self.s.assinatura_painel())
        meta.write_text('{"status":"ficticio"}', encoding="utf-8")
        mudou = self.s.assinatura_painel()
        self.assertNotEqual(inicial, mudou)
        (rels / "FINAL-ficticio.md").write_text("MINUTA", encoding="utf-8")
        final = self.s.assinatura_painel()
        self.assertNotEqual(mudou, final)
        (self.prod / "config.json").write_text('{}', encoding="utf-8")
        self.assertNotEqual(final, self.s.assinatura_painel())
        # Esta pasta serve só ao teste de assinaturas, não representa um caso completo.
        (rels / "FINAL-ficticio.md").unlink()
        rels.rmdir()
        meta.unlink()
        caso.rmdir()

    def test_falha_na_geracao_preserva_html_e_aguarda_antes_de_retentar(self):
        def executar(args, **kw):
            if Path(args[1]).name == "indexar.py":
                (self.prod / "base.json").write_text('{"casos":[]}', encoding="utf-8")
                return subprocess.CompletedProcess(args, 0)
            raise subprocess.CalledProcessError(1, args, stderr=b"falha ficticia")

        with patch.object(self.s.subprocess, "run", side_effect=executar) as run:
            with self.assertLogs(self.s.app.logger, level="ERROR"):
                self.s.atualizar_painel(self.s.assinatura_painel())
            self.assertEqual(self.html.read_text(encoding="utf-8"), "PAINEL ANTERIOR FICTICIO")
            r = self.client.get("/painel")
            self.assertEqual(r.status_code, 503)
            self.assertEqual(r.headers["Retry-After"], "30")
            self.assertEqual(run.call_count, 2)
            self.assertEqual(list(self.prod.glob(".painel-*")), [])

    def test_geracao_real_em_workspace_vazio_e_reuso_do_resultado(self):
        self.client.get("/painel")
        self.aguardar()
        self.assertFalse(self.s._painel_cache["erro"])
        with patch.object(self.s.subprocess, "run", side_effect=AssertionError("Reconstrução repetida")):
            for _ in range(3):
                with self.client.get("/painel") as r:
                    self.assertEqual(r.status_code, 200)
                    self.assertEqual(r.headers["X-CPJ-Painel"], "pronto")
                    self.assertIn(b"<html", r.data)


if __name__ == "__main__":
    unittest.main(verbosity=2)
