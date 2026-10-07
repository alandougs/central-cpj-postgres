"""Testes de equivalência e limite de concorrência da extração F02."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfReader, PdfWriter

ROOT = Path(__file__).resolve().parents[4]
EXTRAIR = ROOT / "plugin/investigacao-cpj/skills/pdf-autos-policiais/scripts/extrair.py"


def tesseract_local():
    candidatos = [
        os.environ.get("CPJ_TESSERACT"),
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files\PDF24\tesseract\tesseract.exe",
        shutil.which("tesseract"),
    ]
    return next((p for p in candidatos if p and Path(p).is_file()), None)


def gerar_pdf_ficticio(destino):
    """Cria páginas escaneadas determinísticas, sem dados de caso."""
    paginas = []
    try:
        fonte = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf" if os.name == "nt" else "DejaVuSans.ttf", 30)
    except OSError:
        fonte = ImageFont.load_default()
    for numero in range(1, 5):
        imagem = Image.new("RGB", (900, 1200), "white")
        ImageDraw.Draw(imagem).text(
            (60, 80), f"DOCUMENTO FICTICIO PAGINA {numero}", fill="black", font=fonte
        )
        paginas.append(imagem)
    paginas[0].save(destino, "PDF", save_all=True, append_images=paginas[1:], resolution=120)


@unittest.skipUnless(tesseract_local(), "Tesseract local indisponível; teste de OCR ignorado")
class TesteDesempenhoF02(unittest.TestCase):
    def test_paralelismo_preserva_texto_e_metodos(self):
        with tempfile.TemporaryDirectory(prefix="cpj-f02-teste-") as tmp:
            base = Path(tmp)
            pdf = base / "ficticio.pdf"
            gerar_pdf_ficticio(pdf)
            saidas = {}
            env = os.environ.copy()
            tessdata = ROOT / "ferramentas/tessdata"
            if (tessdata / "por.traineddata").is_file() and (tessdata / "por.traineddata").stat().st_size > 0:
                env["TESSDATA_PREFIX"] = str(tessdata)
            exe = tesseract_local()
            if exe:
                env["PATH"] = str(Path(exe).parent) + os.pathsep + env.get("PATH", "")

            for workers in (1, 2):
                destino = base / f"saida-{workers}"
                proc = subprocess.run(
                    [sys.executable, "-X", "utf8", str(EXTRAIR), str(pdf),
                     "--saida", str(destino), "--ocr", "tesseract", "--lang", "por",
                     "--workers", str(workers)],
                    cwd=ROOT, env=env, capture_output=True, text=True, timeout=180,
                )
                self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
                relatorio = json.loads((destino / "relatorio_extracao.json").read_text(encoding="utf-8"))
                texto = (destino / "transcricao.md").read_text(encoding="utf-8")
                self.assertEqual(relatorio["ocr_workers"], workers)
                self.assertEqual(relatorio["metodos"], {"ocr-tesseract": 4})
                self.assertEqual(texto.count("## Página "), 4)
                texto = "\n".join(
                    linha.split(" | Gerado em:", 1)[0] if " | Gerado em:" in linha else linha
                    for linha in texto.splitlines()
                )
                saidas[workers] = (texto, relatorio["metodos"])

            self.assertEqual(saidas[1], saidas[2])


if __name__ == "__main__":
    unittest.main(verbosity=2)
