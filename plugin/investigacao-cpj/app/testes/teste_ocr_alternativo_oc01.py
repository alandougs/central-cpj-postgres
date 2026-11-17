"""OC01: segundo motor de OCR local (RapidOCR/ONNX, modelo latino) forçável no extrator; somente fixtures TEMP."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

APP = Path(__file__).resolve().parents[1]
EXTRAIR = APP.parent / "skills/pdf-autos-policiais/scripts/extrair.py"

try:
    import rapidocr  # noqa: F401
    TEM_RAPIDOCR = True
except ImportError:
    TEM_RAPIDOCR = False


def pdf_escaneado(caminho):
    """PDF só com imagem (sem camada de texto), como uma página digitalizada."""
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (1700, 700), "white")
    d = ImageDraw.Draw(img)
    try:
        fonte = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 44)
    except OSError:
        fonte = ImageFont.load_default(size=44)
    d.text((60, 80), "Relatório de Investigação fictício", fill="black", font=fonte)
    d.text((60, 220), "Transferência Pix de R$ 1.234,56 em 05/10/2026", fill="black", font=fonte)
    d.text((60, 360), "Ação de teste sem dados reais", fill="black", font=fonte)
    img.save(caminho, "PDF", resolution=200)


def extrair(pdf, saida, *extra, env=None):
    return subprocess.run([sys.executable, "-B", "-X", "utf8", str(EXTRAIR), str(pdf), "--saida", str(saida),
                           "--sem-reaproveitar", *extra], capture_output=True, text=True, encoding="utf-8",
                          env=env or dict(os.environ), timeout=600)


class MotorAlternativo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="cpj-ocr-oc01-")
        self.base = Path(self.tmp.name)
        self.pdf = self.base / "escaneado.pdf"
        pdf_escaneado(self.pdf)
        self.env = dict(os.environ, CPJ_WORKSPACE=str(self.base))

    def tearDown(self):
        self.tmp.cleanup()

    def test_opcao_aparece_na_ajuda(self):
        r = subprocess.run([sys.executable, "-B", "-X", "utf8", str(EXTRAIR), "--help"], capture_output=True, text=True, encoding="utf-8")
        self.assertIn("rapidocr", r.stdout)

    @unittest.skipUnless(TEM_RAPIDOCR, "rapidocr não instalado")
    def test_rapidocr_forcado_transcreve_portugues_e_registra_metodo(self):
        saida = self.base / "saida"
        r = extrair(self.pdf, saida, "--ocr", "rapidocr", env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr[-2000:])
        md = (saida / "transcricao.md").read_text(encoding="utf-8")
        for trecho in ("Investigação", "1.234,56", "05/10/2026", "Ação"):
            self.assertIn(trecho, md)
        self.assertIn("método: ocr-rapidocr | confiança OCR", md)
        rel = json.loads(r.stdout[r.stdout.find("{"):])
        self.assertEqual(rel["metodos"], {"ocr-rapidocr": 1})
        self.assertTrue(rel["ferramentas"]["ocr"].startswith("rapidocr"))
        self.assertEqual(rel["pendentes_transcricao_visual"], [])
        # Retomada pelo checkpoint com o mesmo motor não refaz o OCR.
        r2 = extrair(self.pdf, saida, "--ocr", "rapidocr", env=self.env)
        self.assertEqual(r2.returncode, 0, r2.stderr[-2000:])
        self.assertIn("1 de 1 página(s) reaproveitada(s)", r2.stderr)

    def test_rapidocr_ausente_falha_com_mensagem_clara(self):
        codigo = ("import os,sys,runpy;sys.modules['rapidocr']=None;sys.path.insert(0,os.path.dirname(sys.argv[1]));"
                  "sys.argv=[sys.argv[1],sys.argv[2],'--saida',sys.argv[3],'--ocr','rapidocr','--sem-reaproveitar'];"
                  "runpy.run_path(sys.argv[0],run_name='__main__')")
        r = subprocess.run([sys.executable, "-B", "-X", "utf8", "-c", codigo, str(EXTRAIR), str(self.pdf), str(self.base / "s2")],
                           capture_output=True, text=True, encoding="utf-8", env=self.env, timeout=120)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("RapidOCR indisponível", r.stderr)
        self.assertFalse((self.base / "s2" / "transcricao.md").exists())


from unittest.mock import MagicMock, patch  # noqa: E402
from astra_fixture import AstraFixture  # noqa: E402


class FilaComMotor(AstraFixture, unittest.TestCase):
    """O motor escolhido no reprocessamento acompanha o item da fila até a chamada do extrator."""

    def test_enfileirar_guarda_motor_e_processar_repassa_ao_extrator(self):
        from rotas import comum
        doc, arq = "doc-ficticio", "doc-ficticio.pdf"
        (self.ws / "casos" / self.caso / "00-originais" / arq).write_bytes(b"%PDF-1.4 ficticio")
        fluxos = MagicMock()
        fluxos.registrar_extracao.return_value = {"id": "etapa-ficticia"}
        with patch.object(comum, "fluxos", return_value=fluxos), patch.object(comum.fila, "put") as put:
            comum.enfileirar(self.caso, doc, arq, modo="rapido", usuario="astra_ficticio", ocr="rapidocr")
            with self.assertRaises(ValueError):
                comum.enfileirar(self.caso, doc, arq, modo="rapido", ocr="motor-inexistente")
        item = comum.ler_proc_item(self.caso, doc)
        self.assertEqual(item["ocr"], "rapidocr")
        self.assertEqual(put.call_args.args[0]["ocr"], "rapidocr")
        chamadas = []

        def rodar(cmd, *args, **kw):
            chamadas.append(cmd)
            if cmd[1].endswith("diagnostico.py"):
                return '{"paginas": 1}'
            raise RuntimeError("parada fictícia após montar o comando")
        with patch.object(comum, "rodar", side_effect=rodar):
            comum.processar(put.call_args.args[0])
        extrair_cmd = next(c for c in chamadas if c[1].endswith("extrair.py"))
        self.assertEqual(extrair_cmd[-2:], ["--ocr", "rapidocr"])
        self.assertEqual(comum.ler_proc_item(self.caso, doc)["status"], "erro")

    def test_rota_reprocessar_repassa_motor_e_recusa_invalido(self):
        from rotas import comum
        doc, arq = "doc-rota", "doc-rota.md"
        comum.gravar_proc(self.caso, {"trabalhos": [{"doc": doc, "arquivo": arq, "status": "erro", "modo": "rapido"}]})
        url = f"/api/casos/{self.caso}/reprocessar/{doc}"
        with patch("rotas.casos.enfileirar") as enf:
            r = self.post(url, {"modo": "rapido", "ocr": "rapidocr"})
            self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
            self.assertEqual(enf.call_args.kwargs["ocr"], "rapidocr")
            self.assertEqual(self.post(url, {"modo": "rapido"}).status_code, 200)
            self.assertIsNone(enf.call_args.kwargs["ocr"])
            self.assertEqual(self.post(url, {"modo": "rapido", "ocr": "motor-inexistente"}).status_code, 400)
            self.assertEqual(enf.call_count, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
