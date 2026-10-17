"""Teste UN15 (navegador): painel único de fluxos por O.S. no Início.

Playwright/Edge com servidor local, usuários e O.S. fictícios; rede simulada por page.route.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from teste_fila_unificada_un15 import Base, HTML  # noqa: E402


class FilaUnificadaUI(Base):
    def semear(self):
        ex = self.F.criar(self.caso, "astra_ficticio", "k-ui")
        a = self.F.vincular_etapa(ex["id"], "extracao", "processamento", f"{self.caso}|doc-a|t1", HTML + ".pdf")
        r = self.F.atualizar(a["id"], a["versao"], "em_execucao", 10)
        self.F.atualizar(a["id"], r["versao"], "concluida", 100)
        b1 = self.F.vincular_etapa(ex["id"], "extracao", "processamento", f"{self.caso}|doc-b|t1", "doc-b.pdf")
        r = self.F.atualizar(b1["id"], b1["versao"], "em_execucao", 20)
        self.F.atualizar(b1["id"], r["versao"], "falhou", None, "erro de leitura")
        b2 = self.F.retentar(b1["id"], f"{self.caso}|doc-b|t2")
        r = self.F.atualizar(b2["id"], b2["versao"], "em_execucao", 5)
        self.F.atualizar(b2["id"], r["versao"], "aguardando_operador", None, "OCR indisponível: " + HTML)
        return ex, a, b1, b2

    def estados(self, ex):
        return [e["estado"] for e in self.F.obter(ex["id"])["etapas"]]

    def test_renderiza_uma_linha_escapa_html_e_nao_inventa_progresso(self):
        self.semear()
        self.browser(r'''
        const erros=[];page.on('pageerror',e=>erros.push(e.message));
        await page.goto(url+'/#inicio');await page.waitForSelector('#fluxos-lista article');
        assert.equal(await page.locator('#fluxos-lista article').count(),1);
        const art=page.locator('#fluxos-lista article');
        const texto=await art.innerText();
        assert.ok(texto.includes('OS-901-2099')&&texto.includes('doc-b.pdf'),texto);
        assert.ok(texto.includes('<img src=x onerror='),'o HTML deve aparecer como texto');
        assert.ok(texto.includes('OCR indisponível'),'pendência de OCR visível sem abrir detalhes');
        assert.ok(texto.includes('progresso não informado'));
        assert.equal(await art.locator('.prog').count(),0,'sem percentual mensurável não há barra');
        assert.equal(await page.evaluate(()=>window.__xss),undefined,'HTML de dados não pode executar');
        assert.equal(await page.locator('#fluxos-lista img, #fluxos-lista script').count(),0);
        const prox=art.locator('details.fluxo-prox');
        assert.equal(await prox.count(),1);assert.equal(await prox.evaluate(d=>d.open),false);
        assert.ok(!(await art.locator('ul.fluxo-pends').innerText()).includes('ainda não iniciada'),'etapas ausentes só nos detalhes');
        const hist=art.locator('details.fluxo-hist');
        assert.equal(await hist.evaluate(d=>d.open),false);
        assert.equal(await art.locator('.fluxo-hist-tab').count(),0,'histórico só é carregado ao abrir');
        const [resp]=await Promise.all([page.waitForResponse(r=>/\/api\/fluxos\/[0-9a-f-]{36}\?/.test(r.url())),hist.locator('summary').click()]);
        assert.equal(resp.status(),200);
        await art.locator('.fluxo-hist-tab tbody tr').nth(2).waitFor();
        assert.equal(await art.locator('.fluxo-hist-tab tbody tr').count(),3,'tentativas e documentos no histórico');
        assert.equal(await art.locator('button[data-acao="cancelar"]').count(),1);
        assert.equal(await art.locator('form.fluxo-reconc').count(),1);
        assert.equal(await page.evaluate(()=>window.__xss),undefined);
        assert.deepEqual(erros,[]);
        ''')

    def test_perfil_sem_trabalho_nao_ve_acoes_nem_texto_operacional(self):
        self.semear()
        self.browser(r'''
        const ctx2=await browser.newContext();
        assert.equal((await ctx2.request.post(url+'/api/entrar',{headers:{'X-CPJ':'1'},data:{login:'leitor_ficticio',senha:'Ficticia123'}})).status(),200);
        const p2=await ctx2.newPage();await p2.goto(url+'/#inicio');await p2.waitForSelector('#fluxos-lista article');
        const t=await p2.locator('#fluxos-lista article').innerText();
        assert.ok(t.includes('aguardando conferência do operador'));
        assert.ok(!t.includes('OCR indisponível'),'texto operacional não é exibido a este perfil');
        assert.equal(await p2.locator('#fluxos-lista button, #fluxos-lista form').count(),0);
        ''')

    def test_respostas_tardias_fora_de_ordem_e_aba_oculta(self):
        self.semear()
        self.browser(r'''
        await page.goto(url+'/#inicio');await page.waitForSelector('#fluxos-lista article');
        const base=await page.evaluate(()=>fetch('/api/fluxos',{headers:{'X-CPJ':'1'}}).then(r=>r.json()));
        // 1) fora de ordem: a resposta antiga (seq 4) chega depois da nova (seq 5) e é ignorada
        const nova=JSON.parse(JSON.stringify(base));nova.itens[0].caso='OS-NOVA-2099';
        const velha=JSON.parse(JSON.stringify(base));velha.itens[0].caso='OS-VELHA-2099';
        const r=await page.evaluate(([n,v])=>{const s=FilaUnificada._estado.aplicado+10;return [FilaUnificada.aplicarLista(n,s),FilaUnificada.aplicarLista(v,s-1)]},[nova,velha]);
        assert.deepEqual(r,[true,false]);
        let t=await page.locator('#fluxos-lista').innerText();
        assert.ok(t.includes('OS-NOVA-2099')&&!t.includes('OS-VELHA-2099'),t);
        // 2) resposta atrasada depois de trocar de usuário: descartada, lista continua vazia
        await page.evaluate(()=>{FilaUnificada.limpar()});
        let liberar;const preso=new Promise(res=>liberar=res);
        await page.route('**/api/fluxos?*',async route=>{try{const resp=await route.fetch();await preso;await route.fulfill({response:resp})}catch(e){}});
        const pendente=page.evaluate(()=>FilaUnificada.atualizarPainel().then(()=>'ok',e=>'erro:'+e.message));
        await page.waitForTimeout(300);
        await page.evaluate(()=>{S.usuario={...S.usuario,login:'outro_usuario'};reiniciarPolling(true)});
        liberar();const fim=await pendente;
        assert.equal(await page.locator('#fluxos-lista article').count(),0,'dados do usuário anterior não podem aparecer: '+fim);
        await page.unroute('**/api/fluxos?*');
        // 3) aba oculta: nenhuma consulta de fluxos; ao voltar, volta a consultar
        await page.evaluate(()=>{S.usuario={...S.usuario,login:'astra_ficticio'}});
        let chamadas=0;page.on('request',q=>{if(q.url().includes('/api/fluxos'))chamadas++});
        await page.evaluate(()=>{Object.defineProperty(document,'hidden',{configurable:true,get:()=>true});document.dispatchEvent(new Event('visibilitychange'))});
        await page.evaluate(()=>acordarPolling());
        await page.waitForTimeout(1500);
        assert.equal(chamadas,0,'oculta: sem consultas');
        await page.evaluate(()=>{Object.defineProperty(document,'hidden',{configurable:true,get:()=>false});document.dispatchEvent(new Event('visibilitychange'))});
        await page.waitForSelector('#fluxos-lista article');
        assert.ok(chamadas>=1,'visível: consulta retomada');
        ''')

    def test_falha_de_rede_mantem_dados_avisa_e_recupera_sem_perder_estado_da_tela(self):
        self.semear()
        self.browser(r'''
        await page.goto(url+'/#inicio');await page.waitForSelector('#fluxos-lista article');
        const art=page.locator('#fluxos-lista article');
        await art.locator('details.fluxo-hist summary').click();
        await art.locator('.fluxo-hist-tab tbody tr').nth(2).waitFor();
        const campo=art.locator('input[name="motivo"]');
        await campo.click();await campo.type('conferi no provedor');
        // falha de rede: últimos dados e a tela do operador permanecem; aviso aparece
        await page.route('**/api/fluxos?*',r=>r.abort());
        await page.evaluate(()=>acordarPolling());
        await page.waitForFunction(()=>document.querySelector('#fluxos-estado').textContent.includes('Fluxos indisponíveis'));
        assert.equal(await page.locator('#fluxos-lista article').count(),1,'últimos dados mantidos');
        assert.equal(await campo.inputValue(),'conferi no provedor');
        await page.unroute('**/api/fluxos?*');
        // reconexão com dado alterado: a tela atualiza sem fechar detalhes, apagar o texto digitado ou perder o foco
        await page.route('**/api/fluxos?*',async route=>{const resp=await route.fetch();const j=await resp.json();j.itens[0].atualizado_em='2031-02-03T04:05:00';await route.fulfill({response:resp,json:j})});
        await page.evaluate(()=>{document.querySelector('input[name="motivo"]').focus();acordarPolling()});
        await page.waitForFunction(()=>document.querySelector('#fluxos-lista').innerText.includes('2031-02-03 04:05'));
        assert.equal(await page.locator('#fluxos-estado').innerText(),'');
        assert.equal(await art.locator('details.fluxo-hist').evaluate(d=>d.open),true);
        assert.equal(await art.locator('.fluxo-hist-tab tbody tr').count(),3);
        assert.equal(await page.locator('input[name="motivo"]').inputValue(),'conferi no provedor');
        assert.equal(await page.evaluate(()=>document.activeElement.name),'motivo');
        ''')

    def test_cancelar_e_reconciliar_pelo_painel(self):
        ex, a, b1, b2 = self.semear()
        self.browser(r'''
        await page.goto(url+'/#inicio');await page.waitForSelector('#fluxos-lista article');
        const art=page.locator('#fluxos-lista article');
        // conferência sem motivo não envia nada
        const botao=art.locator('form.fluxo-reconc button[type=submit]');
        let enviados=0;page.on('request',q=>{if(q.method()==='POST'&&q.url().includes('/api/fluxos/'))enviados++});
        await botao.click();assert.equal(enviados,0);
        await art.locator('input[name="motivo"]').fill('conferido: nenhuma cobrança no provedor');
        const [r]=await Promise.all([page.waitForResponse(x=>x.url().includes('/reconciliar')),botao.click()]);
        assert.equal(r.status(),200,await r.text());
        await page.waitForFunction(()=>!document.querySelector('form.fluxo-reconc'));
        // cancelamento: recusado no diálogo não envia; aceito cancela
        page.once('dialog',d=>d.dismiss());
        await page.locator('button[data-acao="cancelar"]').click();
        await page.waitForTimeout(300);assert.equal(enviados,1,'cancelar recusado não envia');
        page.once('dialog',d=>d.accept());
        const [c]=await Promise.all([page.waitForResponse(x=>x.url().includes('/cancelar')),page.locator('button[data-acao="cancelar"]').click()]);
        assert.equal(c.status(),200,await c.text());
        ''')
        self.assertEqual(self.estados(ex), ["concluida", "falhou", "cancelada"])   # reconciliou para na_fila e depois cancelou
        caso = json.loads(self.caso_json.read_text(encoding="utf-8"))
        self.assertEqual(caso["status"], "recebido")


if __name__ == "__main__":
    unittest.main(verbosity=2)
