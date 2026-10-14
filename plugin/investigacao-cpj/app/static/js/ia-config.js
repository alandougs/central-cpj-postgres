// ---------------- configurações de IA (modo agente × API)
async function carregarConfigIA(){
  const modo=$("#cfgia-modo"); if(!modo) return;
  try{
    const c=await api("/api/sistema/ia-config");
    const sel=$("#cfgia-prov");
    sel.innerHTML='<option value="auto">Automático: Claude → GPT → Gemini → demais</option>'+c.provedores_prontos.map(p=>`<option value="${esc(p)}">Começar por ${esc(p)}</option>`).join("");
    modo.value=c.modo_padrao; sel.value=c.provedor_api||"auto"; $("#cfgia-prompt").value=c.prompt_sistema||"";
    if(!c.provedores_prontos.length) $("#msg-cfgia").textContent="Nenhum provedor pronto: ative e salve chave e modelo no cartão de chaves.";
  }catch(x){}
}
if($("#b-cfgia"))$("#b-cfgia").onclick=async()=>{
  const modo=$("#cfgia-modo").value, prov=$("#cfgia-prov").value, msg=$("#msg-cfgia");
  if(modo==="api"&&!confirm("Na via API o conteúdo dos autos extraídos será enviado aos provedores ativos, na ordem escolhida, até uma chamada funcionar. Confirma que isso é compatível com o sigilo do caso?"))return;
  msg.textContent="salvando…";
  try{await api("/api/sistema/ia-config",{json:{modo_padrao:modo,provedor_api:prov,prompt_sistema:$("#cfgia-prompt").value}});msg.textContent="Salvo!";toast("Configurações salvas");setTimeout(()=>msg.textContent="",3000)}
  catch(x){msg.textContent="Erro: "+x.message}
};

