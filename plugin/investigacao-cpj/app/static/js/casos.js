// ---------------- casos

function compararNumeroOS(a,b){
 const numero=c=>{const m=String(c.ordem_servico||c.id||"").match(/\d+/);return m?Number(m[0]):Infinity};
 return numero(a)-numero(b)||String(a.ordem_servico||a.id||"").localeCompare(String(b.ordem_servico||b.id||""),"pt-BR",{numeric:true});
}
let tq;$("#q-casos").oninput=()=>{clearTimeout(tq);tq=setTimeout(carregarCasos,250)};$("#st-casos").onchange=carregarCasos;$("#pz-casos").onchange=carregarCasos;$("#meus-casos").onchange=carregarCasos;

async function carregarCasos(){const cs=await api(`/api/casos?q=${enc($("#q-casos").value)}&status=${$("#st-casos").value}&prazo=${$("#pz-casos").value}&meus=${$("#meus-casos").checked?1:""}`);
 cs.sort(compararNumeroOS);

 $("#casos-vazio").hidden=!!cs.length;$("#t-casos").innerHTML=cs.map(c=>`<tr class="${c.status==="entregue"?"caso-entregue":""}" data-id="${esc(c.id)}"><td><b>${esc(c.ordem_servico||c.id)}</b>${!c.visto&&pode("trabalho")?' <span class="badge b-wait"><i aria-hidden="true"></i>nova</span>':""}${c.prioridade&&c.prioridade!=="normal"?` <span class="badge pz-hoje">${esc(c.prioridade)}</span>`:""}</td>

 <td>${esc(c.bo||"—")}<br><span class="muted">${esc(c.inquerito||"")}</span></td><td>${esc([...c.vitimas,...c.investigados].slice(0,3).join("; ")||"—")}</td><td>${esc(c.modalidade||"—")}</td>

 <td>${c.processando?badge("processando")+barraHTML(c.progresso_proc):(c.erro?badge("erro"):esc(c.status))}</td><td>${prazoBadge(c)}</td><td class="n">${c.paginas??"—"}</td></tr>`).join("");

 $$("#t-casos tr").forEach(tr=>tr.onclick=()=>abrirCaso(tr.dataset.id,true))}

let casoAberto=null;
let casoCarga=0,astraContextoCaso=null;

function explorarCasoNoAstra(id,rotulo,busca){
 if(!pode("pesquisa")||!confirmarSaidaEditor())return;
 const sel=$("#gr-caso");
 if(!Array.from(sel.options).some(o=>o.value===id))sel.add(new Option(rotulo||id,id));
 sel.value=id;if(busca!==undefined)$("#gr-busca").value=busca;
 let barra=$("#astra-contexto-caso");
 if(!barra){barra=document.createElement("div");barra.id="astra-contexto-caso";barra.className="acoes";$("#grafo").prepend(barra)}
 barra.replaceChildren();const voltar=document.createElement("button");voltar.type="button";voltar.className="btn";voltar.id="b-astra-voltar-caso";
 voltar.textContent=`Voltar à O.S. ${rotulo||id}`;voltar.onclick=async()=>{if(!confirmarSaidaEditor())return;await abrirCaso(id,true);if(casoAberto===id)abrirAba("casos")};barra.append(voltar);
 abrirAba("grafo");astraContextoCaso={id,q:$("#gr-busca").value.trim(),carga:grCarga};
}

function resumoGrafoDoCaso(id){
 const ctx=astraContextoCaso;
 if(!ctx||ctx.id!==id||ctx.carga!==grCarga||$("#gr-caso").value!==id||$("#gr-busca").value.trim()!==ctx.q)return "Contagens de contas e conexões ainda não consultadas neste recorte do ASTRA.";
 if(grEstado==="carregando")return "Consulta de vínculos em andamento; aguarde ou acompanhe no ASTRA.";
 if(grEstado==="erro")return `Consulta de vínculos indisponível: ${grErro}. Use Explorar no ASTRA para tentar novamente.`;
 if(grEstado!=="pronto")return "Contagens de vínculos não disponíveis para este recorte.";
 if(grDados.indice_disponivel===false)return "O índice de vínculos não está disponível; as contagens não foram apuradas.";
 const contas=(grDados.nos||[]).filter(n=>n.tipo==="CONTA").length,conexoes=(grDados.arestas||[]).length;
 const limite=grDados.truncado===true?" Resultado parcial; refine a busca.":grDados.completude==="nao_aferida"?" Completude não aferida; confira os limites.":"";
 return `${contas} contas e ${conexoes} conexões retornadas no recorte consultado.${limite}${grDados.aviso?" "+grDados.aviso:""}`;
}

