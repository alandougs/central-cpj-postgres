"""AST70: exclusão por identidade manual, com API/índice/originais fictícios."""
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import unittest
import uuid
from unittest.mock import patch
from astra_fixture import AstraFixture

BASE = Path(__file__).resolve().parents[2] / 'skills/base-cpj/scripts'
URL = '/api/grafo/vinculo/remover'


class ExclusaoManual(AstraFixture, unittest.TestCase):
    def criar(self, **extra):
        payload = self.payload(**dict({'relacao':self._testMethodName}, **extra))
        resposta = self.post('/api/grafo/vinculo', payload)
        self.assertEqual(resposta.status_code, 200, resposta.get_json())
        return resposta.get_json()

    def remover(self, registro, **extra):
        return self.post(URL, {'id':registro['id'], 'caso':self.caso,
                               'versao':registro['versao'], **extra})

    def indexar(self):
        r = subprocess.run([sys.executable, '-X', 'utf8', str(BASE/'indexar.py')],
                           env=dict(os.environ, CPJ_WORKSPACE=str(self.ws)), capture_output=True,
                           text=True, encoding='utf-8')
        self.assertEqual(r.returncode, 0, r.stdout+r.stderr)

    def test_exclui_id_manual_com_tombstone_e_retorna_versao(self):
        import vinculos_manuais as vm
        registro = self.criar()
        resposta = self.remover(registro)
        self.assertEqual(resposta.status_code, 200, resposta.get_json())
        retorno = resposta.get_json()
        self.assertEqual((retorno['id'], retorno['versao']), (registro['id'], 2))
        self.assertFalse(retorno['indexacao_pendente'])
        self.assertNotIn(registro['id'], {r['id'] for r in vm.listar(self.ws)})
        estado = next(r for r in vm.listar(self.ws, incluir_excluidos=True) if r['id']==registro['id'])
        self.assertTrue(estado['excluido'])
        self.assertEqual([e['acao'] for e in vm.historico(self.ws, registro['id'])], ['criar','excluir'])

    def test_tupla_legada_nao_exclui_relacao_documental(self):
        linha = ('CONTA','banco ficticio|somente-leitura','CHAVE_PIX','ficticia',
                 'relação documental somente leitura','caso',self.caso,'fonte fictícia pág. 7')
        with closing(sqlite3.connect(self.db_path)) as db:
            db.execute('INSERT INTO arestas VALUES(?,?,?,?,?,?,?,?)', linha); db.commit()
        resposta = self.post(URL, dict(zip(('a_tipo','a_valor','b_tipo','b_valor','relacao'),linha[:5])))
        self.assertEqual(resposta.status_code, 400)
        with closing(sqlite3.connect(self.db_path)) as db:
            self.assertIn(linha, db.execute('SELECT * FROM arestas').fetchall())

    def test_csrf_perfil_e_sessao_nao_autorizam_exclusao(self):
        import vinculos_manuais as vm
        registro = self.criar()
        payload = {'id':registro['id'], 'caso':self.caso, 'versao':1}
        self.assertEqual(self.client.post(URL,json=payload).status_code, 403)
        self.post('/api/sair', {})
        self.assertEqual(self.post(URL,payload).status_code, 401)
        self.assertEqual(self.post('/api/entrar', {'login':'leitor_ficticio','senha':'Ficticia123'}).status_code, 200)
        self.assertEqual(self.post(URL,payload).status_code, 403)
        self.assertIn(registro['id'], {r['id'] for r in vm.listar(self.ws)})

    def test_retry_repetido_e_versao_antiga_nao_criam_novo_evento(self):
        import vinculos_manuais as vm
        registro = self.criar()
        self.assertEqual(self.remover(registro).status_code, 200)
        antes = vm.historico(self.ws,registro['id'])
        self.assertEqual(self.remover(registro).status_code, 409)
        self.assertEqual(self.remover(registro,versao=2).status_code, 409)
        self.assertEqual(vm.historico(self.ws,registro['id']), antes)

    def test_malformados_rejeitados_sem_criar_eventos(self):
        import vinculos_manuais as vm
        id_ = str(uuid.uuid4())
        antes = vm.listar(self.ws, incluir_excluidos=True)
        base = {'id':id_, 'caso':self.caso, 'versao':1}
        for payload in ([], ['id'], 'texto', None, {}, {'id':id_},
                        {**base,'versao':True}, {**base,'versao':'1'}, {**base,'versao':0},
                        {**base,'versao':-1}, {**base,'versao':None}, {**base,'id':{}},
                        {**base,'id':'nao-e-uuid'}, {**base,'caso':[]}, {**base,'caso':''},
                        {**base,'caso':'../OS-901-2099'}, {**base,'a_tipo':'CONTA'}):
            with self.subTest(payload=payload):
                resposta = self.post(URL,payload)
                self.assertEqual(resposta.status_code,400,resposta.get_json())
        self.assertEqual(self.client.post(URL,data='{',content_type='application/json',headers={'X-CPJ':'1'}).status_code,400)
        self.assertEqual(vm.listar(self.ws, incluir_excluidos=True),antes)

    def test_id_inexistente_automatico_ou_de_outro_caso_retorna404(self):
        import vinculos_manuais as vm
        registro = self.criar()
        automatico_id = str(uuid.uuid4())
        automatica = ('NOME','ficticio somente documental','CONTA','banco ficticio|999',
                      'documental sem exclusão','caso',self.caso,
                      json.dumps({'schema':'astra-manual/1','id':automatico_id,'versao':1,'evidencia':{'documento':'documental.pdf'}}))
        with closing(sqlite3.connect(self.db_path)) as db:
            db.execute('INSERT INTO arestas VALUES(?,?,?,?,?,?,?,?)',automatica); db.commit()
        for payload in ({'id':str(uuid.uuid4()),'caso':self.caso,'versao':1},
                        {'id':automatico_id,'caso':self.caso,'versao':1},
                        {'id':registro['id'],'caso':'OS-902-2099','versao':1},
                        {'id':registro['id'],'caso':'OS-999-2099','versao':1}):
            with self.subTest(payload=payload): self.assertEqual(self.post(URL,payload).status_code,404)
        self.assertIn(registro['id'],{r['id'] for r in vm.listar(self.ws)})
        with closing(sqlite3.connect(self.db_path)) as db:
            self.assertIn(automatica,db.execute('SELECT * FROM arestas').fetchall())

    def test_versao_alterada_exige_reabrir_antes_de_excluir(self):
        import vinculos_manuais as vm
        registro = self.criar()
        atualizado = vm.atualizar(self.ws,registro['id'],{'a_rotulo':'Anotação humana revisada'},'revisor_ficticio',versao=1)
        self.assertEqual(self.remover(registro).status_code,409)
        self.assertEqual(vm.historico(self.ws,registro['id'])[-1]['registro'],atualizado)
        self.assertEqual(self.remover(registro,versao=2).status_code,200)
        self.assertEqual(vm.historico(self.ws,registro['id'])[-1]['registro']['versao'],3)

    def test_versao_futura_nao_autoriza_excluir_se_registro_mudar_para_outra_os(self):
        import vinculos_manuais as vm
        registro = self.criar()
        listar_real = vm.listar
        def snapshot_antes_da_mudanca(ws, incluir_excluidos=False):
            resultado = listar_real(ws,incluir_excluidos=incluir_excluidos)
            vm.atualizar(ws,registro['id'],{'caso':'OS-902-2099'},'revisor_ficticio',versao=1)
            return resultado
        with patch.object(vm,'listar',side_effect=snapshot_antes_da_mudanca):
            resposta = self.remover(registro,versao=2)
        self.assertEqual(resposta.status_code,409,resposta.get_json())
        atual = next(r for r in vm.listar(self.ws,incluir_excluidos=True) if r['id']==registro['id'])
        self.assertEqual((atual['caso'],atual['versao'],atual['excluido']),('OS-902-2099',2,False))

    def test_mesma_tupla_preserva_documental_segundo_manual_e_outra_os_apos_reindexar_reiniciar(self):
        import vinculos_manuais as vm
        pasta = self.ws/'casos'/self.caso
        original = pasta/'00-originais/prova-ficticia.txt'
        original.write_bytes(b'CONTEUDO ORIGINAL FICTICIO - NAO ALTERAR')
        fluxo = pasta/'02-analise/fluxo-financeiro.csv'
        fluxo.write_text('seq;origem_banco;origem_ag_conta;origem_chave;fonte_pag\n1;Banco Ficticio;1234;chave-ficticia;7\n',encoding='utf-8')
        hashes = {p:hashlib.sha256(p.read_bytes()).hexdigest() for p in (original,fluxo)}
        self.indexar()
        relacao = 'chave Pix vinculada (conforme autos)'
        alvo = self.criar(relacao=relacao,documento='fonte-manual-alvo.pdf')
        segundo = self.criar(relacao=relacao,documento='outra-fonte-manual.pdf')
        outro_caso = self.criar(relacao=relacao,documento='fonte-manual-outra-os.pdf',caso='OS-902-2099')
        with closing(sqlite3.connect(self.db_path)) as db:
            documental = db.execute("SELECT * FROM arestas WHERE origem='caso' AND relacao=? AND fonte=?",(relacao,self.caso)).fetchall()
        self.assertEqual(len(documental),1,'Fixture deve conter uma relação documental realmente gerada do CSV.')
        self.assertEqual(documental[0][:5],('CONTA','banco ficticio|1234','CHAVE_PIX','chave-ficticia',relacao))
        self.assertEqual(self.remover(alvo).status_code,200)
        for _ in range(2): self.indexar()
        with closing(sqlite3.connect(self.db_path)) as db:
            self.assertIn(documental[0],db.execute('SELECT * FROM arestas').fetchall())
        codigo="import sys,json;sys.path.insert(0,sys.argv[1]);import vinculos_manuais as v;print(json.dumps(v.listar(sys.argv[2],incluir_excluidos=True)))"
        r=subprocess.run([sys.executable,'-X','utf8','-c',codigo,str(BASE),str(self.ws)],capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(r.returncode,0,r.stderr)
        estados={a['id']:a for a in json.loads(r.stdout)}
        self.assertTrue(estados[alvo['id']]['excluido'])
        self.assertFalse(estados[segundo['id']]['excluido'])
        self.assertFalse(estados[outro_caso['id']]['excluido'])
        self.assertEqual({p:hashlib.sha256(p.read_bytes()).hexdigest() for p in hashes},hashes)
        self.assertEqual(len(vm.historico(self.ws,alvo['id'])),2)

    def test_falha_cache_preserva_exclusao_e_get_nao_ressuscita(self):
        import vinculos_manuais as vm
        registro = self.criar()
        with patch.object(vm,'projetar',side_effect=sqlite3.OperationalError('falha fictícia de disco')):
            resposta = self.remover(registro)
        self.assertEqual(resposta.status_code,200,resposta.get_json())
        self.assertTrue(resposta.get_json()['indexacao_pendente'])
        with closing(sqlite3.connect(self.db_path)) as db:
            caches = [json.loads(r[0]).get('id') for r in db.execute("SELECT localizador FROM arestas WHERE origem='manual'")]
        self.assertIn(registro['id'],caches,'Cache obsoleto deve continuar para provar que o GET respeita o tombstone.')
        def grafo_ids():
            return {a.get('id') for a in self.client.get('/api/grafo',query_string={'caso':self.caso}).get_json()['arestas']}
        self.assertNotIn(registro['id'],grafo_ids())
        self.assertEqual(self.remover(registro).status_code,409)
        self.indexar(); self.assertNotIn(registro['id'],grafo_ids())
        self.assertEqual(len(vm.historico(self.ws,registro['id'])),2)

    def test_falha_fonte_nao_altera_cache_ou_historico(self):
        import vinculos_manuais as vm
        registro = self.criar()
        antes = vm.historico(self.ws,registro['id'])
        with closing(sqlite3.connect(self.db_path)) as db: arestas_antes = db.execute('SELECT * FROM arestas').fetchall()
        with patch.object(vm,'excluir',side_effect=OSError('falha fictícia na fonte')):
            resposta = self.remover(registro)
        self.assertEqual(resposta.status_code,503,resposta.get_json())
        self.assertEqual(vm.historico(self.ws,registro['id']),antes)
        with closing(sqlite3.connect(self.db_path)) as db: self.assertEqual(db.execute('SELECT * FROM arestas').fetchall(),arestas_antes)

    def test_get_nao_migra_legado_nem_escreve_fonte(self):
        import vinculos_manuais as vm
        legado = ('NOME','legado ficticio sem identidade','CONTA','ficticio|2',
                  'legado deve aguardar migração explícita','manual',self.caso,'fonte antiga fictícia')
        with closing(sqlite3.connect(self.db_path)) as db:
            db.execute('INSERT INTO arestas VALUES(?,?,?,?,?,?,?,?)',legado); db.commit()
        antes = vm.listar(self.ws,incluir_excluidos=True)
        self.assertEqual(self.client.get('/api/grafo',query_string={'caso':self.caso}).status_code,200)
        self.assertEqual(vm.listar(self.ws,incluir_excluidos=True),antes)

    def test_auditoria_exclusao_registra_id_e_caso_sem_identificadores_dos_extremos(self):
        registro = self.criar(a_valor='banco ficticio|segredo-do-caso-nao-logar')
        self.assertEqual(self.remover(registro).status_code,200)
        eventos=[json.loads(l) for l in (self.ws/'config/auditoria.log').read_text(encoding='utf-8').splitlines()]
        eventos=[e for e in eventos if e.get('acao')=='grafo_vinculo_removido']
        self.assertTrue(any(registro['id'] in str(e) and self.caso in str(e) for e in eventos))
        self.assertFalse(any('segredo-do-caso-nao-logar' in str(e) for e in eventos))


if __name__ == '__main__':
    unittest.main(verbosity=2)
