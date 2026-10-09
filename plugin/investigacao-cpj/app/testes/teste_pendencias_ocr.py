#!/usr/bin/env python3
"""Teste do backend para a varredura e processamento em lote de pendências de OCR (AG06)."""
import io
import json
import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.servidor import app

from rotas.comum import C
from rotas import comum

class TestePendenciasOCR(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="cpj-teste-pendencias-")
        self.ws_patcher2 = patch("rotas.comum.WS", self.tmp)
        self.ws_patcher3 = patch("rotas.comum.C.CASOS", os.path.join(self.tmp, "casos"))
        self.ws_patcher4 = patch("rotas.comum.C.MODELO", os.path.join(self.tmp, "casos", "_MODELO-CASO"))
        self.ws_patcher2.start()
        self.ws_patcher3.start()
        self.ws_patcher4.start()
        
        modelo = Path(self.tmp) / "casos" / "_MODELO-CASO"
        for p in ("00-originais", "01-extracao", "02-analise", "03-relatorios"):
            (modelo / p).mkdir(parents=True)
        (modelo / "caso.json").write_text(json.dumps({"datas": {}}))
        
        from rotas.comum import auth
        auth.salvar_usuario("admin", "Admin", "admin", "SenhaFicticia123")
        
        app.config["TESTING"] = True
        self.client = app.test_client()
        
        # Login
        r = self.client.post("/api/entrar", json={"login": "admin", "senha": "SenhaFicticia123"}, headers={"X-CPJ": "1"})
        self.assertTrue(r.status_code == 200)

    def tearDown(self):
        self.ws_patcher2.stop()
        self.ws_patcher3.stop()
        self.ws_patcher4.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_varredura_e_processamento_lote(self):
        # 1. Cria um caso
        id_ = "OS-999-2099"
        C.novo("999/2099", "123", "", "", "", id_=id_)
        orig_dir = os.path.join(self.tmp, "casos", id_, "00-originais")
        os.makedirs(orig_dir, exist_ok=True)
        
        # Cria arquivos:
        # doc1.pdf: pendente
        # doc2.md: com transcricao (não deve aparecer)
        # doc3.pdf: já na fila (não deve aparecer)
        
        with open(os.path.join(orig_dir, "doc1.pdf"), "w") as f: f.write("PDF 1")
        with open(os.path.join(orig_dir, "doc2.md"), "w") as f: f.write("MD 1")
        with open(os.path.join(orig_dir, "doc3.pdf"), "w") as f: f.write("PDF 3")
        
        # Simula extração pronta para doc2
        ext_dir = os.path.join(self.tmp, "casos", id_, "01-extracao", "doc2")
        os.makedirs(ext_dir, exist_ok=True)
        with open(os.path.join(ext_dir, "transcricao.md"), "w") as f: f.write("Feito")
        
        # Simula doc3 na fila
        proc = {"trabalhos": [{"doc": "doc3", "arquivo": "doc3.pdf", "status": "na_fila"}]}
        with open(os.path.join(self.tmp, "casos", id_, "processamento.json"), "w", encoding="utf-8") as f:
            json.dump(proc, f)
            
        # 2. Testa varredura
        r = self.client.get("/api/pendencias-ocr", headers={"X-CPJ": "1"})
        self.assertEqual(r.status_code, 200)
        p = r.json.get("pendentes", [])
        self.assertEqual(len(p), 1)
        self.assertEqual(p[0]["arquivo"], "doc1.pdf")
        self.assertEqual(p[0]["doc"], "doc1")
        
        # 3. Testa lote com entrada inválida
        r = self.client.post("/api/pendencias-ocr/processar", json=[
            {"caso": "invalido", "arquivo": "doc1.pdf", "doc": "doc1"}
        ], headers={"X-CPJ": "1"})
        self.assertEqual(r.status_code, 200)
        res = r.json.get("resultados", [])
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["status"], "erro")
        
        # 4. Testa lote válido
        with patch("rotas.casos.enfileirar") as mock_enf:
            r = self.client.post("/api/pendencias-ocr/processar", json=[
                {"caso": id_, "arquivo": "doc1.pdf", "doc": "doc1"}
            ], headers={"X-CPJ": "1"})
            self.assertEqual(r.status_code, 200)
            res = r.json.get("resultados", [])
            self.assertEqual(len(res), 1)
            self.assertEqual(res[0]["status"], "enfileirado")
            mock_enf.assert_called_once_with(id_, "doc1", "doc1.pdf")

if __name__ == "__main__":
    unittest.main()
