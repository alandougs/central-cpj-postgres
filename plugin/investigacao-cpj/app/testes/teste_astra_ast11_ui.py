"""Inspetor de relação e conferências humanas sobre fontes fictícias."""
from contextlib import closing
import hashlib
import json
import sqlite3
import unittest
from astra_fixture import AstraFixture


class InspetorUI(AstraFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        from reportlab.pdfgen import canvas
        pasta = self.ws / 'casos' / self.caso
        self.hashes = {}
        with closing(sqlite3.connect(self.db_path)) as db:
            db.execute('DELETE FROM arestas')
            for numero in (1, 2, 3):
                documento = f'fonte-{numero}-ficticia.pdf'
                arquivo = pasta / '00-originais' / documento
                if numero < 3:
                    pdf = canvas.Canvas(str(arquivo))
                    pdf.drawString(50, 800, f'FONTE FICTICIA {numero}')
                    pdf.showPage(); pdf.save()
                    self.hashes[arquivo] = hashlib.sha256(arquivo.read_bytes()).hexdigest()
                meta = {'schema': 'astra-evidencia/1', 'origem': 'caso', 'caso': self.caso,
                        'documento': documento, 'arquivo_original': f'casos/{self.caso}/00-originais/{documento}',
                        'pagina': 1, 'fls': str(10 + numero), 'tipo': 'documental',
                        'trecho': 'TRECHO CONTRADITORIO FICTICIO' if numero == 2 else 'TRECHO FICTICIO',
                        'status_fonte': 'OCR NÃO CONFERIDO' if numero == 2 else None,
                        'posicao': 'contradiz' if numero == 2 else None}
                db.execute('INSERT INTO arestas VALUES(?,?,?,?,?,?,?,?)',
                           ('CONTA', 'conta-a-ficticia', 'CONTA', 'conta-b-ficticia',
                            'transferencia ficticia', 'caso', self.caso, json.dumps(meta)))
            db.commit()

    def tearDown(self):
        for arquivo, esperado in self.hashes.items():
            self.assertEqual(hashlib.sha256(arquivo.read_bytes()).hexdigest(), esperado)

    def test_clique_na_aresta_exibe_todas_as_fontes(self):
        self.browser(r'''
        const errors=[];page.on('pageerror',e=>errors.push(e.message));
        await page.goto(url+'/#grafo');await page.waitForLoadState('networkidle');
        await page.locator('#gr-caso').selectOption('OS-901-2099');
        await page.waitForFunction(()=>grEstado==='pronto'&&grEdges.length===1);
        const point=await page.evaluate(()=>{
          cancelAnimationFrame(grAnimId);grAnimId=null;grEnergy=0;grAjustarAoEstabilizar=false;
          grNodes[0].x=120;grNodes[0].y=180;grNodes[1].x=420;grNodes[1].y=180;
          grZoom=1;grPanX=0;grPanY=0;grDesenhar();
          const r=document.querySelector('#cv-grafo').getBoundingClientRect();return{x:r.left+270,y:r.top+180};
        });
        await page.mouse.click(point.x,point.y);
        const panel=page.locator('#gr-detalhes-conteudo');
        assert.equal(await panel.locator('.gr-evidencia').count(),3,'Clique na aresta deve abrir três referências');
        assert.ok((await panel.innerText()).includes('TRECHO CONTRADITORIO FICTICIO'));
        assert.ok(!(await panel.innerText()).includes('"schema"'),'Metadados internos não substituem a referência legível');
        assert.equal(await panel.locator('a[href^="/arquivo/"]').count(),2);
        assert.equal(await panel.getByRole('button',{name:'Conferi o original',exact:true}).count(),2);
        assert.equal(await panel.getByRole('button',{name:'Marcar como candidato',exact:true}).count(),3);
        assert.deepEqual(errors,[]);
        ''')

    def test_conferencia_observacao_historico_reabertura_e_conflito(self):
        self.browser(r'''
        const errors=[];page.on('pageerror',e=>errors.push(e.message));
        async function abrir(){
          await page.goto(url+'/#grafo');await page.waitForLoadState('networkidle');
          await page.locator('#gr-caso').selectOption('OS-901-2099');
          await page.waitForFunction(()=>grEstado==='pronto'&&grEdges.length===1);
          await page.evaluate(()=>grInspecionarNo(grNodes.find(n=>n.valor==='conta-a-ficticia')));
        }
        await abrir();
        const panel=page.locator('#gr-detalhes-conteudo');
        const card=()=>panel.locator('.gr-evidencia').filter({hasText:'fonte-1-ficticia.pdf'});
        async function salvar(button){
          const [r]=await Promise.all([page.waitForResponse(r=>r.url().endsWith('/api/grafo/evidencia/revisar')),button.click()]);
          assert.equal(r.status(),200,await r.text());
          await page.waitForFunction(()=>!document.querySelector('[data-gr-revisar][disabled]'));
        }
        await salvar(card().getByRole('button',{name:'Conferi o original',exact:true}));
        assert.ok((await card().innerText()).includes('astra_ficticio'));
        assert.doesNotMatch(await card().innerText(),/Conferência humana não registrada/);
        await card().locator('textarea').fill("Hipótese fictícia <img src=x onerror=alert('ficticio')>");
        await salvar(card().getByRole('button',{name:'Registrar observação/hipótese',exact:true}));
        await card().locator('textarea').fill('Hipótese fictícia revisada');
        await salvar(card().getByRole('button',{name:'Registrar observação/hipótese',exact:true}));
        await card().getByRole('button',{name:'Ver histórico',exact:true}).click();
        await page.waitForFunction(()=>document.querySelector('[data-gr-historico-conteudo]')?.textContent.includes('Hipótese fictícia <img'));
        assert.equal(await panel.locator('img').count(),0);
        assert.ok((await card().innerText()).includes('conferência do original'));
        await abrir();
        assert.equal(await card().locator('textarea').inputValue(),'Hipótese fictícia revisada');
        assert.ok((await card().innerText()).includes('astra_ficticio'));
        await page.locator('#gf-conta').uncheck();await page.locator('#gf-conta').check();
        assert.equal(await panel.locator('.gr-evidencia').count(),3);
        const missing=panel.locator('.gr-evidencia').filter({hasText:'fonte-3-ficticia.pdf'});
        assert.equal(await missing.getByRole('button',{name:'Conferi o original',exact:true}).count(),0);
        await card().locator('textarea').fill('Rascunho fictício ainda não registrado');
        await salvar(missing.getByRole('button',{name:'Marcar como candidato',exact:true}));
        assert.ok((await missing.innerText()).includes('Candidato marcado pelo operador'));
        assert.equal(await card().locator('textarea').inputValue(),'Rascunho fictício ainda não registrado');
        await page.route('**/api/grafo/evidencia/revisar',r=>r.fulfill({status:409,contentType:'application/json',body:JSON.stringify({erro:'Versão alterada; reabra a fonte.'})}));
        await card().locator('textarea').fill('Texto fictício preservado após conflito');
        await card().getByRole('button',{name:'Registrar observação/hipótese',exact:true}).click();
        await page.waitForFunction(()=>document.querySelector('[data-gr-revisao-aviso]')?.textContent.includes('Versão alterada'));
        assert.equal(await card().locator('textarea').inputValue(),'Texto fictício preservado após conflito');
        await page.unroute('**/api/grafo/evidencia/revisar');
        assert.deepEqual(errors,[]);
        ''')

    def test_leitor_consulta_fontes_e_historico_sem_acoes_de_escrita(self):
        self.browser(r'''
        assert.equal((await context.request.post(url+'/api/sair',{headers:{'X-CPJ':'1'},data:{}})).status(),200);
        assert.equal((await context.request.post(url+'/api/entrar',{headers:{'X-CPJ':'1'},data:{login:'leitor_ficticio',senha:'Ficticia123'}})).status(),200);
        await page.goto(url+'/#grafo');await page.waitForLoadState('networkidle');
        await page.locator('#gr-caso').selectOption('OS-901-2099');
        await page.waitForFunction(()=>grEstado==='pronto'&&grEdges.length===1);
        await page.evaluate(()=>grInspecionarAresta(grEdges[0]));
        const p=page.locator('#gr-detalhes-conteudo');
        assert.equal(await p.locator('.gr-evidencia').count(),3);
        assert.equal(await p.locator('[data-gr-revisar]').count(),0);
        assert.equal(await p.locator('textarea').count(),0);
        const [historico]=await Promise.all([page.waitForResponse(r=>r.url().includes('/api/grafo/evidencia/historico?')),
          p.getByRole('button',{name:'Ver histórico',exact:true}).first().click()]);
        assert.equal(historico.status(),200);
        await page.waitForFunction(()=>{const t=document.querySelector('[data-gr-historico-conteudo]')?.textContent;return t&&t!=='Carregando histórico…'});
        ''')


if __name__ == '__main__':
    unittest.main(verbosity=2)
