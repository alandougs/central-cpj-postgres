// ---------------- grafo relacional

let grDados={nos:[],arestas:[],casos:[]}, grNodes=[], grEdges=[], grNodeMap=new Map();

let grZoom=1.0, grPanX=0, grPanY=0;

let grDraggingNode=null, grHoveredNode=null, grSelectedNode=null;
let grSelectedEdge=null;

let grIsPanning=false, grStartPan={x:0,y:0}, grMouseDownPos={x:0,y:0};

let grAnimId=null, grEnergy=1.0, grInitialized=false;
let grCarga=0, grEstado="pronto", grErro="";
let grAjustarAoEstabilizar=false;
let grPaginaContexto=null,grMaisEmCurso=false,grPaginaErro="",grPaginaOperacao=0;



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

// Layout em memória da sessão; os dados investigativos permanecem completos.
let grVistas=new Map(),grPosicoes=new Map(),grVistaChave=null,grDominioChave=null;
let grCentro={x:400,y:280},grSimulando=false,grTicks=0,grQuietTicks=0,grLayoutEstado="parado";
let grMovimentoMax=0,grDrawDirty=false,grVisCache=null,grHitCache=null,grSize=null;
let grRepulsionPairs=0,grRotulosMedidas=new Map();
let grAgrupar=false,grExpandidos=new Set(),grProjecao=null;
const GR_RAIO_REPULSAO=400,GR_MAX_TICKS=360,GR_QUIET_TICKS=8;
function grHashID(value){let h=2166136261;for(let i=0;i<value.length;i++){h^=value.charCodeAt(i);h=Math.imul(h,16777619)}h^=h>>>16;h=Math.imul(h,0x7feb352d);h^=h>>>15;h=Math.imul(h,0x846ca68b);return(h^(h>>>16))>>>0}
function grChavesVista(){return{dominio:$("#gr-caso")?.value||"",vista:JSON.stringify([$("#gr-caso")?.value||"",($("#gr-busca")?.value||"").trim().toLowerCase()])}}
function grGuardarVista(){
  if(grVistaChave===null)return;
  let pos=grPosicoes.get(grDominioChave);if(!pos)grPosicoes.set(grDominioChave,pos=new Map());
  for(const n of grNodes)pos.set(n.id,{x:n.x,y:n.y,vx:n.vx,vy:n.vy,fixo:!!n.fixo});
  const anterior=grVistas.get(grVistaChave)||{};
  grVistas.set(grVistaChave,{...anterior,zoom:grZoom,panX:grPanX,panY:grPanY,selecao:grSelectedNode?.id||null,aresta:typeof grSelectedEdge!=="undefined"&&grSelectedEdge?grChaveAresta(grSelectedEdge):null,
    centro:{...grCentro},simulando:grSimulando,ticks:grTicks,quietTicks:grQuietTicks,estado:grLayoutEstado});
}
function grVisiveis(){
  const categorias=["caso","pessoa","conta","doc","tel","outros"],ativos=new Map(categorias.map(c=>[c,grCatAtiva(c)]));
  const chave=categorias.map(c=>ativos.get(c)?"1":"0").join("");
  if(grVisCache?.nodes===grNodes&&grVisCache?.edges===grEdges&&grVisCache.chave===chave)return grVisCache;
  const nos=grNodes.filter(n=>ativos.get(n.cat)!==false),ids=new Set(nos);
  grHitCache=null;grProjecao=null;
  return grVisCache={nodes:grNodes,edges:grEdges,chave,nos,arestas:grEdges.filter(e=>ids.has(e.source)&&ids.has(e.target))};
}
function grInvalidarEspaco(){grHitCache=null;grProjecao=null}
function grEstaVisivel(){
  if(typeof document!=="undefined"&&document.hidden)return false;
  const aba=$("#grafo"),app=$("#app");
  return (!aba?.classList||aba.classList.contains("on"))&&app?.hidden!==true;
}
function grPedirDesenho(){grDrawDirty=true;grStartLoop()}
function grVisibilidadeMudou(){
  if(!grEstaVisivel()){if(grAnimId!==null)cancelAnimationFrame(grAnimId);grAnimId=null;return}
  if(grSimulando||grDrawDirty)grStartLoop();
}
function grReaquecer(){grEnergy=1;grSimulando=true;grTicks=0;grQuietTicks=0;grLayoutEstado="movendo";grPedirDesenho()}
function grDentro(x,y,pad,b){return x+pad>=b.x0&&x-pad<=b.x1&&y+pad>=b.y0&&y-pad<=b.y1}
function grMedirRotulo(ctx,texto,fonte){const chave=fonte+"|"+texto;if(!grRotulosMedidas.has(chave)){ctx.font=fonte;grRotulosMedidas.set(chave,ctx.measureText(texto).width)}return grRotulosMedidas.get(chave)}

