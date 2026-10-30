"""AP38: navegação canônica do mapa em Edge, somente workspace fictício TEMP."""
import base64
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from teste_interface_rg26 import InterfaceFixtureRG26
from teste_mapa_real_mp91 import png_ficticio  # MP91: o mapa real pede tiles a tile.openstreetmap.org


def executar_navegador_ap38(url, cenario):
    """Processo próprio do Edge encerrado pelo Playwright, sem fechar Edge do operador."""
    runtime = Path.home() / '.cache/codex-runtimes/codex-primary-runtime/dependencies/node'
    node = shutil.which('node') or str(runtime / 'bin/node.exe')
    env = dict(os.environ, NODE_PATH=str(runtime / 'node_modules'))
    script = r'''
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const url=URL_FIXTURE;
(async()=>{
 const servidor=await chromium.launchServer({headless:true,channel:process.env.CPJ_BROWSER_CHANNEL||'msedge'});
 try {
  const browser=await chromium.connect(servidor.wsEndpoint());
  const context=await browser.newContext();
  const login=await context.request.post(url+'/api/entrar',{headers:{'X-CPJ':'1'},data:{login:'rg26.admin',senha:'Ficticia123'}});
  assert.equal(login.status(),200);
  const page=await context.newPage(),externas=[],erros=[];
  page.on('pageerror',e=>erros.push(e.message));
  page.on('console',m=>{if(m.type()==='error')erros.push(m.text())});
  await page.route('**/*',async route=>{
   if(/^https?:/.test(route.request().url())&&new URL(route.request().url()).origin!==url){
    if(new URL(route.request().url()).hostname==='tile.openstreetmap.org')await route.fulfill({status:200,contentType:'image/png',body:Buffer.from(PNG_B64,'base64')});
    else{externas.push(route.request().url());await route.abort()}
   }else await route.continue();
  });
  await page.goto(url+'/#casos');await page.waitForLoadState('networkidle');
  CENARIO
  assert.deepEqual(externas,[],'Sem CDN ou recursos externos');
  assert.deepEqual(erros,[],'Sem erro JavaScript, recurso ou CSP');
 }catch(e){console.error(e);process.exitCode=1}
 finally{
  if(process.platform==='win32'){
   const pid=servidor.process().pid;
   try{require('node:child_process').execFileSync('taskkill',['/PID',String(pid),'/T','/F'],{stdio:'ignore'})}
   catch(erro){try{process.kill(pid,0);throw erro}catch(consulta){if(consulta.code!=='ESRCH')throw consulta}}
  }else await servidor.kill();
  process.exit(process.exitCode||0);
 }
})().catch(e=>{console.error(e);process.exitCode=1});
'''.replace('URL_FIXTURE', json.dumps(url)).replace('PNG_B64', json.dumps(base64.b64encode(png_ficticio()).decode())).replace('CENARIO', cenario)
    try:
        resultado = subprocess.run([node, '-'], input=script, text=True, encoding='utf-8',
                                   env=env, capture_output=True, timeout=55)
    except subprocess.TimeoutExpired as erro:
        raise AssertionError(f'Edge não encerrou em 55 s: {erro.stdout!r} {erro.stderr!r}') from erro
    if resultado.returncode:
        raise AssertionError(resultado.stdout + resultado.stderr)


