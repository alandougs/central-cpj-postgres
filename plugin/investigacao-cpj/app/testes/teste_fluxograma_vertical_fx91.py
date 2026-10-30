"""FX91: visão em camadas do fluxograma financeiro em fluxo vertical e grande. Edge real, rede bloqueada, dados fictícios."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

STATIC = Path(__file__).resolve().parents[1] / 'static'
RUNTIME = Path.home() / '.cache/codex-runtimes/codex-primary-runtime/dependencies/node'

SCRIPT = r'''
const fs=require('node:fs'),assert=require('node:assert/strict');const{chromium}=require('playwright');
const [js,css1,css2]=process.argv.slice(2);
const camada=(n,titulo,subtotal,txs)=>({camada:n,titulo,subtotal,transacoes:txs});
const tx=(valor,fmt,o,d,extra={})=>({valor,valor_fmt:fmt,data:'2099-01-02',meio:'PIX',origem_titular:o,destino_titular:d,origem_banco:'Banco Fictício',destino_banco:'Banco Teste',fls:'10',...extra});
const fixture={ordem_servico:'1/2099',total_fraude:7000,total_fraude_fmt:'R$ 7.000,00',total_transacoes:4,vitimas:['V'],investigados:['I'],camadas:[
 camada(1,'1ª Camada — Saída da Vítima',7000,[tx(5000,'R$ 5.000,00','Vítima Fictícia',"Laranja D'Ávila"),tx(2000,'R$ 2.000,00','Vítima Fictícia','<img src=x onerror=window.__xss=1>')]),
 camada(2,'2ª Camada — Repasses',5000,[tx(5000,'R$ 5.000,00',"Laranja D'Ávila",'Destino Final Fictício',{hora:'10:30',obs:'observação fictícia'})]),
 camada(3,'3ª Camada — Saques',5000,[tx(1500,'R$ 1.500,00','Destino Final Fictício','Saque em espécie')])]};
const html=`<main style="max-width:1380px;margin:0 auto;padding:20px 16px"><section class="aba on" id="fluxograma"><select id="fx-caso-sel"><option value="">Selecione um caso…</option></select><div class="kpis" id="fx-kpis"></div><div id="fx-conteudo"></div></section></main>`;
(async()=>{const browser=await chromium.launch({channel:'msedge',headless:true});const errors=[];let passed=0;
try{const context=await browser.newContext({viewport:{width:1400,height:900}});await context.route('**/*',r=>r.abort());
const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));await page.setContent(html);
await page.addStyleTag({path:css1});await page.addStyleTag({path:css2});
await page.addScriptTag({content:`const $=s=>document.querySelector(s),enc=encodeURIComponent,esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));let casoAberto=null;async function api(){return ${JSON.stringify(fixture)}}`});
await page.addScriptTag({path:js});
await page.evaluate(()=>CPJFluxograma.carregar('OS-FICTICIA-1'));await page.waitForSelector('#fx-visao-camadas');
const geo=()=>page.evaluate(()=>{const c=document.querySelector('#fx-visao-camadas').getBoundingClientRect();
 const camadas=[...document.querySelectorAll('#fx-visao-camadas .fx-camada')].map(e=>{const r=e.getBoundingClientRect();return{top:r.top,bottom:r.bottom,w:r.width}});
 const valor=document.querySelector('#fx-visao-camadas .fx-valor'),corpo=document.querySelector('#fx-visao-camadas .fx-tx');
 return{cw:c.width,camadas,conectores:document.querySelectorAll('#fx-visao-camadas .fx-conector').length,
  valorPx:valor?parseFloat(getComputedStyle(valor).fontSize):0,corpoPx:corpo?parseFloat(getComputedStyle(corpo).fontSize):0,
  texto:document.querySelector('#fx-visao-camadas').textContent,imgs:document.querySelectorAll('#fx-visao-camadas img').length,xss:window.__xss||0,
  txs:document.querySelectorAll('#fx-visao-camadas .fx-tx').length,
  overflow:document.documentElement.scrollWidth>document.documentElement.clientWidth}});
let g=await geo();
assert.equal(g.camadas.length,3,'3 camadas');
for(let i=1;i<g.camadas.length;i++)assert.ok(g.camadas[i].top>=g.camadas[i-1].bottom,'camada '+(i+1)+' deve ficar abaixo da anterior');
for(const c of g.camadas){assert.ok(c.w>=g.cw*0.9,'camada ocupa a largura do contêiner: '+c.w+' / '+g.cw);assert.ok(c.w>=700,'camada grande em tela larga: '+c.w)}
assert.ok(g.cw<=1140,'largura limitada para leitura: '+g.cw);
assert.equal(g.conectores,2,'conectores = camadas - 1');
assert.ok(g.valorPx>=20,'valor em destaque: '+g.valorPx);assert.ok(g.corpoPx>=14,'texto legível: '+g.corpoPx);
assert.equal(g.txs,4);assert.ok(g.texto.includes('R$ 5.000,00'));assert.ok(g.texto.includes("D'Ávila"));
assert.ok(g.texto.includes('<img src=x onerror=window.__xss=1>'),'HTML do dado aparece como texto');assert.equal(g.imgs,0);assert.equal(g.xss,0);passed++;
// filtro por valor mínimo continua restringindo
await page.locator('#fx-filtro-val-min').fill('4800');await page.locator('#b-fx-aplicar-filtros').click();
g=await geo();assert.equal(g.txs,2,'filtro valor mínimo restringe');assert.equal(g.camadas.length,3,'camadas vazias seguem visíveis');
assert.ok(g.texto.includes('Nenhuma transação atende aos filtros nesta camada.'));passed++;
await page.locator('#b-fx-limpar-filtros').click();assert.equal((await geo()).txs,4);
// alternar para tabela e voltar
await page.locator('#b-fx-toggle-visao').click();await page.waitForSelector('#fx-visao-tabela:not([hidden])');
assert.equal(await page.locator('#fx-tab-transacoes tbody tr').count(),4);assert.ok(await page.locator('#fx-visao-camadas').isHidden());
await page.locator('#b-fx-toggle-visao').click();await page.waitForSelector('#fx-visao-camadas:not([hidden])');assert.equal((await geo()).camadas.length,3);passed++;
// estreito: uma coluna, sem rolagem horizontal
await page.setViewportSize({width:390,height:800});g=await geo();
for(let i=1;i<g.camadas.length;i++)assert.ok(g.camadas[i].top>=g.camadas[i-1].bottom);assert.equal(g.overflow,false,'sem rolagem horizontal no celular');passed++;
assert.deepEqual(errors,[]);console.log(JSON.stringify({passed,browser:browser.version(),network:'blocked',data:'synthetic-only'}));
}finally{await browser.close()}})().catch(e=>{console.error(e);process.exitCode=1});
'''


class FluxogramaVertical(unittest.TestCase):
    def test_camadas_empilhadas_grandes_e_filtros(self):
        node = RUNTIME / 'bin/node.exe'
        if not node.is_file():
            self.skipTest('Runtime Node/Playwright indisponível')
        with tempfile.TemporaryDirectory() as tmp:
            arq = Path(tmp) / 'fx91.cjs'
            arq.write_text(SCRIPT, encoding='utf-8')
            r = subprocess.run([str(node), str(arq), str(STATIC / 'js/fluxograma.js'),
                                str(STATIC / 'css/central.css'), str(STATIC / 'css/apple-cpj.css')],
                               env=dict(os.environ, NODE_PATH=str(RUNTIME / 'node_modules')),
                               capture_output=True, text=True, encoding='utf-8', timeout=90)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == '__main__':
    unittest.main(verbosity=2)