function grChaveAresta(e){return e.relacao_id||JSON.stringify([e.a_tipo,e.a_valor,e.b_tipo,e.b_valor,e.relacao])}

function grMostrarAgrupamento(ativo){
  grAgrupar=!!ativo;grExpandidos.clear();grInvalidarEspaco();
  const b=$("#b-gr-agrupar");if(b){b.textContent=ativo?"Mostrar todos os nós":"Agrupar visualmente";b.setAttribute("aria-pressed",String(!!ativo))}
  grPedirDesenho();
}

function grProjetar(){
  const vis=grVisiveis();
  if(!grAgrupar)return vis;
  if(grProjecao?.vis===vis&&grProjecao.zoom===grZoom&&grProjecao.selecao===grSelectedNode&&grProjecao.aresta===grSelectedEdge)return grProjecao;
  const cells=new Map(),nos=[],mapa=new Map(),cell=96/grZoom;
  for(const n of vis.nos){
    if(n===grSelectedNode||n===grSelectedEdge?.source||n===grSelectedEdge?.target||grExpandidos.has(n.id)){nos.push(n);mapa.set(n.id,n);continue}
    const key=n.cat+"|"+Math.floor(n.x/cell)+"|"+Math.floor(n.y/cell);
    let bucket=cells.get(key);if(!bucket)cells.set(key,bucket=[]);bucket.push(n);
  }
  for(const [key,membros] of cells){
    if(membros.length===1){nos.push(membros[0]);mapa.set(membros[0].id,membros[0]);continue}
    const grupo={id:"visual|"+key,grGrupo:true,membros,relacoes:[],cat:membros[0].cat,cor:membros[0].cor,
      x:membros.reduce((s,n)=>s+n.x,0)/membros.length,y:membros.reduce((s,n)=>s+n.y,0)/membros.length,
      r:16+Math.min(12,Math.log2(membros.length)),rotulo:membros.length+" membros",grOrdem:Math.max(...membros.map(n=>n.grOrdem))};
    nos.push(grupo);for(const n of membros)mapa.set(n.id,grupo);
  }
  const foco=n=>n===grSelectedNode||n===grSelectedEdge?.source||n===grSelectedEdge?.target;
  nos.sort((a,b)=>Number(foco(a))-Number(foco(b))||a.grOrdem-b.grOrdem);
  const grupos=new Map();
  for(const e of vis.arestas){
    const source=mapa.get(e.source.id),target=mapa.get(e.target.id);
    if(source.grGrupo)source.relacoes.push(e);
    if(target.grGrupo&&target!==source)target.relacoes.push(e);
    if(source===target)continue;
    if(!source.grGrupo&&!target.grGrupo){grupos.set(grChaveAresta(e),e);continue}
    const key=JSON.stringify([source.id,target.id]);let agregado=grupos.get(key);
    if(!agregado)grupos.set(key,agregado={source,target,grVisual:true,originais:[],relacao:""});
    agregado.originais.push(e);
  }
  for(const e of grupos.values())if(e.grVisual)e.relacao=e.originais.length+" relações · "+e.originais.reduce((s,a)=>s+grFontes(a).length,0)+" referências";
  grHitCache=null;
  return grProjecao={vis,zoom:grZoom,selecao:grSelectedNode,aresta:grSelectedEdge,nos,arestas:[...grupos.values()]};
}

function grExpandirGrupo(grupo){
  for(const n of grupo.membros)grExpandidos.add(n.id);
  grInvalidarEspaco();grPedirDesenho();
}

