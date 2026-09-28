#!/usr/bin/env python3
"""Regressão de extratos fictícios: formatos contábeis e tabelas sem bordas."""
import csv
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "plugin" / "investigacao-cpj" / "skills" / "pdf-autos-policiais" / "scripts" / "tabelas.py"


def gerar_extrato(destino):
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    limites = [35, 110, 300, 360, 450, 560]
    horizontais = [770, 744, 710, 684, 658]
    for x in limites:
        pdf.line(x, horizontais[-1], x, horizontais[0])
    for y in horizontais:
        pdf.line(limites[0], y, limites[-1], y)

    linhas_com_bordas = [
        ["DATA", "HISTORICO", "DOC", "VALOR", "SALDO"],
        ["10/04/2026", "PIX FICTICIO", "000001", "R$ 1.234,56 D", "8.765,44"],
        ["11/04/2026", "TRANSFERENCIA\nCOMPLEMENTAR", "000002", "-0,01 C", "8.765,43"],
        ["12/04/2026", "TARIFA", "000003", "0,10 D", "8.765,33"],
    ]
    for indice, linha in enumerate(linhas_com_bordas):
        for coluna, valor in enumerate(linha):
            pdf.setFont("Courier", 6.5)
            for quebra, trecho in enumerate(valor.split("\n")):
                pdf.drawString(limites[coluna] + 2, horizontais[indice] - 12 - 10 * quebra, trecho)
    pdf.showPage()

    # Extrato contínuo sem grades: o cabeçalho se repete no início da página seguinte.
    inicio_colunas = [35, 110, 300, 360, 450]
    linhas_sem_bordas = [
        ["DATA", "HISTORICO", "DOC", "VALOR", "SALDO"],
        ["13/04/2026", "PIX RECEBIDO", "000004", "0,01 C", "8.765,34"],
        ["14/04/2026", "TRANSFERENCIA", "000005", "0,02 D", "8.765,32"],
        ["", "COMPLEMENTAR", "", "", ""],
        ["15/04/2026", "TARIFA", "000006", "0,10 D", "8.765,22"],
    ]
    for indice, linha in enumerate(linhas_sem_bordas):
        pdf.setFont("Courier", 8)
        for x, valor in zip(inicio_colunas, linha):
            if valor:
                altura = 770 - indice * 22
                if indice == 3:
                    altura = 770 - 2 * 22 - 10
                pdf.drawString(x, altura, valor)
    pdf.showPage()
    pdf.save()
    Path(destino).write_bytes(buffer.getvalue())


class TesteTabelasE04(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cpj-tabelas-e04-")
        self.pasta = Path(self.temp.name)
        self.pdf = self.pasta / "extrato-ficticio.pdf"
        self.saida = self.pasta / "extracao"
        gerar_extrato(self.pdf)
        subprocess.run(
            [sys.executable, str(SCRIPT), str(self.pdf), "--saida", str(self.saida)],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env={**os.environ, "CPJ_WORKSPACE": str(self.pasta)},
        )

    def tearDown(self):
        self.temp.cleanup()

    def ler_csv(self, pagina):
        caminho = self.saida / "tabelas" / f"t001_pag{pagina:04d}.csv"
        if pagina > 1:
            caminho = self.saida / "tabelas" / f"t002_pag{pagina:04d}.csv"
        bruto = caminho.read_bytes()
        self.assertTrue(bruto.startswith(b"\xef\xbb\xbf"), "CSV deve conter BOM UTF-8")
        with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
            leitor = csv.reader(arquivo, delimiter=";")
            return list(leitor)

    def test_extrato_com_bordas_preserva_centavos_sinais_dc_e_descricao(self):
        linhas = self.ler_csv(1)
        self.assertEqual(linhas[0], ["pagina_pdf", "col1", "col2", "col3", "col4", "col5"])
        self.assertIn(["1", "10/04/2026", "PIX FICTICIO", "000001", "R$ 1.234,56 D", "8.765,44"], linhas)
        self.assertIn(["1", "11/04/2026", "TRANSFERENCIA COMPLEMENTAR", "000002", "-0,01 C", "8.765,43"], linhas)
        self.assertIn(["1", "12/04/2026", "TARIFA", "000003", "0,10 D", "8.765,33"], linhas)

    def test_extrato_sem_bordas_com_cabecalho_repetido_e_extraido(self):
        linhas = self.ler_csv(2)
        self.assertIn(["2", "DATA", "HISTORICO", "DOC", "VALOR", "SALDO"], linhas)
        self.assertIn(["2", "13/04/2026", "PIX RECEBIDO", "000004", "0,01 C", "8.765,34"], linhas)
        self.assertIn(["2", "14/04/2026", "TRANSFERENCIA COMPLEMENTAR", "000005", "0,02 D", "8.765,32"], linhas)
        self.assertIn(["2", "15/04/2026", "TARIFA", "000006", "0,10 D", "8.765,22"], linhas)
        self.assertEqual(sum(linha[1] == "DATA" for linha in linhas[1:]), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)