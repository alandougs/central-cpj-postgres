// ---------------- fluxograma financeiro e tabela de eventos (AG-R08)

let estadoFluxo = {
  casoId: null,
  dados: null,
  todasTransacoes: [],
  transacoesFiltradas: [],
  visaoAtual: "camadas" // "camadas" ou "tabela"
};

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

  estadoFluxo.casoId = id;

  try{
    const d=await api(`/api/casos/${enc(id)}/fluxograma`);
    estadoFluxo.dados = d;
    const camadas=d.camadas||[];
    const nCamadas=camadas.length;

    // Achata transações
    const todas=[];
    camadas.forEach((camObj,idx)=>{
      (camObj.transacoes||[]).forEach(t=>{
        todas.push({
          ...t,
          camada: camObj.camada || (idx+1),
          camadaTitulo: camObj.titulo || `Camada ${camObj.camada || (idx+1)}`
        });
      });
    });
    estadoFluxo.todasTransacoes = todas;
    estadoFluxo.transacoesFiltradas = todas;

    const nTransacoes=d.total_transacoes||todas.length;

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

    renderizarVisualizacaoFluxo();

  }catch(x){
    if(cont) cont.innerHTML=`<div class="aviso alerta">Erro ao carregar fluxograma: ${esc(x.message)}</div>`;
  }
}

