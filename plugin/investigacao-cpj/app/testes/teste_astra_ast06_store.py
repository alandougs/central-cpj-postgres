"""AST60: persistência local dos vínculos, exclusivamente em workspaces fictícios."""
import importlib.util
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[4]
SCRIPTS = ROOT / 'plugin/investigacao-cpj/skills/base-cpj/scripts'
APP = ROOT / 'plugin/investigacao-cpj/app'
sys.path.insert(0, str(SCRIPTS))


class Store(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='cpj-astra-store-')
        self.addCleanup(self.temp.cleanup)
        self.ws = Path(self.temp.name)
        (self.ws / 'casos').mkdir()
        (self.ws / 'modelos').mkdir()

    def modulo(self):
        self.assertIsNotNone(importlib.util.find_spec('vinculos_manuais'),
                             'Vínculos manuais precisam de fonte independente do índice regenerável.')
        import vinculos_manuais
        return vinculos_manuais

    def payload(self, **extras):
        return {'caso':'OS-900-2099', 'a_tipo':'NOME', 'a_valor':'Ána Fictícia',
                'b_tipo':'CONTA', 'b_valor':'banco ficticio|001234', 'relacao':'hipótese fictícia',
                'a_rotulo':'Ana Fictícia', 'b_rotulo':'Conta Fictícia',
                'evidencia':{'documento':'oficio-ficticio.pdf','pagina':7,'fls':'12','observacao':'Conferir no original'},
                **extras}

    def test_cria_sem_indice_reabre_com_identidade_e_evidencia(self):
        m = self.modulo()
        registro = m.criar(self.ws, self.payload(), 'investigador_ficticio')
        import uuid
        self.assertEqual(str(uuid.UUID(registro['id'])), registro['id'])
        self.assertEqual(registro['versao'], 1)
        self.assertEqual(registro['status'], 'hipotese')
        self.assertFalse(registro['excluido'])
        self.assertEqual(registro['a_valor'], 'ana ficticia')
        self.assertEqual(registro['evidencia']['pagina'], 7)
        self.assertEqual(m.listar(self.ws), [registro])
        self.assertFalse((self.ws/'rag/cpj.sqlite').exists())

    def test_leituras_da_fonte_ausente_nao_criam_pastas_ou_alteram_indice(self):
        m = self.modulo(); db = self.banco(); db.commit()
        import hashlib
        arquivo = self.ws/'rag/cpj.sqlite'
        hash_antes = hashlib.sha256(arquivo.read_bytes()).hexdigest()
        antes = {str(p.relative_to(self.ws)) for p in self.ws.rglob('*')}
        self.assertEqual(m.listar(self.ws),[])
        with self.assertRaises(KeyError): m.historico(self.ws,'00000000-0000-0000-0000-000000000000')
        self.assertEqual(m.exportar_eventos(self.ws),{})
        self.assertEqual(m.exportar_legados(self.ws),{})
        self.assertEqual({str(p.relative_to(self.ws)) for p in self.ws.rglob('*')},antes)
        self.assertEqual(hashlib.sha256(arquivo.read_bytes()).hexdigest(),hash_antes)

    def test_duplicata_nao_apaga_nem_cria_outro_evento(self):
        m = self.modulo()
        primeiro = m.criar(self.ws, self.payload(), 'ficticio')
        with self.assertRaises(m.Conflito):
            m.criar(self.ws, self.payload(), 'outro_ficticio')
        self.assertEqual(m.listar(self.ws), [primeiro])
        self.assertEqual(len(list((self.ws/'consulta/_grafo-manual/eventos').glob('*.json'))), 1)

    def test_atualiza_com_cas_conferencia_e_historico_imutavel(self):
        m = self.modulo()
        self.assertTrue(callable(getattr(m, 'atualizar', None)), 'Edição precisa preservar versões anteriores.')
        registro = m.criar(self.ws, self.payload(), 'autor_ficticio')
        antigo = {p.name:p.read_bytes() for p in (self.ws/'consulta/_grafo-manual/eventos').glob('*.json')}
        novo = m.atualizar(self.ws, registro['id'], {'evidencia':{'observacao':'Conferência humana fictícia'},
                          'status':'conferido'}, 'revisor_ficticio', versao=1)
        self.assertEqual(novo['versao'], 2)
        self.assertEqual(novo['status'], 'conferido')
        self.assertEqual(novo['revisado_por'], 'revisor_ficticio')
        self.assertTrue(novo['revisado_em'])
        self.assertEqual(novo['evidencia']['documento'], 'oficio-ficticio.pdf')
        self.assertEqual(novo['evidencia']['observacao'], 'Conferência humana fictícia')
        for nome, conteudo in antigo.items():
            self.assertEqual((self.ws/'consulta/_grafo-manual/eventos'/nome).read_bytes(), conteudo)
        with self.assertRaises(m.Conflito):
            m.atualizar(self.ws, registro['id'], {'relacao':'versão obsoleta'}, 'outro', versao=1)
        self.assertEqual([e['acao'] for e in m.historico(self.ws, registro['id'])], ['criar','atualizar'])
        self.assertEqual(m.historico(self.ws, registro['id'])[0]['registro']['evidencia']['observacao'], 'Conferir no original')

    def test_exclusao_preserva_tombstone_e_nao_atinge_outro_caso(self):
        m = self.modulo()
        self.assertTrue(callable(getattr(m, 'excluir', None)), 'Exclusão precisa de tombstone persistente.')
        um = m.criar(self.ws, self.payload(), 'autor')
        dois = m.criar(self.ws, self.payload(caso='OS-901-2099'), 'autor')
        apagado = m.excluir(self.ws, um['id'], 'investigador', versao=1)
        self.assertTrue(apagado['excluido'])
        self.assertEqual(apagado['versao'], 2)
        self.assertEqual(m.listar(self.ws), [dois])
        self.assertEqual(len(m.listar(self.ws, incluir_excluidos=True)), 2)
        with self.assertRaises(KeyError):
            m.excluir(self.ws, '00000000-0000-0000-0000-000000000000', 'investigador')
        with self.assertRaises(m.Conflito):
            m.atualizar(self.ws, um['id'], {'relacao':'ressuscitar'}, 'investigador', versao=2)

    def test_validacao_nao_deduz_identidade_ou_pagina(self):
        m = self.modulo()
        for extra in ({'a_tipo':'PESSOA','a_valor':'Ana Ficticia'}, {'b_tipo':'QUALQUER'},
                      {'evidencia':{'pagina':True}}, {'evidencia':{'pagina':'7'}}, {'caso':''}):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                m.criar(self.ws, self.payload(**extra), 'ficticio')
        self.assertEqual(m.listar(self.ws), [])

    def test_escritores_em_processos_separados_nao_perdem_eventos(self):
        m = self.modulo()
        script = "import sys,json; import vinculos_manuais as v; v.criar(sys.argv[1],json.loads(sys.argv[2]),'ficticio')"
        env = dict(os.environ, PYTHONPATH=str(SCRIPTS))
        processos = [subprocess.Popen([sys.executable, '-X','utf8','-c',script,str(self.ws),
                      json.dumps(self.payload(relacao='relação fictícia '+str(n)))],env=env,
                      stdout=subprocess.PIPE,stderr=subprocess.PIPE) for n in range(6)]
        for p in processos:
            _, erro = p.communicate(timeout=30)
            self.assertEqual(p.returncode, 0, erro.decode('utf-8','replace'))
        self.assertEqual({r['relacao'] for r in m.listar(self.ws)},
                         {'relação fictícia '+str(n) for n in range(6)})

    def banco(self):
        (self.ws/'rag').mkdir(exist_ok=True)
        db = sqlite3.connect(self.ws/'rag/cpj.sqlite')
        self.addCleanup(db.close)
        db.executescript('''CREATE TABLE arestas(a_tipo TEXT,a_valor TEXT,b_tipo TEXT,b_valor TEXT,
            relacao TEXT,origem TEXT,fonte TEXT,localizador TEXT);
            CREATE TABLE rotulos(tipo TEXT,valor TEXT,rotulo TEXT,PRIMARY KEY(tipo,valor));''')
        return db

    def test_migra_legados_inclusive_ast05_sem_perder_localizador_ou_duplicatas(self):
        m = self.modulo()
        self.assertTrue(callable(getattr(m, 'migrar_legados', None)), 'Reindexação precisa preservar o legado primeiro.')
        db = self.banco()
        linha = ('NOME','Ána Fictícia','CONTA','banco ficticio|001234','hipótese antiga',
                 'manual','OS-900-2099','texto antigo integral: pág. incerta, conferir')
        db.executemany('INSERT INTO arestas VALUES(?,?,?,?,?,?,?,?)',[linha,linha])
        evidencia = {'documento':'legado.pdf','pagina':17,'fls':'22','observacao':'Texto literal'}
        loc = json.dumps({'schema':'astra-manual/1','evidencia':evidencia},ensure_ascii=False)
        db.execute('INSERT INTO arestas VALUES(?,?,?,?,?,?,?,?)',
                   ('NOME','Outra Fictícia','CONTA','banco ficticio|999','outro legado','manual','OS-900-2099',loc))
        db.execute('INSERT INTO rotulos VALUES(?,?,?)',('NOME','Ána Fictícia','Rótulo legado'))
        db.commit(); db.execute('BEGIN IMMEDIATE')
        self.assertEqual(m.migrar_legados(self.ws,db),3)
        self.assertEqual(m.migrar_legados(self.ws,db),0)
        registros = m.listar(self.ws)
        self.assertEqual(len(registros),3)
        antigos = [r for r in registros if r['relacao']=='hipótese antiga']
        self.assertEqual(len({r['id'] for r in antigos}),2)
        self.assertTrue(all(r['legado']['localizador']==linha[-1] for r in antigos))
        self.assertTrue(all(r['a_rotulo']=='Rótulo legado' for r in antigos))
        self.assertEqual(next(r for r in registros if r['relacao']=='outro legado')['evidencia'],evidencia)
        db.rollback()

    def test_projecao_nao_comita_e_restaura_rotulo_documental_apos_excluir(self):
        m = self.modulo()
        self.assertTrue(callable(getattr(m, 'projetar', None)), 'Grafo precisa ser reconstruído da fonte durável.')
        db = self.banco()
        automatica = ('NOME','ana ficticia','CONTA','banco ficticio|001234','titular','caso','OS-900-2099','fonte.pdf pág. 7')
        db.execute('INSERT INTO arestas VALUES(?,?,?,?,?,?,?,?)',automatica)
        db.execute('INSERT INTO rotulos VALUES(?,?,?)',('NOME','ana ficticia','Nome documental'))
        db.commit()
        registro = m.criar(self.ws,self.payload(),'ficticio')
        db.execute('BEGIN IMMEDIATE'); m.projetar(self.ws,db)
        self.assertTrue(db.in_transaction)
        self.assertEqual(db.execute("SELECT count(*) FROM arestas WHERE origem='manual'").fetchone()[0],1)
        localizador = json.loads(db.execute("SELECT localizador FROM arestas WHERE origem='manual'").fetchone()[0])
        self.assertEqual((localizador['id'],localizador['versao']),(registro['id'],1))
        db.rollback()
        self.assertEqual(db.execute('SELECT count(*) FROM arestas').fetchone()[0],1)
        db.execute('BEGIN IMMEDIATE'); m.projetar(self.ws,db); db.commit()
        m.excluir(self.ws,registro['id'],'ficticio')
        db.execute('BEGIN IMMEDIATE')
        self.assertEqual(m.migrar_legados(self.ws,db),0,'Cache obsoleto não pode ressuscitar tombstone.')
        m.projetar(self.ws,db); db.commit()
        self.assertEqual(db.execute('SELECT * FROM arestas').fetchall(),[automatica])
        self.assertEqual(db.execute("SELECT rotulo FROM rotulos WHERE tipo='NOME' AND valor='ana ficticia'").fetchone()[0], 'Nome documental')

    def indexar(self):
        return subprocess.run([sys.executable,'-X','utf8',str(SCRIPTS/'indexar.py')],
                    env=dict(os.environ,CPJ_WORKSPACE=str(self.ws)),capture_output=True,text=True,encoding='utf-8')

    def test_indexacao_dupla_preserva_manual_e_falha_nao_esvazia_grafo(self):
        m = self.modulo()
        primeiro = self.indexar()
        self.assertEqual(primeiro.returncode,0,primeiro.stderr)
        db = sqlite3.connect(self.ws/'rag/cpj.sqlite')
        self.addCleanup(db.close)
        db.execute('INSERT INTO arestas VALUES(?,?,?,?,?,?,?,?)',
                   ('NOME','legado ficticio','CONTA','banco|1','vínculo legado','manual','OS-900-2099','texto intacto'))
        db.commit()
        for _ in range(2):
            r = self.indexar()
            self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(db.execute("SELECT count(*) FROM arestas WHERE origem='manual'").fetchone()[0],1,
                         'Reindexar não pode apagar o vínculo manual legado.')
        self.assertEqual(len(m.listar(self.ws)),1)
        db.execute("CREATE TRIGGER impedir_falha BEFORE INSERT ON arestas BEGIN SELECT RAISE(ABORT,'falha ficticia'); END")
        db.commit()
        antes = db.execute('SELECT * FROM arestas').fetchall()
        falha = self.indexar()
        self.assertNotEqual(falha.returncode,0)
        self.assertEqual(db.execute('SELECT * FROM arestas').fetchall(),antes)

    def test_pasta_interna_nao_e_base_nem_removivel(self):
        m = self.modulo()
        registro = m.criar(self.ws,self.payload(),'ficticio')
        script = "import consulta; import sys; consulta.remover('_grafo-manual')"
        r = subprocess.run([sys.executable,'-c',script],env=dict(os.environ,CPJ_WORKSPACE=str(self.ws),PYTHONPATH=str(SCRIPTS)),
                            capture_output=True,text=True,encoding='utf-8')
        self.assertNotEqual(r.returncode,0,'A rota de bases não pode apagar o histórico interno.')
        self.assertEqual(m.listar(self.ws),[registro])

    def tarefas(self, ws=None):
        sys.path.insert(0,str(APP))
        from tarefas import Tarefas
        return Tarefas(str(ws or self.ws),None,None,iniciar_agente=False)

    def test_pacotes_dados_e_completo_preservam_historico_importacao_repetida(self):
        m = self.modulo()
        registro = m.criar(self.ws,self.payload(),'autor_ficticio')
        m.atualizar(self.ws,registro['id'],{'relacao':'Anotação preservada'},'revisor',versao=1)
        removido = m.criar(self.ws,self.payload(relacao='removido ficticio'),'autor')
        m.excluir(self.ws,removido['id'],'autor')
        tarefas = self.tarefas()
        for modo in ('dados','completo'):
            tid = tarefas.nova('exportacao','Fictícia','teste')
            retorno = tarefas.exportar(tid,modo,False)
            pacote = self.ws/'exportacoes'/retorno['arquivo']
            with zipfile.ZipFile(pacote) as z:
                nomes = z.namelist()
                self.assertTrue(any(n.startswith('dados/consulta/_grafo-manual/eventos/') for n in nomes))
                self.assertFalse(any(n.endswith('.lock') for n in nomes))
            destino = self.ws/('destino-'+modo)
            (destino/'casos').mkdir(parents=True); (destino/'modelos').mkdir()
            importador = self.tarefas(destino)
            for n in range(2):
                entrada = destino/f'entrada-{n}.zip'; shutil.copy2(pacote,entrada)
                itid = importador.nova('importacao','Fictícia','teste')
                importador.importar(itid,str(entrada))
            self.assertEqual(m.listar(destino,incluir_excluidos=True),m.listar(self.ws,incluir_excluidos=True))
            self.assertEqual(len(m.historico(destino,registro['id'])),2)

    def test_importacao_rejeita_mesmo_id_com_conteudo_divergente_antes_de_confirmar(self):
        m = self.modulo()
        m.criar(self.ws,self.payload(),'autor')
        tarefas = self.tarefas()
        tid = tarefas.nova('exportacao','Fictícia','teste')
        pacote = self.ws/'exportacoes'/tarefas.exportar(tid,'dados',False)['arquivo']
        evento = next((self.ws/'consulta/_grafo-manual/eventos').glob('*.json'))
        conteudo_original = evento.read_bytes()
        destino = self.ws/'destino-conflito'
        (destino/'casos').mkdir(parents=True); (destino/'modelos').mkdir()
        pasta = destino/'consulta/_grafo-manual/eventos'; pasta.mkdir(parents=True)
        divergente = json.loads(conteudo_original); divergente['registro']['relacao']='Conteúdo divergente'
        (pasta/evento.name).write_text(json.dumps(divergente),encoding='utf-8')
        importador = self.tarefas(destino)
        tid = importador.nova('importacao','Fictícia','teste')
        entrada = destino/'entrada.zip'; shutil.copy2(pacote,entrada)
        with self.assertRaisesRegex(ValueError,'divergente'):
            importador.importar(tid,str(entrada))
        self.assertEqual(m.listar(destino)[0]['relacao'],'Conteúdo divergente')
        self.assertEqual(evento.read_bytes(),conteudo_original)

    @unittest.skipUnless(os.name=='nt' and shutil.which('powershell.exe'),'Requer Windows/robocopy')
    def test_backup_restauracao_reconstroi_sem_indice(self):
        m = self.modulo()
        registro = m.criar(self.ws,self.payload(),'autor')
        for nome in ('calibracao','producao','referencias','config','usuarios','ferramentas'):
            (self.ws/nome).mkdir(exist_ok=True)
        for nome in ('backup.ps1','restaurar.ps1'):
            shutil.copy2(ROOT/'ferramentas'/nome,self.ws/'ferramentas'/nome)
        backup = self.ws/'destino-backup'; backup.mkdir()
        cmd = ['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(self.ws/'ferramentas/backup.ps1'),'-Destino',str(backup)]
        r = subprocess.run(cmd,capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        shutil.rmtree(self.ws/'consulta')
        cmd = ['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(self.ws/'ferramentas/restaurar.ps1'),'-Origem',str(backup/'CPJ-TRABALHO-backup')]
        r = subprocess.run(cmd,capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        self.assertEqual(m.listar(self.ws),[registro])
        r = self.indexar(); self.assertEqual(r.returncode,0,r.stderr)
        with closing(sqlite3.connect(self.ws/'rag/cpj.sqlite')) as db:
            loc = json.loads(db.execute("SELECT localizador FROM arestas WHERE origem='manual'").fetchone()[0])
            self.assertEqual(loc['id'],registro['id'])

    def test_historia_corrompida_nao_e_tratada_como_fonte_vazia(self):
        m = self.modulo()
        m.criar(self.ws,self.payload(),'autor')
        evento = next((self.ws/'consulta/_grafo-manual/eventos').glob('*.json'))
        evento.write_text('[]',encoding='utf-8')
        try:
            m.listar(self.ws)
        except Exception as erro:
            self.assertIsInstance(erro,ValueError,'Corrupção deve ser erro de validação explícito.')
        else:
            self.fail('Histórico corrompido não pode parecer fonte vazia.')

    def test_falha_atomica_nao_perde_versao_anterior(self):
        from unittest.mock import patch
        m = self.modulo()
        registro = m.criar(self.ws,self.payload(),'autor')
        with patch.object(m.os,'replace',side_effect=OSError('falha fictícia de armazenamento')):
            with self.assertRaises(OSError):
                m.atualizar(self.ws,registro['id'],{'relacao':'não confirmado'},'autor',versao=1)
        self.assertEqual(m.listar(self.ws),[registro])
        self.assertEqual(len(m.historico(self.ws,registro['id'])),1)
        self.assertEqual(list((self.ws/'consulta/_grafo-manual/eventos').glob('*.tmp')),[])

    def test_cas_em_dois_processos_aceita_apenas_uma_revisao(self):
        m = self.modulo()
        registro = m.criar(self.ws,self.payload(),'autor')
        script = """import sys; import vinculos_manuais as v
try: v.atualizar(sys.argv[1],sys.argv[2],{'relacao':sys.argv[3]},'ficticio',versao=1)
except v.Conflito: print('conflito')
else: print('salvo')
"""
        processos = [subprocess.Popen([sys.executable,'-X','utf8','-c',script,str(self.ws),registro['id'],str(n)],
                      env=dict(os.environ,PYTHONPATH=str(SCRIPTS)),stdout=subprocess.PIPE,stderr=subprocess.PIPE) for n in range(2)]
        saidas = []
        for p in processos:
            out, erro = p.communicate(timeout=30)
            self.assertEqual(p.returncode,0,erro.decode('utf-8','replace')); saidas.append(out.decode().strip())
        self.assertEqual(sorted(saidas),['conflito','salvo'])
        self.assertEqual(len(m.historico(self.ws,registro['id'])),2)

    def test_migracao_interrompida_retomada_nao_perde_ou_duplica(self):
        from unittest.mock import patch
        m = self.modulo(); db = self.banco()
        for n in range(3):
            db.execute('INSERT INTO arestas VALUES(?,?,?,?,?,?,?,?)',
                       ('NOME','legado '+str(n),'CONTA','banco|1','relação '+str(n),'manual','OS-900-2099','texto integral'))
        db.commit(); db.execute('BEGIN IMMEDIATE')
        real_replace = os.replace; quantidade = 0
        def falhar_na_segunda(origem,destino):
            nonlocal quantidade
            if Path(destino).parent.name == 'eventos':
                quantidade += 1
                if quantidade == 2: raise OSError('falha fictícia no disco')
            return real_replace(origem,destino)
        with patch.object(m.os,'replace',side_effect=falhar_na_segunda), self.assertRaises(OSError):
            m.migrar_legados(self.ws,db)
        self.assertEqual(len(m.listar(self.ws)),1)
        self.assertEqual(m.migrar_legados(self.ws,db),2)
        self.assertEqual(len(m.listar(self.ws)),3)
        self.assertEqual(db.execute('SELECT count(*) FROM arestas').fetchone()[0],3)

    def test_importacao_nao_admite_arquivo_interno_por_variacao_de_caixa(self):
        sys.path.insert(0,str(APP))
        from tarefas import _caminho_importavel
        for nome in ('consulta/_GRAFO-MANUAL/intruso.json', 'consulta/_grafo-manual/eventos/../intruso.json',
                     'consulta/_grafo-manual/.vinculos.lock', 'consulta/_grafo-manual./eventos/intruso.json'):
            with self.subTest(nome=nome): self.assertFalse(_caminho_importavel(nome))

    def test_pasta_interna_protegida_tambem_em_subpasta(self):
        m = self.modulo(); registro = m.criar(self.ws,self.payload(),'autor')
        script = "import consulta; consulta.remover('_grafo-manual/eventos')"
        r = subprocess.run([sys.executable,'-c',script],env=dict(os.environ,CPJ_WORKSPACE=str(self.ws),PYTHONPATH=str(SCRIPTS)),capture_output=True)
        self.assertNotEqual(r.returncode,0)
        self.assertEqual(m.listar(self.ws),[registro])

    def test_snapshot_exportavel_nao_muda_quando_fonte_recebe_nova_versao(self):
        m = self.modulo()
        self.assertTrue(callable(getattr(m,'exportar_eventos',None)), 'Exportação precisa capturar um histórico consistente.')
        registro = m.criar(self.ws,self.payload(),'autor')
        snapshot = m.exportar_eventos(self.ws)
        m.atualizar(self.ws,registro['id'],{'relacao':'modificação após snapshot'},'autor',versao=1)
        destino = self.ws/'destino-snapshot'
        m.importar_eventos(destino,snapshot)
        self.assertEqual(m.listar(destino)[0]['versao'],1)
        self.assertEqual(m.listar(self.ws)[0]['versao'],2)

    def test_migra_id_identificado_sem_fonte_nao_inventa_historico_anterior(self):
        import uuid
        m = self.modulo(); db = self.banco()
        id_ = str(uuid.uuid4())
        loc = json.dumps({'schema':'astra-manual/1','id':id_,'versao':3,'evidencia':self.payload()['evidencia']})
        db.execute('INSERT INTO arestas VALUES(?,?,?,?,?,?,?,?)',
                   ('NOME','ana ficticia','CONTA','banco|1','legado identificado','manual','OS-900-2099',loc))
        db.commit(); db.execute('BEGIN IMMEDIATE')
        m.migrar_legados(self.ws,db)
        registro = m.listar(self.ws)[0]
        self.assertEqual(registro['id'],id_,'Identidade já registrada na projeção deve ser preservada.')
        self.assertEqual(registro['versao'],1,'As versões anteriores ausentes não podem ser inventadas.')
        self.assertEqual(registro['legado']['localizador'],loc)

    @unittest.skipUnless(os.name=='nt','Aliases Win32')
    def test_remocao_por_alias_win32_nao_apaga_fonte(self):
        m = self.modulo(); registro = m.criar(self.ws,self.payload(),'autor')
        r = subprocess.run([sys.executable,'-c',"import consulta; consulta.remover('_grafo-manual.')"],
                           env=dict(os.environ,CPJ_WORKSPACE=str(self.ws),PYTHONPATH=str(SCRIPTS)),capture_output=True)
        self.assertNotEqual(r.returncode,0,'Alias Win32 não pode contornar proteção da pasta interna.')
        self.assertEqual(m.listar(self.ws),[registro])

    def test_importacao_valida_snapshot_legado_e_metadados_imutaveis(self):
        m = self.modulo()
        registro = m.criar(self.ws,self.payload(),'autor')
        m.atualizar(self.ws,registro['id'],{'relacao':'versão dois'},'revisor',versao=1)
        snapshot = m.exportar_eventos(self.ws)
        for modo in ('versao_booleana','legado_incompleto','trocar_autor'):
            arquivos = dict(snapshot)
            for nome,conteudo in arquivos.items():
                evento = json.loads(conteudo)
                if evento['versao'] != 2: continue
                if modo == 'versao_booleana': evento['registro']['versao'] = True; evento['versao'] = True
                if modo == 'legado_incompleto': evento['registro']['legado'] = {}; del evento['registro']['evidencia']
                if modo == 'trocar_autor': evento['registro']['usuario'] = 'autor falsamente alterado'
                arquivos[nome] = json.dumps(evento).encode('utf-8')
            with self.subTest(modo=modo), self.assertRaises(ValueError):
                m.validar_importacao(self.ws/('destino-invalido-'+modo),arquivos)

    def test_rotulo_orfao_preservado_em_legado_hash_sem_criar_arestas_e_vai_no_pacote(self):
        import hashlib
        m = self.modulo(); db = self.banco()
        db.execute('DROP TABLE arestas')
        db.execute('INSERT INTO rotulos VALUES(?,?,?)',('NOME','orfao ficticio','Anotação órfã sem origem conhecida'))
        db.commit()
        for _ in range(2):
            r = self.indexar(); self.assertEqual(r.returncode,0,r.stderr)
        snapshots = list((self.ws/'consulta/_grafo-manual/legados').glob('*.json'))
        self.assertEqual(len(snapshots),1,'A anotação antiga deve sobreviver mesmo sem aresta manual.')
        preservado = snapshots[0].read_bytes(); snapshot = json.loads(preservado)
        self.assertEqual(snapshot['proveniencia'],'desconhecida')
        self.assertEqual(snapshot['origem'],'rag/cpj.sqlite')
        self.assertEqual(snapshot['conteudo']['rotulos'],[{'tipo':'NOME','valor':'orfao ficticio','rotulo':'Anotação órfã sem origem conhecida'}])
        digest = hashlib.sha256(json.dumps(snapshot['conteudo'],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')).hexdigest()
        self.assertEqual((snapshot['sha256'],snapshots[0].stem),(digest,digest))
        self.assertEqual(m.listar(self.ws),[])
        self.assertEqual(db.execute('SELECT count(*) FROM arestas').fetchone()[0],0)
        tarefas = self.tarefas(); tid = tarefas.nova('exportacao','Fictício','teste')
        pacote = self.ws/'exportacoes'/tarefas.exportar(tid,'dados',False)['arquivo']
        with zipfile.ZipFile(pacote) as z:
            self.assertEqual(z.read('dados/consulta/_grafo-manual/legados/'+snapshots[0].name),preservado)
        destino = self.ws/'destino-orfao'; (destino/'casos').mkdir(parents=True); (destino/'modelos').mkdir()
        importador = self.tarefas(destino); tid = importador.nova('importacao','Fictício','teste')
        entrada = destino/'entrada.zip'; shutil.copy2(pacote,entrada); importador.importar(tid,str(entrada))
        self.assertEqual((destino/'consulta/_grafo-manual/legados'/snapshots[0].name).read_bytes(),preservado)
        self.assertEqual(m.listar(destino),[])

    def test_ast05_migrado_reenvio_sem_rotulo_continua_duplicata(self):
        m = self.modulo(); db = self.banco(); payload = self.payload(a_valor='ana ficticia')
        loc = json.dumps({'schema':'astra-manual/1','evidencia':payload['evidencia']},ensure_ascii=False)
        db.execute('INSERT INTO arestas VALUES(?,?,?,?,?,?,?,?)',
                   ('NOME','ana ficticia','CONTA',payload['b_valor'],payload['relacao'],'manual',payload['caso'],loc))
        db.execute('INSERT INTO rotulos VALUES(?,?,?)',('NOME','ana ficticia','Rótulo existente'))
        db.commit(); db.execute('BEGIN IMMEDIATE'); m.migrar_legados(self.ws,db); db.commit()
        with self.assertRaises(m.Conflito):
            m.criar(self.ws,self.payload(a_rotulo='',b_rotulo=''),'outro_ficticio')
        self.assertEqual(len(m.listar(self.ws)),1)

    def test_snapshot_captura_anotacao_orfa_alterada_apos_primeira_migracao(self):
        m = self.modulo(); db = self.banco()
        for texto in ('primeira anotação órfã','anotação órfã alterada'):
            db.execute('INSERT OR REPLACE INTO rotulos VALUES(?,?,?)',('NOME','orfao',texto))
            db.commit(); r = self.indexar(); self.assertEqual(r.returncode,0,r.stderr)
        snapshots = [json.loads(p.read_bytes()) for p in (self.ws/'consulta/_grafo-manual/legados').glob('*.json')]
        self.assertEqual({s['conteudo']['rotulos'][0]['rotulo'] for s in snapshots},
                         {'primeira anotação órfã','anotação órfã alterada'})
        self.assertEqual(m.listar(self.ws),[])
        self.assertEqual(db.execute('SELECT count(*) FROM arestas').fetchone()[0],0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
