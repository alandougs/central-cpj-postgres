"""Todas as fontes de uma relação são visíveis e abrem documentos distintos."""
from contextlib import closing
import json
import sqlite3
import unittest
from astra_fixture import AstraFixture


class FontesUI(AstraFixture, unittest.TestCase):
    def test_fontes_independentes_ausencia_contradicao_e_hipotese_conferida(self):
        from reportlab.pdfgen import canvas
        pasta = self.ws / 'casos' / self.caso
        relacao = 'transferiu R$ 10,00 em 01/01/2099 (Pix)'
        with closing(sqlite3.connect(self.db_path)) as db:
            for documento, pagina in [('fonte-a-ficticia.pdf', 2), ('fonte-b-ficticia.pdf', 5), ('fonte-ausente.pdf', None)]:
                if pagina:
                    pdf = canvas.Canvas(str(pasta / '00-originais' / documento))
                    for numero in range(1, 6):
                        pdf.drawString(50, 800, f'FONTE FICTICIA {documento} PAGINA {numero}')
                        pdf.showPage()
                    pdf.save()
                meta = {'schema': 'astra-evidencia/1', 'origem': 'caso', 'caso': self.caso,
                        'documento': documento, 'arquivo_original': f'casos/{self.caso}/00-originais/{documento}',
                        'arquivo_derivado': None, 'pagina': pagina, 'paginas': [pagina] if pagina else None,
                        'fls': None, 'tipo': 'documental', 'localizador_original': documento,
                        'trecho': 'AFIRMACAO FICTICIA CONTRARIA' if pagina == 5 else 'TRECHO FICTICIO LITERAL',
                        'status_fonte': 'DIVERGENCIA FICTICIA REGISTRADA' if pagina == 5 else None,
                        'registro_origem': {'linha': None, 'seq': None}}
                db.execute('INSERT INTO arestas VALUES(?,?,?,?,?,?,?,?)',
                           ('CONTA', 'banco ficticio|1234', 'CONTA', 'banco ficticio|7890', relacao,
                            'caso', self.caso, json.dumps(meta, ensure_ascii=False)))
            db.commit()
        criado = self.post('/api/grafo/vinculo', self.payload(
            b_tipo='CONTA', b_valor='banco ficticio|7890', relacao=relacao,
            documento='', pagina=None, fls='', observacao="Hipótese d'água <img src=x onerror=alert('ficticio')>"))
        self.assertEqual(criado.status_code, 200, criado.get_json())
        import vinculos_manuais as vm
        vm.atualizar(self.ws, criado.get_json()['id'], {'status': 'conferido'}, 'revisor_ficticio', versao=1)
        self.browser(r'''
        const errors=[];page.on('pageerror',e=>errors.push(e.message));
        await page.goto(url+'/#grafo');await page.waitForLoadState('networkidle');
        await Promise.all([page.waitForResponse(r=>r.url().includes('/api/grafo?caso=OS-901-2099')),page.locator('#gr-caso').selectOption('OS-901-2099')]);
        await page.waitForFunction(()=>grEstado==='pronto');
        await page.evaluate(()=>grInspecionarNo(grNodes.find(n=>n.valor==='banco ficticio|7890')));
        const panel=page.locator('#gr-detalhes-conteudo');
        const sources=panel.locator('.gr-evidencia');assert.equal(await sources.count(),4);
        const text=await panel.innerText();
        for(const phrase of ['fonte-a-ficticia.pdf','fonte-b-ficticia.pdf','fonte-ausente.pdf','AFIRMACAO FICTICIA CONTRARIA','DIVERGENCIA FICTICIA REGISTRADA','revisor_ficticio'])assert.ok(text.includes(phrase),phrase);
        assert.ok(/hipótese manual/i.test(text));assert.ok(/não informad/i.test(text));
        const links=panel.locator('a[href^="/arquivo/"]');assert.equal(await links.count(),2);
        const hrefs=await links.evaluateAll(links=>links.map(a=>a.getAttribute('href')));
        assert.ok(hrefs.some(h=>h.endsWith('fonte-a-ficticia.pdf#page=2')));
        assert.ok(hrefs.some(h=>h.endsWith('fonte-b-ficticia.pdf#page=5')));
        for(const href of hrefs){const response=await context.request.get(url+href.split('#')[0]);assert.equal(response.status(),200);assert.ok(response.headers()['content-type'].includes('application/pdf'))}
        assert.equal(await panel.getByRole('button',{name:'remover',exact:true}).count(),1);
        assert.equal(await panel.locator('img').count(),0);
        assert.equal(await page.evaluate(()=>grEdges.length),1);
        assert.deepEqual(errors,[]);
        ''')


if __name__ == '__main__':
    unittest.main(verbosity=2)
