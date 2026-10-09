"""GF02: carga, seletor e renderização reais com API/DOM inteiramente fictícios."""
import json
import re
import unittest
from pathlib import Path

import quickjs


HTML = Path(__file__).resolve().parents[1] / "static" / "index.html"


class GrafoInterface(unittest.TestCase):
    def setUp(self):
        self.html = HTML.read_text(encoding="utf-8")
        self.ctx = quickjs.Context()
        self.ctx.eval("""
            const elementos={},desenhos=[];
            const pincel=new Proxy({}, {get(o,k){return o[k]||((...args)=>desenhos.push([k,...args]))}});
            function $(id){return elementos[id]||(elementos[id]={value:'',checked:true,hidden:true,
                style:{},innerHTML:'',textContent:'',width:800,height:560,
                addEventListener(){},getBoundingClientRect(){return {width:800,height:560,left:0,top:0}},
                getContext(){return pincel}})}
            const enc=encodeURIComponent,esc=s=>String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;');
            const window={devicePixelRatio:1,addEventListener(){}};
            const requestAnimationFrame=()=>1,cancelAnimationFrame=()=>{};
            let resposta={nos:[],arestas:[],casos:[]},falha='',urls=[];
            async function api(url){urls.push(url);if(falha)throw new Error(falha);return resposta}
        """)
        comparator = self.html.split("function compararNumeroOS", 1)[1].split("let tq;", 1)[0]
        self.ctx.eval("function compararNumeroOS" + comparator)
        graph = self.html.split("// ---------------- grafo relacional", 1)[1].split("// ---------------- estatísticas", 1)[0]
        self.ctx.eval(graph)

    def run_js(self, source):
        self.ctx.eval(source)
        while self.ctx.execute_pending_job():
            pass

    def value(self, expr):
        return json.loads(self.ctx.eval("JSON.stringify(" + expr + ")"))

    def fixture(self, nodes=False):
        data = {"nos": [], "arestas": [], "casos": [], "indice_disponivel": True,
                "ordens_servico": [{"id": "OS-100-2099", "ordem_servico": "100/2099"},
                                  {"id": "OS-9-2099", "ordem_servico": "9/2099"},
                                  {"id": "OS-10-2099", "ordem_servico": "10/2099"}]}
        if nodes:
            data["nos"] = [{"tipo": "PESSOA", "valor": "P:FICTICIO", "rotulo": "Ana Fictícia"},
                           {"tipo": "CASO", "valor": "OS-9-2099"}]
            data["arestas"] = [{"a_tipo": "PESSOA", "a_valor": "P:FICTICIO", "b_tipo": "CASO",
                               "b_valor": "OS-9-2099", "relacao": "consta nos autos",
                               "fonte": "OS-9-2099", "localizador": "pág. 1", "origem": "fictício"}]
        self.ctx.eval("resposta=" + json.dumps(data))

    def test_busca_vazia_mantem_os_numericas_e_selecao(self):
        self.fixture()
        self.run_js("$('#gr-caso').value='OS-10-2099';$('#gr-busca').value='inexistente';carregarGrafo()")
        options = re.findall(r'<option value="([^"]+)"', self.value("$('#gr-caso').innerHTML"))
        self.assertEqual(options, ["OS-9-2099", "OS-10-2099", "OS-100-2099"])
        self.assertEqual(self.value("$('#gr-caso').value"), "OS-10-2099")
        self.assertIn("nesta O.S.", self.value("$('#gr-mensagem').textContent"))
        self.assertIn("q=inexistente", self.value("urls[0]"))

    def test_os_sem_arestas_explica_ausencia(self):
        self.fixture()
        self.run_js("$('#gr-caso').value='OS-9-2099';carregarGrafo()")
        self.assertFalse(self.value("$('#gr-mensagem').hidden"))
        self.assertIn("ainda não possui vínculos", self.value("$('#gr-mensagem').textContent"))
        self.assertEqual(self.value("grNodes.length"), 0)

    def test_atualiza_os_mesmo_depois_da_primeira_carga(self):
        self.fixture()
        self.run_js("carregarGrafo();")
        self.run_js("resposta.ordens_servico.push({id:'OS-11-2099',ordem_servico:'11/2099'});carregarGrafo()")
        self.assertIn('value="OS-11-2099"', self.value("$('#gr-caso').innerHTML"))

    def test_desenha_nos_arestas_e_inspeciona_fonte(self):
        self.fixture(nodes=True)
        self.run_js("carregarGrafo()")
        self.run_js("grInspecionarNo(grNodes[0])")
        self.assertTrue(self.value("$('#gr-mensagem').hidden"))
        self.assertEqual(self.value("$('#gr-status').textContent"), "2 nós visíveis · 1 conexões")
        self.assertTrue(self.value("desenhos.some(d=>d[0]==='arc')"))
        self.assertTrue(self.value("desenhos.some(d=>d[0]==='lineTo')"))
        self.assertIn("pág. 1", self.value("$('#gr-detalhes-conteudo').innerHTML"))

    def test_filtros_contam_so_conexoes_visiveis(self):
        self.fixture(nodes=True)
        self.run_js("carregarGrafo();$('#gf-caso').checked=false;grDesenhar()")
        self.assertEqual(self.value("$('#gr-status').textContent"), "1 nós visíveis · 0 conexões")
        self.run_js("$('#gf-pessoa').checked=false;grDesenhar()")
        self.assertIn("ocultos pelos filtros", self.value("$('#gr-mensagem').textContent"))

    def test_rede_estabiliza_e_permanece_enquadrada(self):
        self.fixture(nodes=True)
        self.run_js("""
            for(let i=0;i<5;i++){
                resposta.nos.push({tipo:'CONTA',valor:'DEMO|'+i});
                resposta.arestas.push({a_tipo:'PESSOA',a_valor:'P:FICTICIO',
                    b_tipo:'CONTA',b_valor:'DEMO|'+i,relacao:'titular'});
            }
            carregarGrafo();
        """)
        self.run_js("for(let i=0;i<250;i++)grTickPhysics();grResetView()")
        self.assertTrue(self.value("grNodes.every(n=>Number.isFinite(n.x)&&Number.isFinite(n.y)&&Math.abs(n.x)<2000&&Math.abs(n.y)<2000)"))
        self.assertTrue(self.value("grNodes.every(n=>n.x*grZoom+grPanX>=40&&n.x*grZoom+grPanX<=760&&n.y*grZoom+grPanY>=40&&n.y*grZoom+grPanY<=520)"))

    def test_erro_limpa_desenho_anterior_e_preserva_os(self):
        self.fixture(nodes=True)
        self.run_js("carregarGrafo()")
        self.run_js("falha='falha fictícia';carregarGrafo()")
        self.assertEqual(self.value("grNodes.length+grEdges.length"), 0)
        self.assertIn("tentar novamente", self.value("$('#gr-mensagem').textContent"))
        self.assertIn("OS-9-2099", self.value("$('#gr-caso').innerHTML"))
        self.assertEqual(self.value("$('#gr-status').textContent"), "Falha no carregamento")

    def test_sem_indice_mantem_cadastro_selecionavel(self):
        self.fixture()
        self.run_js("resposta.indice_disponivel=false;carregarGrafo()")
        self.assertIn("índice de vínculos", self.value("$('#gr-mensagem').textContent"))
        self.assertIn('value="OS-9-2099"', self.value("$('#gr-caso').innerHTML"))

    def test_resposta_antiga_nao_sobrepoe_busca_mais_recente(self):
        self.fixture()
        self.run_js("let pendentes=[];api=url=>new Promise(resolve=>pendentes.push(resolve));carregarGrafo();carregarGrafo()")
        self.run_js("pendentes[1](resposta)")
        self.run_js("pendentes[0]({nos:[],arestas:[],casos:['OS-999-2099']})")
        self.assertNotIn("OS-999-2099", self.value("$('#gr-caso').innerHTML"))

    def test_sintaxe_completa(self):
        for script in re.findall(r"<script(?:[^>]*)>(.*?)</script>", self.html, re.S):
            self.ctx.eval("new Function(" + json.dumps(script) + ")")


if __name__ == "__main__":
    unittest.main(verbosity=2)