function grInspecionarGrupo(grupo,limite=50){
  grSelectedNode=null;grSelectedEdge=null;const p=$("#gr-detalhes-conteudo");$("#gr-d-dica").hidden=true;
  const relacoes=grupo.relacoes||[],fontes=relacoes.reduce((s,e)=>s+grFontes(e).length,0);
  p.innerHTML=`<h4>Agrupamento visual · ${grupo.membros.length} membros</h4>
    <p>A proximidade visual não confirma identidade ou vínculo.</p>
    <div>${relacoes.length} relações · ${fontes} referências preservadas</div>
    <button class="btn sm" data-gr-expandir>Expandir ${grupo.membros.length} membros</button>
    <button class="btn sm" data-gr-recolher>Recolher expansões visuais</button>
    <p>Membros: exibindo ${Math.min(limite,grupo.membros.length)} de ${grupo.membros.length}</p>
    ${grupo.membros.slice(0,limite).map((n,i)=>`<div><button class="btn sm" data-gr-membro="${i}">${esc(n.rotulo)}</button></div>`).join("")}
    <p>Relações: exibindo ${Math.min(limite,relacoes.length)} de ${relacoes.length}</p>
    ${relacoes.slice(0,limite).map((e,i)=>`<div><button class="btn sm" data-gr-relacao="${i}">${esc(e.source.rotulo)} → ${esc(e.target.rotulo)} · ${esc(e.relacao)} · ${grFontes(e).length} referências</button></div>`).join("")}
    ${limite<Math.max(grupo.membros.length,relacoes.length)?'<button class="btn sm" data-gr-mais>Mostrar mais 50</button>':""}`;
  p.querySelectorAll("[data-gr-expandir]").forEach(b=>b.onclick=()=>grExpandirGrupo(grupo));
  p.querySelectorAll("[data-gr-recolher]").forEach(b=>b.onclick=()=>{grExpandidos.clear();grInvalidarEspaco();grPedirDesenho()});
  p.querySelectorAll("[data-gr-membro]").forEach(b=>b.onclick=()=>grFocarNo(grupo.membros[Number(b.dataset.grMembro)].id));
  p.querySelectorAll("[data-gr-relacao]").forEach(b=>b.onclick=()=>grInspecionarAresta(relacoes[Number(b.dataset.grRelacao)]));
  p.querySelectorAll("[data-gr-mais]").forEach(b=>b.onclick=()=>grInspecionarGrupo(grupo,limite+50));
  grInvalidarEspaco();grPedirDesenho();
}

function grFindProjectedEdgeAt(wx,wy){
  let escolhido=null,menor=(6/grZoom)**2;
  for(const e of grProjetar().arestas){const a=e.source,b=e.target,dx=b.x-a.x,dy=b.y-a.y,d2=dx*dx+dy*dy;
    const t=d2?Math.max(0,Math.min(1,((wx-a.x)*dx+(wy-a.y)*dy)/d2)):0;
    const d=(wx-a.x-t*dx)**2+(wy-a.y-t*dy)**2;if(d<=menor){menor=d;escolhido=e}
  }
  return escolhido;
}

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
  const width=Math.floor(rect.width)||800,height=Math.floor(rect.height)||560;
  if(cv.width!==Math.floor(width*dpr)||cv.height!==Math.floor(height*dpr)){
    cv.width=Math.floor(width*dpr);cv.height=Math.floor(height*dpr);grDrawDirty=true;
  }
  grSize={width,height,dpr};
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
    const avisos=[grDados.aviso,grDados.truncado===true?"Resultado parcial: há relações adicionais. Carregue as próximas relações ou refine a busca/O.S.":grDados.completude==="nao_aferida"?"Completude não aferida: confira os limites e refine a busca antes de concluir.":""];
    texto=[texto,...avisos.filter(Boolean)].filter(Boolean).join(" ");
  }
  if(msg){msg.textContent=texto;msg.hidden=!texto}
  if(status)status.textContent=grEstado==="carregando"?"Carregando…":grEstado==="erro"?"Falha no carregamento":`${visNodes.length} nós visíveis · ${conexoes} conexões`;
  grAtualizarPaginacao();
}

function grAtualizarPaginacao(){
  const box=$("#gr-paginacao"),texto=$("#gr-paginacao-texto"),b=$("#b-gr-mais");if(!box||!texto||!b)return;
  const total=Number.isInteger(grDados.total)?grDados.total:null;
  const msg=grEstado==="carregando"?"Carregando relações…":total!==null?`${grEdges.length} de ${total} relações carregadas neste recorte.`:
    `${grEdges.length} relações carregadas; total documental não apurado.`;
  const mesmaOperacao=grPaginaOperacao===grCarga;
  const valor=[msg,mesmaOperacao&&grMaisEmCurso?"Carregando próximas relações…":"",mesmaOperacao?grPaginaErro:""].filter(Boolean).join(" ");
  if(texto.textContent!==valor)texto.textContent=valor;
  b.hidden=grEstado!=="pronto"||!Number.isInteger(grDados.proxima_pagina);b.disabled=mesmaOperacao&&grMaisEmCurso;
}

