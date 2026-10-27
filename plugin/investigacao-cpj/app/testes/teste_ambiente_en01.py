"""EN01: descoberta portátil e OCR de imagem fictícia com PATH sem Tesseract."""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

APP = Path(__file__).resolve().parents[1]
ROOT = APP.parents[2]
SCRIPTS = APP.parent / 'skills/pdf-autos-policiais/scripts'


class AmbientePortatil(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='cpj-en01-')
        cls.ws = Path(cls.tmp.name)
        cls.env = patch.dict(os.environ, {'CPJ_WORKSPACE': str(cls.ws), 'CPJ_SEM_AGENTE_EMBUTIDO': '1', 'CPJ_TESSERACT': ''})
        cls.env.start()
        sys.path.insert(0, str(APP))
        from rotas import comum
        cls.c = comum

    @classmethod
    def tearDownClass(cls):
        cls.env.stop()
        cls.tmp.cleanup()

    def descoberta(self, explicito='', local=True):
        base = self.ws / self._testMethodName
        portatil = base / 'ferramentas/tesseract'
        rival = base / 'rival'
        rival.mkdir(parents=True, exist_ok=True)
        (rival / 'tesseract.exe').write_bytes(b'fixture nao executar')
        if local:
            portatil.mkdir(parents=True, exist_ok=True)
            (portatil / 'tesseract.exe').write_bytes(b'fixture nao executar')
        with patch.object(self.c, 'PLUGIN', str(base / 'plugin/investigacao-cpj')), patch.object(self.c, 'WS', str(base)), patch.dict(os.environ, {'CPJ_TESSERACT': explicito, 'PATH': str(rival)}):
            return Path(self.c._achar_tesseract()), portatil, rival

    def test_portatil_do_projeto_precede_path(self):
        achado, portatil, _ = self.descoberta()
        self.assertEqual(achado, portatil)

    def test_configuracao_explicita_diretorio_ou_executavel_precede_portatil(self):
        explicito = self.ws / 'explicito'
        explicito.mkdir(exist_ok=True)
        exe = explicito / 'tesseract.exe'
        exe.write_bytes(b'fixture nao executar')
        for valor in (explicito, exe):
            with self.subTest(valor=valor):
                achado, _, _ = self.descoberta(str(valor))
                self.assertEqual(achado, explicito)

    def test_portatil_ausente_preserva_fallback_path(self):
        achado, _, rival = self.descoberta(local=False)
        self.assertEqual(achado, rival)

    def test_configuracao_inexistente_permite_portatil(self):
        achado, portatil, _ = self.descoberta(str(self.ws / 'ausente'))
        self.assertEqual(achado, portatil)

    def test_cli_descobre_runtime_local_e_extrai_scan_sem_path_preparado(self):
        from PIL import Image, ImageDraw, ImageFont
        from reportlab.pdfgen import canvas
        from reportlab.lib.utils import ImageReader
        base = self.ws / 'cli'
        scripts = base / 'plugin/investigacao-cpj/skills/pdf-autos-policiais/scripts'
        shutil.copytree(SCRIPTS, scripts, ignore=shutil.ignore_patterns('__pycache__'))
        origem = os.environ.get('CPJ_EN01_ENGINE')
        engine = Path(origem) if origem else ROOT / 'ferramentas/tesseract'
        self.assertTrue((engine / 'tesseract.exe').is_file(), 'EN01 exige runtime real; nao ignorar')
        shutil.copytree(engine, base / 'ferramentas/tesseract')
        tessdata = Path(os.environ.get('TESSDATA_PREFIX', str(ROOT / 'ferramentas/tessdata')))
        idiomas = base / 'ferramentas/tessdata'
        idiomas.mkdir()
        shutil.copy2(tessdata / 'por.traineddata', idiomas)
        imagem = Image.new('RGB', (1700, 800), 'white')
        fonte = ImageFont.truetype(r'C:\Windows\Fonts\arial.ttf', 48)
        ImageDraw.Draw(imagem).text((100, 200), 'ORDEM DE SERVICO 991 / 2099 FICTICIO', font=fonte, fill='black')
        pdf = base / 'scan-ficticio.pdf'
        doc = canvas.Canvas(str(pdf), pagesize=(850, 400))
        doc.drawImage(ImageReader(imagem), 0, 0, width=850, height=400)
        doc.save(); imagem.close()
        antes = hashlib.sha256(pdf.read_bytes()).hexdigest()
        env = dict(os.environ, PATH=str(Path(os.environ['SystemRoot']) / 'System32'), CPJ_WORKSPACE=str(base))
        for nome in ('CPJ_TESSERACT', 'TESSDATA_PREFIX'):
            env.pop(nome, None)
        r = subprocess.run([sys.executable, '-B', '-X', 'utf8', str(scripts / 'extrair.py'), str(pdf), '--saida', str(base / 'saida'), '--ocr', 'tesseract', '--sem-reaproveitar'], env=env, capture_output=True, text=True, encoding='utf-8', timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        texto = (base / 'saida/transcricao.md').read_text(encoding='utf-8')
        self.assertIn('FICTICIO', texto)
        self.assertNotIn('PENDENTE', texto)
        self.assertEqual(hashlib.sha256(pdf.read_bytes()).hexdigest(), antes)


if __name__ == '__main__':
    unittest.main(verbosity=2)
