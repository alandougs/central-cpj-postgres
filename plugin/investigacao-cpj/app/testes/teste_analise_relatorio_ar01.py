"""AR01: análise do operador entrega fluxo de relatório; fila fictícia isolada."""
import json
import os
from pathlib import Path
import sys
import tempfile
import shutil
import subprocess
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from werkzeug.serving import make_server
from teste_explorer_ex01 import ExplorerFixture

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
from plantao import Plantao
from tarefas import Tarefas
import executores_llm as EL


class FluxoAR01(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='cpj-ar01-fila-')
        self.addCleanup(self.temp.cleanup)
        self.ws = self.temp.name
        self.pl = Plantao(self.ws)
        self.cons = json.dumps(EL.criar_consentimento('operador_ficticio', ['cli:codex']))

    def test_pedido_publico_de_analise_encadeia_relatorio_e_revisao(self):
        t = Tarefas(self.ws, SimpleNamespace(), SimpleNamespace(), iniciar_agente=False)
        primeiro = t.enfileirar_ia('OS-901-2099','analisar','operador_ficticio',
                                  preferido='AgenteFicticio',consentimento=self.cons)
        jobs = sorted(t.plantao.pedidos(), key=lambda j:j['ordem'])
        self.assertEqual([j['acao'] for j in jobs], ['analisar','financeiro','relatorio','revisar'])
        self.assertEqual(jobs[0]['id'], primeiro)
        self.assertEqual([j['depende_de'] for j in jobs], [None]+[j['id'] for j in jobs[:-1]])
        self.assertTrue(all(j['consentimento']==self.cons for j in jobs))



class InterfaceAR01(ExplorerFixture,unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sem_agente=os.environ.get('CPJ_SEM_AGENTE_EMBUTIDO')
        os.environ['CPJ_SEM_AGENTE_EMBUTIDO']='1'
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        if cls.sem_agente is None: os.environ.pop('CPJ_SEM_AGENTE_EMBUTIDO',None)
        else: os.environ['CPJ_SEM_AGENTE_EMBUTIDO']=cls.sem_agente

    def setUp(self): pass

    def test_botao_analise_pede_aceite_e_cria_fluxo_com_docx(self):
        runtime=Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/node'
        node=shutil.which('node') or str(runtime/'bin/node.exe')
        if not Path(node).is_file(): self.skipTest('Node/Playwright necessario para teste de navegador')
        env=dict(os.environ,NODE_PATH=str(runtime/'node_modules'))
        server=make_server('127.0.0.1',0,self.s.app,threaded=True)
        t=threading.Thread(target=server.serve_forever,daemon=True); t.start()
        fixture=json.dumps({'url':f'http://127.0.0.1:{server.server_port}','id':self.id})
        script=r'''
const {chromium}=require('playwright');const assert=require('node:assert/strict');
const f=FIXTURE;
(async()=>{const b=await chromium.launch({headless:true,channel:'msedge'});
try{const c=await b.newContext();
assert.equal((await c.request.post(f.url+'/api/entrar',{headers:{'X-CPJ':'1'},data:{login:'admin_ex01',senha:'Ficticia123'}})).status(),200);
const p=await c.newPage();p.on('dialog',x=>x.accept());
await p.goto(f.url+'/#casos');await p.waitForLoadState('networkidle');
await p.evaluate(id=>abrirCaso(id),f.id);
await p.getByRole('button',{name:/^Analisar IP/}).click();
await p.locator('#modal-consentimento').waitFor({state:'visible'});
assert.ok((await p.locator('#cons-destinos').innerText()).includes('codex'));
const [r]=await Promise.all([p.waitForResponse(r=>r.url().endsWith('/ia')&&r.request().method()==='POST'),p.locator('#b-cons-aceitar').click()]);
assert.equal(r.status(),200);assert.ok((await r.json()).tarefa);
await c.close();}finally{await b.close()}})().catch(e=>{console.error(e);process.exit(1)});
'''.replace('FIXTURE',fixture)
        try:
            with patch('plantao.destinos_externos',return_value=['cli:codex']):
                r=subprocess.run([node,'-'],input=script,text=True,encoding='utf-8',env=env,capture_output=True,timeout=60)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            jobs=sorted([j for j in self.s.tarefas.plantao.pedidos() if j['caso']==self.id],key=lambda j:j['ordem'])
            self.assertEqual([j['acao'] for j in jobs],['analisar','financeiro','relatorio','revisar'])
            self.assertTrue(all(j['estado']=='pendente' for j in jobs))
            for job in jobs:
                cons=json.loads(job['consentimento'])
                self.assertEqual(cons['destinos'],['cli:codex'])
                self.assertEqual(cons['usuario'],'admin_ex01')
                self.assertTrue(cons['aceito'])
        finally:
            server.shutdown();t.join(timeout=5);server.server_close()


if __name__=='__main__': unittest.main(verbosity=2)