function painelInvestigativo(id,j){
 const c=j.caso,T=j.trabalho,arqs=Array.isArray(j.arquivos)?j.arquivos:[],r=j.resumo||{},jobs=j.processamento?.trabalhos||[];
 const originais=arqs.filter(a=>a.caminho.startsWith("00-originais/"));
 const docs=Number.isInteger(r.documentos)?`${r.documentos} documento(s) cadastrado(s)/extraído(s)`:"Documentos extraídos não informados";
 const paginas=Number.isFinite(r.paginas)?`${r.paginas} páginas registradas`:"Páginas não informadas";
 const ativo=jobs.some(t=>["na_fila","processando"].includes(t.status)),erros=jobs.filter(t=>t.status==="erro"||t.erro);
 const iaAtiva=(j.ia||[]).some(t=>["na_fila","executando"].includes(t.status));
 const transcricao=arqs.some(a=>/^01-extracao\/.+\/transcricao(?:-normalizada)?\.md$/.test(a.caminho));
 const pendentes=c.preenchimento_os?.pendentes;
 const link=a=>`/arquivo/${enc(id)}/${a.caminho.split("/").map(enc).join("/")}`;
 const fonte=a=>`<li><a href="${link(a)}" target="_blank" rel="noopener">${esc(a.caminho)}</a>${a.tamanho===0?" — arquivo vazio; conferir":""}</li>`;
 const fontes=arqs.filter(a=>a.caminho.startsWith("00-originais/")||/^01-extracao\/.+\/(?:transcricao(?:-normalizada)?\.md|ordens-de-servico\/.+\.md)$/.test(a.caminho)||/^02-analise\/(?:solicitacoes-os|dados-faltantes)\.md$/.test(a.caminho));
 const lacuna=arqs.find(a=>a.caminho==="02-analise/dados-faltantes.md");
 const disponibilidade=[["Transcrição",transcricao],["Identificadores extraídos",arqs.some(a=>/^01-extracao\/.+\/entidades\.csv$/.test(a.caminho))],["Análise de pessoas",arqs.some(a=>a.caminho==="02-analise/pessoas.csv")],["Fluxo financeiro",arqs.some(a=>a.caminho==="02-analise/fluxo-financeiro.csv")]].map(([nome,tem])=>`${nome}: ${tem?"arquivo disponível para conferir":"não disponível"}`).join(" · ");
 let passo={texto:"Consultar material",acao:"fontes"};
 if(ativo)passo={texto:"Acompanhar extração",acao:"processamento"};
 else if(iaAtiva)passo={texto:"Acompanhar análise",acao:"ia"};
 else if(erros.length)passo={texto:"Conferir extração",acao:"processamento"};
 else if(c.status==="recebido")passo={texto:"Conferir material recebido",acao:"fontes"};
 else if(["extraido","em_analise"].includes(c.status))passo=transcricao&&pode("pesquisa")?{texto:"Explorar vínculos",acao:"explorar"}:{texto:"Conferir extração",acao:"fontes"};
 else if(c.status==="analisado"&&T&&pode("ia"))passo={texto:"Preparar relatório",acao:"relatorio"};
 else if(c.status==="minuta"&&T)passo={texto:"Revisar minuta",acao:"minuta"};
 else if(c.status==="entregue"&&(j.relatorios||[]).some(f=>f.tipo==="final"))passo={texto:"Ver relatório FINAL",acao:"final"};
 else if(c.status==="devolvido")passo={texto:"Conferir pendências",acao:"fontes"};
 return `<section id="astra-proximo-passo" style="margin-top:14px"><h4>Próximo passo da O.S.</h4><p class="muted">Ações para conferir o material, explorar vínculos e preparar a minuta. A conferência das fontes permanece sob responsabilidade do operador.</p>
 <div class="acoes"><button type="button" class="btn pri" id="b-caso-proximo" data-passo="${passo.acao}">${passo.texto}</button>${pode("pesquisa")?`<button type="button" class="btn" id="b-explorar-astra" data-caso="${esc(id)}">Explorar no ASTRA</button>`:""}<button type="button" class="btn" id="b-caso-conferir-fontes">Conferir fontes e pendências</button>${T&&pode("pesquisa")?'<button type="button" class="btn" id="b-caso-hipotese">Registrar hipótese de vínculo</button>':""}</div>
 ${pode("pesquisa")?'<div class="acoes"><label for="astra-identificador">Pessoa ou conta</label><input id="astra-identificador" placeholder="Digite o nome ou identificador para explorar" style="max-width:360px"><button type="button" class="btn sm" id="b-caso-explorar-identificador">Explorar identificador</button></div>':""}
 <div id="astra-material-resumo" role="status"><p>${originais.length} arquivos originais · ${docs} · ${paginas}.</p><p>${esc(disponibilidade)}.</p><p>${esc(resumoGrafoDoCaso(id))}</p><p>${Array.isArray(pendentes)?pendentes.length+" campo(s) de cadastro pendente(s)" :"Pendências de cadastro não informadas"}. ${lacuna?`<a href="${link(lacuna)}" target="_blank" rel="noopener">Registro de lacunas disponível</a>${lacuna.tamanho===0?" — arquivo vazio; conferir":""}`:"Registro de lacunas não disponível"}.</p>${ativo?'<p>Extração em andamento; acompanhe o progresso em Processamento.</p>':""}${erros.map(t=>`<p class="aviso alerta">${esc(t.arquivo||"Documento")}: ${esc(t.erro||"Processamento com erro; confira o documento e tente reprocessar.")}</p>`).join("")}</div>
 <div id="astra-fontes" hidden><h5>Material disponível para conferência</h5>${fontes.length?`<ul>${fontes.map(fonte).join("")}</ul>`:'<p>Nenhum documento ou registro de fontes disponível. Confira o recebimento e o processamento da O.S.</p>'}</div></section>`;
}

let origemVisualizador=null;
function fecharVisualizadorRelatorio(){
 $("#visualizador-relatorio").hidden=true;$("#vis-frame").removeAttribute("src");$("#vis-frame").removeAttribute("sandbox");
 if(origemVisualizador&&origemVisualizador.isConnected)origemVisualizador.focus();origemVisualizador=null;
}
function visualizarRelatorio(id,arquivo,origem){
 const caminho="03-relatorios/"+arquivo,rel=caminho.split("/").map(enc).join("/"),docx=/\.docx$/i.test(arquivo),frame=$("#vis-frame");
 origemVisualizador=origem;$("#vis-titulo").textContent=arquivo;$("#vis-aviso").hidden=false;
 $("#vis-aviso").textContent=docx?"Prévia de texto e tabelas do DOCX. Para a formatação completa, abra o original no Word.":"Se o navegador não exibir o PDF, clique em Abrir original.";
 $("#vis-original").href=`/arquivo/${enc(id)}/${rel}`;
 if(docx)frame.setAttribute("sandbox","allow-same-origin");else frame.removeAttribute("sandbox");
 frame.src=`/${docx?"visualizar":"arquivo"}/${enc(id)}/${rel}`;$("#visualizador-relatorio").hidden=false;$("#vis-fechar").focus();
}
$("#vis-fechar").onclick=fecharVisualizadorRelatorio;
$("#visualizador-relatorio").onclick=e=>{if(e.target===$("#visualizador-relatorio"))fecharVisualizadorRelatorio()};
document.addEventListener("keydown",e=>{if(e.key==="Escape"&&!$("#visualizador-relatorio").hidden)fecharVisualizadorRelatorio()});