class MapaUnicoAP38(InterfaceFixtureRG26):
    def cenario(self, js):
        executar_navegador_ap38(self.url, js)

    def test_mapa_tem_uma_tela_principal_e_preserva_estado_ao_navegar(self):
        self.cenario(r'''
  const mapa=page.locator('#nav button[data-a="mapa"]');
  assert.equal(await mapa.count(),1,'Mapa deve pertencer à navegação principal');
  assert.equal(await page.locator('#b-seg-mapa,#b-gr-mapa').count(),0,'Acessos duplicados removidos');
  await mapa.click();await page.waitForLoadState('networkidle');
  assert.equal(await page.locator('section.aba.on').getAttribute('id'),'mapa');
  assert.equal(await mapa.getAttribute('aria-current'),'page');
  assert.equal(new URL(page.url()).hash,'#mapa');
  assert.equal(await page.locator('#mapa #m-mapa #svg-mapa-offline').count(),1);
  assert.equal(await page.locator('#pesquisa #m-mapa,#grafo #m-mapa').count(),0);
  assert.equal(await page.locator('#svg-mapa-offline').count(),1);
  await page.locator('#b-mapa-modo-estados').click();
  await page.evaluate(()=>window.mapaInstanciaAP38=document.getElementById('svg-mapa-offline'));
  await page.locator('#mapa-f-uf').fill('SP');
  await page.locator('#f-mapa-filtros button[type=submit]').click();
  await page.waitForLoadState('networkidle');
  await page.locator('#b-mapa-zoom-in').click();
  const zoom=await page.locator('#mapa-zoom-label').textContent();
  await page.locator('#nav button[data-a="pesquisa"]').click();
  assert.equal(await mapa.getAttribute('aria-current'),null);
  await mapa.click();await page.waitForLoadState('networkidle');
  assert.equal(await page.locator('#mapa-f-uf').inputValue(),'SP');
  assert.equal(await page.locator('#mapa-zoom-label').textContent(),zoom);
  assert.equal(await page.evaluate(()=>window.mapaInstanciaAP38===document.getElementById('svg-mapa-offline')),true);
  await page.reload();await page.waitForLoadState('networkidle');
  assert.equal(await page.locator('section.aba.on').getAttribute('id'),'mapa','URL direta abre a mesma tela');
  assert.equal(await page.locator('#nav-btn-mapa').getAttribute('aria-current'),'page');
''')

    def test_radar_e_alias_legado_abrem_mesmo_mapa_com_contexto(self):
        self.cenario(r'''
  await page.evaluate(()=>{window.mapaInstanciaAP38=document.getElementById('svg-mapa-offline');
    abrirAba('pesquisa');CPJInteligenciaMapa.ativarModoPesquisa('correlacoes')});
  await page.locator('#corr-f-caso').fill('OS-931-2099');
  const consultaCaso=page.waitForRequest(r=>new URL(r.url()).pathname==='/api/inteligencia/mapa');
  await page.locator('#b-corr-ir-mapa').click();
  const requisicao=await consultaCaso;
  assert.equal(new URL(requisicao.url()).searchParams.get('caso'),'OS-931-2099');
  await (await requisicao.response()).finished();
  assert.equal(await page.locator('section.aba.on').getAttribute('id'),'mapa');
  assert.equal(await page.locator('#mapa-f-caso').inputValue(),'OS-931-2099');
  await page.locator('#b-mapa-voltar-radar').click();
  assert.equal(await page.locator('section.aba.on').getAttribute('id'),'pesquisa');
  assert.equal(await page.locator('#m-correlacoes').isVisible(),true);
  await page.evaluate(()=>CPJInteligenciaMapa.ativarModoPesquisa('mapa'));
  await page.waitForLoadState('networkidle');
  assert.equal(await page.locator('section.aba.on').getAttribute('id'),'mapa');
  assert.equal(await page.locator('#nav-btn-mapa').getAttribute('aria-current'),'page');
  await page.evaluate(()=>{CPJInteligenciaMapa.iniciar();CPJInteligenciaMapa.iniciar()});
  assert.equal(await page.evaluate(()=>window.mapaInstanciaAP38===document.getElementById('svg-mapa-offline')),true);
  assert.equal(await page.locator('#svg-mapa-offline').count(),1);
''')

    def test_rotulo_e_alvo_mantem_tamanho_real_ao_redimensionar_e_aproximar(self):
        self.cenario(r'''
  const ponto={id:'p-ap38',nome:'Pessoa fictícia',tipo_pessoa:'PF',caso:'OS-931-2099',municipio:'Local fictício',uf:'SP',lat:-22,lon:-51,precisao:'municipio_aproximado'};
  await page.route('**/api/inteligencia/mapa*',r=>r.fulfill({json:{pontos:[ponto],grupos:[{id:'g-ap38',total:1,registros_ids:[ponto.id],municipio:ponto.municipio,uf:'SP',lat:ponto.lat,lon:ponto.lon}],sem_localizacao:[],resumo:{},cartografia:{ufs:{}}}}));
  await page.locator('#nav button[data-a="mapa"]').click();
  await page.locator('#b-mapa-modo-estados').click();
  await page.waitForSelector('.mapa-ponto');
  for(const width of [1440,390,1024]){
   await page.setViewportSize({width,height:1000});
   await page.locator('#b-mapa-zoom-in').click();
   const tamanho=await page.locator('.mapa-ponto').evaluate(el=>{
    const texto=el.querySelector('text'),ctm=texto.getScreenCTM();
    const alvo=el.querySelector('.mapa-alvo');
    return {fonte:parseFloat(getComputedStyle(texto).fontSize)*Math.hypot(ctm.a,ctm.b),alvo:alvo?.getBoundingClientRect().width||0};
   });
   assert.ok(tamanho.fonte>=12&&tamanho.fonte<=13.1,JSON.stringify({width,...tamanho}));
   assert.ok(tamanho.alvo>=43.5,JSON.stringify({width,...tamanho}));
  }
''')

    def test_retorno_ao_mapa_com_correlacao_preserva_zoom(self):
        self.cenario(r'''
  await page.route('**/api/inteligencia/correlacoes?*',r=>r.fulfill({json:{itens:[{id:'cid-ficticio-ap38',tipo:'CPF',valor_exibicao:'Identificador fictício',titulo:'Coincidência fictícia',ocorrencias:[]}],total:1,resumo:{}}}));
  await page.route('**/api/inteligencia/mapa*',r=>r.fulfill({json:{pontos:[],grupos:[],sem_localizacao:[],resumo:{},cartografia:{ufs:{}}}}));
  await page.evaluate(()=>CPJInteligenciaMapa.ativarModoPesquisa('correlacoes'));
  await page.locator('[data-corr-acao="mapa"]').click();
  await page.waitForLoadState('networkidle');
  await page.locator('#b-mapa-modo-estados').click();
  await page.locator('#b-mapa-zoom-in').click();
  const zoom=await page.locator('#mapa-zoom-label').textContent();
  await page.locator('#nav button[data-a="pesquisa"]').click();
  const consulta=page.waitForRequest(r=>new URL(r.url()).pathname==='/api/inteligencia/mapa');
  await page.locator('#nav button[data-a="mapa"]').click();
  assert.equal(new URL((await consulta).url()).searchParams.get('correlacao_id'),'cid-ficticio-ap38');
  await page.waitForLoadState('networkidle');
  assert.equal(await page.locator('#mapa-zoom-label').textContent(),zoom,'Retornar à aba mantém o zoom escolhido');
''')


if __name__ == '__main__':
    unittest.main(verbosity=2)
