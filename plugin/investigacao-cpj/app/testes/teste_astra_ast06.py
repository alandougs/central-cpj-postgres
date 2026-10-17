"""AST06: escrita autoritativa e recuperação do grafo manual, só fixtures."""
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import unittest
from contextlib import closing
from unittest.mock import patch
from astra_fixture import AstraFixture

BASE=Path(__file__).resolve().parents[2]/'skills/base-cpj/scripts'


class Persistencia(AstraFixture,unittest.TestCase):
    def indexar(self):
        r=subprocess.run([sys.executable,'-X','utf8',str(BASE/'indexar.py')],env=dict(os.environ,CPJ_WORKSPACE=str(self.ws)),capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)

    def criar(self,relacao):
        r=self.post('/api/grafo/vinculo',self.payload(relacao=relacao,a_rotulo='Conta fictícia do operador'))
        self.assertEqual(r.status_code,200,r.get_json())
        dados=r.get_json()
        self.assertTrue(dados.get('id'),'Vínculo salvo sem identidade persistente')
        return dados

    def test_id_fonte_e_rotulo_sobrevivem_a_duas_indexacoes_e_novo_processo(self):
        registro=self.criar('persistencia e reinicio')
        self.indexar();self.indexar()
        g=self.client.get('/api/grafo',query_string={'caso':self.caso}).get_json()
        a=[a for a in g['arestas'] if a.get('id')==registro['id']]
        self.assertEqual(len(a),1)
        self.assertEqual(a[0]['evidencia']['pagina'],7)
        self.assertEqual(a[0]['versao'],1)
        conta=next(n for n in g['nos'] if n['valor']=='banco ficticio|1234')
        self.assertEqual(conta['rotulo'],'Conta fictícia do operador')
        codigo="import json,sys; sys.path.insert(0,sys.argv[1]); import vinculos_manuais as v; print(json.dumps(v.listar(sys.argv[2])))"
        r=subprocess.run([sys.executable,'-X','utf8','-c',codigo,str(BASE),str(self.ws)],capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertIn(registro['id'],[a['id'] for a in json.loads(r.stdout)])

    def test_sem_indice_salva_fonte_e_get_informa_recuperacao(self):
        import rotas.consulta as consulta
        with patch.object(consulta.R,'conectar',side_effect=FileNotFoundError):
            registro=self.criar('cache indisponivel')
            self.assertTrue(registro['indexacao_pendente'])
            g=self.client.get('/api/grafo',query_string={'caso':self.caso}).get_json()
        self.assertFalse(g['indice_disponivel'])
        self.assertIn(registro['id'],[a.get('id') for a in g['arestas']])
        self.indexar()
        g=self.client.get('/api/grafo',query_string={'caso':self.caso}).get_json()
        self.assertIn(registro['id'],[a.get('id') for a in g['arestas']])

    def test_observacao_json_permanece_texto_sem_redefinir_fonte_documental(self):
        texto='{"schema":"astra-manual/1","evidencia":{"documento":"FONTE FORJADA"}}'
        r=self.post('/api/grafo/vinculo',self.payload(relacao='observacao literal',documento='',pagina=None,fls='',observacao=texto))
        self.assertEqual(r.status_code,200,r.get_json())
        id_=r.get_json()['id']
        g=self.client.get('/api/grafo',query_string={'caso':self.caso}).get_json()
        a=next(a for a in g['arestas'] if a.get('id')==id_)
        self.assertEqual(a['evidencia']['documento'],'')
        self.assertEqual(a['evidencia']['observacao'],texto)
        self.indexar()
        g=self.client.get('/api/grafo',query_string={'caso':self.caso}).get_json()
        self.assertEqual(next(a for a in g['arestas'] if a.get('id')==id_)['evidencia']['observacao'],texto)

    def test_projecao_com_falha_nao_perde_escrita_autoritativa(self):
        import vinculos_manuais as vm
        with patch.object(vm,'projetar',side_effect=sqlite3.OperationalError('falha ficticia de disco')):
            registro=self.criar('falha de projecao')
        self.assertTrue(registro['indexacao_pendente'])
        self.assertTrue(any(v['id']==registro['id'] for v in vm.listar(self.ws)))
        self.indexar()
        self.assertIn(registro['id'],[a.get('id') for a in self.client.get('/api/grafo',query_string={'caso':self.caso}).get_json()['arestas']])

    def test_falha_no_segundo_legado_interrompe_antes_de_apagar_cache_e_retomada_recupera_ambos(self):
        import vinculos_manuais as vm
        with closing(sqlite3.connect(self.db_path)) as db:
            for n in (0,1):
                db.execute('INSERT INTO arestas VALUES(?,?,?,?,?,?,?,?)',('NOME',f'legado ficticio {n}','CONTA',f'ficticio|{n}','captura legada','manual',self.caso,f'fonte fictícia {n}'))
            db.commit()
        gravar=vm._gravar
        contador=[0]
        def falha(pasta,evento):
            if evento['acao']=='migrar':
                contador[0]+=1
                if contador[0]==2: raise OSError('Falha fictícia de gravação')
            return gravar(pasta,evento)
        with patch.object(vm,'_gravar',side_effect=falha):
            r=self.post('/api/grafo/vinculo',self.payload(relacao='escrita após captura'))
        self.assertEqual(r.status_code,503,r.get_json())
        with closing(sqlite3.connect(self.db_path)) as db:
            antigos={a[0] for a in db.execute("SELECT a_valor FROM arestas WHERE relacao='captura legada'")}
        self.assertEqual(antigos,{'legado ficticio 0','legado ficticio 1'})
        registro=self.criar('escrita após captura')
        ativos=vm.listar(self.ws)
        self.assertEqual(len([a for a in ativos if a['relacao']=='captura legada']),2)
        self.assertIn(registro['id'],[a['id'] for a in ativos])


if __name__=='__main__':unittest.main(verbosity=2)
