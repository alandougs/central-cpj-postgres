"""AST05: contrato HTTP de vínculos e origem documental, com dados fictícios."""
import json
import sqlite3
import unittest
from astra_fixture import AstraFixture


class Contrato(AstraFixture,unittest.TestCase):
    def test_campos_reaparecem_no_grafo(self):
        p=self.payload(relacao='fonte preservada')
        r=self.post('/api/grafo/vinculo',p)
        self.assertEqual(r.status_code,200,r.get_json())
        edges=self.client.get('/api/grafo',query_string={'caso':self.caso}).get_json()['arestas']
        a=next(a for a in edges if a['relacao']==p['relacao'])
        self.assertEqual(a['caso'],self.caso)
        self.assertEqual(a['evidencia'],{'documento':'oficio-ficticio.pdf','pagina':7,'fls':'12','observacao':p['observacao']})

    def test_aliases_legados_sem_perder_fonte(self):
        p=self.payload(relacao='compatibilidade')
        p['caso_id']=p.pop('caso'); p['fonte']=p.pop('documento'); p['obs']=p.pop('observacao')
        self.assertEqual(self.post('/api/grafo/vinculo',p).status_code,200)
        a=next(a for a in self.client.get('/api/grafo',query_string={'caso':self.caso}).get_json()['arestas'] if a['relacao']=='compatibilidade')
        self.assertEqual(a['evidencia']['documento'],'oficio-ficticio.pdf')

    def test_duplicata_rejeitada_sem_apagar_primeiro_vinculo(self):
        p=self.payload(relacao='sem duplicação')
        self.assertEqual(self.post('/api/grafo/vinculo',p).status_code,200)
        self.assertEqual(self.post('/api/grafo/vinculo',p).status_code,409)

    def test_validacao_e_identidade_nao_deduzida_pelo_nome(self):
        for extra,code in [({'caso':'OS-999-2099'},404),({'caso':''},400),({'pagina':-1},400),({'pagina':'sete'},400),({'a_tipo':'PESSOA','a_valor':'Ana Fictícia'},400),({'a_tipo':'inexistente'},400),({'caso_id':'OS-902-2099'},400),({'a_valor':[]},400)]:
            with self.subTest(extra=extra):
                self.assertEqual(self.post('/api/grafo/vinculo',self.payload(**extra)).status_code,code)

    def test_leitor_e_sem_csrf_nao_alteram_indice(self):
        with sqlite3.connect(self.db_path) as db: antes=db.execute('SELECT count(*) FROM arestas').fetchone()[0]
        self.assertEqual(self.client.post('/api/grafo/vinculo',json=self.payload()).status_code,403)
        self.client.post('/api/sair',headers={'X-CPJ':'1'})
        self.client.post('/api/entrar',json={'login':'leitor_ficticio','senha':'Ficticia123'},headers={'X-CPJ':'1'})
        self.assertEqual(self.post('/api/grafo/vinculo',self.payload()).status_code,403)
        with sqlite3.connect(self.db_path) as db: self.assertEqual(db.execute('SELECT count(*) FROM arestas').fetchone()[0],antes)

    def test_texto_adversarial_e_auditoria_sem_trecho_investigativo(self):
        texto="<img src=x onerror=alert('ficticio')> ' OR 1=1 --"
        r=self.post('/api/grafo/vinculo',self.payload(relacao='texto literal',observacao=texto))
        self.assertEqual(r.status_code,200)
        logs=(self.ws/'config/auditoria.log').read_text(encoding='utf-8')
        self.assertNotIn(texto,logs)

    def test_ui_preserva_campos_e_inspecao_segura(self):
        self.browser(r'''
        await page.goto(url+'/#grafo'); await page.waitForLoadState('networkidle');
        await page.locator('#gr-caso').selectOption('OS-901-2099');
        await page.locator('#b-gr-novo-vinc').click();
        const form=page.locator('#f-vinculo');
        assert.equal(await form.locator('[name=caso_id]').inputValue(),'OS-901-2099');
        await form.locator('[name=a_tipo]').selectOption('NOME');
        await form.locator('[name=a_valor]').fill("Nome ficticio d'agua");
        await form.locator('[name=b_tipo]').selectOption('CONTA');
        await form.locator('[name=b_valor]').fill('banco ficticio|7890');
        await form.locator('[name=relacao]').fill('hipótese UI');
        await form.locator('[name=documento]').fill('oficio-ui.pdf');
        await form.locator('[name=pagina]').fill('8');
        await form.locator('[name=fls]').fill('13');
        await form.locator('[name=observacao]').fill("<img src=x onerror=alert('ficticio')>");
        const [response]=await Promise.all([page.waitForResponse(r=>r.url().endsWith('/api/grafo/vinculo')&&r.request().method()==='POST'),form.locator('[type=submit]').click()]);
        assert.equal(response.status(),200);
        await page.waitForFunction(()=>grNodes.some(n=>n.valor==='banco ficticio|7890'));
        await page.evaluate(()=>grInspecionarNo(grNodes.find(n=>n.valor==='banco ficticio|7890')));
        const text=await page.locator('#gr-detalhes-conteudo').innerText();
        assert.ok(text.includes('oficio-ui.pdf'));assert.ok(text.includes('pág. 8'));assert.ok(text.includes('13'));
        assert.equal(await page.locator('#gr-detalhes-conteudo img').count(),0);
        ''')


if __name__=='__main__': unittest.main(verbosity=2)
