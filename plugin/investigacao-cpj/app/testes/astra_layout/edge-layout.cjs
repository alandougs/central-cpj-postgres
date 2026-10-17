// Real Edge/canvas/events; fixture APIs in memory, every network request blocked.
const fs=require('node:fs'),assert=require('node:assert/strict');const{chromium}=require('playwright');
const source=fs.readFileSync(process.argv[2],'utf8');
const data={nos:Array.from({length:20},(_,i)=>({tipo:'PESSOA',valor:'P:FICTICIO-'+i,rotulo:'Pessoa fictícia '+i})),arestas:[],casos:['OS-1-2099'],ordens_servico:[{id:'OS-1-2099',ordem_servico:'1/2099'}]};
for(let i=0;i<20;i++)data.arestas.push({a_tipo:'PESSOA',a_valor:data.nos[i].valor,b_tipo:'PESSOA',b_valor:data.nos[(i+1)%20].valor,relacao:'relação fictícia',relacao_id:'rel-ficticia-'+i,evidencias:[{id:'ref-ficticia-'+i,tipo:'hipotese_manual',origem:'manual',caso:'OS-1-2099',documento:null,observacao:'Hipótese fictícia, não confirma identidade.'}]});
const html=`<style>body{margin:0;background:#101826;color:white}#box{width:calc(100vw - 80px);max-width:1000px;height:60vh}canvas{width:100%;height:100%;display:block}</style><div id="app"><section id="grafo" class="aba on"><select id="gr-caso"><option value="">Todas</option><option>OS-1-2099</option></select><input id="gr-busca"><button id="b-gr-reset">Centralizar</button><button id="b-gr-buscar">Buscar</button><button id="b-gr-foto">PNG</button>${['caso','pessoa','conta','doc','tel','outros'].map(c=>`<input id="gf-${c}" type="checkbox" checked>`).join('')}<div id="box"><canvas id="cv-grafo"></canvas></div><div id="gr-status"></div><div id="gr-mensagem"></div><div id="gr-d-dica"></div><div id="gr-detalhes-conteudo"></div></section></div>`;
(async()=>{const browser=await chromium.launch({channel:'msedge',headless:true});let passed=0;const errors=[];
try{const context=await browser.newContext({viewport:{width:1200,height:1000},deviceScaleFactor:1});await context.route('**/*',r=>r.abort());
const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));await page.setContent(html);
await page.addScriptTag({content:`const $=s=>document.querySelector(s),enc=encodeURIComponent,esc=s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');const pode=()=>false,toast=()=>{},hoje=()=>'',compararNumeroOS=()=>0;let fixture=${JSON.stringify(data)};async function api(){return JSON.parse(JSON.stringify(fixture))}`});
await page.addScriptTag({content:source});
await page.evaluate(()=>{grInitEvents();grDados=fixture;grMontarGrafo();cancelAnimationFrame(grAnimId);grAnimId=null;grSimulando=false;grEnergy=0;grAjustarAoEstabilizar=false;grNodes.forEach((n,i)=>{n.x=100+i%5*120;n.y=80+Math.floor(i/5)*120;n.vx=n.vy=0;n.fixo=true});grZoom=1;grPanX=0;grPanY=0;grInvalidarEspaco();grDesenhar()});
const point=await page.evaluate(()=>{const r=$('#cv-grafo').getBoundingClientRect();return{x:r.left+grNodes[0].x,y:r.top+grNodes[0].y,id:grNodes[0].id}});
await page.mouse.click(point.x,point.y);await page.waitForFunction(()=>grSelectedNode!==null);await page.mouse.wheel(0,-100);await page.waitForFunction(()=>grZoom>1);
const pan=await page.evaluate(()=>{const r=$('#cv-grafo').getBoundingClientRect();return{x:r.right-30,y:r.bottom-30,before:[grPanX,grPanY]}});
await page.mouse.move(pan.x,pan.y);await page.mouse.down();await page.mouse.move(pan.x-45,pan.y-25,{steps:3});await page.mouse.up();
assert.notDeepEqual(await page.evaluate(()=>[grPanX,grPanY]),pan.before);
await page.evaluate(()=>{grNodes[0].fixo=false});const drag=await page.evaluate(()=>{const r=$('#cv-grafo').getBoundingClientRect();return{x:r.left+grNodes[0].x*grZoom+grPanX,y:r.top+grNodes[0].y*grZoom+grPanY}});
await page.mouse.move(drag.x,drag.y);await page.mouse.down();await page.mouse.move(drag.x+60,drag.y+40,{steps:10});await page.mouse.up();
await page.waitForFunction(()=>grNodes[0].fixo);const state=await page.evaluate(()=>({cam:[grZoom,grPanX,grPanY],point:[grNodes[0].x,grNodes[0].y],id:grSelectedNode.id}));
await page.evaluate(()=>carregarGrafo());assert.deepEqual(await page.evaluate(()=>({cam:[grZoom,grPanX,grPanY],point:[grNodes[0].x,grNodes[0].y],id:grSelectedNode.id})),state);
await page.setViewportSize({width:900,height:800});await page.waitForFunction(()=>grSize.width<900);
assert.deepEqual(await page.evaluate(()=>[grZoom,grPanX,grPanY]),state.cam);assert.deepEqual(await page.evaluate(()=>[grNodes[0].x,grNodes[0].y]),state.point);passed++;
// Internal visibility and document visibility preserve physical/camera state.
await page.evaluate(()=>{$('#grafo').classList.remove('on')});await page.waitForFunction(()=>grAnimId===null);
const frozen=await page.evaluate(()=>grNodes.map(n=>[n.id,n.x,n.y]));await page.waitForTimeout(60);assert.deepEqual(await page.evaluate(()=>grNodes.map(n=>[n.id,n.x,n.y])),frozen);
await page.evaluate(()=>{$('#grafo').classList.add('on');Object.defineProperty(document,'hidden',{configurable:true,get:()=>true});document.dispatchEvent(new Event('visibilitychange'))});
assert.equal(await page.evaluate(()=>grAnimId),null);await page.evaluate(()=>{Object.defineProperty(document,'hidden',{configurable:true,get:()=>false});document.dispatchEvent(new Event('visibilitychange'))});passed++;
// Real accessible group controls, expansion and member-to-original inspection.
await page.evaluate(()=>{if(grAnimId)cancelAnimationFrame(grAnimId);grAnimId=null;grSimulando=false;grEnergy=0;grNodes.forEach(n=>{n.x=100;n.y=100;n.fixo=true});grSelectedNode=null;grSelectedEdge=null;grZoom=.5;grPanX=0;grPanY=0;grInvalidarEspaco();grDesenhar()});
await page.getByRole('button',{name:'Agrupar visualmente',exact:true}).click();await page.waitForFunction(()=>grProjetar().nos.length===1);
const group=await page.evaluate(()=>{const r=$('#cv-grafo').getBoundingClientRect(),n=grProjetar().nos[0];return{x:r.left+n.x*grZoom+grPanX,y:r.top+n.y*grZoom+grPanY}});
await page.mouse.click(group.x,group.y);assert.ok((await page.locator('#gr-detalhes-conteudo').innerText()).includes('20 membros'));
assert.ok((await page.locator('#gr-detalhes-conteudo').innerText()).includes('20 relações · 20 referências preservadas'));
await page.getByRole('button',{name:'Expandir 20 membros',exact:true}).click();await page.waitForFunction(()=>grProjetar().nos.length===20);
await page.locator('[data-gr-membro]').first().click();assert.equal(await page.evaluate(()=>grSelectedNode.tipo),'PESSOA');assert.equal(await page.locator('.gr-evidencia').count(),2);
assert.ok((await page.locator('#gr-detalhes-conteudo').innerText()).includes('Hipótese fictícia'));passed++;
assert.deepEqual(errors,[]);console.log(JSON.stringify({passed,browser:browser.version(),network:'blocked',canvas:'real',data:'synthetic-only'}));
}finally{await browser.close()}})().catch(e=>{console.error(e);process.exitCode=1});
