// Correctness only. No timing benchmark and no operational data/backend.
const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const source=fs.readFileSync(process.argv[2]||path.join(__dirname,'grafo-draft.js'),'utf8');
function fixture(n=20,density=2){const nos=Array.from({length:n},(_,i)=>({tipo:'PESSOA',valor:'P:FICTICIO-'+i,rotulo:'Pessoa fictícia '+i}));return {nos,arestas:nos.flatMap((a,i)=>Array.from({length:density},(_,k)=>({a_tipo:a.tipo,a_valor:a.valor,b_tipo:'PESSOA',b_valor:nos[(i+k+1)%n].valor,relacao:'relação fictícia',evidencias:[{id:'ref-'+i+'-'+k,tipo:'hipotese_manual',documento:null}]}))),casos:[],indice_disponivel:true}}
function setup(){
 const calls=[],raf=new Map(),listeners={},elements={};let id=0;
 const ctx=new Proxy({measureText:s=>({width:String(s).length*6})},{get:(o,k)=>k in o?o[k]:(...args)=>calls.push([k,...args]),set:(o,k,v)=>(o[k]=v,true)});
 function element(key){return elements[key]||(elements[key]={value:'',checked:true,hidden:false,style:{},innerHTML:'',textContent:'',width:800,height:560,dataset:{},classList:{contains:()=>true},parentElement:{},addEventListener:(event,fn)=>listeners[key+':'+event]=fn,querySelectorAll:()=>[],getBoundingClientRect:()=>({width:800,height:560,left:10,top:20}),getContext:()=>ctx,appendChild(){},setAttribute(){},getAttribute(){return null}})}
 const sandbox={console,Map,Set,Math,JSON,Array,Number,String,Boolean,Object,Date,encodeURIComponent,performance:{now:()=>0},$:element,enc:encodeURIComponent,esc:s=>String(s??''),pode:()=>false,compararNumeroOS:()=>0,api:async()=>fixture(),toast(){},hoje:()=>'',requestAnimationFrame:fn=>{raf.set(++id,fn);return id},cancelAnimationFrame:key=>raf.delete(key),document:{hidden:false,addEventListener:(event,fn)=>listeners['document:'+event]=fn,createElement:()=>element('created')},window:{devicePixelRatio:1,addEventListener:(event,fn)=>listeners['window:'+event]=fn},ResizeObserver:class{constructor(fn){listeners.resize=fn}observe(){}},MutationObserver:class{constructor(fn){listeners.mutation=fn}observe(){}},URL};
 vm.createContext(sandbox);new vm.Script(source,{filename:'grafo-under-test.js'}).runInContext(sandbox);vm.runInContext('grInitEvents()',sandbox);
 return {run:s=>vm.runInContext(s,sandbox),data:d=>{sandbox.input=d;vm.runInContext('grDados=input;grMontarGrafo()',sandbox)},value:s=>JSON.parse(JSON.stringify(vm.runInContext(s,sandbox))),calls,raf,listeners,elements,sandbox,frame(){const pending=[...raf];raf.clear();for(const[,fn]of pending)fn()}};
}
const tests=[];function test(name,fn){tests.push([name,fn])}
test('seed and fixed ticks independent of input order',()=>{const a=setup(),b=setup(),data=fixture();a.data(data);b.data({...data,nos:data.nos.slice().reverse(),arestas:data.arestas.slice().reverse()});a.run('for(let i=0;i<20;i++)grTickPhysics()');b.run('for(let i=0;i<20;i++)grTickPhysics()');assert.deepEqual(a.value('grNodes.map(n=>[n.id,n.x,n.y])'),b.value('grNodes.map(n=>[n.id,n.x,n.y])'))});
test('identical refresh keeps camera, selection, position and all evidence metadata',async()=>{const f=setup();f.data(fixture());f.run('grZoom=2;grPanX=123;grPanY=-456;grInspecionarNo(grNodes[4]);grNodes[4].x=999;grNodes[4].fixo=true');const id=f.value('grSelectedNode.id');f.sandbox.input=fixture();await f.run('api=async()=>input;carregarGrafo()');assert.equal(f.value('grSelectedNode.id'),id);assert.deepEqual(f.value('[grZoom,grPanX,grPanY]'),[2,123,-456]);assert.equal(f.value('grSelectedNode.x'),999);assert.equal(f.value('grEdges[0].evidencias[0].id'),'ref-0-0')});
test('new node does not move existing seed or reset camera',()=>{const f=setup();f.data(fixture());const before=f.value('grNodes.map(n=>[n.id,n.x,n.y])');f.run('grZoom=2;grPanX=37;grPanY=18');const d=fixture();d.nos.push({tipo:'CPF',valor:'FICTICIO-NOVO'});f.data(d);for(const[id,x,y]of before){const n=f.value(`grNodeMap.get(${JSON.stringify(id)})`);assert.equal(n.x,x);assert.equal(n.y,y)}assert.deepEqual(f.value('[grZoom,grPanX,grPanY]'),[2,37,18])});
test('grid physics agrees with reference including cutoff and negative cells',()=>{const f=setup();f.data(fixture(14,2));f.run(`grNodes.forEach((n,i)=>{n.x=[-800,-400,-.001,0,1,399.999,400,400.001,799.9,800,1200,0,0,0][i];n.y=i<11?0:[0,500,-500][i-11];n.vx=0;n.vy=0});globalThis.ref=grNodes.map(n=>({...n}));`);
 const ref=f.value('ref'),edges=f.value('grEdges.map(e=>[e.source.id,e.target.id])');const m=new Map(ref.map(n=>[n.id,n]));for(const n of ref){n.vx+=(400-n.x)*.0025;n.vy+=(280-n.y)*.0025}for(let i=0;i<ref.length;i++)for(let j=i+1;j<ref.length;j++){const a=ref[i],b=ref[j],dx=b.x-a.x,dy=b.y-a.y,s=Math.max(1,dx*dx+dy*dy);if(s>160000)continue;const d=Math.sqrt(s),fx=dx/d*3000/s,fy=dy/d*3000/s;a.vx-=fx;a.vy-=fy;b.vx+=fx;b.vy+=fy}for(const[aId,bId]of edges){const a=m.get(aId),b=m.get(bId),dx=b.x-a.x,dy=b.y-a.y,d=Math.hypot(dx,dy)||1,k=(d-((a.r+b.r)*3+45))*.035,fx=dx/d*k,fy=dy/d*k;a.vx+=fx;a.vy+=fy;b.vx-=fx;b.vy-=fy}for(const n of ref){n.vx*=.84;n.vy*=.84;n.x+=n.vx;n.y+=n.vy}f.run('grTickPhysics()');const actual=f.value('grNodes');for(let i=0;i<ref.length;i++)for(const k of['x','y','vx','vy'])assert.ok(Math.abs(actual[i][k]-ref[i][k])<1e-9,`${i} ${k}: ${actual[i][k]} != ${ref[i][k]}`)});
