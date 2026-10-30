// ---------------- pesquisa

$$(".seg button").forEach(b=>b.onclick=()=>{$$(".seg button").forEach(x=>x.classList.toggle("on",x===b));$("#m-pessoas").hidden=b.dataset.m!=="pessoas";$("#m-texto").hidden=b.dataset.m!=="texto"});

$("#b-limpar-p").onclick=()=>{$("#f-pessoas").reset();$("#r-pessoas").innerHTML="";$("#r-vinc").innerHTML=""};

const EST={confirmado:["st-conf","●","em aberto/vigente"],indeterminado:["st-ind","◐","sem situação"],historico:["st-hist","○","histórico"],negado:["st-neg","–","negado"]};

const estBadge=(e,rot)=>{const x=EST[e];return x?`<span class="badge ${x[0]}" title="interpretação automática — conferir">${x[1]} ${esc(rot?rot+": ":"")}${x[2]}</span>`:""};

let ultimasPessoas=[];

$("#f-pessoas").onsubmit=async e=>{e.preventDefault();const f=new FormData(e.target),q=new URLSearchParams();

 for(const[k,v]of f)if(v.trim()&&!k.endsWith("_sel"))q.set(k,v.trim());

 const sel={mandado:f.get("mandado_sel"),cautelar:f.get("cautelar_sel")};

 for(const[k,v]of Object.entries(sel)){if(v==="tem")q.set(k,"1");else if(v)q.set(k+"_estado",v)}

 if(![...q.keys()].filter(k=>k!=="origem").length){toast("Preencha ao menos um campo ou escolha uma situação");return}

 $("#r-vinc").innerHTML="";$("#r-pessoas").innerHTML=barraHTML(0,true);

 try{const j=await api("/api/pesquisa/pessoas?"+q);

 // filtro de estado exato também no navegador (garante o resultado mesmo se o servidor ignorar o parâmetro)

 let ps=j.pessoas.filter(p=>(!["confirmado","historico","indeterminado","negado"].includes(sel.mandado)||p.mandado_estado===sel.mandado)&&(!["confirmado","historico","indeterminado","negado"].includes(sel.cautelar)||p.cautelar_estado===sel.cautelar));

 ultimasPessoas=ps;

 const cel=(k,v)=>v?String(v).split(" | ").map(x=>`<span class="v" data-k="${k}" data-v="${esc(x)}">${esc(x)}</span>`).join("<br>"):"";

 const antec=p=>{let it=[];try{it=JSON.parse(p.antecedentes_itens||"[]")}catch{}

  const l=it.map(i=>`<div>${estBadge(i.estado,i.tipo==="mandado"?"mandado":"cautelar")}<div class="muted">${esc(i.trecho)}</div></div>`).join("");

  return l+(p.processos?`<div><b>Processos:</b> ${cel("processo",p.processos)}</div>`:"")+(p.bos?`<div><b>BO:</b> ${cel("bo",p.bos)}</div>`:"")+(p.placas||p.veiculos?`<div><b>Veículos:</b> ${cel("placa",p.placas)} ${esc(p.veiculos||"")}</div>`:"")||'<span class="muted">—</span>'};

 let h=j.aviso&&!ps.length?`<div class="aviso">${esc(j.aviso)}</div>`:(!ps.length?'<div class="aviso">Nenhum resultado.</div>':"");

 if(ps.length)h+=`<div class="muted" style="margin-bottom:6px">${ps.length} registro(s). Cada linha é um <b>registro de origem</b>; homônimos não são unidos automaticamente.</div><div class="card" style="padding:4px 10px;overflow:auto"><table><thead><tr><th>Nome</th><th>Mãe / Pai</th><th>CPF / RG</th><th>Telefones</th><th>Endereços</th><th>Empresas / CNPJ</th><th>Antecedentes</th><th>Origem</th></tr></thead><tbody>${ps.map((p,i)=>`<tr>

  <td>${cel("nome",p.nome)}${p.nascimento?`<div class="muted">nasc. ${esc(p.nascimento)}</div>`:""}${p.condicao?`<div class="muted">${esc(p.condicao)}</div>`:""}

   <div class="acoes" style="margin-top:4px"><button class="btn sm" data-vinc="${i}">vínculos</button>${p.texto?`<button class="btn sm" data-ficha="${i}">ficha</button>`:""}</div></td>

  <td>${cel("mae",p.mae)}${p.pai?"<br>"+cel("pai",p.pai):""}</td>

  <td>${cel("cpf",p.cpf)}${p.rg?"<br>"+cel("rg",p.rg):""}</td><td>${cel("telefone",p.telefones)}</td><td>${cel("endereco",p.enderecos)}</td><td>${cel("empresa",p.empresas)}${p.cnpj?"<br>"+cel("cnpj",p.cnpj):""}</td>

  <td style="min-width:200px">${antec(p)}</td>

  <td>${p.origem==="caso"?`<a class="lk" data-caso="${esc(p.fonte)}">${esc(p.fonte)}</a>`:`<span class="badge">consulta</span> ${esc(p.fonte)}`}<div class="muted">${esc(p.localizador||"")}</div></td></tr>`).join("")}</tbody></table></div>`;

 if(j.ocorrencias.length)h+=`<div class="card" style="margin-top:10px"><h4>Ocorrências nos autos</h4><table><tbody>${j.ocorrencias.map(o=>`<tr><td><a class="lk" data-caso="${esc(o.caso)}">${esc(o.caso)}</a></td><td>${esc(o.tipo)}</td><td>${esc(o.valor)}</td><td>pág. ${esc(o.pagina??"—")}</td></tr>`).join("")}</tbody></table></div>`;

 $("#r-pessoas").innerHTML=h;

 $$("#r-pessoas .v").forEach(s=>s.onclick=()=>{const f=$("#f-pessoas");f.reset();f[s.dataset.k].value=s.dataset.v;f.requestSubmit()});

 $$("#r-pessoas [data-caso]").forEach(a=>a.onclick=()=>{abrirAba("casos");abrirCaso(a.dataset.caso)});

 $$("#r-pessoas [data-vinc]").forEach(b=>b.onclick=()=>{const p=ultimasPessoas[+b.dataset.vinc];verVinculos("PESSOA",p.no_id,p.nome||p.cpf)});

 $$("#r-pessoas [data-ficha]").forEach(b=>b.onclick=()=>{const p=ultimasPessoas[+b.dataset.ficha];

  $("#r-vinc").innerHTML=`<div class="card"><div style="display:flex;justify-content:space-between"><h4>Ficha de origem — ${esc(p.nome||"")}</h4><button class="btn sm" id="b-fecha-v">fechar</button></div><div class="muted">${esc(p.fonte)} · ${esc(p.localizador||"")}</div><pre class="res tx" style="white-space:pre-wrap;font:inherit">${esc(p.texto)}</pre></div>`;

  $("#b-fecha-v").onclick=()=>$("#r-vinc").innerHTML="";$("#r-vinc").scrollIntoView({behavior:"smooth"})})

  }catch(x){$("#r-pessoas").innerHTML=`<div class="aviso alerta">${esc(x.message)}</div>`}};

