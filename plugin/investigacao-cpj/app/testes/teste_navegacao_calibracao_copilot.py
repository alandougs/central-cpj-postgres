#!/usr/bin/env python3
"""U01: seleção de O.S. em CASOS abre e rola até a ficha/IA; painel de calibração (upload do FINAL, comparação local,
aprovação por lição) e uso da área de referências para exemplos de estilo. Verificações estáticas do index.html
(+ sintaxe do JavaScript, se o módulo quickjs estiver instalado)."""
import json
import re
import sys
import unittest
from pathlib import Path

HTML = Path(__file__).resolve().parents[1] / "static" / "index.html"


class NavegacaoCalibracaoU01(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t = HTML.read_text(encoding="utf-8")

    def test_01_selecao_de_os_rola_ate_o_detalhe(self):
        self.assertIn("async function abrirCaso(id,rolar){const novoCaso=casoAberto!==id;", self.t)
        self.assertIn('if(rolar||novoCaso)requestAnimationFrame(()=>$("#detalhe").scrollIntoView(', self.t)
        self.assertIn("abrirCaso(tr.dataset.id,true)", self.t, "clique na linha da lista de casos")
        self.assertIn("abrirCaso(e.dataset.id,true)", self.t, "clique nas listas do Início")

    def test_02_atalhos_para_ficha_ia_e_calibracao(self):
        for alvo in ("nv-ficha", "nv-ia", "nv-cal"):
            self.assertIn(f'data-ir="{alvo}"', self.t)
            self.assertIn(f'id="{alvo}"', self.t)
        self.assertIn('$$("#detalhe [data-ir]").forEach', self.t)
        self.assertIn('$$("#detalhe [data-calibrar]").forEach', self.t, "o botão 'calibrar estilo' da tabela passa a funcionar")

    def test_03_painel_de_calibracao(self):
        for ident in ("cal-arq", "b-cal-comparar", "prog-cal", "cal-msg", "cal-res", "b-cal-ref"):
            self.assertIn(f'id="{ident}"', self.t)
        self.assertIn('accept=".pdf,.docx,.md,.txt"', self.t)
        self.assertIn("fd.append(\"final\",f)", self.t, "envia o FINAL escolhido, por upload explícito")
        self.assertIn("/calibrar`,{method:\"POST\",body:fd}", self.t)
        self.assertIn("/calibrar/aprovar", self.t)
        self.assertIn('data-lic="', self.t, "uma caixa de seleção por lição")
        self.assertIn("Nada é gravado até você aprovar", self.t)
        self.assertIn("confirm(`Gravar ${ids.length}", self.t, "confirmação antes de gravar")

    def test_04_definir_final_nao_calibra_mais_sozinho(self):
        self.assertNotIn("/calibrar`,{json:{arquivo", self.t)
        self.assertNotIn('post("/calibrar",{arquivo', self.t)
        self.assertNotIn("calibra o estilo.`))return", self.t)

    def test_05_area_de_referencias_reaproveitada(self):
        self.assertIn('id="card-referencias"', self.t)
        self.assertIn('$("#card-referencias")', self.t)

    def test_06_sintaxe_do_javascript(self):
        try:
            import quickjs
        except ImportError:
            self.skipTest("quickjs não instalado (pip install quickjs)")
        ctx = quickjs.Context()
        blocos = [b for b in re.findall(r"<script(?:[^>]*)>(.*?)</script>", self.t, flags=re.S) if len(b) > 200]
        self.assertTrue(blocos)
        for b in blocos:
            ctx.eval("new Function(" + json.dumps(b) + "); 1")


if __name__ == "__main__":
    unittest.main(verbosity=2)
