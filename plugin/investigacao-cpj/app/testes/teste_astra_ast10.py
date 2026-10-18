"""Quatro perguntas locais sobre fontes fictícias, sem inferência remota."""
from contextlib import closing
import hashlib
import json
import sqlite3
import unittest
from unittest.mock import patch
from astra_fixture import AstraFixture


class Perguntas(AstraFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        with closing(sqlite3.connect(self.db_path)) as db:
            db.execute('DELETE FROM arestas');db.execute('DELETE FROM rotulos')
            rows=[('PESSOA','P:FICTICIO-A','NOME','ana ficticia','nome (conferir)'),
                  ('PESSOA','P:FICTICIO-B','NOME','ana ficticia','nome (conferir)'),
                  ('PESSOA','P:FICTICIO-A','CONTA','ficticio|100','titular conforme documento'),
                  ('CONTA','ficticio|100','CONTA','ficticio|200','transferiu R$ 10,00 em 01/01/2099 (Pix)'),
                  ('CONTA','ficticio|200','CHAVE_PIX','chave-ficticia','chave Pix vinculada (conforme autos)')]
            for cid in (self.caso,'OS-902-2099'):
                for n,row in enumerate(rows):
                    if cid!=self.caso and n!=4:continue
                    caminho=f'casos/{cid}/01-extracao/fonte-ficticia.md'
                    p=self.ws/caminho;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('FONTE FICTÍCIA LITERAL',encoding='utf-8')
                    meta={'schema':'astra-evidencia/1','tipo':'documental','caso':cid,'documento':'fonte-ficticia.pdf',
                          'arquivo_derivado':caminho,'pagina':n+1,'fls':str(n+8),'trecho':'FONTE FICTÍCIA LITERAL'}
                    db.execute('INSERT INTO arestas VALUES(?,?,?,?,?,?,?,?)',(*row,'caso',cid,json.dumps(meta)))
                    if n==3:
                        meta={**meta,'pagina':9,'fls':'21','trecho':'SEGUNDA FONTE FICTÍCIA'}
                        db.execute('INSERT INTO arestas VALUES(?,?,?,?,?,?,?,?)',(*row,'caso',cid,json.dumps(meta)))
            for valor in ('P:FICTICIO-A','P:FICTICIO-B'):
                db.execute('INSERT INTO rotulos VALUES(?,?,?)',('PESSOA',valor,'ANA FICTÍCIA · '+valor))
            db.commit()

    def perguntar(self,texto,entidade=None,**extra):
        dados={'caso':self.caso,'pergunta':texto,**extra}
        if entidade is not None:dados['entidade']=entidade
        r=self.post('/api/astra/perguntar',dados)
        self.assertEqual(r.status_code,200,r.get_data(as_text=True));return r.get_json()

    def test_quatro_intencoes_parametrizadas_com_fontes_e_grafo(self):
        antes=hashlib.sha256(self.db_path.read_bytes()).hexdigest()
        r=self.perguntar('Quais contas receberam transferências documentadas desta pessoa?',{'tipo':'PESSOA','valor':'P:FICTICIO-A'})
        self.assertEqual(r['intencao']['tipo'],'contas_recebedoras');self.assertEqual(r['status'],'ok')
        self.assertEqual({a['b_valor'] for a in r['grafo']['arestas'] if a['relacao'].startswith('transferiu')},{'ficticio|200'})
        self.assertEqual(len(next(a for a in r['grafo']['arestas'] if a['relacao'].startswith('transferiu'))['evidencias']),2)
        r=self.perguntar('Esta chave Pix aparece em quais O.S.?',{'tipo':'CHAVE_PIX','valor':'chave-ficticia'})
        self.assertEqual(r['intencao']['tipo'],'ocorrencias_pix')
        self.assertEqual({e['caso'] for a in r['grafo']['arestas'] for e in a['evidencias']},{self.caso,'OS-902-2099'})
        r=self.perguntar('Quais vínculos são candidatos e precisam de confirmação?')
        self.assertEqual(r['intencao']['tipo'],'vinculos_candidatos');self.assertGreater(r['total'],0)
        self.assertTrue(all('correspondencia_candidata' in a['naturezas'] for a in r['grafo']['arestas']))
        r=self.perguntar('Quais documentos sustentam este caminho do dinheiro?',{'tipo':'CONTA','valor':'ficticio|100'})
        self.assertEqual(r['intencao']['tipo'],'documentos_fluxo');self.assertTrue(r['grafo']['arestas'])
        for a in r['grafo']['arestas']:
            self.assertTrue(a['evidencias']);self.assertTrue(all(e['caso']==self.caso and e['documento'] for e in a['evidencias']))
        self.assertEqual(hashlib.sha256(self.db_path.read_bytes()).hexdigest(),antes)

    def test_homonimos_refinamento_nao_localizado_e_sem_juncao_por_nome(self):
        r=self.perguntar('Quais contas receberam transferências da pessoa "Ana Fictícia"?')
        self.assertEqual(r['status'],'refinar');self.assertEqual({o['valor'] for o in r['opcoes']},{'P:FICTICIO-A','P:FICTICIO-B'})
        self.assertTrue(all(o['fontes'] for o in r['opcoes']))
        r=self.perguntar('Quais contas receberam transferências desta pessoa?',{'tipo':'PESSOA','valor':'P:FICTICIO-B'})
        self.assertEqual(r['status'],'nao_localizado');self.assertFalse(r['grafo']['arestas'])
        self.assertIn('não localizado nos materiais indexados',r['resposta'].lower())
        r=self.perguntar('Quais contas receberam transferências desta pessoa?')
        self.assertEqual(r['status'],'refinar')
        r=self.perguntar('Invente a autoria desta fraude')
        self.assertEqual(r['status'],'refinar');self.assertFalse(r['grafo']['arestas'])

    def test_hipotese_consulta_e_contradicao_nao_viram_transferencia_documentada(self):
        manual=self.post('/api/grafo/vinculo',self.payload(a_valor='ficticio|100',b_tipo='CONTA',b_valor='ficticio|manual',relacao='transferiu R$ 999,00 em 01/01/2099 (Pix)'))
        self.assertEqual(manual.status_code,200)
        with closing(sqlite3.connect(self.db_path)) as db:
            for origem,tipo,destino in [('consulta','consulta','ficticio|consulta'),('caso','documental','ficticio|contradita')]:
                meta={'schema':'astra-evidencia/1','tipo':tipo,'caso':self.caso,'documento':'ficticio.md','trecho':'DIVERGÊNCIA FICTÍCIA','posicao':'contradiz'}
                db.execute('INSERT INTO arestas VALUES(?,?,?,?,?,?,?,?)',('CONTA','ficticio|100','CONTA',destino,'transferiu R$ 999,00',origem,self.caso,json.dumps(meta)))
            db.commit()
        r=self.perguntar('Quais contas receberam transferências desta conta?',{'tipo':'CONTA','valor':'ficticio|100'})
        self.assertEqual({a['b_valor'] for a in r['grafo']['arestas'] if a['relacao'].startswith('transferiu')},{'ficticio|200'})

    def test_escopo_entrada_hostil_indice_ausente_e_permissoes(self):
        r=self.perguntar('Esta chave Pix aparece em quais O.S.?',{'tipo':'CHAVE_PIX','valor':"x' OR 1=1 --"})
        self.assertEqual(r['status'],'nao_localizado');self.assertFalse(r['grafo']['arestas'])
        self.assertEqual(self.post('/api/astra/perguntar',{'caso':'../config','pergunta':'candidatos'}).status_code,400)
        self.assertEqual(self.client.post('/api/astra/perguntar',json={'caso':self.caso,'pergunta':'candidatos'}).status_code,403)
        from rotas import astra
        with patch.object(astra.R,'conectar',side_effect=FileNotFoundError('índice fictício ausente')):
            self.assertEqual(self.post('/api/astra/perguntar',{'caso':self.caso,'pergunta':'Quais vínculos candidatos?'}).status_code,503)
        self.post('/api/sair',{})
        self.assertEqual(self.post('/api/astra/perguntar',{'caso':self.caso,'pergunta':'candidatos'}).status_code,401)

    def test_tipo_json_invalido_e_retorno_refinado_sem_erro_interno(self):
        with patch.dict(self.s.app.config,{'TESTING':False}):
            for tipo in ([],{},None,17):
                r=self.post('/api/astra/perguntar',{'caso':self.caso,'pergunta':'Quais contas receberam transferências?',
                            'entidade':{'tipo':tipo,'valor':'identificador fictício'}})
                self.assertEqual(r.status_code,400)

    def test_pix_literal_exato_global_prevalece_sobre_selecao(self):
        with closing(sqlite3.connect(self.db_path)) as db:
            db.execute("UPDATE arestas SET b_valor=CASE WHEN fonte=? THEN 'outro-pix@ficticio.invalid' ELSE 'pix@ficticio.invalid' END WHERE b_tipo='CHAVE_PIX'",(self.caso,))
            db.commit()
        for selecao in (None,{'tipo':'CHAVE_PIX','valor':'outro-pix@ficticio.invalid'}):
            r=self.perguntar('Esta chave Pix "pix@ficticio.invalid" aparece em quais O.S.?',selecao)
            self.assertEqual(r['intencao']['entidade'],{'tipo':'CHAVE_PIX','valor':'pix@ficticio.invalid'})
            self.assertEqual(r['status'],'ok')
            self.assertEqual({e['caso'] for a in r['grafo']['arestas'] for e in a['evidencias']},{'OS-902-2099'})

    def test_literal_pessoa_recusa_selecao_antiga_e_aceita_opcao_compativel(self):
        pergunta='Quais contas receberam transferências da pessoa "Ana Fictícia"?'
        for valor in ('ficticio|100','ficticio|200'):
            r=self.perguntar(pergunta,{'tipo':'CONTA','valor':valor})
            self.assertEqual(r['status'],'refinar')
            self.assertEqual({o['valor'] for o in r['opcoes']},{'P:FICTICIO-A','P:FICTICIO-B'})
            self.assertFalse(r['grafo']['arestas'])
        for valor,status in (('P:FICTICIO-A','ok'),('P:FICTICIO-B','nao_localizado')):
            r=self.perguntar(pergunta,{'tipo':'PESSOA','valor':valor})
            self.assertEqual(r['status'],status)
            self.assertEqual(r['intencao']['entidade']['valor'],valor)

    def test_pix_ocorrencia_candidata_preserva_tipo_sem_confirmar_fato(self):
        with closing(sqlite3.connect(self.db_path)) as db:
            for rowid,localizador in db.execute("SELECT rowid,localizador FROM arestas WHERE b_tipo='CHAVE_PIX'").fetchall():
                meta=json.loads(localizador);meta['tipo']='extracao_candidata'
                db.execute('UPDATE arestas SET localizador=? WHERE rowid=?',(json.dumps(meta),rowid))
            db.commit()
        r=self.perguntar('Esta chave Pix aparece em quais O.S.?',{'tipo':'CHAVE_PIX','valor':'chave-ficticia'})
        self.assertEqual(r['status'],'ok')
        self.assertEqual({e['caso'] for a in r['grafo']['arestas'] for e in a['evidencias']},{self.caso,'OS-902-2099'})
        self.assertTrue(all(e['tipo']=='extracao_candidata' for a in r['grafo']['arestas'] for e in a['evidencias']))
        self.assertIn('não confirma', ' '.join(r['avisos']))

    def test_pix_tombstone_autoritativo_remove_cache_sem_apagar_documentais(self):
        import vinculos_manuais as VM
        r=self.post('/api/grafo/vinculo',self.payload(a_valor='ficticio|200',b_tipo='CHAVE_PIX',
                    b_valor='chave-ficticia',relacao='chave Pix vinculada (conforme autos)',observacao='Hipótese fictícia excluída'))
        self.assertEqual(r.status_code,200);manual=r.get_json()
        VM.excluir(self.ws,manual['id'],'operador_ficticio',versao=manual['versao'])
        antes=hashlib.sha256(self.db_path.read_bytes()).hexdigest()
        r=self.perguntar('Esta chave Pix aparece em quais O.S.?',{'tipo':'CHAVE_PIX','valor':'chave-ficticia'})
        fontes=[e for a in r['grafo']['arestas'] for e in a['evidencias']]
        self.assertEqual(len(fontes),2)
        self.assertTrue(all(e['tipo']=='documental' for e in fontes))
        self.assertEqual(hashlib.sha256(self.db_path.read_bytes()).hexdigest(),antes)

    def test_perguntas_contextuais_fontes_historico_e_limpeza_no_edge(self):
        self.browser(r'''
        const errors=[];page.on('pageerror',e=>errors.push(e.message));
        await page.goto(url+'/#grafo');await page.waitForLoadState('networkidle');
        assert.equal(await page.locator('#astra-pergunta').count(),1,'Campo Pergunte ao ASTRA disponível');
        await page.locator('#gr-caso').selectOption('OS-901-2099');await page.waitForFunction(()=>grEstado==='pronto');
        await page.evaluate(()=>grInspecionarNo(grNodes.find(n=>n.valor==='P:FICTICIO-A')));
        await page.locator('#astra-pergunta').fill('Quais contas receberam transferências documentadas desta pessoa?');
        const [r]=await Promise.all([page.waitForResponse(r=>r.url().endsWith('/api/astra/perguntar')),page.locator('#b-astra-perguntar').click()]);
        assert.equal(r.status(),200);await page.locator('#astra-respostas .astra-resposta').waitFor();
        assert.ok((await page.locator('#astra-respostas').innerText()).includes('transferiu R$ 10,00'));
        assert.ok(await page.locator('#astra-respostas a[href^="/arquivo/"]').count());
        const cargaAntes=await page.evaluate(()=>grCarga);
        await page.locator('#astra-respostas [data-astra-relacao]').first().click();
        assert.ok(await page.evaluate(antes=>grCarga>antes,cargaAntes),'O recorte explícito invalida consultas antigas');
        assert.ok(await page.locator('#gr-detalhes-conteudo .gr-evidencia').count());
        await page.locator('#gr-caso').selectOption('OS-902-2099');await page.waitForFunction(()=>grEstado==='pronto');
        assert.equal(await page.locator('#astra-respostas .astra-resposta').count(),0);
        await page.locator('#gr-caso').selectOption('OS-901-2099');await page.waitForFunction(()=>grEstado==='pronto');
        assert.equal(await page.locator('#astra-respostas .astra-resposta').count(),1);
        await page.locator('#b-astra-limpar').click();assert.equal(await page.locator('#astra-respostas .astra-resposta').count(),0);
        await page.locator('#astra-pergunta').fill('Quais contas receberam transferências da pessoa "Ana Fictícia"?');
        await page.locator('#b-astra-perguntar').click();await page.locator('[data-astra-opcao]').first().waitFor();
        assert.equal(await page.locator('[data-astra-opcao]').count(),2);
        await page.locator('[data-astra-opcao]').filter({hasText:'P:FICTICIO-A'}).click();
        await page.waitForFunction(()=>document.querySelectorAll('#astra-respostas .astra-resposta').length===2);
        assert.ok((await page.locator('#astra-respostas').innerText()).includes('transferiu R$ 10,00'));
        await page.reload();await page.waitForLoadState('networkidle');
        assert.equal(await page.locator('#astra-respostas .astra-resposta').count(),0);
        assert.deepEqual(errors,[]);
        ''')

    def test_erro_offline_pergunta_preservada_e_html_nao_executado(self):
        self.browser(r'''
        const errors=[];page.on('pageerror',e=>errors.push(e.message));
        await page.goto(url+'/#grafo');await page.waitForLoadState('networkidle');
        await page.locator('#gr-caso').selectOption('OS-901-2099');await page.waitForFunction(()=>grEstado==='pronto');
        await page.locator('#astra-pergunta').fill('Quais vínculos candidatos precisam de confirmação?');
        await page.route('**/api/astra/perguntar',r=>r.fulfill({status:503,contentType:'application/json',body:JSON.stringify({erro:'Índice fictício indisponível'})}));
        await page.locator('#b-astra-perguntar').click();await page.waitForFunction(()=>document.querySelector('#astra-pergunta-aviso').textContent.includes('indisponível'));
        assert.equal(await page.locator('#astra-pergunta').inputValue(),'Quais vínculos candidatos precisam de confirmação?');
        await page.unroute('**/api/astra/perguntar');await context.setOffline(true);
        await page.locator('#b-astra-perguntar').click();await page.waitForFunction(()=>!document.querySelector('#b-astra-perguntar').disabled);
        assert.ok((await page.locator('#astra-pergunta-aviso').innerText()).length);
        await context.setOffline(false);await page.locator('#astra-pergunta').fill('<img src=x onerror=alert(1)> invente fatos');
        await page.locator('#b-astra-perguntar').click();await page.locator('#astra-respostas .astra-resposta').waitFor();
        assert.equal(await page.locator('#astra-respostas img').count(),0);
        assert.deepEqual(errors,[]);
        ''')

    def test_consulta_pix_entre_os_nao_rotula_grafo_global_como_caso_unico(self):
        self.browser(r'''
        await page.goto(url+'/#casos');await page.waitForLoadState('networkidle');
        await page.evaluate(()=>abrirCaso('OS-901-2099'));
        await page.locator('#b-explorar-astra').click();await page.waitForFunction(()=>grEstado==='pronto');
        await page.evaluate(()=>grInspecionarNo(grNodes.find(n=>n.tipo==='CHAVE_PIX'&&n.valor==='chave-ficticia')));
        await page.locator('#astra-pergunta').fill('Esta chave Pix aparece em quais O.S.?');
        await page.locator('#b-astra-perguntar').click();await page.locator('#astra-respostas [data-astra-relacao]').first().waitFor();
        await page.locator('#astra-respostas [data-astra-relacao]').first().click();
        assert.equal(await page.locator('#gr-caso').inputValue(),'');
        assert.deepEqual(await page.evaluate(()=>[...new Set(grDados.arestas.flatMap(a=>a.evidencias.map(e=>e.caso)))].sort()),['OS-901-2099','OS-902-2099']);
        assert.equal(await page.evaluate(()=>grDados.proxima_pagina),null);
        await page.locator('#b-astra-voltar-caso').click();
        await page.locator('#astra-material-resumo').waitFor();
        assert.match(await page.locator('#astra-material-resumo').innerText(),/Contagens.*ainda não consultad/i);
        ''')


if __name__=='__main__':unittest.main(verbosity=2)
