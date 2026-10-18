"""AST110: revisão humana rastreável, somente fontes/workspaces fictícios."""
from contextlib import closing
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import patch
from astra_fixture import AstraFixture

ROOT=Path(__file__).resolve().parents[4]
BASE=ROOT/'plugin/investigacao-cpj/skills/base-cpj/scripts'
URL='/api/grafo/evidencia/revisar'
HIST='/api/grafo/evidencia/historico'
CG_CAMPOS=('caso','a_tipo','a_valor','b_tipo','b_valor','relacao','evidencia_id')


class Revisoes(AstraFixture,unittest.TestCase):
    def fonte(self,**extra):
        p=self.ws/'casos'/self.caso/'01-extracao/fonte-ficticia.md'
        p.write_text('FONTE FICTÍCIA SEM CONCLUSÃO DE AUTORIA',encoding='utf-8')
        meta={'schema':'astra-evidencia/1','caso':self.caso,'tipo':'extracao_candidata',
              'documento':'fonte-ficticia.pdf','arquivo_derivado':str(p.relative_to(self.ws)).replace('\\','/'),
              'pagina':7,'fls':'12v','trecho':'TRECHO FICTÍCIO LITERAL','localizador_original':'pág. 7; fls. 12v',**extra}
        linha=('PESSOA','P:FICTICIO-REVISAR','NOME','homonimo ficticio',self._testMethodName,'caso',self.caso,json.dumps(meta,ensure_ascii=False))
        with closing(sqlite3.connect(self.db_path)) as db:
            db.execute('INSERT INTO arestas VALUES(?,?,?,?,?,?,?,?)',linha);db.commit()
        g=self.client.get('/api/grafo',query_string={'caso':self.caso}).get_json()
        grupo=next(a for a in g['arestas'] if a['relacao']==self._testMethodName)
        return {k:grupo[k] for k in ('a_tipo','a_valor','b_tipo','b_valor','relacao')} | {'caso':self.caso,'evidencia_id':grupo['evidencias'][0]['id']}

    def revisar(self,alvo,acao='conferir_fonte',versao=0,**extra):
        if acao=='conferir_fonte':extra={'fonte':'derivado',**extra}
        return self.post(URL,{**alvo,'acao':acao,'versao':versao,**extra})

    def test_caso_com_ponto_revisao_overlay_historico_cas_e_limites_de_caminho(self):
        import conferencias_grafo as cg
        anterior=self.caso
        self.addCleanup(setattr,self,'caso',anterior)
        self.caso='OS.901-2099'
        pasta=self.ws/'casos'/self.caso
        shutil.copytree(self.ws/'casos'/anterior,pasta)
        documento=pasta/'caso.json'
        dados=json.loads(documento.read_text(encoding='utf-8'));dados['id']=self.caso
        documento.write_text(json.dumps(dados),encoding='utf-8')
        self.assertEqual(self.client.get('/api/casos/'+self.caso).status_code,200)
        alvo=self.fonte()
        self.assertEqual(self.client.get('/api/grafo',query_string={'caso':self.caso}).status_code,200)
        r=self.revisar(alvo)
        self.assertEqual(r.status_code,200,r.get_json())
        revisao=r.get_json()['revisao']
        self.assertEqual(revisao['versao'],1);self.assertTrue(revisao['id'].startswith('rev-'))
        self.assertEqual(revisao['recurso_conferido'],'derivado')
        g=self.client.get('/api/grafo',query_string={'caso':self.caso})
        self.assertEqual(g.status_code,200,g.get_json())
        fonte=next(a for a in g.get_json()['arestas'] if a['relacao']==self._testMethodName)['evidencias'][0]
        self.assertEqual(fonte['revisao'],revisao)
        self.assertEqual((fonte['tipo'],fonte['caso']),('extracao_candidata',self.caso))
        self.assertEqual(self.revisar(alvo,'marcar_candidato',0).status_code,409)
        r=self.revisar(alvo,'marcar_candidato',1)
        self.assertEqual(r.status_code,200,r.get_json())
        h=self.client.get(HIST,query_string=alvo)
        self.assertEqual(h.status_code,200,h.get_json())
        self.assertTrue(h.get_json()['referencia_atual'])
        self.assertEqual([e['versao'] for e in h.get_json()['historico']],[1,2])
        self.assertTrue(h.get_json()['revisao']['candidato'])
        self.assertTrue(all(e['alvo']['caso']==self.caso for e in h.get_json()['historico']))
        antes=cg.exportar(self.ws)
        for invalido in ('.','..','../OS-901-2099','OS-901-2099/../OS-902-2099',
                         'OS-901-2099\\..\\OS-902-2099','/OS-901-2099','\\OS-901-2099',
                         'OS-901-2099/','OS-901-2099\\','%2e%2e','OS-901%2F..'):
            with self.subTest(caso=invalido):
                adulterado={**alvo,'caso':invalido}
                with self.assertRaises(ValueError):cg.alvo(adulterado)
                self.assertEqual(self.revisar(adulterado,'marcar_candidato',2).status_code,400)
                self.assertEqual(self.client.get(HIST,query_string=adulterado).status_code,400)
        ausente={**alvo,'caso':'OS.AUSENTE-2099'}
        self.assertEqual(self.revisar(ausente,'marcar_candidato',2).status_code,404)
        self.assertEqual(self.client.get(HIST,query_string=ausente).status_code,404)
        self.assertEqual(cg.exportar(self.ws),antes)

    def test_conferir_candidato_observacao_historico_e_reabertura_sem_promocao(self):
        alvo=self.fonte();r=self.revisar(alvo)
        self.assertEqual(r.status_code,200,r.get_json())
        revisao=r.get_json()['revisao'];self.assertEqual(revisao['versao'],1)
        self.assertEqual(revisao['usuario'],'astra_ficticio');self.assertTrue(revisao['data'])
        self.assertTrue(revisao['fonte_conferida'])
        self.assertEqual(revisao['recurso_conferido'],'derivado')
        r=self.revisar(alvo,'marcar_candidato',1);self.assertEqual(r.status_code,200,r.get_json())
        texto='<img src=x onerror=alert(1)> HIPÓTESE FICTÍCIA'
        r=self.revisar(alvo,'registrar_observacao',2,observacao=texto);self.assertEqual(r.status_code,200,r.get_json())
        self.assertEqual(r.get_json()['revisao']['observacao'],texto)
        h=self.client.get(HIST,query_string=alvo);self.assertEqual(h.status_code,200,h.get_json())
        self.assertEqual([e['acao'] for e in h.get_json()['historico']],['conferir_fonte','marcar_candidato','registrar_observacao'])
        self.assertTrue(h.get_json()['revisao']['candidato'])
        self.client=self.s.app.test_client();self.setUp()
        g=self.client.get('/api/grafo',query_string={'caso':self.caso}).get_json()
        e=next(a for a in g['arestas'] if a['relacao']==self._testMethodName)['evidencias'][0]
        self.assertEqual((e['tipo'],e['origem'],e['trecho']),('extracao_candidata','caso','TRECHO FICTÍCIO LITERAL'))
        self.assertEqual(e['revisao']['versao'],3);self.assertEqual(e['revisao']['observacao'],texto)
        self.assertEqual(e['revisao']['fonte_usuario'],'astra_ficticio')
        self.assertEqual(e['revisao']['fonte_data'],revisao['data'])

    def test_cas_retry_perfil_csrf_caso_e_payload_sem_escrita_indevida(self):
        alvo=self.fonte();self.assertEqual(self.revisar(alvo).status_code,200)
        self.assertEqual(self.revisar(alvo).status_code,409)
        self.assertEqual(self.revisar({**alvo,'caso':'OS-902-2099'}).status_code,404)
        self.assertEqual(self.revisar({**alvo,'relacao':'outra relação'}).status_code,404)
        self.assertEqual(self.revisar(alvo,'fato_comprovado',1).status_code,400)
        self.assertEqual(self.revisar(alvo,'registrar_observacao',True,observacao='x').status_code,400)
        self.assertEqual(self.revisar(alvo,usuario='admin_falso').status_code,400)
        self.assertEqual(self.client.post(URL,json={**alvo,'acao':'marcar_candidato','versao':1}).status_code,403)
        self.post('/api/sair',{});self.post('/api/entrar',{'login':'leitor_ficticio','senha':'Ficticia123'})
        self.assertEqual(self.revisar(alvo,'marcar_candidato',1).status_code,403)
        self.assertEqual(self.client.get(HIST,query_string=alvo).status_code,200)

    def test_fonte_ausente_permite_observacao_mas_nao_declarar_conferida(self):
        alvo=self.fonte(arquivo_derivado=None,arquivo_original=None)
        self.assertEqual(self.revisar(alvo).status_code,409)
        r=self.revisar(alvo,'registrar_observacao',observacao='FONTE AUSENTE, CONFERÊNCIA PENDENTE')
        self.assertEqual(r.status_code,200,r.get_json())
        self.assertFalse(r.get_json()['revisao']['fonte_conferida'])

    def test_tres_fontes_independentes_recurso_explicito_e_lookup_fora_do_corte_visual(self):
        alvo=self.fonte();self.fonte(documento='segunda-fonte.pdf');self.fonte(documento='terceira-fonte.pdf')
        self.assertEqual(self.revisar(alvo,fonte='original').status_code,409)
        with closing(sqlite3.connect(self.db_path)) as db:
            db.executemany('INSERT INTO arestas VALUES(?,?,?,?,?,?,?,?)',
                [('CONTA',f'antecede|{n}','CONTA','outro|1','lote fictício','caso',self.caso,'fonte ausente') for n in range(405)]);db.commit()
        g=self.client.get('/api/grafo',query_string={'caso':self.caso}).get_json()
        self.assertTrue(g['truncado']);self.assertNotIn(self._testMethodName,{a['relacao'] for a in g['arestas']})
        r=self.revisar(alvo);self.assertEqual(r.status_code,200,r.get_json())
        self.assertEqual(r.get_json()['revisao']['recurso_conferido'],'derivado')
        with closing(sqlite3.connect(self.db_path)) as db:
            db.execute("DELETE FROM arestas WHERE relacao='lote fictício'");db.commit()
        g=self.client.get('/api/grafo',query_string={'caso':self.caso}).get_json()
        es=next(a for a in g['arestas'] if a['relacao']==self._testMethodName)['evidencias']
        self.assertEqual(len(es),3);self.assertEqual(sum(e['revisao']['fonte_conferida'] for e in es),1)

    def test_manual_editada_ou_excluida_nao_recebe_conferencia_antiga_mas_preserva_historico(self):
        import vinculos_manuais as vm
        criado=self.post('/api/grafo/vinculo',self.payload(relacao=self._testMethodName)).get_json()
        g=self.client.get('/api/grafo',query_string={'caso':self.caso}).get_json()
        grupo=next(a for a in g['arestas'] if a['relacao']==self._testMethodName)
        alvo={k:grupo[k] for k in CG_CAMPOS if k not in ('caso','evidencia_id')}|{'caso':self.caso,'evidencia_id':grupo['evidencias'][0]['id']}
        self.assertEqual(self.revisar(alvo,'registrar_observacao',observacao='Hipótese antiga fictícia').status_code,200)
        vm.atualizar(self.ws,criado['id'],{'evidencia':{'observacao':'Texto manual alterado'}},'ficticio',1)
        self.assertEqual(self.revisar(alvo,'marcar_candidato',1).status_code,409)
        h=self.client.get(HIST,query_string=alvo);self.assertEqual(h.status_code,200,h.get_json())
        self.assertFalse(h.get_json()['referencia_atual']);self.assertEqual(len(h.get_json()['historico']),1)
        g=self.client.get('/api/grafo',query_string={'caso':self.caso}).get_json()
        e=next(a for a in g['arestas'] if a['relacao']==self._testMethodName)['evidencias'][0]
        self.assertEqual(e['revisao']['versao'],0);self.assertEqual(e['observacao'],'Texto manual alterado')
        vm.excluir(self.ws,criado['id'],'ficticio',2)
        self.assertEqual(self.revisar(alvo,'marcar_candidato',1).status_code,409)

    def test_historico_corrompido_bloqueia_get_post_sem_parecer_nao_conferido(self):
        from rotas import consulta as rota
        alvo=self.fonte();self.assertEqual(self.revisar(alvo).status_code,200)
        pasta=self.ws/'consulta/_grafo-manual/conferencias'
        arquivo=next(p for p in pasta.glob('*.json') if json.loads(p.read_bytes())['alvo']==alvo)
        antes=arquivo.read_bytes();evento=json.loads(antes);evento['revisao']['fonte_conferida']=False
        arquivo.write_text(json.dumps(evento),encoding='utf-8')
        try:
            self.assertEqual(self.client.get('/api/grafo',query_string={'caso':self.caso}).status_code,503)
            self.assertEqual(self.client.get('/api/vinculos',query_string={'tipo':'PESSOA','valor':alvo['a_valor']}).status_code,503)
            with patch.object(rota.R,'conectar',side_effect=FileNotFoundError('índice indisponível fictício')):
                self.assertEqual(self.client.get('/api/grafo',query_string={'caso':self.caso}).status_code,503)
            self.assertEqual(self.revisar(alvo,'marcar_candidato',1).status_code,503)
            self.assertEqual(self.client.get(HIST,query_string=alvo).status_code,503)
        finally:arquivo.write_bytes(antes)

    def test_documental_alterada_exige_referencia_atual_e_historico_continua_acessivel(self):
        alvo=self.fonte();self.assertEqual(self.revisar(alvo).status_code,200)
        with closing(sqlite3.connect(self.db_path)) as db:
            loc=db.execute('SELECT localizador FROM arestas WHERE relacao=?',(self._testMethodName,)).fetchone()[0]
            meta=json.loads(loc);meta['trecho']='TRECHO FICTÍCIO CORRIGIDO'
            db.execute('UPDATE arestas SET localizador=? WHERE relacao=?',(json.dumps(meta),self._testMethodName));db.commit()
        self.assertEqual(self.revisar(alvo,'registrar_observacao',1,observacao='Não deve revisar referência anterior').status_code,409)
        h=self.client.get(HIST,query_string=alvo);self.assertEqual(h.status_code,200,h.get_json())
        self.assertFalse(h.get_json()['referencia_atual'])
        g=self.client.get('/api/grafo',query_string={'caso':self.caso}).get_json()
        e=next(a for a in g['arestas'] if a['relacao']==self._testMethodName)['evidencias'][0]
        self.assertEqual(e['revisao']['versao'],0);self.assertNotEqual(e['id'],alvo['evidencia_id'])


