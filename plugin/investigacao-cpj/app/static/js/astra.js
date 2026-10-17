// Perguntas locais e histórico em memória, separados por sessão e O.S.
let astraHistoricos=new Map(),astraRascunhos=new Map(),astraUsuario=null,astraCasoMostrado=null;
let astraConsultaCarga=0,astraConsultando=false;

function astraSessaoAtual(){
  const login=S.usuario?.login||null;
  if(login!==astraUsuario){astraUsuario=login;astraHistoricos.clear();astraRascunhos.clear();astraCasoMostrado=null;astraConsultaCarga++;astraConsultando=false}
}

function astraSelecionada(){
  const n=grSelectedNode;
  return n&&grNodes.includes(n)&&n.tipo!=="CASO"?{tipo:n.tipo,valor:n.valor}:null;
}

function astraMostrar(){
  if(!$("#astra-pergunta"))return;
  astraSessaoAtual();const caso=$("#gr-caso").value;
  const rotulo=$("#gr-caso").selectedOptions[0]?.textContent||caso;
  $("#astra-pergunta-contexto").textContent=caso?`${rotulo}${grSelectedNode?" · seleção: "+grSelectedNode.rotulo:" · selecione um nó quando a pergunta precisar de identificador"}`:"Selecione uma O.S. para contextualizar a pergunta.";
  if(caso!==astraCasoMostrado){astraCasoMostrado=caso;$("#astra-pergunta").value=astraRascunhos.get(caso)||"";$("#astra-pergunta-aviso").textContent="";astraRenderizarHistorico(caso)}
  $("#b-astra-perguntar").disabled=astraConsultando||!pode("pesquisa");
}

function astraRenderizarHistorico(caso){
  const h=astraHistoricos.get(caso)||[],painel=$("#astra-respostas");
  painel.innerHTML=h.map((item,i)=>`<article class="astra-resposta" style="margin-top:12px;border-top:1px solid var(--line);padding-top:8px;overflow-wrap:anywhere">
    <p><b>Pergunta:</b> ${esc(item.pergunta)}</p><p>${esc(item.resultado.resposta)}</p>
    ${(item.resultado.avisos||[]).map(a=>`<p class="aviso">${esc(a)}</p>`).join("")}
    ${(item.resultado.opcoes||[]).map((o,j)=>`<div><button class="btn sm" data-astra-opcao="${i}:${j}">${esc(o.rotulo)} · ${esc(o.valor)}</button>${grEvidenciasHTML({evidencias:o.fontes||[]})}</div>`).join("")}
    ${(item.resultado.grafo.arestas||[]).map((a,j)=>`<div style="margin-top:8px"><b>${esc(a.a_valor)} → ${esc(a.b_valor)}</b><div>${esc(a.relacao)}</div>
      <button class="btn sm" data-astra-relacao="${i}:${j}">Ver relação no grafo</button>${grEvidenciasHTML(a)}</div>`).join("")}
    </article>`).join("");
  painel.querySelectorAll("[data-astra-opcao]").forEach(b=>b.onclick=()=>{
    const [i,j]=b.dataset.astraOpcao.split(":").map(Number),item=h[i],o=item.resultado.opcoes[j];
    astraPerguntar(item.pergunta,{tipo:o.tipo,valor:o.valor});
  });
  painel.querySelectorAll("[data-astra-relacao]").forEach(b=>b.onclick=()=>{
    if(!confirmarSaidaEditor())return;
    const [i,j]=b.dataset.astraRelacao.split(":").map(Number),item=h[i],a=item.resultado.grafo.arestas[j];
    // O recorte é o da resposta explícita, com tuplas e fontes fornecidas pela API.
    grCarga++;
    grDados={...grDados,...item.resultado.grafo,truncado:item.resultado.truncado,
      completude:item.resultado.truncado?"parcial":"completa_no_escopo",indice_disponivel:true,
      pagina:1,total:item.resultado.total,limite:item.resultado.limite,proxima_pagina:null,revisao:null,
      aviso:"Recorte da pergunta: "+item.resultado.avisos.join(" ")};
    if(item.resultado.intencao.filtros.escopo==="todas_os")$("#gr-caso").value="";
    $("#gr-busca").value="";
    grEstado="pronto";grMontarGrafo();
    const edge=grEdges.find(e=>e.relacao_id===a.relacao_id);
    if(edge)grInspecionarAresta(edge);
    astraMostrar();
    $("#cv-grafo").scrollIntoView({behavior:"smooth",block:"center"});
  });
}

