"""AP37: computed CSS, contrast and input states on synthetic browser content."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import unittest
from fonte_interface import ler_interface


STATIC = Path(__file__).resolve().parents[1] / "static"


class EstiloAppleAP37(unittest.TestCase):
    def test_contraste_controles_responsividade_e_preferencias(self):
        css_file = STATIC / "css/apple-cpj.css"
        self.assertTrue(css_file.is_file(), "The local AP37 stylesheet must exist")
        source = ler_interface(STATIC / "index.html")
        base = re.search(r"<style>(.*?)</style>", source, re.S).group(1)
        panel_source = (STATIC.parents[1] / "skills/base-cpj/scripts/gerar_painel.py").read_text(encoding="utf-8")
        panel_css = re.search(r"<style>(.*?)</style>", panel_source, re.S).group(1)
        runtime = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node"
        node = shutil.which("node") or str(runtime / "bin/node.exe")
        env = dict(os.environ)
        if (runtime / "node_modules/playwright").exists():
            env["NODE_PATH"] = str(runtime / "node_modules")
        script = r'''
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const css=__AP37_MAIN_STYLE__,base=__AP37_BASE_STYLE__,panelCSS=__AP37_PANEL_STYLE__;
function luminance(rgb){return rgb.slice(0,3).map(v=>v/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4).reduce((a,v,i)=>a+v*[.2126,.7152,.0722][i],0)}
function ratio(a,b){const ls=[luminance(a),luminance(b)].sort((x,y)=>x-y);return (ls[1]+.05)/(ls[0]+.05)}
(async()=>{
 console.log('AP37 launching browser');
 const bs=await chromium.launchServer({headless:true,channel:process.env.CPJ_BROWSER_CHANNEL||'msedge',timeout:20000});
 const browser=await chromium.connect(bs.wsEndpoint());
 try{
  const page=await browser.newPage();page.setDefaultTimeout(10000);
  console.log('AP37 browser ready');
  await page.route('**/*',r=>r.abort());
  await page.setContent(`<html data-theme="light"><head><style>${base}</style><style>${css}</style></head><body>
   <header><div class="hd"><div class="brand"><div class="logo">ASTRA<small>Setor de Investigação de Fraudes Patrimoniais</small></div></div>
   <nav>${['Início','Nova O.S.','Casos','Mapa','Pesquisa','Sistema'].map((t,i)=>`<button class="${i?'':'on'}">${t}</button>`).join('')}</nav><button class="btn sm" id="tema">Tema</button></div></header>
   <main><section><h2>Casos de teste</h2><p class="sub">Documentos fictícios para verificar a interface.</p><div class="g2"><div class="card"><h3>Ficha</h3><label for="dado">Identificador</label><input id="dado" placeholder="Pesquisar"><div class="acoes"><button class="btn pri">Pesquisar</button><button class="btn sm">Limpar</button></div><p class="muted">Informação secundária</p><span class="badge pz-vencido">Vencido</span><span class="badge pz-hoje">Hoje</span><span class="badge pz-proximo">Próximo</span><div class="prog ind"><i></i></div></div><div class="card"><table><thead><tr><th>O.S.</th><th>Processo</th></tr></thead><tbody><tr class="linha-concluida"><td>1/2099</td><td>Teste fictício</td></tr></tbody></table></div></div>
   <div class="mapa-layout" style="display:grid;grid-template-columns:1fr 380px;gap:16px"><div class="card mapa-superficie" style="background:#060d18"><svg id="svg-mapa-offline" style="width:100%;height:530px"><polygon fill="#0b1a2e" stroke="#1f3c63"/><polygon id="uf-sp" fill="#16345b" stroke="#325f96"/><text fill="#4b6a8e">SP</text><text id="uf-count" fill="#38bdf8">2</text><g class="mapa-ponto" role="button" tabindex="0" aria-label="Pessoa fictícia" transform="translate(60 60)"><circle class="mapa-alvo" r="22" fill="transparent"/></g></svg></div><div class="card">Inspetor sintético</div></div>
   <p hidden id="sentinela">Oculto</p></section></main></body></html>`);
  for(const theme of ['light','dark']){
   await page.locator('html').evaluate((e,t)=>e.dataset.theme=t,theme);
   const pairs=await page.evaluate(()=>{
    const rgb=s=>(s.match(/[\d.]+/g)||[]).map(Number);
    function bg(e){while(e){const v=getComputedStyle(e).backgroundColor,c=rgb(v);if(c.length===3||c[3]===1)return c;e=e.parentElement}return [255,255,255]}
    return ['body','.sub','.muted','.btn.pri','nav button.on','input','.pz-vencido','.pz-hoje','.pz-proximo','.linha-concluida td'].map(sel=>{const e=document.querySelector(sel),s=getComputedStyle(e);return {sel,color:rgb(s.color),bg:bg(e)}})
   });
   for(const p of pairs)assert.ok(ratio(p.color,p.bg)>=4.5,`${theme} ${p.sel}: ${ratio(p.color,p.bg).toFixed(2)}:1`);
   console.log(theme+' contrast '+pairs.map(p=>p.sel+'='+ratio(p.color,p.bg).toFixed(2)).join(', '));
   const land=await page.locator('#svg-mapa-offline polygon').first().evaluate(e=>getComputedStyle(e).fill);
   assert.equal(land,theme==='light'?'rgb(229, 233, 239)':'rgb(43, 48, 56)','UF geometry follows appearance');
   const geometry=await page.locator('#uf-sp').evaluate(e=>[getComputedStyle(e).fill,getComputedStyle(e).stroke,getComputedStyle(document.querySelector('#uf-count')).fill].map(v=>v.match(/[\d.]+/g).map(Number)));
   assert.ok(ratio(geometry[0],geometry[1])>=3,`Map boundary ${theme}: ${ratio(geometry[0],geometry[1])}`);
   assert.ok(ratio(geometry[0],geometry[2])>=4.5,`Map count ${theme}: ${ratio(geometry[0],geometry[2])}`);
  }
  await page.locator('.mapa-ponto').focus();
  assert.equal(await page.locator('.mapa-alvo').evaluate(e=>getComputedStyle(e).strokeWidth),'3px','Keyboard focus has a visible map target ring');
  await page.locator('input').focus();
  assert.ok(await page.locator('input').evaluate(e=>parseFloat(getComputedStyle(e).outlineWidth)>=2),'Keyboard focus must be visible');
  assert.equal(await page.locator('#sentinela').isVisible(),false,'Styles must preserve hidden');
  for(const width of [360,768,1440]){
   await page.setViewportSize({width,height:1000});
   const sizes=await page.evaluate(()=>({viewport:innerWidth,document:document.documentElement.scrollWidth,buttons:[...document.querySelectorAll('.btn,nav button')].map(e=>e.getBoundingClientRect().height),map:document.querySelector('.mapa-layout').getBoundingClientRect().width}));
   assert.ok(sizes.document<=sizes.viewport,`No document overflow at ${width}: ${sizes.document}`);
   assert.ok(sizes.buttons.every(h=>h>=32),`Desktop controls >=32px: ${sizes.buttons}`);
   assert.ok(sizes.map<=sizes.viewport);
  }
  await page.setViewportSize({width:720,height:900});
  await page.locator('body').evaluate(e=>e.style.zoom='2');
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'200% zoom must retain content');
  await page.locator('body').evaluate(e=>e.style.zoom='');
  await page.emulateMedia({reducedMotion:'reduce'});
  assert.equal(await page.locator('.prog.ind i').evaluate(e=>getComputedStyle(e).animationName),'none');
  const cdp=await page.context().newCDPSession(page);
  await cdp.send('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-transparency',value:'reduce'}]});
  assert.equal(await page.evaluate(()=>matchMedia('(prefers-reduced-transparency: reduce)').matches),true);
  assert.equal(await page.locator('header').evaluate(e=>getComputedStyle(e).backdropFilter),'none');
  await cdp.send('Emulation.setEmulatedMedia',{features:[{name:'prefers-contrast',value:'more'}]});
  assert.ok(await page.evaluate(()=>{const s=getComputedStyle(document.documentElement);return s.getPropertyValue('--line').trim()===s.getPropertyValue('--control-line').trim()}),'Higher contrast strengthens separators with an explicit theme');
  const touch=await browser.newContext({isMobile:true,hasTouch:true,viewport:{width:360,height:800}});
  const tp=await touch.newPage();await tp.setContent(`<style>${base}</style><style>${css}</style><button class="btn sm">Ação</button>`);
  assert.ok(await tp.locator('button').evaluate(e=>e.getBoundingClientRect().height>=44),'Touch control >=44px');
  await touch.close();
  await page.setContent(`<html data-theme="light"><head><style>${panelCSS}</style></head><body><div class="wrap"><header><h1>Produção fictícia</h1><div class="ctl"><select><option>2099</option></select><button>Tema</button></div></header><div class="grid two"><div class="card"><h2>Entregas</h2><div class="k-s">Descrição de indicador</div></div><div class="card">Dados sintéticos</div></div></div></body></html>`);
  for(const theme of ['light','dark']){
   await page.locator('html').evaluate((e,t)=>e.dataset.theme=t,theme);
   const p=await page.locator('.k-s').evaluate(e=>[getComputedStyle(e).color,getComputedStyle(e.parentElement).backgroundColor].map(v=>v.match(/[\d.]+/g).map(Number)));
   assert.ok(ratio(...p)>=4.5,`Panel ${theme} secondary text: ${ratio(...p)}`);
  }
  await page.setViewportSize({width:360,height:800});
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Standalone panel fits360px');
  await page.locator('button').focus();
  assert.equal(await page.locator('button').evaluate(e=>getComputedStyle(e).outlineWidth),'3px');
 }finally{
  try{await Promise.race([browser.close(),new Promise(r=>setTimeout(r,2000))])}finally{
   try{require('node:child_process').execFileSync('taskkill',['/PID',String(bs.process().pid),'/T','/F'],{stdio:'ignore'})}catch{}
  }
 }
})().then(()=>process.exit(0)).catch(e=>{console.error(e);process.exit(1)});
'''.replace("__AP37_PANEL_STYLE__", json.dumps(panel_css)).replace("__AP37_MAIN_STYLE__", json.dumps(css_file.read_text(encoding="utf-8"))).replace("__AP37_BASE_STYLE__", json.dumps(base))
        result = subprocess.run([node, "-"], input=script, text=True, encoding="utf-8",
                                env=env, capture_output=True, timeout=70)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        print(result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
