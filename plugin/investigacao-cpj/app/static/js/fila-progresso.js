// Leitura do progresso já publicado pela fila; nenhum comando ou acesso externo.
(function(root){
 "use strict";
 const numero=v=>Number.isFinite(Number(v))&&v!==null&&v!==""?Number(v):null;
 const segundos=(a,b)=>{const x=Date.parse(a),y=typeof b==="number"?b:Date.parse(b);return Number.isFinite(x)&&Number.isFinite(y)&&y>=x?(y-x)/1000:null};
 const extensao=t=>String(t.arquivo||"").toLowerCase().match(/\.[a-z0-9]+$/)?.[0]||"";
 const mediana=a=>{a=[...a].sort((x,y)=>x-y);return a.length%2?a[(a.length-1)/2]:(a[a.length/2-1]+a[a.length/2])/2};
 const faixa=n=>n>0&&Number.isFinite(n)?{min:Math.max(1,n*.5),max:Math.max(30,n*2)}:null;
 const somar=(a,b)=>a&&b?{min:a.min+b.min,max:a.max+b.max}:null;
 function etapa(t){
  const e=String(t.etapa||"").toLowerCase(),ext=extensao(t),pdf=ext===".pdf",md=ext===".md";
  const visual=pdf&&t.modo&&t.modo!=="rapido";
  let n=null,titulo=String(t.etapa||"Preparando o arquivo"),descricao=t.etapa?"Etapa em execução; aguardando novo avanço informado pelo processamento.":"Aguardando os primeiros detalhes do processamento.";
  if(e.includes("transcrição visual")){n=7;titulo="Transcrevendo imagens com IA";descricao="Convertendo as páginas selecionadas em texto com o provedor autorizado."}
  else if(e.includes("indexa")){n=pdf?6:md?5:3;titulo="Preparando a pesquisa";descricao="Indexando o conteúdo e os registros extraídos para as buscas do sistema."}
  else if(e.includes("após ocr")||e.includes("consolida")||e==="registro"){n=pdf?5:md?4:2;titulo="Consolidando a extração";descricao="Organizando os resultados e atualizando os dados da Ordem de Serviço."}
  else if(e.includes("dados críticos")){n=pdf?4:3;titulo="Identificando dados importantes";descricao="Localizando pessoas, contas, chaves Pix e outros identificadores no texto extraído."}
  else if(e.includes("tabelas")){n=pdf?3:2;titulo="Extraindo tabelas";descricao="Texto já extraído; localizando tabelas e salvando planilhas CSV."}
  else if(e.includes("extração/ocr")){n=2;titulo="Extraindo texto e reconhecendo páginas";descricao="Lendo o texto do PDF e aplicando OCR nas páginas que precisam de reconhecimento."}
  else if(e.includes("diagnóstico")){n=1;titulo="Verificando o PDF";descricao="Verificando a estrutura do documento e a necessidade de OCR."}
  else if(e.includes("dados da o.s.")){n=1;titulo="Lendo a Ordem de Serviço";descricao="Procurando os dados iniciais da O.S. no documento."}
  else if(e.includes("importa")){n=1;titulo=md?"Importando o texto Markdown":"Importando a planilha CSV";descricao="Copiando e organizando o conteúdo para processamento."}
  const atual=numero(t.pagina_atual),total=numero(t.paginas);
  return {atividade:titulo,descricao,etapaNumero:n,etapasTotal:pdf?(visual?7:6):md?5:3,
   pagina:e.includes("extração/ocr")&&total>0?{atual:Math.max(0,Math.min(total,atual||0)),total}:null};
 }
 function criar(){
  const observados=new Map();
  function calcular(trabalhos,agora=Date.now()){
   const ts=Array.isArray(trabalhos)?trabalhos:[],chaves=new Set();
   const historico=ts.filter(t=>t.status==="concluido"&&segundos(t.inicio,t.fim)>0);
   let ativos=0,aguardando=0,erros=0,semEstimativa=0,acumulado={min:0,max:0};
   // O worker de extração é sequencial; mantém a ordem devolvida pela API.
   const itens=ts.map(t=>{
    const rodando=t.status==="processando",esperando=t.status==="na_fila",pendente=rodando||esperando;
    if(rodando)ativos++;if(esperando)aguardando++;if(t.status==="erro")erros++;
    const chave=JSON.stringify([t.caso,t.doc,t.arquivo,t.inicio]),sinal=JSON.stringify([t.status,t.etapa,t.progresso,t.pagina_atual]);chaves.add(chave);
    const anterior=observados.get(chave),mudanca=anterior?.sinal===sinal?anterior.quando:agora;
    observados.set(chave,{sinal,quando:mudanca});
    const decorrido=rodando?segundos(t.inicio,agora):t.status==="concluido"?segundos(t.inicio,t.fim):null;
    const parecidos=historico.filter(h=>extensao(h)===extensao(t)&&String(h.modo||"")===String(t.modo||""));
    const paginas=numero(t.paginas),porPagina=parecidos.filter(h=>numero(h.paginas)>0);
    let duracao=null,base=null,restante=null,recalculando=false;
    if(parecidos.length){
     duracao=paginas>0&&porPagina.length?mediana(porPagina.map(h=>segundos(h.inicio,h.fim)/Number(h.paginas)))*paginas:mediana(parecidos.map(h=>segundos(h.inicio,h.fim)));
     base=paginas>0&&porPagina.length?"histórico por página":"histórico de arquivos semelhantes";
    }
    if(rodando&&decorrido!==null){
     if(duracao!==null){restante=faixa(duracao-decorrido);recalculando=!restante}
     else if(String(t.etapa||"").toLowerCase().includes("extração/ocr")&&decorrido>=15&&numero(t.progresso)>=10&&numero(t.progresso)<90){
      restante=faixa(decorrido*(100-Number(t.progresso))/Number(t.progresso));base="ritmo inicial de extração";
     }
    }else if(esperando)restante=faixa(duracao);
    if(!pendente)base=null;
    let iniciaEm=null,terminaEm=null;
    if(pendente){
     if(!restante)semEstimativa++;
     iniciaEm=rodando?{min:0,max:0}:acumulado;
     acumulado=somar(acumulado,restante);terminaEm=acumulado;
    }
    return {trabalho:t,...etapa(t),decorrido,restante,base,recalculando,iniciaEm,terminaEm,
     posicao:esperando?aguardando:null,semAvanco:rodando?Math.max(0,(agora-mudanca)/1000):0};
   });
   for(const chave of observados.keys())if(!chaves.has(chave))observados.delete(chave);
   return {itens,ativos,aguardando,erros,semEstimativa,total:ativos+aguardando?acumulado:null,agora};
  }
  return {calcular,html};
 }
 function tempo(n){
  if(n===null||!Number.isFinite(n))return "em cálculo";
  const m=Math.max(1,Math.ceil(n/60));return m<60?`${m} min`:`${Math.floor(m/60)} h${m%60?` ${m%60} min`:""}`;
 }
 function intervalo(f){if(!f)return "em cálculo";if(f.max<60)return "menos de 1 min";const a=tempo(f.min),b=tempo(f.max);return a===b?a:`${a} a ${b}`}
 function horario(f,agora){
  if(!f)return "em cálculo";
  const h=n=>new Date(agora+n*1000).toLocaleTimeString("pt-BR",{hour:"2-digit",minute:"2-digit"});
  const a=h(f.min),b=h(f.max);return a===b?a:`${a}–${b}`;
 }
 function decorridoTexto(n){return n<60?`${Math.floor(n)} s`:tempo(Math.floor(n/60)*60)}
 function html(v,{esc,badge,barraHTML}){
  if(!v.itens.length)return '<div class="vazio">Nada na fila</div>';
  const total=v.total?`Restante da fila: aproximadamente ${intervalo(v.total)} · término entre ${horario(v.total,v.agora)}`:
   v.ativos+v.aguardando?`Previsão total em cálculo · ${v.semEstimativa} arquivo(s) ainda sem estimativa confiável`:
   v.erros?"Fila sem processamento ativo; confira os arquivos com erro.":v.itens.every(i=>i.trabalho.status==="concluido")?"Fila concluída":"Nenhum arquivo em processamento.";
  const resumo=`<div data-fila-resumo style="padding:12px;border:1px solid var(--line);border-radius:10px;margin:10px 0"><b>${v.ativos} em processamento · ${v.aguardando} aguardando${v.erros?` · ${v.erros} com erro`:""}</b><div style="margin-top:6px" data-fila-total>${esc(total)}</div><div class="muted" style="margin-top:6px">Previsões aproximadas, atualizadas conforme o histórico e o ritmo observado. OCR e tabelas podem variar de duração.</div></div>`;
  return resumo+v.itens.map(i=>{
   const t=i.trabalho,run=t.status==="processando",fila=t.status==="na_fila",p=Math.max(0,Math.min(100,numero(t.progresso)||0));
   const atividade=run?`${i.etapaNumero?`Etapa ${i.etapaNumero} de ${i.etapasTotal} · `:""}${i.atividade}`:fila?`Aguardando sua vez · posição ${i.posicao}`:t.status==="erro"?`Processamento interrompido · ${t.etapa||"etapa não informada"}`:t.status==="concluido"?"Processamento concluído":String(t.etapa||t.status||"");
   let detalhe=run?i.descricao:fila?"Este arquivo começará quando os anteriores terminarem.":t.limitacao||"";
   if(i.pagina&&run)detalhe+=` Página ${i.pagina.atual} de ${i.pagina.total}.`;
   if(t.status==="concluido"&&numero(t.paginas)>0)detalhe+=` ${Number(t.paginas)} páginas processadas.`;
   let estimativa=run?(i.restante?`Restante aproximado: ${intervalo(i.restante)} · término previsto: ${horario(i.terminaEm,v.agora)}`:i.recalculando?"Recalculando previsão: a duração superou o histórico disponível.":"Estimativa em cálculo; aguardando histórico ou avanço suficiente."):
    fila?(i.restante?`Duração aproximada: ${intervalo(i.restante)}${i.iniciaEm?` · início em ${intervalo(i.iniciaEm)} · término previsto: ${horario(i.terminaEm,v.agora)}`:" · aguardando a previsão dos arquivos anteriores para calcular início e término."}`:"Previsão em cálculo; aguardando tempo medido para este tipo de arquivo."):"";
   const decorrido=i.decorrido===null?"":`${run?"Em processamento há":"Duração"}: ${decorridoTexto(i.decorrido)}`;
   const sinal=run&&i.semAvanco>=60?`<div class="muted">Última mudança de progresso observada há ${tempo(i.semAvanco)}; aguardando novo avanço desta etapa.</div>`:"";
   return `<div class="job" data-fila-item><div class="l1"><div><b>${esc(t.caso||"")}</b> · ${esc(t.arquivo||"")}</div>${badge(t.status)}</div><div style="margin-top:6px" data-fila-atividade><b>${esc(atividade)}</b></div><div class="muted">${esc(detalhe)}</div>${run||fila?barraHTML(p):""}<div class="muted">${esc(decorrido)}${run?` · Progresso: ${p}%`:""}</div>${estimativa?`<div style="margin-top:4px" data-fila-estimativa>${esc(estimativa)}</div>`:""}${i.base&&i.restante?`<div class="muted">Base da previsão: ${esc(i.base)}.</div>`:""}${sinal}${t.erro?`<div style="color:var(--crit)">${esc(t.erro)}</div>`:""}</div>`;
  }).join("");
 }
 const api={criar,...criar()};root.CPJFilaProgresso=api;
 if(typeof module!=="undefined"&&module.exports)module.exports=api;
})(globalThis);
