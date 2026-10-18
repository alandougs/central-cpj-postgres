"""AST15: HTTP real + Edge em workspace fictício, sem benchmark de produção."""
import unittest
from astra_fixture import AstraFixture

class AtualizacaoUI(AstraFixture,unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from flask import request,jsonify
        cls.ocr=[]
        @cls.s.app.before_request
        def controle_ficticio():
            if request.path=='/__ast15' and request.method=='POST':
                d=request.get_json()
                if 'ocr' in d:cls.ocr=d['ocr']
                if 'tarefa' in d:cls.s.tarefas.at(d['tarefa'],**d['dados'])
                return jsonify(ok=True)
            if request.path=='/api/fila':return jsonify(idioma_ocr='por',trabalhos=cls.ocr)

    def setUp(self):
        super().setUp()
        type(self).ocr=[]
        with self.s.tarefas.trava:self.s.tarefas.t.clear()
        self.tid=self.s.tarefas.nova('ia','Análise FICTÍCIA','astra_ficticio',caso=self.caso)
        self.s.tarefas.at(self.tid,status='executando',etapa='analisando FICTÍCIO',progresso=35,resultado={'resumo':'RESUMO FICTÍCIO'})

    def test_consulta_unica_render_estavel_e_contexto_preservado(self):
        self.browser(r'''
        const errors=[];page.on('pageerror',e=>errors.push(e.message));
        await page.goto(url+'/#casos');await page.waitForSelector('#app:not([hidden])');
        await page.evaluate(()=>abrirCaso('OS-901-2099'));
        await page.waitForSelector('#ia-painel details');
        await page.evaluate(()=>reiniciarPolling());
        const requests=[];page.on('request',r=>{if(r.url().endsWith('/api/tarefas'))requests.push(r.method())});
        await page.evaluate(()=>Promise.all([atualizarTarefas(),atualizarIA()]));
        assert.equal(requests.length,1,'Consumidores concorrentes compartilham GET real');
        await page.locator('#ia-painel details').evaluate(e=>e.open=true);
        await page.evaluate(()=>{window.oldDetails=document.querySelector('#ia-painel details');window.muts=0;window.ob=new MutationObserver(ms=>muts+=ms.length);ob.observe(document.querySelector('#ia-painel'),{subtree:true,childList:true,characterData:true})});
        await page.evaluate(()=>ciclo());
        assert.equal(await page.evaluate(()=>muts),0,'Dados iguais não substituem DOM');
        assert.equal(await page.evaluate(()=>oldDetails===document.querySelector('#ia-painel details')&&oldDetails.open),true);
        await page.evaluate(()=>reiniciarPolling());
        await page.locator('#b-explorar-astra').click();await page.waitForFunction(()=>grEstado==='pronto');
        await page.locator('#astra-pergunta').fill('PERGUNTA FICTÍCIA EM EDIÇÃO');
        await page.evaluate(()=>ciclo());
        assert.equal(await page.locator('#astra-pergunta').inputValue(),'PERGUNTA FICTÍCIA EM EDIÇÃO');
        assert.deepEqual(errors,[]);
        ''')

    def test_erro_visivel_retry_leitura_oculta_e_retorno(self):
        self.browser(r'''
        await page.goto(url+'/#casos');await page.waitForSelector('#app:not([hidden])');
        await page.evaluate(()=>abrirCaso('OS-901-2099'));await page.waitForSelector('#ia-painel .job');
        await page.evaluate(()=>reiniciarPolling());
        const writes=[];page.on('request',r=>{if(r.method()==='POST')writes.push(r.url())});
        await page.route('**/api/tarefas',r=>r.fulfill({status:503,contentType:'application/json',body:JSON.stringify({erro:'Falha FICTÍCIA'})}));
        await page.evaluate(()=>ciclo());
        assert.match(await page.locator('#polling-aviso').innerText(),/indisponível|desatualizad/i);
        assert.match(await page.locator('#ia-painel').innerText(),/analisando FICTÍCIO/);
        await page.unroute('**/api/tarefas');await page.locator('#polling-retentar').click();
        await page.waitForFunction(()=>document.querySelector('#polling-aviso').textContent==='');
        await page.evaluate(()=>{Object.defineProperty(document,'hidden',{configurable:true,value:true});document.dispatchEvent(new Event('visibilitychange'))});
        let gets=0;page.on('request',r=>{if(r.url().endsWith('/api/tarefas'))gets++});
        await page.evaluate(()=>ciclo());assert.equal(gets,0);
        await Promise.all([page.waitForResponse(r=>r.url().endsWith('/api/tarefas')),page.evaluate(()=>{Object.defineProperty(document,'hidden',{configurable:true,value:false});document.dispatchEvent(new Event('visibilitychange'))})]);assert.equal(gets,1);
        assert.deepEqual(writes,[],'Retry de leitura não reexecuta comando');
        ''')

    def test_conclusao_nao_desmonta_rascunho_e_erro_cancelamento_nao_vira_sucesso(self):
        self.browser(r'''
        await page.goto(url+'/#casos');await page.waitForSelector('#app:not([hidden])');
        await page.evaluate(()=>abrirCaso('OS-901-2099'));await page.waitForSelector('#ia-painel .job');
        await page.evaluate(()=>reiniciarPolling());
        await page.evaluate(()=>abrirEditor('OS-901-2099'));
        const input=page.locator('#ed-secoes textarea').first();await input.fill('TEXTO FICTÍCIO NÃO DESCARTAR');
        let dialogs=0;page.on('dialog',async d=>{dialogs++;await d.dismiss()});
        await page.evaluate(()=>atualizarIA([{id:'ia-fim-ficticio',tipo:'ia',caso:'OS-901-2099',status:'concluida',titulo:'Relatório FICTÍCIO',resultado:{resumo:'Concluído FICTÍCIO'}}]));
        assert.equal(await input.inputValue(),'TEXTO FICTÍCIO NÃO DESCARTAR');assert.equal(dialogs,0);
        assert.equal(await page.locator('#editor').isVisible(),true);
        assert.match(await page.locator('#ia-painel').innerText(),/Atualizar ficha|resultado/i);
        await page.evaluate(()=>{clearTimeout(edTimer);fecharEditor()});
        await page.evaluate(()=>atualizarIA());
        await page.route('**/api/tarefas/*/cancelar',r=>r.fulfill({json:{ok:false}}));
        page.removeAllListeners('dialog');page.on('dialog',d=>d.accept());
        await page.locator('#ia-painel [data-cancel]').click();
        await page.waitForFunction(()=>/não.*cancel|cancelamento.*não/i.test((document.querySelector('#toast')||{}).innerText||''),null,{timeout:5000});
        assert.match(await page.locator('#toast').innerText(),/não.*cancel|cancelamento.*não/i);
        ''')

    def test_etapas_ocr_ia_relatorio_revisao_sem_refresh(self):
        self.browser(r'''
        await page.goto(url+'/#nova');await page.waitForSelector('#app:not([hidden])');
        for(const etapa of ['na_fila','processando','concluido']){
          const fase={na_fila:'na fila',processando:'extração/OCR',concluido:'concluído'}[etapa];
          assert.equal((await context.request.post(url+'/__ast15',{headers:{'X-CPJ':'1'},data:{ocr:[{caso:'OS-901-2099',arquivo:'FICTICIO.pdf',status:etapa,etapa:fase,progresso:etapa==='concluido'?100:35,paginas:70,pagina_atual:40}]}})).status(),200);
          await page.evaluate(()=>ciclo());
          const texto=await page.locator('#fila').innerText();
          assert.match(texto,{na_fila:/Aguardando sua vez/,processando:/Extraindo texto.*reconhecendo páginas/,concluido:/Processamento concluído/}[etapa]);
          if(etapa==='processando')assert.match(texto,/Página 40 de 70/);
          assert.equal(await page.locator('#fila .badge').first().innerText(),{na_fila:'na fila',processando:'processando',concluido:'concluído'}[etapa]);
        }
        await page.evaluate(()=>abrirAba('casos'));await page.evaluate(()=>abrirCaso('OS-901-2099'));
        const tid=await page.locator('#ia-painel [data-cancel]').getAttribute('data-cancel');
        for(const etapa of ['análise FICTÍCIA','redação FICTÍCIA','revisão FICTÍCIA']){
          await context.request.post(url+'/__ast15',{headers:{'X-CPJ':'1'},data:{tarefa:tid,dados:{status:'executando',etapa,progresso:50}}});
          await page.evaluate(()=>ciclo());assert.ok((await page.locator('#ia-painel').innerText()).includes(etapa));
          assert.equal(await page.locator('#ia-painel [data-ia-resultado]').count(),0);
        }
        await context.request.post(url+'/__ast15',{headers:{'X-CPJ':'1'},data:{tarefa:tid,dados:{status:'concluida',etapa:'Revisão concluída FICTÍCIA',progresso:100,fim:new Date().toISOString()}}});
        await page.evaluate(()=>ciclo());assert.equal(await page.locator('#ia-painel [data-ia-resultado]').count(),1);
        assert.match(await page.locator('#ia-painel').innerText(),/Revisão concluída FICTÍCIA/);
        ''')

    def test_agente_indisponivel_nao_silencia_erro_e_recupera(self):
        self.browser(r'''
        const errors=[];page.on('pageerror',e=>errors.push(e.message));
        await page.goto(url+'/#sistema');await page.waitForSelector('#app:not([hidden])');
        await page.waitForLoadState('networkidle');await page.evaluate(()=>reiniciarPolling());
        await page.route('**/api/plantao/agentes',r=>r.fulfill({status:503,contentType:'application/json',body:JSON.stringify({erro:'Plantão FICTÍCIO indisponível'})}));
        await page.evaluate(()=>{nCiclo=2;return ciclo()});
        assert.match(await page.locator('#polling-aviso').innerText(),/Plantão FICTÍCIO indisponível/);
        assert.equal(await page.evaluate(()=>polling.erros),1);
        await page.unroute('**/api/plantao/agentes');
        await page.locator('#polling-retentar').click();
        await page.waitForFunction(()=>document.querySelector('#polling-aviso').textContent==='');
        assert.deepEqual(errors,[]);
        ''')

if __name__=='__main__':unittest.main(verbosity=2)
