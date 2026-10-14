const fs=require('node:fs'), path=require('node:path'), http=require('node:http'), crypto=require('node:crypto');
const {chromium}=require('playwright');
const dir=__dirname,input=process.argv[2]||path.join(dir,'index-before.html');
const source=fs.readFileSync(input,'utf8');
if(!/iniciar\(\);\s*<\/script>/.test(source))throw Error('Bootstrap changed; adapt fixture explicitly');
const html=source.replace(/iniciar\(\);\s*<\/script>/,'/* fixture: bootstrap disabled */</script>');
const result={schema:'astra-ui-baseline/1',started:new Date().toISOString(),input,sha256:crypto.createHash('sha256').update(source).digest('hex'),limits:['Synthetic API and HTML; no operational backend.','Timing in a shared Windows host, Edge headless, viewport 1440x1000 DPR1.','CDP renderer task durations and heap are recorded, not system CPU utilization.','Microbench temporarily suppresses RAF scheduling; live animation measured separately.','Five repetitions per graph size/density; graph topology deterministic but original layout remains random.'],graph:[],polling:[],errors:[],externalRequests:[]};
let fixture='idle';
const task={id:'ia-ficticio-2099',tipo:'ia',caso:'OS-1-2099',titulo:'Análise fictícia',usuario:'operador_ficticio',status:'executando',progresso:35,etapa:'analisando',detalhe:'Bloco fictício',resultado:null};
function respond(url){
 if(url.pathname==='/api/tarefas'){if(fixture==='error')return {status:503,body:{erro:'Indisponibilidade fictícia'}};return {status:200,body:fixture==='active'?[task]:[]};}
 if(url.pathname==='/api/fila')return {status:200,body:{idioma_ocr:'por',trabalhos:fixture==='active'?[{caso:'OS-1-2099',arquivo:'ficticio.pdf',status:'processando',etapa:'OCR',progresso:35,paginas:10,pagina_atual:3}]:[]}};
 if(url.pathname==='/api/plantao/agentes')return {status:200,body:{agentes:[],ociosos:0}};
 return {status:200,body:{}};
}
const server=http.createServer((req,res)=>{const url=new URL(req.url,'http://localhost');if(url.pathname.startsWith('/api/')){const r=respond(url);res.writeHead(r.status,{'Content-Type':'application/json'});res.end(JSON.stringify(r.body));}else if(url.pathname==='/'){res.writeHead(200,{'Content-Type':'text/html; charset=utf-8'});res.end(html)}else{res.writeHead(404);res.end()}});
const save=()=>fs.writeFileSync(path.join(dir,'results.json'),JSON.stringify(result,null,2));
const quant=(a,p)=>{const b=a.slice().sort((x,y)=>x-y);return b[Math.max(0,Math.ceil(p*b.length)-1)]||0};
function stats(a){return {n:a.length,p50:quant(a,.5),p95:quant(a,.95),min:Math.min(...a),max:Math.max(...a)}}
function graph(n,density){const nos=Array.from({length:n},(_,i)=>({tipo:'PESSOA',valor:'P:FICTICIO-'+i,rotulo:'Pessoa fictícia '+i})),arestas=[];for(let i=0;i<n;i++)for(let k=1;k<=density;k++)arestas.push({a_tipo:'PESSOA',a_valor:nos[i].valor,b_tipo:'PESSOA',b_valor:nos[(i+k)%n].valor,relacao:'referência fictícia',origem:'fictício',fonte:'ficticio.pdf',localizador:'pág. 1'});return {nos,arestas,casos:[],indice_disponivel:true}}
async function main(){
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const base='http://127.0.0.1:'+server.address().port;
 const browser=await chromium.launch({channel:'msedge',headless:true});result.browser=browser.version();
 try{
 const context=await browser.newContext({viewport:{width:1440,height:1000},deviceScaleFactor:1});
 await context.route('**/*',route=>{const u=new URL(route.request().url());if(u.origin!==base){result.externalRequests.push(u.origin);return route.abort()}return route.continue()});
 const page=await context.newPage();page.on('pageerror',e=>result.errors.push(e.message));
 await page.goto(base);await page.waitForLoadState('networkidle');
 await page.evaluate(()=>{$('#tela-login').hidden=true;$('#app').hidden=false;$$('section.aba').forEach(x=>x.classList.toggle('on',x.id==='grafo'));S={usuario:{login:'ficticio',nome:'Operador fictício'},perms:['pesquisa'],solo:true};});
 const cdp=await context.newCDPSession(page);await cdp.send('Performance.enable');
 for(const n of [50,100,500,1000])for(const density of [2,10])for(let repeat=1;repeat<=5;repeat++){
 const data=graph(n,density);const metricBefore=await cdp.send('Performance.getMetrics');
 const sample=await page.evaluate(async data=>{
   if(grAnimId)cancelAnimationFrame(grAnimId);grAnimId=null;
   const tick=grTickPhysics,draw=grDesenhar,start=grStartLoop;
   grDados=data;let physics=[],drawing=[],frames=[];grStartLoop=()=>{};
   const t0=performance.now();grMontarGrafo();grDesenhar();const mount=performance.now()-t0;
   for(let i=0;i<3;i++){tick();draw()}
   for(let i=0;i<20;i++){let t=performance.now();tick();physics.push(performance.now()-t);t=performance.now();draw();drawing.push(performance.now()-t)}
   const livePhysics=[],liveDrawing=[];let last=null;
   grTickPhysics=()=>{const t=performance.now();const r=tick();livePhysics.push(performance.now()-t);const now=performance.now();if(last!==null)frames.push(now-last);last=now;return r};
   grDesenhar=()=>{const t=performance.now();const r=draw();liveDrawing.push(performance.now()-t);return r};
   grStartLoop=start;grEnergy=1;grAjustarAoEstabilizar=false;
   const liveStart=performance.now();grStartLoop();
   await new Promise(resolve=>{let tries=0;function check(){if(grAnimId===null||++tries>=800)resolve();else setTimeout(check,20)}check()});
   const liveDuration=performance.now()-liveStart;
   if(grAnimId)cancelAnimationFrame(grAnimId);const timedOut=grAnimId!==null;grAnimId=null;
   grTickPhysics=tick;grDesenhar=draw;grStartLoop=start;
   return {mountMs:mount,physicsMs:physics,drawMs:drawing,livePhysicsMs:livePhysics,liveDrawMs:liveDrawing,frameIntervalsMs:frames,liveDurationMs:liveDuration,timedOut,nodeCount:grNodes.length,edgeCount:grEdges.length,zoom:grZoom,canvas:{width:$('#cv-grafo').width,height:$('#cv-grafo').height}};
 },data);
 const metricAfter=await cdp.send('Performance.getMetrics');const before=Object.fromEntries(metricBefore.metrics.map(x=>[x.name,x.value])),after=Object.fromEntries(metricAfter.metrics.map(x=>[x.name,x.value]));
 result.graph.push({nodes:n,density,repeat,...sample,cdp:{taskDurationSeconds:after.TaskDuration-before.TaskDuration,scriptDurationSeconds:after.ScriptDuration-before.ScriptDuration,layoutDurationSeconds:after.LayoutDuration-before.LayoutDuration,jsHeapUsedBytes:after.JSHeapUsedSize,jsHeapTotalBytes:after.JSHeapTotalSize}});
 save();console.log(JSON.stringify({graph:n,density,repeat,mountMs:sample.mountMs,physicsP95:quant(sample.physicsMs,.95),drawP95:quant(sample.drawMs,.95),frames:sample.frameIntervalsMs.length,liveMs:sample.liveDurationMs}));
 }
 // Real ciclo scheduler and renderers; no startup/session/worker is run.
 for(const scenario of [{name:'idle-inicio',tab:'inicio',kind:'idle',caseOpen:false},{name:'idle-case',tab:'casos',kind:'idle',caseOpen:true},{name:'active-case',tab:'casos',kind:'active',caseOpen:true},{name:'idle-other-tab-case-open',tab:'pesquisa',kind:'idle',caseOpen:true},{name:'error-case',tab:'casos',kind:'error',caseOpen:true},{name:'hidden-case-emulated',tab:'casos',kind:'idle',caseOpen:true,hidden:true}]){
 fixture=scenario.kind;const requests=[],responses=[];let cycles=0;
 const onReq=req=>{if(req.url().startsWith(base+'/api/'))requests.push({path:new URL(req.url()).pathname,at:Date.now(),method:req.method()})};
 const onResponse=async res=>{if(res.url().startsWith(base+'/api/'))responses.push({path:new URL(res.url()).pathname,status:res.status()})};page.on('request',onReq);page.on('response',onResponse);
 const before=Date.now();
 await page.evaluate(s=>{clearTimeout(tc);S={usuario:{login:'ficticio',nome:'Operador fictício'},perms:['pesquisa'],solo:true};$$('section.aba').forEach(x=>x.classList.toggle('on',x.id===s.tab));casoAberto=s.caseOpen?'OS-1-2099':null;if(!$('#ia-painel')){const p=document.createElement('div');p.id='ia-painel';$('#detalhe').appendChild(p)}Object.defineProperty(document,'hidden',{configurable:true,get:()=>!!s.hidden});window.__mutations=0;window.__obs=new MutationObserver(m=>window.__mutations+=m.length);window.__obs.observe($('#app'),{subtree:true,childList:true,characterData:true});window.__cycleStart=nCiclo;ciclo()},scenario);
 await page.waitForTimeout(5200);
 const dom=await page.evaluate(()=>{clearTimeout(tc);window.__obs.disconnect();return {mutations:window.__mutations,cycles:nCiclo-window.__cycleStart,documentHidden:document.hidden,iaPanel:$('#ia-painel').innerText,chip:$('#chip-tarefas').innerText}});
 page.off('request',onReq);page.off('response',onResponse);const counts={};for(const req of requests)counts[req.path]=(counts[req.path]||0)+1;
 result.polling.push({...scenario,observedMs:Date.now()-before,requests,counts,responses,...dom});save();console.log(JSON.stringify({polling:scenario.name,counts,...dom}));
 }
 const summaries=[];for(const nodes of [50,100,500,1000])for(const density of [2,10]){const rows=result.graph.filter(x=>x.nodes===nodes&&x.density===density);summaries.push({nodes,density,repetitions:rows.length,mountMs:stats(rows.map(x=>x.mountMs)),physicsMs:stats(rows.flatMap(x=>x.physicsMs)),drawMs:stats(rows.flatMap(x=>x.drawMs)),liveFrameIntervalMs:stats(rows.flatMap(x=>x.frameIntervalsMs)),medianFps:1000/quant(rows.flatMap(x=>x.frameIntervalsMs),.5),liveDurationMs:stats(rows.map(x=>x.liveDurationMs)),cdpHeapUsedBytes:stats(rows.map(x=>x.cdp.jsHeapUsedBytes)),cdpTaskDurationSeconds:stats(rows.map(x=>x.cdp.taskDurationSeconds)),timeouts:rows.filter(x=>x.timedOut).length})}
 result.summary=summaries;result.finished=new Date().toISOString();save();console.log('COMPLETE '+path.join(dir,'results.json'));
 if(result.errors.length||result.externalRequests.length||result.graph.some(x=>x.timedOut))throw Error('Review errors/external requests/timeout');
 await context.close();
 }finally{await browser.close();await new Promise(resolve=>server.close(resolve))}
}
main().catch(e=>{result.fatal=e.stack;save();console.error(e);server.close();process.exitCode=1});
