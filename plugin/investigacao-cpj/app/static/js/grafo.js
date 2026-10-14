// ---------------- grafo relacional

let grDados={nos:[],arestas:[],casos:[]}, grNodes=[], grEdges=[], grNodeMap=new Map();

let grZoom=1.0, grPanX=0, grPanY=0;

let grDraggingNode=null, grHoveredNode=null, grSelectedNode=null;
let grSelectedEdge=null;

let grIsPanning=false, grStartPan={x:0,y:0}, grMouseDownPos={x:0,y:0};

let grAnimId=null, grEnergy=1.0, grInitialized=false;
let grCarga=0, grEstado="pronto", grErro="";
let grAjustarAoEstabilizar=false;



const GR_TIPOS={

  CASO:      {cor:"#A78BFA",r:16,cat:"caso",label:"Caso"},

  PESSOA:    {cor:"#38BDF8",r:12,cat:"pessoa",label:"Pessoa"},

  NOME:      {cor:"#38BDF8",r:11,cat:"pessoa",label:"Nome"},

  CONTA:     {cor:"#34D399",r:11,cat:"conta",label:"Conta"},

  CHAVE_PIX: {cor:"#10B981",r:11,cat:"conta",label:"Pix"},

  CPF:       {cor:"#F43F5E",r:11,cat:"doc",label:"CPF"},

  CNPJ:      {cor:"#FB7185",r:11,cat:"doc",label:"CNPJ"},

  TELEFONE:  {cor:"#FBBF24",r:10,cat:"tel",label:"Telefone"},

  EMAIL:     {cor:"#F59E0B",r:10,cat:"tel",label:"E-mail"},

  ENDERECO:  {cor:"#FB923C",r:9,cat:"outros",label:"Endereço"},

  PLACA:     {cor:"#F97316",r:9,cat:"outros",label:"Placa"},

  PROCESSO:  {cor:"#C084FC",r:9,cat:"outros",label:"Processo"},

  BO:        {cor:"#E879F9",r:9,cat:"outros",label:"BO"}

};

function grGetCfg(tipo){return GR_TIPOS[tipo]||{cor:"#94A3B8",r:9,cat:"outros",label:tipo}}

function grCatAtiva(cat){

  if(cat==="caso")return $("#gf-caso")?$("#gf-caso").checked:true;

  if(cat==="pessoa")return $("#gf-pessoa")?$("#gf-pessoa").checked:true;

  if(cat==="conta")return $("#gf-conta")?$("#gf-conta").checked:true;

  if(cat==="doc")return $("#gf-doc")?$("#gf-doc").checked:true;

  if(cat==="tel")return $("#gf-tel")?$("#gf-tel").checked:true;

  if(cat==="outros")return $("#gf-outros")?$("#gf-outros").checked:true;

  return true;

}

function grResizeCanvas(){

  const cv=$("#cv-grafo");if(!cv)return;

  const rect=cv.getBoundingClientRect(),dpr=window.devicePixelRatio||1;

  const w=Math.floor(rect.width)||800,h=Math.floor(rect.height)||560;

  if(cv.width!==w*dpr||cv.height!==h*dpr){cv.width=w*dpr;cv.height=h*dpr}

}

function grAtualizarCasos(data, selecionado){
  const sel=$("#gr-caso");if(!sel)return;
  const ordens=Array.isArray(data.ordens_servico)?data.ordens_servico:
    (data.casos||[]).map(id=>({id,ordem_servico:id}));
  const lista=ordens.slice().sort(compararNumeroOS);
  sel.innerHTML='<option value="">Todas as O.S. (conexões gerais)</option>'+lista.map(c=>{
    const os=c.ordem_servico||c.id;
    return `<option value="${esc(c.id)}">${esc(os===c.id?os:"O.S. "+os)}</option>`;
  }).join("");
  sel.value=lista.some(c=>c.id===selecionado)?selecionado:"";
}