let pendenciasItens = [];
async function carregarPendencias(){
  if(!pode("trabalho"))return;
  const geracao=polling.geracao;
  const p = await lerAtualizacao("/api/pendencias-ocr");
  if(geracao!==polling.geracao)return;
  const assinatura=JSON.stringify(p.pendentes||[]);
  if(carregarPendencias.assinatura===assinatura)return;
  carregarPendencias.assinatura=assinatura;
  pendenciasItens = p.pendentes || [];
  renderPendencias();
}

function atualizarBotaoPendencias() {
  const chks = $$(".pend-chk");
  const numMarcados = Array.from(chks).filter(c => c.checked).length;
  $("#b-processar-pendentes").disabled = numMarcados === 0;
  $("#pend-chk-todos").checked = chks.length > 0 && numMarcados === chks.length;
}

function renderPendencias(){
  const t = $("#t-pendencias");
  if(!pendenciasItens.length){
    t.innerHTML = "";
    $("#pendencias-vazio").hidden = false;
    $("#b-processar-pendentes").disabled = true;
    $("#pend-chk-todos").disabled = true;
    return;
  }
  $("#pendencias-vazio").hidden = true;
  $("#pend-chk-todos").disabled = false;
  
  t.innerHTML = pendenciasItens.map((i, idx) => `
    <tr>
      <td><input type="checkbox" class="pend-chk" data-idx="${idx}" checked></td>
      <td><b>${esc(i.os)}</b></td>
      <td>${esc(i.arquivo)}</td>
      <td>${i.status?badge(i.status):(i.erro?badge("erro"):esc("-"))}${i.erro?` <span style="color:var(--crit)">${esc(i.erro)}</span>`:""}${i.motivo?` <span style="color:var(--crit)">${esc(i.motivo)}</span>`:""}</td>
    </tr>
  `).join("");
  
  $$(".pend-chk").forEach(c => c.onchange = atualizarBotaoPendencias);
  atualizarBotaoPendencias();
}

$("#pend-chk-todos").onchange = e => {
  $$(".pend-chk").forEach(c => c.checked = e.target.checked);
  atualizarBotaoPendencias();
};

$("#b-processar-pendentes").onclick = async () => {
  const selecionados = [];
  $$(".pend-chk").forEach(c => {
    if(c.checked) selecionados.push(pendenciasItens[parseInt(c.dataset.idx)]);
  });
  if(!selecionados.length) return;
  
  $("#b-processar-pendentes").disabled = true;
  $("#b-processar-pendentes").textContent = "Processando...";
  
  try {
    const r = await api("/api/pendencias-ocr/processar", { method: "POST", json: selecionados });
    let enfileirados = 0;
    r.resultados.forEach(res => {
      if(res.status === "enfileirado") enfileirados++;
    });
    toast(`${enfileirados} arquivo(s) enviado(s) para a fila`);
    await carregarPendencias();
  } catch(e) {
    toast("Erro ao processar: " + (e.message || "Erro desconhecido"));
  } finally {
    $("#b-processar-pendentes").textContent = "Processar OS em Lote";
    atualizarBotaoPendencias();
  }
};

const NOMES_OS={ordem_servico:"O.S.",bo:"BO",inquerito:"IP",processo:"Processo",natureza:"Natureza",requisitante:"Delegado requisitante",escrivao:"Escrivão do feito",prazo:"Prazo",determinacao:"Determinação"};

const ESTADO_IA_OS={modelo_local_nao_instalado:"modelo local não instalado; complete manualmente",modelo_remoto_bloqueado:"modelo remoto bloqueado; selecione um modelo local",aguardando_ocr:"aguardando extração/OCR",dispensada:"campos detectados por script",concluida:"IA local consultada",ia_local_nao_configurada:"modelo local ainda não configurado",ia_local_indisponivel:"IA local indisponível; complete os campos pendentes",sem_evidencia:"dados não localizados; complete manualmente",resposta_invalida:"IA sem resposta válida; complete manualmente"};

