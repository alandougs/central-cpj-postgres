const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),zlib=require('node:zlib'),crypto=require('node:crypto'),os=require('node:os');
const {chromium}=require('playwright');
const app=path.resolve(process.argv[2]),beforeFile=path.resolve(process.argv[3]),output=path.resolve(process.argv[4]);
if(!fs.existsSync(path.join(app,'static/index.html')))throw Error('Passe a pasta app do snapshot a comparar');
const before=JSON.parse(zlib.gunzipSync(fs.readFileSync(beforeFile))),hash=s=>crypto.createHash('sha256').update(s).digest('hex');
const sourceHashes={before:{},after:{}};for(const [file,src]of Object.entries(before)){sourceHashes.before[file]=hash(src);sourceHashes.after[file]=hash(fs.readFileSync(path.join(app,file)))}
const result={schema:'astra-polling-comparison/1',started:new Date().toISOString(),app,sourceHashes,host:{platform:os.platform(),arch:os.arch(),release:os.release()},limits:['Synthetic HTTP APIs and actual local HTML/JS/CSS; bootstrap disabled. No operational server/data/executor.','Same instrument, scenarios, viewport and observation window before/after. Paired order alternates to limit ordering effects.','MutationObserver records are DOM mutations, not compositor repaints. CDP LayoutCount/RecalcStyleCount/TaskDuration measured separately.','Heap is renderer JavaScript heap, not RAM of whole browser/system. Timing on a shared host.','Hidden emulated through document.hidden and visibilitychange; not proof of native background throttling.','Each scenario has 3 repetitions per variant and 5200 ms observation after its initial request.'],sharedSources:{},samples:[],errors:[],externalRequests:[]};
const scenarios=[{name:'idle-inicio',tab:'inicio',kind:'idle',caseOpen:false},{name:'idle-case',tab:'casos',kind:'idle',caseOpen:true},{name:'active-case',tab:'casos',kind:'active',caseOpen:true},{name:'idle-other-tab-case-open',tab:'pesquisa',kind:'idle',caseOpen:true},{name:'error-case',tab:'casos',kind:'error',caseOpen:true},{name:'hidden-case-emulated',tab:'casos',kind:'idle',caseOpen:true,hidden:true}];
let mode='before',kind='idle';
const task={id:'ia-ficticio-2099',tipo:'ia',caso:'OS-1-2099',titulo:'Análise fictícia',usuario:'operador_ficticio',status:'executando',progresso:35,etapa:'analisando',detalhe:'Bloco fictício',resultado:null};
const server=http.createServer((req,res)=>{
 const u=new URL(req.url,'http://localhost');res.setHeader('Cache-Control','no-store');
 if(u.pathname==='/api/tarefas'){res.writeHead(kind==='error'?503:200,{'Content-Type':'application/json'});res.end(JSON.stringify(kind==='error'?{erro:'Indisponibilidade fictícia'}:kind==='active'?[task]:[]));return}
 if(u.pathname==='/api/fila'){res.writeHead(200,{'Content-Type':'application/json'});res.end(JSON.stringify({idioma_ocr:'por',trabalhos:[]}));return}
 let rel=u.pathname==='/'?'static/index.html':u.pathname.replace(/^\//,'');
 if(rel==='static/js/bootstrap.js'){res.writeHead(200,{'Content-Type':'text/javascript'});res.end('// Bootstrap disabled for synthetic polling measurement.');return}
 const file=path.resolve(app,rel);
 if(!file.startsWith(app+path.sep)||!rel.startsWith('static/')||!fs.existsSync(file)){res.writeHead(404);res.end();return}
 const ext=path.extname(file),mime={'.js':'text/javascript','.css':'text/css','.html':'text/html','.png':'image/png'}[ext]||'application/octet-stream';
 const content=mode==='before'&&before[rel]!==undefined?before[rel]:fs.readFileSync(file);if(before[rel]===undefined)result.sharedSources[rel]=hash(content);
 res.writeHead(200,{'Content-Type':mime+'; charset=utf-8'});res.end(content);
});
const save=()=>fs.writeFileSync(output,zlib.gzipSync(JSON.stringify(result),{level:9}));
const values=m=>Object.fromEntries(m.metrics.map(x=>[x.name,x.value]));
(async()=>{
 await new Promise(r=>server.listen(0,'127.0.0.1',r));const base='http://127.0.0.1:'+server.address().port;
 const browser=await chromium.launch({channel:'msedge',headless:true});result.browser=browser.version();
 try{
  for(let repeat=1;repeat<=3;repeat++)for(const scenario of scenarios)for(const variant of repeat%2?['before','after']:['after','before']){
   mode=variant;kind=scenario.kind;
   const context=await browser.newContext({viewport:{width:1440,height:1000},deviceScaleFactor:1});
   await context.route('**/*',r=>{if(new URL(r.request().url()).origin!==base){result.externalRequests.push(r.request().url());return r.abort()}return r.continue()});
   const page=await context.newPage();page.on('pageerror',e=>result.errors.push({variant,scenario:scenario.name,error:e.message}));
   await page.goto(base);await page.waitForLoadState('networkidle');
   const requests=[],responses=[],pending=new Map();
   page.on('request',r=>{if(r.url().startsWith(base+'/api/')){const item={path:new URL(r.url()).pathname,method:r.method(),at:Date.now()};requests.push(item);pending.set(r,item)}});
   page.on('response',r=>{const item=pending.get(r.request());if(item)responses.push({path:item.path,status:r.status(),latencyMs:Date.now()-item.at})});
   const cdp=await context.newCDPSession(page);await cdp.send('Performance.enable');const start=values(await cdp.send('Performance.getMetrics')),at=Date.now();
   await page.evaluate(async s=>{
    clearTimeout(tc);S={usuario:{login:'ficticio',nome:'Operador fictício'},perms:['pesquisa'],solo:true};$('#tela-login').hidden=true;$('#app').hidden=false;
    $$('section.aba').forEach(x=>x.classList.toggle('on',x.id===s.tab));casoAberto=s.caseOpen?'OS-1-2099':null;
    const p=document.createElement('div');p.id='ia-painel';$('#detalhe').append(p);
    Object.defineProperty(document,'hidden',{configurable:true,get:()=>!!s.hidden});
    window.__mutations=0;window.__obs=new MutationObserver(ms=>window.__mutations+=ms.length);__obs.observe($('#app'),{subtree:true,childList:true,characterData:true});window.__cycleStart=nCiclo;
    await ciclo();await new Promise(r=>queueMicrotask(r));window.__initialMutations=__mutations;__mutations=0;
   },scenario);
   await page.waitForTimeout(5200);
   const dom=await page.evaluate(()=>{clearTimeout(tc);__obs.disconnect();return{initialMutations:__initialMutations,steadyMutations:__mutations,cycles:nCiclo-__cycleStart,hidden:document.hidden,chip:$('#chip-tarefas').innerText,iaPanel:$('#ia-painel').innerText}});
   const end=values(await cdp.send('Performance.getMetrics')),counts={};requests.forEach(r=>counts[r.path]=(counts[r.path]||0)+1);
   const cdpDelta={};for(const k of ['LayoutCount','RecalcStyleCount','TaskDuration','ScriptDuration','LayoutDuration'])cdpDelta[k]=end[k]-start[k];cdpDelta.JSHeapUsedSize=end.JSHeapUsedSize;
   result.samples.push({variant,repeat,...scenario,observedMs:Date.now()-at,requests,responses,counts,...dom,cdp:cdpDelta});save();console.log(JSON.stringify({variant,repeat,scenario:scenario.name,counts,steadyMutations:dom.steadyMutations}));await context.close();
  }
  result.finished=new Date().toISOString();save();if(result.errors.length||result.externalRequests.length)throw Error('Review errors/externalRequests in raw output');
 }finally{await browser.close();await new Promise(r=>server.close(r))}
})().catch(e=>{result.fatal=e.stack;save();console.error(e);server.close();process.exitCode=1});
