#!/usr/bin/env python3
"""UI01: protocolo de marcação entre a busca do RAG e o destaque da Pesquisa da Central.

Defeito de origem (D7 da revisão de LC01): a interface destacava qualquer texto entre
colchetes do trecho devolvido, porque o snippet do FTS usava colchete como marcador de termo
casado. Colchete, nos autos, é determinação das regras 3 e 17 (`[dígito incerto]`,
`[PESQUISAR: CNPJ]`) — e um acerto só por semântica devolve o excerto cru, sem marcador
nenhum, onde todo colchete vem dos autos.

Workspace sintético em TEMP; nenhum caso real é lido.
"""
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "plugin/investigacao-cpj/skills/base-cpj/scripts"
JS_PESQUISA = ROOT / "plugin/investigacao-cpj/app/static/js/pesquisa.js"
JS_CORE = ROOT / "plugin/investigacao-cpj/app/static/js/core.js"


def _carregar(nome):
    spec = importlib.util.spec_from_file_location(nome, BASE / f"{nome}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ProtocoloDeBuscaUI01(unittest.TestCase):
    """A busca precisa dizer o que destacar em separado do texto; não dá para a interface
    adivinhar olhando o próprio texto."""

    # Os colchetes abaixo são os dos autos, pelas regras 3 e 17. O termo pesquisado é
    # "transferência", que não tem colchete nenhum.
    TRANSCRICAO = ("# Transcrição sintética\n\n## Página 1\nFls. 11\n"
                   "O extrato aponta a transferência para a conta 555.666.777-?1 "
                   "[dígito incerto] e a empresa citada segue [PESQUISAR: CNPJ] "
                   "na data do fato apurado.\n")
    CONSULTA = "transferência"

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="cpj-ui01-sintetico-")
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.ws = Path(cls.tmp.name)
        (cls.ws / "modelos").mkdir()
        caso = "OS-9802-2099"
        doc = cls.ws / "casos" / caso / "01-extracao" / "autos-ui01"
        doc.mkdir(parents=True)
        (doc / "transcricao.md").write_text(cls.TRANSCRICAO, encoding="utf-8")
        (cls.ws / "casos" / caso / "caso.json").write_text(json.dumps({
            "id": caso, "status": "recebido", "ordem_servico": caso[3:],
        }), encoding="utf-8")
        env = dict(os.environ, CPJ_WORKSPACE=str(cls.ws), PYTHONDONTWRITEBYTECODE="1",
                   PYTHONIOENCODING="utf-8", CPJ_SEM_AGENTE_EMBUTIDO="1")
        r = subprocess.run([sys.executable, str(BASE / "indexar.py"), "--tudo"], cwd=cls.ws,
                           env=env, capture_output=True, text=True, encoding="utf-8", timeout=900)
        if r.returncode:
            raise AssertionError(f"indexar.py falhou ({r.returncode}):\n{r.stdout}\n{r.stderr}")
        os.environ["CPJ_WORKSPACE"] = str(cls.ws)
        cls.addClassCleanup(os.environ.pop, "CPJ_WORKSPACE", None)
        cls.rag = _carregar("rag")

    def primeiro(self):
        res, _ = self.rag.buscar(self.CONSULTA, modo="lexical", n=5)
        self.assertTrue(res, "a consulta casa por palavra; deveria achar o trecho")
        return res[0]

    def marcados(self, r):
        return [r["trecho"][i:j] for i, j in r["marcas"]]

    def test_busca_devolve_as_marcas_junto_do_trecho(self):
        self.assertEqual(set(self.primeiro()), {"caso", "arquivo", "tipo", "pagina", "fls",
                                                "secao", "trecho", "marcas"})

    def test_marca_cai_sobre_o_termo_casado(self):
        marcados = [t.lower() for t in self.marcados(self.primeiro())]
        self.assertTrue(marcados, "o snippet do FTS tem termo casado; a marca não pode faltar")
        self.assertTrue(any("transfer" in t for t in marcados),
                        f"a marca deveria cair sobre o termo pesquisado, veio em {marcados}")

    def test_colchete_dos_autos_chega_literal_e_sem_marca(self):
        r = self.primeiro()
        self.assertIn("[dígito incerto]", r["trecho"],
                      "o colchete dos autos é conteúdo e tem de chegar inteiro")
        for texto in self.marcados(r):
            self.assertNotIn("dígito incerto", texto, "colchete dos autos não é termo casado")
            self.assertNotIn("PESQUISAR", texto, "colchete dos autos não é termo casado")

    def test_trecho_devolvido_nao_leva_sentinela(self):
        for r in self.rag.buscar(self.CONSULTA, modo="lexical", n=5)[0]:
            self.assertNotIn(self.rag.MARCA_I, r["trecho"], "sentinela não pode sair da busca")
            self.assertNotIn(self.rag.MARCA_F, r["trecho"], "sentinela não pode sair da busca")

    def test_marcas_sao_intervalos_crescentes_dentro_do_texto(self):
        r = self.primeiro()
        fim = 0
        for par in r["marcas"]:
            self.assertEqual(len(par), 2)
            i, j = par
            self.assertIsInstance(i, int)
            self.assertIsInstance(j, int)
            self.assertGreaterEqual(i, fim, "as marcas têm de vir em ordem e sem sobrepor")
            self.assertGreater(j, i, "marca vazia não é destaque")
            self.assertLessEqual(j, len(r["trecho"]), "marca fora do texto devolvido")
            fim = j

    def test_desmarcar_pareia_sentinela_e_devolve_posicao(self):
        texto, marcas = self.rag._desmarcar(
            f"paga {self.rag.MARCA_I}pix{self.rag.MARCA_F} hoje")
        self.assertEqual(texto, "paga pix hoje")
        self.assertEqual(marcas, [[5, 8]])
        self.assertEqual(texto[5:8], "pix")

    def test_desmarcar_descarta_sentinela_sem_par(self):
        texto, marcas = self.rag._desmarcar(f"a{self.rag.MARCA_I}b")
        self.assertEqual((texto, marcas), ("ab", []))
        texto, marcas = self.rag._desmarcar(f"a{self.rag.MARCA_F}b")
        self.assertEqual((texto, marcas), ("ab", []))

    def test_desmarcar_nao_enxerga_marcador_em_colchete(self):
        cru = "conta 555.666.777-?1 [dígito incerto] e [PESQUISAR: CNPJ]"
        self.assertEqual(self.rag._desmarcar(cru), (cru, []),
                         "colchete é conteúdo dos autos, nunca marcador")