function grAtualizarEstado(visNodes, conexoes){
  const msg=$("#gr-mensagem"),status=$("#gr-status");let texto="";
  if(grEstado==="carregando")texto="Carregando vínculos e lista de O.S.…";
  else if(grEstado==="erro")texto="Não foi possível carregar o grafo: "+grErro+". Clique em Buscar para tentar novamente.";
  else if(grDados.indice_disponivel===false)texto="O índice de vínculos ainda não está disponível. As O.S. cadastradas continuam disponíveis no seletor.";
  else if(!grNodes.length){
    const q=$("#gr-busca").value.trim(),caso=$("#gr-caso").value;
    texto=q?"Nenhum vínculo encontrado para esta busca"+(caso?" nesta O.S.":"")+". Experimente outro nome ou identificador, ou limpe a busca.":
      caso?"Esta O.S. ainda não possui vínculos disponíveis no índice. O cadastro da O.S. pode ser consultado na aba Casos.":
      "Ainda não há vínculos disponíveis no índice. Selecione uma O.S. ou consulte o cadastro na aba Casos.";
  }else if(!visNodes.length)texto="Todos os nós estão ocultos pelos filtros. Marque um dos tipos acima para exibir o grafo.";
  if(grEstado==="pronto"){
    const avisos=[grDados.aviso,grDados.truncado===true?"Resultado parcial: há relações adicionais. Refine a busca ou a O.S.":grDados.completude==="nao_aferida"?"Completude não aferida: confira os limites e refine a busca antes de concluir.":""];
    texto=[texto,...avisos.filter(Boolean)].filter(Boolean).join(" ");
  }
  if(msg){msg.textContent=texto;msg.hidden=!texto}
  if(status)status.textContent=grEstado==="carregando"?"Carregando…":grEstado==="erro"?"Falha no carregamento":`${visNodes.length} nós visíveis · ${conexoes} conexões`;
}

async function carregarGrafo(){
  grInitEvents();
  const carga=++grCarga,caso=$("#gr-caso").value,q=$("#gr-busca").value.trim();
  grEstado="carregando";grErro="";grAtualizarEstado([],0);
  try{
    const data=await api(`/api/grafo?caso=${enc(caso)}&q=${enc(q)}`);
    if(carga!==grCarga)return;
    grDados=data;grAtualizarCasos(data,caso);grEstado="pronto";
    grInspecionarNo(null);grHoveredNode=null;grDraggingNode=null;
    grMontarGrafo();grDesenhar();
  }catch(x){
    if(carga!==grCarga)return;
    grDados={nos:[],arestas:[]};grNodes=[];grEdges=[];grNodeMap.clear();
    grEstado="erro";grErro=x.message;grInspecionarNo(null);grDesenhar();
  }
}

function grMontarGrafo(){

  grResizeCanvas();

  const cv=$("#cv-grafo"),dpr=window.devicePixelRatio||1;

  const w=cv?cv.width/dpr:800,h=cv?cv.height/dpr:560;

  const cx=w/2,cy=h/2,radius=Math.min(w,h)*0.38;

  const nTotal=(grDados.nos&&grDados.nos.length)||1;

  grNodeMap.clear();

  grNodes=(grDados.nos||[]).map((n,i)=>{

    const cfg=grGetCfg(n.tipo),ang=(i/nTotal)*2*Math.PI,rDist=radius*(0.3+0.7*Math.random());

    const node={

      id:n.tipo+"|"+n.valor,tipo:n.tipo,valor:n.valor,rotulo:n.rotulo||n.valor,

      cat:cfg.cat,r:cfg.r,cor:cfg.cor,

      x:cx+rDist*Math.cos(ang),y:cy+rDist*Math.sin(ang),vx:0,vy:0

    };

    grNodeMap.set(node.id,node);return node;

  });

  grEdges=[];

  for(const a of (grDados.arestas||[])){

    const s=grNodeMap.get(a.a_tipo+"|"+a.a_valor),t=grNodeMap.get(a.b_tipo+"|"+a.b_valor);

    if(s&&t){

      grEdges.push({...a,source:s,target:t,caso:a.caso||a.fonte,relacao:a.relacao||"vinculado a",origem:a.origem||"",fonte:a.fonte||"",localizador:a.localizador||""});

    }

  }

  grResetView();

  grEnergy=1.0;
  grAjustarAoEstabilizar=true;

  grStartLoop();

}

