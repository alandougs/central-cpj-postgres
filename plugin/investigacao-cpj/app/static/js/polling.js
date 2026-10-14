// Atualização de leitura: uma rodada, dados compartilhados e nenhum comando repetido.
let tc=0,nCiclo=0;
const polling={geracao:0,emCurso:null,leituras:new Map(),erros:0,ativo:false,ocrAtivo:false,pendente:false,observados:new Map()};
function pollingAviso(erro){
 let box=$("#polling-estado");
 if(!box){box=document.createElement("span");box.id="polling-estado";box.className="muted";box.setAttribute("role","status");
  const msg=document.createElement("span");msg.id="polling-aviso";box.append(msg);
  const b=document.createElement("button");b.id="polling-retentar";b.type="button";b.className="btn sm";b.textContent="Tentar novamente";b.onclick=()=>ciclo();box.append(b);
  $("#chip-tarefas").parentElement?.append(box);
 }
 const texto=erro?`Atualização indisponível: ${erro.message||erro}. Últimos dados podem estar desatualizados. `:"";
 const msg=$("#polling-aviso");if(msg&&msg.textContent!==texto)msg.textContent=texto;
 const b=$("#polling-retentar");if(b&&b.hidden!==!erro)b.hidden=!erro;
}
function reiniciarPolling(limpar=false){
 clearTimeout(tc);tc=0;polling.geracao++;polling.leituras.forEach(r=>r.controller.abort());polling.leituras.clear();polling.emCurso=null;
 polling.erros=0;polling.erroAgentes=false;polling.ativo=false;polling.ocrAtivo=false;polling.pendente=false;polling.observados.clear();
 if(limpar){["#ia-painel","#lista-tarefas"].forEach(sel=>{const el=$(sel);if(el){el.innerHTML="";delete el._pollingHTML}});const msg=$("#polling-aviso");if(msg)msg.textContent="";const b=$("#polling-retentar");if(b)b.hidden=true;const chip=$("#chip-tarefas");if(chip)chip.textContent="tarefas: —"}
}
function lerAtualizacao(url){
 if(polling.leituras.has(url))return polling.leituras.get(url).promise;
 const geracao=polling.geracao,login=S.usuario?.login,controller=new AbortController();
 const registro={controller,promise:null};
 const timeout=setTimeout(()=>controller.abort(),12000);
 registro.promise=api(url,{signal:controller.signal}).then(dados=>{
  if(geracao!==polling.geracao||login!==S.usuario?.login)throw new Error("Sessão de atualização encerrada");
  return dados;
 }).catch(e=>{if(controller.signal.aborted&&geracao===polling.geracao&&!document.hidden)throw new Error("Tempo de leitura esgotado");throw e})
 .finally(()=>{clearTimeout(timeout);if(polling.leituras.get(url)===registro)polling.leituras.delete(url)});
 polling.leituras.set(url,registro);return registro.promise;
}
async function consultarTarefas(){const ts=await lerAtualizacao("/api/tarefas");polling.ativo=ts.some(t=>["executando","na_fila"].includes(t.status));if(!polling.emCurso)programarPolling(polling.ativo||polling.ocrAtivo?1600:8000);return ts}
function htmlAtualizado(el,html){
 if(!el||el._pollingHTML===html)return false;
 const abertos=[...el.querySelectorAll("details[open]")].map(d=>d.closest("[data-tarefa]")?.dataset.tarefa);
 el.innerHTML=html;el._pollingHTML=html;
 el.querySelectorAll("details").forEach(d=>{if(abertos.includes(d.closest("[data-tarefa]")?.dataset.tarefa))d.open=true});return true;
}
function etapaTarefa(t){
 const chave=[t.status,t.etapa,t.progresso,t.detalhe].join("|"),anterior=polling.observados.get(t.id),agora=Date.now();
 if(!anterior||anterior.chave!==chave)polling.observados.set(t.id,{chave,desde:agora});
 const parado=anterior&&anterior.chave===chave&&agora-anterior.desde>=60000&&["executando","processando"].includes(t.status);
 return `${t.etapa||t.status||"Estado não informado"}${t.detalhe?" · "+t.detalhe:""}${parado?" · Sem alteração de progresso observada há pelo menos 1 minuto; use Atualizar para consultar.":""}`;
}
function programarPolling(ms){clearTimeout(tc);if(S.usuario&&!document.hidden)tc=setTimeout(ciclo,ms)}
async function ciclo(){
 clearTimeout(tc);tc=0;if(!S.usuario||document.hidden)return;
 if(polling.emCurso)return polling.emCurso;
 const geracao=polling.geracao,login=S.usuario.login; nCiclo++;
 const atual=()=>geracao===polling.geracao&&login===S.usuario?.login&&!document.hidden;
 const rodada=(async()=>{
  try{
   const ts=await consultarTarefas();if(!atual())return;
   await atualizarTarefas(ts);if(!atual())return;
   if($("#nova").classList.contains("on")||$("#inicio").classList.contains("on")||polling.ocrAtivo){const fila=await atualizarFila();if(fila)polling.ocrAtivo=fila.trabalhos.some(t=>["processando","na_fila"].includes(t.status))}
   if(!atual())return;
   if($("#pendencias").classList.contains("on"))await carregarPendencias();
   if(!atual())return;
   if(casoAberto&&$("#casos").classList.contains("on"))await atualizarIA(ts);
   if((nCiclo%3===0||polling.erroAgentes)&&$("#sistema").classList.contains("on"))await carregarAgentes(true);
   if(atual()){polling.erros=0;pollingAviso(null)}
  }catch(e){if(atual()){polling.erros++;pollingAviso(e)}}
  finally{if(atual()){
   polling.emCurso=null;
   const atraso=polling.erros?Math.min(60000,3200*2**Math.min(5,polling.erros-1)):(polling.ativo||polling.ocrAtivo?1600:8000);
   programarPolling(polling.pendente?0:atraso);polling.pendente=false;
  }}
 })();polling.emCurso=rodada;return rodada;
}
function acordarPolling(){if(!S.usuario||document.hidden)return;if(polling.emCurso){polling.pendente=true;return}return ciclo()}
document.addEventListener("visibilitychange",()=>{
 if(document.hidden){reiniciarPolling();return}
 polling.observados.clear();ciclo();
});
