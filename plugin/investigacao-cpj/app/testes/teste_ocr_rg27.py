"""RG27: seleção consistente e OCR português real, somente fixtures TEMP."""
import gc
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

APP = Path(__file__).resolve().parents[1]
SCRIPTS = APP.parent / "skills/pdf-autos-policiais/scripts"


from teste_extracao_markdown_md01 import estado as estado_md01

class OCRPortugues(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="cpj-ocr-rg27-")
        cls.ws = Path(cls.tmp.name)
        cls.ambiente = patch.dict(os.environ, {"CPJ_WORKSPACE": str(cls.ws), "CPJ_SEM_AGENTE_EMBUTIDO": "1", "CPJ_IA_LOCAL_MODELO": ""})
        cls.ambiente.start()
        sys.path.insert(0, str(APP))
        from rotas import comum
        cls.c = comum

    @classmethod
    def tearDownClass(cls):
        gc.collect()
        cls.tmp.cleanup()
        cls.ambiente.stop()

    def test_engine_preferido_tem_prioridade_sobre_outro_no_path(self):
        with tempfile.TemporaryDirectory(dir=self.ws) as d:
            base = Path(d)
            preferido, rival = base / "preferido", base / "rival"
            for p in (preferido, rival):
                p.mkdir()
                exe = p / ("tesseract.exe" if os.name == "nt" else "tesseract")
                exe.write_bytes(b"fixture de descoberta; nao executar")
                exe.chmod(0o700)
            with patch.object(self.c, "TESS_DIR", str(preferido)), patch.dict(os.environ, {"PATH": str(rival)}):
                env = self.c.ambiente_ocr()
                achado = shutil.which("tesseract", path=env["PATH"])
                self.assertEqual(Path(achado).parent, preferido, "Probe e subprocesso precisam selecionar o mesmo engine")

    def test_prefixo_de_idioma_explicito_e_preservado_sem_pacote_local(self):
        with patch.object(self.c, "TESSDATA_LOCAL", str(self.ws / "sem-idioma")), patch.dict(os.environ, {"TESSDATA_PREFIX": "idioma-explicito-ficticio"}):
            self.assertEqual(self.c.ambiente_ocr()["TESSDATA_PREFIX"], "idioma-explicito-ficticio")

    def test_fixture_imagem_executa_ocr_portugues_e_parser_sem_alterar_original(self):
        from PIL import Image, ImageDraw, ImageFont
        from reportlab.lib.utils import ImageReader
        from reportlab.pdfgen import canvas
        env = self.c.ambiente_ocr()
        exe = shutil.which("tesseract", path=env.get("PATH"))
        self.assertIsNotNone(exe, "RG27 exige engine Tesseract real; nao ignorar este teste")
        idiomas = subprocess.run([exe, "--list-langs"], env=env, capture_output=True, text=True, timeout=20)
        self.assertEqual(idiomas.returncode, 0, idiomas.stderr)
        self.assertIn("por", idiomas.stdout.split(), "RG27 exige idioma portugues real")
        with tempfile.TemporaryDirectory(dir=self.ws) as d:
            base = Path(d)
            pdf = base / "scan-ficticio.pdf"
            imagem = Image.new("RGB", (1700, 900), "white")
            fonte = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf" if os.name == "nt" else "DejaVuSans.ttf", 42)
            desenho = ImageDraw.Draw(imagem)
            for i, linha in enumerate(("Ordem de Servico: 992/2099", "Escrivao do feito: ESCRIVAO FICTICIO", "Natureza: Estelionato ficticio")):
                desenho.text((80, 100 + 100*i), linha, font=fonte, fill="black")
            doc = canvas.Canvas(str(pdf), pagesize=(850, 450))
            doc.drawImage(ImageReader(imagem), 0, 0, width=850, height=450); doc.save(); imagem.close()
            antes = hashlib.sha256(pdf.read_bytes()).hexdigest()
            destino = base / "extraido"
            r = subprocess.run([sys.executable, "-X", "utf8", str(SCRIPTS / "extrair.py"), str(pdf), "--saida", str(destino),
                                "--ocr", "tesseract", "--lang", "por", "--sem-reaproveitar"], env=env,
                               capture_output=True, text=True, encoding="utf-8", timeout=60)
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            rel = estado_md01.ler(destino, "relatorio_extracao.json")
            self.assertEqual(rel["ferramentas"]["ocr"], "tesseract (por)")
            self.assertEqual(rel["metodos"], {"ocr-tesseract": 1})
            texto = (destino / "transcricao.md").read_text(encoding="utf-8")
            campos, conflitos = self.c.D_OS.extrair(texto, pdf.name)
            self.assertFalse(conflitos)
            self.assertEqual(campos["escrivao"]["valor"], "ESCRIVAO FICTICIO")
            self.assertEqual(campos["ordem_servico"]["valor"], "992/2099")
            self.assertEqual(campos["escrivao"]["pagina"], 1)
            self.assertEqual(hashlib.sha256(pdf.read_bytes()).hexdigest(), antes)


if __name__ == "__main__": unittest.main(verbosity=2)