async function grCarregarMais(){
  if((grMaisEmCurso&&grPaginaOperacao===grCarga)||grEstado!=="pronto"||!Number.isInteger(grDados.proxima_pagina)||!grPaginaContexto)return;
  const {caso,q}=grPaginaContexto;
  if($("#gr-caso").value!==caso||$("#gr-busca").value.trim()!==q){carregarGrafo();return}
  const carga=grCarga,pagina=grDados.proxima_pagina,revisao=grDados.revisao;
  grMaisEmCurso=true;grPaginaOperacao=carga;grPaginaErro="";grAtualizarPaginacao();
  try{
    const data=await api(`/api/grafo?caso=${enc(caso)}&q=${enc(q)}&pagina=${pagina}&limite=${grDados.limite||400}&revisao=${enc(revisao||"")}`);
    if(carga!==grCarga||$("#gr-caso").value!==caso||$("#gr-busca").value.trim()!==q)return;
    const existentes=new Set(grDados.arestas.map(a=>a.relacao_id));
    if(data.pagina!==pagina||data.revisao!==revisao||data.arestas.some(a=>existentes.has(a.relacao_id)))throw new Error("Página incompatível; clique em Buscar para recarregar o recorte.");
    const nos=new Map(grDados.nos.map(n=>[n.tipo+"|"+n.valor,n]));
    for(const n of data.nos)if(!nos.has(n.tipo+"|"+n.valor))nos.set(n.tipo+"|"+n.valor,n);
    const arestas=grDados.arestas.concat(data.arestas),total=Number.isInteger(data.total)?data.total:null;
    const truncado=total!==null?arestas.length<total:data.truncado;
    grGuardarVista();grDados={...grDados,...data,nos:[...nos.values()],arestas,truncado,
      completude:data.indice_disponivel===false?data.completude:truncado?"parcial":"completa_no_escopo"};
    grMontarGrafo();grAtualizarInspetor();grDesenhar();
  }catch(x){
    if(carga!==grCarga)return;
    grPaginaErro=x.status===409?"As fontes mudaram durante a consulta. Clique em Buscar para recarregar sem misturar versões.":`Não foi possível carregar a próxima página: ${x.message}`;
    if(x.status===409)grDados={...grDados,proxima_pagina:null,truncado:true,completude:"parcial"};
  }finally{if(carga===grCarga){grMaisEmCurso=false;grAtualizarPaginacao()}}
}

async function carregarGrafo(){
  grInitEvents();grGuardarVista();
  const carga=++grCarga,caso=$("#gr-caso").value,q=$("#gr-busca").value.trim();
  grPaginaContexto={caso,q};grMaisEmCurso=false;grPaginaErro="";
  grEstado="carregando";grErro="";grAtualizarEstado([],0);
  try{
    const data=await api(`/api/grafo?caso=${enc(caso)}&q=${enc(q)}`);
    if(carga!==grCarga)return;
    grDados=data;grAtualizarCasos(data,caso);grEstado="pronto";
    grHoveredNode=null;grDraggingNode=null;grMontarGrafo();
    const id=grVistas.get(grVistaChave)?.selecao;
    if(typeof grSelectedEdge!=="undefined"&&grSelectedEdge)grInspecionarAresta(grSelectedEdge);
    else grInspecionarNo(id?grNodeMap.get(id)||null:null);
    if(id&&!grNodeMap.has(id)){
      const dica=$("#gr-d-dica");if(dica){dica.hidden=false;dica.textContent="O nó selecionado não está neste resultado."}
    }
    grDesenhar();
  }catch(x){
    if(carga!==grCarga)return;
    grDados={nos:[],arestas:[]};grNodes=[];grEdges=[];grNodeMap.clear();grVisCache=null;grInvalidarEspaco();
    grSimulando=false;grEnergy=0;if(grAnimId!==null)cancelAnimationFrame(grAnimId);grAnimId=null;
    grEstado="erro";grErro=x.message;grInspecionarNo(null);grDesenhar();
  }
}

