"""ENV04: diagnóstico usa a venv local e checkpoint descobre OCR do PDF24."""
import ast
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]


class Ambiente(unittest.TestCase):
    def test_diagnostico_prefere_venv_sem_python_no_path(self):
        fonte = (ROOT / "ferramentas/verificar-ambiente.ps1").read_text(encoding="utf-8")
        preambulo = fonte.split("Item 'Python'", 1)[0]
        with tempfile.TemporaryDirectory(prefix="cpj-env04-") as td:
            ws = Path(td)
            (ws / "ferramentas").mkdir()
            exe = ws / ".venv/Scripts/python.exe"
            exe.parent.mkdir(parents=True)
            exe.write_bytes(b"fixture ficticia, nao executada")
            script = ws / "ferramentas/probe.ps1"
            script.write_text(preambulo + '\nWrite-Output ("PY=" + $PY)\n', encoding="utf-8-sig")
            r = subprocess.run([shutil.which("powershell"), "-NoProfile", "-ExecutionPolicy", "Bypass",
                                "-File", str(script)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("PY=" + str(exe), r.stdout)

    def test_checkpoint_descobre_pdf24_sem_tesseract_no_path(self):
        arquivo = ROOT / "plugin/investigacao-cpj/app/testes/teste_ocr_checkpoint_claude.py"
        arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
        nodes = []
        for node in arvore.body:
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) and ast.unparse(node.value.func) == "os.environ.update":
                break
            nodes.append(node)
        pdf24 = r"C:\Program Files\PDF24\tesseract"
        with tempfile.TemporaryDirectory(prefix="cpj-env04-ocr-") as td:
            with patch.dict(os.environ, {"PATH": "fixture-sem-ocr"}, clear=True), \
                 patch("tempfile.mkdtemp", return_value=td), \
                 patch("os.path.isdir", side_effect=lambda p: str(p) == pdf24), \
                 patch("os.path.isfile", side_effect=lambda p: str(p) == os.path.join(pdf24, "tesseract.exe")):
                namespace = {"__file__": str(arquivo)}
                exec(compile(ast.Module(body=nodes, type_ignores=[]), str(arquivo), "exec"), namespace)
                self.assertIn(pdf24, namespace["env"]["PATH"].split(os.pathsep))


if __name__ == "__main__":
    unittest.main(verbosity=2)