class Persistencia(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='cpj-conferencias-')
        self.addCleanup(self.temp.cleanup);self.ws=Path(self.temp.name)
        sys.path.insert(0,str(BASE));sys.path.insert(0,str(ROOT/'plugin/investigacao-cpj/app'))

    def dados(self):
        import conferencias_grafo as cg
        alvo={'caso':'OS-999-2099','a_tipo':'CONTA','a_valor':'ficticio|1','b_tipo':'CONTA','b_valor':'ficticio|2',
              'relacao':'relação fictícia','evidencia_id':'ev-'+'a'*64}
        ref={'id':alvo['evidencia_id'],'caso':alvo['caso'],'tipo':'extracao_candidata','origem':'caso',
             'original_disponivel':False,'derivado_disponivel':True,'documento':'Fonte fictícia','trecho':'FONTE LITERAL'}
        return cg,alvo,ref

    def test_modulo_independente_e_leitura_ausente_sem_criar_pastas(self):
        sys.path.insert(0,str(BASE))
        self.assertIsNotNone(importlib.util.find_spec('conferencias_grafo'))
        import conferencias_grafo as cg
        with tempfile.TemporaryDirectory(prefix='cpj-conferencias-') as ws:
            antes=list(Path(ws).rglob('*'))
            self.assertEqual(cg.listar(ws),{})
            self.assertEqual(cg.exportar(ws),{})
            self.assertEqual(list(Path(ws).rglob('*')),antes)

    def test_eventos_cas_atomicos_historico_preserva_autor_da_conferencia(self):
        cg,a,ref=self.dados()
        um=cg.revisar(self.ws,a,lambda _:ref,'conferir_fonte','autor_ficticio',0,recurso='derivado')
        antes=cg.exportar(self.ws)
        dois=cg.revisar(self.ws,a,lambda _:ref,'registrar_observacao','outro_ficticio',1,'Observação inicial')
        self.assertEqual((dois['fonte_usuario'],dois['fonte_data']),('autor_ficticio',um['data']))
        self.assertEqual(dois['usuario'],'outro_ficticio')
        for nome,conteudo in antes.items():self.assertEqual(cg.exportar(self.ws)[nome],conteudo)
        with self.assertRaises(cg.Conflito):cg.revisar(self.ws,a,lambda _:ref,'marcar_candidato','terceiro',1)
        with patch.object(cg.VM.os,'replace',side_effect=OSError('falha fictícia')):
            with self.assertRaises(OSError):cg.revisar(self.ws,a,lambda _:ref,'registrar_observacao','terceiro',2,'Observação editada')
        self.assertEqual(len(cg.historico(self.ws,a)),2)
        cg.revisar(self.ws,a,lambda _:ref,'registrar_observacao','terceiro',2,'Observação editada')
        self.assertEqual([e['observacao'] for e in cg.historico(self.ws,a)],['','Observação inicial','Observação editada'])

    def tarefas(self,ws):
        from tarefas import Tarefas
        return Tarefas(str(ws),None,None,iniciar_agente=False)

    def test_pacotes_dados_completo_importacao_repetida_e_chain_invalida_fail_closed(self):
        cg,a,ref=self.dados()
        cg.revisar(self.ws,a,lambda _:ref,'conferir_fonte','ficticio',0,recurso='derivado')
        cg.revisar(self.ws,a,lambda _:ref,'registrar_observacao','ficticio',1,'Observação fictícia')
        for pasta in ('casos','modelos'):(self.ws/pasta).mkdir()
        tarefa=self.tarefas(self.ws)
        for modo in ('dados','completo'):
            tid=tarefa.nova('exportacao','Fictícia','teste')
            pacote=self.ws/'exportacoes'/tarefa.exportar(tid,modo,False)['arquivo']
            with zipfile.ZipFile(pacote) as z:
                self.assertEqual(len([n for n in z.namelist() if n.startswith('dados/consulta/_grafo-manual/conferencias/')]),2)
                self.assertFalse(any(n.endswith('.lock') for n in z.namelist()))
            destino=self.ws/('importado-'+modo);destino.mkdir()
            importador=self.tarefas(destino)
            for n in range(2):
                entrada=destino/f'entrada-{n}.zip';shutil.copy2(pacote,entrada)
                itid=importador.nova('importacao','Fictícia','teste');importador.importar(itid,str(entrada))
            self.assertEqual(cg.exportar(destino),cg.exportar(self.ws))
        import vinculos_manuais as vm
        eventos=cg.exportar(self.ws);incompleto={nome:b for nome,b in eventos.items() if json.loads(b)['versao']==2}
        destino=self.ws/'invalido'
        with self.assertRaises(ValueError):vm.importar_eventos(destino,{},conferencias=incompleto)
        self.assertEqual(cg.listar(destino),{})

    def test_backup_restauracao_preserva_conferencias_sem_indice(self):
        cg,a,ref=self.dados();cg.revisar(self.ws,a,lambda _:ref,'marcar_candidato','ficticio',0)
        antes=cg.exportar(self.ws)
        for nome in ('casos','modelos','calibracao','producao','referencias','config','usuarios','ferramentas'):(self.ws/nome).mkdir(exist_ok=True)
        for nome in ('backup.ps1','restaurar.ps1'):shutil.copy2(ROOT/'ferramentas'/nome,self.ws/'ferramentas'/nome)
        backup=self.ws/'destino-backup';backup.mkdir()
        r=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(self.ws/'ferramentas/backup.ps1'),'-Destino',str(backup)],capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        # Remove exclusivamente o subconjunto fictício que será recuperado pelo backup real.
        pasta=(self.ws/'consulta').resolve();self.assertTrue(pasta.is_relative_to(self.ws.resolve()))
        shutil.rmtree(pasta)
        r=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(self.ws/'ferramentas/restaurar.ps1'),'-Origem',str(backup/'CPJ-TRABALHO-backup')],capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        self.assertEqual(cg.exportar(self.ws),antes)
        self.assertFalse((self.ws/'rag/cpj.sqlite').exists())

    def test_cas_entre_processos_e_reinicio_nao_perdem_revisao(self):
        cg,a,ref=self.dados();cg.revisar(self.ws,a,lambda _:ref,'marcar_candidato','ficticio',0)
        script="""import json,sys;sys.path.insert(0,sys.argv[1]);import conferencias_grafo as c
a=json.loads(sys.argv[3]);r=json.loads(sys.argv[4])
try:c.revisar(sys.argv[2],a,lambda _:r,'registrar_observacao',sys.argv[5],1,sys.argv[5])
except c.Conflito:sys.exit(7)
"""
        procs=[subprocess.Popen([sys.executable,'-B','-X','utf8','-c',script,str(BASE),str(self.ws),json.dumps(a),json.dumps(ref),usuario],stdout=subprocess.PIPE,stderr=subprocess.PIPE) for usuario in ('ator-a','ator-b')]
        codigos=[]
        for p in procs:
            saida,erro=p.communicate(timeout=45);codigos.append(p.returncode)
            self.assertIn(p.returncode,(0,7),saida+erro)
        self.assertEqual(sorted(codigos),[0,7]);self.assertEqual(len(cg.historico(self.ws,a)),2)
        script="import sys,json;sys.path.insert(0,sys.argv[1]);import conferencias_grafo as c;print(json.dumps(c.listar(sys.argv[2])))"
        r=subprocess.run([sys.executable,'-B','-X','utf8','-c',script,str(BASE),str(self.ws)],capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(json.loads(r.stdout),cg.listar(self.ws))

    def test_importacao_conflitante_nao_publica_manual_nem_caso_do_pacote(self):
        cg,a,ref=self.dados();cg.revisar(self.ws,a,lambda _:ref,'marcar_candidato','ficticio',0)
        (self.ws/'casos/OS-999-2099').mkdir(parents=True);(self.ws/'modelos').mkdir()
        (self.ws/'casos/OS-999-2099/caso.json').write_text(json.dumps({'id':'OS-999-2099','status':'recebido','ip':{},'datas':{}}),encoding='utf-8')
        tarefa=self.tarefas(self.ws);tid=tarefa.nova('exportacao','Fictícia','teste')
        pacote=self.ws/'exportacoes'/tarefa.exportar(tid,'dados',False)['arquivo']
        destino=self.ws/'destino-conflitante';destino.mkdir()
        eventos=cg.exportar(self.ws);nome,conteudo=next(iter(eventos.items()))
        divergente=json.loads(conteudo);divergente['usuario']='outro_ficticio';divergente['revisao']['usuario']='outro_ficticio'
        import vinculos_manuais as vm
        vm.importar_eventos(destino,{},conferencias={nome:(json.dumps(divergente)+'\n').encode('utf-8')})
        importador=self.tarefas(destino);tid=importador.nova('importacao','Fictícia','teste')
        entrada=destino/'entrada.zip';shutil.copy2(pacote,entrada)
        antes=cg.exportar(destino)
        with self.assertRaises(ValueError):importador.importar(tid,str(entrada))
        self.assertFalse((destino/'casos/OS-999-2099').exists())
        self.assertEqual(cg.exportar(destino),antes)

    def test_importacao_rejeita_estado_booleano_malformado_sem_publicar_evento(self):
        cg,a,ref=self.dados();cg.revisar(self.ws,a,lambda _:ref,'marcar_candidato','ficticio',0)
        nome,conteudo=next(iter(cg.exportar(self.ws).items()))
        e=json.loads(conteudo);e['revisao']['candidato']=1
        import vinculos_manuais as vm
        destino=self.ws/'invalido'
        with self.assertRaises(ValueError):vm.importar_eventos(destino,{},conferencias={nome:json.dumps(e).encode('utf-8')})
        self.assertEqual(cg.listar(destino),{})


if __name__=='__main__':unittest.main(verbosity=2)