async function abrirCaso(id,rolar){const novoCaso=casoAberto!==id;if(edCaso&&edCaso!==id&&!confirmarSaidaEditor())return;const carga=++casoCarga;casoAberto=id;
 if(novoCaso)$("#detalhe").innerHTML='<div class="card" role="status">Carregando a O.S.…</div>';
 let j;try{j=await api("/api/casos/"+enc(id))}catch(x){if(carga===casoCarga){$("#detalhe").innerHTML=`<div class="card"><p class="aviso alerta">Não foi possível abrir a O.S.: ${esc(x.message)}</p><button type="button" class="btn" id="b-caso-retentar">Tentar novamente</button></div>`;$("#b-caso-retentar").onclick=()=>abrirCaso(id,true)}return}
 if(carga!==casoCarga||casoAberto!==id)return;const c=j.caso,r=j.resumo,T=j.trabalho;

 const campo=(k,l,v,t="text")=>`<div><label>${l}</label><input data-k="${k}" type="${t}" value="${esc(v??"")}"></div>`;

 const sel=(k,l,ops,v)=>`<div><label>${l}</label><select data-k="${k}">${ops.map(o=>`<option ${o===(v||"")?"selected":""}>${o}</option>`).join("")}</select></div>`;

 const podeGestao=T||c.criado_por===S.usuario.login||S.usuario.perfil==="delegado";

 let dados=`${campo("ordem_servico","Ordem de Serviço",c.ordem_servico)}${campo("bo","BO",c.bo)}${campo("inquerito","Inquérito Policial",c.inquerito)}${campo("processo","Processo",c.processo)}

  ${campo("requisitante","Requisitante",c.requisitante)}${campo("escrivao","Escrivão do feito",c.escrivao)}${campo("prazo","Prazo",c.prazo,"date")}${sel("prioridade","Prioridade",["normal","urgente","reu-preso"],c.prioridade)}`;

 if(T){const rs=await api("/api/responsaveis");if(carga!==casoCarga||casoAberto!==id)return;dados+=`<div><label>Responsável</label><select data-k="responsavel"><option value="">— não atribuído —</option>${rs.map(u=>`<option value="${esc(u.login)}" ${u.login===c.responsavel?"selected":""}>${esc(u.nome)}</option>`).join("")}</select></div>`}

 if(T)dados+=`${campo("natureza","Natureza",c.natureza)}${sel("modalidade","Modalidade",MOD,c.modalidade)}${sel("status","Status",ST,c.status)}${sel("resultado.autoria","Autoria",["","identificada","indicios","nao_identificada"],(c.resultado||{}).autoria)}

  ${campo("vitimas","Vítima(s)",(c.vitimas||[]).join(", "))}${campo("investigados","Investigado(s)",(c.investigados||[]).join(", "))}${campo("financeiro.valor_rastreado","Valor rastreado (R$)",(c.financeiro||{}).valor_rastreado)}`;

 const docs=(c.documentos||[]).map(d=>`<tr><td>${esc(d.arquivo)}</td><td class="n">${d.paginas??"—"}</td><td>${esc(Object.entries(d.metodos||{}).map(([k,v])=>k+": "+v).join(", ")||d.tipo||"—")}</td></tr>`).join("");

 const proc=(j.processamento.trabalhos||[]).map(t=>`<div class="job"><div class="l1"><span>${esc(t.arquivo)} · <span class="muted">${esc(t.etapa||"")}</span></span><span>${badge(t.status)} ${T?`<button class="btn sm" data-rep="${esc(t.doc)}">reprocessar</button>`:""}</span></div>${["processando","na_fila"].includes(t.status)?barraHTML(t.progresso):""}${t.erro?`<div class="muted" style="color:var(--crit)">${esc(t.erro)}</div>`:""}</div>`).join("");

 const link=a=>`/arquivo/${enc(id)}/${a.split("/").map(enc).join("/")}`;
 const pastaArquivo=a=>T&&j.local===true?`<button class="btn sm" data-pasta-arquivo="${esc(a)}" title="Mostrar ${esc(a)} no Explorador de Arquivos">Abrir na pasta</button>`:"";

 const linhaRelatorio=f=>{const a="03-relatorios/"+f.arquivo,dx=/\.docx$/i.test(f.arquivo),visual=dx||/\.pdf$/i.test(f.arquivo);return `<tr><td><a class="lk" href="${link(a)}" target="_blank">${esc(f.arquivo)}</a></td><td>${esc(f.tipo)}</td><td class="muted">${esc(f.modificado.replace("T"," "))}</td>

  <td>${pastaArquivo(a)} ${visual?`<button class="btn sm" data-visualizar="${esc(f.arquivo)}" title="Visualizar relatório no sistema">Visualizar</button> `:""}${T&&f.tipo==="minuta"?`<button class="btn sm" data-edit="${esc(f.arquivo)}">editar</button> <button class="btn sm" data-gdocx="${esc(f.arquivo)}">gerar DOCX</button>`:""}${T&&dx?`<button class="btn sm" data-pdf="${esc(f.arquivo)}">PDF</button> ${j.local!==false?`<button class="btn sm" data-word="${esc(a)}">abrir no Word</button>`:""} ${f.tipo!=="final"?`<button class="btn sm" data-final="${esc(f.arquivo)}">definir FINAL</button>`:""} <button class="btn sm" data-calibrar="${esc(f.arquivo)}" title="Calibrar estilo com este relatório">calibrar estilo</button>`:""}</td></tr>`};
 const rels=[["relatorios-docx","Word (DOCX)",true],["relatorios-outros","Outros relatórios",false]].map(([grupo,titulo,docx])=>{const arquivos=j.relatorios.filter(f=>/\.docx$/i.test(f.arquivo)===docx);return arquivos.length?`<section id="${grupo}"><h5>${titulo}</h5><table><tbody>${arquivos.map(linhaRelatorio).join("")}</tbody></table></section>`:""}).join("");
 const arqs=[["arquivos-docx","Word (DOCX)",true],["arquivos-outros","Outros arquivos",false]].map(([grupo,titulo,docx])=>{const arquivos=j.arquivos.filter(a=>/\.docx$/i.test(a.caminho)===docx);return arquivos.length?`<section id="${grupo}"><h5>${titulo}</h5>${arquivos.map(a=>`<div><a href="${link(a.caminho)}" target="_blank">${esc(a.caminho)}</a><span class="muted">${kb(a.tamanho)}</span>${pastaArquivo(a.caminho)}</div>`).join("")}</section>`:""}).join("");

 const baixa=c.status==="entregue"?`<div>${badge("concluido")} Baixa em <b>${dt((c.datas||{}).entregue)}</b> · origem: ${esc((c.baixa||{}).origem||"—")} ${T?'<button class="btn sm" id="b-desfazer">Desfazer baixa</button>':""}</div>`

   :(T?`<div class="acoes" style="margin:0"><input type="date" id="d-baixa" style="width:auto" value="${hoje()}"><button class="btn sm" id="b-baixa">Dar baixa (entregue)</button></div>`:'<span class="muted">Em andamento</span>');

 $("#detalhe").innerHTML=`<div class="card"><div style="display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;align-items:center"><h3 style="margin:0">${esc(c.ordem_servico||id)} <span class="muted">(${esc(id)})</span> ${prazoBadge(r)}</h3>

 <div class="acoes" style="margin:0">${T?'<button class="btn sm" id="b-pasta">Abrir pasta</button><button class="btn sm" id="b-caso-ver-fluxo">Ver Fluxograma</button><a class="btn sm" id="b-caso-fluxo-csv" href="/api/casos/'+enc(id)+'/fluxo-csv" target="_blank">Planilha (CSV)</a><button class="btn sm" id="b-cruzar">Cruzar com outros casos</button>':""}${podeGestao?'<button class="btn sm pri" id="b-salvar">Salvar</button>':""}</div></div>

 <div class="acoes" style="margin:10px 0 0"><button class="btn sm" data-ir="nv-ficha">Ficha</button><button class="btn sm" data-ir="nv-relatorios">Relatórios</button>${T&&j.local!==false?'<button class="btn sm" id="b-pasta-relatorios" title="Abrir pasta dos relatórios de investigação">📁 Relatórios</button>':""}${T?'<button class="btn sm" data-ir="nv-ia">IA</button><button class="btn sm" data-ir="nv-cal">Calibração</button>':""}</div>
 ${painelInvestigativo(id,j)}
 <div class="campos" id="nv-ficha" style="margin-top:12px">${dados}</div>${c.preenchimento_os?`<div class="muted">Preenchimento automático: ${esc(ESTADO_IA_OS[c.preenchimento_os.ia]||"aguardando processamento")}. Pendentes: ${esc((c.preenchimento_os.pendentes||[]).map(k=>NOMES_OS[k]||k).join(", ")||"nenhum")}. ${Object.keys(c.preenchimento_os.conflitos||{}).length?"Dados divergentes: "+esc(Object.keys(c.preenchimento_os.conflitos).map(k=>NOMES_OS[k]||k).join(", "))+". Confira no IP antes de preencher.":""}<details><summary>Fontes dos dados preenchidos</summary>${Object.entries(c.preenchimento_os.fontes||{}).map(([k,d])=>`<p>${esc(NOMES_OS[k]||k)}: ${esc(d.documento)}, pág. ${d.pagina} — ${esc(d.trecho)} (${esc(d.metodo)})</p>`).join("")}</details></div>`:""}<label>Determinação da autoridade</label><textarea data-k="determinacao" rows="2" ${podeGestao?"":"disabled"}>${esc(c.determinacao||"")}</textarea>

 ${T?`<div class="card" id="nv-ia" style="margin-top:14px;background:var(--page)"><h4>Inteligência artificial</h4><div class="acoes" style="margin:0 0 8px">
  <button class="btn" id="b-transcricao-visual">Transcrever páginas a conferir</button>

  <button class="btn pri" data-ia="esteira" style="background:#1b5e20;border-color:#1b5e20;color:#fff;font-weight:600" title="Executa a esteira completa: OCR, RAG, analistas, redação, revisão e DOCX">⚡ Esteira Completa 1-Clique</button><button class="btn" data-ia="completo">Analisar IP e gerar relatório</button><button class="btn pri" data-ia="relatorio">Gerar relatório</button><button class="btn" data-ia="revisar">Revisar relatório</button><button class="btn" id="b-ia-ver-fluxo">Ver Fluxograma</button><a class="btn" href="/api/casos/${enc(id)}/fluxo-csv" target="_blank">Planilha de Rastreio (CSV)</a></div>

  <div class="campos" style="margin:0 0 8px;grid-template-columns:minmax(0,2fr) minmax(0,1fr)"><div><input id="ia-obs" placeholder="Observações para o agente (opcional): diligências que você fez, consultas, foco pedido pelo delegado…"></div>

  <div><select id="ia-agente" title="Quem executa"><option value="">Qualquer agente ocioso (recomendado)</option></select></div></div>

  <div class="muted" id="ia-agentes-resumo"></div><div id="ia-painel" style="margin-top:8px"></div></div>
 <div class="card" id="nv-cal" style="margin-top:14px;background:var(--page)"><h4>Calibração do estilo (minuta × FINAL)</h4>
  <p class="muted">Envie o relatório FINAL (PDF, DOCX ou MD) que você assinou. A comparação com a última minuta é feita neste computador e gera só lições genéricas, sem nomes, números ou trechos do caso. Nada é gravado até você aprovar.</p>
  <div class="acoes" style="margin:0"><input type="file" id="cal-arq" accept=".pdf,.docx,.md,.txt"><button class="btn pri" id="b-cal-comparar">Comparar com a minuta</button><button class="btn sm" id="b-cal-ref">Guardar como exemplo de estilo</button></div>
  <div class="prog" id="prog-cal" hidden><i aria-hidden="true"></i></div><div class="muted" id="cal-msg" style="margin-top:6px"></div><div id="cal-res"></div></div>`:""}

 <div class="g2" style="margin-top:14px"><div>

  <h4 id="nv-relatorios">Relatórios</h4>${rels||'<div class="muted">Nenhum relatório ainda.</div>'}${T?'<div class="acoes"><button class="btn sm" id="b-nova-minuta">Escrever/editar minuta</button></div>':""}

  <h4 style="margin-top:14px">Produção</h4>${baixa}

  <h4 id="nv-documentos" style="margin-top:14px">Documentos</h4>${docs?`<table><thead><tr><th>Arquivo</th><th class="n">Págs.</th><th>Métodos</th></tr></thead><tbody>${docs}</tbody></table>`:'<div class="muted">—</div>'}

  <h4 id="nv-processamento" style="margin-top:14px">Processamento</h4>${T?'<label for="modo-reprocessar">Modo ao reprocessar</label><select id="modo-reprocessar"><option value="rapido">Rápido — somente local</option><option value="inteligente" selected>Inteligente — páginas a conferir</option><option value="ia_completa">IA Completa — todas as páginas</option></select>':""}${proc||'<div class="muted">—</div>'}<div id="cruz"></div></div>

 <div><h4>Arquivos</h4><div class="arqs">${arqs||'<span class="muted">—</span>'}</div></div></div></div>`;

 if(rolar||novoCaso)requestAnimationFrame(()=>$("#detalhe").scrollIntoView({behavior:"smooth",block:"start"}));
 const irPara=k=>{const e=$("#"+k);if(e)e.scrollIntoView({behavior:"smooth",block:"start"})};
 $$("#detalhe [data-ir]").forEach(b=>b.onclick=()=>irPara(b.dataset.ir));$$("#detalhe [data-calibrar]").forEach(b=>b.onclick=()=>irPara("nv-cal"));
 const explorar=busca=>explorarCasoNoAstra(id,c.ordem_servico||id,busca);
 if($("#b-explorar-astra"))$("#b-explorar-astra").onclick=()=>explorar();
 if($("#b-caso-explorar-identificador"))$("#b-caso-explorar-identificador").onclick=()=>{const busca=$("#astra-identificador").value.trim();if(busca)explorar(busca);else $("#astra-identificador").focus()};
 const conferirFontes=()=>{$("#astra-fontes").hidden=false;irPara("astra-fontes")};
 $("#b-caso-conferir-fontes").onclick=conferirFontes;
 if($("#b-caso-ver-fluxo"))$("#b-caso-ver-fluxo").onclick=()=>{if(!confirmarSaidaEditor())return;const sel=$("#fx-caso-sel");sel.value=Array.from(sel.options).some(o=>o.value===id)?id:"";abrirAba("fluxograma")};
 if($("#b-caso-hipotese"))$("#b-caso-hipotese").onclick=()=>{if(!$("#modal-vinculo").hidden)return;explorar();if($("#grafo").classList.contains("on")){$("#f-vinculo").reset();grAbrirModalVinculo()}};
 $("#b-caso-proximo").onclick=()=>{switch($("#b-caso-proximo").dataset.passo){
  case "explorar":explorar();break;case "processamento":irPara("nv-processamento");break;case "ia":irPara("nv-ia");break;
  case "relatorio":$("#detalhe [data-ia='relatorio']")?.click();break;case "minuta":$("#b-nova-minuta")?.click();break;
  case "final":{const f=j.relatorios.find(f=>f.tipo==="final"&&/\.(docx|pdf)$/i.test(f.arquivo))||j.relatorios.find(f=>f.tipo==="final");const link=Array.from($$("#detalhe a")).find(a=>a.getAttribute("href")===`/arquivo/${enc(id)}/03-relatorios/${enc(f.arquivo)}`);link?.click();break}
  default:conferirFontes();
 }};

 const post=(u,b)=>api(`/api/casos/${enc(id)}${u}`,{json:b||{}});
 if($("#b-cal-comparar")){
  const msg=t=>{$("#cal-msg").textContent=t||""},barra=on=>{const p=$("#prog-cal");p.hidden=!on;p.classList.toggle("ind",on)};
  $("#b-cal-comparar").onclick=async()=>{const f=$("#cal-arq").files[0];$("#cal-res").innerHTML="";
   if(!f){msg("Selecione o arquivo FINAL (PDF, DOCX ou MD).");return}
   const fd=new FormData();fd.append("final",f);msg("Comparando localmente com a última minuta…");barra(true);$("#b-cal-comparar").disabled=true;
   try{const r=await api(`/api/casos/${enc(id)}/calibrar`,{method:"POST",body:fd});msg(r.mensagem||"");
    const m=r.metricas||{},mi=m.minuta||{},fi=m.final||{};
    const resumo=`<div class="muted">Similaridade com a minuta: ${Math.round((m.similaridade||0)*100)}% · palavras ${mi.palavras||0} → ${fi.palavras||0} · citações/1000 palavras ${mi.citacoes_por_mil||0} → ${fi.citacoes_por_mil||0} · tópicos ${mi.topicos||0} → ${fi.topicos||0}</div>`;
    $("#cal-res").innerHTML=resumo+(r.licoes&&r.licoes.length?`<div style="margin:8px 0">${r.licoes.map(l=>`<label style="display:flex;gap:8px;align-items:flex-start;margin:4px 0"><input type="checkbox" data-lic="${esc(l.id)}" checked><span>${esc(l.texto)}</span></label>`).join("")}</div><div class="acoes"><button class="btn pri" id="b-cal-aprovar">Gravar lições aprovadas</button><span class="muted">Desmarque o que não quiser. Só a lista acima, sem dados do caso, vai para a calibração.</span></div>`:'<div class="muted" style="margin-top:8px">Nenhuma diferença relevante: nada a calibrar.</div>');
    if($("#b-cal-aprovar"))$("#b-cal-aprovar").onclick=async()=>{const ids=$$("#cal-res [data-lic]").filter(x=>x.checked).map(x=>x.dataset.lic);
     if(!ids.length){msg("Marque ao menos uma lição.");return}
     if(!confirm(`Gravar ${ids.length} lição(ões) genérica(s) em calibracao\\licoes-aprendidas.md?`))return;
     try{const a=await post("/calibrar/aprovar",{ids});toast(`Calibração registrada: ${a.gravadas.length} nova(s), ${a.ja_existentes.length} já existente(s)`);$("#cal-res").innerHTML="";msg("Lições aprovadas registradas.")}catch(x){msg("Erro: "+x.message)}}
   }catch(x){msg("Erro: "+x.message)}finally{barra(false);$("#b-cal-comparar").disabled=false}};
  $("#b-cal-ref").onclick=()=>{abrirAba("sistema");setTimeout(()=>{const e=$("#card-referencias");if(e)e.scrollIntoView({behavior:"smooth",block:"start"})},200)};
 }

 if($("#b-salvar"))$("#b-salvar").onclick=async()=>{const d={};$$("#detalhe [data-k]").forEach(e=>{if(!e.disabled)d[e.dataset.k]=e.value});try{await post("",d);toast("Salvo");carregarCasos()}catch(x){toast(x.message)}};

 if($("#b-pasta"))$("#b-pasta").onclick=()=>post("/abrir",{}).catch(x=>toast(x.message));
 if($("#b-pasta-relatorios"))$("#b-pasta-relatorios").onclick=()=>post("/abrir",{sub:"03-relatorios"}).catch(x=>toast(x.message));
 $$("#detalhe [data-pasta-arquivo]").forEach(b=>b.onclick=()=>post("/abrir",{sub:b.dataset.pastaArquivo,selecionar:true}).catch(x=>toast(x.message)));
 $$("#detalhe [data-visualizar]").forEach(b=>b.onclick=()=>visualizarRelatorio(id,b.dataset.visualizar,b));

 if($("#b-cruzar"))$("#b-cruzar").onclick=async()=>{const r=await api("/api/cruzar/"+enc(id));$("#cruz").innerHTML=`<h4 style="margin-top:14px">Conexões com outros casos</h4>`+(r.length?`<table><tbody>${r.map(x=>`<tr><td>${esc(x.tipo)}</td><td>${esc(x.valor)}</td><td>também em <b>${esc(x.outro_caso)}</b> (págs. ${esc(x.paginas)})</td></tr>`).join("")}</tbody></table><div class="muted">Indícios de vinculação a verificar nos originais.</div>`:'<div class="muted">Nenhuma conexão encontrada.</div>')};

 $$("#detalhe [data-rep]").forEach(b=>b.onclick=async()=>{try{const modo=$("#modo-reprocessar").value;const r=await processarPDFComAviso(cons=>post(`/reprocessar/${enc(b.dataset.rep)}`,{modo,...(cons?{consentimento_externo:cons}:{})}));toast(r.recusado?r.mensagem:"Reenviado para a fila"+(r.limitacao?" · "+r.limitacao:""))}catch(x){toast(x.message)}});

 if($("#b-baixa"))$("#b-baixa").onclick=async()=>{try{await post("/baixa",{data:$("#d-baixa").value});toast("Baixa registrada");abrirCaso(id);carregarCasos()}catch(x){toast(x.message)}};

 if($("#b-desfazer"))$("#b-desfazer").onclick=async()=>{if(!confirm("Desfazer a baixa? O caso volta para 'minuta'."))return;await post("/baixa",{desfazer:true});abrirCaso(id);carregarCasos()};

 if($("#b-transcricao-visual"))$("#b-transcricao-visual").onclick=async()=>{try{await enviarPedidoIA((u,d)=>post("/transcricao-visual",d),{})}catch(x){toast(x.message)}};
 $$("#detalhe [data-ia]").forEach(b=>b.onclick=async()=>{const acao=b.dataset.ia;if(!confirm(`Acionar o agente de IA: ${b.textContent}? Ele trabalha sozinho e pode levar vários minutos.`))return;

  try{await enviarPedidoIA(post,{acao,observacoes:$("#ia-obs").value,agente:$("#ia-agente")?$("#ia-agente").value:""})}catch(x){toast(x.message)}});

 if($("#ia-agente"))carregarAgentes().then(g=>{if(!g||!$("#ia-agente"))return;

  $("#ia-agente").innerHTML='<option value="">Qualquer agente ocioso (recomendado)</option>'+g.agentes.filter(a=>a.aprovado).map(a=>`<option value="${esc(a.nome)}">${esc(a.nome)} — ${esc(a.estado)}</option>`).join("");

  $("#ia-agentes-resumo").innerHTML=g.ociosos?`${g.ociosos} agente(s) ocioso(s) de plantão.`:`<span style="color:var(--warn)">Nenhum agente ocioso agora: o pedido aguardará na fila até um agente ficar disponível.</span>`});

 $$("#detalhe [data-edit]").forEach(b=>b.onclick=()=>abrirEditor(id,b.dataset.edit));if($("#b-nova-minuta"))$("#b-nova-minuta").onclick=()=>abrirEditor(id,null);

 $$("#detalhe [data-gdocx]").forEach(b=>b.onclick=async()=>{b.disabled=true;try{const r=await post("/docx",{minuta:b.dataset.gdocx});toast(`DOCX gerado: ${r.docx}${r.pendentes?" · pendentes: "+r.pendentes:""}`);abrirCaso(id)}catch(x){toast(x.message)}b.disabled=false});

 $$("#detalhe [data-pdf]").forEach(b=>b.onclick=async()=>{b.disabled=true;try{const r=await post("/pdf",{docx:b.dataset.pdf});toast("PDF gerado: "+r.pdf);abrirCaso(id)}catch(x){alert(x.message)}b.disabled=false});

 $$("#detalhe [data-word]").forEach(b=>b.onclick=()=>post("/abrir",{sub:b.dataset.word}).catch(x=>toast(x.message)));

 $$("#detalhe [data-final]").forEach(b=>b.onclick=async()=>{if(!confirm(`Definir ${b.dataset.final} como relatório FINAL? Isso registra a entrega. Depois, use Calibração do estilo para enviar o FINAL assinado.`))return;try{await post("/final",{docx:b.dataset.final});toast("Relatório FINAL definido");abrirCaso(id);carregarCasos()}catch(x){if(x.status===409&&x.data&&x.data.bloqueado){mostrarModalFinalRessalva(id,b.dataset.final,x.data);return}toast(x.message)}});

 atualizarIA()}

