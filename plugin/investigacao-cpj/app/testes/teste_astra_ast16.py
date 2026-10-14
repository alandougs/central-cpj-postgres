"""AST16: recursos locais reais, ordem de execucao e cobertura dos leitores."""
from pathlib import Path
import tempfile
import unittest
from html.parser import HTMLParser
from astra_fixture import AstraFixture
from fonte_interface import expandir, ler_interface, javascript


class Recursos(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.scripts, self.styles = [], []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "script":
            self.scripts.append(attrs)
        if tag == "link" and "stylesheet" in attrs.get("rel", "").split():
            self.styles.append(attrs)


class FonteInterface(unittest.TestCase):
    def test_expande_na_ordem_do_html_e_falha_se_recurso_faltar(self):
        with tempfile.TemporaryDirectory(prefix="cpj-ast16-helper-") as temp:
            root = Path(temp)
            (root / "index.html").write_text('<link rel="stylesheet" href="/static/a.css"><script src="/static/b.js"></script><script src="/static/a.js"></script>', encoding="utf-8")
            (root / "a.css").write_text("body{color:red}", encoding="utf-8")
            (root / "a.js").write_text("trace.push('a');", encoding="utf-8")
            (root / "b.js").write_text("const trace=['b'];", encoding="utf-8")
            source = ler_interface(root / "index.html")
            self.assertIn("body{color:red}", source)
            import quickjs
            context = quickjs.Context()
            self.assertEqual(context.eval(javascript(source) + "trace.join(',')"), "b,a")
            (root / "b.js").unlink()
            with self.assertRaises(FileNotFoundError):
                ler_interface(root / "index.html")

    def test_recusa_recurso_externo_traversal_e_execucao_assincrona(self):
        for url in ("https://external.invalid/x.js", "//external.invalid/x.js", "/static/../x.js", "/static/%2e%2e/x.js"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                expandir(f'<script src="{url}"></script>', lambda url: "")
        for attr in ("async", "defer", 'type="module"'):
            with self.subTest(attr=attr), self.assertRaises(ValueError):
                expandir(f'<script {attr} src="/static/a.js"></script>', lambda url: "")


class Modulos(AstraFixture, unittest.TestCase):
    def test_recursos_sao_servidos_locais_na_ordem_de_dependencia(self):
        with self.client.get("/") as response:
            self.assertEqual(response.status_code, 200)
            resources = Recursos(response.get_data(as_text=True))
        self.assertGreater(len(resources.scripts), 1, "Frontend ainda esta no bloco monolitico")
        names = [s.get("src", "").rsplit("/", 1)[-1] for s in resources.scripts]
        self.assertEqual(names, ["fila-progresso.js", "core.js", "sessao.js", "polling.js", "inicio.js", "recebimento.js", "casos.js", "editor.js", "pesquisa.js", "grafo.js", "estatisticas.js", "sistema.js", "ia-config.js", "llm.js", "fluxograma.js", "vinculos.js", "astra.js", "bootstrap.js"])
        self.assertEqual(len(resources.styles), 1)
        for attrs in resources.scripts + resources.styles:
            url = attrs.get("src") or attrs["href"]
            self.assertTrue(url.startswith("/static/"))
            self.assertFalse(any(k in attrs for k in ("async", "defer", "type")))
            with self.client.get(url) as asset:
                self.assertEqual(asset.status_code, 200, url)
                self.assertIn(asset.mimetype, ("text/css", "text/javascript", "application/javascript"))
                self.assertGreater(len(asset.data), 0)

    def test_browser_executa_globais_bootstrap_unico_e_navegacao(self):
        self.browser(r'''
        const errors=[],missing=[];let sessions=0;
        page.on('pageerror',e=>errors.push(e.message));
        page.on('response',r=>{if(r.url().includes('/static/js/')||r.url().includes('/static/css/'))if(r.status()!==200)missing.push(r.url());if(r.url().endsWith('/api/sessao'))sessions++});
        await page.goto(url+'/#inicio');await page.waitForLoadState('networkidle');
        await page.waitForFunction(()=>!document.querySelector('#app').hidden);
        assert.equal(sessions,1);
        for(const name of ['api','abrirAba','abrirCaso','abrirEditor','carregarGrafo','pedirConsentimentoExterno','ciclo'])assert.equal(await page.evaluate(n=>typeof window[n],name),'function');
        await page.locator('#nav [data-a="casos"]').click();await page.waitForSelector('#casos.on');
        await page.evaluate(()=>abrirEditor('OS-901-2099'));
        await page.locator('#ed-secoes textarea').first().waitFor();await page.locator('#ed-cancelar').click();
        await page.locator('#nav [data-a="grafo"]').click();await page.waitForFunction(()=>grEstado==='pronto');
        assert.deepEqual(missing,[]);assert.deepEqual(errors,[]);
        ''')


if __name__ == "__main__":
    unittest.main(verbosity=2)