function grTickPhysics(){

  const visNodes=grNodes.filter(n=>grCatAtiva(n.cat)),nVis=visNodes.length;if(!nVis)return 0;

  const cv=$("#cv-grafo"),dpr=window.devicePixelRatio||1;

  const w=cv.width/dpr,h=cv.height/dpr,cx=w/2,cy=h/2;

  for(let i=0;i<nVis;i++){

    const n=visNodes[i];if(n===grDraggingNode)continue;

    n.vx+=(cx-n.x)*0.0025;n.vy+=(cy-n.y)*0.0025;

  }

  const kRep=3000;

  for(let i=0;i<nVis;i++){

    const a=visNodes[i];

    for(let j=i+1;j<nVis;j++){

      const b=visNodes[j];let dx=b.x-a.x,dy=b.y-a.y,distSq=dx*dx+dy*dy;

      if(distSq<1)distSq=1;if(distSq>160000)continue;

      const dist=Math.sqrt(distSq),f=kRep/distSq,fx=(dx/dist)*f,fy=(dy/dist)*f;

      if(a!==grDraggingNode){a.vx-=fx;a.vy-=fy;}

      if(b!==grDraggingNode){b.vx+=fx;b.vy+=fy;}

    }

  }

  for(const e of grEdges){

    const a=e.source,b=e.target;if(!grCatAtiva(a.cat)||!grCatAtiva(b.cat))continue;

    const dx=b.x-a.x,dy=b.y-a.y,dist=Math.sqrt(dx*dx+dy*dy)||1;

    const targetDist=(a.r+b.r)*3+45,f=(dist-targetDist)*0.035,fx=(dx/dist)*f,fy=(dy/dist)*f;

    if(a!==grDraggingNode){a.vx+=fx;a.vy+=fy;}

    if(b!==grDraggingNode){b.vx-=fx;b.vy-=fy;}

  }

  let totalMove=0;const damping=0.84;

  for(let i=0;i<nVis;i++){

    const n=visNodes[i];if(n===grDraggingNode)continue;

    n.vx*=damping;n.vy*=damping;n.x+=n.vx;n.y+=n.vy;

    totalMove+=Math.abs(n.vx)+Math.abs(n.vy);

  }

  return totalMove/nVis;

}

function grDesenhar(){

  const cv=$("#cv-grafo");if(!cv)return;

  grResizeCanvas();

  const ctx=cv.getContext("2d"),dpr=window.devicePixelRatio||1;

  const w=cv.width/dpr,h=cv.height/dpr;

  ctx.save();ctx.scale(dpr,dpr);

  ctx.fillStyle="#080e1a";ctx.fillRect(0,0,w,h);

  ctx.save();ctx.translate(grPanX,grPanY);ctx.scale(grZoom,grZoom);

  const visNodes=grNodes.filter(n=>grCatAtiva(n.cat)),visSet=new Set(visNodes);

  for(const e of grEdges){

    if(!visSet.has(e.source)||!visSet.has(e.target))continue;

    const isHigh=e===grSelectedEdge||(grSelectedNode&&(e.source===grSelectedNode||e.target===grSelectedNode))||

                 (grHoveredNode&&(e.source===grHoveredNode||e.target===grHoveredNode));

    ctx.beginPath();ctx.moveTo(e.source.x,e.source.y);ctx.lineTo(e.target.x,e.target.y);

    if(isHigh){ctx.strokeStyle="#38BDF8";ctx.lineWidth=2.4;ctx.shadowColor="#0284C7";ctx.shadowBlur=8}

    else{ctx.strokeStyle="rgba(148, 163, 184, 0.28)";ctx.lineWidth=1.2;ctx.shadowBlur=0}

    ctx.stroke();

    const dx=e.target.x-e.source.x,dy=e.target.y-e.source.y,d=Math.sqrt(dx*dx+dy*dy)||1;

    const ux=dx/d,uy=dy/d,arrX=e.target.x-ux*(e.target.r+4),arrY=e.target.y-uy*(e.target.r+4);

    ctx.beginPath();ctx.moveTo(arrX,arrY);

    ctx.lineTo(arrX-ux*7+uy*3.5,arrY-uy*7-ux*3.5);ctx.lineTo(arrX-ux*7-uy*3.5,arrY-uy*7+ux*3.5);

    ctx.closePath();ctx.fillStyle=isHigh?"#38BDF8":"rgba(148, 163, 184, 0.4)";ctx.fill();

    if((grZoom>0.8||isHigh)&&e.relacao){

      const mx=(e.source.x+e.target.x)/2,my=(e.source.y+e.target.y)/2;

      ctx.font="9.5px sans-serif";ctx.fillStyle=isHigh?"#E0F2FE":"rgba(148, 163, 184, 0.75)";

      ctx.textAlign="center";ctx.textBaseline="middle";ctx.fillText(e.relacao,mx,my-4);

    }

  }

  ctx.shadowBlur=0;

  for(const n of visNodes){

    const isSel=(n===grSelectedNode),isHov=(n===grHoveredNode);

    ctx.save();ctx.beginPath();ctx.arc(n.x,n.y,n.r,0,2*Math.PI);

    if(isSel||isHov){ctx.shadowColor=n.cor;ctx.shadowBlur=isSel?16:10}

    ctx.fillStyle=n.cor;ctx.fill();

    ctx.lineWidth=isSel?3:(isHov?2.5:1.5);

    ctx.strokeStyle=isSel?"#FFFFFF":(isHov?"#FFFFFF":"rgba(255, 255, 255, 0.45)");

    ctx.stroke();ctx.restore();

    ctx.font=isSel?"bold 12px sans-serif":(isHov?"bold 11px sans-serif":"11px sans-serif");

    ctx.textAlign="center";ctx.textBaseline="top";

    ctx.lineWidth=3;ctx.strokeStyle="rgba(8, 14, 26, 0.9)";ctx.strokeText(n.rotulo,n.x,n.y+n.r+4);

    ctx.fillStyle=isSel?"#38BDF8":(isHov?"#FFFFFF":"#E2E8F0");

    ctx.fillText(n.rotulo,n.x,n.y+n.r+4);

  }

  ctx.restore();ctx.restore();

  grAtualizarEstado(visNodes,grEdges.filter(e=>visSet.has(e.source)&&visSet.has(e.target)).length);

}

