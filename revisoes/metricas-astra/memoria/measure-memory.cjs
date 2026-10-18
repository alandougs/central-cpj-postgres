// AST172: frozen AST13 inputs, fictitious graphs, process working sets from Windows.
const fs=require('node:fs'),path=require('node:path'),http=require('node:http');
const os=require('node:os'),zlib=require('node:zlib'),crypto=require('node:crypto');
const {execFileSync}=require('node:child_process');
const {chromium}=require('playwright');
if(!process.argv.includes('--execute-frozen'))throw Error('Wait for the exclusive host window; pass --execute-frozen only after release.');
const output=process.argv[2];
if(!output||!path.isAbsolute(output)||fs.existsSync(output))throw Error('Provide a new absolute output filename; no overwrite.');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const graphDir=path.resolve(__dirname,'../grafo'),manifest=JSON.parse(fs.readFileSync(path.join(graphDir,'package-manifest.json')));
const snapshots={};
for(const side of ['before','after']){
  const relative='snapshots/'+side+'.html',packed=fs.readFileSync(path.join(graphDir,relative+'.gz'));
  const raw=zlib.gunzipSync(packed),entry=manifest.files[relative];
  if(sha(packed)!==entry.gzipSha256||sha(raw)!==entry.sha256)throw Error('Frozen snapshot integrity mismatch: '+side);
  let html=raw.toString('utf8');
  if(!/iniciar\(\);\s*<\/script>/.test(html))throw Error('Explicit bootstrap adapter required.');
  html=html.replace(/iniciar\(\);\s*<\/script>/,'/* memory fixture: bootstrap disabled */</script>');
  snapshots[side]={html,sha256:sha(raw),gzipSha256:sha(packed),adaptedSha256:sha(html),sourceAssets:JSON.parse(fs.readFileSync(path.join(graphDir,'snapshots/'+side+'.sources.json'),'utf8'))};
}
function graph(n,density){const nos=Array.from({length:n},(_,i)=>({tipo:'PESSOA',valor:'P:FICTICIO-'+i,rotulo:'Pessoa fictícia '+i})),arestas=[];for(let i=0;i<n;i++)for(let k=1;k<=density;k++)arestas.push({a_tipo:'PESSOA',a_valor:nos[i].valor,b_tipo:'PESSOA',b_valor:nos[(i+k)%n].valor,relacao:'referência fictícia',origem:'fictício',fonte:'ficticio.pdf',localizador:'pág. 1'});return {nos,arestas,casos:[],indice_disponivel:true}}
const result={schema:'astra-windows-working-set/1',started:new Date().toISOString(),host:{platform:os.platform(),release:os.release(),arch:os.arch(),node:process.version},method:{viewport:{width:1440,height:1000},dpr:1,nodes:[50,100,500,1000],density:10,repetitions:3,pairOrder:'repeat 1 and 3 before/after; repeat 2 after/before, per node count',freshBrowserPerSample:true,networkIdleBeforeMount:true,physicsIterations:23,fixedWaitAfterMountMs:1000,rafSuppressed:true,gcForced:false},sources:Object.fromEntries(Object.entries(snapshots).map(([side,s])=>[side,{sha256:s.sha256,gzipSha256:s.gzipSha256,adaptedSha256:s.adaptedSha256,assets:s.sourceAssets}])),samples:[],errors:[],externalRequests:[],limits:['Sum of per-process Windows working sets can double-count shared pages; it is not private RAM or total system memory.','CDP SystemInfo.getProcessInfo identifies only this fresh browser instance; helper Node/PowerShell and other applications are excluded.','Each process is read sequentially, not in an atomic OS snapshot. Processes may exit between CDP enumeration and Get-Process; missing reads are recorded and invalidate the sample.','Point-in-time measurement after fixed mounting workload and wait, not peak memory, long-running convergence, leak test or operational workload.','No forced garbage collection; fresh browser each sample, existing OS/file caches and host noise remain.','Three paired samples per node count; p95 is nearest-rank maximum, not a reliable tail estimate.','JS heap from the page Performance CDP session is separate from process working set; never add them.','Before has random layout, after deterministic layout and adaptive text; all original nodes/edges remain expanded.']};
const save=()=>fs.writeFileSync(output,JSON.stringify(result,null,2));
const server=http.createServer((req,res)=>{const u=new URL(req.url,'http://localhost');if(u.pathname==='/before'||u.pathname==='/after'){res.writeHead(200,{'Content-Type':'text/html; charset=utf-8'});res.end(snapshots[u.pathname.slice(1)].html)}else if(u.pathname.startsWith('/api/')){res.writeHead(200,{'Content-Type':'application/json'});res.end(JSON.stringify({}))}else{res.writeHead(404);res.end()}});
async function sample(base,side,n,repeat,order,attempt){
  const browser=await chromium.launch({channel:'msedge',headless:true});
  try{
    result.browser=browser.version();
    const browserCdp=await browser.newBrowserCDPSession();
    const context=await browser.newContext({viewport:result.method.viewport,deviceScaleFactor:1});
    await context.route('**/*',route=>{const u=new URL(route.request().url());if(u.origin!==base){result.externalRequests.push(u.origin);return route.abort()}return route.continue()});
    const page=await context.newPage();page.on('pageerror',e=>result.errors.push({side,n,repeat,message:e.message}));
    await page.goto(base+'/'+side);await page.waitForLoadState('networkidle');
    const cdp=await context.newCDPSession(page);await cdp.send('Performance.enable');
    const mounted=await page.evaluate(data=>{
      $('#tela-login').hidden=true;$('#app').hidden=false;$$('section.aba').forEach(x=>x.classList.toggle('on',x.id==='grafo'));
      S={usuario:{login:'ficticio',nome:'Operador fictício'},perms:['pesquisa'],solo:true};
      if(grAnimId)cancelAnimationFrame(grAnimId);grAnimId=null;grStartLoop=()=>{};
      if(typeof grAgrupar!=='undefined'){grAgrupar=false;grExpandidos.clear();grProjecao=null}
      if(typeof grVistas!=='undefined'){grVistas.clear();grPosicoes.clear();grVistaChave=null;grDominioChave=null;grNodes=[];grEdges=[];grSelectedNode=null;if(typeof grSelectedEdge!=='undefined')grSelectedEdge=null;grVisCache=null;grHitCache=null;grSimulando=false;grEnergy=1}
      grDados=data;grMontarGrafo();grDesenhar();
      // Same mount + three warm-up + twenty tick/draw calls as AST13 micro workload.
      for(let i=0;i<23;i++){grTickPhysics();grDesenhar()}
      return {nodeCount:grNodes.length,edgeCount:grEdges.length,visibleNodeCount:grNodes.filter(n=>grCatAtiva(n.cat)).length,visibleEdgeCount:grEdges.filter(e=>grCatAtiva(e.source.cat)&&grCatAtiva(e.target.cat)).length,projectedNodeCount:typeof grProjetar==='undefined'?grNodes.length:grProjetar().nos.length,projectedEdgeCount:typeof grProjetar==='undefined'?grEdges.length:grProjetar().arestas.length,zoom:grZoom,rafStopped:grAnimId===null};
    },graph(n,10));
    for(const key of ['nodeCount','visibleNodeCount','projectedNodeCount'])if(mounted[key]!==n)throw Error('Node count changed '+key);
    for(const key of ['edgeCount','visibleEdgeCount','projectedEdgeCount'])if(mounted[key]!==n*10)throw Error('Edge count changed '+key);
    if(!mounted.rafStopped)throw Error('Unexpected RAF scheduling');
    await page.waitForTimeout(result.method.fixedWaitAfterMountMs);
    const enumerationTime=new Date().toISOString(),info=await browserCdp.send('SystemInfo.getProcessInfo');
    const ids=[...new Set(info.processInfo.map(p=>p.id))];
    if(!ids.length||ids.some(id=>!Number.isSafeInteger(id)||id<=0))throw Error('Invalid CDP OS PID inventory');
    const readStarted=new Date().toISOString();
    const rows=JSON.parse(execFileSync('powershell.exe',['-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',path.join(__dirname,'working-set.ps1')],{input:JSON.stringify(ids),encoding:'utf8',timeout:15000}));
    const byId=new Map(rows.map(r=>[r.pid,r]));
    const processes=info.processInfo.map(p=>({...p,...byId.get(p.id)}));
    const missing=processes.filter(p=>!Number.isSafeInteger(p.workingSetBytes)||p.workingSetBytes<0);
    const totalsByType={};for(const p of processes)if(Number.isSafeInteger(p.workingSetBytes))totalsByType[p.type]=(totalsByType[p.type]||0)+p.workingSetBytes;
    const metrics=Object.fromEntries((await cdp.send('Performance.getMetrics')).metrics.map(m=>[m.name,m.value]));
    const row={side,nodes:n,density:10,repeat,order,attempt,mounted,enumerationTime,readStarted,readFinished:new Date().toISOString(),processes,complete:missing.length===0,missingPids:missing.map(p=>p.id),sumWorkingSetBytes:Object.values(totalsByType).reduce((a,b)=>a+b,0),workingSetBytesByType:totalsByType,heap:{jsHeapUsedBytes:metrics.JSHeapUsedSize,jsHeapTotalBytes:metrics.JSHeapTotalSize}};
    result.samples.push(row);save();console.log(JSON.stringify({side,nodes:n,repeat,order,processes:processes.length,complete:row.complete,sumWorkingSetBytes:row.sumWorkingSetBytes,heapUsedBytes:metrics.JSHeapUsedSize}));
    if(missing.length)throw Object.assign(Error('Process exited or working set missing; sample is incomplete.'),{retryable:true});
    await context.close();
  }finally{await browser.close()}
}
const quant=(a,p)=>a.slice().sort((x,y)=>x-y)[Math.max(0,Math.ceil(a.length*p)-1)];
async function main(){
  await new Promise(r=>server.listen(0,'127.0.0.1',r));const base='http://127.0.0.1:'+server.address().port;
  try{
    let order=0;
    result.method.maxFreshAttemptsPerSample=3;
    for(const n of result.method.nodes)for(let repeat=1;repeat<=3;repeat++)for(const side of repeat===2?['after','before']:['before','after']){
      for(let attempt=1;attempt<=3;attempt++){
        try{await sample(base,side,n,repeat,++order,attempt);break}
        catch(e){if(!e.retryable||attempt===3)throw e;console.log('INCOMPLETE retained; retrying same logical sample with fresh browser')}
      }
    }
    result.summary=result.method.nodes.map(nodes=>({nodes,density:10,...Object.fromEntries(['before','after'].map(side=>{const rows=result.samples.filter(r=>r.complete&&r.nodes===nodes&&r.side===side),values=rows.map(r=>r.sumWorkingSetBytes);return [side,{samples:rows.length,workingSetBytesP50:quant(values,.5),workingSetBytesP95:quant(values,.95),heapUsedBytesP50:quant(rows.map(r=>r.heap.jsHeapUsedBytes),.5)}]}))}));
    result.finished=new Date().toISOString();save();
    if(result.errors.length||result.externalRequests.length)throw Error('Page errors or external requests; inspect raw result.');
    console.log('COMPLETE '+output);
  }finally{await new Promise(r=>server.close(r))}
}
main().catch(e=>{result.fatal=e.stack;save();console.error(e);server.close();process.exitCode=1});
