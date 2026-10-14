"""Exclusão UI por identidade, inclusive aresta de entrada e texto com aspas."""
import json
import sqlite3
import unittest
from contextlib import closing
from astra_fixture import AstraFixture


class ExclusaoUI(AstraFixture, unittest.TestCase):
    def test_entrada_aspas_cancelamento_e_exclusao_exata_preservam_documental(self):
        p = self.payload(a_tipo='NOME', a_valor="Nome fictício d'água", relacao="Pix d'água")
        primeiro = self.post('/api/grafo/vinculo', p).get_json()
        segundo = self.post('/api/grafo/vinculo', dict(p, observacao='Outra anotação fictícia')).get_json()
        with closing(sqlite3.connect(self.db_path)) as db:
            db.execute('INSERT INTO arestas VALUES (?,?,?,?,?,?,?,?)', ('NOME', "nome ficticio d'agua", 'CHAVE_PIX', 'chave-ficticia', p['relacao'], 'autos', self.caso, 'pág. 4; fls. 8'))
            db.commit()
        self.browser("const manualId=" + json.dumps(primeiro['id']) + "; const otherId=" + json.dumps(segundo['id']) + r'''
        const errors=[];page.on('pageerror',e=>errors.push(e.message));
        await page.goto(url+'/#grafo');await page.waitForLoadState('networkidle');
        await Promise.all([page.waitForResponse(r=>r.url().includes('/api/grafo?caso=OS-901-2099')),page.locator('#gr-caso').selectOption('OS-901-2099')]);
        await page.waitForFunction(()=>grEstado==='pronto');
        await page.waitForFunction(()=>grNodes.some(n=>n.valor==='chave-ficticia'));
        await page.evaluate(()=>grInspecionarNo(grNodes.find(n=>n.valor==='chave-ficticia')));
        const panel=page.locator('#gr-detalhes-conteudo');
        const remove=panel.getByRole('button',{name:'remover',exact:true});
        assert.equal(await remove.count(),2);
        let deletions=0;page.on('request',r=>{if(r.url().endsWith('/api/grafo/vinculo/remover'))deletions++});
        page.once('dialog',d=>d.dismiss());await remove.first().click();
        await page.waitForTimeout(150);assert.equal(deletions,0);
        page.once('dialog',d=>d.accept());
        const sent=page.waitForRequest(r=>r.url().endsWith('/api/grafo/vinculo/remover'),{timeout:2000});
        await remove.first().click();const request=await sent;
        const data=request.postDataJSON();assert.ok([manualId,otherId].includes(data.id));
        assert.equal(data.caso,'OS-901-2099');assert.equal(data.versao,1);
        assert.equal(data.a_valor,undefined);assert.equal(data.b_valor,undefined);
        await page.waitForFunction(()=>grEstado==='pronto'&&grEdges.flatMap(e=>e.evidencias||[]).filter(e=>e.manual_id).length===1);
        const graph=await (await context.request.get(url+'/api/grafo?caso=OS-901-2099')).json();
        const sources=graph.arestas.flatMap(e=>e.evidencias);
        assert.equal(sources.filter(e=>e.origem==='autos').length,1);
        assert.equal(sources.filter(e=>e.manual_id).length,1);
        assert.notEqual(sources.find(e=>e.manual_id).manual_id,data.id);
        assert.deepEqual(errors,[]);
        ''')


if __name__ == '__main__':
    unittest.main(verbosity=2)
