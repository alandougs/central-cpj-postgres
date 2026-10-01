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


if __name__ == "__main__":
    unittest.main(verbosity=2)