test('pinned nodes remain after physics and fit',()=>{const f=setup();f.data(fixture());f.run('grNodes[2].fixo=true;grNodes[2].x=111;grNodes[2].y=-222;for(let i=0;i<100;i++)grTickPhysics();grResetView()');assert.deepEqual(f.value('[grNodes[2].x,grNodes[2].y]'),[111,-222])});
test('hit grid matches reverse linear topmost at borders and after movement',()=>{const f=setup();f.data(fixture(100,2));f.run('grNodes.forEach((n,i)=>{n.x=(i%10)*64;n.y=Math.floor(i/10)*64});grInvalidarEspaco()');for(const[x,y]of[[0,0],[64,64],[63,65],[600,600],[-5,0],[640,640]]){const expected=f.value(`(()=>{for(let i=grNodes.length-1;i>=0;i--){const n=grNodes[i];if((n.x-(${x}))**2+(n.y-(${y}))**2<=(n.r+5)**2)return n.id}return null})()`);assert.equal(f.value(`grFindNodeAt(${x},${y})?.id||null`),expected)}f.run('grNodes[99].x=0;grNodes[99].y=0;grInvalidarEspaco()');assert.equal(f.value('grFindNodeAt(0,0).id'),f.value('grNodes[99].id'))});
test('CSS coordinates transform correctly at multiple DPRs',()=>{const f=setup();f.data(fixture());for(const dpr of[1,2])for(const z of[.2,1,4]){f.sandbox.window.devicePixelRatio=dpr;f.run(`grZoom=${z};grPanX=37;grPanY=-18`);const p=f.value(`grScreenToWorld(${10+37+100*z},${20-18+200*z})`);assert.ok(Math.abs(p.x-100)<1e-9);assert.ok(Math.abs(p.y-200)<1e-9)}});
test('hidden tabs pause RAF and resume at most one loop',()=>{const f=setup();f.data(fixture());assert.equal(f.raf.size,1);f.sandbox.document.hidden=true;f.listeners['document:visibilitychange']();assert.equal(f.raf.size,0);f.run('grStartLoop();grStartLoop()');assert.equal(f.raf.size,0);f.sandbox.document.hidden=false;f.listeners['document:visibilitychange']();f.run('grStartLoop();grStartLoop()');assert.equal(f.raf.size,1);f.elements['#grafo'].classList.contains=()=>false;f.listeners.mutation();assert.equal(f.raf.size,0)});
test('drag persists and event redraws are coalesced',()=>{const f=setup();f.data(fixture());f.run('grEnergy=0;grSimulando=false;grAnimId&&cancelAnimationFrame(grAnimId);grAnimId=null;grZoom=1;grPanX=0;grPanY=0');const p=f.value('[grNodes[0].x,grNodes[0].y]');f.listeners['#cv-grafo:mousedown']({clientX:p[0]+10,clientY:p[1]+20});const calls=f.calls.length;for(let i=0;i<10;i++)f.listeners['window:mousemove']({clientX:120+i,clientY:240+i});assert.equal(f.calls.length,calls);assert.equal(f.raf.size,1);f.listeners['window:mouseup']({clientX:129,clientY:249});assert.equal(f.value('grNodes[0].fixo'),true);assert.deepEqual(f.value('[grNodes[0].x,grNodes[0].y]'),[119,229])});
test('a stable layout ends and interaction does not refit it',()=>{const f=setup();f.data(fixture(1,0));f.run('grNodes[0].x=400;grNodes[0].y=280;grNodes[0].vx=0;grNodes[0].vy=0;grZoom=2;grPanX=100;grPanY=120;grAjustarAoEstabilizar=false');for(let i=0;i<30&&f.raf.size;i++)f.frame();assert.equal(f.raf.size,0);assert.deepEqual(f.value('[grZoom,grPanX,grPanY]'),[2,100,120]);assert.equal(f.value('grLayoutEstado'),'estavel')});
test('filtered nodes cannot be hit and metadata survives filter toggles',()=>{const f=setup();f.data(fixture());const point=f.value('[grNodes[0].x,grNodes[0].y]');f.elements['#gf-pessoa'].checked=false;assert.equal(f.value(`grFindNodeAt(${point[0]},${point[1]})`),null);f.elements['#gf-pessoa'].checked=true;assert.ok(f.value(`grFindNodeAt(${point[0]},${point[1]})`));assert.equal(f.value('grEdges[0].evidencias.length'),1)});
test('expanded drawing retains every node, edge and arrow; label reduction has explicit full-detail ablation',()=>{
  const f=setup();f.data(fixture(50,10));f.run('grZoom=1;grPanX=0;grPanY=0');f.calls.length=0;f.run('grDesenhar()');
  assert.equal(f.calls.filter(x=>x[0]==='arc').length,50);assert.equal(f.calls.filter(x=>x[0]==='lineTo').length,1500);
  assert.equal(f.calls.filter(x=>x[0]==='fillText').length,50);f.calls.length=0;f.run('grDesenhar({detalheCompleto:true})');
  assert.equal(f.calls.filter(x=>x[0]==='fillText').length,550);assert.equal(f.value('grEdges.length'),500);
});
test('culling retains segments crossing viewport with offscreen endpoints',()=>{
  const f=setup();f.data(fixture(2,1));f.run('grZoom=1;grPanX=0;grPanY=0;grNodes[0].x=-100;grNodes[0].y=280;grNodes[1].x=900;grNodes[1].y=280');
  f.calls.length=0;f.run('grDesenhar()');assert.equal(f.calls.filter(x=>x[0]==='arc').length,0);assert.equal(f.calls.filter(x=>x[0]==='lineTo').length,6);
});
test('resize changes backing canvas without resetting camera, position or physics centre',()=>{
  const f=setup();f.data(fixture());f.run('grZoom=2;grPanX=40;grPanY=50');const before=f.value('grNodes.map(n=>[n.x,n.y])');
  f.elements['#cv-grafo'].getBoundingClientRect=()=>({width:600,height:400,left:10,top:20});f.sandbox.window.devicePixelRatio=2;f.listeners.resize();
  assert.deepEqual(f.value('[grZoom,grPanX,grPanY]'),[2,40,50]);assert.deepEqual(f.value('grNodes.map(n=>[n.x,n.y])'),before);
  assert.deepEqual(f.value('[grCentro.x,grCentro.y]'),[400,280]);assert.deepEqual(f.value('[$("#cv-grafo").width,$("#cv-grafo").height]'),[1200,800]);
});
test('root11 edge click and relation ID survive reordered refresh with sources intact',async()=>{
  const f=setup(),data=fixture(2,1);data.arestas.forEach((e,i)=>e.relacao_id='rel-ficticia-'+i);f.data(data);
  f.run('grZoom=1;grPanX=0;grPanY=0;grAjustarAoEstabilizar=false;grNodes[0].x=120;grNodes[0].y=180;grNodes[1].x=420;grNodes[1].y=180;grInvalidarEspaco()');
  f.listeners['#cv-grafo:mousedown']({clientX:280,clientY:200});f.listeners['window:mouseup']({clientX:280,clientY:200});
  const id=f.value('grSelectedEdge.relacao_id');assert.ok(id);assert.equal(f.value('grSelectedNode'),null);
  const positions=f.value('grNodes.map(n=>[n.id,n.x,n.y])');f.sandbox.input={...data,nos:data.nos.slice().reverse(),arestas:data.arestas.slice().reverse()};
  await f.run('api=async()=>input;carregarGrafo()');
  assert.equal(f.value('grSelectedEdge.relacao_id'),id);assert.deepEqual(f.value('grNodes.map(n=>[n.id,n.x,n.y])'),positions);
  assert.deepEqual(f.value('[grZoom,grPanX,grPanY]'),[1,0,0]);assert.equal(f.value('grSelectedEdge.evidencias[0].tipo'),'hipotese_manual');
  assert.ok(f.value('$("#gr-detalhes-conteudo").innerHTML').includes('relação fictícia'));
});
test('visual grouping keeps members, relations and sources and expands without merging identities',()=>{
  const f=setup(),data=fixture(100,2);data.arestas.forEach((e,i)=>e.relacao_id='rel-ficticia-'+i);f.data(data);
  f.run('grZoom=.5;grNodes.forEach((n,i)=>{n.x=100+i%10;n.y=100+Math.floor(i/10)});grInvalidarEspaco();grMostrarAgrupamento(true)');
  assert.equal(f.value('grNodes.length'),100);assert.equal(f.value('grEdges.length'),200);
  assert.equal(f.value('grProjetar().nos.length'),1);assert.equal(f.value('grProjetar().nos[0].membros.length'),100);
  assert.equal(f.value('grProjetar().nos[0].relacoes.length'),200);
  f.run('grInspecionarGrupo(grProjetar().nos[0])');assert.ok(f.value('$("#gr-detalhes-conteudo").innerHTML').includes('100 membros'));
  f.run('grExpandirGrupo(grProjetar().nos[0])');assert.equal(f.value('grProjetar().nos.length'),100);
  assert.equal(f.value('grProjetar().arestas.length'),200);assert.equal(f.value('grEdges.flatMap(e=>e.evidencias).length'),200);
  f.run('grMostrarAgrupamento(false)');assert.equal(f.value('grProjetar().nos.length'),100);
});
test('explicitly focused member stays individually visible inside a grouped graph',()=>{
  const f=setup();f.data(fixture(30,2));f.run('grZoom=.5;grNodes.forEach(n=>{n.x=100;n.y=100});grInvalidarEspaco();grMostrarAgrupamento(true);grFocarNo(grNodes[0].id)');
  assert.ok(f.value('grProjetar().nos.includes(grSelectedNode)'));assert.equal(f.value('grSelectedNode.tipo'),'PESSOA');
  assert.equal(f.value('grFindNodeAt(100,100).id'),f.value('grSelectedNode.id'));
  assert.equal(f.value('grEdges.length'),60);
});
test('public edge inspection exposes both original endpoints in a cached grouped projection',()=>{
  const f=setup();f.data(fixture(30,2));f.run('grZoom=.5;grNodes.forEach(n=>{n.x=100;n.y=100});grInvalidarEspaco();grMostrarAgrupamento(true);grProjetar();grInspecionarAresta(grEdges[0])');
  assert.ok(f.value('grProjetar().nos.includes(grSelectedEdge.source)'));
  assert.ok(f.value('grProjetar().nos.includes(grSelectedEdge.target)'));
  assert.ok(f.value('grProjetar().arestas.includes(grSelectedEdge)'));
  assert.equal(f.value('grSelectedEdge.evidencias[0].tipo'),'hipotese_manual');assert.equal(f.value('grEdges.length'),60);
});
(async()=>{let failed=0;for(const[name,fn]of tests){try{await fn();console.log('PASS '+name)}catch(e){failed++;console.log('FAIL '+name+'\n'+e.stack)}}console.log(JSON.stringify({tests:tests.length,failed,mode:'correctness-only',source:process.argv[2]||'grafo-draft.js'}));process.exitCode=failed?1:0})();
