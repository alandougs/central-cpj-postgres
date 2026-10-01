#!/usr/bin/env python3
"""Testes fictícios para o fluxograma financeiro inserido no DOCX."""
import csv
import importlib.util
from pathlib import Path
import tempfile
import unittest

from PIL import Image


AQUI = Path(__file__).resolve().parent
ROOT = AQUI.parents[3]
SCRIPT = ROOT / "plugin" / "investigacao-cpj" / "skills" / "relatorio-ip-fraude" / "scripts" / "gerar_diagrama_financeiro.py"
TEMP_ROOT = ROOT / ".tmp-testes-diagrama"


def modulo_diagrama():
    spec = importlib.util.spec_from_file_location("diagrama_financeiro_teste", SCRIPT)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


class TesteDiagramaFinanceiro(unittest.TestCase):
    def test_carrega_csv_e_gera_png_com_dados_documentados(self):
        TEMP_ROOT.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="cpj-diagrama-", dir=TEMP_ROOT) as tmp:
            pasta = Path(tmp)
            origem = pasta / "fluxo-financeiro.csv"
            saida = pasta / "fluxo.png"
            campos = [
                "seq", "data", "valor", "meio", "origem_titular", "origem_banco",
                "destino_titular", "destino_banco", "camada", "fonte_pag", "fls",
                "status_conferencia",
            ]
            with origem.open("w", newline="", encoding="utf-8-sig") as arquivo:
                escritor = csv.DictWriter(arquivo, fieldnames=campos, delimiter=";")
                escritor.writeheader()
                escritor.writerow({
                    "seq": "1", "data": "10/03/2026", "valor": "1234,56", "meio": "PIX",
                    "origem_titular": "VÍTIMA FICTÍCIA", "origem_banco": "BANCO FICTÍCIO",
                    "destino_titular": "RECEBEDOR FICTÍCIO", "destino_banco": "BANCO TESTE",
                    "camada": "1", "fonte_pag": "12", "fls": "14", "status_conferencia": "conferido",
                })

            modulo = modulo_diagrama()
            transacoes = modulo.carregar_transacoes(origem)
            resultado = modulo.desenhar_diagrama(transacoes, saida, caso_id="OS-TESTE-2026", dpi=300)

            self.assertEqual(Path(resultado), saida)
            self.assertTrue(saida.is_file())
            with Image.open(saida) as imagem:
                self.assertEqual(imagem.format, "PNG")
                self.assertGreaterEqual(imagem.info["dpi"][0], 299)
                self.assertGreater(imagem.width, 600)
                self.assertGreater(imagem.height, 300)

    def test_ignora_linha_sem_valor_documentado(self):
        TEMP_ROOT.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="cpj-diagrama-", dir=TEMP_ROOT) as tmp:
            origem = Path(tmp) / "vazio.csv"
            origem.write_text("valor;origem_titular;destino_titular\n;ORIGEM;DESTINO\n", encoding="utf-8-sig")
            self.assertEqual(modulo_diagrama().carregar_transacoes(origem), [])

    def _gerar_docx(self, nome_caso, csv_texto):
        """Roda gerar_docx.py num workspace temporário com o modelo oficial copiado; devolve (processo, pasta de relatórios)."""
        import os
        import shutil
        import subprocess
        import sys
        modelos = ROOT / "modelos"
        if not (modelos / "MODELO RELATORIO DE INVESTIGACAO - CPJ 2026.docx").is_file():
            self.skipTest("modelo DOCX oficial não está neste workspace")
        sys.path.insert(0, str(AQUI))
        from teste_gate_v04 import LIMPA
        TEMP_ROOT.mkdir(exist_ok=True)
        tmp = tempfile.TemporaryDirectory(prefix="cpj-diagrama-docx-", dir=TEMP_ROOT, ignore_cleanup_errors=True)
        self.addCleanup(tmp.cleanup)
        ws = Path(tmp.name)
        (ws / "modelos").mkdir()
        for arq in modelos.iterdir():
            if arq.is_file():
                shutil.copy(arq, ws / "modelos" / arq.name)
        caso = ws / "casos" / nome_caso
        (caso / "03-relatorios").mkdir(parents=True)
        (caso / "02-analise").mkdir()
        if csv_texto is not None:
            (caso / "02-analise" / "fluxo-financeiro.csv").write_text(csv_texto, encoding="utf-8-sig")
        minuta = caso / "03-relatorios" / "minuta-v01.md"
        minuta.write_text(LIMPA, encoding="utf-8")
        saida = caso / "03-relatorios" / "RELATORIO.docx"
        env = dict(os.environ, CPJ_WORKSPACE=str(ws), PYTHONIOENCODING="utf-8")
        gerar = ROOT / "plugin" / "investigacao-cpj" / "skills" / "relatorio-ip-fraude" / "scripts" / "gerar_docx.py"
        r = subprocess.run([sys.executable, str(gerar), str(minuta), "--saida", str(saida)], cwd=str(ws), env=env,
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        return r, caso / "03-relatorios", saida

    def test_docx_recebe_o_fluxograma_do_csv_do_caso(self):
        csv_texto = ("seq;data;valor;origem_titular;destino_titular;origem_banco;destino_banco;fonte_pag;fls\n"
                     "1;10/03/2026;1500,00;VITIMA FICTICIA;RECEBEDOR FICTICIO;BANCO A;BANCO B;2;4\n")
        r, pasta, saida = self._gerar_docx("OS-950-2099", csv_texto)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("Aviso ao gerar fluxograma", r.stderr)
        self.assertTrue(list(pasta.glob("FLUXO-FINANCEIRO-*.png")), "PNG gerado ao lado do DOCX")
        import docx
        d = docx.Document(str(saida))
        self.assertTrue(d.inline_shapes, "figura inserida no DOCX")
        self.assertIn("Fluxograma do Caminho do Dinheiro", " ".join(p.text for p in d.paragraphs))

    def test_sem_csv_o_docx_sai_sem_figura_e_sem_erro(self):
        r, pasta, _ = self._gerar_docx("OS-951-2099", None)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse(list(pasta.glob("*.png")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