function mostrarModalFinalRessalva(id, docxNome, data){
  const m=$("#modal-final-ressalva");
  if(!m)return;
  const achados=data.achados||data.conferencia||[];
  $("#final-ressalva-lista").innerHTML=achados.length?achados.map(a=>`
    <div style="padding:6px;border-bottom:1px solid var(--borda,#eee);line-height:1.4">
      <span class="badge ${a.nivel==='BLOQUEIA'?'b-err':'b-wait'}">${esc(a.nivel||'BLOQUEIA')}</span>
      <b>${esc(a.codigo||'ACHADO')}</b> ${a.linha?`(linha ${a.linha})`:''}: ${esc(a.detalhe||'')}
      ${a.dado?`<br><code style="font-size:11px;background:rgba(0,0,0,0.06);padding:2px 4px;border-radius:3px">${esc(a.dado)}</code>`:''}
    </div>`).join(""):'<div>Conferência reprovada sem detalhes adicionais.</div>';
  $("#final-ressalva-texto").value="";
  m.hidden=false;

  const btnConfirmar=$("#b-confirmar-final-ressalva");
  btnConfirmar.onclick=async()=>{
    const just=($("#final-ressalva-texto").value||"").trim();
    if(just.length<15){
      alert("A justificativa é obrigatória e deve conter no mínimo 15 caracteres.");
      return;
    }
    try{
      btnConfirmar.disabled=true;
      await api(`/api/casos/${enc(id)}/final`,{json:{docx:docxNome,forcar:true,justificativa:just}});
      m.hidden=true;
      toast("Relatório FINAL definido com ressalva");
      abrirCaso(id);
      carregarCasos();
    }catch(err){
      alert(err.message);
    }finally{
      btnConfirmar.disabled=false;
    }
  };
}
if($("#b-fecha-final-ressalva"))$("#b-fecha-final-ressalva").onclick=()=>{$("#modal-final-ressalva").hidden=true};
if($("#b-canc-final-ressalva"))$("#b-canc-final-ressalva").onclick=()=>{$("#modal-final-ressalva").hidden=true};

