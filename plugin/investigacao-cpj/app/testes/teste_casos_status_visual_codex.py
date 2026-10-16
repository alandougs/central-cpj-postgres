#!/usr/bin/env python3
"""A tabela de Casos destaca a linha inteira para status finalizados."""
from pathlib import Path
import re
import unittest


HTML = (Path(__file__).resolve().parents[1] / "static" / "index.html").read_text(encoding="utf-8")


class CasosStatusVisualTests(unittest.TestCase):
    def test_status_entregue_e_concluido_aplicam_classe_na_linha(self):
        self.assertTrue(re.search(r'function casoEstaFinalizado\s*\(', HTML), "helper de status finalizado ausente")
        self.assertTrue('"entregue"' in HTML, "status entregue não é tratado como final")
        self.assertTrue('"concluido"' in HTML, "status concluído não é tratado como final")
        self.assertTrue(re.search(r'<tr class="\$\{casoEstaFinalizado\(c\)\?"linha-concluida":""\}"', HTML),
                        "a classe deve ser aplicada no elemento da linha")

    def test_todas_as_celulas_da_linha_recebem_o_fundo_verde(self):
        self.assertTrue(re.search(r'\.linha-concluida\s*>\s*td\s*\{\s*background:\s*var\(--good-soft\)',
                                  HTML), "cada célula deve usar o fundo verde")


if __name__ == "__main__":
    unittest.main()