let tpPesq;

$$("#f-pessoas input, #f-pessoas select").forEach(el=>{

 el.addEventListener("input", ()=>{

  clearTimeout(tpPesq);

  tpPesq=setTimeout(()=>{

   const f=$("#f-pessoas");let tem=false;

   for(const [k,v] of new FormData(f)){if(v.trim()&&!k.endsWith("_sel")&&k!=="origem"){tem=true;break}}

   if(tem)f.requestSubmit();

  },400);

 });

});

const TIPO_NOME={PESSOA:"Registro de pessoa",NOME:"Nome (homônimos possíveis)",CPF:"CPF",RG:"RG",TELEFONE:"Telefone",PLACA:"Veículo (placa)",CNPJ:"CNPJ",EMPRESA:"Empresa",EMAIL:"E-mail",ENDERECO:"Endereço",PROCESSO:"Processo/IP/TC",BO:"BO",CONTA:"Conta bancária",CHAVE_PIX:"Chave Pix",CASO:"Caso (O.S.)"};

let pilhaV=[];

async function verVinculos(tipo,valor,rotulo,voltar){if(!valor){toast("Registro sem identificação");return}

 if(!voltar)pilhaV.push([tipo,valor,rotulo]);$("#r-vinc").innerHTML=barraHTML(0,true);

 try{const g=await api(`/api/vinculos?tipo=${enc(tipo)}&valor=${enc(valor)}&niveis=2`);

  const rot=Object.fromEntries(g.nos.map(n=>[n.tipo+"|"+n.valor,n.rotulo||n.valor]));

  const grupos={};g.nos.filter(n=>n.nivel>0).forEach(n=>(grupos[n.tipo]=grupos[n.tipo]||[]).push(n));

  let h=`<div class="card"><div style="display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap"><h4 style="margin:0">Vínculos de ${esc(TIPO_NOME[tipo]||tipo)}: ${esc(rotulo||valor)}</h4>

   <span>${pilhaV.length>1?'<button class="btn sm" id="b-volta-v">voltar</button> ':""}<button class="btn sm" id="b-fecha-v">fechar</button></span></div>

   <p class="muted">Até 2 níveis. Ligações por <b>nome</b> são apenas candidatas (homônimos possíveis) e não são seguidas adiante. Conexões são indícios a verificar nos originais. Clique num item para navegar.</p>`;

  if(!g.nos.length||!Object.keys(grupos).length)h+='<div class="vazio">Nenhum vínculo encontrado.</div>';

  h+=`<div class="g3">${Object.entries(grupos).map(([t,ns])=>`<div><h4>${esc(TIPO_NOME[t]||t)} (${ns.length})</h4>${ns.slice(0,40).map(n=>`<div><a class="lk" data-nt="${esc(n.tipo)}" data-nv="${esc(n.valor)}" data-nr="${esc(n.rotulo||n.valor)}">${esc(n.rotulo||n.valor)}</a>${n.nivel>1?' <span class="muted">(2º nível)</span>':""}</div>`).join("")}</div>`).join("")}</div>`;

  if(g.arestas.length)h+=`<details style="margin-top:10px"><summary>Ligações e fontes (${g.arestas.length})</summary><table><tbody>${g.arestas.slice(0,300).map(a=>`<tr><td>${esc(rot[a.a_tipo+"|"+a.a_valor]||a.a_valor)}</td><td class="muted">${esc(a.relacao)}</td><td>${esc(rot[a.b_tipo+"|"+a.b_valor]||a.b_valor)}</td><td class="muted">${grEvidenciasHTML(a)}</td></tr>`).join("")}</tbody></table></details>`;

  if(g.truncado===true||g.completude==="nao_aferida")h+='<div class="aviso">Resultado parcial ou completude não aferida. Refine a busca e confira os limites antes de concluir.</div>';
  if(g.arestas.length>300)h+=`<div class="aviso">Mostrando 300 de ${g.arestas.length} relações recebidas; refine a busca.</div>`;
  $("#r-vinc").innerHTML=h+"</div>";

  $$("#r-vinc [data-nt]").forEach(a=>a.onclick=()=>a.dataset.nt==="CASO"?(abrirAba("casos"),abrirCaso(a.dataset.nv)):verVinculos(a.dataset.nt,a.dataset.nv,a.dataset.nr));

  $("#b-fecha-v").onclick=()=>{$("#r-vinc").innerHTML="";pilhaV=[]};

  if($("#b-volta-v"))$("#b-volta-v").onclick=()=>{pilhaV.pop();const a=pilhaV[pilhaV.length-1];verVinculos(a[0],a[1],a[2],true)};

  $("#r-vinc").scrollIntoView({behavior:"smooth"})}catch(x){$("#r-vinc").innerHTML=`<div class="aviso alerta">${esc(x.message)}</div>`}}