function renderizarVisualizacaoFluxo(){
  const cont = $("#fx-conteudo");
  if (!cont || !estadoFluxo.dados) return;

  const d = estadoFluxo.dados;
  const txs = estadoFluxo.transacoesFiltradas;
  const camadas = d.camadas || [];
  const cores = ["#38BDF8","#FB923C","#34D399","#A78BFA","#F43F5E"];

  let htmlFiltros = `
    <div class="filtros-financeiros">
      <span style="font-weight:600;font-size:12.5px">Filtros de Transações:</span>
      <label>Data Início <input type="date" id="fx-filtro-data-ini"></label>
      <label>Data Fim <input type="date" id="fx-filtro-data-fim"></label>
      <label>Valor Mín <input type="number" id="fx-filtro-val-min" placeholder="R$ min" style="width:85px"></label>
      <label>Valor Máx <input type="number" id="fx-filtro-val-max" placeholder="R$ max" style="width:85px"></label>
      <input id="fx-filtro-termo" placeholder="Buscar titular, banco ou Pix..." style="max-width:200px">
      <button type="button" class="btn sm pri" id="b-fx-aplicar-filtros">Filtrar</button>
      <button type="button" class="btn sm" id="b-fx-limpar-filtros">Limpar</button>
      <button type="button" class="btn sm" id="b-fx-toggle-visao" style="margin-left:auto">${estadoFluxo.visaoAtual === "tabela" ? "Ver em Camadas" : "Ver Tabela Estruturada"}</button>
    </div>
  `;

  // Visão em Camadas
  let htmlCamadas = '<div id="fx-visao-camadas" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:16px;align-items:start"' + (estadoFluxo.visaoAtual === "tabela" ? ' hidden' : '') + '>';
  camadas.forEach((camObj, idx) => {
    const cor = cores[idx % cores.length];
    const subtotalFmt = camObj.subtotal ? `R$ ${camObj.subtotal.toLocaleString("pt-BR",{minimumFractionDigits:2,maximumFractionDigits:2})}` : "";
    const camadaTxs = txs.filter(t => (t.camada === camObj.camada) || (!t.camada && idx === 0));

    htmlCamadas += `
      <div class="card" style="border-top:3px solid ${cor};background:var(--surface)">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;padding-bottom:6px;border-bottom:1px solid var(--line)">
          <h4 style="margin:0;color:${cor};font-size:13.5px">${esc(camObj.titulo || ("Camada " + camObj.camada))}</h4>
          ${subtotalFmt ? `<span class="badge" style="border-color:${cor}55;color:${cor};font-weight:700">${subtotalFmt}</span>` : ""}
        </div>
        <div style="display:flex;flex-direction:column;gap:10px">
    `;

    if (!camadaTxs.length) {
      htmlCamadas += '<div class="muted" style="font-size:12px;padding:8px 0">Nenhuma transação atende aos filtros nesta camada.</div>';
    } else {
      camadaTxs.forEach(t => {
        const precisao = t.hora ? "Exata (com hora)" : (t.data ? "Data sem hora" : "Aproximada");
        htmlCamadas += `
          <div style="background:var(--page);border:1px solid var(--line);border-radius:6px;padding:10px;font-size:12.5px">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
              <b style="font-size:14px;color:var(--good)">${esc(t.valor_fmt || ("R$ " + (Number(t.valor)||0).toFixed(2)))}</b>
              <div style="display:flex;gap:4px;align-items:center">
                <span class="badge-precisao">${esc(precisao)}</span>
                ${t.meio ? `<span class="badge">${esc(t.meio)}</span>` : ""}
                ${t.data ? `<span class="muted">${esc(t.data)}${t.hora ? " " + esc(t.hora) : ""}</span>` : ""}
              </div>
            </div>
            <div style="margin-bottom:4px">
              <span class="muted">De:</span> <b>${esc(t.origem_titular || "—")}</b>
              ${t.origem_banco ? `<span class="muted">(${esc(t.origem_banco)}${t.origem_chave ? " · " + esc(t.origem_chave) : ""})</span>` : ""}
            </div>
            <div style="margin-bottom:6px">
              <span class="muted">Para:</span> <b>${esc(t.destino_titular || "—")}</b>
              ${t.destino_banco ? `<span class="muted">(${esc(t.destino_banco)}${t.destino_chave ? " · " + esc(t.destino_chave) : ""})</span>` : ""}
            </div>
            <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--muted);border-top:1px dashed var(--line);padding-top:4px">
              <span>${t.fls ? `fls. ${esc(t.fls)}` : (t.pagina ? `pág. ${esc(t.pagina)}` : "")}</span>
              <span>${t.obs ? esc(t.obs) : "vínculo direto"}</span>
            </div>
          </div>
        `;
      });
    }

    htmlCamadas += '</div></div>';
  });
  htmlCamadas += '</div>';

  // Visão em Tabela Estruturada (AG-R08)
  let htmlTabela = '<div class="card" id="fx-visao-tabela"' + (estadoFluxo.visaoAtual === "camadas" ? ' hidden' : '') + ' style="overflow-x:auto">';
  htmlTabela += `
    <table style="width:100%;font-size:12.5px" id="fx-tab-transacoes">
      <thead>
        <tr>
          <th>Camada</th>
          <th>Sentido</th>
          <th>Data / Hora</th>
          <th>Precisão Temporal</th>
          <th>Origem (Titular / Banco)</th>
          <th>Destino (Titular / Banco)</th>
          <th class="n">Valor (R$)</th>
          <th>Fonte nos Autos</th>
        </tr>
      </thead>
      <tbody>
  `;

  if (!txs.length) {
    htmlTabela += '<tr><td colspan="8" class="muted" style="text-align:center;padding:16px">Nenhuma transação encontrada com os filtros informados.</td></tr>';
  } else {
    txs.forEach(t => {
      const precisao = t.hora ? "Exata (com hora)" : (t.data ? "Data informada" : "Data aproximada");
      const valorFmt = t.valor_fmt || ("R$ " + (Number(t.valor)||0).toLocaleString("pt-BR", {minimumFractionDigits:2, maximumFractionDigits:2}));
      const fonteDoc = t.fls ? `fls. ${esc(t.fls)}` : (t.pagina ? `pág. ${esc(t.pagina)}` : "documento");

      htmlTabela += `
        <tr>
          <td><span class="badge">${esc(t.camadaTitulo || ("Camada " + (t.camada||1)))}</span></td>
          <td><span class="badge-transacao badge-enviado">Transferência</span></td>
          <td><b>${esc(t.data || "—")}</b> ${t.hora ? esc(t.hora) : ""}</td>
          <td><span class="badge-precisao">${esc(precisao)}</span></td>
          <td><b>${esc(t.origem_titular || "—")}</b><br><span class="muted">${esc(t.origem_banco || "")}${t.origem_chave ? " · " + esc(t.origem_chave) : ""}</span></td>
          <td><b>${esc(t.destino_titular || "—")}</b><br><span class="muted">${esc(t.destino_banco || "")}${t.destino_chave ? " · " + esc(t.destino_chave) : ""}</span></td>
          <td class="n" style="font-weight:700;color:var(--good)">${esc(valorFmt)}</td>
          <td>${esc(fonteDoc)}</td>
        </tr>
      `;
    });
  }

  htmlTabela += '</tbody></table></div>';

  cont.innerHTML = htmlFiltros + htmlCamadas + htmlTabela;

  // Binds de filtros e alternância de visão
  const bToggle = $("#b-fx-toggle-visao");
  if (bToggle) {
    bToggle.onclick = () => {
      estadoFluxo.visaoAtual = estadoFluxo.visaoAtual === "camadas" ? "tabela" : "camadas";
      renderizarVisualizacaoFluxo();
    };
  }

  const bAplicar = $("#b-fx-aplicar-filtros");
  if (bAplicar) {
    bAplicar.onclick = () => {
      const dtIni = $("#fx-filtro-data-ini")?.value;
      const dtFim = $("#fx-filtro-data-fim")?.value;
      const valMin = parseFloat($("#fx-filtro-val-min")?.value || "");
      const valMax = parseFloat($("#fx-filtro-val-max")?.value || "");
      const termo = ($("#fx-filtro-termo")?.value || "").toLowerCase().trim();

      estadoFluxo.transacoesFiltradas = estadoFluxo.todasTransacoes.filter(t => {
        if (dtIni && t.data && t.data < dtIni) return false;
        if (dtFim && t.data && t.data > dtFim) return false;
        const val = Number(t.valor) || 0;
        if (!isNaN(valMin) && val < valMin) return false;
        if (!isNaN(valMax) && val > valMax) return false;
        if (termo) {
          const haystack = `${t.origem_titular || ""} ${t.destino_titular || ""} ${t.origem_banco || ""} ${t.destino_banco || ""} ${t.origem_chave || ""} ${t.destino_chave || ""}`.toLowerCase();
          if (!haystack.includes(termo)) return false;
        }
        return true;
      });
      renderizarVisualizacaoFluxo();
    };
  }

  const bLimpar = $("#b-fx-limpar-filtros");
  if (bLimpar) {
    bLimpar.onclick = () => {
      estadoFluxo.transacoesFiltradas = estadoFluxo.todasTransacoes;
      renderizarVisualizacaoFluxo();
    };
  }
}

window.CPJFluxograma = {
  carregar: carregarFluxoDoCaso,
  carregarAba: carregarAbaFluxograma,
  estado: () => estadoFluxo
};

