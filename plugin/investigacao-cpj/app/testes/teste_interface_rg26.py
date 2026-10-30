"""RG26: navegador real, recursos locais e fixtures sintéticas isoladas."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest

APP = Path(__file__).resolve().parents[1]


def executar_navegador(url, cenario, autenticar=True):
    runtime = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node"
    node = shutil.which("node") or str(runtime / "bin/node.exe")
    if not Path(node).is_file():
        raise AssertionError("Node/Playwright necessário para validar RG26")
    env = dict(os.environ)
    if (runtime / "node_modules/playwright").exists():
        env["NODE_PATH"] = str(runtime / "node_modules")
    script = r'''
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const url = URL_FIXTURE;
(async()=>{
 const servidor=await chromium.launchServer({headless:true,channel:process.env.CPJ_BROWSER_CHANNEL||'msedge'});
 try {
  const browser=await chromium.connect(servidor.wsEndpoint());
  const context=await browser.newContext();
  if(AUTENTICAR) {
   const login=await context.request.post(url+'/api/entrar',{headers:{'X-CPJ':'1'},
     data:{login:'rg26.admin',senha:'Ficticia123'}});
   assert.equal(login.status(),200);
  }
  const page=await context.newPage(),erros=[],externas=[],pedidos=[],recursos=[];
  page.on('pageerror',e=>erros.push(e.message));
  page.on('console',m=>{if(m.type()==='error')erros.push(m.text())});
  page.on('request',r=>pedidos.push({url:r.url(),method:r.method(),body:r.postData()}));
  page.on('response',r=>{if(r.request().resourceType()==='script')recursos.push({url:r.url(),status:r.status()})});
  await page.route('**/*',async route=>{
   if(/^https?:/.test(route.request().url())&&new URL(route.request().url()).origin!==url){
    externas.push(route.request().url());await route.abort();
   }else await route.continue();
  });
  await page.goto(url+'/#casos');await page.waitForLoadState('networkidle');
  CENARIO
  assert.deepEqual(externas,[],'A interface não deve carregar CDN ou recurso externo');
  assert.deepEqual(erros,[],'Nenhum erro de compilação, execução ou CSP');
 }catch(e){console.error(e);process.exitCode=1}
 finally{
  // Edge pode manter o WebSocket aberto mesmo após browser.close neste host.
  // Encerre exclusivamente a árvore do browser criado por este teste.
  if(process.platform==='win32'){
   const pid=servidor.process().pid;
   const fim=require('node:child_process').spawnSync('taskkill',['/PID',String(pid),'/T','/F'],{stdio:'ignore',windowsHide:true,timeout:10000});
   if(fim.status!==0){
    try{process.kill(pid,0);throw new Error('Edge de teste não foi encerrado: '+pid)}
    catch(e){if(e.code!=='ESRCH')throw e}
   }
  }else await servidor.kill();
 }
 process.exit(process.exitCode||0);
})().catch(e=>{console.error(e);process.exit(1)});
'''.replace("URL_FIXTURE", json.dumps(url)).replace("AUTENTICAR", str(autenticar).lower()).replace("CENARIO", cenario)
    r = subprocess.run([node, "-"], input=script, text=True, encoding="utf-8", env=env,
                       capture_output=True, timeout=55)
    if r.returncode:
        raise AssertionError(r.stdout + r.stderr)


def verificar_scripts_navegador(url, autenticar=True):
    executar_navegador(url, r'''
  const fontes=await page.locator('script[src]').evaluateAll(es=>es.map(e=>e.src));
  assert.ok(fontes.length>0,'Scripts locais devem ser realmente exercitados');
  assert.equal(new Set(fontes).size,fontes.length,'Um recurso não deve ser incluído duas vezes');
  for(const fonte of fontes){
   assert.equal(new URL(fonte).origin,url);
   assert.ok(recursos.some(r=>r.url===fonte&&r.status===200),'Script deve ter sido carregado: '+fonte);
  }
  assert.equal(await page.evaluate(()=>typeof CPJFilaProgresso.calcular),'function');
  assert.equal(await page.evaluate(()=>typeof CPJInteligenciaMapa.carregarMapa),'function');
  const tema=await page.locator('html').getAttribute('data-theme');
  await page.locator('#tema').evaluate(e=>e.click());
  assert.notEqual(await page.locator('html').getAttribute('data-theme'),tema,'Um clique muda o tema uma única vez');
  await page.locator('#tema').evaluate(e=>e.click());
  assert.equal(await page.locator('html').getAttribute('data-theme'),tema);
  if(AUTENTICADO){
   await page.evaluate(()=>{CPJInteligenciaMapa.iniciar();CPJInteligenciaMapa.iniciar()});
   assert.equal(await page.locator('#nav-btn-mapa').count(),1);
   assert.equal(await page.locator('#nav-btn-correlacoes').count(),1);
   let envios=0;
   await page.route('**/api/minha-conta',async route=>{envios++;await route.fulfill({json:{email:'rg26@exemplo.invalid',cargo:'Investigador de Polícia'}})});
   await page.evaluate(()=>{abrirAba('sistema');preencherConta()});
   await page.locator('#f-conta input[name=email]').fill('rg26@exemplo.invalid');
   await page.locator('#f-conta button:not([type])').click();
   await page.waitForFunction(()=>document.querySelector('#msg-conta').textContent==='Dados salvos');
   assert.equal(envios,1,'Uma submissão deve gerar uma única gravação');
  }
'''.replace("AUTENTICADO", str(autenticar).lower()), autenticar)


class InterfaceFixtureRG26(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="cpj-interface-rg26-")
        cls.ws = Path(cls.temp.name)
        cls.env = {k: os.environ.get(k) for k in ("CPJ_WORKSPACE", "CPJ_SEM_AGENTE_EMBUTIDO")}
        os.environ.update(CPJ_WORKSPACE=str(cls.ws), CPJ_SEM_AGENTE_EMBUTIDO="1")
        (cls.ws / "casos").mkdir()
        sys.path.insert(0, str(APP))
        import servidor
        assert Path(servidor.WS).resolve() == cls.ws.resolve(), "Execute cada suíte em processo isolado."
        cls.s = servidor
        servidor.auth.salvar_usuario("rg26.admin", "Administrador fictício", "admin", "Ficticia123")
        cls.server = servidor.criar_servidor_wsgi(servidor.app, "127.0.0.1", 0)
        cls.server.prepare()
        cls.thread = threading.Thread(target=cls.server.serve, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.bind_addr[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()
        cls.thread.join(timeout=5)
        cls.temp.cleanup()
        for k, v in cls.env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def cenario(self, js):
        executar_navegador(self.url, js)


class ScriptsLocaisRG26(InterfaceFixtureRG26):
    def test_scripts_carregam_compilam_e_nao_duplicam_handlers(self):
        verificar_scripts_navegador(self.url)


if __name__ == "__main__":
    unittest.main(verbosity=2)
