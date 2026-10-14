// ---------------- grafo relacional vínculos manuais

function grAbrirModalVinculo(origTipo,origVal){

  const m=$("#modal-vinculo"), f=$("#f-vinculo");

  if(!m||!f)return;

  if(origTipo) f.a_tipo.value=origTipo;

  if(origVal) f.a_valor.value=origVal;

  f.caso_id.value=$("#gr-caso")?.value||casoAberto||"";

  m.hidden=false;

  if(!origVal) f.a_valor.focus(); else f.relacao.focus();

}

if($("#b-gr-novo-vinc")) $("#b-gr-novo-vinc").onclick=()=>grAbrirModalVinculo();

if($("#b-fecha-mv")) $("#b-fecha-mv").onclick=()=>{$("#modal-vinculo").hidden=true};

if($("#b-canc-mv")) $("#b-canc-mv").onclick=()=>{$("#modal-vinculo").hidden=true};

if($("#f-vinculo")) $("#f-vinculo").onsubmit=async e=>{

  e.preventDefault();

  const f=e.target, msg=$("#msg-vinc-novo");

  if(msg) msg.textContent="salvando…";

  try{

    const resposta=await api("/api/grafo/vinculo",{json:{

      a_tipo:f.a_tipo.value, a_valor:f.a_valor.value.trim(),

      relacao:f.relacao.value.trim(),

      b_tipo:f.b_tipo.value, b_valor:f.b_valor.value.trim(),

      documento:f.documento.value.trim(), caso:f.caso_id.value.trim(),
      pagina:f.pagina.value?Number(f.pagina.value):null,fls:f.fls.value.trim(),observacao:f.observacao.value.trim()

    }});

    $("#modal-vinculo").hidden=true;

    f.relacao.value=""; f.b_valor.value="";

    toast(resposta.aviso||"Hipótese manual salva; confira a fonte antes de concluir.");

    carregarGrafo();

  }catch(x){

    if(msg) msg.textContent="Erro: "+x.message;

  }

};

async function grRemoverVinculo(vinculo,botao){
  if(!vinculo||vinculo.origem!=="manual"||!vinculo.id||!pode("trabalho"))return;
  if(!confirm(`Remover a anotação manual "${vinculo.relacao}"? As relações documentais e o histórico serão preservados.`))return;
  if(botao)botao.disabled=true;
  try{
    const r=await api("/api/grafo/vinculo/remover",{json:{id:vinculo.id,caso:vinculo.caso,versao:vinculo.versao}});
    toast(r.aviso||"Anotação manual removida; histórico preservado.");
    await carregarGrafo();
  }catch(x){toast("Não foi possível remover: "+x.message)}
  finally{if(botao&&botao.isConnected)botao.disabled=false}
}



