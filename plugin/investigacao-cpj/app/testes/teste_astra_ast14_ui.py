"""Paginação visual preserva fontes e estado; não mistura versões ou casos."""
from contextlib import closing
import json
import sqlite3
import time
import unittest
from astra_fixture import AstraFixture


class PaginasUI(AstraFixture,unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.control={'delay':False}
        from flask import request
        @cls.s.app.before_request
        def atrasar_pagina_ficticia():
            if request.path=='/api/grafo' and request.args.get('pagina')=='2' and cls.control['delay']:
                cls.control['delay']=False;time.sleep(.7)

    def setUp(self):
        super().setUp();self.control['delay']=False
        with closing(sqlite3.connect(self.db_path)) as db:
            db.execute('DELETE FROM arestas')
            for i in range(405):
                for numero in range(2 if i==0 else 1):
                    meta={'schema':'astra-evidencia/1','tipo':'documental','caso':self.caso,
                          'documento':f'fonte-ficticia-{numero}.pdf','pagina':numero+1,'fls':str(numero+10),
                          'trecho':f'TRECHO FICTÍCIO {numero}'}
                    db.execute('INSERT INTO arestas VALUES(?,?,?,?,?,?,?,?)',
                               ('CONTA',f'ficticio|{i:05}','CONTA','ficticio|destino','transferiu R$ 10,00 em 01/01/2099 (Pix)' if i==0 else 'relação fictícia',
                                'caso',self.caso,json.dumps(meta)))
            db.commit()

    def test_carrega_proxima_pagina_fontes_e_vista_sem_salto(self):
        self.browser(r'''
        const errors=[];page.on('pageerror',e=>errors.push(e.message));
        await page.goto(url+'/#grafo');await page.waitForLoadState('networkidle');
        await page.locator('#gr-caso').selectOption('OS-901-2099');await page.waitForFunction(()=>grEstado==='pronto'&&grEdges.length===400);
        assert.equal(await page.locator('#b-gr-mais').count(),1,'Carregar próximas relações deve estar disponível');
        assert.match(await page.locator('#gr-paginacao').innerText(),/400.*405/);
        await page.evaluate(()=>{const n=grNodeMap.get('CONTA|ficticio|00000');n.x=240;n.y=180;n.fixo=true;
          grInspecionarNo(n);grZoom=1.25;grPanX=25;grPanY=35;});
        await page.locator('#gf-outros').uncheck();
        const [r]=await Promise.all([page.waitForResponse(r=>r.url().includes('pagina=2')),page.locator('#b-gr-mais').click()]);
        assert.equal(r.status(),200);await page.waitForFunction(()=>grEdges.length===405);
        assert.match(await page.locator('#gr-paginacao').innerText(),/405.*405/);
        assert.equal(await page.locator('#b-gr-mais').isVisible(),false);
        assert.equal(await page.locator('#gf-outros').isChecked(),false);
        assert.deepEqual(await page.evaluate(()=>({x:grNodeMap.get('CONTA|ficticio|00000').x,y:grNodeMap.get('CONTA|ficticio|00000').y,
          zoom:grZoom,px:grPanX,py:grPanY,selecao:grSelectedNode?.id})),{x:240,y:180,zoom:1.25,px:25,py:35,selecao:'CONTA|ficticio|00000'});
        assert.equal(await page.locator('#gr-detalhes-conteudo .gr-evidencia').count(),2);
        assert.equal(await page.evaluate(()=>new Set(grEdges.map(a=>a.relacao_id)).size),405);
        assert.deepEqual(errors,[]);
        ''')

    def test_versao_alterada_preserva_grafo_e_exige_recarregar(self):
        self.browser(r'''
        await page.goto(url+'/#grafo');await page.waitForLoadState('networkidle');
        await page.locator('#gr-caso').selectOption('OS-901-2099');await page.waitForFunction(()=>grEstado==='pronto'&&grEdges.length===400);
        const created=await context.request.post(url+'/api/grafo/vinculo',{headers:{'X-CPJ':'1'},data:{
          a_tipo:'CONTA',a_valor:'ficticio|00000',b_tipo:'CONTA',b_valor:'ficticio|novo',relacao:'hipótese fictícia nova',
          caso:'OS-901-2099',documento:'',pagina:null,fls:'',observacao:'Hipótese fictícia do teste'}});
        assert.equal(created.status(),200);
        const [r]=await Promise.all([page.waitForResponse(r=>r.url().includes('pagina=2')),page.locator('#b-gr-mais').click()]);
        assert.equal(r.status(),409);await page.waitForFunction(()=>document.querySelector('#gr-paginacao').textContent.includes('mudaram'));
        assert.equal(await page.evaluate(()=>grEdges.length),400);
        await page.locator('#b-gr-buscar').click();await page.waitForFunction(()=>grEstado==='pronto'&&grDados.total===406);
        assert.match(await page.locator('#gr-paginacao').innerText(),/400.*406/);
        ''')

    def test_pagina_atrasada_nao_troca_caso_e_falha_preserva_resultado(self):
        self.control['delay']=True
        self.browser(r'''
        await page.goto(url+'/#grafo');await page.waitForLoadState('networkidle');
        await page.locator('#gr-caso').selectOption('OS-901-2099');await page.waitForFunction(()=>grEstado==='pronto'&&grEdges.length===400);
        const old=page.waitForResponse(r=>r.url().includes('pagina=2'));
        await page.locator('#b-gr-mais').click();
        await page.locator('#gr-caso').selectOption('OS-902-2099');await old;
        await page.waitForFunction(()=>grEstado==='pronto'&&grEdges.length===0);
        assert.equal(await page.locator('#gr-caso').inputValue(),'OS-902-2099');
        await page.locator('#gr-caso').selectOption('OS-901-2099');await page.waitForFunction(()=>grEstado==='pronto'&&grEdges.length===400);
        await page.route('**/api/grafo?*',route=>{
          if(new URL(route.request().url()).searchParams.get('pagina')==='2')return route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({erro:'Falha fictícia de leitura'})});
          return route.continue();
        });
        await page.locator('#b-gr-mais').click();await page.waitForFunction(()=>document.querySelector('#gr-paginacao').textContent.includes('Falha fictícia'));
        assert.equal(await page.evaluate(()=>grEdges.length),400);
        assert.equal(await page.locator('#b-gr-mais').isEnabled(),true);
        ''')

    def test_recorte_da_pergunta_nao_herda_erro_de_pagina_anterior(self):
        self.browser(r'''
        await page.goto(url+'/#grafo');await page.waitForLoadState('networkidle');
        await page.locator('#gr-caso').selectOption('OS-901-2099');await page.waitForFunction(()=>grEstado==='pronto'&&grEdges.length===400);
        await page.route('**/api/grafo?*',route=>new URL(route.request().url()).searchParams.get('pagina')==='2'?
          route.fulfill({status:409,contentType:'application/json',body:JSON.stringify({erro:'Mudança fictícia de versão'})}):route.continue());
        await page.locator('#b-gr-mais').click();await page.waitForFunction(()=>document.querySelector('#gr-paginacao').textContent.includes('mudaram'));
        await page.evaluate(()=>grInspecionarNo(grNodeMap.get('CONTA|ficticio|00000')));
        await page.locator('#astra-pergunta').fill('Quais documentos sustentam este caminho do dinheiro?');
        await page.locator('#b-astra-perguntar').click();await page.locator('[data-astra-relacao]').first().waitFor();
        await page.locator('[data-astra-relacao]').first().click();
        assert.doesNotMatch(await page.locator('#gr-paginacao').innerText(),/mudaram/);
        assert.equal(await page.locator('#b-gr-mais').isVisible(),false);
        ''')


if __name__=='__main__':unittest.main(verbosity=2)
