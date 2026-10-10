"""SE01: fluxo do modal executado em QuickJS, sem navegador ou rede."""
import json
from pathlib import Path
import re
import unittest
import quickjs

HTML = Path(__file__).resolve().parents[1] / "static" / "index.html"


class Interface(unittest.TestCase):
    def setUp(self):
        texto = HTML.read_text(encoding="utf-8")
        blocos = []
        for assinatura in ("function pedirConsentimentoExterno(destinos)", "async function enviarPedidoIA(post,dados)"):
            m = re.search(re.escape(assinatura) + r"\{[\s\S]*?\n\}", texto)
            self.assertIsNotNone(m, "Fluxo de consentimento ainda não implementado")
            blocos.append(m.group(0))
        self.ctx = quickjs.Context()
        self.ctx.eval('''
        var chamadas=[], mensagens=[], atualizacoes=0, resultado=null;
        var els={}; ['#modal-consentimento','#cons-destinos','#b-cons-aceitar','#b-cons-recusar'].forEach(k=>els[k]={hidden:true,textContent:'',onclick:null,focus:()=>{}});
        var listeners={}; var document={addEventListener:(k,f)=>listeners[k]=f,removeEventListener:(k,f)=>{delete listeners[k]}};
        function $(k){return els[k]} function toast(t){mensagens.push(t)} function atualizarIA(){atualizacoes++}
        var requer=true;
        async function post(u,d){chamadas.push(JSON.parse(JSON.stringify(d)));if(d.consentimento_externo){return d.consentimento_externo.recusado?{ok:true,mensagem:'Envio recusado.'}:{tarefa:'ia-ficticia'}};return requer?{requer_consentimento:true,destinos:['openai','cli:codex'],escopo:'api_ia'}:{tarefa:'ia-local'}}
        ''')
        self.ctx.eval("\n".join(blocos))

    def jobs(self):
        for _ in range(100):
            if not self.ctx.execute_pending_job(): return
        self.fail("Promise não estabilizou")

    def iniciar(self):
        self.ctx.eval("enviarPedidoIA(post,{acao:'analisar',agente:'ficticio'}).then(r=>resultado=r)")
        self.jobs()

    def valor(self, texto): return json.loads(self.ctx.eval("JSON.stringify(" + texto + ")"))

    def test_aviso_espera_acao_e_lista_todos_destinos(self):
        self.iniciar()
        self.assertFalse(self.valor("els['#modal-consentimento'].hidden"))
        self.assertEqual(len(self.valor("chamadas")), 1)
        self.assertEqual(self.valor("mensagens"), [])
        self.assertIn("openai", self.valor("els['#cons-destinos'].textContent"))
        self.assertIn("codex", self.valor("els['#cons-destinos'].textContent"))

    def test_aceitar_cria_com_destinos_sem_identidade_cliente(self):
        self.iniciar(); self.ctx.eval("els['#b-cons-aceitar'].onclick()"); self.jobs()
        c = self.valor("chamadas")
        self.assertEqual(len(c), 2)
        self.assertEqual(c[-1]["consentimento_externo"]["destinos"], ["openai", "cli:codex"])
        self.assertNotIn("usuario", c[-1]["consentimento_externo"])
        self.assertNotIn("data_hora", c[-1]["consentimento_externo"])
        self.assertEqual(self.valor("resultado.tarefa"), "ia-ficticia")
        self.assertEqual(self.valor("atualizacoes"), 1)
        self.assertTrue(self.valor("els['#modal-consentimento'].hidden"))

    def test_recusar_audita_sem_toast_de_enfileiramento(self):
        self.iniciar(); self.ctx.eval("els['#b-cons-recusar'].onclick()"); self.jobs()
        self.assertTrue(self.valor("chamadas")[1]["consentimento_externo"]["recusado"])
        self.assertEqual(self.valor("atualizacoes"), 0)
        self.assertIsNone(self.valor("resultado.tarefa || null"))
        self.assertNotIn("Pedido enviado ao plantão", self.valor("mensagens"))

    def test_escape_equivale_a_recusar(self):
        self.iniciar(); self.ctx.eval("listeners.keydown({key:'Escape',preventDefault:()=>{}})"); self.jobs()
        self.assertTrue(self.valor("chamadas")[1]["consentimento_externo"]["recusado"])
        self.assertEqual(self.valor("atualizacoes"), 0)

    def test_local_sem_aviso_conclui_normalmente(self):
        self.ctx.eval("requer=false"); self.iniciar()
        self.assertTrue(self.valor("els['#modal-consentimento'].hidden"))
        self.assertEqual(len(self.valor("chamadas")), 1)
        self.assertEqual(self.valor("resultado.tarefa"), "ia-local")


if __name__ == "__main__": unittest.main(verbosity=2)