function grMontarGrafo(){
  grGuardarVista();grResizeCanvas();
  const chaves=grChavesVista(),vista=grVistas.get(chaves.vista),pos=grPosicoes.get(chaves.dominio)||new Map();
  grVistaChave=chaves.vista;grDominioChave=chaves.dominio;
  grCentro=vista?.centro||{x:(grSize?.width||800)/2,y:(grSize?.height||560)/2};
  grNodeMap=new Map();
  grNodes=(grDados.nos||[]).map(n=>{
    const cfg=grGetCfg(n.tipo),id=n.tipo+"|"+n.valor;
    const ang=grHashID(id+"|angulo")/4294967296*2*Math.PI;
    const raio=212.8*(.3+.7*grHashID(id+"|raio")/4294967296);
    const node={id,tipo:n.tipo,valor:n.valor,rotulo:n.rotulo||n.valor,cat:cfg.cat,r:cfg.r,cor:cfg.cor,
      x:grCentro.x+raio*Math.cos(ang),y:grCentro.y+raio*Math.sin(ang),vx:0,vy:0,fixo:false,...pos.get(id)};
    grNodeMap.set(id,node);return node;
  }).sort((a,b)=>a.id<b.id?-1:a.id>b.id?1:0);
  grNodes.forEach((n,i)=>n.grOrdem=i);
  grEdges=[];
  for(const a of grDados.arestas||[]){
    const s=grNodeMap.get(a.a_tipo+"|"+a.a_valor),t=grNodeMap.get(a.b_tipo+"|"+a.b_valor);
    if(s&&t)grEdges.push({...a,source:s,target:t,caso:a.caso||a.fonte,relacao:a.relacao||"vinculado a",origem:a.origem||"",fonte:a.fonte||"",localizador:a.localizador||""});
  }
  const ordem=grEdges.map(edge=>({edge,chave:JSON.stringify([edge.source.id,edge.target.id,edge.relacao])}));
  ordem.sort((a,b)=>a.chave<b.chave?-1:a.chave>b.chave?1:0);grEdges=ordem.map(item=>item.edge);
  const topologia=JSON.stringify([grNodes.map(n=>n.id),ordem.map(item=>item.chave)]);
  grVisCache=null;grInvalidarEspaco();grHoveredNode=null;grDraggingNode=null;
  grSelectedNode=vista?.selecao?grNodeMap.get(vista.selecao)||null:null;
  if(typeof grSelectedEdge!=="undefined")grSelectedEdge=vista?.aresta?grEdges.find(e=>grChaveAresta(e)===vista.aresta)||null:null;
  if(vista){grZoom=vista.zoom;grPanX=vista.panX;grPanY=vista.panY}else grResetView();
  const mudou=!vista||vista.topologia!==topologia;
  grSimulando=mudou||vista?.simulando===true;
  grTicks=mudou?0:vista.ticks;grQuietTicks=mudou?0:vista.quietTicks;
  grLayoutEstado=grSimulando?"movendo":vista?.estado||"parado";grEnergy=grSimulando?1:0;
  grAjustarAoEstabilizar=!vista;
  grVistas.set(grVistaChave,{...vista,topologia,selecao:vista?.selecao||null,aresta:vista?.aresta||null});
  grDrawDirty=true;grStartLoop();
}

function grTickPhysics(){
  const vis=grVisiveis(),nos=vis.nos;if(!nos.length){grMovimentoMax=0;return 0}
  const livre=n=>n!==grDraggingNode&&!n.fixo;
  for(const n of nos)if(livre(n)){n.vx+=(grCentro.x-n.x)*.0025;n.vy+=(grCentro.y-n.y)*.0025}
  const cells=new Map(),cell=GR_RAIO_REPULSAO;
  for(let i=0;i<nos.length;i++){const n=nos[i],key=Math.floor(n.x/cell)+","+Math.floor(n.y/cell);let bucket=cells.get(key);if(!bucket)cells.set(key,bucket=[]);bucket.push(i)}
  let pairs=0;
  for(let i=0;i<nos.length;i++){
    const a=nos[i],cx=Math.floor(a.x/cell),cy=Math.floor(a.y/cell);
    for(let dyCell=-1;dyCell<=1;dyCell++)for(let dxCell=-1;dxCell<=1;dxCell++){
      const bucket=cells.get((cx+dxCell)+","+(cy+dyCell));if(!bucket)continue;
      for(const j of bucket){if(j<=i)continue;pairs++;
        const b=nos[j],dx=b.x-a.x,dy=b.y-a.y,sq=Math.max(1,dx*dx+dy*dy);if(sq>160000)continue;
        const dist=Math.sqrt(sq),force=3000/sq,fx=dx/dist*force,fy=dy/dist*force;
        if(livre(a)){a.vx-=fx;a.vy-=fy}if(livre(b)){b.vx+=fx;b.vy+=fy}
      }
    }
  }
  grRepulsionPairs=pairs;
  for(const e of vis.arestas){const a=e.source,b=e.target,dx=b.x-a.x,dy=b.y-a.y,dist=Math.sqrt(dx*dx+dy*dy)||1;
    const force=(dist-((a.r+b.r)*3+45))*.035,fx=dx/dist*force,fy=dy/dist*force;
    if(livre(a)){a.vx+=fx;a.vy+=fy}if(livre(b)){b.vx-=fx;b.vy-=fy}
  }
  let move=0,max=0;
  for(const n of nos){if(!livre(n)){n.vx=0;n.vy=0;continue}n.vx*=.84;n.vy*=.84;n.x+=n.vx;n.y+=n.vy;
    move+=Math.abs(n.vx)+Math.abs(n.vy);max=Math.max(max,Math.abs(n.vx),Math.abs(n.vy));
  }
  grMovimentoMax=max;grInvalidarEspaco();return move/nos.length;
}

