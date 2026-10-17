"""AST14: paginação/completude/SQL apenas sobre workspaces fictícios."""
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import unittest
from unittest.mock import patch
from astra_fixture import AstraFixture


class Paginacao(AstraFixture,unittest.TestCase):
    def setUp(self):
        super().setUp()
        with closing(sqlite3.connect(self.db_path)) as db:
            db.executescript('DELETE FROM arestas; DELETE FROM rotulos;')
        fonte=(self.ws/'consulta/_grafo-manual').resolve()
        self.assertTrue(fonte.is_relative_to(self.ws.resolve()))
        if fonte.exists():shutil.rmtree(fonte)

    def inserir(self,n=1,caso=None,origem='caso',inicio=0,fontes=2):
        caso=caso or self.caso
        with closing(sqlite3.connect(self.db_path)) as db:
            for i in range(inicio,inicio+n):
                for f in range(fontes):
                    meta={'schema':'astra-evidencia/1','caso':caso,'tipo':'documental',
                          'documento':f'fonte-ficticia-{f}.pdf','pagina':f+1,'localizador_original':f'linha fictícia {i}',
                          'registro_origem':{'linha':i+2,'seq':str(i)}}
                    db.execute('INSERT INTO arestas VALUES(?,?,?,?,?,?,?,?)',
                        ('CONTA',f'ficticio|{i:05}','CONTA','ficticio|destino','relação fictícia',origem,caso,json.dumps(meta)))
            db.commit()

    def grafo(self,**params):
        r=self.client.get('/api/grafo',query_string=params)
        self.assertEqual(r.status_code,200,r.get_json());return r.get_json()

    def test_total_logico_paginacao_ordenada_todas_fontes_e_pagina_vazia(self):
        self.inserir(405)
        paginas=[self.grafo(pagina=p,limite=200) for p in (1,2,3,4)]
        self.assertEqual([g['total'] for g in paginas],[405]*4)
        self.assertEqual([len(g['arestas']) for g in paginas],[200,200,5,0])
        self.assertEqual([g['proxima_pagina'] for g in paginas],[2,3,None,None])
        self.assertEqual([g['pagina'] for g in paginas],[1,2,3,4])
        chaves=[tuple(a[k] for k in ('a_tipo','a_valor','b_tipo','b_valor','relacao')) for g in paginas for a in g['arestas']]
        self.assertEqual(chaves,sorted(set(chaves)))
        self.assertTrue(all(a['total_evidencias']==2 for g in paginas for a in g['arestas']))
        self.assertTrue(all(g['truncado'] for g in paginas))

    def test_busca_todos_seeds_sem_corte_trinta_e_caso_restrito(self):
        with closing(sqlite3.connect(self.db_path)) as db:
            for c in (self.caso,'OS-902-2099'):
                for i in range(45):
                    p=f'P:FICTICIO-{c}-{i:03}'
                    for tipo,valor in (('NOME',f'ana ficticia {i:03}'),('CPF',f'{i:011}')):
                        db.execute('INSERT INTO arestas VALUES(?,?,?,?,?,?,?,?)',('PESSOA',p,tipo,valor,'dado fictício','caso',c,'pág. 1'))
            db.commit()
        g=self.grafo(q='Ána',limite=400);self.assertEqual(g['total'],180)
        self.assertEqual(len(g['arestas']),180);self.assertFalse(g['truncado'])
        g=self.grafo(q='Ána',caso=self.caso,limite=31);self.assertEqual(g['total'],90)
        self.assertEqual(len(g['arestas']),31);self.assertTrue(g['truncado'])
        self.assertTrue(all(e['caso']==self.caso for a in g['arestas'] for e in a['evidencias']))

    def test_pagina_e_limite_invalidos_sao400(self):
        for dados in ({'pagina':'0'},{'pagina':'-1'},{'pagina':'1.5'},{'limite':'0'},{'limite':'401'},
                      {'limite':'texto'},{'pagina':'true'},{'pagina':''}):
            with self.subTest(dados=dados):self.assertEqual(self.client.get('/api/grafo',query_string=dados).status_code,400)

    def test_cache_cadastro_por_stat_invalida_edicao_externa_adicao_remocao_sem_indice(self):
        from rotas import consulta as rota
        carregar=rota.C.carregar
        with patch.object(rota.C,'carregar',wraps=carregar) as spy:
            self.grafo();spy.reset_mock();self.grafo()
            self.assertEqual(spy.call_count,0,'GET repetido não deve reler todos os JSONs inalterados.')
            arquivo=self.ws/'casos'/self.caso/'caso.json';antes=arquivo.read_bytes()
            c=json.loads(antes);c['ordem_servico']='777/2099';arquivo.write_text(json.dumps(c),encoding='utf-8')
            try:
                g=self.grafo();self.assertEqual(spy.call_count,1)
                self.assertEqual(next(c['ordem_servico'] for c in g['ordens_servico'] if c['id']==self.caso),'777/2099')
            finally:arquivo.write_bytes(antes)
        novo=self.ws/'casos/OS-999-2099';novo.mkdir()
        (novo/'caso.json').write_text(json.dumps({'id':novo.name,'ordem_servico':'999/2099'}),encoding='utf-8')
        with patch.object(rota.R,'conectar',side_effect=FileNotFoundError('sem índice fictício')):
            self.assertIn(novo.name,self.grafo()['casos'])
            (novo/'caso.json').unlink();novo.rmdir()
            self.assertNotIn(novo.name,self.grafo()['casos'])

    def test_versao_entre_paginas_bloqueia_mistura_de_reindexacao(self):
        self.inserir(4)
        g=self.grafo(limite=2)
        r=self.client.get('/api/grafo',query_string={'pagina':2,'limite':2,'revisao':g['revisao']})
        self.assertEqual(r.status_code,200,r.get_json())
        self.inserir(1,inicio=20)
        r=self.client.get('/api/grafo',query_string={'pagina':2,'limite':2,'revisao':g['revisao']})
        self.assertEqual(r.status_code,409,r.get_json())

    def test_manuais_mesma_tupla_tombstone_e_revisao_fora_do_cache_com_contagem_exata(self):
        import vinculos_manuais as vm
        self.inserir(3)
        dados={'caso':self.caso,'a_tipo':'CONTA','a_valor':'ficticio|00000','b_tipo':'CONTA','b_valor':'ficticio|destino',
               'relacao':'relação fictícia','evidencia':{'documento':'manual-a.pdf'}}
        a=vm.criar(self.ws,dados,'autor_ficticio')
        b=vm.criar(self.ws,{**dados,'evidencia':{'documento':'manual-b.pdf'}},'autor_ficticio')
        vm.criar(self.ws,{**dados,'caso':'OS-902-2099'},'autor_ficticio')
        with closing(sqlite3.connect(self.db_path)) as db:
            db.execute('BEGIN IMMEDIATE');vm.projetar(self.ws,db);db.commit()
        vm.excluir(self.ws,a['id'],'autor_ficticio',1)
        for params in ({},{'q':'00000'},{'caso':self.caso}):
            g=self.grafo(**params)
            self.assertEqual(g['total'],3)
            e=next(x for x in g['arestas'] if x['a_valor']=='ficticio|00000')
            ids={r['manual_id'] for r in e['evidencias']}
            self.assertNotIn(a['id'],ids);self.assertIn(b['id'],ids)
            self.assertEqual(e['total_evidencias'],3 if params.get('caso') else 4)
        versao=self.grafo()['revisao']
        vm.atualizar(self.ws,b['id'],{'a_rotulo':'Nova anotação humana'},'autor_ficticio',1)
        self.assertEqual(self.client.get('/api/grafo',query_string={'pagina':2,'limite':1,'revisao':versao}).status_code,409)

    def test_sql_rotulos_em_lote_e_conexao_unica_sem_reconstruir_indice(self):
        from rotas import consulta as rota
        self.inserir(80)
        with closing(sqlite3.connect(self.db_path)) as db:
            db.executemany('INSERT INTO rotulos VALUES(?,?,?)',[('CONTA',f'ficticio|{i:05}',f'Conta fictícia {i}') for i in range(80)]);db.commit()
        conectar=rota.R.conectar;comandos=[]
        def conexao():
            db=conectar();db.set_trace_callback(comandos.append);return db
        antes=hashlib.sha256(self.db_path.read_bytes()).hexdigest()
        with patch.object(rota.R,'conectar',side_effect=conexao) as spy:
            g=self.grafo();self.assertEqual(spy.call_count,1)
        self.assertEqual(len(g['arestas']),80)
        self.assertLess(len(comandos),20,'Rótulos não devem exigir um SELECT por nó.')
        self.assertEqual(hashlib.sha256(self.db_path.read_bytes()).hexdigest(),antes)

    def test_indice_de_fonte_e_tupla_criado_somente_por_indexar(self):
        scripts=Path(__file__).resolve().parents[2]/'skills/base-cpj/scripts'
        r=subprocess.run([sys.executable,'-B','-X','utf8',str(scripts/'indexar.py')],env=dict(os.environ,CPJ_WORKSPACE=str(self.ws)),capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        with closing(sqlite3.connect(self.db_path)) as db:
            fonte=db.execute('EXPLAIN QUERY PLAN SELECT a_tipo,a_valor,b_tipo,b_valor,relacao FROM arestas WHERE fonte=?',(self.caso,)).fetchall()
            tupla=db.execute('EXPLAIN QUERY PLAN SELECT localizador FROM arestas WHERE a_tipo=? AND a_valor=? AND b_tipo=? AND b_valor=? AND relacao=?',('CONTA','a','CONTA','b','r')).fetchall()
        self.assertTrue(any('INDEX' in p[3] and 'fonte=?' in p[3] for p in fonte),fonte)
        self.assertTrue(any('INDEX' in p[3] and 'relacao=?' in p[3] for p in tupla),tupla)

    def test_rotulo_autoritativo_atualizado_e_excluido_nao_usa_cache_obsoleto(self):
        import vinculos_manuais as vm
        self.inserir()
        with closing(sqlite3.connect(self.db_path)) as db:
            db.execute('INSERT INTO rotulos VALUES(?,?,?)',('CONTA','ficticio|00000','Rótulo documental'));db.commit()
        dados={'caso':self.caso,'a_tipo':'CONTA','a_valor':'ficticio|00000','b_tipo':'CONTA','b_valor':'ficticio|destino',
               'relacao':'relação fictícia','a_rotulo':'Rotulo manual antigo','evidencia':{'documento':'manual.pdf'}}
        m=vm.criar(self.ws,dados,'ficticio')
        with closing(sqlite3.connect(self.db_path)) as db:
            db.execute('BEGIN IMMEDIATE');vm.projetar(self.ws,db);db.commit()
        vm.atualizar(self.ws,m['id'],{'a_rotulo':'Rotulo manual novo'},'ficticio',1)
        self.assertEqual(self.grafo(q='Rotulo manual novo')['total'],1)
        self.assertEqual(self.grafo(q='Rotulo manual antigo')['total'],0)
        vm.excluir(self.ws,m['id'],'ficticio',2)
        self.assertEqual(self.grafo(q='Rotulo manual antigo')['total'],0)
        g=self.grafo()
        self.assertEqual(next(n['rotulo'] for n in g['nos'] if n['valor']=='ficticio|00000'),'Rótulo documental')
        self.assertEqual(g['arestas'][0]['total_evidencias'],2)

    def test_sem_indice_pagina_manuais_mas_nao_afirma_total_documental(self):
        from rotas import consulta as rota
        import vinculos_manuais as vm
        for i in range(3):vm.criar(self.ws,{'caso':self.caso,'a_tipo':'CONTA','a_valor':f'ficticio|{i}',
            'b_tipo':'CONTA','b_valor':'ficticio|destino','relacao':'hipótese','evidencia':{'documento':'manual.pdf'}},'ficticio')
        with patch.object(rota.R,'conectar',side_effect=FileNotFoundError('índice ausente fictício')):
            g=self.grafo(limite=2)
            self.assertIsNone(g['total']);self.assertEqual(g['total_disponivel'],3)
            self.assertEqual(g['proxima_pagina'],2);self.assertTrue(g['truncado'])
            g=self.grafo(limite=2,pagina=2)
            self.assertEqual(len(g['arestas']),1);self.assertIsNone(g['proxima_pagina'])
            self.assertIsNone(g['total']);self.assertTrue(g['aviso']);self.assertFalse(g['indice_disponivel'])

    def test_versao_wal_sem_frames_nao_muda_por_leitura(self):
        with closing(sqlite3.connect(self.db_path)) as db:db.execute('PRAGMA journal_mode=WAL')
        self.inserir(4)
        antes=hashlib.sha256(self.db_path.read_bytes()).hexdigest()
        a=self.grafo(limite=2);b=self.grafo(limite=2,pagina=2,revisao=a['revisao'])
        self.assertEqual(a['revisao'],b['revisao'])
        self.assertEqual(hashlib.sha256(self.db_path.read_bytes()).hexdigest(),antes)

    def test_vinculos_paginados_nao_atravessam_nome_de_homonimo(self):
        with closing(sqlite3.connect(self.db_path)) as db:
            for pid,cpf in (('P:FICTICIO-A','11144477700'),('P:FICTICIO-B','22255588800')):
                for tipo,valor in (('NOME','homonimo ficticio'),('CPF',cpf)):
                    db.execute('INSERT INTO arestas VALUES(?,?,?,?,?,?,?,?)',('PESSOA',pid,tipo,valor,'dado cadastral','caso',self.caso,'fonte fictícia'))
            db.commit()
        es=[]
        for pagina in (1,2):
            r=self.client.get('/api/vinculos',query_string={'tipo':'PESSOA','valor':'P:FICTICIO-A','niveis':3,'pagina':pagina,'limite':1})
            self.assertEqual(r.status_code,200,r.get_json());g=r.get_json()
            self.assertEqual(g['total'],2);es+=g['arestas']
        self.assertEqual(len(es),2);self.assertTrue(all(a['a_valor']=='P:FICTICIO-A' for a in es))

    def test_escrita_concorrente_wal_durante_get_nao_retorna_completude_misturada(self):
        from rotas import consulta as rota
        with closing(sqlite3.connect(self.db_path)) as db:db.execute('PRAGMA journal_mode=WAL')
        self.inserir(2)
        consultar=rota.R.pagina_grafo
        def alterar_depois_da_consulta(*args,**kwargs):
            resultado=consultar(*args,**kwargs)
            self.inserir(1,inicio=99)
            return resultado
        with patch.object(rota.R,'pagina_grafo',side_effect=alterar_depois_da_consulta):
            r=self.client.get('/api/grafo')
        self.assertEqual(r.status_code,409,r.get_json())
        self.assertTrue(r.get_json()['recarregar'])
        self.assertEqual(self.grafo()['total'],3)

    def test_nivel_no_na_segunda_pagina_preserva_distancia_da_semente(self):
        with closing(sqlite3.connect(self.db_path)) as db:
            for a,b in (('ficticio|a','ficticio|b'),('ficticio|b','ficticio|c')):
                db.execute('INSERT INTO arestas VALUES(?,?,?,?,?,?,?,?)',('CONTA',a,'CONTA',b,'transferência fictícia','caso',self.caso,'pág. 1'))
            db.commit()
        r=self.client.get('/api/vinculos',query_string={'tipo':'CONTA','valor':'ficticio|a','limite':1,'pagina':2,'niveis':2})
        self.assertEqual(r.status_code,200,r.get_json())
        self.assertEqual({n['valor']:n['nivel'] for n in r.get_json()['nos']},{'ficticio|b':1,'ficticio|c':2})

    def test_busca_por_rotulo_documental_coexistente_com_rotulo_humano(self):
        import vinculos_manuais as vm
        self.inserir()
        with closing(sqlite3.connect(self.db_path)) as db:
            db.execute('INSERT INTO rotulos VALUES(?,?,?)',('CONTA','ficticio|00000','Semente documental'));db.commit()
        vm.criar(self.ws,{'caso':self.caso,'a_tipo':'CONTA','a_valor':'ficticio|00000','b_tipo':'CONTA',
            'b_valor':'ficticio|destino','relacao':'relação fictícia','a_rotulo':'Semente humana',
            'evidencia':{'documento':'anotação.pdf'}},'ficticio')
        for q in ('Semente documental','Semente humana'):
            g=self.grafo(q=q)
            self.assertEqual(g['total'],1)
            self.assertEqual(g['arestas'][0]['total_evidencias'],3)


if __name__=='__main__':unittest.main(verbosity=2)
