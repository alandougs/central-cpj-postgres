"""AP39: revisão independente Edge com workspace e geografia sintéticos TEMP."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from teste_interface_rg26 import InterfaceFixtureRG26

EVIDENCIAS = Path(tempfile.gettempdir()) / "cpj-apple-ap39-20261022"


def navegador(url, cenario):
    """Edge de teste tem processo próprio; kill não alcança navegador do operador."""
    runtime = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node"
    env = dict(os.environ, NODE_PATH=str(runtime / "node_modules"))
    script = r'''
const {chromium}=require('playwright'),assert=require('node:assert/strict');
const url=URL_FIXTURE;
(async()=>{
 const servidor=await chromium.launchServer({headless:true,channel:process.env.CPJ_BROWSER_CHANNEL||'msedge'});
 try{
  const browser=await chromium.connect(servidor.wsEndpoint()),context=await browser.newContext();
  assert.equal((await context.request.post(url+'/api/entrar',{headers:{'X-CPJ':'1'},data:{login:'rg26.admin',senha:'Ficticia123'}})).status(),200);
  const page=await context.newPage(),erros=[],externas=[],pedidos=[],recursos=[];
  page.on('pageerror',e=>erros.push(e.message));
  page.on('console',m=>{if(m.type()==='error')erros.push(m.text())});
  page.on('request',r=>pedidos.push({url:r.url(),method:r.method(),body:r.postData()}));
  page.on('response',r=>{if(r.request().resourceType()==='script')recursos.push({url:r.url(),status:r.status()})});
  await page.route('**/*',async route=>{
   if(/^https?:/.test(route.request().url())&&new URL(route.request().url()).origin!==url){externas.push(route.request().url());await route.abort()}
   else await route.continue();
  });
  await page.goto(url+'/#casos');await page.waitForLoadState('networkidle');
  CENARIO
  assert.deepEqual(externas,[],'Sem recursos externos');
  assert.deepEqual(erros,[],'Sem erro JS ou CSP');
 }catch(e){console.error(e);process.exitCode=1}
 finally{
  if(process.platform==='win32'){
   try{require('node:child_process').execFileSync('taskkill',['/PID',String(servidor.process().pid),'/T','/F'],{stdio:'ignore'})}catch{}
  }else await servidor.kill();
 }
 process.exit(process.exitCode||0);
})().catch(e=>{console.error(e);process.exit(1)});
'''.replace("URL_FIXTURE", json.dumps(url)).replace("CENARIO", cenario)
    resultado = subprocess.run([shutil.which("node") or str(runtime / "bin/node.exe"), "-"],
        input=script, text=True, encoding="utf-8", env=env, capture_output=True, timeout=100)
    if resultado.returncode:
        raise AssertionError(resultado.stdout + resultado.stderr)

SETUP = r'''
 const fs=require('node:fs');
 const out=EVIDENCIAS;
 fs.mkdirSync(out,{recursive:true});
 const registro={id:'ficticio-1',caso:'OS-931-2099',nome:'Pessoa fictícia Alfa',tipo_pessoa:'PF',
  papel:'vítima',municipio:'Presidente Prudente',uf:'SP',lat:-22.12,lon:-51.38,
  precisao:'municipio_aproximado',enderecos_bruto:'Presidente Prudente / SP',
  fonte:{caso:'OS-931-2099',arquivo:'01-extracao/autos/transcricao.md',pagina:2,fls:'30'}};
 const reg2={...registro,id:'ficticio-2',nome:'Empresa fictícia Beta',tipo_pessoa:'PJ',municipio:'São Paulo',lat:-23.55,lon:-46.63};
 const reg3={...registro,id:'ficticio-3',nome:'Pessoa fictícia sem endereço',motivo_sem_localizacao:'sem_endereco'};
 await page.route('**/api/inteligencia/mapa*',route=>route.fulfill({json:{
  pontos:[registro,reg2],grupos:[
   {id:'grupo-a',total:1,registros_ids:[registro.id],municipio:registro.municipio,uf:'SP',lat:registro.lat,lon:registro.lon,precisoes:['municipio_aproximado']},
   {id:'grupo-b',total:1,registros_ids:[reg2.id],municipio:reg2.municipio,uf:'SP',lat:reg2.lat,lon:reg2.lon,precisoes:['municipio_aproximado']}],
  sem_localizacao:[reg3],resumo:{total_registros:3,localizados:2,sem_localizacao:1,pf_localizados:1,pj_localizados:1,precisao_municipio:2},
  cartografia:{total_municipios_base:2,metadata:{licenca:'Geometria sintética de teste'},ufs:{SP:{nome:'São Paulo (fixture)',lat:-23,lon:-49,
   poligono:[[-53,-20],[-49,-19],[-44,-23],[-48,-25],[-53,-23]]}}}}}));
 async function mapa(){
  await page.locator('#nav button[data-a="mapa"]').click();
  await page.waitForSelector('#svg-mapa-offline .mapa-ponto');
 }
 async function tema(t){
  if(await page.locator('html').getAttribute('data-theme')!==t) await page.locator('#tema').click();
  await page.evaluate(()=>Promise.all(document.getAnimations().map(a=>a.finished.catch(()=>{}))));
 }
 async function overflow(){return page.evaluate(()=>({inner:innerWidth,scroll:document.documentElement.scrollWidth,
  excess:[...document.querySelectorAll('body *')].filter(e=>{const r=e.getBoundingClientRect();return r.width&&r.right>innerWidth+2&&getComputedStyle(e).position!=='absolute'}).slice(0,8).map(e=>e.id||e.className)}))}
'''.replace("EVIDENCIAS", json.dumps(str(EVIDENCIAS)))


class AppleUIAP39(InterfaceFixtureRG26):
    def cenario(self, js):
        navegador(self.url, js)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        for numero, status in ((931, "analisado"), (932, "entregue")):
            caso = cls.ws / "casos" / f"OS-{numero}-2099"
            (caso / "01-extracao/autos").mkdir(parents=True)
            (caso / "01-extracao/autos/transcricao.md").write_text(
                "## Página 2\nFONTE SINTÉTICA AP39; Fls. 30", encoding="utf-8")
            (caso / "caso.json").write_text(json.dumps({
                "schema": "cpj-caso/1", "id": caso.name,
                "ordem_servico": f"{numero}/2099", "status": status,
                "natureza": "Estelionato — fixture de interface", "prazo": "2099-12-30",
                "vitimas": ["Pessoa fictícia Alfa"], "investigados": ["Pessoa fictícia Beta"],
                "datas": {}, "documentos": [], "financeiro": {}, "relatorios": []}), encoding="utf-8")

    def test_01_evidencia_visual_desktop_compacto_temas(self):
        prefixo = "antes" if os.environ.get("CPJ_AP39_BASELINE") else "depois"
        abas = [] if os.environ.get("CPJ_AP39_SO_MAPA") else ["inicio", "casos", "nova"]
        for largura in (1440, 390):
            self.cenario(SETUP + r'''
 const width=LARGURA;
  await page.setViewportSize({width,height:1000});
  for(const t of ['light','dark']){
   await tema(t);
   for(const aba of ABAS_CAPTURA){
    await page.locator('#nav button[data-a="'+aba+'"]').click();
    await page.waitForLoadState('networkidle');
    await page.screenshot({path:out+'/'+PREFIXO+'-'+aba+'-'+width+'-'+t+'.png',fullPage:true});
   }
   await mapa();
   await page.screenshot({path:out+'/'+PREFIXO+'-mapa-'+width+'-'+t+'.png',fullPage:true});
  }
'''.replace("PREFIXO", json.dumps(prefixo)).replace("LARGURA", str(largura)).replace("ABAS_CAPTURA", json.dumps(abas)))

    @unittest.skipIf(bool(os.environ.get("CPJ_AP39_BASELINE")), "Apenas captura da linha de base")
    def test_02_contraste_foco_teclado_e_layout(self):
        self.cenario(SETUP + r'''
 const medicoes=[];
 for(const t of ['light','dark']){
  await tema(t);await mapa();
  // A troca de aba anima as cores por 120ms; medir apenas o estado concluído.
  await page.evaluate(()=>Promise.all(document.getAnimations().map(a=>a.finished.catch(()=>{}))));
  const dados=await page.evaluate(()=>{
   const rgba=s=>s.match(/[\d.]+/g).map(Number),blend=(a,b)=>a.slice(0,3).map((v,i)=>v*(a[3]??1)+b[i]*(1-(a[3]??1)));
   function fundo(e){if(!e)return [255,255,255];const c=rgba(getComputedStyle(e).backgroundColor);return blend(c,fundo(e.parentElement))}
   const lum=c=>c.map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4}).reduce((a,v,i)=>a+v*[.2126,.7152,.0722][i],0);
   return [...document.querySelectorAll('#nav button,#mapa h2,#f-mapa-filtros label,#f-mapa-filtros .btn,#mapa-kpis .l,#mapa-inspetor-vazio')]
    .filter(e=>e.getBoundingClientRect().width&&getComputedStyle(e).visibility!=='hidden')
    .map(e=>{const s=getComputedStyle(e),bg=fundo(e),fg=blend(rgba(s.color),bg),a=lum(bg),b=lum(fg),size=parseFloat(s.fontSize),weight=parseInt(s.fontWeight)||400;
     return {texto:e.textContent.trim(),ratio:(Math.max(a,b)+.05)/(Math.min(a,b)+.05),min:size>=24||(size>=18.66&&weight>=700)?3:4.5,font:s.fontFamily,size}});
  });
  assert.ok(dados.length>15);medicoes.push({tema:t,dados});
  for(const d of dados)assert.ok(d.ratio>=d.min,JSON.stringify(d));
  assert.ok(dados.every(d=>/system-ui|Segoe UI|apple-system/.test(d.font)),'Tipografia de sistema computada');
  await page.locator('#mapa-f-caso').focus();await page.keyboard.press('Tab');
  assert.equal(await page.evaluate(()=>document.activeElement.id),'mapa-f-tipo');
  const foco=await page.evaluate(()=>{const s=getComputedStyle(document.activeElement);return {style:s.outlineStyle,width:parseFloat(s.outlineWidth)}});
  assert.ok(foco.width>=2&&foco.style!=='none',JSON.stringify(foco));
  for(const width of [1440,390,720]){
   await page.setViewportSize({width,height:1000});
   for(const aba of ['inicio','casos','nova','mapa']){
    if(aba==='mapa')await mapa();else await page.locator('#nav button[data-a="'+aba+'"]').click();
    const o=await overflow();assert.ok(o.scroll<=o.inner+2,JSON.stringify({t,width,aba,...o}));
   }
  }
 }
 const zoom=await context.newCDPSession(page);
 await zoom.send('Emulation.setDeviceMetricsOverride',{width:720,height:500,deviceScaleFactor:2,mobile:false});
 await page.locator('#nav button[data-a=nova]').click();
 const z=await page.evaluate(()=>({ratio:devicePixelRatio,inner:innerWidth,scroll:document.documentElement.scrollWidth}));
 assert.equal(z.ratio,2);assert.equal(z.inner,720);assert.ok(z.scroll<=722,JSON.stringify(z));
 await page.screenshot({path:out+'/depois-reflow-200.png',fullPage:true});
 fs.writeFileSync(out+'/contraste.json',JSON.stringify(medicoes,null,2));
''')

    @unittest.skipIf(bool(os.environ.get("CPJ_AP39_BASELINE")), "Apenas captura da linha de base")
    def test_03_mapa_unico_atalhos_filtro_fonte_tema_recursos(self):
        self.cenario(SETUP + r'''
 await mapa();
 assert.equal(await page.locator('#svg-mapa-offline').count(),1);
 assert.equal(await page.locator('#m-mapa').count(),1);
 assert.equal(await page.locator('#nav button.on').count(),1);
 assert.equal((await page.locator('#nav button.on').textContent()).trim(),'Mapa');
 assert.equal(await page.locator('#pesquisa #m-mapa').count(),0);
 await page.locator('#mapa-f-caso').fill('OS-931-2099');
 await page.locator('#mapa-f-uf').fill('SP');
 const aplicacao=page.waitForRequest(r=>new URL(r.url()).pathname==='/api/inteligencia/mapa');
 await page.locator('#f-mapa-filtros button[type=submit]').click();
 const reqAplicacao=await aplicacao,urlAplicacao=new URL(reqAplicacao.url());
 assert.equal(urlAplicacao.searchParams.get('caso'),'OS-931-2099');
 assert.equal(urlAplicacao.searchParams.get('uf'),'SP');
 await (await reqAplicacao.response()).finished();
 await page.evaluate(r=>CPJInteligenciaMapa.inspecionarRegistroMapa(r),registro);
 assert.equal(await page.locator('#b-insp-fonte').getAttribute('href'),'/arquivo/OS-931-2099/01-extracao/autos/transcricao.md');
 const fonte=await context.request.get(url+await page.locator('#b-insp-fonte').getAttribute('href'));
 assert.equal(fonte.status(),200);assert.ok((await fonte.text()).includes('FONTE SINTÉTICA AP39'));
 const instancia=await page.locator('#m-mapa').evaluate(e=>{e.dataset.ap39='instancia';return e.dataset.ap39});
 await page.locator('#nav button[data-a=grafo]').click();
 await page.locator('#nav button[data-a=mapa]').click();
 assert.equal(await page.locator('#m-mapa').getAttribute('data-ap39'),instancia);
 assert.equal(await page.locator('#mapa-f-uf').inputValue(),'SP');
 assert.equal(await page.locator('#b-insp-fonte').getAttribute('href'),'/arquivo/OS-931-2099/01-extracao/autos/transcricao.md');
 await page.locator('#b-mapa-voltar-radar').click();
 await page.locator('#corr-f-caso').fill('OS-932-2099');
 const navegacao=page.waitForRequest(r=>new URL(r.url()).pathname==='/api/inteligencia/mapa');
 await page.locator('#b-corr-ir-mapa').click();
 const reqNavegacao=await navegacao,urlNavegacao=new URL(reqNavegacao.url());
 await (await reqNavegacao.response()).finished();
 assert.equal(await page.locator('#mapa-f-caso').inputValue(),'OS-932-2099');
 assert.equal(urlNavegacao.searchParams.get('caso'),'OS-932-2099');
 assert.equal(urlNavegacao.searchParams.get('uf'),'SP');
 assert.equal(await page.locator('#m-mapa').getAttribute('data-ap39'),instancia);
 assert.equal(await page.locator('#mapa-f-uf').inputValue(),'SP');
 await tema('light');await page.emulateMedia({colorScheme:'dark'});
 assert.equal(await page.locator('html').getAttribute('data-theme'),'light');
 await page.setViewportSize({width:1440,height:1000});
 await page.screenshot({path:out+'/depois-mapa-inspetor-1440-light.png',fullPage:true});
 await page.emulateMedia({reducedMotion:'reduce'});
 const rm=await page.locator('#nav button').first().evaluate(e=>getComputedStyle(e).transitionDuration);
 assert.ok(rm.split(',').every(s=>parseFloat(s)<=.01),rm);
 const cdp=await context.newCDPSession(page);
 await cdp.send('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-transparency',value:'reduce'}]});
 assert.equal(await page.locator('header').evaluate(e=>getComputedStyle(e).backdropFilter),'none');
 await cdp.send('Emulation.setEmulatedMedia',{features:[{name:'prefers-contrast',value:'more'}]});
 assert.equal(await page.locator('header').evaluate(e=>getComputedStyle(e).backdropFilter),'none');
 const fontes=await page.locator('script[src]').evaluateAll(es=>es.map(e=>e.src));
 assert.equal(new Set(fontes).size,fontes.length);
 for(const f of fontes)assert.ok(recursos.some(r=>r.url===f&&r.status===200),f);
 assert.equal(await page.locator('link[href*="apple-cpj.css"]').count(),1);
''')

    @unittest.skipIf(bool(os.environ.get("CPJ_AP39_BASELINE")), "Apenas captura da linha de base")
    def test_04_painel_e_login_evidencia_visual(self):
        self.cenario(SETUP + r'''
 for(const width of [1440,390]){
  await page.setViewportSize({width,height:1000});
  for(const t of ['light','dark']){
   await tema(t);
   await page.locator('#nav button[data-a=estatisticas]').click();
   for(let i=0;i<25;i++){
    const r=await context.request.get(url+'/painel');
    if(r.headers()['x-cpj-painel']==='pronto')break;
    if(i===24)throw new Error('Painel fictício não ficou pronto');
    await new Promise(r=>setTimeout(r,200));
   }
   await page.locator('#if-painel').evaluate(e=>e.src='/painel');
   await page.waitForLoadState('networkidle');
   const frame=page.frameLocator('#if-painel');
   await frame.locator('#kpis .card').first().waitFor();
   const fundoFrame=await frame.locator('body').evaluate(e=>getComputedStyle(e).backgroundColor);
   const rgb=fundoFrame.match(/[\d.]+/g).slice(0,3).map(Number);
   assert.equal(rgb.every(c=>c<80),t==='dark','Painel deve acompanhar tema principal: '+t+' / '+fundoFrame);
   await page.screenshot({path:out+'/depois-estatisticas-'+width+'-'+t+'.png',fullPage:true});
  }
 }
 assert.equal((await context.request.post(url+'/api/sair',{headers:{'X-CPJ':'1'}})).status(),200);
 await page.goto(url+'/');await page.waitForLoadState('networkidle');
 assert.ok(await page.locator('#f-login').isVisible());
 for(const t of ['light','dark']){
  await page.evaluate(t=>document.documentElement.dataset.theme=t,t);
  await page.screenshot({path:out+'/depois-login-390-'+t+'.png',fullPage:true});
 }
''')

    @unittest.skipIf(bool(os.environ.get("CPJ_AP39_BASELINE")), "Apenas captura da linha de base")
    def test_05_alvos_mapa_acessiveis_por_teclado(self):
        self.cenario(SETUP + r'''
 await mapa();
 const ponto=page.locator('#svg-mapa-offline .mapa-ponto').first();
 await page.setViewportSize({width:390,height:1000});
 // ResizeObserver substitui os nós SVG; aguarda o layout e a repintura.
 await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
 const tamanho=await ponto.locator('text').evaluate(e=>{const m=e.getScreenCTM();return parseFloat(getComputedStyle(e).fontSize)*Math.hypot(m.a,m.b)});
 fs.writeFileSync(out+'/rotulo-mapa-390.json',JSON.stringify({pxEfetivos:tamanho}));
 assert.ok(tamanho>=11,JSON.stringify({pxEfetivos:tamanho}));
 assert.equal(await ponto.getAttribute('tabindex'),'0','Marcador clicável precisa receber foco de teclado');
 assert.equal(await ponto.getAttribute('role'),'button');
 await ponto.focus();await page.keyboard.press('Enter');
 assert.ok((await page.locator('#mapa-inspetor-conteudo').textContent()).includes('Pessoa fictícia Alfa'));
 assert.equal(await page.locator('#b-insp-fonte').getAttribute('href'),'/arquivo/OS-931-2099/01-extracao/autos/transcricao.md');
 const semloc=page.locator('[data-semloc-id]').first();
 assert.equal(await semloc.getAttribute('tabindex'),'0','Registro clicável precisa receber foco de teclado');
 await semloc.focus();await page.keyboard.press('Space');
 assert.ok((await page.locator('#mapa-inspetor-conteudo').textContent()).includes('Pessoa fictícia sem endereço'));
 const foco=await semloc.evaluate(e=>{const s=getComputedStyle(e);return {w:parseFloat(s.outlineWidth),style:s.outlineStyle}});
 assert.ok(foco.w>=2&&foco.style!=='none',JSON.stringify(foco));
''')


if __name__ == "__main__":
    unittest.main(verbosity=2)