function grDesenhar(opcoes){
  const cv=$("#cv-grafo");if(!cv)return;if(!grSize)grResizeCanvas();
  const ctx=cv.getContext("2d"),{width:w,height:h,dpr}=grSize;
  const vis=grVisiveis(),projecao=grProjetar(),b={x0:-grPanX/grZoom,y0:-grPanY/grZoom,x1:(w-grPanX)/grZoom,y1:(h-grPanY)/grZoom};
  ctx.save();ctx.scale(dpr,dpr);ctx.fillStyle="#080e1a";ctx.fillRect(0,0,w,h);
  ctx.save();ctx.translate(grPanX,grPanY);ctx.scale(grZoom,grZoom);
  const high=e=>typeof grSelectedEdge!=="undefined"&&(e===grSelectedEdge||e.originais?.includes(grSelectedEdge))||grSelectedNode&&(e.source===grSelectedNode||e.target===grSelectedNode)||grHoveredNode&&(e.source===grHoveredNode||e.target===grHoveredNode);
  const lines=[],highlines=[];
  for(const e of projecao.arestas){const a=e.source,t=e.target,pad=16;
    if(Math.max(a.x,t.x)+pad<b.x0||Math.min(a.x,t.x)-pad>b.x1||Math.max(a.y,t.y)+pad<b.y0||Math.min(a.y,t.y)-pad>b.y1)continue;
    (high(e)?highlines:lines).push(e);
  }
  function drawLines(edges,highlight){
    ctx.strokeStyle=highlight?"#38BDF8":"rgba(148, 163, 184, 0.28)";ctx.lineWidth=highlight?2.4:1.2;
    ctx.shadowColor="#0284C7";ctx.shadowBlur=highlight?8:0;
    // Preserve individual alpha compositing at crossings; batch state changes only.
    for(const e of edges){ctx.beginPath();ctx.moveTo(e.source.x,e.source.y);ctx.lineTo(e.target.x,e.target.y);ctx.stroke()}
    ctx.fillStyle=highlight?"#38BDF8":"rgba(148, 163, 184, 0.4)";
    for(const e of edges){const dx=e.target.x-e.source.x,dy=e.target.y-e.source.y,d=Math.sqrt(dx*dx+dy*dy)||1;
      const ux=dx/d,uy=dy/d,x=e.target.x-ux*(e.target.r+4),y=e.target.y-uy*(e.target.r+4);
      ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(x-ux*7+uy*3.5,y-uy*7-ux*3.5);ctx.lineTo(x-ux*7-uy*3.5,y-uy*7+ux*3.5);ctx.closePath();ctx.fill();
    }
    ctx.font="9.5px sans-serif";ctx.fillStyle=highlight?"#E0F2FE":"rgba(148, 163, 184, 0.75)";ctx.textAlign="center";ctx.textBaseline="middle";
    // A selected/hovered relationship always exposes its label. Data/evidence is never reduced.
    for(const e of edges){
      if(!e.relacao||!(e.grVisual||highlight||grZoom>.8&&(vis.arestas.length<=300||opcoes?.detalheCompleto)))continue;const x=(e.source.x+e.target.x)/2,y=(e.source.y+e.target.y)/2-4;
      const half=grMedirRotulo(ctx,e.relacao,"9.5px sans-serif")/2;
      if(x+half>=b.x0&&x-half<=b.x1&&y+10>=b.y0&&y-10<=b.y1)ctx.fillText(e.relacao,x,y);
    }
  }
  drawLines(lines,false);drawLines(highlines,true);ctx.shadowBlur=0;
  for(const n of projecao.nos){
    const sel=n===grSelectedNode,hover=n===grHoveredNode,font=sel?"bold 12px sans-serif":hover?"bold 11px sans-serif":"11px sans-serif";
    const half=grMedirRotulo(ctx,n.rotulo,font)/2;
    if(n.x+Math.max(n.r,half)<b.x0||n.x-Math.max(n.r,half)>b.x1||n.y+n.r+22<b.y0||n.y-n.r>b.y1)continue;
    ctx.save();ctx.beginPath();ctx.arc(n.x,n.y,n.r,0,2*Math.PI);
    if(sel||hover){ctx.shadowColor=n.cor;ctx.shadowBlur=sel?16:10}ctx.fillStyle=n.cor;ctx.fill();
    ctx.lineWidth=sel?3:hover?2.5:1.5;ctx.strokeStyle=sel||hover?"#FFFFFF":"rgba(255, 255, 255, 0.45)";ctx.stroke();ctx.restore();
    ctx.font=font;ctx.textAlign="center";ctx.textBaseline="top";ctx.lineWidth=3;ctx.strokeStyle="rgba(8, 14, 26, 0.9)";
    ctx.strokeText(n.rotulo,n.x,n.y+n.r+4);ctx.fillStyle=sel?"#38BDF8":hover?"#FFFFFF":"#E2E8F0";ctx.fillText(n.rotulo,n.x,n.y+n.r+4);
  }
  ctx.restore();ctx.restore();grDrawDirty=false;
  const grupos=grAgrupar?projecao.nos.filter(n=>n.grGrupo).length:0;
  const status=grEstado+"|"+grErro+"|"+vis.chave+"|"+vis.nos.length+"|"+vis.arestas.length+"|"+grAgrupar+"|"+grupos;
  if(grVisCache.estado!==status){grAtualizarEstado(vis.nos,vis.arestas.length);if(grAgrupar&&$("#gr-status"))$("#gr-status").textContent+=` · ${grupos} grupos visuais`;grVisCache.estado=status}
  cv.title=vis.arestas.length>300?"Selecione um nó para exibir os rótulos de suas relações e inspecionar as fontes.":"";
}

