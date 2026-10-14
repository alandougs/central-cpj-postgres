"""EX01: interface real no Edge headless, com workspace fictício e sem abrir Explorer."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
import unittest
from werkzeug.serving import make_server
from teste_explorer_ex01 import ExplorerFixture


class ExplorerUIEX01(ExplorerFixture, unittest.TestCase):
    def test_docx_separados_e_clique_revela_arquivo_correto(self):
        runtime = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node"
        node = shutil.which("node") or str(runtime / "bin/node.exe")
        if not Path(node).is_file():
            self.skipTest("Node necessario para Playwright")
        env = dict(os.environ)
        if (runtime / "node_modules/playwright").exists():
            env["NODE_PATH"] = str(runtime / "node_modules")
        server = make_server("127.0.0.1", 0, self.s.app, threaded=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        fixture = json.dumps({"url": f"http://127.0.0.1:{server.server_port}", "id": self.id, "docx": self.docx})
        script = r'''
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const f = FIXTURE;
(async()=>{
 const browser=await chromium.launch({headless:true,channel:process.env.CPJ_BROWSER_CHANNEL||'msedge'});
 try {
  const context=await browser.newContext();
  const login=await context.request.post(f.url+'/api/entrar',{headers:{'X-CPJ':'1'},data:{login:'admin_ex01',senha:'Ficticia123'}});
  assert.equal(login.status(),200);
  const page=await context.newPage(), erros=[], pedidos=[];
  page.on('pageerror',e=>erros.push(e.message));
  await page.route('**/api/casos/*/abrir',async route=>{
   const req=route.request();pedidos.push({url:req.url(),body:req.postDataJSON(),csrf:req.headers()['x-cpj']});
   await route.fulfill({json:{ok:true}});
  });
  await page.goto(f.url+'/#casos');await page.waitForLoadState('networkidle');
  await page.evaluate(id=>abrirCaso(id),f.id);
  assert.equal(await page.locator('#arquivos-docx a').count(),1,'DOCX deve ter grupo proprio');
  assert.equal(await page.locator('#arquivos-outros a[href$=".DOCX"]').count(),0);
  assert.equal(await page.locator('#arquivos-outros a').filter({hasText:'fluxo financeiro.csv'}).count(),1);
  assert.equal(await page.locator('#relatorios-docx a').count(),1);
  assert.equal(await page.locator('#relatorios-outros a').count(),1);
  assert.ok((await page.locator('#relatorios-docx').innerText()).includes('Word (DOCX)'));
  await Promise.all([page.waitForResponse(r=>r.url().endsWith('/abrir')),page.locator('#relatorios-docx [data-pasta-arquivo]').click()]);
  assert.deepEqual(pedidos[0].body,{sub:f.docx,selecionar:true});
  assert.equal(pedidos[0].csrf,'1');
  await Promise.all([page.waitForResponse(r=>r.url().endsWith('/abrir')),page.locator('#arquivos-outros [data-pasta-arquivo="02-analise/fluxo financeiro.csv"]').click()]);
  assert.deepEqual(pedidos[1].body,{sub:'02-analise/fluxo financeiro.csv',selecionar:true});
  assert.ok(pedidos.every(p=>p.url.endsWith('/api/casos/'+f.id+'/abrir')));
  const dados=await (await context.request.get(f.url+'/api/casos/'+f.id)).json();
  await page.route('**/api/casos/'+f.id,route=>route.fulfill({json:{...dados,local:false}}));
  await page.evaluate(id=>abrirCaso(id),f.id);
  assert.equal(await page.locator('[data-pasta-arquivo]').count(),0,'Acesso remoto nao deve oferecer Explorer');
  assert.equal(await page.locator('#arquivos-docx a').count(),1,'Download continua disponivel');
  assert.deepEqual(erros,[]);
  await context.close();
  console.log('UI EX01 OK: grupos DOCX, links, cliques por arquivo e acesso remoto.');
 } finally {await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
'''.replace("FIXTURE", fixture)
        # O disparo real do Explorer é validado isoladamente na suíte de rotas.
        try:
            r = subprocess.run([node, "-"], input=script, text=True, encoding="utf-8", env=env,
                               capture_output=True, timeout=90)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            print(r.stdout.strip())
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()

    def setUp(self):
        pass


if __name__ == "__main__":
    unittest.main(verbosity=2)
