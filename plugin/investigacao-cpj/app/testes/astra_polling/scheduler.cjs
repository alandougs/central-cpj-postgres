const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
let resolver=null;let now=0,serial=0,timers=new Map(),requests=[],tasks=[],fail=false,hang=false,active='casos',hidden=false,ocr=false;
const listeners={},els=new Map();
const element=()=>({dataset:{},textContent:'',innerHTML:'',className:'',append(){},setAttribute(){},querySelectorAll(){return[]},classList:{contains(v){return v==='on'&&this.owner===active}}});
function $(s){if(!els.has(s)){const el=element();el.classList.owner=s.slice(1);els.set(s,el)}return els.get(s)}
const ctx=vm.createContext({console,AbortController,Promise,Map,Set,WeakMap,JSON,Math,Error,Date:{now:()=>now},performance:{now:()=>now},S:{usuario:{login:'ficticio'}},casoAberto:'OS-FICTICIA',pode:()=>true,$,$$:()=>[],esc:String,document:{get hidden(){return hidden},addEventListener:(e,f)=>listeners[e]=f,createElement:element},setTimeout:(f,ms)=>{const id=++serial;timers.set(id,{f,at:now+ms});return id},clearTimeout:id=>timers.delete(id),api:(u,o={})=>{requests.push({u,at:now,o});if(hang)return new Promise((res,rej)=>{resolver=res;o.signal?.addEventListener('abort',()=>rej(new Error('aborted')))});return fail?Promise.reject(new Error('Falha fictícia')):Promise.resolve(tasks)},atualizarTarefas:async data=>data===undefined?ctx.api('/api/tarefas'):data,atualizarIA:async data=>data===undefined?ctx.api('/api/tarefas'):data,atualizarFila:async()=>({trabalhos:ocr?[{status:'processando'}]:[]}),carregarPendencias:async()=>{},carregarAgentes:async()=>({})});
vm.runInContext(fs.readFileSync(process.argv[2],'utf8'),ctx);
const run=s=>vm.runInContext(s,ctx),flush=async()=>{for(let i=0;i<35;i++)await Promise.resolve()};
async function tick(ms){const target=now+ms;for(;;){const a=[...timers].filter(([,t])=>t.at<=target).sort((a,b)=>a[1].at-b[1].at)[0];if(!a)break;now=a[1].at;timers.delete(a[0]);a[1].f();await flush()}now=target;await flush()}
(async()=>{
 const test=process.argv[3];
 if(test==='intervalos'){
  run('ciclo()');await flush();assert.equal(requests.length,1);await tick(7999);assert.equal(requests.length,1);await tick(1);assert.equal(requests.length,2);
  tasks=[{id:'x',status:'executando'}];run('ciclo()');await flush();const count=requests.length;await tick(1599);assert.equal(requests.length,count);await tick(1);assert.equal(requests.length,count+1);
  tasks=[];active='nova';ocr=true;run('ciclo()');await flush();const n=requests.length;await tick(1600);assert.equal(requests.length,n+1,'OCR ativo mantém intervalo curto');
 }
 if(test==='compartilhar'){
  hang=true;run('ciclo();ciclo()');await flush();assert.equal(requests.length,1);
  run('consultarTarefas().catch(()=>{})');await flush();assert.equal(requests.length,1,'consumidores compartilham GET');
 }
 if(test==='erros'){
  fail=true;run('ciclo()');await flush();let total=1;for(const delay of [3200,6400,12800,25600,51200,60000,60000]){await tick(delay-1);assert.equal(requests.length,total);await tick(1);assert.equal(requests.length,++total)}
  fail=false;await tick(60000);const n=requests.length;await tick(8000);assert.equal(requests.length,n+1);
 }
 if(test==='visibilidade'){
  run('ciclo()');await flush();hidden=true;listeners.visibilitychange();await tick(60000);assert.equal(requests.length,1);
  hidden=false;listeners.visibilitychange();listeners.visibilitychange();await flush();assert.equal(requests.length,2,'retorno coalescido');
  run('reiniciarPolling()');ctx.S.usuario=null;await tick(60000);assert.equal(requests.length,2);
 }
 if(test==='timeout'){
  hang=true;run('ciclo()');await flush();await tick(11999);assert.equal(requests.length,1);await tick(1);assert.ok(requests[0].o.signal.aborted);hang=false;await tick(3200);assert.equal(requests.length,2);assert.ok(requests.every(r=>!r.o.method||r.o.method==='GET'));
 }
 if(test==='sessao'){
  hang=true;run('ciclo()');await flush();run('reiniciarPolling(true)');ctx.S.usuario={login:'outro_ficticio'};hang=false;run('ciclo()');await flush();assert.equal(requests.length,2);assert.equal(run('polling.erros'),0);
 }
 if(test==='etapa'){
  ctx.t={id:'ficticio',status:'executando',etapa:'Analisando',progresso:35};assert.equal(run('etapaTarefa(t)'),'Analisando');now=60001;assert.match(run('etapaTarefa(t)'),/Sem alteração/);assert.doesNotMatch(run('etapaTarefa(t)'),/interromp|caiu/);
  hidden=true;listeners.visibilitychange();hidden=false;listeners.visibilitychange();await flush();assert.doesNotMatch(run('etapaTarefa(t)'),/Sem alteração/);
 }
 console.log(test+' OK');
})().catch(e=>{console.error(e);process.exitCode=1});
