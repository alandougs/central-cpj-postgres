// Painel único de fluxos por O.S. (contrato cpj-fluxos/1). Leitura de /api/fluxos; ações só por clique do operador.
(function(root,fabrica){
 if(typeof module==="object"&&module.exports)module.exports=fabrica(root);else root.FilaUnificada=fabrica(root);
})(typeof self!=="undefined"?self:this,function(root){
 "use strict";
 const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
 const ESTADOS={na_fila:["b-wait","na fila"],em_execucao:["b-run","em execução"],aguardando_operador:["b-wait","aguardando conferência do operador"],
  falhou:["b-err","falhou"],concluida:["b-ok","concluída"],cancelada:["","cancelada"]};
 const ETAPAS={recebimento:"Recebimento",extracao:"Extração/OCR",analise:"Análise",relatorio:"Relatório",revisao:"Revisão"};
 const FILTROS={"":["Todas",""],atencao:["Exigem atenção","falhou,aguardando_operador"],andamento:["Em andamento","na_fila,em_execucao"]};
 const LIMITE=100;
 const quando=v=>v?esc(String(v).replace("T"," ").slice(0,16)):"—";
 const badge=st=>{const m=ESTADOS[st]||["",st||"—"];return `<span class="badge ${m[0]}"><i aria-hidden="true"></i>${esc(m[1])}</span>`};
 const progressoValido=p=>typeof p==="number"&&Number.isFinite(p)&&p>=0&&p<=100;
 function barra(p){
  if(!progressoValido(p))return '<div class="muted fluxo-sem-prog">progresso não informado</div>';
  const n=Math.round(p);return `<div class="prog" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${n}"><i style="width:${n}%"></i></div>`;
 }
 function pendenciaHTML(p,acao){
  const rotulo={aguardando_operador:"Aguardando conferência do operador",falhou:"Falhou"}[p.tipo]||p.tipo||"Pendência";
  let h=`<li class="fluxo-pend" data-tipo="${esc(p.tipo)}"><b>${esc(rotulo)}</b> · ${esc(ETAPAS[p.etapa]||p.etapa||"")}${p.documento?` · ${esc(p.documento)}`:""}`;
  if(p.detalhe)h+=`<div class="muted">${esc(p.detalhe)}</div>`;
  if(acao)h+=`<form class="fluxo-reconc" data-acao="reconciliar" data-exec="${esc(acao.execucao_id)}" data-etapa="${esc(acao.etapa_id)}" data-versao="${esc(acao.versao)}">`
   +`<label>Resultado conferido <select name="estado" data-foco="e-${esc(acao.etapa_id)}"><option value="na_fila">Não foi executada: liberar para nova solicitação</option><option value="cancelada">Cancelar esta etapa</option></select></label> `
   +`<label>Motivo <input name="motivo" type="text" maxlength="300" minlength="3" required autocomplete="off" data-foco="m-${esc(acao.etapa_id)}"></label> `
   +`<button type="submit" class="btn sm">Registrar conferência</button></form>`;
  return h+"</li>";
 }
 function historicoHTML(d){
  if(!d)return '<div class="muted">Abra para carregar o histórico.</div>';
  if(d.carregando&&!d.etapas.length)return '<div class="muted" role="status">Carregando histórico…</div>';
  let h="";
  if(d.erro)h+=`<div class="muted" role="status">Não foi possível carregar o histórico: ${esc(d.erro)}</div>`;
  if(d.etapas.length)h+='<table class="fluxo-hist-tab"><thead><tr><th>Etapa</th><th>Documento</th><th>Tentativa</th><th>Estado</th><th>Atualizado</th></tr></thead><tbody>'
   +d.etapas.map(e=>`<tr><td>${esc(ETAPAS[e.etapa]||e.etapa)}</td><td>${esc(e.documento||"—")}</td><td class="n">${esc(e.tentativa)}</td><td>${badge(e.estado)}${e.detalhe?`<div class="muted">${esc(e.detalhe)}</div>`:""}</td><td>${quando(e.atualizado_em)}</td></tr>`).join("")+"</tbody></table>";
  else if(!d.erro)h+='<div class="muted">Nenhuma etapa registrada.</div>';
  if(d.proximo_cursor)h+=`<button type="button" class="btn sm" data-acao="mais-historico" data-exec="${esc(d.execucao_id)}"${d.carregando?" disabled":""}>Carregar mais</button>`;
  return h;
 }
 function itemHTML(i,ctx={}){
  const reconc=new Map((i.acoes||[]).filter(a=>a.acao==="reconciliar").map(a=>[a.etapa_id,a]));
  const cancelar=(i.acoes||[]).filter(a=>a.acao==="cancelar");
  const visiveis=(i.pendencias||[]).filter(p=>p.tipo!=="etapa_ausente"),proximas=(i.pendencias||[]).filter(p=>p.tipo==="etapa_ausente");
  const docs=i.documentos||[];
  const id=esc(i.execucao_id),aberto=ctx.abertos?.has(i.execucao_id);
  let h=`<article class="job fluxo" data-os="${esc(i.caso)}" data-exec="${id}" data-estado="${esc(i.estado)}">`
   +`<div class="l1"><b>${esc(i.caso)}</b>${badge(i.estado)}</div>`
   +`<div class="muted">${i.etapa?`Etapa: ${esc(ETAPAS[i.etapa]||i.etapa)} · `:""}atualizado em ${quando(i.atualizado_em)}</div>${barra(i.progresso)}`;
  h+=docs.length?`<div class="fluxo-docs">Documentos (${docs.length}): ${docs.slice(0,6).map(esc).join(", ")}${docs.length>6?` e mais ${docs.length-6}`:""}</div>`:'<div class="muted">Nenhum documento vinculado.</div>';
  if(visiveis.length)h+=`<ul class="fluxo-pends">${visiveis.map(p=>pendenciaHTML(p,p.tipo==="aguardando_operador"?reconc.get(p.etapa_id):null)).join("")}</ul>`;
  if(proximas.length)h+=`<details class="fluxo-prox"><summary>Próximas etapas (${proximas.length})</summary><ul>${proximas.map(p=>`<li>${esc(ETAPAS[p.etapa]||p.etapa)} ainda não iniciada</li>`).join("")}</ul></details>`;
  h+=`<details class="fluxo-hist" data-fluxo="${id}"${aberto?" open":""}><summary>Histórico de documentos e tentativas</summary><div class="fluxo-hist-corpo">${aberto?historicoHTML(ctx.detalhes?.get(i.execucao_id)):""}</div></details>`;
  if(cancelar.length)h+='<div class="fluxo-acoes">'+cancelar.map(a=>`<button type="button" class="btn sm dan" data-acao="cancelar" data-exec="${esc(a.execucao_id)}" data-versao="${esc(a.versao)}"${ctx.ocupados?.has(a.execucao_id)?" disabled":""}>${cancelar.length>1?"Cancelar execução pendente":"Cancelar o que está pendente"}</button>`).join(" ")+"</div>";
  return h+"</article>";
 }
 function listaHTML(dados,ctx={}){
  const itens=dados?.itens||[];
  let h=itens.length?itens.map(i=>itemHTML(i,ctx)).join(""):'<div class="vazio">Nenhum fluxo registrado para as suas O.S.</div>';
  if(dados?.proximo_cursor)h+=`<div class="muted" role="status">Há mais O.S. do que as ${LIMITE} exibidas. Use o filtro para ver apenas as que exigem atenção ou estão em andamento.</div>`;
  return h;
 }

 // ---------------------------------------------------------------- controlador (somente com DOM)
 const estado={seq:0,aplicado:0,login:null,dados:null,filtro:"",detalhes:new Map(),abertos:new Set(),rascunhos:new Map(),ocupados:new Set(),html:null,aviso:"",cfg:null};
 const cfg=()=>estado.cfg||(estado.cfg={
  ler:u=>root.lerAtualizacao(u),api:(u,o)=>root.api(u,o),login:()=>root.S?.usuario?.login??null,
  aviso:t=>root.toast&&root.toast(t),acordar:()=>root.acordarPolling&&root.acordarPolling(),confirmar:t=>root.confirm(t)});
 const el=id=>root.document&&root.document.getElementById(id);
 function urlLista(){const e=FILTROS[estado.filtro][1];return `/api/fluxos?limite=${LIMITE}${e?`&estado=${e}`:""}`}
 function mostrarAviso(t){estado.aviso=t||"";const a=el("fluxos-estado");if(a&&a.textContent!==estado.aviso)a.textContent=estado.aviso}
 function desenhar(){
  const lista=el("fluxos-lista");if(!lista)return false;
  const doc=root.document,foco=doc.activeElement&&lista.contains(doc.activeElement)?doc.activeElement.dataset?.foco||doc.activeElement.dataset?.acao&&`${doc.activeElement.dataset.acao}:${doc.activeElement.dataset.exec}`:null;
  lista.querySelectorAll("input[data-foco]").forEach(i=>{if(i.value)estado.rascunhos.set(i.dataset.foco,i.value);else estado.rascunhos.delete(i.dataset.foco)});
  lista.querySelectorAll("select[data-foco]").forEach(s=>estado.rascunhos.set(s.dataset.foco,s.value));
  const html=listaHTML(estado.dados,estado);
  if(html===estado.html)return false;
  const rolagem=lista.scrollTop;
  lista.innerHTML=html;estado.html=html;
  lista.querySelectorAll("[data-foco]").forEach(c=>{const v=estado.rascunhos.get(c.dataset.foco);if(v!==undefined)c.value=v});
  if(foco){const alvo=[...lista.querySelectorAll("[data-foco],[data-acao]")].find(c=>(c.dataset.foco||`${c.dataset.acao}:${c.dataset.exec}`)===foco);if(alvo)alvo.focus({preventScroll:true})}
  lista.scrollTop=rolagem;return true;
 }
 const referencia=id=>{const i=(estado.dados?.itens||[]).find(x=>x.execucao_id===id);return i?`${i.versao}|${i.atualizado_em}`:""};
 function aplicarLista(dados,seq){
  if(seq<estado.aplicado)return false;      // resposta atrasada: nunca sobrescreve uma mais nova
  estado.aplicado=seq;estado.dados=dados;
  const vivos=new Set((dados.itens||[]).map(i=>i.execucao_id));
  [...estado.abertos].forEach(id=>{if(!vivos.has(id))estado.abertos.delete(id)});     // O.S. saiu do filtro: não mantém detalhe órfão
  [...estado.detalhes.keys()].forEach(id=>{if(!vivos.has(id))estado.detalhes.delete(id)});
  mostrarAviso("");desenhar();
  estado.abertos.forEach(id=>{const d=estado.detalhes.get(id);if(d&&!d.carregando&&d.ref!==referencia(id))carregarHistorico(id,false)});   // histórico aberto acompanha a O.S.
  return true;
 }
 async function atualizarPainel(){
  if(!el("fluxos-lista"))return null;
  const c=cfg(),login=c.login();
  if(estado.login!==login){limpar(false);estado.login=login}
  const meu=++estado.seq;
  let dados;
  try{dados=await c.ler(urlLista())}
  catch(e){if(meu===estado.seq&&login===c.login()&&!(root.document&&root.document.hidden))mostrarAviso(`Fluxos indisponíveis (${e.message||e}). Exibindo os últimos dados recebidos.`);throw e}
  if(login!==c.login()||meu<estado.aplicado)return null;
  return aplicarLista(dados,meu)?dados:null;
 }
 async function carregarHistorico(execId,mais){
  const c=cfg(),login=c.login(),atual=estado.detalhes.get(execId)||{execucao_id:execId,etapas:[],proximo_cursor:null,carregando:false,erro:""};
  if(atual.carregando)return;
  if(mais&&!atual.proximo_cursor)return;
  const refSolicitada=referencia(execId);
  atual.carregando=true;atual.erro="";estado.detalhes.set(execId,atual);desenhar();
  try{
   const d=await c.api(`/api/fluxos/${encodeURIComponent(execId)}?limite=50${mais?`&cursor=${encodeURIComponent(atual.proximo_cursor)}`:""}`);
   if(login!==c.login()||estado.detalhes.get(execId)!==atual)return;
   if(refSolicitada!==referencia(execId))return;     // a O.S. mudou durante a consulta: não aplicar histórico antigo
   atual.etapas=mais?atual.etapas.concat(d.etapas||[]):(d.etapas||[]);atual.proximo_cursor=d.proximo_cursor||null;
   if(!mais)atual.ref=refSolicitada;
  }catch(e){if(estado.detalhes.get(execId)===atual&&login===c.login()){atual.erro=e.message||String(e);atual.ref=referencia(execId)}}
  finally{
   atual.carregando=false;
   if(estado.detalhes.get(execId)===atual){
    desenhar();
    if(!atual.erro&&login===c.login()&&!(root.document&&root.document.hidden)&&estado.abertos.has(execId)&&refSolicitada!==referencia(execId))carregarHistorico(execId,false);
   }
  }
 }
 async function executar(botao,execId,fazer,sucesso){
  const c=cfg();if(estado.ocupados.has(execId))return;
  estado.ocupados.add(execId);botao.disabled=true;
  try{const r=await fazer();c.aviso(sucesso(r))}
  catch(e){c.aviso(e.status===409?"O estado mudou desde a última atualização. Confira o que está exibido e tente de novo.":(e.message||"Falha na operação"))}
  finally{estado.ocupados.delete(execId);estado.html=null;c.acordar();desenhar()}
 }
 function aoClicar(ev){
  const b=ev.target.closest&&ev.target.closest("button[data-acao]");if(!b)return;
  const c=cfg(),id=b.dataset.exec;
  if(b.dataset.acao==="mais-historico"){carregarHistorico(id,true);return}
  if(b.dataset.acao==="cancelar"){
   if(!c.confirmar("Cancelar as etapas ainda pendentes desta O.S.? Etapas já concluídas são preservadas e nada é entregue."))return;
   executar(b,id,()=>c.api(`/api/fluxos/${encodeURIComponent(id)}/cancelar`,{json:{versao:Number(b.dataset.versao)}}),
    r=>`Cancelamento registrado: ${r.canceladas} etapa(s) cancelada(s), ${r.preservadas} preservada(s).`);
  }
 }
 function aoEnviar(ev){
  const f=ev.target.closest&&ev.target.closest("form.fluxo-reconc");if(!f)return;
  ev.preventDefault();
  const c=cfg(),motivo=f.elements.motivo.value.trim(),botao=f.querySelector("button[type=submit]");
  if(motivo.length<3){c.aviso("Informe o motivo conferido (mínimo 3 caracteres).");return}
  estado.rascunhos.delete(`m-${f.dataset.etapa}`);
  executar(botao,f.dataset.exec,()=>c.api(`/api/fluxos/${encodeURIComponent(f.dataset.exec)}/etapas/${encodeURIComponent(f.dataset.etapa)}/reconciliar`,
   {json:{versao:Number(f.dataset.versao),estado:f.elements.estado.value,motivo}}),()=>"Conferência registrada. Nenhuma nova chamada foi disparada.");
 }
 function aoAbrir(ev){
  const d=ev.target;if(!d||!d.classList||!d.classList.contains("fluxo-hist"))return;
  const id=d.dataset.fluxo;
  if(d.open){if(estado.abertos.has(id))return;      // reabertura causada pelo redesenho: nada a carregar
   estado.abertos.add(id);const corpo=d.querySelector(".fluxo-hist-corpo");if(corpo&&!estado.detalhes.has(id))corpo.innerHTML=historicoHTML({carregando:true,etapas:[]});carregarHistorico(id,false)}
  else estado.abertos.delete(id);
  estado.html=null;
 }
 function limpar(tudo=true){
  estado.seq++;estado.aplicado=estado.seq;estado.dados=null;estado.detalhes.clear();estado.abertos.clear();estado.rascunhos.clear();estado.ocupados.clear();estado.html=null;estado.aviso="";
  if(tudo)estado.login=null;
  const l=el("fluxos-lista");if(l)l.innerHTML="";mostrarAviso("");
 }
 function iniciar(configuracao){
  if(configuracao)estado.cfg=Object.assign(cfg(),configuracao);
  const l=el("fluxos-lista");if(!l||l._fluxosLigado)return;l._fluxosLigado=true;
  l.addEventListener("click",aoClicar);l.addEventListener("submit",aoEnviar);l.addEventListener("toggle",aoAbrir,true);
  const f=el("fluxos-filtro");
  if(f){f.innerHTML=Object.entries(FILTROS).map(([k,v])=>`<option value="${k}">${esc(v[0])}</option>`).join("");
   f.addEventListener("change",()=>{estado.filtro=f.value;estado.seq++;estado.aplicado=estado.seq;estado.dados=null;estado.html=null;estado.detalhes.clear();estado.abertos.clear();
    l.innerHTML="";atualizarPainel().catch(()=>{})})}
 }
 function invalidar(){estado.seq++;estado.aplicado=estado.seq}      // aba oculta/leitura abortada: respostas em voo deixam de valer
 const api={invalidar,itemHTML,listaHTML,historicoHTML,barra,badge,esc,aplicarLista,atualizarPainel,limpar,iniciar,_estado:estado};
 if(root.document&&root.document.readyState!=="loading")iniciar();
 else if(root.document)root.document.addEventListener("DOMContentLoaded",()=>iniciar());
 return api;
});
