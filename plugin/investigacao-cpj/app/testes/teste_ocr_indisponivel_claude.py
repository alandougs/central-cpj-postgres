#!/usr/bin/env python3
"""OCR01: sem Tesseract, o processamento não pode terminar em silêncio.

Dados fictícios em workspace temporário. Executar:
python -X utf8 plugin/investigacao-cpj/app/testes/teste_ocr_indisponivel_claude.py
"""
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.servidor import app

from rotas.comum import C
from rotas import comum

ID = "OS-998-2099"


def relatorio(ocr, pendentes):
    return {
        "arquivo": "autos.pdf", "sha256_original": "0" * 64, "paginas": 3,
        "ferramentas": {"texto": "pypdfium2", "ocr": ocr},
        "metodos": {"texto-nativo": 3 - len(pendentes), "pendente-transcricao-visual": len(pendentes)},
        "pendentes_transcricao_visual": pendentes, "conferir_visualmente": [],
    }


class BaseOCR(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="cpj-teste-ocr01-")
        self.patches = [
            patch("rotas.comum.WS", self.tmp),
            patch("rotas.comum.C.CASOS", os.path.join(self.tmp, "casos")),
            patch("rotas.comum.C.MODELO", os.path.join(self.tmp, "casos", "_MODELO-CASO")),
        ]
        for p in self.patches:
            p.start()
        modelo = Path(self.tmp) / "casos" / "_MODELO-CASO"
        for p in ("00-originais", "01-extracao", "02-analise", "03-relatorios"):
            (modelo / p).mkdir(parents=True)
        (modelo / "caso.json").write_text(json.dumps({"datas": {}}))
        C.novo("998/2099", "123", "", "", "", id_=ID)
        self.caso = Path(self.tmp) / "casos" / ID
        (self.caso / "00-originais" / "autos.pdf").write_bytes(b"%PDF-1.4 ficticio")

    def tearDown(self):
        for p in self.patches:
            p.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)


class TesteProcessarSemOCR(BaseOCR):
    def _processar(self, ocr, pendentes, limitacao_previa=None, plano=()):
        comum.gravar_proc(ID, {"trabalhos": [{"doc": "autos", "arquivo": "autos.pdf", "status": "na_fila", "limitacao": limitacao_previa}]})

        def rodar_falso(cmd, env, log, progresso=None, chave=None):
            script = os.path.basename(cmd[1])
            if script == "diagnostico.py":
                return json.dumps({"paginas": 3})
            if script == "extrair.py":
                dest = Path(cmd[cmd.index("--saida") + 1])
                (dest / "transcricao.md").write_text("## Página 1\nTexto fictício.\n", encoding="utf-8")
                (dest / "relatorio_extracao.json").write_text(json.dumps(relatorio(ocr, pendentes)), encoding="utf-8")
            return ""

        with patch.object(comum, "rodar", rodar_falso), patch.object(comum, "idioma_ocr", return_value=None), \
             patch.object(comum.D_OS, "aplicar"), patch.object(comum.C, "importar_ip"), \
             patch.object(comum, "plano_transcricao_visual", return_value=list(plano)):
            comum.processar({"caso": ID, "doc": "autos", "arquivo": "autos.pdf", "modo": "inteligente", "usuario": "teste",
                             "limitacao": limitacao_previa})
        return comum.ler_proc(ID)["trabalhos"][0]

    def test_sem_tesseract_preserva_limitacao_previa_do_job(self):
        t = self._processar("indisponível", [2], limitacao_previa="Limitação fictícia do envio.")
        self.assertIn("Limitação fictícia do envio.", t["limitacao"])
        self.assertIn("OCR indisponível", t["limitacao"])

    def test_sem_tesseract_com_plano_visual_mantem_os_dois_avisos(self):
        t = self._processar("indisponível", [2], plano=[{"documento": "autos", "paginas": [2]}])
        self.assertIn("OCR indisponível", t["limitacao"])
        self.assertIn("transcrição visual pendente", t["limitacao"])

    def test_aviso_menciona_idioma_alem_do_tesseract(self):
        t = self._processar("indisponível", [2])
        self.assertIn("idioma", t["limitacao"])

    def test_sem_tesseract_registra_limitacao_no_job(self):
        t = self._processar("indisponível", [2, 3])
        self.assertEqual(t["status"], "concluido")
        self.assertIn("OCR indisponível", t.get("limitacao") or "")
        self.assertIn("2 página(s)", t.get("limitacao") or "")

    def test_sem_tesseract_registra_no_registro_de_tratamento(self):
        self._processar("indisponível", [2, 3])
        registro = (self.caso / "registro-tratamento.md").read_text(encoding="utf-8")
        self.assertIn("OCR indisponível", registro)

    def test_com_tesseract_nao_registra_limitacao(self):
        t = self._processar("tesseract (por)", [])
        self.assertEqual(t["status"], "concluido")
        self.assertFalse(t.get("limitacao"))


class TestePendenciasSemOCR(BaseOCR):
    def setUp(self):
        super().setUp()
        from rotas.comum import auth
        auth.salvar_usuario("admin", "Admin", "admin", "SenhaFicticia123")
        app.config["TESTING"] = True
        self.client = app.test_client()
        r = self.client.post("/api/entrar", json={"login": "admin", "senha": "SenhaFicticia123"}, headers={"X-CPJ": "1"})
        self.assertEqual(r.status_code, 200)

    def _extracao(self, doc, ocr, pendentes):
        (self.caso / "00-originais" / f"{doc}.pdf").write_bytes(b"%PDF-1.4 ficticio")
        d = self.caso / "01-extracao" / doc
        d.mkdir(parents=True, exist_ok=True)
        (d / "transcricao.md").write_text("Texto fictício.", encoding="utf-8")
        (d / "relatorio_extracao.json").write_text(json.dumps(relatorio(ocr, pendentes)), encoding="utf-8")

    def _pendentes(self):
        r = self.client.get("/api/pendencias-ocr", headers={"X-CPJ": "1"})
        self.assertEqual(r.status_code, 200)
        return {p["arquivo"]: p for p in r.json["pendentes"]}

    def test_lista_transcricao_feita_sem_ocr(self):
        self._extracao("autos", "indisponível", [5, 6])
        p = self._pendentes()
        self.assertIn("autos.pdf", p)
        self.assertIn("OCR", p["autos.pdf"].get("motivo") or "")

    def test_nao_lista_transcricao_com_ocr(self):
        self._extracao("autos", "tesseract (por)", [])
        self.assertNotIn("autos.pdf", self._pendentes())

    def test_relatorio_malformado_nao_derruba_a_varredura(self):
        self._extracao("autos", "indisponível", [5])
        (self.caso / "01-extracao" / "autos" / "relatorio_extracao.json").write_text("[1, 2]", encoding="utf-8")
        self._extracao("outro", "indisponível", [1])
        self.assertIn("outro.pdf", self._pendentes())

    def test_nao_lista_sem_ocr_quando_todas_paginas_tem_texto(self):
        self._extracao("autos", "indisponível", [])
        self.assertNotIn("autos.pdf", self._pendentes())


if __name__ == "__main__":
    unittest.main()