function grStartLoop(){

  if(grAnimId)cancelAnimationFrame(grAnimId);

  function step(){

    if(grEnergy>0.04||grDraggingNode){

      grTickPhysics();

      if(!grDraggingNode)grEnergy*=0.985;

      grDesenhar();grAnimId=requestAnimationFrame(step);

    }else{if(grAjustarAoEstabilizar){grAjustarAoEstabilizar=false;grResetView()}else grDesenhar();grAnimId=null}

  }

  grAnimId=requestAnimationFrame(step);

}

function grScreenToWorld(sx,sy){

  const cv=$("#cv-grafo"),rect=cv.getBoundingClientRect();

  return {x:(sx-rect.left-grPanX)/grZoom,y:(sy-rect.top-grPanY)/grZoom};

}

function grFindNodeAt(wx,wy){

  const visNodes=grNodes.filter(n=>grCatAtiva(n.cat));

  for(let i=visNodes.length-1;i>=0;i--){

    const n=visNodes[i],dx=wx-n.x,dy=wy-n.y;

    if(dx*dx+dy*dy<=(n.r+5)*(n.r+5))return n;

  }

  return null;

}

function grFontes(aresta){
  if(Array.isArray(aresta.evidencias))return aresta.evidencias;
  return [{tipo:aresta.origem==="manual"?"hipotese_manual":"documental",origem:aresta.origem,
    caso:aresta.caso||aresta.fonte,documento:aresta.evidencia?.documento,pagina:aresta.evidencia?.pagina,
    fls:aresta.evidencia?.fls,observacao:aresta.evidencia?.observacao,localizador_original:aresta.localizador,
    manual_id:aresta.id,manual_versao:aresta.versao}];
}

function grFindEdgeAt(wx,wy){
  let escolhido=null,menor=(6/grZoom)**2;
  for(const e of grEdges){
    if(!grCatAtiva(e.source.cat)||!grCatAtiva(e.target.cat))continue;
    const a=e.source,b=e.target,dx=b.x-a.x,dy=b.y-a.y,d2=dx*dx+dy*dy;
    const t=d2?Math.max(0,Math.min(1,((wx-a.x)*dx+(wy-a.y)*dy)/d2)):0;
    const d=(wx-a.x-t*dx)**2+(wy-a.y-t*dy)**2;
    if(d<=menor){menor=d;escolhido=e}
  }
  return escolhido;
}

function grRevisaoHTML(e,chave){
  const r=e.revisao||{},escrita=pode("trabalho")&&e.caso&&e.id;
  const registro=r.versao?`<div>${r.fonte_conferida?`Registro de conferência ${r.recurso_conferido==="original"?"do original":"da extração/registro"} por ${esc(r.fonte_usuario||r.usuario||"responsável não informado")} em ${esc(r.fonte_data||r.data||"data não informada")}. `:""}${r.candidato?"Candidato marcado pelo operador. ":""}Último registro: ${esc(r.usuario||"Responsável não informado")} · ${esc(r.data||"Data não informada")}</div>`:"";
  return `${registro}${escrita?`<div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:6px">
    ${e.url_original?`<button class="btn sm" data-gr-revisar="${chave}" data-acao="conferir_fonte" data-fonte="original">Conferi o original</button>`:""}
    ${e.url_derivado?`<button class="btn sm" data-gr-revisar="${chave}" data-acao="conferir_fonte" data-fonte="derivado">Conferi a extração/registro</button>`:""}
    <button class="btn sm" data-gr-revisar="${chave}" data-acao="marcar_candidato">Marcar como candidato</button>
    </div><label style="display:block;margin-top:6px">Observação/hipótese do operador
    <textarea data-gr-observacao="${chave}" rows="2" maxlength="4000" style="width:100%">${esc(r.observacao||"")}</textarea></label>
    <button class="btn sm" data-gr-revisar="${chave}" data-acao="registrar_observacao">Registrar observação/hipótese</button>`:""}
    ${e.caso&&e.id?`<button class="btn sm" data-gr-historico="${chave}">Ver histórico</button>`:""}
    <div class="muted" role="status" data-gr-revisao-aviso></div><div data-gr-historico-conteudo></div>`;
}

