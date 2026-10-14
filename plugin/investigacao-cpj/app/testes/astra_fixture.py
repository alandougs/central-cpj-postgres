"""Servidor, usuários e índice exclusivamente fictícios para o ASTRA."""
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
from contextlib import closing
from werkzeug.serving import make_server


class AstraFixture:
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='cpj-astra-')
        cls.ws = Path(cls.temp.name)
        cls.env = {k: os.environ.get(k) for k in ('CPJ_WORKSPACE','CPJ_SEM_AGENTE_EMBUTIDO','CPJ_WORKSPACES')}
        os.environ.update(CPJ_WORKSPACE=str(cls.ws), CPJ_SEM_AGENTE_EMBUTIDO='1')
        os.environ.pop('CPJ_WORKSPACES',None)
        cls.caso = 'OS-901-2099'
        for numero in (901,902):
            p=cls.ws/'casos'/f'OS-{numero}-2099'
            for sub in ('00-originais','01-extracao','02-analise','03-relatorios'): (p/sub).mkdir(parents=True)
            (p/'caso.json').write_text(json.dumps({'id':p.name,'ordem_servico':f'{numero}/2099','status':'recebido','datas':{},'ip':{},'relatorios':[]}),encoding='utf-8')
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
        import servidor
        cls.s=servidor
        assert Path(servidor.WS).resolve()==cls.ws.resolve(), 'Teste requer processo isolado'
        servidor.app.config.update(TESTING=True)
        servidor.auth.salvar_usuario('astra_ficticio','Operador fictício','investigador','Ficticia123')
        servidor.auth.salvar_usuario('leitor_ficticio','Leitor fictício','delegado','Ficticia123')
        (cls.ws/'rag').mkdir(exist_ok=True)
        cls.db_path=cls.ws/'rag/cpj.sqlite'
        with closing(sqlite3.connect(cls.db_path)) as db:
            db.executescript('CREATE TABLE arestas(a_tipo TEXT,a_valor TEXT,b_tipo TEXT,b_valor TEXT,relacao TEXT,origem TEXT,fonte TEXT,localizador TEXT); CREATE TABLE rotulos(tipo TEXT,valor TEXT,rotulo TEXT,PRIMARY KEY(tipo,valor));')

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()
        for k,v in cls.env.items():
            if v is None: os.environ.pop(k,None)
            else: os.environ[k]=v

    def setUp(self):
        self.client=self.s.app.test_client()
        r=self.client.post('/api/entrar',json={'login':'astra_ficticio','senha':'Ficticia123'},headers={'X-CPJ':'1'})
        self.assertEqual(r.status_code,200)

    def post(self,path,payload):
        return self.client.post(path,json=payload,headers={'X-CPJ':'1'})

    def payload(self,**extra):
        p={'a_tipo':'CONTA','a_valor':'banco ficticio|1234','b_tipo':'CHAVE_PIX','b_valor':'chave-ficticia','relacao':'chave vinculada','caso':self.caso,'documento':'oficio-ficticio.pdf','pagina':7,'fls':'12','observacao':'Hipótese do operador, conferir a fonte'}
        p.update(extra)
        return p

    def browser(self, script):
        runtime=Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/node'
        node=runtime/'bin/node.exe'
        if not node.is_file(): self.skipTest('Runtime Node/Playwright indisponível')
        server=make_server('127.0.0.1',0,self.s.app,threaded=True)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        setup="""const {chromium}=require('playwright');const assert=require('node:assert/strict');
        (async()=>{const browser=await chromium.launch({headless:true,channel:'msedge'});
        try{const context=await browser.newContext(); const url=URL_FIXTURE;
        assert.equal((await context.request.post(url+'/api/entrar',{headers:{'X-CPJ':'1'},data:{login:'astra_ficticio',senha:'Ficticia123'}})).status(),200);
        const page=await context.newPage();page.setDefaultTimeout(10000);
        BODY_FIXTURE
        }finally{await browser.close()}})().catch(e=>{console.error(e);process.exit(1)});"""
        setup=setup.replace('URL_FIXTURE',json.dumps(f'http://127.0.0.1:{server.server_port}')).replace('BODY_FIXTURE',script)
        try:
            r=subprocess.run([str(node),'-'],input=setup,text=True,encoding='utf-8',env=dict(os.environ,NODE_PATH=str(runtime/'node_modules')),capture_output=True,timeout=90)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            return r.stdout
        finally:
            server.shutdown();thread.join(timeout=5);server.server_close()