function pedirConsentimentoExterno(destinos){
 const modal=$("#modal-consentimento"),aceitar=$("#b-cons-aceitar"),recusar=$("#b-cons-recusar");
 if(!Array.isArray(destinos)||!destinos.length)return Promise.reject(new Error("Destinos externos não informados."));
 if(!modal.hidden)return Promise.reject(new Error("Responda ao aviso de processamento externo já aberto."));
 $("#cons-destinos").textContent=destinos.map(d=>d.startsWith("cli:")?d.slice(4)+" (CLI)":d).join(", ");
 modal.hidden=false;
 return new Promise(resolve=>{
  const fechar=aceito=>{modal.hidden=true;aceitar.onclick=null;recusar.onclick=null;document.removeEventListener("keydown",tecla);resolve(aceito?{aceito:true,destinos:destinos.slice()}:{recusado:true})};
  const tecla=e=>{if(e.key==="Escape"){e.preventDefault();fechar(false)}};
  aceitar.onclick=()=>fechar(true);recusar.onclick=()=>fechar(false);
  document.addEventListener("keydown",tecla);recusar.focus();
 });
}
async function enviarPedidoIA(post,dados){
 let r=await post("/ia",dados);
 while(r.requer_consentimento){
  const espera=pedirConsentimentoExterno(r.destinos);
  if(r.paginas)$("#cons-destinos").textContent+=` · ${r.paginas} página(s) indicada(s); transcrições existentes serão preservadas.`;
  const cons=await espera;
  r=await post("/ia",{...dados,consentimento_externo:{...cons,escopo:r.escopo||"api_ia"}});
  if(cons.recusado){toast(r.mensagem||"Envio recusado.");return r}
 }
 if(r.tarefa){toast("Pedido enviado ao plantão");atualizarIA()}
 else throw new Error(r.erro||"O pedido não foi enfileirado.");
 return r;
}
async function atualizarIA(dados){
 const id=casoAberto,painel=$("#ia-painel"),geracao=polling.geracao,login=S.usuario?.login;
 if(!id||!painel)return;
 let todos;try{todos=dados||await consultarTarefas()}catch(e){if(id===casoAberto&&geracao===polling.geracao)pollingAviso(e);return null}
 if(id!==casoAberto||painel!==$("#ia-painel")||geracao!==polling.geracao||login!==S.usuario?.login)return;
 const ts=todos.filter(t=>t.tipo==="ia"&&t.caso===id).slice(0,3);
 const html=ts.map(t=>{const run=["executando","na_fila"].includes(t.status);return `<div class="job" data-tarefa="${esc(t.id)}"><div class="l1"><span><b>${esc(t.titulo)}</b></span><span>${badge(t.status)} ${run?`<button class="btn sm dan" data-cancel="${esc(t.id)}">cancelar</button>`:""}</span></div>
  ${run?barraHTML(t.progresso):""}<div class="muted">${run?`${t.progresso}% · `:""}${esc(etapaTarefa(t))}</div>${t.erro?`<div class="muted" style="color:var(--crit)">${esc(t.erro)}</div>`:""}
  ${t.resultado&&t.resultado.resumo?`<details><summary>Resumo do agente</summary><div class="res tx">${esc(t.resultado.resumo)}</div></details>`:""}
  ${t.status==="concluida"?`<button type="button" class="btn sm" data-ia-resultado>${t.resultado?"Resultado disponível":"Etapa concluída"} · Atualizar ficha</button>`:""}</div>`}).join("");
 if(htmlAtualizado(painel,html)){
  painel.querySelectorAll("[data-cancel]").forEach(b=>b.onclick=async()=>{if(confirm("Cancelar a tarefa de IA?")){
   try{const r=await api(`/api/tarefas/${enc(b.dataset.cancel)}/cancelar`,{method:"POST"});if(!r.ok)throw new Error("Cancelamento não confirmado pelo servidor");await atualizarIA();acordarPolling()}catch(e){toast(e.message)}
  }});
  painel.querySelectorAll("[data-ia-resultado]").forEach(b=>b.onclick=()=>{if(id===casoAberto)abrirCaso(id,true)});
 }
 return todos;
}
