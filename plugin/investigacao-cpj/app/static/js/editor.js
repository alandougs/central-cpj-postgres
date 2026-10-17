// ---------------- editor de minuta

const META=[["ordem_servico","Ordem de Serviço"],["referencia","Referência"],["natureza","Natureza"],["investigados","Investigado(s)"],["vitimas","Vítima(s)"],["local","Local"],["data_fatos","Data dos fatos"],["local_data","Local e data"],["data_rodape","Data do rodapé"],["delegado","Delegado(a) destinatário(a)"],["delegado_genero","Gênero Delegado(a) (M/F)"],["escrivao","Escrivão(ã) do feito"]];

let edCaso=null,edSessao=0,ed=null,edTimer=null;

function dadosEditor(){const meta={},secoes={};$$("#ed-meta [data-m]").forEach(e=>meta[e.dataset.m]=e.value);$$("#ed-secoes [data-s]").forEach(e=>secoes[e.dataset.s]=e.value);return {meta,secoes}}
function estadoEditor(){if(!ed)return;const estado=ed.salvando?"salvando":ed.conflito?"conflito":ed.erro?"erro":ed.dirty?"dirty":"salvo";
 $("#editor").dataset.estado=estado;$("#ed-salvar").disabled=ed.salvando||ed.carregando||ed.falhaCarga;$("#ed-salvar").textContent=ed.erro||ed.conflito?"Tentar salvar novamente":"Salvar rascunho";
 $("#ed-docx").disabled=ed.salvando||ed.carregando||ed.dirty||!ed.arquivo;$("#ed-comparar").hidden=!ed.conflito;
 $("#ed-tit").textContent=`Minuta — ${edCaso}${ed.arquivo?" (base: "+ed.arquivo+")":" (nova)"}`;
 $("#ed-msg").textContent=ed.falhaCarga?`Erro ao abrir: ${ed.erro}. Feche e tente abrir novamente.`:ed.carregando?"Carregando…":ed.salvando?"Salvando rascunho…":ed.conflito?"Conflito: há outra versão no servidor. Seu texto foi mantido. Compare e concilie antes de salvar novamente.":ed.erro?`Erro: ${ed.erro}. Seu texto foi mantido; tente salvar novamente.`:ed.dirty?"Alterações pendentes de salvamento.":ed.salvo_em?`Rascunho salvo: ${ed.arquivo} · ${ed.salvo_em}`:"Nenhuma alteração pendente.";
}
function fecharEditor() {clearTimeout(edTimer);++edSessao;ed=null;edCaso=null;$("#editor").hidden=true}
function confirmarSaidaEditor(){if(!ed||$("#editor").hidden)return true;if(ed.salvando){toast("Aguarde a confirmação do salvamento antes de sair.");return false}
 if(ed.dirty&&!confirm("Há alterações sem salvamento confirmado. Sair e descartar este texto? Cancele para continuar editando e salvar."))return false;fecharEditor();return true}
function agendarRascunho(){clearTimeout(edTimer);if(ed?.dirty&&!ed.erro&&!ed.conflito)edTimer=setTimeout(salvarRascunho,2000)}
function editarRascunho(){if(!ed||ed.carregando)return;ed.dirty=JSON.stringify(dadosEditor())!==ed.confirmado;estadoEditor();agendarRascunho()}
$("#ed-meta").addEventListener("input",editarRascunho);$("#ed-secoes").addEventListener("input",editarRascunho);

async function abrirEditor(id,arq){if(!confirmarSaidaEditor())return;const sessao=++edSessao;edCaso=id;ed={dirty:false,salvando:false,carregando:true,arquivo:null,versao:0,ultima:null,erro:null,conflito:false,salvo_em:null};
 $("#ed-meta").innerHTML="";$("#ed-secoes").innerHTML="";$("#ed-comparacao").hidden=true;$("#editor").hidden=false;estadoEditor();
 try{const m=await api(`/api/casos/${enc(id)}/minuta${arq?"?arquivo="+enc(arq):""}`);if(sessao!==edSessao)return;
  ed.arquivo=m.arquivo;ed.versao=m.versao_num;ed.ultima=m.ultima;
  $("#ed-meta").innerHTML=META.map(([k,l])=>`<div><label>${l}</label><input data-m="${k}" value="${esc(m.meta[k]||"")}"></div>`).join("");
  $("#ed-secoes").innerHTML=Object.entries(m.secoes).map(([s,t])=>`<div><label><b>${s}</b></label><textarea data-s="${s}" rows="${s==="DILIGÊNCIAS REALIZADAS"?16:7}">${esc(t)}</textarea></div>`).join("");
  ed.confirmado=JSON.stringify(dadosEditor());ed.carregando=false;estadoEditor();
 }catch(x){if(sessao!==edSessao)return;ed.erro=x.message;ed.carregando=false;ed.falhaCarga=true;estadoEditor()}}

