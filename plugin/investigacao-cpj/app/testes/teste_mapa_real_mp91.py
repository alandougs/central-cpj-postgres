"""MP91: mapa real (Leaflet local + tiles OpenStreetMap) na aba Mapa. Edge real, dados fictícios.

Nenhum teste acessa a internet: os tiles do OSM são interceptados e respondidos com um PNG fictício,
e qualquer outro host externo é abortado e reprovado.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import unittest
import urllib.request
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parent))
from teste_interface_rg26 import InterfaceFixtureRG26

APP = Path(__file__).resolve().parents[1]
LEAFLET = APP / 'static' / 'vendor' / 'leaflet'
SRI_OFICIAL = {  # Leaflet 1.9.4, valores publicados pelo projeto
    'leaflet.js': 'sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=',
    'leaflet.css': 'sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=',
}


def png_ficticio(lado=256, cinza=226):
    def bloco(tipo, dados):
        corpo = tipo + dados
        return struct.pack('>I', len(dados)) + corpo + struct.pack('>I', zlib.crc32(corpo) & 0xffffffff)
    linha = b'\x00' + bytes([cinza]) * lado
    bruto = zlib.compress(linha * lado)
    return (b'\x89PNG\r\n\x1a\n' + bloco(b'IHDR', struct.pack('>IIBBBBB', lado, lado, 8, 0, 0, 0, 0))
            + bloco(b'IDAT', bruto) + bloco(b'IEND', b''))


DADOS = r'''
const FIX={
 pontos:[
  {id:'p1',nome:'Pessoa fictícia A',tipo_pessoa:'PF',caso:'OS-931-2099',municipio:'Presidente Prudente',uf:'SP',lat:-22.1207,lon:-51.3925,precisao:'municipio_aproximado',papel:'investigado'},
  {id:'p2',nome:'<img src=x onerror="window.__xss=1">Empresa fictícia',tipo_pessoa:'PJ',caso:'OS-931-2099',municipio:'Álvares <b>Machado</b>',uf:'SP',lat:-22.0764,lon:-51.4727,precisao:'coordenada_documentada',papel:'vítima'},
  {id:'p3',nome:'Pessoa fictícia C',tipo_pessoa:'PF',caso:'OS-932-2099',municipio:'Curitiba',uf:'PR',lat:-25.4284,lon:-49.2733,precisao:'municipio_aproximado',papel:'investigado'},
  {id:'p4',nome:'Pessoa fictícia D',tipo_pessoa:'PF',caso:'OS-932-2099',municipio:'Curitiba',uf:'PR',lat:-25.4284,lon:-49.2733,precisao:'municipio_aproximado',papel:'vítima'}
 ],
 grupos:[
  {id:'g1',total:1,pf:1,pj:0,registros_ids:['p1'],municipio:'Presidente Prudente',uf:'SP',lat:-22.1207,lon:-51.3925,casos:['OS-931-2099'],precisoes:['municipio_aproximado']},
  {id:'g2',total:1,pf:0,pj:1,registros_ids:['p2'],municipio:'Álvares <b>Machado</b>',uf:'SP',lat:-22.0764,lon:-51.4727,casos:['OS-931-2099'],precisoes:['coordenada_documentada']},
  {id:'g3',total:2,pf:2,pj:0,registros_ids:['p3','p4'],municipio:'Curitiba',uf:'PR',lat:-25.4284,lon:-49.2733,casos:['OS-932-2099'],precisoes:['municipio_aproximado']},
  {id:'g4',total:1,pf:1,pj:0,registros_ids:['p9'],municipio:'Sem coordenada',uf:'SP',lat:null,lon:null,casos:['OS-934-2099'],precisoes:[]}
 ],
 sem_localizacao:[{id:'s1',nome:'Sem local <b>x</b>',tipo_pessoa:'PF',caso:'OS-933-2099',papel:'investigado',motivo_sem_localizacao:'sem_endereco',enderecos_bruto:''}],
 resumo:{total_registros:5,localizados:4,sem_localizacao:1,pf_localizados:3,pj_localizados:1,precisao_municipio:3,precisao_coordenada:1},
 cartografia:{ufs:{}}
};
await page.route('**/api/inteligencia/mapa*',r=>r.fulfill({json:FIX}));
const abrirMapa=async()=>{
 await page.setViewportSize({width:1440,height:1000});
 await page.locator('#nav button[data-a="mapa"]').click();
 await page.waitForSelector('#mapa-real.leaflet-container');
 await page.waitForFunction(()=>document.querySelectorAll('.mapa-real-marcador').length>0);
};
const zoomDoMapa=()=>page.evaluate(()=>CPJInteligenciaMapa.mapaReal().getZoom());
const marcadores=()=>page.locator('.mapa-real-marcador').count();
'''


def executar(url, cenario, tiles='ok', timeout=90):
    """Edge próprio, encerrado pelo Playwright. tiles: 'ok' responde PNG fictício; 'falha' aborta os tiles."""
    runtime = Path.home() / '.cache/codex-runtimes/codex-primary-runtime/dependencies/node'
    node = shutil.which('node') or str(runtime / 'bin/node.exe')
    env = dict(os.environ, NODE_PATH=str(runtime / 'node_modules'))
    script = r'''
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const url=URL_FIXTURE,MODO_TILES=MODO_JSON,PNG=Buffer.from(PNG_B64,'base64');
(async()=>{
 const servidor=await chromium.launchServer({headless:true,channel:process.env.CPJ_BROWSER_CHANNEL||'msedge'});
 try {
  const browser=await chromium.connect(servidor.wsEndpoint());
  const context=await browser.newContext();
  const login=await context.request.post(url+'/api/entrar',{headers:{'X-CPJ':'1'},data:{login:'rg26.admin',senha:'Ficticia123'}});
  assert.equal(login.status(),200);
  const page=await context.newPage(),externas=[],erros=[],tiles=[];
  page.on('pageerror',e=>erros.push(e.message));
  page.on('console',m=>{
   if(m.type()!=='error')return;
   if(MODO_TILES==='falha'&&/tile\.openstreetmap\.org/.test((m.location()||{}).url||''))return;
   erros.push(m.text());
  });
  await page.route('**/*',async route=>{
   const u=new URL(route.request().url());
   if(/^https?:/.test(u.href)&&u.origin!==url){
    if(u.hostname==='tile.openstreetmap.org'){
     tiles.push({url:u.href,referer:(await route.request().allHeaders())['referer']||''});
     if(MODO_TILES==='falha')return route.abort();
     return route.fulfill({status:200,contentType:'image/png',body:PNG});
    }
    externas.push(u.href);return route.abort();
   }
   return route.continue();
  });
  await page.goto(url+'/#casos');await page.waitForLoadState('networkidle');
  DADOS
  CENARIO
  assert.deepEqual(externas,[],'Nenhum host externo além dos tiles do OpenStreetMap');
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
'''
    script = (script.replace('URL_FIXTURE', json.dumps(url)).replace('MODO_JSON', json.dumps(tiles))
              .replace('PNG_B64', json.dumps(base64.b64encode(png_ficticio()).decode()))
              .replace('DADOS', DADOS).replace('CENARIO', cenario))
    try:
        r = subprocess.run([node, '-'], input=script, text=True, encoding='utf-8', env=env,
                           capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired as erro:
        raise AssertionError(f'Edge não encerrou em {timeout} s: {erro.stdout!r} {erro.stderr!r}') from erro
    if r.returncode:
        raise AssertionError(r.stdout + r.stderr)


class BibliotecaLocal(unittest.TestCase):
    def test_leaflet_local_integro_e_com_licenca(self):
        for nome, sri in SRI_OFICIAL.items():
            dados = (LEAFLET / nome).read_bytes()
            calculado = 'sha256-' + base64.b64encode(hashlib.sha256(dados).digest()).decode()
            self.assertEqual(calculado, sri, nome)
        for nome in ('LICENSE', 'LEIAME.md', 'images/layers.png', 'images/marker-icon.png'):
            self.assertTrue((LEAFLET / nome).is_file(), nome)
        self.assertIn('BSD 2-Clause', (LEAFLET / 'LICENSE').read_text(encoding='utf-8'))
        self.assertIn('1.9.4', (LEAFLET / 'LEIAME.md').read_text(encoding='utf-8'))

    def test_codigo_do_mapa_so_cita_o_host_de_tiles_e_a_pagina_de_atribuicao(self):
        js = (APP / 'static' / 'js' / 'inteligencia-mapa.js').read_text(encoding='utf-8')
        urls = set(re.findall(r'https?://[^\s"\'`<>)]+', js))
        hosts = {re.match(r'https?://([^/]+)', u).group(1) for u in urls}
        self.assertEqual(hosts, {'tile.openstreetmap.org', 'www.openstreetmap.org'}, urls)
        self.assertIn('https://tile.openstreetmap.org/{z}/{x}/{y}.png', urls)
        self.assertNotIn('unpkg', js)
        self.assertNotIn('cdn', js.lower())


class MapaReal(InterfaceFixtureRG26):
    # O fixture RG26 admite uma única subclasse por processo: segurança e navegador ficam juntos.
    def cenario(self, js, tiles='ok'):
        executar(self.url, js, tiles)

    def test_00_csp_libera_somente_o_host_de_tiles_em_img_src(self):
        with urllib.request.urlopen(self.url + '/') as r:
            csp = r.headers['Content-Security-Policy']
        self.assertIn("img-src 'self' data: https://tile.openstreetmap.org;", csp)
        self.assertEqual(re.findall(r'https?://[^\s;]+', csp), ['https://tile.openstreetmap.org'], csp)
        self.assertNotIn('*', csp)
        self.assertNotIn('unsafe-eval', csp)
        self.assertIn("default-src 'self'", csp)
        self.assertIn("script-src 'self' 'unsafe-inline';", csp)
        self.assertIn("connect-src 'self';", csp)
        self.assertIn("style-src 'self' 'unsafe-inline';", csp)

    def test_csp_de_arquivos_de_caso_continua_fechada(self):
        import web_seguro
        self.assertNotIn('http', web_seguro.CSP_ARQUIVO)
        self.assertIn("default-src 'none'", web_seguro.CSP_ARQUIVO)

    def test_arquivos_do_leaflet_sao_servidos_localmente(self):
        for caminho in ('leaflet.js', 'leaflet.css', 'images/layers.png'):
            with urllib.request.urlopen(f'{self.url}/static/vendor/leaflet/{caminho}') as r:
                self.assertEqual(r.status, 200, caminho)

    def test_01_mapa_real_e_o_padrao_com_tiles_somente_osm_e_marcadores(self):
        self.cenario(r'''
  await abrirMapa();
  assert.equal(await page.locator('#svg-mapa-offline').isVisible(),false,'mapa por estados fica oculto no modo real');
  assert.equal(await page.locator('#mapa-real').isVisible(),true);
  for(let i=0;i<60&&!tiles.length;i++)await page.waitForTimeout(100);
  assert.ok(tiles.length>0,'tiles solicitados ao servidor do OpenStreetMap');
  for(const t of tiles){
   assert.match(t.url,/^https:\/\/tile\.openstreetmap\.org\/\d{1,2}\/\d+\/\d+\.png$/,'a URL do tile só leva z/x/y: '+t.url);
   const ref=new URL(t.referer);
   assert.equal(ref.origin,url,'o Referer é só a origem local');
   assert.equal(ref.pathname+ref.search+ref.hash,'/','o Referer não leva caminho, consulta nem fragmento');
  }
  assert.match(await page.locator('#mapa-real .leaflet-control-attribution').innerText(),/OpenStreetMap contributors/);
  assert.equal(await page.locator('#mapa-real .leaflet-control-attribution').isVisible(),true);
  assert.equal(await zoomDoMapa()<=8,true,'enquadramento inicial afastado');
  assert.equal(await marcadores(),2,'afastado: Presidente Prudente e Álvares Machado agrupam; Curitiba fica separada; ponto sem coordenada não aparece');
  await page.evaluate(()=>CPJInteligenciaMapa.mapaReal().setView([-22.1,-51.43],12,{animate:false}));
  await page.waitForFunction(()=>document.querySelectorAll('.mapa-real-marcador').length===3);
  assert.equal(await page.locator('#mapa-badge-semloc').textContent(),'1');
  assert.ok((await page.locator('#mapa-lista-semloc').innerText()).includes('Sem local <b>x</b>'),'texto sem localização escapado');
  assert.equal(await page.locator('#mapa-lista-semloc b').count(),1,'só o <b> do próprio layout envolve o nome; nenhum <b> vindo do dado');
''')

    def test_02_rotulos_tooltips_e_inspetor_escapam_html_dos_dados(self):
        self.cenario(r'''
  await abrirMapa();
  await page.evaluate(()=>CPJInteligenciaMapa.mapaReal().setView([-22.1,-51.43],12,{animate:false}));
  await page.waitForFunction(()=>document.querySelectorAll('.mapa-real-marcador').length===3);
  const alvo=page.locator('.mapa-real-marcador[data-ponto-id="p2"]');
  await alvo.hover();
  await page.waitForSelector('.leaflet-tooltip');
  assert.equal(await page.locator('.leaflet-tooltip img').count(),0,'HTML do nome não vira elemento');
  assert.ok((await page.locator('.leaflet-tooltip').innerText()).includes('<img src=x onerror='));
  assert.equal(await page.locator('#mapa-real img[src="x"], #mapa-real .mrk-rotulo img, #mapa-real .mrk-rotulo b').count(),0);
  await alvo.click();
  await page.waitForFunction(()=>document.getElementById('mapa-inspetor-conteudo').textContent.includes('Empresa fictícia'));
  assert.equal(await page.locator('#mapa-inspetor-conteudo img').count(),0);
  assert.equal(await page.evaluate(()=>window.__xss),undefined,'nenhum script dos dados executou');
''')

    def test_03_alternancia_entre_mapa_real_e_por_estados_preserva_a_instancia(self):
        self.cenario(r'''
  await abrirMapa();
  await page.evaluate(()=>{window.__inst=CPJInteligenciaMapa.mapaReal();window.__cont=document.getElementById('mapa-real')});
  assert.equal(await page.locator('#b-mapa-modo-real').getAttribute('aria-pressed'),'true');
  await page.locator('#b-mapa-modo-estados').click();
  assert.equal(await page.locator('#svg-mapa-offline').isVisible(),true);
  assert.equal(await page.locator('#mapa-real').isVisible(),false);
  assert.equal(await page.locator('#b-mapa-modo-estados').getAttribute('aria-pressed'),'true');
  assert.equal(await page.locator('#b-mapa-modo-real').getAttribute('aria-pressed'),'false');
  await page.waitForSelector('.mapa-ponto');
  assert.equal(await page.locator('.mapa-ponto').count(),2,'mapa por estados continua desenhando os pontos individuais');
  assert.equal(await page.locator('#b-mapa-zoom-in').isVisible(),true);
  await page.locator('#b-mapa-modo-real').click();
  assert.equal(await page.locator('#mapa-real').isVisible(),true);
  assert.equal(await page.locator('#svg-mapa-offline').isVisible(),false);
  assert.equal(await page.locator('#b-mapa-zoom-in').isVisible(),false);
  assert.equal(await page.evaluate(()=>window.__inst===CPJInteligenciaMapa.mapaReal()&&window.__cont===document.getElementById('mapa-real')),true,'mesma instância');
  await page.waitForFunction(()=>document.querySelectorAll('.mapa-real-marcador').length>0);
''')

    def test_04_sem_internet_mostra_aviso_e_permite_voltar_ao_mapa_por_estados(self):
        self.cenario(r'''
  await abrirMapa();
  await page.waitForSelector('#mapa-real-aviso:not([hidden])',{timeout:15000});
  const aviso=await page.locator('#mapa-real-aviso').innerText();
  assert.match(aviso,/OpenStreetMap/);
  assert.equal(await page.locator('.mapa-real-marcador').count()>0,true,'marcadores continuam sobre o mapa vazio');
  await page.locator('#b-mapa-real-usar-estados').click();
  assert.equal(await page.locator('#svg-mapa-offline').isVisible(),true);
  assert.equal(await page.locator('#mapa-real-aviso').isVisible(),false);
  await page.waitForSelector('.mapa-ponto');
''', tiles='falha')

    def test_05_atalhos_de_enquadramento_movem_o_mapa_real(self):
        self.cenario(r'''
  await abrirMapa();
  const dentro=(lat,lon)=>page.evaluate(([a,b])=>CPJInteligenciaMapa.mapaReal().getBounds().contains([a,b]),[lat,lon]);
  await page.locator('#b-mapa-foco-deinter8').click();
  await page.waitForFunction(()=>CPJInteligenciaMapa.mapaReal().getZoom()>=7);
  assert.equal(await dentro(-22.1207,-51.3925),true,'DEINTER 8 contém Presidente Prudente');
  await page.locator('#b-mapa-reset-zoom').click();
  await page.waitForFunction(()=>CPJInteligenciaMapa.mapaReal().getZoom()<=5);
  assert.equal(await dentro(-15,-50),true,'Brasil inteiro');
  await page.locator('#b-mapa-foco-sp').click();
  await page.waitForFunction(()=>CPJInteligenciaMapa.mapaReal().getBounds().contains([-22.5,-48]));
  await page.locator('#b-mapa-fit-pontos').click();
  await page.waitForFunction(()=>{const b=CPJInteligenciaMapa.mapaReal().getBounds();return b.contains([-22.1207,-51.3925])&&b.contains([-25.4284,-49.2733])});
''')

    def test_06_agrupamento_afastado_aproxima_e_municipal_abre_o_leque(self):
        self.cenario(r'''
  await abrirMapa();
  const z0=await zoomDoMapa();
  const grande=page.locator('.mapa-real-marcador[data-agrupado="1"]');
  assert.equal(await grande.count(),1);
  assert.equal((await grande.innerText()).trim(),'2','soma os registros dos grupos próximos');
  await grande.click();
  await page.waitForFunction(z=>CPJInteligenciaMapa.mapaReal().getZoom()>z,z0);
  await page.waitForFunction(()=>document.querySelectorAll('.mapa-real-marcador').length===3);
  await page.evaluate(()=>CPJInteligenciaMapa.mapaReal().setView([-25.4284,-49.2733],10,{animate:false}));
  const curitiba=page.locator('.mapa-real-marcador[data-grupo-id="g3"]');
  await curitiba.waitFor({state:'visible'});
  await curitiba.click();
  await page.waitForSelector('#mapa-fanout-box:not([hidden])');
  assert.equal(await page.locator('#mapa-fanout-box [data-fanout-membro]').count(),2);
  assert.equal(await page.locator('.mapa-real-satelite').count(),2,'leque desenhado no mapa');
  await page.locator('#mapa-fanout-box [data-fanout-membro]').nth(1).click();
  await page.waitForFunction(()=>document.getElementById('mapa-inspetor-conteudo').textContent.includes('Pessoa fictícia D'));
  await page.locator('#b-fecha-fanout').click();
  assert.equal(await page.locator('.mapa-real-satelite').count(),0);
''')

    def test_07_estreito_e_tema_claro_continuam_utilizaveis(self):
        self.cenario(r'''
  await abrirMapa();
  for(const tema of ['light','dark']){
   await page.evaluate(t=>document.documentElement.setAttribute('data-theme',t),tema);
   for(const largura of [390,1024]){
    await page.setViewportSize({width:largura,height:900});
    await page.waitForTimeout(150);
    const caixa=await page.locator('#mapa-real').boundingBox();
    assert.ok(caixa.width>=300&&caixa.height>=300,JSON.stringify({tema,largura,caixa}));
    const alvo=await page.locator('.mapa-real-marcador').first().boundingBox();
    assert.ok(alvo.width>=40&&alvo.height>=40,'alvo de toque de pelo menos 40 px: '+JSON.stringify(alvo));
   }
  }
''')


if __name__ == '__main__':
    unittest.main(verbosity=2)