function grStartLoop(){
  if(!grEstaVisivel())return;
  if(!grSimulando&&grEnergy>.04){grSimulando=true;grTicks=0;grQuietTicks=0;grLayoutEstado="movendo"}
  if(grAnimId!==null||(!grSimulando&&!grDrawDirty))return;
  function step(){
    grAnimId=null;if(!grEstaVisivel())return;
    if(grSimulando){
      const move=grTickPhysics();grTicks++;grQuietTicks=move<.04&&grMovimentoMax<.12&&!grDraggingNode?grQuietTicks+1:0;
      grDrawDirty=true;
      if(grQuietTicks>=GR_QUIET_TICKS||grTicks>=GR_MAX_TICKS&&!grDraggingNode){
        grSimulando=false;grEnergy=0;grLayoutEstado=grQuietTicks>=GR_QUIET_TICKS?"estavel":"limite";
        if(grAjustarAoEstabilizar){grAjustarAoEstabilizar=false;grResetView()}
      }
    }
    if(grDrawDirty)grDesenhar();
    if(grSimulando||grDrawDirty)grAnimId=requestAnimationFrame(step);
  }
  grAnimId=requestAnimationFrame(step);
}

function grScreenToWorld(sx,sy){

  const cv=$("#cv-grafo"),rect=cv.getBoundingClientRect();

  return {x:(sx-rect.left-grPanX)/grZoom,y:(sy-rect.top-grPanY)/grZoom};

}

