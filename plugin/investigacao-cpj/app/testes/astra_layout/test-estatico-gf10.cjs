// GF10: layout calculado uma vez e exibido parado. Somente dados fictícios; sem rede nem backend.
const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const source=fs.readFileSync(process.argv[2],'utf8');
function fixture(n=20,density=2){const nos=Array.from({length:n},(_,i)=>({tipo:'PESSOA',valor:'P:FICTICIO-'+i,rotulo:'Pessoa fictícia '+i}));return {nos,arestas:nos.flatMap((a,i)=>Array.from({length:density},(_,k)=>({a_tipo:a.tipo,a_valor:a.valor,b_tipo:'PESSOA',b_valor:nos[(i+k+1)%n].valor,relacao:'relação fictícia',evidencias:[{id:'ref-'+i+'-'+k,tipo:'hipotese_manual',documento:null}]}))),casos:[],indice_disponivel:true}}
function setup(){
 const raf=new Map(),listeners={},elements={};let id=0;
 const ctx=new Proxy({measureText:s=>({width:String(s).length*6})},{get:(o,k)=>k in o?o[k]:()=>{},set:(o,k,v)=>(o[k]=v,true)});
 function element(key){return elements[key]||(elements[key]={value:'',checked:true,hidden:false,style:{},innerHTML:'',textContent:'',width:800,height:560,dataset:{},classList:{contains:()=>true},parentElement:{},addEventListener:(event,fn)=>listeners[key+':'+event]=fn,querySelectorAll:()=>[],getBoundingClientRect:()=>({width:800,height:560,left:0,top:0}),getContext:()=>ctx,appendChild(){},setAttribute(){},getAttribute(){return null}})}
 const sandbox={console,Map,Set,Math,JSON,Array,Number,String,Boolean,Object,Date,encodeURIComponent,performance:{now:()=>0},$:element,enc:encodeURIComponent,esc:s=>String(s??''),pode:()=>false,compararNumeroOS:()=>0,api:async()=>fixture(),toast(){},hoje:()=>'',requestAnimationFrame:fn=>{raf.set(++id,fn);return id},cancelAnimationFrame:key=>raf.delete(key),document:{hidden:false,addEventListener:(event,fn)=>listeners['document:'+event]=fn,createElement:()=>element('created')},window:{devicePixelRatio:1,addEventListener:(event,fn)=>listeners['window:'+event]=fn},ResizeObserver:class{constructor(fn){listeners.resize=fn}observe(){}},MutationObserver:class{constructor(fn){listeners.mutation=fn}observe(){}},URL};
 vm.createContext(sandbox);new vm.Script(source,{filename:'grafo-under-test.js'}).runInContext(sandbox);vm.runInContext('grInitEvents()',sandbox);
 return {run:s=>vm.runInContext(s,sandbox),data:d=>{sandbox.input=d;vm.runInContext('grDados=input;grMontarGrafo()',sandbox)},value:s=>JSON.parse(JSON.stringify(vm.runInContext(s,sandbox))),sandbox,raf,listeners,elements,frames(max=50){for(let i=0;i<max&&raf.size;i++){const pending=[...raf];raf.clear();for(const[,fn]of pending)fn()}}};
}
const pos='grNodes.map(n=>[n.id,n.x,n.y])';
const tests=[];function test(name,fn){tests.push([name,fn])}
test('layout is settled before the first frame and frames never move nodes',()=>{
 const f=setup();f.data(fixture());assert.equal(f.value('grSimulando'),false);assert.ok(['estavel','limite'].includes(f.value('grLayoutEstado')));
 const antes=f.value(pos);f.frames();assert.equal(f.raf.size,0);assert.deepEqual(f.value(pos),antes);
 assert.ok(f.value('grTickPhysics()')<.04,'layout should already be at rest');
});
test('settled layout is deterministic regardless of input order',()=>{
 const a=setup(),b=setup(),d=fixture();a.data(d);b.data({...d,nos:d.nos.slice().reverse(),arestas:d.arestas.slice().reverse()});assert.deepEqual(a.value(pos),b.value(pos));
});
test('dragging one node moves only that node',()=>{
 const f=setup();f.data(fixture());f.frames();f.run('grZoom=1;grPanX=0;grPanY=0;grInvalidarEspaco()');
 const antes=new Map(f.value(pos).map(([id,x,y])=>[id,[x,y]])),alvo=f.value('[grNodes[0].id,grNodes[0].x,grNodes[0].y]');
 f.listeners['#cv-grafo:mousedown']({clientX:alvo[1],clientY:alvo[2]});
 for(let i=1;i<=10;i++)f.listeners['window:mousemove']({clientX:alvo[1]+6*i,clientY:alvo[2]+4*i});
 f.listeners['window:mouseup']({clientX:alvo[1]+60,clientY:alvo[2]+40});f.frames();
 assert.equal(f.value('grSimulando'),false);assert.equal(f.raf.size,0);
 for(const[id,x,y]of f.value(pos)){if(id===alvo[0])assert.deepEqual([x,y],[alvo[1]+60,alvo[2]+40]);else assert.deepEqual([x,y],antes.get(id),id)}
});
test('toggling a category filter does not move visible nodes',()=>{
 const f=setup();f.data(fixture());f.frames();const antes=f.value(pos);
 f.elements['#gf-pessoa'].checked=false;f.elements['#gf-pessoa'].onchange();f.frames();
 f.elements['#gf-pessoa'].checked=true;f.elements['#gf-pessoa'].onchange();f.frames();
 assert.equal(f.value('grSimulando'),false);assert.deepEqual(f.value(pos),antes);
});
test('large layout is computed in frame slices without drawing intermediate positions',()=>{
 const f=setup();let t=0;f.sandbox.performance={now:()=>t+=5};f.data(fixture(60,2));
 assert.equal(f.value('grLayoutEstado'),'organizando');assert.equal(f.value('grSimulando'),true);
 f.run('grDesenhar()');assert.equal(f.elements['#gr-status'].textContent,'Organizando o grafo…');
 f.frames(1000);assert.equal(f.raf.size,0);assert.equal(f.value('grSimulando'),false);
 assert.ok(['estavel','limite'].includes(f.value('grLayoutEstado')));assert.equal(f.value('grNodes.filter(n=>n.fixo).length'),0);
 assert.notEqual(f.elements['#gr-status'].textContent,'Organizando o grafo…');
 const antes=f.value(pos);f.run('grPedirDesenho()');f.frames();assert.deepEqual(f.value(pos),antes);
});
test('reloading while organizing releases temporary pins',()=>{
 const f=setup();let t=0;f.sandbox.performance={now:()=>t+=5};const d=fixture(60,2);f.data(d);
 assert.equal(f.value('grSimulando'),true);d.nos.push({tipo:'CPF',valor:'FICTICIO-NOVO'});f.data(d);f.frames(1000);
 assert.equal(f.value('grSimulando'),false);assert.equal(f.value('grNodes.filter(n=>n.fixo).length'),0);
});
test('first load fits the settled layout into the view',()=>{
 const f=setup();f.data(fixture());const r=f.value('(()=>{const xs=grNodes.map(n=>n.x*grZoom+grPanX),ys=grNodes.map(n=>n.y*grZoom+grPanY);return[Math.min(...xs),Math.max(...xs),Math.min(...ys),Math.max(...ys)]})()');
 assert.ok(r[0]>=0&&r[1]<=800&&r[2]>=0&&r[3]<=560,JSON.stringify(r));
});
(async()=>{let failed=0;for(const[name,fn]of tests){try{await fn();console.log('PASS '+name)}catch(e){failed++;console.log('FAIL '+name+'\n'+e.stack)}}console.log(JSON.stringify({tests:tests.length,failed,data:'synthetic-only'}));process.exitCode=failed?1:0})();
