"""MV01: movimento do console ASTRA em navegador sintético, desligado em movimento reduzido."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import unittest
from fonte_interface import ler_interface


STATIC = Path(__file__).resolve().parents[1] / "static"


class MovimentoMV01(unittest.TestCase):
    def test_movimento_hover_status_e_movimento_reduzido(self):
        css = (STATIC / "css/apple-cpj.css").read_text(encoding="utf-8")
        base = re.search(r"<style>(.*?)</style>", ler_interface(STATIC / "index.html"), re.S).group(1)
        central = (STATIC / "css/central.css").read_text(encoding="utf-8")
        runtime = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node"
        node = shutil.which("node") or str(runtime / "bin/node.exe")
        env = dict(os.environ)
        if (runtime / "node_modules/playwright").exists():
            env["NODE_PATH"] = str(runtime / "node_modules")
        script = r'''
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const css=__MV01_CSS__,base=__MV01_BASE__,central=__MV01_CENTRAL__;
(async()=>{
 const bs=await chromium.launchServer({headless:true,channel:process.env.CPJ_BROWSER_CHANNEL||'msedge',timeout:20000});
 const browser=await chromium.connect(bs.wsEndpoint());
 try{
  const page=await browser.newPage();page.setDefaultTimeout(10000);
  await page.route('**/*',r=>r.abort());
  await page.setContent(`<html data-theme="dark"><head><style>${base}</style><style>${central}</style><style>${css}</style></head><body>
   <header><div class="hd"><div class="brand"><div class="logo">ASTRA</div></div><nav><button class="on">Início</button><button>Casos <span class="n">2</span></button></nav></div></header>
   <main>
    <section class="aba on" id="inicio"><h2>Início fictício</h2><div class="kpis"><div class="kpi"><div class="l">O.S.</div><div class="kv">3</div></div></div>
     <div class="card" id="c1"><button class="btn pri" id="pri">Ação</button><div class="prog"><i style="width:50%"></i></div></div>
     <div class="esteira-grid"><div class="etapa-card ativa" id="ativa">Etapa ativa</div><div class="etapa-card pendente">Pendente</div></div></section>
    <section class="aba" id="grafo"><div class="card" id="cg">Grafo fictício</div></section>
    <section class="aba" id="mapa"><div class="card" id="cm">Mapa fictício</div></section>
   </main>
   <div class="modal" id="mod" hidden><div class="card">Modal fictício</div></div></body></html>`);
  const anim=sel=>page.locator(sel).evaluate(e=>getComputedStyle(e).animationName);
  const pseudo=(sel,p)=>page.locator(sel).evaluate((e,p)=>getComputedStyle(e,p).animationName,p);
  assert.match(await anim('#inicio'),/mv-entrar/,'Active tab enters with motion');
  await page.waitForTimeout(700);
  assert.equal(await page.locator('#inicio').evaluate(e=>getComputedStyle(e).transform),'none','Tab ends without a residual transform');
  await page.evaluate(()=>{document.querySelector('#inicio').classList.remove('on');document.querySelector('#grafo').classList.add('on');document.querySelector('#mapa').classList.add('on')});
  for(const s of ['#grafo','#mapa','#cg','#cm'])assert.equal(await anim(s),'none',`${s} stays still (GF10)`);
  await page.evaluate(()=>{for(const s of document.querySelectorAll('section'))s.classList.toggle('on',s.id==='inicio')});
  assert.match(await pseudo('header','::after'),/mv-varrer/,'Glass header has a moving highlight');
  assert.match(await anim('#ativa'),/mv-pulso/,'Active stage pulses');
  assert.match(await anim('nav button .n'),/mv-pulso/,'Pending counter pulses');
  assert.match(await anim('.prog > i'),/mv-brilho/,'Progress bar has a moving sheen');
  assert.equal(await anim('.etapa-card.pendente'),'none','Inactive stages stay still');
  await page.waitForTimeout(500);
  const kpi=page.locator('.kpi');await kpi.hover();await page.waitForTimeout(350);
  assert.notEqual(await kpi.evaluate(e=>getComputedStyle(e).transform),'none','KPI lifts on hover');
  await page.locator('#pri').hover();await page.waitForTimeout(350);
  assert.notEqual(await page.locator('#pri').evaluate(e=>getComputedStyle(e).boxShadow),'none','Primary button glows on hover');
  await page.evaluate(()=>document.querySelector('#mod').hidden=false);
  assert.match(await anim('#mod > .card'),/mv-modal/,'Modal card enters with motion');
  await page.evaluate(()=>document.querySelector('#mod').hidden=true);
  for(const width of [360,1440]){
   await page.setViewportSize({width,height:900});
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`No overflow at ${width}`);
  }
  await page.emulateMedia({reducedMotion:'reduce'});
  for(const s of ['#inicio','#ativa','nav button .n','.prog > i'])assert.equal(await anim(s),'none',`${s} still with reduced motion`);
  assert.equal(await pseudo('header','::after'),'none');
  await page.mouse.move(0,0);await kpi.hover();
  assert.equal(await kpi.evaluate(e=>getComputedStyle(e).transform),'none','No hover lift with reduced motion');
  await page.emulateMedia({reducedMotion:'no-preference'});
  const cdp=await page.context().newCDPSession(page);
  await cdp.send('Emulation.setEmulatedMedia',{features:[{name:'prefers-contrast',value:'more'}]});
  assert.equal(await page.locator('header').evaluate(e=>getComputedStyle(e,'::after').display),'none','High contrast removes the header highlight');
  console.log('MV01 ok: entrada, hover, pulso, reflexo, progresso, modal, grafo/mapa parados, movimento reduzido');
 }finally{
  try{await Promise.race([browser.close(),new Promise(r=>setTimeout(r,2000))])}finally{
   try{require('node:child_process').execFileSync('taskkill',['/PID',String(bs.process().pid),'/T','/F'],{stdio:'ignore'})}catch{}
  }
 }
})().then(()=>process.exit(0)).catch(e=>{console.error(e);process.exit(1)});
'''.replace("__MV01_CSS__", json.dumps(css)).replace("__MV01_BASE__", json.dumps(base)).replace("__MV01_CENTRAL__", json.dumps(central))
        result = subprocess.run([node, "-"], input=script, text=True, encoding="utf-8",
                                env=env, capture_output=True, timeout=70)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        print(result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