function grFindNodeAt(wx,wy){
  const vis=grProjetar();
  if(!grHitCache){
    const cells=new Map();let max=0;
    for(const n of vis.nos){const key=Math.floor(n.x/64)+","+Math.floor(n.y/64);let bucket=cells.get(key);if(!bucket)cells.set(key,bucket=[]);bucket.push(n);max=Math.max(max,n.r+5)}
    grHitCache={cells,max,ordem:new Map(vis.nos.map((n,i)=>[n,i]))};
  }
  const {cells,max,ordem}=grHitCache;let top=null;
  for(let y=Math.floor((wy-max)/64);y<=Math.floor((wy+max)/64);y++)for(let x=Math.floor((wx-max)/64);x<=Math.floor((wx+max)/64);x++){
    for(const n of cells.get(x+","+y)||[]){const dx=wx-n.x,dy=wy-n.y;if(dx*dx+dy*dy<=(n.r+5)**2&&(!top||ordem.get(n)>ordem.get(top)))top=n}
  }
  return top;
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
  const n=grNodeMap.get(id);if(!n)return;
  grAjustarAoEstabilizar=false;grInspecionarNo(n);
  if(!grSize)grResizeCanvas();grPanX=grSize.width/2-n.x*grZoom;grPanY=grSize.height/2-n.y*grZoom;grPedirDesenho();
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
  if(grInitialized)return;const cv=$("#cv-grafo");if(!cv)return;grInitialized=true;
  if(!$("#gr-paginacao")&&typeof document!=="undefined"){
    const p=document.createElement("div");p.id="gr-paginacao";p.className="acoes";p.setAttribute("role","status");
    p.innerHTML='<span id="gr-paginacao-texto" class="muted"></span><button type="button" class="btn sm" id="b-gr-mais" hidden>Carregar próximas relações</button>';
    $("#gr-mensagem").insertAdjacentElement("afterend",p);$("#b-gr-mais").onclick=grCarregarMais;
  }
  if(!$("#b-gr-agrupar")&&typeof document!=="undefined"){
    const b=document.createElement("button");b.id="b-gr-agrupar";b.className="btn sm";b.textContent="Agrupar visualmente";b.setAttribute("aria-pressed","false");
    b.onclick=()=>grMostrarAgrupamento(!grAgrupar);$("#b-gr-reset")?.insertAdjacentElement?.("afterend",b);
  }
  cv.addEventListener("wheel",e=>{
    e.preventDefault();grAjustarAoEstabilizar=false;
    const rect=cv.getBoundingClientRect(),mx=e.clientX-rect.left,my=e.clientY-rect.top;
    const zoom=Math.max(.2,Math.min(4,grZoom*(e.deltaY<0?1.15:.87)));
    grPanX=mx-(mx-grPanX)*(zoom/grZoom);grPanY=my-(my-grPanY)*(zoom/grZoom);grZoom=zoom;grPedirDesenho();
  },{passive:false});
  cv.addEventListener("mousedown",e=>{
    grAjustarAoEstabilizar=false;grMouseDownPos={x:e.clientX,y:e.clientY};
    const pt=grScreenToWorld(e.clientX,e.clientY),n=grFindNodeAt(pt.x,pt.y);
    if(n?.grGrupo){grInspecionarGrupo(n);return}
    if(n){grDraggingNode=n;grReaquecer()}else{grIsPanning=true;grStartPan={x:e.clientX-grPanX,y:e.clientY-grPanY}}
  });
  window.addEventListener("mousemove",e=>{
    if(grDraggingNode){
      const pt=grScreenToWorld(e.clientX,e.clientY);grDraggingNode.x=pt.x;grDraggingNode.y=pt.y;grDraggingNode.vx=0;grDraggingNode.vy=0;
      grInvalidarEspaco();grPedirDesenho();
    }else if(grIsPanning){grPanX=e.clientX-grStartPan.x;grPanY=e.clientY-grStartPan.y;grPedirDesenho()}
    else{
      const rect=cv.getBoundingClientRect(),dentro=e.clientX>=rect.left&&e.clientX<=rect.right&&e.clientY>=rect.top&&e.clientY<=rect.bottom;
      const pt=dentro?grScreenToWorld(e.clientX,e.clientY):null,n=pt?grFindNodeAt(pt.x,pt.y):null;
      if(n!==grHoveredNode){grHoveredNode=n;cv.style.cursor=n?"pointer":"grab";grPedirDesenho()}
    }
  });
  window.addEventListener("mouseup",e=>{
    const dist=Math.hypot(e.clientX-grMouseDownPos.x,e.clientY-grMouseDownPos.y);
    if(grDraggingNode){if(dist<5)grInspecionarNo(grDraggingNode);else grDraggingNode.fixo=true}
    else if(grIsPanning&&dist<5){const pt=grScreenToWorld(e.clientX,e.clientY);if(!grFindNodeAt(pt.x,pt.y)){
      const e=grAgrupar?grFindProjectedEdgeAt(pt.x,pt.y):grFindEdgeAt(pt.x,pt.y);
      if(e?.grVisual){const membros=[...new Set(e.originais.flatMap(a=>[a.source,a.target]))];grInspecionarGrupo({membros,relacoes:e.originais})}
      else grInspecionarAresta(e);
    }}
    grDraggingNode=null;grIsPanning=false;grPedirDesenho();
  });
  cv.addEventListener("dblclick",()=>{grAjustarAoEstabilizar=false;grResetView()});
  ["#gf-caso","#gf-pessoa","#gf-conta","#gf-doc","#gf-tel","#gf-outros"].forEach(id=>{const el=$(id);if(el)el.onchange=()=>{grVisCache=null;grInvalidarEspaco();grReaquecer()}});
  if($("#b-gr-buscar"))$("#b-gr-buscar").onclick=()=>carregarGrafo();
  if($("#gr-busca"))$("#gr-busca").onkeydown=e=>{if(e.key==="Enter")carregarGrafo()};
  if($("#gr-caso"))$("#gr-caso").onchange=()=>carregarGrafo();
  if($("#b-gr-reset"))$("#b-gr-reset").onclick=()=>{grAjustarAoEstabilizar=false;grResetView()};
  if($("#b-gr-foto"))$("#b-gr-foto").onclick=()=>{grDesenhar();const a=document.createElement("a");a.download=`grafo-relacional-sip-${hoje()}.png`;a.href=cv.toDataURL("image/png");a.click();toast("Imagem PNG do grafo salva")};
  if(typeof document!=="undefined")document.addEventListener("visibilitychange",grVisibilidadeMudou);
  if(typeof MutationObserver!=="undefined"){
    const observer=new MutationObserver(grVisibilidadeMudou);
    for(const el of[$("#grafo"),$("#app")])if(el)observer.observe(el,{attributes:true,attributeFilter:["class","hidden"]});
  }
  if(typeof ResizeObserver!=="undefined")new ResizeObserver(()=>{grResizeCanvas();grPedirDesenho()}).observe(cv.parentElement||cv);
  window.addEventListener("resize",()=>{grResizeCanvas();grPedirDesenho()});
}