// Protocolo de marcação: a busca devolve `trecho` sem marcador nenhum e `marcas` com os
// intervalos [inicio,fim) a destacar, em unidade UTF-16. Nada no texto é lido como marcador —
// colchete vindo dos autos ("[dígito incerto]", "[PESQUISAR: CNPJ]", regras 3 e 17) é conteúdo,
// não termo casado. Marca malformada derruba só o destaque: o texto segue escapado e inteiro.
function trechoHTML(r){
 const t=String(r&&r.trecho!=null?r.trecho:""),m=Array.isArray(r&&r.marcas)?r.marcas:[];
 let fim=0,h="";
 for(const par of m){
  if(!Array.isArray(par)||par.length!==2)return esc(t);
  const i=par[0],j=par[1];
  if(!Number.isInteger(i)||!Number.isInteger(j)||i<fim||j<=i||j>t.length)return esc(t);
  h+=esc(t.slice(fim,i))+"<mark>"+esc(t.slice(i,j))+"</mark>";fim=j;
 }
 return h+esc(t.slice(fim));
}

$("#f-busca").onsubmit=async e=>{e.preventDefault();const q=$("#q-busca").value.trim();if(!q)return;$("#r-busca").innerHTML=barraHTML(0,true);

 try{const j=await api(`/api/busca?q=${enc(q)}&tipo=${$("#tp-busca").value}`);let h=j.aviso?`<div class="aviso">${esc(j.aviso)}</div>`:"";

 if(j.entidades.length)h+=`<div class="card" style="margin-bottom:12px"><h4>Identificador em ${new Set(j.entidades.map(x=>x.caso)).size} caso(s)</h4><table><tbody>${j.entidades.map(x=>`<tr><td><b>${esc(x.caso)}</b></td><td>${esc(x.tipo)}</td><td>${esc(x.valor)}</td><td>pág. ${esc(x.pagina??"—")}</td></tr>`).join("")}</tbody></table></div>`;

 h+=`<div class="card">${j.trechos.length?j.trechos.map(r=>`<div class="res"><div class="meta"><b>${esc(r.caso||"—")}</b> · ${esc(r.tipo)} · ${r.pagina?"pág. "+r.pagina:esc(r.secao||"")}${r.fls?" · fls. "+esc(r.fls):""} · ${r.caso?`<a class="lk" href="/arquivo/${enc(r.caso)}/${r.arquivo.split(/[\\/]/).slice(2).map(enc).join("/")}" target="_blank">abrir</a>`:esc(r.arquivo)}</div><div class="tx">${trechoHTML(r)}</div></div>`).join(""):'<div class="vazio">Nada encontrado</div>'}</div>`;$("#r-busca").innerHTML=h}catch(x){$("#r-busca").innerHTML=`<div class="aviso">${esc(x.message)}</div>`}};



