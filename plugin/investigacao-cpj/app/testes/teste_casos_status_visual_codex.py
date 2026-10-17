#!/usr/bin/env python3
"""A tabela de Casos destaca em verde a linha cujo status é `entregue` (UX03, 15/10/2026).

Requisito vigente (PRD, UX03): somente `entregue` recebe o fundo verde, inclusive no hover; os demais
status, inclusive `concluido`, e a abertura da ficha pelo clique na linha não mudam. O contrato anterior
(helper `casoEstaFinalizado`, classe `linha-concluida`, status `concluido` destacado) foi substituído
por essa determinação. A interface é lida do HTML e dos módulos locais (CSS/JS).
"""
from pathlib import Path
import re
import unittest

STATIC = Path(__file__).resolve().parents[1] / "static"
CSS = (STATIC / "css" / "central.css").read_text(encoding="utf-8")
CASOS_JS = (STATIC / "js" / "casos.js").read_text(encoding="utf-8")


class CasosStatusVisualTests(unittest.TestCase):
    def test_somente_status_entregue_aplica_classe_na_linha(self):
        m = re.search(r'<tr class="\$\{c\.status==="entregue"\?"caso-entregue":""\}" data-id="\$\{esc\(c\.id\)\}"', CASOS_JS)
        self.assertTrue(m, "a classe deve ser aplicada no elemento da linha, só quando status === 'entregue'")
        self.assertNotIn("concluido", CASOS_JS[max(0, m.start() - 200):m.end() + 200],
                         "status concluído não deve receber o destaque")
        self.assertNotIn("linha-concluida", CASOS_JS + CSS, "contrato antigo (linha-concluida) foi substituído")

    def test_linha_entregue_tem_fundo_verde_tambem_no_hover(self):
        regra = re.search(r'tbody\.clic tr\.caso-entregue,\s*tbody\.clic tr\.caso-entregue:hover\s*\{([^}]*)\}', CSS)
        self.assertTrue(regra, "regra de fundo para a linha entregue e seu hover ausente")
        self.assertRegex(regra.group(1), r'background:\s*var\(--good-soft\)')

    def test_celulas_nao_sobrepoem_o_fundo_da_linha_entregue(self):
        # O fundo é da linha; nenhuma regra de célula pode cobrir o verde nas linhas entregues.
        self.assertFalse(re.search(r'tr\.caso-entregue\s*>?\s*td\s*\{[^}]*background:(?!\s*var\(--good-soft\))', CSS))
        self.assertFalse(re.search(r'(?<![\w.-])td\s*\{[^}]*background:', CSS), "td não deve definir fundo próprio")


if __name__ == "__main__":
    unittest.main()
