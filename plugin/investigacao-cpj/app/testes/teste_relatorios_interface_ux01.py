"""UX01: ordenação numérica e visualizador sob demanda, com DOM fictício."""
import json
import re
import unittest
from pathlib import Path

import quickjs


HTML = Path(__file__).resolve().parents[1] / "static" / "index.html"


class RelatoriosInterface(unittest.TestCase):
    def setUp(self):
        self.html = HTML.read_text(encoding="utf-8")
        self.ctx = quickjs.Context()
        self.ctx.eval("""
            const elementos={};
            function $(id){return elementos[id]||(elementos[id]={hidden:true,value:'',checked:false,
                attrs:{},setAttribute(k,v){this.attrs[k]=v},removeAttribute(k){delete this.attrs[k]},
                focus(){this.focado=true}})}
            function $$(s){return []}
            const enc=encodeURIComponent,esc=s=>String(s??'');
            const pode=()=>false,prazoBadge=()=>'',badge=()=>'',barraHTML=()=>'';
            let origemVisualizador=null;
        """)
        for inicio, fim in [
            ("function compararNumeroOS", "let tq;"),
            ("async function carregarCasos", "let casoAberto=null;"),
            ("function fecharVisualizadorRelatorio", '$("#vis-fechar").onclick='),
        ]:
            trecho = self.html.split(inicio, 1)[1].split(fim, 1)[0]
            self.ctx.eval(inicio + trecho)

    def valor(self, expressao):
        return json.loads(self.ctx.eval("JSON.stringify(" + expressao + ")"))

    def test_lista_real_ordena_numero_e_preserva_filtro(self):
        casos = [{"id": "OS-100-2099", "ordem_servico": "100/2099"},
                 {"id": "OS-10-2099", "ordem_servico": "10/2099"},
                 {"id": "OS-9-2099", "ordem_servico": "9/2099"},
                 {"id": "OS-11-2099", "ordem_servico": ""}]
        for c in casos:
            c.update(vitimas=[], investigados=[], status="entregue")
        self.ctx.eval("const fixture=" + json.dumps(casos) + ";let urlConsulta='';"
                      "async function api(url){urlConsulta=url;return fixture}"
                      "$('#st-casos').value='entregue';carregarCasos();")
        while self.ctx.execute_pending_job():
            pass
        ids = re.findall(r'data-id="([^"]+)"', self.valor("$('#t-casos').innerHTML"))
        self.assertEqual(ids, ["OS-9-2099", "OS-10-2099", "OS-11-2099", "OS-100-2099"])
        self.assertIn("status=entregue", self.valor("urlConsulta"))

    def test_sem_numero_vai_ao_fim(self):
        self.ctx.eval("const lista=[{id:'OS-TESTE'},{id:'OS-2-2099'},{id:'OS-1-2099'}];lista.sort(compararNumeroOS)")
        self.assertEqual(self.valor("lista.map(c=>c.id)"), ["OS-1-2099", "OS-2-2099", "OS-TESTE"])

    def test_pdf_carrega_so_ao_clicar_e_fechar_descarrega(self):
        self.assertNotRegex(self.html, r'<iframe[^>]*id="vis-frame"[^>]*\bsrc=')
        self.ctx.eval("const botao={isConnected:true,focus(){this.focado=true}};"
                      "visualizarRelatorio('OS-1-2099','Relatório fictício.pdf',botao)")
        self.assertEqual(self.valor("$('#vis-frame').src"),
                         "/arquivo/OS-1-2099/03-relatorios/Relat%C3%B3rio%20fict%C3%ADcio.pdf")
        self.assertFalse(self.valor("$('#vis-aviso').hidden"))
        self.assertIn("Abrir original", self.valor("$('#vis-aviso').textContent"))
        self.assertNotIn("sandbox", self.valor("$('#vis-frame').attrs"))
        self.ctx.eval("fecharVisualizadorRelatorio()")
        self.assertTrue(self.valor("$('#visualizador-relatorio').hidden"))
        self.assertTrue(self.valor("botao.focado"))

    def test_docx_usa_previa_local_e_link_original(self):
        self.ctx.eval("visualizarRelatorio('OS-1-2099','Relatório fictício.DOCX',null)")
        self.assertTrue(self.valor("$('#vis-frame').src").startswith("/visualizar/"))
        self.assertTrue(self.valor("$('#vis-original').href").startswith("/arquivo/"))
        self.assertFalse(self.valor("$('#vis-aviso').hidden"))
        self.assertEqual(self.valor("$('#vis-frame').attrs.sandbox"), "allow-same-origin")

    def test_atalho_abre_pasta_relatorios(self):
        self.assertIn('post("/abrir",{sub:"03-relatorios"})', self.html)
        self.assertIn('id="b-pasta-relatorios"', self.html)
        self.assertIn('data-visualizar="', self.html)

    def test_sintaxe_javascript_completa(self):
        scripts = re.findall(r"<script(?:[^>]*)>(.*?)</script>", self.html, re.S)
        for script in scripts:
            self.ctx.eval("new Function(" + json.dumps(script) + ")")


if __name__ == "__main__":
    unittest.main(verbosity=2)
