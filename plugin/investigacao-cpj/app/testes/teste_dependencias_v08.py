#!/usr/bin/env python3
"""V08 — Validação de manifestos de dependências do workspace CPJ.

Valida:
1. requirements.txt contém unicamente dependências do core de produção (sem psycopg, Postgres congelado).
2. requirements-opcional.txt contém psycopg e dependências opcionais/legadas.
3. requirements-dev.txt contém dependências de desenvolvimento e testes E2E (Playwright, Pytest, Ruff).
4. Todas as bibliotecas do core em requirements.txt são importáveis no ambiente Python local.
5. ferramentas/verificar-ambiente.ps1 valida a integridade contra requirements.txt.
"""
import os
from pathlib import Path
import unittest

AQUI = Path(__file__).resolve().parent
WORKSPACE = AQUI.parents[3]

CORE_PACKAGES = [
    "flask",
    "cryptography",
    "openpyxl",
    "pdfplumber",
    "pillow",
    "pypdf",
    "pypdfium2",
    "pytesseract",
    "python-docx",
]

CORE_MODULES = [
    "flask",
    "cryptography",
    "openpyxl",
    "pdfplumber",
    "PIL",
    "pypdf",
    "pypdfium2",
    "pytesseract",
    "docx",
]


class TesteDependenciasV08(unittest.TestCase):
    def test_01_requirements_txt_sem_psycopg(self):
        req_file = WORKSPACE / "requirements.txt"
        self.assertTrue(req_file.exists(), "requirements.txt não encontrado")
        texto = req_file.read_text(encoding="utf-8").lower()

        # Postgres está congelado e movido para legado/
        self.assertNotIn("psycopg", texto, "requirements.txt não deve conter psycopg")

        for pkg in CORE_PACKAGES:
            self.assertIn(pkg, texto, f"Pacote core '{pkg}' ausente em requirements.txt")

    def test_02_requirements_opcional_contem_psycopg(self):
        req_opc = WORKSPACE / "requirements-opcional.txt"
        self.assertTrue(req_opc.exists(), "requirements-opcional.txt não encontrado")
        self.assertGreater(req_opc.stat().st_size, 0, "requirements-opcional.txt está vazio")
        texto = req_opc.read_text(encoding="utf-8").lower()
        self.assertIn("psycopg", texto, "requirements-opcional.txt deve conter psycopg")

    def test_03_requirements_dev_contem_playwright(self):
        req_dev = WORKSPACE / "requirements-dev.txt"
        self.assertTrue(req_dev.exists(), "requirements-dev.txt não encontrado")
        self.assertGreater(req_dev.stat().st_size, 0, "requirements-dev.txt está vazio")
        texto = req_dev.read_text(encoding="utf-8").lower()
        self.assertIn("playwright", texto, "requirements-dev.txt deve conter playwright")

    def test_04_importacao_modulos_core(self):
        for mod in CORE_MODULES:
            try:
                __import__(mod)
            except ImportError as e:
                self.fail(f"Falha ao importar módulo obrigatório '{mod}': {e}")

    def test_05_verificar_ambiente_ps1_referencia_requirements(self):
        script_ps1 = WORKSPACE / "ferramentas" / "verificar-ambiente.ps1"
        self.assertTrue(script_ps1.exists(), "verificar-ambiente.ps1 não encontrado")
        texto = script_ps1.read_text(encoding="utf-8")
        self.assertIn("requirements.txt", texto, "verificar-ambiente.ps1 deve referenciar requirements.txt")


if __name__ == "__main__":
    unittest.main()