async function salvarRascunho(){clearTimeout(edTimer);if(!ed||ed.carregando||ed.salvando||!ed.dirty)return;const sessao=edSessao,id=edCaso,dados=dadosEditor(),texto=JSON.stringify(dados);
 ed.salvando=true;estadoEditor();
 try{const r=await api(`/api/casos/${enc(id)}/minuta`,{json:{...dados,gerar_docx:false,versao_base:ed.versao,ultima_vista:ed.ultima}});if(sessao!==edSessao)return;
  ed.arquivo=r.arquivo;ed.ultima=r.arquivo;ed.versao=r.versao;ed.confirmado=texto;ed.salvo_em=new Date().toLocaleTimeString("pt-BR");ed.erro=null;ed.conflito=false;ed.dirty=JSON.stringify(dadosEditor())!==texto;$("#ed-comparacao").hidden=true;
 }catch(x){if(sessao!==edSessao)return;ed.erro=x.message;ed.conflito=x.status===409;ed.dirty=true;
 }finally{if(sessao===edSessao){ed.salvando=false;estadoEditor();agendarRascunho()}}}
$("#ed-cancelar").onclick=confirmarSaidaEditor;$("#ed-salvar").onclick=salvarRascunho;
$("#ed-docx").onclick=async()=>{if(!ed||ed.dirty||ed.salvando||!ed.arquivo)return;const sessao=edSessao,id=edCaso,arquivo=ed.arquivo;$("#ed-docx").disabled=true;
 try{const r=await api(`/api/casos/${enc(id)}/docx`,{json:{minuta:arquivo}});if(sessao!==edSessao)return;$("#ed-msg").textContent=`DOCX gerado de ${arquivo}: ${r.docx}`;if(casoAberto===id)abrirCaso(id).catch(x=>toast(x.message));
 }catch(x){if(sessao===edSessao)$("#ed-msg").textContent=`Erro ao gerar DOCX: ${x.message}. O rascunho salvo foi preservado.`}finally{if(sessao===edSessao)$("#ed-docx").disabled=ed.dirty||ed.salvando}};
$("#ed-comparar").onclick=async()=>{if(!ed?.conflito)return;const sessao=edSessao;
 try{const m=await api(`/api/casos/${enc(edCaso)}/minuta`);if(sessao!==edSessao)return;ed.comparada=m;
  $("#ed-servidor").value=m.arquivo+"\n\n"+Object.entries(m.meta).map(([k,v])=>`${k}: ${v}`).join("\n")+"\n\n"+Object.entries(m.secoes).map(([s,t])=>`## ${s}\n\n${t}`).join("\n\n");$("#ed-comparacao").hidden=false;
 }catch(x){if(sessao===edSessao)$("#ed-msg").textContent=`Não foi possível comparar: ${x.message}. Seu texto foi mantido.`}};
$("#ed-reconciliar").onclick=()=>{if(!ed?.comparada)return;ed.versao=ed.comparada.versao_num;ed.ultima=ed.comparada.ultima;ed.comparada=null;ed.erro=null;ed.conflito=false;$("#ed-comparacao").hidden=true;estadoEditor()};
window.addEventListener("beforeunload",e=>{if(ed&&(ed.dirty||ed.salvando)){e.preventDefault();e.returnValue=""}});
window.addEventListener("hashchange",()=>{if(S.usuario&&ABAS.some(a=>a[0]===location.hash.slice(1)))abrirAba(location.hash.slice(1))});



