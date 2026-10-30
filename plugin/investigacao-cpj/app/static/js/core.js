

const $=s=>document.querySelector(s), $$=s=>document.querySelectorAll(s);

const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));

const dt=s=>s?esc(String(s).slice(0,10).split("-").reverse().join("/")):"—", kb=n=>n>1048576?(n/1048576).toFixed(1)+" MB":Math.max(1,Math.round(n/1024))+" KB";

const enc=encodeURIComponent, hoje=()=>new Date(Date.now()-new Date().getTimezoneOffset()*6e4).toISOString().slice(0,10);

function toast(t){const e=$("#toast");e.textContent=t;e.style.opacity=1;clearTimeout(e._t);e._t=setTimeout(()=>e.style.opacity=0,3000)}

let S={usuario:null,perms:[]}; const pode=p=>S.perms.includes(p);

async function api(u,o={}){o.headers=Object.assign({"X-CPJ":"1"},o.headers||{});if(o.json!==undefined){o.method=o.method||"POST";o.headers["Content-Type"]="application/json";o.body=JSON.stringify(o.json);delete o.json}

 const r=await fetch(u,o);const j=await r.json().catch(()=>({}));if(r.status===401&&j.login){iniciar();throw new Error(j.erro)}if(r.status===428){mostrarTrocar();throw new Error(j.erro)}if(!r.ok){const err=new Error(j.erro||j.mensagem||r.statusText);err.status=r.status;err.data=j;throw err}return j}

function mostrarTrocar(){["#tela-login","#tela-setup","#app"].forEach(s=>$(s).hidden=true);$("#tela-trocar").hidden=false}

function enviar(u,fd,barra,tx){return new Promise((ok,ko)=>{const x=new XMLHttpRequest();x.open("POST",u);x.setRequestHeader("X-CPJ","1");

 if(barra){barra.hidden=false;barra.firstElementChild.style.width="0"}

 x.upload.onprogress=e=>{if(e.lengthComputable&&barra){barra.firstElementChild.style.width=(100*e.loaded/e.total)+"%";if(tx)tx.textContent=`enviando ${kb(e.loaded)} de ${kb(e.total)}`}};

 x.onload=()=>{let j={};try{j=JSON.parse(x.responseText)}catch{}if(barra)barra.hidden=true;if(tx)tx.textContent="";x.status===200?ok(j):ko(new Error(j.erro||"Falha no envio"))};

 x.onerror=()=>{if(barra)barra.hidden=true;ko(new Error("Falha de conexão"))};x.send(fd)})}

const barraHTML=(p,ind)=>`<div class="prog${ind?" ind":""}"><i style="width:${Math.max(0,Math.min(100,p||0))}%"></i></div>`;

function badge(st){const mapa={processando:["b-run","processando"],executando:["b-run","executando"],na_fila:["b-wait","na fila"],erro:["b-err","erro"],concluido:["b-ok","concluído"],concluida:["b-ok","concluída"],cancelada:["","cancelada"]},m=Object.prototype.hasOwnProperty.call(mapa,st)?mapa[st]:["",st||"—"];return `<span class="badge ${m[0]}"><i aria-hidden="true"></i>${esc(m[1])}</span>`}

function prazoBadge(c){if(!c.prazo)return '<span class="muted">—</span>';const s=c.situacao_prazo,t={vencido:"⛔ vencido",hoje:"⚠ vence hoje",proximo:"⏳ "+dt(c.prazo)}[s];return t?`<span class="badge pz-${s}">${t}</span>`:`<span class="muted">${dt(c.prazo)}</span>`}

function sincronizarTemaPainel(){try{const r=document.documentElement,p=$("#if-painel").contentDocument;if(p)p.documentElement.dataset.theme=r.dataset.theme||(matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light")}catch(e){}}
$("#if-painel").addEventListener("load",sincronizarTemaPainel);
$("#tema").onclick=()=>{const r=document.documentElement,d=r.dataset.theme==="dark"||(!r.dataset.theme&&matchMedia("(prefers-color-scheme: dark)").matches);r.dataset.theme=d?"light":"dark";sincronizarTemaPainel()};