function grIdentificarFonte(aresta,e){
  return {caso:e.caso,a_tipo:aresta.a_tipo,a_valor:aresta.a_valor,b_tipo:aresta.b_tipo,
    b_valor:aresta.b_valor,relacao:aresta.relacao,evidencia_id:e.id};
}

function grAtualizarInspetor(){
  if(grSelectedEdge)grInspecionarAresta(grSelectedEdge);
  else if(grSelectedNode)grInspecionarNo(grSelectedNode);
}

function grVincularFontes(p,arestas){
  const fonte=b=>{const [i,j]=(b.dataset.grRevisar||b.dataset.grHistorico||b.dataset.grManual).split(":").map(Number);
    return {aresta:arestas[i],e:grFontes(arestas[i])[j],card:b.closest(".gr-evidencia")}};
  p.querySelectorAll("[data-gr-manual]").forEach(b=>b.onclick=()=>{
    const {aresta,e}=fonte(b);
    grRemoverVinculo({origem:"manual",id:e.manual_id,versao:e.manual_versao,caso:e.caso,relacao:aresta.relacao},b);
  });
  p.querySelectorAll("[data-gr-revisar]").forEach(b=>b.onclick=async()=>{
    const {aresta,e,card}=fonte(b),aviso=card.querySelector("[data-gr-revisao-aviso]"),acao=b.dataset.acao;
    const dados={...grIdentificarFonte(aresta,e),versao:e.revisao?.versao||0,acao};
    if(acao==="registrar_observacao"){
      dados.observacao=card.querySelector("textarea").value;
      if(!dados.observacao.trim()){aviso.textContent="Escreva a observação antes de registrar.";return}
    }
    if(acao==="conferir_fonte")dados.fonte=b.dataset.fonte;
    const carga=grCarga,controles=card.querySelectorAll("[data-gr-revisar]");
    controles.forEach(el=>el.disabled=true);aviso.textContent="Registrando conferência…";
    try{
      const r=await api("/api/grafo/evidencia/revisar",{json:dados});
      e.revisao=r.revisao;
      if(carga===grCarga&&card.isConnected){
        const rascunhos=new Map([...p.querySelectorAll("[data-gr-observacao]")].map(el=>[el.dataset.grObservacao,el.value]));
        grAtualizarInspetor();
        p.querySelectorAll("[data-gr-observacao]").forEach(el=>{if(rascunhos.has(el.dataset.grObservacao))el.value=rascunhos.get(el.dataset.grObservacao)});
        toast("Registro humano salvo; a natureza da evidência foi preservada.");
      }
    }catch(x){if(card.isConnected)aviso.textContent=x.message}
    finally{controles.forEach(el=>el.disabled=false)}
  });
  p.querySelectorAll("[data-gr-historico]").forEach(b=>b.onclick=async()=>{
    const {aresta,e,card}=fonte(b),alvo=card.querySelector("[data-gr-historico-conteudo]");
    b.disabled=true;alvo.textContent="Carregando histórico…";
    try{
      const q=new URLSearchParams(grIdentificarFonte(aresta,e));
      const r=await api("/api/grafo/evidencia/historico?"+q);
      if(!card.isConnected)return;
      const acoes={conferir_fonte:"Conferência de fonte",marcar_candidato:"Candidato marcado",registrar_observacao:"Observação/hipótese"};
      alvo.innerHTML=r.historico.length?r.historico.map(h=>`<div style="border-top:1px solid var(--line);padding:6px 0;white-space:pre-wrap">${esc(acoes[h.acao]||h.acao)}${h.recurso_conferido?" · "+esc(h.recurso_conferido):""}<br>${esc(h.usuario)} · ${esc(h.data)}${h.observacao?"<br>"+esc(h.observacao):""}</div>`).join(""):"Nenhuma conferência humana registrada.";
    }catch(x){if(card.isConnected)alvo.textContent=x.message}
    finally{b.disabled=false}
  });
}

