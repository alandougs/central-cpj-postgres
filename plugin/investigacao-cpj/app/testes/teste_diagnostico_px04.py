"""Regressão PX04: diagnosticar PDFs protegidos e corrompidos separadamente."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from pypdf import PdfWriter


RAIZ = Path(__file__).resolve().parents[4]
SCRIPT = RAIZ / "plugin" / "investigacao-cpj" / "skills" / "pdf-autos-policiais" / "scripts" / "diagnostico.py"


class DiagnosticoPdfProtegidoOuCorrompido(unittest.TestCase):
    def executar(self, caminho):
        resultado = subprocess.run(
            [sys.executable, str(SCRIPT), str(caminho)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=dict(os.environ, PYTHONIOENCODING="utf-8"),
        )
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
        return json.loads(resultado.stdout)

    def test_classifica_pdf_cifrado_como_senha(self):
        with tempfile.TemporaryDirectory(prefix="px04-senha-") as tmp:
            caminho = Path(tmp) / "protegido.pdf"
            writer = PdfWriter()
            writer.add_blank_page(width=72, height=72)
            writer.encrypt("senha-ficticia")
            with caminho.open("wb") as arquivo:
                writer.write(arquivo)

            diagnostico = self.executar(caminho)

        self.assertIn("erro", diagnostico)
        self.assertEqual(diagnostico["motivo_erro"], "senha")
        self.assertIn("senha", diagnostico["erro"].lower())

    def test_classifica_pdf_truncado_como_corrompido(self):
        with tempfile.TemporaryDirectory(prefix="px04-corrompido-") as tmp:
            caminho = Path(tmp) / "truncado.pdf"
            caminho.write_bytes(b"%PDF-1.7\ntruncated")

            diagnostico = self.executar(caminho)

        self.assertIn("erro", diagnostico)
        self.assertEqual(diagnostico["motivo_erro"], "corrompido")
        self.assertIn("corromp", diagnostico["erro"].lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)