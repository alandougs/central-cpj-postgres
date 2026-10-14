// ---------------- nova O.S.

let arquivos=[];const inp=$("#arqs"),drop=$("#drop");drop.onclick=()=>inp.click();inp.onchange=()=>addArqs(inp.files);

["dragenter","dragover"].forEach(e=>drop.addEventListener(e,ev=>{ev.preventDefault();drop.classList.add("on")}));["dragleave","drop"].forEach(e=>drop.addEventListener(e,ev=>{ev.preventDefault();drop.classList.remove("on")}));

drop.addEventListener("drop",ev=>addArqs(ev.dataTransfer.files));

let deteccaoOS=0,autoOS={};

async function detectarOS(){const versao=++deteccaoOS,f=$("#f-os"),tx=$("#dados-os-auto");

 for(const [k,v] of Object.entries(autoOS))if(f.elements[k]?.value===v)f.elements[k].value="";autoOS={};

 const fd=new FormData();const selecionados=arquivos.filter(a=>/\.(pdf|md)$/i.test(a.name)&&a.size<=64*1024*1024);

 if(!selecionados.length){tx.textContent="Envie o documento para tentar o preenchimento após OCR, ou complete os campos manualmente.";return}

 selecionados.forEach(a=>fd.append("arquivos",a));tx.textContent="Detectando dados no IP/processo…";

 try{const j=await enviar("/api/os/detectar",fd);if(versao!==deteccaoOS)return;const fontes=[];

  for(const [k,d] of Object.entries(j.campos)){const nome=k==="ordem_servico"?"os":k;const campo=f.elements[nome];if(campo&&!campo.value.trim()){campo.value=d.valor;autoOS[nome]=d.valor;campo.title=`${d.documento} · pág. ${d.pagina}: ${d.trecho}`;fontes.push(`${nome}: ${d.documento}, pág. ${d.pagina}`)}}

  tx.textContent=(fontes.length?"Preenchidos: "+fontes.join("; ")+". ":"Nenhum campo novo detectado. ")+(Object.keys(j.conflitos).length?"Dados divergentes: "+Object.keys(j.conflitos).join(", ")+". ":"")+"Os campos restantes serão tentados após o OCR e pela IA local configurada.";

 }catch(x){if(versao===deteccaoOS)tx.textContent="Prévia indisponível. Envie o documento para processamento e OCR."}}

function addArqs(fl){for(const f of fl)if(/\.(pdf|md|csv)$/i.test(f.name)&&!arquivos.some(a=>a.name===f.name&&a.size===f.size))arquivos.push(f);listaArqs();detectarOS()}

function listaArqs(){$("#lista-arq").innerHTML=arquivos.map((f,i)=>`<li><span>${esc(f.name)}</span><span class="muted">${kb(f.size)} · <a class="lk" data-i="${i}">remover</a></span></li>`).join("");$$("#lista-arq a").forEach(a=>a.onclick=()=>{arquivos.splice(+a.dataset.i,1);listaArqs();detectarOS()})}

async function processarPDFComAviso(enviarPedido){
 let cons=null;
 while(true){
  const r=await enviarPedido(cons);
  if(!r.requer_consentimento)return r;
  const espera=pedirConsentimentoExterno(r.destinos);
  $("#cons-destinos").textContent+=` · ${r.paginas} página(s). ${r.aviso||""}`;
  cons={...await espera,escopo:r.escopo};
 }
}
async function salvarRecebimento(processar){const f=$("#f-os");if(!f.reportValidity())return;

 if(processar&&!arquivos.length){$("#msg-up").textContent="Selecione o PDF do IP/processo antes de clicar em Processar PDF.";return}

 ++deteccaoOS;const fd=new FormData(f);if(processar)arquivos.forEach(a=>fd.append("arquivos",a));else fd.append("somente_cadastro","1");

 const botoes=[$("#b-enviar"),$("#b-salvar-os"),$("#b-nova-os")];botoes.forEach(b=>b.disabled=true);

 try{const j=await processarPDFComAviso(cons=>{if(cons)fd.set("consentimento_externo",JSON.stringify(cons));return enviar("/api/os",fd,processar?$("#prog-up"):null,processar?$("#prog-up-tx"):null)});
  if(j.recusado){$("#msg-up").textContent=j.mensagem;return}
  f.elements.caso_id.value=j.caso;

  $("#msg-up").innerHTML=`Dados ${j.criado?"salvos":"atualizados"} · <b>${esc(j.caso)}</b>${processar?" · "+j.recebidos.length+" arquivo(s) na fila":". Os arquivos selecionados serão enviados quando clicar em Processar PDF."}${j.ignorados.length?" · ignorados: "+esc(j.ignorados.join("; ")):""}`;

  if(processar){arquivos=[];autoOS={};listaArqs();$("#dados-os-auto").textContent="Processamento iniciado. Confira os campos preenchidos e pendentes na ficha do caso."+(j.limitacao?" "+j.limitacao:"");atualizarFila().catch(x=>toast(x.message))}

 }catch(x){$("#msg-up").textContent=x.message}finally{botoes.forEach(b=>b.disabled=false)}}

$("#f-os").onsubmit=e=>{e.preventDefault();salvarRecebimento(true)};

$("#b-salvar-os").onclick=()=>salvarRecebimento(false);

$("#b-nova-os").onclick=()=>{++deteccaoOS;$("#f-os").reset();$("#f-os").elements.caso_id.value="";$("#f-os").recebido.value=hoje();arquivos=[];autoOS={};listaArqs();$("#msg-up").textContent="Novo cadastro. Selecione o IP/processo ou preencha os campos.";$("#dados-os-auto").textContent="Os dados serão detectados ao selecionar o documento."};

async function atualizarFila(){
 const geracao=polling.geracao;let j;
 try{j=await lerAtualizacao("/api/fila")}catch(e){if(geracao===polling.geracao)pollingAviso(e);throw e}
 if(geracao!==polling.geracao)return null;
 polling.ocrAtivo=j.trabalhos.some(t=>["processando","na_fila"].includes(t.status));
 if(!polling.emCurso)programarPolling(polling.ocrAtivo||polling.ativo?1600:8000);
 const idioma=j.idioma_ocr?`OCR: ${j.idioma_ocr==="por"?"português":j.idioma_ocr}`:"";
 if($("#ocr-lang").textContent!==idioma)$("#ocr-lang").textContent=idioma;

 htmlAtualizado($("#fila"),j.trabalhos.length?j.trabalhos.map(t=>{const run=t.status==="processando";return `<div class="job"><div class="l1"><div><b>${esc(t.caso)}</b> · ${esc(t.arquivo)}</div>${badge(t.status)}</div>

 <div class="muted">${esc(t.etapa||"")}${run&&t.paginas?` · página ${t.pagina_atual||0} de ${t.paginas}`:(t.paginas?` · ${t.paginas} págs.`:"")}${t.erro?` · <span style="color:var(--crit)">${esc(t.erro)}</span>`:""}</div>${run||t.status==="na_fila"?barraHTML(t.progresso):""}</div>`}).join(""):'<div class="vazio">Nada na fila</div>');return j}