function grEvidenciasHTML(aresta,acoes=false,conexao=0){
  const nomes={documental:"Referência documental — conferir original",cadastro:"Cadastro do caso — conferir fonte",
    consulta:"Base de consulta — não substitui os autos",extracao_candidata:"Extração candidata — conferir texto e original",
    hipotese_manual:"Hipótese manual",correspondencia_candidata:"Correspondência candidata por nome",
    origem_desconhecida:"Origem não identificada — conferir referência"};
  const fontes=grFontes(aresta);
  const link=(url,texto)=>typeof url==="string"&&/^\/arquivo\/[^?#]+(?:#page=\d+)?$/.test(url)?`<a class="lk" href="${esc(url)}" target="_blank" rel="noopener">${esc(texto)}</a>`:"";
  return `<details open style="margin-top:8px"><summary>Fontes (${fontes.length})</summary>${fontes.map((e,i)=>{
    const conferencia=e.revisao?.fonte_conferida?{estado:"conferida_pelo_operador",usuario:e.revisao.fonte_usuario,data:e.revisao.fonte_data}:e.conferencia;
    const conferida=conferencia?.estado==="conferida_pelo_operador"&&conferencia.usuario&&conferencia.data;
    let localizador=e.localizador_original;
    try{const meta=JSON.parse(localizador);if(["astra-evidencia/1","astra-manual/1"].includes(meta?.schema))localizador=typeof meta.localizador_original==="string"?meta.localizador_original:""}catch{}
    const original=link(e.url_original,e.pagina?`Abrir original · pág. ${e.pagina}`:"Abrir original");
    const derivado=link(e.url_derivado,"Ver extração ou registro");
    return `<div class="gr-evidencia" style="border-top:1px solid var(--line);padding:8px 0;overflow-wrap:anywhere">
      <b>${esc(nomes[e.tipo]||"Referência a conferir")}</b>
      <div>${esc(e.caso||e.origem||"Origem não informada")} · ${esc(e.documento||e.arquivo_derivado||"Documento não identificado")}</div>
      <div class="muted">${e.pagina?`pág. ${esc(e.pagina)} · `:""}${e.fls?`fls. ${esc(e.fls)}`:"Fls. não informadas"}</div>
      ${localizador?`<div class="muted">${esc(localizador)}</div>`:""}
      ${e.trecho?`<blockquote style="margin:6px 0;white-space:pre-wrap">${esc(e.trecho)}</blockquote>`:""}
      ${e.status_fonte?`<div>Status declarado na fonte: ${esc(e.status_fonte)}</div>`:""}
      ${e.posicao==="contradiz"?'<div>Referência registrada como contraditória.</div>':""}
      ${e.observacao?`<div style="white-space:pre-wrap">Observação do operador: ${esc(e.observacao)}</div>`:""}
      <div class="muted">${conferida?`Conferência humana registrada por ${esc(conferencia.usuario)} em ${esc(conferencia.data)}`:"Conferência humana não registrada"}</div>
      ${original||derivado?`<div style="display:flex;gap:12px;flex-wrap:wrap">${original}${derivado}</div>`:'<div class="muted">Fonte indisponível para abertura; referência preservada.</div>'}
      ${e.avisos?.length?`<div class="muted">${esc(e.avisos.join(" · "))}</div>`:""}
      ${acoes?grRevisaoHTML(e,`${conexao}:${i}`):""}
      ${acoes&&e.manual_id&&pode("trabalho")?`<button class="btn sm dan" data-gr-manual="${conexao}:${i}">remover</button>`:""}
    </div>`;
  }).join("")}${aresta.evidencias_truncadas?'<div class="aviso">Há referências adicionais não carregadas.</div>':""}</details>`;
}

function grInspecionarNo(n){

  grSelectedNode=n;grSelectedEdge=null;const p=$("#gr-detalhes-conteudo");

  if(!n){p.innerHTML="";$("#gr-d-dica").hidden=false;return}

  $("#gr-d-dica").hidden=true;const cfg=grGetCfg(n.tipo),conex=[];

  for(const e of grEdges){

    if(e.source===n)conex.push({outro:e.target,rel:e.relacao,dir:"saida",origem:e.origem,fonte:e.fonte,loc:e.localizador,edge:e});

    else if(e.target===n)conex.push({outro:e.source,rel:e.relacao,dir:"entrada",origem:e.origem,fonte:e.fonte,loc:e.localizador,edge:e});

  }

  let h=`<div style="margin-bottom:12px;padding-bottom:10px;border-bottom:1px solid var(--line)">

    <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px">

      <span class="badge" style="background:${cfg.cor}22;color:${cfg.cor};border:1px solid ${cfg.cor}55">${esc(cfg.label)}</span>

      <b style="font-size:13px">${esc(n.rotulo)}</b>

    </div>

    <div class="muted" style="word-break:break-all">${esc(n.valor)}</div>

    ${n.tipo==="CASO"?'<div style="margin-top:8px"><button class="btn sm pri" data-gr-acao="caso">Abrir este Caso (O.S.)</button></div>':""}
    ${["PESSOA","CPF","CONTA","CHAVE_PIX"].includes(n.tipo)?'<div style="margin-top:8px"><button class="btn sm" data-gr-acao="pesquisa">Explorar na Pesquisa</button></div>':""}
    ${pode("trabalho")?'<div style="margin-top:6px"><button class="btn sm pri" data-gr-acao="novo">+ Criar Vínculo deste Nó</button></div>':""}

  </div>

  <h4 style="margin:0 0 6px">Conexões diretas (${conex.length})</h4>`;

  if(!conex.length){h+='<div class="muted">Nenhuma conexão direta encontrada.</div>'}

  else{

    h+=`<div style="display:flex;flex-direction:column;gap:8px">`+conex.map((c,i)=>`

      <div style="background:var(--page);border:1px solid var(--line);border-radius:6px;padding:7px 10px;font-size:12px">

        <div style="display:flex;justify-content:space-between;gap:6px">

          <span class="muted">${c.dir==="saida"?"➔ ":"➔ "}${esc(c.rel)}</span>

          <span class="badge" style="font-size:10px">${esc(c.outro.tipo)}</span>

        </div>

        <div style="margin-top:3px"><a class="lk" data-gr-focar="${i}"><b>${esc(c.outro.rotulo)}</b></a></div>

        ${c.edge.naturezas?.includes("correspondencia_candidata")?'<div class="muted">Nome candidato: a identidade não foi confirmada.</div>':""}
        ${grEvidenciasHTML(c.edge,true,i)}

      </div>`).join("")+`</div>`;

  }

  p.innerHTML=h;
  grVincularFontes(p,conex.map(c=>c.edge));
  p.querySelectorAll("[data-gr-focar]").forEach(b=>b.onclick=()=>grFocarNo(conex[Number(b.dataset.grFocar)].outro.id));
  p.querySelectorAll("[data-gr-acao]").forEach(b=>b.onclick=()=>{
    if(b.dataset.grAcao==="caso"){abrirAba("casos");abrirCaso(n.valor)}
    else if(b.dataset.grAcao==="pesquisa")verVinculos(n.tipo,n.valor,n.rotulo);
    else grAbrirModalVinculo(n.tipo,n.valor);
  });
  grDesenhar();

}

function grInspecionarAresta(e){
  if(!e){grInspecionarNo(null);return}
  grSelectedNode=null;grSelectedEdge=e;
  const p=$("#gr-detalhes-conteudo");$("#gr-d-dica").hidden=true;
  p.innerHTML=`<div style="overflow-wrap:anywhere"><b>${esc(e.source.rotulo)}</b> → <b>${esc(e.target.rotulo)}</b>
    <div>${esc(e.relacao)}</div>${e.naturezas?.includes("correspondencia_candidata")?'<div>Correspondência candidata; identidade não confirmada.</div>':""}
    ${grEvidenciasHTML(e,true,0)}</div>`;
  grVincularFontes(p,[e]);grDesenhar();
}

function grFocarNo(id){

  const n=grNodeMap.get(id);

  if(n){

    grInspecionarNo(n);

    const cv=$("#cv-grafo"),dpr=window.devicePixelRatio||1;

    const w=cv.width/dpr,h=cv.height/dpr;

    grPanX=(w/2)-n.x*grZoom;grPanY=(h/2)-n.y*grZoom;grDesenhar();

  }

}

function grResetView(){

  const cv=$("#cv-grafo");if(!cv)return;

  grResizeCanvas();

  const dpr=window.devicePixelRatio||1,w=cv.width/dpr,h=cv.height/dpr;

  const visNodes=grNodes.filter(n=>grCatAtiva(n.cat));

  if(!visNodes.length){grZoom=1.0;grPanX=0;grPanY=0;grDesenhar();return}

  let minX=Infinity,maxX=-Infinity,minY=Infinity,maxY=-Infinity;

  for(const n of visNodes){

    if(n.x<minX)minX=n.x;if(n.x>maxX)maxX=n.x;

    if(n.y<minY)minY=n.y;if(n.y>maxY)maxY=n.y;

  }

  const pad=60,gw=(maxX-minX)||100,gh=(maxY-minY)||100;

  const zx=(w-pad*2)/gw,zy=(h-pad*2)/gh;

  grZoom=Math.max(0.35,Math.min(1.5,Math.min(zx,zy)));

  grPanX=(w/2)-((minX+maxX)/2)*grZoom;

  grPanY=(h/2)-((minY+maxY)/2)*grZoom;

  grDesenhar();

}

function grInitEvents(){

  if(grInitialized)return;grInitialized=true;

  const cv=$("#cv-grafo");if(!cv)return;

  cv.addEventListener("wheel",e=>{

    e.preventDefault();
    grAjustarAoEstabilizar=false;

    const rect=cv.getBoundingClientRect(),mx=e.clientX-rect.left,my=e.clientY-rect.top;

    const factor=e.deltaY<0?1.15:0.87,newZoom=Math.max(0.2,Math.min(4.0,grZoom*factor));

    grPanX=mx-(mx-grPanX)*(newZoom/grZoom);

    grPanY=my-(my-grPanY)*(newZoom/grZoom);

    grZoom=newZoom;grDesenhar();

  },{passive:false});

  cv.addEventListener("mousedown",e=>{
    grAjustarAoEstabilizar=false;

    const pt=grScreenToWorld(e.clientX,e.clientY);grMouseDownPos={x:e.clientX,y:e.clientY};

    const n=grFindNodeAt(pt.x,pt.y);

    if(n){grDraggingNode=n;grEnergy=1.0;grStartLoop()}

    else{grIsPanning=true;grStartPan={x:e.clientX-grPanX,y:e.clientY-grPanY}}

  });

  window.addEventListener("mousemove",e=>{

    if(grDraggingNode){

      const pt=grScreenToWorld(e.clientX,e.clientY);

      grDraggingNode.x=pt.x;grDraggingNode.y=pt.y;grDraggingNode.vx=0;grDraggingNode.vy=0;

      grDesenhar();

    }else if(grIsPanning){

      grPanX=e.clientX-grStartPan.x;grPanY=e.clientY-grStartPan.y;grDesenhar();

    }else{

      const rect=cv.getBoundingClientRect();

      if(e.clientX>=rect.left&&e.clientX<=rect.right&&e.clientY>=rect.top&&e.clientY<=rect.bottom){

        const pt=grScreenToWorld(e.clientX,e.clientY),n=grFindNodeAt(pt.x,pt.y);

        if(n!==grHoveredNode){grHoveredNode=n;cv.style.cursor=n?"pointer":"grab";grDesenhar()}

      }

    }

  });

  window.addEventListener("mouseup",e=>{

    const dist=Math.hypot(e.clientX-grMouseDownPos.x,e.clientY-grMouseDownPos.y);

    if(grDraggingNode&&dist<5){grInspecionarNo(grDraggingNode)}

    else if(!grDraggingNode&&grIsPanning&&dist<5){

      const pt=grScreenToWorld(e.clientX,e.clientY),n=grFindNodeAt(pt.x,pt.y);

      if(!n)grInspecionarAresta(grFindEdgeAt(pt.x,pt.y));

    }

    grDraggingNode=null;grIsPanning=false;

  });

  cv.addEventListener("dblclick",()=>grResetView());

  ["#gf-caso","#gf-pessoa","#gf-conta","#gf-doc","#gf-tel","#gf-outros"].forEach(id=>{

    const el=$(id);if(el)el.onchange=()=>{grEnergy=0.5;grStartLoop()};

  });

  if($("#b-gr-buscar"))$("#b-gr-buscar").onclick=()=>carregarGrafo();

  if($("#gr-busca"))$("#gr-busca").onkeydown=e=>{if(e.key==="Enter")carregarGrafo()};

  if($("#gr-caso"))$("#gr-caso").onchange=()=>carregarGrafo();

  if($("#b-gr-reset"))$("#b-gr-reset").onclick=()=>grResetView();

  if($("#b-gr-foto"))$("#b-gr-foto").onclick=()=>{

    grDesenhar();const a=document.createElement("a");

    a.download=`grafo-relacional-sip-${hoje()}.png`;a.href=cv.toDataURL("image/png");a.click();

    toast("Imagem PNG do grafo salva");

  };

}