async function astraPerguntar(pergunta,entidade){
  astraSessaoAtual();const caso=$("#gr-caso").value,aviso=$("#astra-pergunta-aviso");
  if(!caso){aviso.textContent="Selecione uma O.S. antes de perguntar.";return}
  if(grEstado==="carregando"){aviso.textContent="Aguarde o carregamento do recorte antes de consultar a seleção.";return}
  if(astraConsultando)return;
  if(!pergunta.trim()){aviso.textContent="Escreva a pergunta.";return}
  const carga=++astraConsultaCarga,login=astraUsuario;
  astraConsultando=true;astraRascunhos.set(caso,pergunta);$("#b-astra-perguntar").disabled=true;aviso.textContent="Consultando os materiais indexados localmente…";
  const json={caso,pergunta};if(entidade)json.entidade=entidade;
  try{
    const resultado=await api("/api/astra/perguntar",{json});
    if(carga!==astraConsultaCarga||login!==(S.usuario?.login||null))return;
    const itens=astraHistoricos.get(caso)||[];itens.push({pergunta,resultado});
    astraHistoricos.set(caso,itens.slice(-10));
    if($("#gr-caso").value===caso){aviso.textContent="Consulta concluída. Confira as fontes e os limites da resposta.";astraRenderizarHistorico(caso)}
  }catch(x){if(carga===astraConsultaCarga&&$("#gr-caso").value===caso)aviso.textContent=`Consulta indisponível: ${x.message}. A pergunta foi preservada; tente novamente.`}
  finally{if(carga===astraConsultaCarga){astraConsultando=false;astraMostrar()}}
}

function astraMontar(){
  const grafo=$("#grafo");if(!grafo||$("#astra-perguntar"))return;
  const secao=document.createElement("section");secao.id="astra-perguntar";secao.className="card";
  secao.innerHTML=`<h3>Pergunte ao ASTRA</h3><p class="muted">Consulta local às referências indexadas. Pergunte sobre contas recebedoras, O.S. de uma chave Pix, vínculos candidatos ou documentos do caminho do dinheiro.</p>
    <p id="astra-pergunta-contexto" class="muted"></p><form id="f-astra-pergunta"><label for="astra-pergunta">Pergunta</label>
    <textarea id="astra-pergunta" rows="2" maxlength="2000" style="width:100%" placeholder="Quais documentos sustentam este caminho do dinheiro?"></textarea>
    <div class="acoes"><button class="btn pri" type="submit" id="b-astra-perguntar">Perguntar</button><button class="btn" type="button" id="b-astra-limpar">Limpar histórico desta O.S.</button></div></form>
    <div role="status" id="astra-pergunta-aviso"></div><p class="muted">Até 10 perguntas por O.S. nesta sessão. Recarregar ou sair limpa o histórico.</p><div id="astra-respostas"></div>`;
  grafo.append(secao);
  $("#f-astra-pergunta").onsubmit=e=>{e.preventDefault();astraPerguntar($("#astra-pergunta").value,astraSelecionada())};
  $("#astra-pergunta").oninput=()=>astraRascunhos.set($("#gr-caso").value,$("#astra-pergunta").value);
  $("#b-astra-limpar").onclick=()=>{const caso=$("#gr-caso").value;astraConsultaCarga++;astraConsultando=false;astraHistoricos.delete(caso);astraRascunhos.delete(caso);$("#astra-pergunta").value="";$("#astra-pergunta-aviso").textContent="Histórico desta O.S. limpo.";astraRenderizarHistorico(caso);astraMostrar()};
  $("#gr-caso").addEventListener("change",astraMostrar);
  const observer=new MutationObserver(astraMostrar);
  observer.observe(grafo,{attributes:true,attributeFilter:["class"]});
  observer.observe($("#app"),{attributes:true,attributeFilter:["hidden"]});
  observer.observe($("#u-nome"),{childList:true});
  observer.observe($("#gr-detalhes-conteudo"),{childList:true});
  astraMostrar();
}

if(typeof window!=="undefined"&&window.addEventListener)window.addEventListener("load",astraMontar);