class FonteDaPesquisaUI01(unittest.TestCase):
    """Trava o defeito na fonte, independente de a função nova existir."""

    def test_fonte_nao_usa_mais_colchete_como_marcador(self):
        fonte = JS_PESQUISA.read_text(encoding="utf-8")
        self.assertTrue("<mark>$1</mark>" not in fonte,
                        "destacar colchete do texto foi o defeito D7; não pode voltar")
        self.assertIn("function trechoHTML", fonte,
                      "o destaque tem de vir das marcas que a busca devolve")


class MarcacaoNaInterfaceUI01(unittest.TestCase):
    """A interface destaca só o que a busca mandou destacar, e escapa tudo."""

    @classmethod
    def setUpClass(cls):
        import quickjs
        fonte = JS_PESQUISA.read_text(encoding="utf-8")
        funcao = re.search(r"^function trechoHTML\b[\s\S]*?^\}", fonte, re.M)
        if not funcao:
            raise AssertionError("pesquisa.js deve expor trechoHTML() para render do trecho")
        esc = re.search(r"^const esc=.*$", JS_CORE.read_text(encoding="utf-8"), re.M)
        cls.ctx = quickjs.Context()
        cls.ctx.eval(esc[0])
        cls.ctx.eval(funcao[0])

    def render(self, trecho, marcas):
        return self.ctx.eval("trechoHTML(" + json.dumps(
            {"trecho": trecho, "marcas": marcas}, ensure_ascii=False) + ")")

    def test_interface_nao_destaca_colchete_dos_autos(self):
        """A reprodução do defeito: excerto só por semântica, sem marca nenhuma."""
        cru = "conta 555.666.777-?1 [dígito incerto] e a empresa [PESQUISAR: CNPJ]"
        saida = self.render(cru, [])
        self.assertNotIn("<mark>", saida, "sem marca não há o que destacar")
        self.assertIn("[dígito incerto]", saida, "o colchete dos autos é texto e fica visível")
        self.assertIn("[PESQUISAR: CNPJ]", saida)

    def test_interface_destaca_apenas_o_intervalo_marcado(self):
        cru = "pagou pix e deixou [dígito incerto] no extrato"
        saida = self.render(cru, [[6, 9]])
        self.assertEqual(saida.count("<mark>"), 1)
        self.assertIn("<mark>pix</mark>", saida)
        self.assertIn("[dígito incerto]", saida)

    def test_interface_escapa_html_dentro_e_fora_da_marca(self):
        saida = self.render('<b>pix</b> & "nota" <script>x</script>', [[0, 8]])
        self.assertNotIn("<b>", saida)
        self.assertNotIn("<script>", saida)
        self.assertIn("&lt;b&gt;pix", saida)
        self.assertIn("&amp;", saida)
        self.assertEqual(saida.count("<mark>"), 1)

    def test_marca_malformada_nao_vaza_html_nem_perde_texto(self):
        cru = '<b>pix</b> [dígito incerto]'
        limpo = self.render(cru, [])
        for marcas in ([[5, 2]], [[0, 999]], [[-1, 3]], [[1.5, 3]], [[0, 3], [1, 5]],
                       [[0]], ["0,3"], "marcas", None, [[0, 0]]):
            saida = self.render(cru, marcas)
            self.assertEqual(saida, limpo,
                             f"marca malformada {marcas!r} deve só perder o destaque")
            self.assertNotIn("<b>", saida)


if __name__ == "__main__":
    unittest.main(verbosity=2)
