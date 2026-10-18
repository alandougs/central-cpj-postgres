// ---------------- fluxograma financeiro

async function carregarAbaFluxograma(casoIdPre){

  const sel=$("#fx-caso-sel");

  if(!sel)return;

  if(sel.options.length<=1){

    try{

      const cs=await api("/api/casos");

      let h='<option value="">Selecione um caso…</option>';

      for(const c of cs){

        const rot=c.ordem_servico ? `O.S. ${c.ordem_servico}` : c.id;

        const sub=c.bo || c.inquerito || "";

        h+=`<option value="${esc(c.id)}">${esc(rot)}${sub?" — "+esc(sub):""}</option>`;

      }

      sel.innerHTML=h;

    }catch(e){

      console.error("Erro ao listar casos:", e);

    }

  }

  sel.onchange=()=>{

    if(sel.value) carregarFluxoDoCaso(sel.value);

  };



  const alvo = casoIdPre || (sel.value && sel.value !== "" ? sel.value : null) || casoAberto;

  if(alvo){

    sel.value = alvo;

    carregarFluxoDoCaso(alvo);

  } else if(sel.options.length > 1){

    let optAlvo = null;

    for(let i=1; i<sel.options.length; i++){

      if(sel.options[i].value.includes("2586")){

        optAlvo = sel.options[i].value;

        break;

      }

    }

    if(!optAlvo) optAlvo = sel.options[1].value;

    sel.value = optAlvo;

    carregarFluxoDoCaso(optAlvo);

  }

}



async function carregarFluxoDoCaso(id){

  if(!id) return;

  const cont=$("#fx-conteudo"), kpis=$("#fx-kpis"), btnCsv=$("#b-fx-csv"), sel=$("#fx-caso-sel");

  if(sel) sel.value=id;

  if(btnCsv){

    btnCsv.href=`/api/casos/${enc(id)}/fluxo-csv`;

    btnCsv.hidden=false;

  }

  if(cont) cont.innerHTML='<div class="card" style="text-align:center;padding:24px"><div class="muted">Carregando fluxo financeiro…</div></div>';

  try{

    const d=await api(`/api/casos/${enc(id)}/fluxograma`);

    const camadas=d.camadas||[];

    const nCamadas=camadas.length;

    const nTransacoes=d.total_transacoes||camadas.reduce((acc,c)=>acc+(c.transacoes?c.transacoes.length:0),0);

    if(!nCamadas || !nTransacoes){

      if(kpis) kpis.innerHTML="";

      if(cont) cont.innerHTML=`<div class="aviso">Nenhuma movimentação financeira estruturada encontrada para o caso <b>${esc(d.ordem_servico||id)}</b>. Cadastre ou processe extratos para gerar o fluxo.</div>`;

      return;

    }

    if(kpis){

      const totalFmt=d.total_fraude_fmt||(d.total_fraude?"R$ "+d.total_fraude.toLocaleString("pt-BR",{minimumFractionDigits:2,maximumFractionDigits:2}):"—");

      kpis.innerHTML=`

        <div class="kpi alerta"><div class="l">Total Rastreado / Prejuízo</div><div class="kv">${esc(totalFmt)}</div></div>

        <div class="kpi"><div class="l">Transações Mapeadas</div><div class="kv">${nTransacoes}</div></div>

        <div class="kpi"><div class="l">Camadas de Rastreio</div><div class="kv">${nCamadas}</div></div>

        <div class="kpi"><div class="l">Partes Envolvidas</div><div class="kv" style="font-size:16px;font-weight:600">${(d.vitimas||[]).length} vít. / ${(d.investigados||[]).length} inv.</div></div>

      `;

    }

    const cores=["#38BDF8","#FB923C","#34D399","#A78BFA","#F43F5E"];

    let out='<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:16px;align-items:start">';

    camadas.forEach((camObj,idx)=>{

      const txs=camObj.transacoes||[];

      const cor=cores[idx%cores.length];

      const subtotalFmt=camObj.subtotal?`R$ ${camObj.subtotal.toLocaleString("pt-BR",{minimumFractionDigits:2,maximumFractionDigits:2})}`:"";

      out+=`

      <div class="card" style="border-top:3px solid ${cor};background:var(--surface)">

        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;padding-bottom:6px;border-bottom:1px solid var(--line)">

          <h4 style="margin:0;color:${cor};font-size:13.5px">${esc(camObj.titulo||("Camada "+camObj.camada))}</h4>

          ${subtotalFmt?`<span class="badge" style="border-color:${cor}55;color:${cor};font-weight:700">${subtotalFmt}</span>`:""}

        </div>

        <div style="display:flex;flex-direction:column;gap:10px">

      `;

      txs.forEach(t=>{

        out+=`

        <div style="background:var(--page);border:1px solid var(--line);border-radius:6px;padding:10px;font-size:12.5px">

          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">

            <b style="font-size:14px;color:var(--good)">${esc(t.valor_fmt||("R$ "+t.valor))}</b>

            <div style="display:flex;gap:4px">

              ${t.meio?`<span class="badge">${esc(t.meio)}</span>`:""}

              ${t.data?`<span class="muted">${esc(t.data)}${t.hora?" "+esc(t.hora):""}</span>`:""}

            </div>

          </div>

          <div style="margin-bottom:4px">

            <span class="muted">De:</span> <b>${esc(t.origem_titular||"—")}</b>

            ${t.origem_banco?`<span class="muted">(${esc(t.origem_banco)}${t.origem_chave?" · "+esc(t.origem_chave):""})</span>`:""}

          </div>

          <div style="margin-bottom:6px">

            <span class="muted">Para:</span> <b>${esc(t.destino_titular||"—")}</b>

            ${t.destino_banco?`<span class="muted">(${esc(t.destino_banco)}${t.destino_chave?" · "+esc(t.destino_chave):""})</span>`:""}

          </div>

          <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--muted);border-top:1px dashed var(--line);padding-top:4px">

            <span>${t.fls?`fls. ${esc(t.fls)}`:""}</span>

            <span>${t.obs?esc(t.obs):"vínculo direto"}</span>

          </div>

        </div>`;

      });

      out+='</div></div>';

    });

    out+='</div>';

    if(cont) cont.innerHTML=out;

  }catch(x){

    if(cont) cont.innerHTML=`<div class="aviso alerta">Erro ao carregar fluxograma: ${esc(x.message)}</div>`;

  }

}



