"""AST80: todas as evidências por relação, sem dados operacionais."""
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import unittest
from unittest.mock import patch
from astra_fixture import AstraFixture

BASE = Path(__file__).resolve().parents[2]/'skills/base-cpj/scripts'


class EvidenciasAPI(AstraFixture,unittest.TestCase):
    def metadado(self,documento,pagina=2,**extra):
        return {'schema':'astra-evidencia/1','localizador_original':f'{documento} pág. {pagina}',
                'origem':'caso','caso':self.caso,'documento':documento,
                'arquivo_original':f'casos/{self.caso}/00-originais/{documento}',
                'arquivo_derivado':f'casos/{self.caso}/02-analise/fluxo-financeiro.csv',
                'pagina':pagina,'paginas':[pagina] if pagina else None,'fls':None,
                'trecho':'TRECHO FICTÍCIO LITERAL','tipo':'documental','registro_origem':{'linha':4,'seq':'1'},
                'data_fato':'01/01/2099','sha256_original':'a'*64,'sha256_derivado':'b'*64,
                'extraido_em':None,'status_fonte':None,**extra}

    def inserir(self,metadado,relacao=None,origem='caso',fonte=None):
        linha=('CONTA','banco ficticio|001234','CONTA','banco ficticio|007890',
               relacao or self._testMethodName,origem,fonte or self.caso,
               json.dumps(metadado,ensure_ascii=False,sort_keys=True) if isinstance(metadado,dict) else metadado)
        with closing(sqlite3.connect(self.db_path)) as db:
            db.execute('INSERT INTO arestas VALUES(?,?,?,?,?,?,?,?)',linha);db.commit()
        return linha

    def grupo(self,url='/api/grafo',**params):
        r=self.client.get(url,query_string=params)
        self.assertEqual(r.status_code,200,r.get_json())
        grupos=[a for a in r.get_json()['arestas'] if a['relacao']==self._testMethodName]
        self.assertEqual(len(grupos),1,'Mesma relação deve aparecer uma vez com todas as fontes.')
        self.assertIn('evidencias',grupos[0],'Fontes adicionais não podem ser descartadas pelo agrupamento.')
        return grupos[0],r.get_json()

    def criar_original(self,nome):
        from reportlab.pdfgen import canvas
        p=self.ws/'casos'/self.caso/'00-originais'/nome
        cv=canvas.Canvas(str(p))
        for n in range(1,6):cv.drawString(50,800,f'PÁGINA FICTÍCIA {n}');cv.showPage()
        cv.save();return p

    def test_duas_fontes_geral_caso_e_q_com_ids_links_separados(self):
        for doc,pagina in (('fonte-a-ficticia.pdf',2),('fonte-b-ficticia.pdf',5)):
            self.criar_original(doc);self.inserir(self.metadado(doc,pagina))
        ids=None
        for params in ({},{'caso':self.caso},{'q':'001234'},{'caso':self.caso,'q':'001234'}):
            with self.subTest(params=params):
                g,_=self.grupo(**params)
                self.assertEqual(g['total_evidencias'],2)
                self.assertEqual({e['pagina'] for e in g['evidencias']},{2,5})
                self.assertEqual({e['fls'] for e in g['evidencias']},{None})
                self.assertEqual(len({e['url_original'] for e in g['evidencias']}),2)
                for e in g['evidencias']:
                    with self.client.get(e['url_original'].split('#')[0]) as resposta:
                        self.assertEqual(resposta.status_code,200)
                atuais={e['id'] for e in g['evidencias']}
                if ids is None:ids=atuais
                else:self.assertEqual(atuais,ids)

    def test_api_vinculos_expoe_todas_fontes_no_mesmo_grupo(self):
        self.inserir(self.metadado('vinculos-a.pdf',2));self.inserir(self.metadado('vinculos-b.pdf',5))
        g,_=self.grupo('/api/vinculos',tipo='CONTA',valor='banco ficticio|001234')
        self.assertEqual({e['documento'] for e in g['evidencias']},{'vinculos-a.pdf','vinculos-b.pdf'})

    def test_fontes_na_mesma_relacao_restritas_ao_caso(self):
        self.inserir(self.metadado('caso-a.pdf'))
        self.inserir(self.metadado('caso-b.pdf',caso='OS-902-2099',arquivo_original='casos/OS-902-2099/00-originais/caso-b.pdf'),fonte='OS-902-2099')
        for params in ({'caso':self.caso},{'caso':self.caso,'q':'001234'}):
            g,_=self.grupo(**params)
            self.assertEqual([e['caso'] for e in g['evidencias']],[self.caso])
            self.assertEqual([e['documento'] for e in g['evidencias']],['caso-a.pdf'])

    def test_origem_legada_desconhecida_preserva_caso_cadastrado_sem_promover_consulta(self):
        self.inserir('localizador legado sem documento',origem='autos')
        self.inserir('consulta não é peça dos autos',origem='consulta')
        for params in ({'caso':self.caso},{'caso':self.caso,'q':'001234'}):
            g,_=self.grupo(**params)
            self.assertEqual(g['total_evidencias'],1)
            e=g['evidencias'][0]
            self.assertEqual((e['caso'],e['origem'],e['tipo']),(self.caso,'autos','origem_desconhecida'))
            self.assertIsNone(e['documento']);self.assertIsNone(e['pagina']);self.assertIsNone(e['url_original'])
            self.assertIn('ORIGEM LEGADA NÃO CLASSIFICADA',e['avisos'])

    def manual(self,documento='manual-ficticio.pdf',**extra):
        import vinculos_manuais as vm
        dados={'a_tipo':'CONTA','a_valor':'banco ficticio|001234','b_tipo':'CONTA','b_valor':'banco ficticio|007890',
               'relacao':self._testMethodName,'caso':self.caso,'evidencia':{'documento':documento,'pagina':2,'fls':'8','observacao':'HIPÓTESE FICTÍCIA'}}
        dados.update(extra)
        return vm.criar(self.ws,dados,'operador_ficticio')

    def test_duas_manuais_mistas_conferencia_individual_e_exclusao_com_cache_pendente(self):
        import vinculos_manuais as vm
        self.inserir(self.metadado('documental.pdf'))
        a=self.manual('manual-a.pdf');b=self.manual('manual-b.pdf');self.manual('outra-os.pdf',caso='OS-902-2099')
        b=vm.atualizar(self.ws,b['id'],{'status':'conferido'},'revisor_ficticio',1)
        # Projeta as duas para provar que a remoção continua autoritativa com cache obsoleto.
        with closing(sqlite3.connect(self.db_path)) as db:
            db.execute('BEGIN IMMEDIATE');vm.projetar(self.ws,db);db.commit()
        for url,params in (('/api/grafo',{'caso':self.caso}),('/api/grafo',{'caso':self.caso,'q':'001234'}),
                           ('/api/vinculos',{'caso':self.caso,'tipo':'CONTA','valor':'banco ficticio|001234'})):
            g,_=self.grupo(url,**params)
            self.assertEqual(g['total_evidencias'],3);self.assertNotIn('id',g)
            ms={e['manual_id']:e for e in g['evidencias'] if e['manual_id']}
            self.assertEqual(set(ms),{a['id'],b['id']})
            self.assertEqual(ms[b['id']]['manual_versao'],2)
            self.assertEqual(ms[b['id']]['conferencia']['estado'],'conferida_pelo_operador')
            self.assertEqual(ms[a['id']]['conferencia']['estado'],'nao_conferida')
            self.assertEqual(ms[b['id']]['tipo'],'hipotese_manual')
        with patch.object(vm,'projetar',side_effect=sqlite3.OperationalError('cache fictício indisponível')):
            r=self.post('/api/grafo/vinculo/remover',{'id':a['id'],'caso':self.caso,'versao':1})
        self.assertEqual(r.status_code,200);self.assertTrue(r.get_json()['indexacao_pendente'])
        for url,params in (('/api/grafo',{'caso':self.caso}),('/api/vinculos',{'caso':self.caso,'tipo':'CONTA','valor':'banco ficticio|001234'})):
            g,_=self.grupo(url,**params)
            self.assertEqual(g['total_evidencias'],2);self.assertEqual(g['id'],b['id'])
            self.assertEqual(g['versao'],2)
            self.assertNotIn(a['id'],{e['manual_id'] for e in g['evidencias']})

    def test_q_expande_manual_sem_cache_por_rotulo_do_no(self):
        self.inserir(self.metadado('vizinho.pdf'),relacao='documental para semente fictícia')
        with closing(sqlite3.connect(self.db_path)) as db:
            db.execute('INSERT OR REPLACE INTO rotulos VALUES(?,?,?)',('CONTA','banco ficticio|001234','sementeespecialficticia'));db.commit()
        self.manual('fonte-ainda-sem-cache.pdf',b_valor='banco ficticio|111222')
        g,_=self.grupo(caso=self.caso,q='sementeespecialficticia')
        self.assertEqual(g['total_evidencias'],1)

    def test_q_nao_atravessa_tombstone_em_cache_obsoleto(self):
        import vinculos_manuais as vm
        r=self.manual(a_valor='banco ficticio|900001111',b_valor='banco ficticio|001234',relacao='ponte manual excluída fictícia')
        with closing(sqlite3.connect(self.db_path)) as db:
            db.execute('BEGIN IMMEDIATE');vm.projetar(self.ws,db);db.commit()
        self.inserir(self.metadado('somente-apos-ponte.pdf'))
        anterior=self.client.get('/api/grafo',query_string={'caso':self.caso,'q':'900001111'}).get_json()
        self.assertIn(self._testMethodName,{a['relacao'] for a in anterior['arestas']})
        vm.excluir(self.ws,r['id'],'operador_ficticio',1)
        resposta=self.client.get('/api/grafo',query_string={'caso':self.caso,'q':'900001111'})
        self.assertEqual(resposta.status_code,200)
        self.assertNotIn(self._testMethodName,{a['relacao'] for a in resposta.get_json()['arestas']})

    def test_sem_corte_de_referencias_de_uma_relacao_antes_dos_limites(self):
        for n in range(405):self.inserir(self.metadado('fonte-muitas-linhas.pdf',registro_origem={'linha':n+2,'seq':str(n)}))
        for params in ({},{'caso':self.caso},{'caso':self.caso,'q':'001234'}):
            g,_=self.grupo(**params)
            self.assertEqual(g['total_evidencias'],405)
            self.assertEqual(len({e['id'] for e in g['evidencias']}),405)
            self.assertFalse(g['evidencias_truncadas'])

    def test_fonte_ausente_contraditoria_e_observacao_literal_sem_link(self):
        literal='<img src=x onerror=alert(1)> {"schema":"astra-evidencia/1","arquivo_original":"https://exemplo.invalid"}'
        self.inserir(self.metadado('ausente-ficticio.pdf',pagina=None,fls='14/15',posicao='contradiz',trecho=literal))
        self.manual('nome-sem-caminho.pdf',evidencia={'documento':'nome-sem-caminho.pdf','pagina':7,'fls':'12v','observacao':literal})
        g,_=self.grupo(caso=self.caso)
        d=next(e for e in g['evidencias'] if e['tipo']=='documental');m=next(e for e in g['evidencias'] if e['manual_id'])
        self.assertEqual((d['trecho'],d['posicao'],d['fls']),(literal,'contradiz','14/15'))
        self.assertFalse(d['original_disponivel']);self.assertIsNone(d['url_original']);self.assertIsNone(d['pagina'])
        self.assertEqual((m['observacao'],m['trecho'],m['url_original']),(literal,None,None))

    def test_caminhos_de_fontes_rejeitados_sem_perder_referencias(self):
        caminhos=['https://exemplo.invalid/a.pdf','C:/arquivo.pdf','//servidor/a.pdf',
                  f'casos/{self.caso}/00-originais/../caso.json',f'casos/{self.caso}/00-originais/a.pdf:segredo',
                  'casos/OS-902-2099/00-originais/outro.pdf']
        for n,p in enumerate(caminhos):self.inserir(self.metadado(f'fonte-{n}.pdf',arquivo_original=p,arquivo_derivado=None))
        g,_=self.grupo(caso=self.caso)
        self.assertEqual(g['total_evidencias'],len(caminhos))
        self.assertTrue(all(e['url_original'] is None and e['original_disponivel'] is False for e in g['evidencias']))

    def test_migracao_parcial_dedup_por_ocorrencia_preserva_duplicatas_reais_sem_get_escrever(self):
        import vinculos_manuais as vm
        self.inserir('anotação legada duplicada fictícia',origem='manual')
        self.inserir('anotação legada duplicada fictícia',origem='manual')
        gravar=vm._gravar;gravadas=[]
        def falhar_segunda(pasta,evento):
            if evento['registro']['relacao']==self._testMethodName:
                if gravadas:raise OSError('interrupção fictícia após primeiro evento')
                gravadas.append(evento)
            return gravar(pasta,evento)
        with closing(sqlite3.connect(self.db_path)) as db:
            db.execute('BEGIN IMMEDIATE')
            with patch.object(vm,'_gravar',side_effect=falhar_segunda):
                with self.assertRaises(OSError):vm.migrar_legados(self.ws,db)
            db.rollback()
        def fonte():return {str(p.relative_to(self.ws)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (self.ws/'consulta/_grafo-manual').rglob('*.json')}
        antes=fonte()
        for params in ({'caso':self.caso},{'caso':self.caso,'q':'001234'}):
            g,_=self.grupo(**params)
            self.assertEqual(g['total_evidencias'],2)
            self.assertEqual(sum(bool(e['manual_id']) for e in g['evidencias']),1)
        self.assertEqual(fonte(),antes)
        with closing(sqlite3.connect(self.db_path)) as db:
            db.execute('BEGIN IMMEDIATE');vm.migrar_legados(self.ws,db);db.commit()
        registros=[r for r in vm.listar(self.ws) if r['relacao']==self._testMethodName]
        self.assertEqual(len(registros),2)
        vm.excluir(self.ws,registros[0]['id'],'operador_ficticio',1)
        g,_=self.grupo(caso=self.caso)
        self.assertEqual(g['total_evidencias'],1)

    def test_integracao_indexacao_dupla_preserva_ids_referencias_e_originais(self):
        pasta=self.ws/'casos'/self.caso
        for doc in ('index-a.pdf','index-b.pdf'):self.criar_original(doc)
        fluxo=pasta/'02-analise/fluxo-financeiro.csv'
        fluxo.write_text('seq;data;valor;meio;origem_banco;origem_ag_conta;destino_banco;destino_ag_conta;documento;fonte_pag;fls\n'
                         '1;01/01/2099;10,00;Pix;Banco Ficticio;001234;Banco Ficticio;007890;00-originais/index-a.pdf;2;10\n'
                         '2;01/01/2099;10,00;Pix;Banco Ficticio;001234;Banco Ficticio;007890;00-originais/index-b.pdf;5;11\n',encoding='utf-8')
        arquivos=[fluxo,*[pasta/'00-originais'/n for n in ('index-a.pdf','index-b.pdf')]]
        hashes={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in arquivos}
        antes=None
        for _ in range(2):
            r=subprocess.run([sys.executable,'-B','-X','utf8',str(BASE/'indexar.py')],env=dict(os.environ,CPJ_WORKSPACE=str(self.ws)),capture_output=True,text=True,encoding='utf-8',timeout=60)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            g=self.client.get('/api/grafo',query_string={'caso':self.caso,'q':'001234'}).get_json()
            relacoes=[a for a in g['arestas'] if a['relacao'].startswith('transferiu R$ 10,00')]
            self.assertEqual(len(relacoes),1)
            es=relacoes[0]['evidencias'];self.assertEqual(len(es),2)
            self.assertEqual({e['pagina'] for e in es},{2,5})
            self.assertEqual({e['fls'] for e in es},{'10','11'})
            self.assertTrue(all(e['url_original'] and e['url_derivado'] for e in es))
            ids={e['id'] for e in es}
            if antes is None:antes=ids
            else:self.assertEqual(ids,antes)
        self.assertEqual({p:hashlib.sha256(p.read_bytes()).hexdigest() for p in arquivos},hashes)

    def test_link_de_junction_nao_publica_documento_externo(self):
        import tempfile
        with tempfile.TemporaryDirectory(prefix='cpj-astra-fora-') as externo:
            Path(externo,'prova.pdf').write_bytes(b'PDF FICTICIO EXTERNO')
            link=self.ws/'casos'/self.caso/'00-originais/atalho-ficticio'
            r=subprocess.run(['cmd','/c','mklink','/J',str(link),externo],capture_output=True)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            try:
                self.inserir(self.metadado('prova.pdf',arquivo_original=f'casos/{self.caso}/00-originais/atalho-ficticio/prova.pdf',arquivo_derivado=None))
                g,_=self.grupo(caso=self.caso)
                self.assertIsNone(g['evidencias'][0]['url_original'])
                self.assertIn('ATALHO DE FONTE REJEITADO',g['evidencias'][0]['avisos'])
            finally:os.rmdir(link)

    def test_metadata_malformada_nao_quebra_leitura_nem_cria_link(self):
        self.inserir(self.metadado('tipo-invalido.pdf',caso={'id':self.caso},pagina=True,
                                  paginas=[True,-1,'2',3],arquivo_original=['fora.pdf'],arquivo_derivado=None))
        g,_=self.grupo()
        e=g['evidencias'][0]
        self.assertIsNone(e['caso']);self.assertIsNone(e['pagina']);self.assertEqual(e['paginas'],[3])
        self.assertIsNone(e['url_original'])

    def test_localizador_legado_preserva_fls_literal_sem_eleicao_de_pdf(self):
        loc=f'casos/{self.caso}/02-analise/pessoas.csv; págs. 12 | 45; fls. 7 verso / 8-A'
        self.inserir(loc)
        g,_=self.grupo(caso=self.caso)
        e=g['evidencias'][0]
        self.assertEqual(e['fls'],'7 verso / 8-A');self.assertEqual(e['paginas'],[12,45])
        self.assertIsNone(e['pagina']);self.assertIsNone(e['url_original'])
        self.assertEqual(e['localizador_original'],loc)

    def test_get_preserva_bytes_de_indice_eventos_e_arquivos_do_caso(self):
        self.inserir(self.metadado('leitura-ficticia.pdf'))
        self.criar_original('leitura-ficticia.pdf');self.manual('anotacao-leitura.pdf')
        def inventario():
            caminhos=[self.db_path,*list((self.ws/'casos').rglob('*')),*list((self.ws/'consulta/_grafo-manual').rglob('*'))]
            return {str(p.relative_to(self.ws)):(p.stat().st_mtime_ns,hashlib.sha256(p.read_bytes()).hexdigest()) for p in caminhos if p.is_file()}
        antes=inventario()
        for url,params in (('/api/grafo',{}),('/api/grafo',{'caso':self.caso}),('/api/grafo',{'caso':self.caso,'q':'001234'}),
                           ('/api/vinculos',{'caso':self.caso,'tipo':'CONTA','valor':'banco ficticio|001234'})):
            self.grupo(url,**params)
        self.assertEqual(inventario(),antes)

    def test_vinculos_sem_schema_grafo_preserva_manual_e_informa_incompletude(self):
        r=self.manual('fonte-sem-indice.pdf')
        with closing(sqlite3.connect(self.db_path)) as db:
            db.execute('ALTER TABLE arestas RENAME TO arestas_temporariamente_ausentes');db.commit()
        try:
            g,retorno=self.grupo('/api/vinculos',caso=self.caso,tipo='CONTA',valor='banco ficticio|001234')
            self.assertEqual(g['id'],r['id'])
            self.assertFalse(retorno['indice_disponivel']);self.assertIsNone(retorno['truncado'])
            self.assertEqual(retorno['completude'],'nao_aferida')
        finally:
            with closing(sqlite3.connect(self.db_path)) as db:
                db.execute('ALTER TABLE arestas_temporariamente_ausentes RENAME TO arestas');db.commit()

    def test_grafo_sem_indice_preserva_rotulos_manuais_e_filtro_de_busca(self):
        from rotas import consulta as rota
        self.manual('fonte-rotulos.pdf',a_rotulo='Rótulo humano fictício A',b_rotulo='Rótulo humano fictício B')
        self.manual('segunda-fonte-sem-rotulo.pdf')
        antes=hashlib.sha256(self.db_path.read_bytes()).hexdigest()
        with patch.object(rota.R,'conectar',side_effect=FileNotFoundError('índice fictício indisponível')):
            g,r=self.grupo(caso=self.caso)
            with self.subTest('rótulos preservados'):
                self.assertEqual({n['rotulo'] for n in r['nos']},{'Rótulo humano fictício A','Rótulo humano fictício B'})
            self.assertFalse(r['indice_disponivel']);self.assertIsNone(r['truncado'])
            self.assertIn(self.caso,r['casos']);self.assertTrue(r['aviso'])
            selecionada,_=self.grupo(caso=self.caso,q='Rótulo humano fictício A')
            self.assertEqual(selecionada['total_evidencias'],2)
            r=self.client.get('/api/grafo',query_string={'caso':self.caso,'q':'semqualquercorrespondenciaficticia'}).get_json()
            with self.subTest('busca sem correspondência'):
                self.assertEqual(r['arestas'],[]);self.assertEqual(r['nos'],[])
            self.assertFalse(r['indice_disponivel']);self.assertIsNone(r['truncado']);self.assertTrue(r['aviso'])
            self.assertIn(self.caso,r['casos'])
        self.assertEqual(hashlib.sha256(self.db_path.read_bytes()).hexdigest(),antes)

    def test_z_corte_relacoes_declarado_sem_cortar_evidencias_selecionadas(self):
        with closing(sqlite3.connect(self.db_path)) as db:
            db.executemany('INSERT INTO arestas VALUES(?,?,?,?,?,?,?,?)',
                [('CONTA',f'ficticio|limite{n}','CONTA','ficticio|destino',f'corte-{n}','caso',self.caso,json.dumps(self.metadado('limite.pdf'))) for n in range(405)])
            db.commit()
        r=self.client.get('/api/grafo',query_string={'caso':self.caso}).get_json()
        self.assertTrue(r['truncado']);self.assertEqual(r['completude'],'parcial')
        self.assertEqual(r['limites']['relacoes'],400)
        self.assertLessEqual(len(r['arestas']),400)
        self.assertTrue(all(not a['evidencias_truncadas'] for a in r['arestas']))


if __name__=='__main__':unittest.main(verbosity=2)
