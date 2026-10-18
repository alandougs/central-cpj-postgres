// ---------------- chaves LLM

async function atualizarModelosLLM(prov){
  const mo=$(`#llm-${prov}-modelo`), ch=$(`#llm-${prov}-chave`), lista=$(`#modelos-${prov}`), msg=$(`#msg-modelos-${prov}`);
  if(!mo||!lista||!msg)return;
  msg.textContent=prov==="copilot"?"Consultando lista documental…":"Consultando catálogo do provedor, sem enviar autos…";
  const body={provedor:prov};
  if(ch&&ch.value.trim())body.chave=ch.value.trim();
  try{
    const r=await api("/api/sistema/llm/modelos",{json:body});
    const modelos=Array.isArray(r.modelos)?r.modelos:[];
    lista.replaceChildren();
    for(const m of modelos){
      const o=document.createElement("option");o.value=m.id;o.textContent=m.nome||m.id;lista.appendChild(o);
    }
    const disponivel=modelos.some(m=>m.id===r.modelo_equilibrado);
    if(!mo.value.trim()&&!mo.dataset.manual&&r.dinamico&&disponivel){mo.value=r.modelo_equilibrado;mo.dataset.manual="1";}
    if(!r.dinamico){msg.textContent=r.aviso||"Lista documental; confirme acesso na sua conta e escolha explicitamente.";}
    else if(!modelos.length){msg.textContent="Catálogo textual vazio; escolha preservada. Você pode digitar o identificador manualmente.";}
    else if(mo.value.trim()&&!modelos.some(m=>m.id===mo.value.trim())){msg.textContent="Escolha preservada; identificador não consta deste catálogo. Confira compatibilidade no provedor e clique em Salvar se desejar mantê-lo.";}
    else{msg.textContent=`${modelos.length} modelos consultados. ${disponivel?"Sugestão equilibrada disponível. ":"Sem sugestão equilibrada confirmada; escolha ou digite o modelo. "}Confira e clique em Salvar.`;}
  }catch(x){msg.textContent="Erro: "+x.message+" Escolha preservada.";}
}

async function carregarLLM(){

  try{

    const d=await api("/api/sistema/llm");

    for(const [p,cfg] of Object.entries(d)){

      const ch=$(`#llm-${p}-chave`), mo=$(`#llm-${p}-modelo`), at=$(`#llm-${p}-ativo`);

      if(mo&&cfg.modelo&&!mo.dataset.manual) mo.value=cfg.modelo;

      if(at) at.checked=!!cfg.ativo;

      if(ch){

        if(cfg.tem_chave){

          ch.placeholder=cfg.chave_mascarada?`Chave: ${cfg.chave_mascarada}`:"Chave já cadastrada (oculta)";

          ch.value="";

        }else{

          ch.placeholder="Chave da API";

        }

      }

    }

  }catch(e){}

}

async function salvarLLM(prov){

  const ch=$(`#llm-${prov}-chave`), mo=$(`#llm-${prov}-modelo`), at=$(`#llm-${prov}-ativo`), msg=$(`#msg-llm-${prov}`);

  if(msg) msg.textContent="salvando…";

  const body={provedor:prov,ativo:at?at.checked:false,modelo:mo?mo.value.trim():""};

  if(ch&&ch.value.trim()) body.chave=ch.value.trim();

  try{

    await api("/api/sistema/llm",{json:body});
    if(mo)mo.dataset.manual="";

    if(msg){msg.textContent="Salvo!";setTimeout(()=>msg.textContent="",3000)}

    toast(`Configuração de ${prov.toUpperCase()} salva`);

    carregarLLM();

  }catch(x){if(msg)msg.textContent="Erro: "+x.message}

}



