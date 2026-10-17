/* Inteligência Relacional e Geográfica — Etapa 1 (Central CPJ)
 * Escopo estrito: Radar de coincidências documentadas entre procedimentos distintos
 * e Mapa de referência offline (100% local, zero requisições externas).
 */
(function () {
  "use strict";

  const MOTIVOS_GEO_ROTULO = {
    sem_endereco: "Sem endereço documentado",
    endereco_incompleto: "Endereço incompleto (sem município/UF identificável)",
    municipio_ambiguo: "Município homônimo sem UF documentada (ambíguo)",
    municipio_incerto: "Município com dígito/grafia incerta nos autos",
    municipio_nao_encontrado_na_base_local: "Município não localizado na base geográfica offline",
    localizacao_conflitante: "Múltiplos endereços em municípios distintos (localização conflitante)",
    coordenada_contexto_incompativel: "Coordenada documentada com contexto incompatível (ex.: local do fato)",
    sem_endereco_pj_associada: "PJ associada na qualificação de PF sem endereço próprio documentado",
    sem_qualificacao_geografica: "Ocorrência sem ficha de qualificação geográfica no caso",
  };

  let estadoCorrelacoes = {
    itens: [],
    total: 0,
    pagina: 1,
    limite: 50,
    parcial: false,
    desatualizado: false,
    motivo_desatualizado: null,
    resumo: { ativos: 0, fixados: 0, descartados: 0, nao_lidos: 0, requer_revisao: 0 },
    limitacoes_procedimento: [],
    limitacoes_coleta: [],
    filtros: {
      caso: "",
      tipo: "",
      estado: "ativos_e_fixados",
      lido: "",
      ordem: "procedimentos",
    },
  };

  let estadoMapa = {
    pontos: [],
    grupos: [],
    sem_localizacao: [],
    resumo: {
      total_registros: 0,
      localizados: 0,
      sem_localizacao: 0,
      pf_localizados: 0,
      pj_localizados: 0,
      precisao_municipio: 0,
      precisao_coordenada: 0,
    },
    correlacao_selecionada: null,
    cartografia: null,
    desatualizado: false,
    motivo_desatualizado: null,
    selecionado: null,
    grupoAberto: null,
    zoom: 1,
    panX: 0,
    panY: 0,
    filtros: {
      caso: "",
      tipo_pessoa: "",
      papel: "",
      uf: "",
      municipio: "",
      correlacao_id: "",
    },
  };

  function escHtml(s) {
    if (typeof window.esc === "function") return window.esc(s);
    return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  function encUri(s) {
    return encodeURIComponent(String(s ?? ""));
  }

  async function chamarApi(url, opts) {
    if (typeof window.api === "function") return window.api(url, opts);
    const headers = { "X-CPJ": "1" };
    const fetchOpts = { method: (opts && opts.method) || "GET", headers, credentials: "same-origin" };
    if (opts && opts.json !== undefined) {
      fetchOpts.method = "POST";
      headers["Content-Type"] = "application/json";
      fetchOpts.body = JSON.stringify(opts.json);
    }
    const r = await fetch(url, fetchOpts);
    const j = await r.json();
    if (!r.ok) throw new Error(j.erro || `Erro HTTP ${r.status}`);
    return j;
  }

  function notificar(msg) {
    if (typeof window.toast === "function") window.toast(msg);
  }

  // ---------------------------------------------------------------- Navegação entre módulos (§3.4)

  function navegarParaQualificacao(item) {
    if (typeof window.abrirAba === "function") window.abrirAba("pesquisa");
    ativarModoPesquisa("pessoas");
    const form = document.getElementById("f-pessoas");
    if (!form) return;
    form.reset();
    if (item.cpf && form.elements.cpf) {
      form.elements.cpf.value = item.cpf;
    } else if (item.cnpj && form.elements.cnpj) {
      form.elements.cnpj.value = item.cnpj;
    } else if (item.nome && form.elements.nome) {
      form.elements.nome.value = item.nome;
    }
    form.requestSubmit();
  }

  function navegarParaCaso(casoId) {
    if (!casoId) return;
    if (typeof window.abrirAba === "function") window.abrirAba("casos");
    if (typeof window.abrirCaso === "function") window.abrirCaso(casoId);
  }

  function navegarParaGrafo(termo, casoId) {
    if (typeof window.abrirAba === "function") window.abrirAba("grafo");
    const selCaso = document.getElementById("gr-caso");
    const inpBusca = document.getElementById("gr-busca");
    if (selCaso && casoId) selCaso.value = casoId;
    if (inpBusca && termo) inpBusca.value = termo;
    if (typeof window.carregarGrafo === "function") window.carregarGrafo();
  }

  function montarUrlFonte(casoId, fonteObj) {
    if (!casoId || !fonteObj) return null;
    let arq = String(fonteObj.arquivo || "").replace(/\\/g, "/").trim();
    if (!arq) return null;
    if (arq.startsWith(`casos/${casoId}/`)) {
      arq = arq.slice(`casos/${casoId}/`.length);
    } else if (arq.startsWith("casos/")) {
      const partes = arq.split("/");
      if (partes.length >= 3) arq = partes.slice(2).join("/");
    }
    if (!arq || arq.startsWith("caso.json")) return null;
    const urlBase = `/arquivo/${encUri(casoId)}/${arq.split("/").map(encUri).join("/")}`;
    const pag = fonteObj.pagina;
    if (pag && Number.isInteger(Number(pag)) && arq.toLowerCase().endsWith(".pdf")) {
      return `${urlBase}#page=${Number(pag)}`;
    }
    return urlBase;
  }

  function formatarCitacaoFonte(fonteObj) {
    if (!fonteObj) return "Fonte nos autos";
    const partes = [];
    if (fonteObj.arquivo) {
      const nomeArq = String(fonteObj.arquivo).replace(/\\/g, "/").split("/").pop();
      partes.push(nomeArq);
    }
    if (fonteObj.documento && fonteObj.documento !== fonteObj.arquivo) {
      partes.push(fonteObj.documento);
    }
    // Regra: nunca presumir que página do PDF equivale a fls. Mostrar cada um quando disponível.
    if (fonteObj.pagina) partes.push(`pág. PDF ${fonteObj.pagina}`);
    if (fonteObj.fls) partes.push(`fls. ${fonteObj.fls}`);
    return partes.join(" · ") || "Fonte documentada";
  }

  // ---------------------------------------------------------------- Inicialização de sub-modos em Pesquisa e Grafo

  function ativarModoPesquisa(modo) {
    const segBtns = document.querySelectorAll("#pesquisa .seg button");
    segBtns.forEach((b) => b.classList.toggle("on", b.dataset.m === modo));
    const paineis = {
      pessoas: document.getElementById("m-pessoas"),
      texto: document.getElementById("m-texto"),
      correlacoes: document.getElementById("m-correlacoes"),
      mapa: document.getElementById("m-mapa"),
    };
    Object.entries(paineis).forEach(([k, el]) => {
      if (el) el.hidden = k !== modo;
    });
    if (modo === "correlacoes") carregarCorrelacoes();
    if (modo === "mapa") carregarMapa();
  }

  function construirContainersDom() {
    const secPesquisa = document.getElementById("pesquisa");
    if (!secPesquisa) return;

    let mCorr = document.getElementById("m-correlacoes");
    if (!mCorr) {
      mCorr = document.createElement("div");
      mCorr.id = "m-correlacoes";
      mCorr.hidden = true;
      secPesquisa.appendChild(mCorr);
    }

    let mMapa = document.getElementById("m-mapa");
    if (!mMapa) {
      mMapa = document.createElement("div");
      mMapa.id = "m-mapa";
      mMapa.hidden = true;
      secPesquisa.appendChild(mMapa);
    }

    mCorr.innerHTML = `
      <div class="card" style="margin-bottom:12px">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:8px">
          <div>
            <h3 style="margin:0">Radar de Coincidências Documentadas (Etapa 1)</h3>
            <p class="muted" style="margin:2px 0 0">Ocorrências exatas do mesmo identificador completo em <b>dois ou mais procedimentos distintos</b>. Sem inferência automática nem score.</p>
          </div>
          <div class="acoes" style="margin:0">
            <button type="button" class="btn sm" id="b-corr-atualizar">Atualizar lista</button>
            <button type="button" class="btn sm" id="b-corr-ir-mapa">Abrir Mapa Offline</button>
          </div>
        </div>
        <div id="corr-aviso-desatualizado" hidden class="aviso alerta" style="margin-bottom:10px"></div>
        <div class="kpis" id="corr-kpis" style="margin-bottom:10px"></div>
        <form id="f-correlacoes-filtros" class="campos" style="grid-template-columns:repeat(auto-fit,minmax(170px,1fr));align-items:end">
          <div>
            <label for="corr-f-caso">Caso / O.S.</label>
            <input id="corr-f-caso" placeholder="Ex.: OS-2580-2026">
          </div>
          <div>
            <label for="corr-f-tipo">Tipo de identificador</label>
            <select id="corr-f-tipo">
              <option value="">Todos os tipos</option>
              <option value="CPF">CPF</option>
              <option value="CNPJ">CNPJ</option>
              <option value="CHAVE_PIX">Chave Pix</option>
              <option value="CONTA">Conta bancária (com banco)</option>
              <option value="TELEFONE">Telefone</option>
              <option value="EMAIL">E-mail</option>
              <option value="PLACA">Placa de veículo</option>
            </select>
          </div>
          <div>
            <label for="corr-f-estado">Estado de revisão</label>
            <select id="corr-f-estado">
              <option value="ativos_e_fixados" selected>Ativos e fixados</option>
              <option value="ativo">Somente ativos</option>
              <option value="fixado">Somente fixados</option>
              <option value="descartado">Descartados</option>
              <option value="todos">Todos</option>
            </select>
          </div>
          <div>
            <label for="corr-f-lido">Situação de leitura</label>
            <select id="corr-f-lido">
              <option value="">Lidos e não lidos</option>
              <option value="0">Não lidos</option>
              <option value="1">Já lidos</option>
            </select>
          </div>
          <div>
            <label for="corr-f-ordem">Ordenar por</label>
            <select id="corr-f-ordem">
              <option value="procedimentos">Nº de procedimentos</option>
              <option value="recentes">Última atualização</option>
            </select>
          </div>
          <div class="acoes" style="margin:0">
            <button type="submit" class="btn pri">Filtrar</button>
            <button type="button" class="btn" id="b-corr-limpar">Limpar</button>
          </div>
        </form>
      </div>
      <div id="corr-limitacoes-box" hidden style="margin-bottom:12px"></div>
      <div id="corr-lista"></div>
    `;

    mMapa.innerHTML = `
      <div class="card" style="margin-bottom:12px">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:8px">
          <div>
            <h3 style="margin:0">Mapa Tático de Referência — Malha Oficial IBGE (5.570 Municípios)</h3>
            <p class="muted" style="margin:2px 0 0">Cartografia vetorial oficial das 27 UFs e sedes municipais do IBGE (100% local, zero requisições externas).</p>
          </div>
          <div class="acoes" style="margin:0;flex-wrap:wrap">
            <button type="button" class="btn sm pri" id="b-mapa-fit-pontos" title="Enquadrar automaticamente todos os pontos visíveis">Enquadrar Pontos</button>
            <button type="button" class="btn sm" id="b-mapa-foco-deinter8" title="Focar na região de Presidente Prudente / DEINTER 8">DEINTER 8</button>
            <button type="button" class="btn sm" id="b-mapa-foco-sp" title="Focar no Estado de São Paulo">Estado de SP</button>
            <button type="button" class="btn sm" id="b-mapa-reset-zoom" title="Visão geral do Brasil">Brasil Inteiro</button>
            <button type="button" class="btn sm" id="b-mapa-voltar-radar">Radar de Correlações</button>
          </div>
        </div>
        <div id="mapa-aviso-desatualizado" hidden class="aviso alerta" style="margin-bottom:8px"></div>
        <div id="mapa-banner-correlacao" hidden class="aviso" style="margin-bottom:8px;display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap"></div>
        <div class="kpis" id="mapa-kpis" style="margin-bottom:10px"></div>
        <form id="f-mapa-filtros" class="campos" style="grid-template-columns:repeat(auto-fit,minmax(150px,1fr));align-items:end">
          <div>
            <label for="mapa-f-caso">Caso / O.S.</label>
            <input id="mapa-f-caso" placeholder="Ex.: OS-2580-2026">
          </div>
          <div>
            <label for="mapa-f-tipo">Natureza (PF / PJ)</label>
            <select id="mapa-f-tipo">
              <option value="">PF e PJ</option>
              <option value="PF">Pessoa Física (PF)</option>
              <option value="PJ">Pessoa Jurídica (PJ)</option>
            </select>
          </div>
          <div>
            <label for="mapa-f-papel">Condição / Papel</label>
            <input id="mapa-f-papel" placeholder="vítima, investigado…">
          </div>
          <div>
            <label for="mapa-f-uf">UF</label>
            <input id="mapa-f-uf" maxlength="2" placeholder="Ex.: SP">
          </div>
          <div>
            <label for="mapa-f-municipio">Município</label>
            <input id="mapa-f-municipio" placeholder="Ex.: Presidente Prudente">
          </div>
          <div class="acoes" style="margin:0">
            <button type="submit" class="btn pri">Aplicar</button>
            <button type="button" class="btn" id="b-mapa-limpar">Limpar</button>
          </div>
        </form>
      </div>

      <div style="display:grid;grid-template-columns:1fr 380px;gap:12px;min-height:580px">
        <div class="card" style="padding:0;position:relative;overflow:hidden;background:radial-gradient(circle at 55% 55%, #0c1c36 0%, #060d18 85%);border:1px solid #1e3a5f;display:flex;flex-direction:column;box-shadow:inset 0 0 40px rgba(0,0,0,0.65)">
          <svg id="svg-mapa-offline" viewBox="0 0 800 560" role="img" aria-label="Mapa tático offline do Brasil — Malha IBGE" style="width:100%;height:530px;display:block;cursor:grab;user-select:none"></svg>

          <!-- Controles flutuantes de zoom e indicador de escala -->
          <div style="position:absolute;top:12px;right:12px;display:flex;flex-direction:column;gap:4px;z-index:4">
            <button type="button" class="btn sm" id="b-mapa-zoom-in" title="Aproximar (+)" style="width:32px;height:32px;padding:0;font-weight:700;font-size:16px;background:rgba(10,20,38,0.9);border-color:#284b7a;color:#e2e8f0">+</button>
            <button type="button" class="btn sm" id="b-mapa-zoom-out" title="Afastar (−)" style="width:32px;height:32px;padding:0;font-weight:700;font-size:16px;background:rgba(10,20,38,0.9);border-color:#284b7a;color:#e2e8f0">−</button>
            <div id="mapa-zoom-label" style="text-align:center;font-size:10px;color:#94a3b8;background:rgba(6,13,24,0.85);padding:2px 4px;border-radius:4px;border:1px solid #1e3250">1.0×</div>
          </div>

          <!-- Tooltip tático flutuante -->
          <div id="mapa-tooltip-hud" hidden style="position:absolute;pointer-events:none;max-width:290px;background:rgba(7,15,28,0.95);border:1px solid #38bdf8;border-radius:7px;padding:8px 10px;z-index:6;box-shadow:0 8px 24px rgba(0,0,0,0.6);font-size:11.5px;color:#f1f5f9"></div>

          <!-- Caixa lateral de detalhamento do agrupamento (leque) -->
          <div id="mapa-fanout-box" hidden style="position:absolute;top:12px;left:12px;width:310px;max-height:390px;overflow-y:auto;background:rgba(8,16,30,0.95);border:1px solid #38BDF8;border-radius:8px;padding:10px;z-index:5;box-shadow:0 10px 28px rgba(0,0,0,0.65)"></div>

          <div style="padding:8px 12px;border-top:1px solid #1e3250;background:rgba(7,14,26,0.95);font-size:11.5px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;color:#cbd5e1">
            <span style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
              <span><span style="color:#0ea5e9;font-weight:700">●</span> Pessoa Física (PF)</span>
              <span><span style="color:#10b981;font-weight:700">◆</span> Pessoa Jurídica (PJ)</span>
              <span><span style="color:#38bdf8;font-weight:700">◉</span> Agrupamento Municipal (clique para abrir em leque)</span>
              <span style="border:1px dashed #94A3B8;padding:1px 6px;border-radius:4px;font-size:11px">Município aproximado (IBGE)</span>
              <span style="border:1px solid #FBBF24;padding:1px 6px;border-radius:4px;color:#FBBF24;font-size:11px">Coordenada documentada</span>
            </span>
            <span class="muted" id="mapa-meta-licenca" style="font-size:11px">Malha Oficial IBGE · 5.570 Municípios</span>
          </div>
        </div>

        <div style="display:flex;flex-direction:column;gap:12px">
          <div class="card" id="mapa-inspetor" style="flex:1;overflow-y:auto">
            <h4 style="margin:0 0 6px">Inspetor Geográfico</h4>
            <p class="muted" id="mapa-inspetor-vazio">Clique em qualquer pino, cidade ou item do leque no mapa (ou num registro sem localização abaixo) para abrir a qualificação, precisão, fontes nos autos e os 4 atalhos diretos.</p>
            <div id="mapa-inspetor-conteudo"></div>
          </div>

          <div class="card" style="max-height:260px;overflow-y:auto">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
              <h4 style="margin:0">Registros sem localização resolvida</h4>
              <span class="badge" id="mapa-badge-semloc">0</span>
            </div>
            <p class="muted" style="margin:0 0 8px;font-size:11.5px">Municípios homônimos sem UF, endereços incompletos ou conflitantes permanecem fora do mapa até confirmação.</p>
            <div id="mapa-lista-semloc"></div>
          </div>
        </div>
      </div>
    `;

    // Eventos do Radar de Correlações
    document.getElementById("f-correlacoes-filtros").addEventListener("submit", (e) => {
      e.preventDefault();
      estadoCorrelacoes.filtros.caso = document.getElementById("corr-f-caso").value.trim();
      estadoCorrelacoes.filtros.tipo = document.getElementById("corr-f-tipo").value;
      estadoCorrelacoes.filtros.estado = document.getElementById("corr-f-estado").value;
      estadoCorrelacoes.filtros.lido = document.getElementById("corr-f-lido").value;
      estadoCorrelacoes.filtros.ordem = document.getElementById("corr-f-ordem").value;
      estadoCorrelacoes.pagina = 1;
      carregarCorrelacoes();
    });

    document.getElementById("b-corr-limpar").addEventListener("click", () => {
      document.getElementById("f-correlacoes-filtros").reset();
      estadoCorrelacoes.filtros = { caso: "", tipo: "", estado: "ativos_e_fixados", lido: "", ordem: "procedimentos" };
      estadoCorrelacoes.pagina = 1;
      carregarCorrelacoes();
    });

    document.getElementById("b-corr-atualizar").addEventListener("click", () => carregarCorrelacoes());
    document.getElementById("b-corr-ir-mapa").addEventListener("click", () => ativarModoPesquisa("mapa"));

    // Eventos do Mapa Offline
    document.getElementById("f-mapa-filtros").addEventListener("submit", (e) => {
      e.preventDefault();
      estadoMapa.filtros.caso = document.getElementById("mapa-f-caso").value.trim();
      estadoMapa.filtros.tipo_pessoa = document.getElementById("mapa-f-tipo").value;
      estadoMapa.filtros.papel = document.getElementById("mapa-f-papel").value.trim();
      estadoMapa.filtros.uf = document.getElementById("mapa-f-uf").value.trim().toUpperCase();
      estadoMapa.filtros.municipio = document.getElementById("mapa-f-municipio").value.trim();
      estadoMapa.enquadrarAoCarregar = true;
      carregarMapa();
    });

    document.getElementById("b-mapa-limpar").addEventListener("click", () => {
      document.getElementById("f-mapa-filtros").reset();
      estadoMapa.filtros = { caso: "", tipo_pessoa: "", papel: "", uf: "", municipio: "", correlacao_id: "" };
      estadoMapa.selecionado = null;
      estadoMapa.grupoAberto = null;
      estadoMapa.enquadrarAoCarregar = true;
      carregarMapa();
    });

    document.getElementById("b-mapa-voltar-radar").addEventListener("click", () => ativarModoPesquisa("correlacoes"));
    document.getElementById("b-mapa-fit-pontos").addEventListener("click", () => enquadrarPontosMapa());
    document.getElementById("b-mapa-reset-zoom").addEventListener("click", () => {
      estadoMapa.zoom = 1;
      estadoMapa.panX = 0;
      estadoMapa.panY = 0;
      desenharSvgMapa();
    });
    document.getElementById("b-mapa-foco-sp").addEventListener("click", () => {
      enquadrarCaixaLatLon(-25.4, -53.2, -19.7, -44.1);
    });
    document.getElementById("b-mapa-foco-deinter8").addEventListener("click", () => {
      enquadrarCaixaLatLon(-23.1, -53.2, -21.1, -49.8);
    });
    document.getElementById("b-mapa-zoom-in").addEventListener("click", () => aplicarZoomCentro(1.45));
    document.getElementById("b-mapa-zoom-out").addEventListener("click", () => aplicarZoomCentro(1 / 1.45));

    configurarInteracaoSvgMapa();
  }

  // ---------------------------------------------------------------- Radar de Correlações: Carregamento e Renderização

  async function carregarCorrelacoes() {
    const cont = document.getElementById("corr-lista");
    if (!cont) return;
    cont.innerHTML = '<div class="card"><span class="muted">Consultando coincidências documentadas…</span></div>';

    const f = estadoCorrelacoes.filtros;
    const qs = new URLSearchParams();
    if (f.caso) qs.set("caso", f.caso);
    if (f.tipo) qs.set("tipo", f.tipo);
    if (f.estado) qs.set("estado", f.estado);
    if (f.lido !== "") qs.set("lido", f.lido);
    if (f.ordem) qs.set("ordem", f.ordem);
    qs.set("pagina", String(estadoCorrelacoes.pagina));
    qs.set("limite", String(estadoCorrelacoes.limite));

    try {
      const res = await chamarApi(`/api/inteligencia/correlacoes?${qs.toString()}`);
      Object.assign(estadoCorrelacoes, res);
      renderizarCorrelacoes();
    } catch (e) {
      cont.innerHTML = `<div class="aviso alerta">Erro ao consultar correlações: ${escHtml(e.message)}</div>`;
    }
  }

  function renderizarCorrelacoes() {
    const avisoDesat = document.getElementById("corr-aviso-desatualizado");
    if (avisoDesat) {
      if (estadoCorrelacoes.desatualizado) {
        avisoDesat.hidden = false;
        avisoDesat.innerHTML = `<b>Atenção:</b> Os dados derivados de correlações/mapa estão desatualizados em relação às últimas alterações nos casos (${escHtml(estadoCorrelacoes.motivo_desatualizado || "reindexação pendente")}). Reindexe a base para atualizar.`;
      } else {
        avisoDesat.hidden = true;
      }
    }

    const kpis = document.getElementById("corr-kpis");
    const r = estadoCorrelacoes.resumo || {};
    if (kpis) {
      kpis.innerHTML = `
        <div class="kpi"><div class="l">Ativas</div><div class="kv">${r.ativos || 0}</div></div>
        <div class="kpi"><div class="l">Fixadas</div><div class="kv">${r.fixados || 0}</div></div>
        <div class="kpi"><div class="l">Não lidas</div><div class="kv">${r.nao_lidos || 0}</div></div>
        <div class="kpi ${r.requer_revisao ? "alerta" : ""}"><div class="l">Requerem revisão</div><div class="kv">${r.requer_revisao || 0}</div></div>
        <div class="kpi"><div class="l">Descartadas</div><div class="kv">${r.descartados || 0}</div></div>
      `;
    }

    const limBox = document.getElementById("corr-limitacoes-box");
    const limProc = estadoCorrelacoes.limitacoes_procedimento || [];
    const limCol = estadoCorrelacoes.limitacoes_coleta || [];
    if (limBox) {
      if (limProc.length || limCol.length) {
        limBox.hidden = false;
        limBox.innerHTML = `
          <details class="card" style="border-color:var(--warn)">
            <summary style="cursor:pointer;font-weight:600">Limitações documentais registradas (${limProc.length + limCol.length}) — não contabilizadas como coincidências confirmadas</summary>
            <div style="margin-top:8px;font-size:12.5px">
              ${limProc.map((lp) => `<div style="margin-bottom:6px">• <b>Procedimento não confirmado:</b> ${escHtml(lp.mensagem)}</div>`).join("")}
              ${limCol.slice(0, 30).map((lc) => `<div style="margin-bottom:4px" class="muted">• <b>${escHtml(lc.caso)}</b> — ${escHtml(lc.tipo)} <code>${escHtml(lc.valor_bruto)}</code> ignorado na coincidência exata (${escHtml(lc.motivo)}).</div>`).join("")}
            </div>
          </details>
        `;
      } else {
        limBox.hidden = true;
        limBox.innerHTML = "";
      }
    }

    const cont = document.getElementById("corr-lista");
    if (!cont) return;
    const itens = estadoCorrelacoes.itens || [];
    if (!itens.length) {
      cont.innerHTML = `<div class="vazio">Nenhuma coincidência documentada encontrada para os filtros selecionados.</div>`;
      return;
    }

    cont.innerHTML = itens
      .map((item) => {
        const badgeEstado =
          item.estado === "fixado"
            ? `<span class="badge st-conf">★ Fixado</span>`
            : item.estado === "descartado"
            ? `<span class="badge st-neg">Descartado</span>`
            : `<span class="badge">Ativo</span>`;
        const badgeLido = item.lido
          ? `<span class="badge st-hist">Lido</span>`
          : `<span class="badge st-ind">● Não lido</span>`;
        const badgeRev = item.requer_revisao
          ? `<span class="badge st-conf" style="border-color:var(--warn);color:var(--warn)">⚠ Requer revisão (evidência alterada)</span>`
          : "";

        const ocorrenciasHtml = (item.ocorrencias || [])
          .map((oc) => {
            const papeisStr = (oc.papeis || []).join(", ") || "mencionado nos autos";
            const pessoasStr = (oc.pessoas_associadas || []).join(" · ") || "—";
            const fontesHtml = (oc.fontes || [])
              .map((f) => {
                const cit = formatarCitacaoFonte(f);
                const url = montarUrlFonte(oc.caso, f);
                return `<span style="margin-right:8px">${url ? `<a class="lk" href="${escHtml(url)}" target="_blank" rel="noopener">${escHtml(cit)}</a>` : escHtml(cit)}</span>`;
              })
              .join("");
            return `
              <tr>
                <td><a class="lk" data-corr-abrir-caso="${escHtml(oc.caso)}"><b>${escHtml(oc.caso)}</b></a></td>
                <td>${escHtml(oc.procedimento_rotulo || oc.procedimento_id)}</td>
                <td><b>${escHtml(pessoasStr)}</b></td>
                <td>${escHtml(papeisStr)}</td>
                <td style="font-size:12px">${fontesHtml || "—"}</td>
              </tr>
            `;
          })
          .join("");

        return `
          <div class="card" data-corr-card="${escHtml(item.id)}" style="margin-bottom:10px;border-left:4px solid ${item.estado === "fixado" ? "#34D399" : item.estado === "descartado" ? "#64748B" : "#38BDF8"}">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;flex-wrap:wrap">
              <div>
                <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin-bottom:4px">
                  <span class="badge"><b>${escHtml(item.rotulo_tipo || item.tipo)}</b></span>
                  <code style="font-size:13.5px;font-weight:700">${escHtml(item.valor_exibicao)}</code>
                  ${badgeEstado}
                  ${badgeLido}
                  ${badgeRev}
                </div>
                <h4 style="margin:2px 0 4px">${escHtml(item.titulo)}</h4>
                <p class="muted" style="margin:0 0 8px">${escHtml(item.explicacao)}</p>
                ${item.motivo ? `<div class="muted" style="margin-bottom:6px"><b>Motivo registrado (${escHtml(item.usuario_estado || "operador")}):</b> ${escHtml(item.motivo)}</div>` : ""}
              </div>
              <div class="acoes" style="margin:0">
                <button type="button" class="btn sm" data-corr-acao="lido" data-id="${escHtml(item.id)}" data-lido="${item.lido ? "0" : "1"}">${item.lido ? "Marcar não lido" : "Marcar como lido"}</button>
                <button type="button" class="btn sm" data-corr-acao="fixar" data-id="${escHtml(item.id)}" data-atual="${escHtml(item.estado)}">${item.estado === "fixado" ? "Desafixar" : "Fixar"}</button>
                ${
                  item.estado === "descartado"
                    ? `<button type="button" class="btn sm" data-corr-acao="reativar" data-id="${escHtml(item.id)}">Reativar</button>`
                    : `<button type="button" class="btn sm" data-corr-acao="abrir-descarte" data-id="${escHtml(item.id)}">Descartar…</button>`
                }
                <button type="button" class="btn sm pri" data-corr-acao="mapa" data-id="${escHtml(item.id)}">Ver no Mapa</button>
                <button type="button" class="btn sm" data-corr-acao="grafo" data-valor="${escHtml(item.valor_exibicao)}" data-caso="${escHtml((item.casos || [])[0] || "")}">Abrir no Grafo</button>
              </div>
            </div>

            <div id="descarte-box-${escHtml(item.id)}" hidden style="margin:8px 0;padding:8px;background:var(--page);border:1px solid var(--line);border-radius:6px">
              <label style="font-size:12px">Motivo do descarte (obrigatório, ex.: conta institucional de concessionária, homônimo já descartado):</label>
              <div style="display:flex;gap:6px;margin-top:4px">
                <input id="inp-motivo-${escHtml(item.id)}" placeholder="Informe o motivo do descarte…">
                <button type="button" class="btn sm pri" data-corr-acao="confirmar-descarte" data-id="${escHtml(item.id)}">Confirmar descarte</button>
                <button type="button" class="btn sm" data-corr-acao="cancelar-descarte" data-id="${escHtml(item.id)}">Cancelar</button>
              </div>
            </div>

            <div style="overflow-x:auto;margin-top:8px">
              <table>
                <thead>
                  <tr><th>O.S. / Caso</th><th>Procedimento (IPe / Processo)</th><th>Pessoa / Empresa associada</th><th>Condição / Papel documentado</th><th>Fontes nos autos</th></tr>
                </thead>
                <tbody>${ocorrenciasHtml}</tbody>
              </table>
            </div>
          </div>
        `;
      })
      .join("");

    // Bind de ações dos cards
    cont.querySelectorAll("[data-corr-abrir-caso]").forEach((el) => {
      el.addEventListener("click", () => navegarParaCaso(el.dataset.corrAbrirCaso));
    });

    cont.querySelectorAll("[data-corr-acao]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const acao = btn.dataset.corrAcao;
        const cid = btn.dataset.id;
        if (acao === "lido") {
          await atualizarEstadoCorrelacaoUI(cid, { lido: btn.dataset.lido === "1" });
        } else if (acao === "fixar") {
          const novoEst = btn.dataset.atual === "fixado" ? "ativo" : "fixado";
          await atualizarEstadoCorrelacaoUI(cid, { estado: novoEst });
        } else if (acao === "reativar") {
          await atualizarEstadoCorrelacaoUI(cid, { estado: "ativo", motivo: "" });
        } else if (acao === "abrir-descarte") {
          const box = document.getElementById(`descarte-box-${cid}`);
          if (box) {
            box.hidden = false;
            const inp = document.getElementById(`inp-motivo-${cid}`);
            if (inp) inp.focus();
          }
        } else if (acao === "cancelar-descarte") {
          const box = document.getElementById(`descarte-box-${cid}`);
          if (box) box.hidden = true;
        } else if (acao === "confirmar-descarte") {
          const inp = document.getElementById(`inp-motivo-${cid}`);
          const motivo = inp ? inp.value.trim() : "";
          if (motivo.length < 3) {
            notificar("Informe um motivo com pelo menos 3 caracteres para descartar.");
            return;
          }
          await atualizarEstadoCorrelacaoUI(cid, { estado: "descartado", motivo });
        } else if (acao === "mapa") {
          estadoMapa.filtros.correlacao_id = cid;
          ativarModoPesquisa("mapa");
        } else if (acao === "grafo") {
          navegarParaGrafo(btn.dataset.valor, btn.dataset.caso);
        }
      });
    });
  }

  async function atualizarEstadoCorrelacaoUI(cid, payload) {
    try {
      await chamarApi("/api/inteligencia/correlacoes/estado", {
        json: { id: cid, ...payload },
      });
      notificar("Estado da coincidência atualizado.");
      await carregarCorrelacoes();
    } catch (e) {
      notificar("Erro: " + e.message);
    }
  }

  // ---------------------------------------------------------------- Mapa Offline: Carregamento e Renderização Vetorial IBGE

  async function carregarMapa() {
    const f = estadoMapa.filtros;
    const qs = new URLSearchParams();
    if (f.caso) qs.set("caso", f.caso);
    if (f.tipo_pessoa) qs.set("tipo_pessoa", f.tipo_pessoa);
    if (f.papel) qs.set("papel", f.papel);
    if (f.uf) qs.set("uf", f.uf);
    if (f.municipio) qs.set("municipio", f.municipio);
    if (f.correlacao_id) qs.set("correlacao_id", f.correlacao_id);

    try {
      const res = await chamarApi(`/api/inteligencia/mapa?${qs.toString()}`);
      const primeiraCarga = !estadoMapa.jaCarregou;
      Object.assign(estadoMapa, res);
      estadoMapa.jaCarregou = true;
      renderizarPainelMapa();
      if (primeiraCarga || estadoMapa.enquadrarAoCarregar || f.correlacao_id) {
        estadoMapa.enquadrarAoCarregar = false;
        enquadrarPontosMapa(true);
      } else {
        desenharSvgMapa();
      }
    } catch (e) {
      const insp = document.getElementById("mapa-inspetor-conteudo");
      if (insp) insp.innerHTML = `<div class="aviso alerta">Erro ao carregar mapa offline: ${escHtml(e.message)}</div>`;
    }
  }

  // Projeção Plate Carrée com correção de cosseno médio para o Brasil (lon: -74.5 a -34.0, lat: 5.8 a -34.2)
  function projetarLatLon(lat, lon) {
    const lonMin = -74.5, lonMax = -34.0;
    const latMax = 5.8, latMin = -34.2;
    const x = ((Number(lon) - lonMin) / (lonMax - lonMin)) * 680 + 60;
    const y = ((latMax - Number(lat)) / (latMax - latMin)) * 500 + 30;
    return [Number(x.toFixed(2)), Number(y.toFixed(2))];
  }

  function enquadrarCaixaLatLon(latMin, lonMin, latMax, lonMax, silencioso) {
    const [x1, y2] = projetarLatLon(latMin, lonMin);
    const [x2, y1] = projetarLatLon(latMax, lonMax);
    const minX = Math.min(x1, x2), maxX = Math.max(x1, x2);
    const minY = Math.min(y1, y2), maxY = Math.max(y1, y2);
    const w = Math.max(8, maxX - minX);
    const h = Math.max(8, maxY - minY);
    const pad = 75;
    const zx = (800 - pad * 2) / w;
    const zy = (560 - pad * 2) / h;
    const z = Math.max(1.0, Math.min(28.0, Math.min(zx, zy)));
    const cx = (minX + maxX) / 2;
    const cy = (minY + maxY) / 2;
    estadoMapa.zoom = Number(z.toFixed(3));
    estadoMapa.panX = Number((400 - cx * estadoMapa.zoom).toFixed(2));
    estadoMapa.panY = Number((280 - cy * estadoMapa.zoom).toFixed(2));
    if (!silencioso) desenharSvgMapa();
  }

  function enquadrarPontosMapa() {
    const grupos = estadoMapa.grupos || [];
    if (!grupos.length) {
      estadoMapa.zoom = 1;
      estadoMapa.panX = 0;
      estadoMapa.panY = 0;
      desenharSvgMapa();
      return;
    }
    if (grupos.length === 1) {
      const g = grupos[0];
      enquadrarCaixaLatLon(g.lat - 0.8, g.lon - 0.8, g.lat + 0.8, g.lon + 0.8, false);
      return;
    }
    let latMin = Infinity, latMax = -Infinity, lonMin = Infinity, lonMax = -Infinity;
    grupos.forEach((g) => {
      if (g.lat < latMin) latMin = g.lat;
      if (g.lat > latMax) latMax = g.lat;
      if (g.lon < lonMin) lonMin = g.lon;
      if (g.lon > lonMax) lonMax = g.lon;
    });
    const dLat = Math.max(0.6, (latMax - latMin) * 0.18);
    const dLon = Math.max(0.6, (lonMax - lonMin) * 0.18);
    enquadrarCaixaLatLon(latMin - dLat, lonMin - dLon, latMax + dLat, lonMax + dLon, false);
  }

  function aplicarZoomCentro(fator, refX, refY) {
    const cx = refX !== undefined ? refX : 400;
    const cy = refY !== undefined ? refY : 280;
    const zAnt = estadoMapa.zoom || 1;
    const zNovo = Math.max(0.85, Math.min(35.0, zAnt * fator));
    estadoMapa.panX = Number((cx - (cx - estadoMapa.panX) * (zNovo / zAnt)).toFixed(2));
    estadoMapa.panY = Number((cy - (cy - estadoMapa.panY) * (zNovo / zAnt)).toFixed(2));
    estadoMapa.zoom = Number(zNovo.toFixed(3));
    desenharSvgMapa();
  }

  function renderizarPainelMapa() {
    const avisoDesat = document.getElementById("mapa-aviso-desatualizado");
    if (avisoDesat) {
      if (estadoMapa.desatualizado) {
        avisoDesat.hidden = false;
        avisoDesat.innerHTML = `<b>Atenção:</b> Dados geográficos derivados estão desatualizados (${escHtml(estadoMapa.motivo_desatualizado || "reindexação pendente")}).`;
      } else {
        avisoDesat.hidden = true;
      }
    }

    const bannerCorr = document.getElementById("mapa-banner-correlacao");
    const cs = estadoMapa.correlacao_selecionada;
    if (bannerCorr) {
      if (cs) {
        bannerCorr.hidden = false;
        bannerCorr.innerHTML = `
          <div>
            <b>Destaque da coincidência:</b> ${escHtml(cs.titulo)} (<code>${escHtml(cs.valor_exibicao)}</code>) —
            <span>${escHtml(cs.mensagem)}</span>
          </div>
          <button type="button" class="btn sm" id="b-mapa-limpar-corr">Limpar destaque</button>
        `;
        const bLimparCorr = document.getElementById("b-mapa-limpar-corr");
        if (bLimparCorr) {
          bLimparCorr.onclick = () => {
            estadoMapa.filtros.correlacao_id = "";
            estadoMapa.enquadrarAoCarregar = true;
            carregarMapa();
          };
        }
      } else {
        bannerCorr.hidden = true;
        bannerCorr.innerHTML = "";
      }
    }

    const r = estadoMapa.resumo || {};
    const kpis = document.getElementById("mapa-kpis");
    if (kpis) {
      kpis.innerHTML = `
        <div class="kpi"><div class="l">Localizados no mapa</div><div class="kv">${r.localizados || 0}</div></div>
        <div class="kpi"><div class="l">PF / PJ no mapa</div><div class="kv">${r.pf_localizados || 0} PF · ${r.pj_localizados || 0} PJ</div></div>
        <div class="kpi"><div class="l">Município aprox.</div><div class="kv">${r.precisao_municipio || 0}</div></div>
        <div class="kpi"><div class="l">Coord. documentada</div><div class="kv">${r.precisao_coordenada || 0}</div></div>
        <div class="kpi ${r.sem_localizacao ? "alerta" : ""}"><div class="l">Sem localização</div><div class="kv">${r.sem_localizacao || 0}</div></div>
      `;
    }

    const metaLic = document.getElementById("mapa-meta-licenca");
    if (metaLic && estadoMapa.cartografia && estadoMapa.cartografia.metadata) {
      const m = estadoMapa.cartografia.metadata;
      const totM = estadoMapa.cartografia.total_municipios_base || 5570;
      metaLic.textContent = `Malha Oficial IBGE (${totM} municípios) · ${m.licenca || "Domínio Público"}`;
    }

    const badgeSemLoc = document.getElementById("mapa-badge-semloc");
    const listaSemLoc = document.getElementById("mapa-lista-semloc");
    const semLoc = estadoMapa.sem_localizacao || [];
    if (badgeSemLoc) badgeSemLoc.textContent = String(semLoc.length);
    if (listaSemLoc) {
      if (!semLoc.length) {
        listaSemLoc.innerHTML = `<div class="muted" style="font-size:12px">Todos os registros filtrados possuem localização resolvida.</div>`;
      } else {
        listaSemLoc.innerHTML = semLoc
          .map((item) => {
            const mot = MOTIVOS_GEO_ROTULO[item.motivo_sem_localizacao] || item.motivo_sem_localizacao || "Não localizado";
            return `
              <div class="card" data-semloc-id="${escHtml(item.id)}" style="padding:8px;margin-bottom:6px;cursor:pointer;background:var(--page);border:1px solid var(--line)">
                <div style="display:flex;justify-content:space-between;gap:4px">
                  <b>${escHtml(item.nome)}</b>
                  <span class="badge">${escHtml(item.tipo_pessoa)} · ${escHtml(item.caso)}</span>
                </div>
                <div class="muted" style="font-size:11.5px;margin-top:2px">
                  ${escHtml(item.papel || "")} · <span style="color:var(--warn)">${escHtml(mot)}</span>
                </div>
                ${item.enderecos_bruto ? `<div class="muted" style="font-size:11px;margin-top:2px">End.: ${escHtml(item.enderecos_bruto)}</div>` : ""}
              </div>
            `;
          })
          .join("");

        listaSemLoc.querySelectorAll("[data-semloc-id]").forEach((el) => {
          el.addEventListener("click", () => {
            const alvo = semLoc.find((x) => x.id === el.dataset.semlocId);
            if (alvo) inspecionarRegistroMapa(alvo);
          });
        });
      }
    }
  }

  function mostrarTooltipMapa(ev, html) {
    const tip = document.getElementById("mapa-tooltip-hud");
    const svg = document.getElementById("svg-mapa-offline");
    if (!tip || !svg) return;
    const rect = svg.getBoundingClientRect();
    let left = ev.clientX - rect.left + 14;
    let top = ev.clientY - rect.top + 14;
    if (left > rect.width - 260) left = Math.max(10, ev.clientX - rect.left - 250);
    if (top > rect.height - 110) top = Math.max(10, ev.clientY - rect.top - 95);
    tip.style.left = `${left}px`;
    tip.style.top = `${top}px`;
    tip.innerHTML = html;
    tip.hidden = false;
  }

  function ocultarTooltipMapa() {
    const tip = document.getElementById("mapa-tooltip-hud");
    if (tip) tip.hidden = true;
  }

  function desenharSvgMapa() {
    const svg = document.getElementById("svg-mapa-offline");
    if (!svg) return;
    const z = Math.max(0.85, Number(estadoMapa.zoom) || 1);
    const invZ = Number((1 / z).toFixed(4));
    const strokeUf = Number((1.1 / Math.pow(z, 0.75)).toFixed(3));
    const lblZoom = document.getElementById("mapa-zoom-label");
    if (lblZoom) lblZoom.textContent = `${z.toFixed(1)}×`;

    const ufs = (estadoMapa.cartografia && estadoMapa.cartografia.ufs) || {};
    const grupos = estadoMapa.grupos || [];
    const pontosPorId = Object.fromEntries((estadoMapa.pontos || []).map((p) => [p.id, p]));

    // Contabilizar registros localizados por UF para destacar estados ativos
    const contagemPorUf = {};
    grupos.forEach((g) => {
      if (g.uf) contagemPorUf[g.uf] = (contagemPorUf[g.uf] || 0) + (g.total || 0);
    });

    // 1) Grade cartográfica sutil (paralelos e meridianos do Brasil)
    let gradeSvg = "";
    [-70, -60, -50, -40].forEach((lon) => {
      const [x] = projetarLatLon(0, lon);
      gradeSvg += `<line x1="${x}" y1="0" x2="${x}" y2="560" stroke="#132642" stroke-width="${(0.6 / z).toFixed(3)}" stroke-dasharray="${(3 / z).toFixed(2)},${(3 / z).toFixed(2)}" />`;
    });
    [0, -10, -20, -30].forEach((lat) => {
      const [, y] = projetarLatLon(lat, -55);
      gradeSvg += `<line x1="0" y1="${y}" x2="800" y2="${y}" stroke="#132642" stroke-width="${(0.6 / z).toFixed(3)}" stroke-dasharray="${(3 / z).toFixed(2)},${(3 / z).toFixed(2)}" />`;
    });

    // 2) Malha vetorial oficial das 27 UFs (IBGE MultiPolygon)
    let ufsSvg = "";
    let siglasUfSvg = "";
    Object.entries(ufs).forEach(([sigla, info]) => {
      const listaPolys = info.poligonos && info.poligonos.length ? info.poligonos : (info.poligono ? [info.poligono] : []);
      if (!listaPolys.length) return;
      const qtdUf = contagemPorUf[sigla] || 0;
      const fillUf = sigla === "SP" ? (qtdUf ? "#16345b" : "#122949") : (qtdUf ? "#132d4e" : "#0b1a2e");
      const strokeCor = qtdUf ? "#325f96" : "#1f3c63";

      const polysHtml = listaPolys
        .map((anel) => {
          const pts = anel.map(([lon, lat]) => projetarLatLon(lat, lon).join(",")).join(" ");
          return `<polygon points="${pts}" fill="${fillUf}" stroke="${strokeCor}" stroke-width="${strokeUf}" stroke-linejoin="round" />`;
        })
        .join("");

      ufsSvg += `<g class="uf-layer" data-uf="${escHtml(sigla)}" data-nome="${escHtml(info.nome || sigla)}" data-qtd="${qtdUf}" style="cursor:pointer;transition:opacity .15s">${polysHtml}</g>`;

      const [cx, cy] = projetarLatLon(info.lat, info.lon);
      const opacidadeSigla = z > 7 ? 0.35 : 0.85;
      siglasUfSvg += `
        <g transform="translate(${cx},${cy}) scale(${invZ})" pointer-events="none" opacity="${opacidadeSigla}">
          <text y="${qtdUf && z < 3.2 ? -3 : 0}" fill="${qtdUf ? "#93c5fd" : "#4b6a8e"}" font-size="9.5" font-weight="700" text-anchor="middle" dominant-baseline="middle" style="text-shadow:0 1px 3px #040911">${escHtml(sigla)}</text>
          ${qtdUf && z < 3.2 ? `<text y="8" fill="#38bdf8" font-size="8" font-weight="600" text-anchor="middle" dominant-baseline="middle">(${qtdUf})</text>` : ""}
        </g>
      `;
    });

    // 3) Arcos táticos conectando cidades quando há correlação destacada ou caso filtrado em múltiplas cidades
    let arcosSvg = "";
    const gruposConexao = grupos.filter((g) => g.destacado_correlacao || estadoMapa.filtros.correlacao_id || estadoMapa.filtros.caso);
    if (gruposConexao.length >= 2 && gruposConexao.length <= 25) {
      // Conectar em estrela a partir do grupo de maior concentração para clareza visual
      const ordenados = gruposConexao.slice().sort((a, b) => b.total - a.total);
      const origem = ordenados[0];
      const [x1, y1] = projetarLatLon(origem.lat, origem.lon);
      for (let i = 1; i < ordenados.length; i++) {
        const dest = ordenados[i];
        const [x2, y2] = projetarLatLon(dest.lat, dest.lon);
        const mx = (x1 + x2) / 2;
        const my = (y1 + y2) / 2;
        const dist = Math.hypot(x2 - x1, y2 - y1);
        const curv = Math.min(45, dist * 0.22);
        const cxArc = mx;
        const cyArc = my - curv;
        arcosSvg += `
          <path d="M ${x1},${y1} Q ${cxArc},${cyArc} ${x2},${y2}"
                fill="none" stroke="#fbbf24" stroke-width="${(1.8 * invZ).toFixed(3)}"
                stroke-dasharray="${(5 * invZ).toFixed(2)},${(4 * invZ).toFixed(2)}"
                opacity="0.78" pointer-events="none" />
        `;
      }
    }

    // 4) Marcadores de pontos e agrupamentos com escala constante na tela (scale(invZ))
    let gruposSvg = "";
    grupos.forEach((g) => {
      const [x, y] = projetarLatLon(g.lat, g.lon);
      const isCluster = g.total > 1;
      const soCoordDoc = (g.precisoes || []).includes("coordenada_documentada") && !(g.precisoes || []).includes("municipio_aproximado");
      const dash = soCoordDoc ? "" : 'stroke-dasharray="3,2"';
      const corBorda = g.destacado_correlacao ? "#FBBF24" : soCoordDoc ? "#FBBF24" : "#bae6fd";

      if (isCluster) {
        const raio = Math.min(20, 11 + Math.ceil(Math.log2(g.total + 1) * 2.4));
        const mostrarCidade = z >= 1.8 || g.total >= 4 || g.destacado_correlacao;
        const corCluster = g.destacado_correlacao ? "#b45309" : "#0369a1";
        const corAnel = g.destacado_correlacao ? "#fbbf24" : "#38bdf8";
        gruposSvg += `
          <g class="mapa-grupo" data-grupo-id="${escHtml(g.id)}" transform="translate(${x},${y}) scale(${invZ})" style="cursor:pointer">
            <circle r="${raio + 5}" fill="${corAnel}" fill-opacity="0.18" stroke="${corBorda}" stroke-width="1.3" ${dash} />
            <circle r="${raio}" fill="${corCluster}" stroke="#e0f2fe" stroke-width="1.8" />
            <text y="0.5" fill="#FFFFFF" font-size="10.5" font-weight="700" text-anchor="middle" dominant-baseline="middle">${g.total}</text>
            ${
              mostrarCidade
                ? `<g transform="translate(0, ${-(raio + 11)})" pointer-events="none">
                     <rect x="${-Math.min(78, (g.municipio || "").length * 3.3 + 8)}" y="-8" width="${Math.min(156, (g.municipio || "").length * 6.6 + 16)}" height="15" rx="4" fill="rgba(6,13,24,0.88)" stroke="#1e3a5f" stroke-width="0.8" />
                     <text y="0.5" fill="#e2e8f0" font-size="9.5" font-weight="600" text-anchor="middle" dominant-baseline="middle">${escHtml((g.municipio || "").slice(0, 22))}</text>
                   </g>`
                : ""
            }
          </g>
        `;
      } else {
        const regId = (g.registros_ids || [])[0];
        const p = pontosPorId[regId];
        if (!p) return;
        const isPj = p.tipo_pessoa === "PJ";
        const corPreench = g.destacado_correlacao ? "#f59e0b" : (isPj ? "#10b981" : "#0ea5e9");
        const rotuloCurto = z >= 2.2 ? (p.nome || "").slice(0, 20) : (g.municipio || p.nome || "").slice(0, 18);
        gruposSvg += `
          <g class="mapa-ponto" data-ponto-id="${escHtml(p.id)}" transform="translate(${x},${y}) scale(${invZ})" style="cursor:pointer">
            <circle r="11.5" fill="${corPreench}" fill-opacity="0.18" stroke="${corBorda}" stroke-width="1.3" ${dash} />
            ${
              isPj
                ? `<rect x="-6" y="-6" width="12" height="12" rx="2.5" transform="rotate(45)" fill="${corPreench}" stroke="#ffffff" stroke-width="1.4" />`
                : `<circle r="6.8" fill="${corPreench}" stroke="#ffffff" stroke-width="1.4" />`
            }
            <g transform="translate(0, -17)" pointer-events="none">
              <rect x="${-Math.min(72, rotuloCurto.length * 3.1 + 7)}" y="-7.5" width="${Math.min(144, rotuloCurto.length * 6.2 + 14)}" height="14" rx="3.5" fill="rgba(6,13,24,0.86)" stroke="#1e3a5f" stroke-width="0.7" />
              <text y="0.5" fill="#f1f5f9" font-size="9" font-weight="600" text-anchor="middle" dominant-baseline="middle">${escHtml(rotuloCurto)}</text>
            </g>
          </g>
        `;
      }
    });

    // 5) Leque visual radial no próprio mapa (Spiderfy) quando um agrupamento está aberto
    let spiderSvg = "";
    if (estadoMapa.grupoAberto) {
      const grp = estadoMapa.grupoAberto;
      const [gx, gy] = projetarLatLon(grp.lat, grp.lon);
      const membros = (grp.registros_ids || []).map((id) => pontosPorId[id]).filter(Boolean);
      const visiveisNoLeque = membros.slice(0, 14);
      const nSat = visiveisNoLeque.length;
      const raioLequePx = Math.max(54, Math.min(96, 38 + nSat * 4.2));

      visiveisNoLeque.forEach((m, idx) => {
        const ang = (idx / nSat) * Math.PI * 2 - Math.PI / 2;
        const sx = Number((Math.cos(ang) * raioLequePx).toFixed(1));
        const sy = Number((Math.sin(ang) * raioLequePx).toFixed(1));
        const isPj = m.tipo_pessoa === "PJ";
        const corSat = isPj ? "#10b981" : "#38bdf8";
        const sel = estadoMapa.selecionado && estadoMapa.selecionado.id === m.id;
        spiderSvg += `
          <g class="mapa-satelite" data-ponto-id="${escHtml(m.id)}" transform="translate(${gx},${gy}) scale(${invZ})" style="cursor:pointer">
            <line x1="0" y1="0" x2="${sx}" y2="${sy}" stroke="#38bdf8" stroke-width="1.3" stroke-dasharray="3,2" opacity="0.85" />
            <g transform="translate(${sx},${sy})">
              <circle r="${sel ? 11 : 8.5}" fill="${corSat}" stroke="${sel ? "#fbbf24" : "#ffffff"}" stroke-width="${sel ? 2.2 : 1.4}" />
              <text y="14" fill="#f8fafc" font-size="8.5" font-weight="600" text-anchor="middle" style="text-shadow:0 1px 3px #000">${escHtml((m.nome || "").slice(0, 14))}</text>
            </g>
          </g>
        `;
      });
    }

    svg.innerHTML = `
      <g id="svg-mapa-viewport" transform="translate(${estadoMapa.panX},${estadoMapa.panY}) scale(${z})">
        ${gradeSvg}
        ${ufsSvg}
        ${siglasUfSvg}
        ${arcosSvg}
        ${gruposSvg}
        ${spiderSvg}
      </g>
    `;

    // Eventos das UFs (hover + clique para enquadrar estado)
    svg.querySelectorAll(".uf-layer").forEach((el) => {
      el.addEventListener("mouseenter", (ev) => {
        const sigla = el.dataset.uf;
        const nome = el.dataset.nome;
        const qtd = Number(el.dataset.qtd || 0);
        mostrarTooltipMapa(
          ev,
          `<div><b>${escHtml(nome)} (${escHtml(sigla)})</b></div>
           <div class="muted">${qtd ? `${qtd} registro(s) localizado(s) neste estado` : "Sem registros filtrados neste estado"} · Duplo clique para focar</div>`
        );
      });
      el.addEventListener("mousemove", (ev) => {
        const tip = document.getElementById("mapa-tooltip-hud");
        if (tip && !tip.hidden) mostrarTooltipMapa(ev, tip.innerHTML);
      });
      el.addEventListener("mouseleave", ocultarTooltipMapa);
      el.addEventListener("dblclick", (ev) => {
        ev.stopPropagation();
        const sigla = el.dataset.uf;
        const info = ufs[sigla];
        if (info && Array.isArray(info.bbox) && info.bbox.length === 4) {
          enquadrarCaixaLatLon(info.bbox[0], info.bbox[1], info.bbox[2], info.bbox[3], false);
        }
      });
    });

    // Eventos dos pontos individuais e satélites do leque
    svg.querySelectorAll(".mapa-ponto, .mapa-satelite").forEach((el) => {
      el.addEventListener("mouseenter", (ev) => {
        const p = pontosPorId[el.dataset.pontoId];
        if (!p) return;
        mostrarTooltipMapa(
          ev,
          `<div><span class="badge">${escHtml(p.tipo_pessoa)}</span> <b>${escHtml(p.nome)}</b></div>
           <div style="color:#93c5fd;margin-top:2px">${escHtml(p.municipio || "")}/${escHtml(p.uf || "")} · <b>${escHtml(p.caso)}</b></div>
           <div class="muted" style="margin-top:2px">Condição: ${escHtml(p.papel || "—")} · Clique para inspecionar</div>`
        );
      });
      el.addEventListener("mouseleave", ocultarTooltipMapa);
      el.addEventListener("click", (ev) => {
        ev.stopPropagation();
        if (!el.classList.contains("mapa-satelite")) fecharFanoutGrupo();
        const p = pontosPorId[el.dataset.pontoId];
        if (p) {
          inspecionarRegistroMapa(p);
          desenharSvgMapa();
        }
      });
    });

    // Eventos dos agrupamentos municipais (clusters)
    svg.querySelectorAll(".mapa-grupo").forEach((el) => {
      el.addEventListener("mouseenter", (ev) => {
        const grp = grupos.find((x) => x.id === el.dataset.grupoId);
        if (!grp) return;
        mostrarTooltipMapa(
          ev,
          `<div><b>${escHtml(grp.municipio || "Agrupamento")}/${escHtml(grp.uf || "")}</b></div>
           <div style="color:#38bdf8;margin-top:2px"><b>${grp.total} registros</b> (${grp.pf} PF · ${grp.pj} PJ)</div>
           <div class="muted" style="margin-top:2px">O.S.: ${escHtml((grp.casos || []).slice(0, 5).join(", "))}${(grp.casos || []).length > 5 ? "…" : ""}</div>
           <div style="color:#fbbf24;font-size:10.5px;margin-top:3px">Clique para abrir o leque de envolvidos</div>`
        );
      });
      el.addEventListener("mouseleave", ocultarTooltipMapa);
      el.addEventListener("click", (ev) => {
        ev.stopPropagation();
        const grp = grupos.find((x) => x.id === el.dataset.grupoId);
        if (grp) abrirFanoutGrupo(grp, pontosPorId);
      });
    });
  }

  function configurarInteracaoSvgMapa() {
    const svg = document.getElementById("svg-mapa-offline");
    if (!svg) return;
    let arrastando = false;
    let iniX = 0, iniY = 0;

    svg.addEventListener("mousedown", (e) => {
      if (e.target.closest(".mapa-ponto, .mapa-grupo, .mapa-satelite")) return;
      arrastando = true;
      iniX = e.clientX;
      iniY = e.clientY;
      svg.style.cursor = "grabbing";
      ocultarTooltipMapa();
    });

    window.addEventListener("mousemove", (e) => {
      if (!arrastando) return;
      const rect = svg.getBoundingClientRect();
      const escX = 800 / (rect.width || 800);
      const escY = 560 / (rect.height || 560);
      const dx = (e.clientX - iniX) * escX;
      const dy = (e.clientY - iniY) * escY;
      iniX = e.clientX;
      iniY = e.clientY;
      estadoMapa.panX = Number((estadoMapa.panX + dx).toFixed(2));
      estadoMapa.panY = Number((estadoMapa.panY + dy).toFixed(2));
      const vp = document.getElementById("svg-mapa-viewport");
      if (vp) vp.setAttribute("transform", `translate(${estadoMapa.panX},${estadoMapa.panY}) scale(${estadoMapa.zoom})`);
    });

    window.addEventListener("mouseup", () => {
      if (!arrastando) return;
      arrastando = false;
      svg.style.cursor = "grab";
    });

    svg.addEventListener("wheel", (e) => {
      e.preventDefault();
      ocultarTooltipMapa();
      const rect = svg.getBoundingClientRect();
      const vx = ((e.clientX - rect.left) / (rect.width || 800)) * 800;
      const vy = ((e.clientY - rect.top) / (rect.height || 560)) * 560;
      const fator = e.deltaY < 0 ? 1.24 : 0.81;
      aplicarZoomCentro(fator, vx, vy);
    }, { passive: false });
  }

  function fecharFanoutGrupo() {
    const box = document.getElementById("mapa-fanout-box");
    if (box) {
      box.hidden = true;
      box.innerHTML = "";
    }
    if (estadoMapa.grupoAberto) {
      estadoMapa.grupoAberto = null;
      desenharSvgMapa();
    }
  }

  function abrirFanoutGrupo(grupo, pontosPorId) {
    estadoMapa.grupoAberto = grupo;
    const box = document.getElementById("mapa-fanout-box");
    if (!box) return;
    const membros = (grupo.registros_ids || []).map((id) => pontosPorId[id]).filter(Boolean);
    box.hidden = false;
    box.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
        <b>${escHtml(grupo.municipio || "Coordenada")}/${escHtml(grupo.uf || "")} (${membros.length})</b>
        <button type="button" class="btn sm" id="b-fecha-fanout">fechar</button>
      </div>
      <div class="muted" style="font-size:11px;margin-bottom:6px">Leque aberto no mapa (${membros.length} registros nesta coordenada municipal). Clique para inspecionar:</div>
      ${membros
        .map(
          (m) => `
        <div data-fanout-membro="${escHtml(m.id)}" style="padding:6px;border-top:1px solid var(--line);cursor:pointer;font-size:12px">
          <div style="display:flex;justify-content:space-between;gap:4px">
            <b>${escHtml(m.nome)}</b>
            <span class="badge">${escHtml(m.tipo_pessoa)}</span>
          </div>
          <div class="muted">${escHtml(m.caso)} · ${escHtml(m.papel || "")}</div>
        </div>
      `
        )
        .join("")}
    `;

    const btnFecha = document.getElementById("b-fecha-fanout");
    if (btnFecha) btnFecha.onclick = fecharFanoutGrupo;

    box.querySelectorAll("[data-fanout-membro]").forEach((el) => {
      el.addEventListener("click", () => {
        const p = pontosPorId[el.dataset.fanoutMembro];
        if (p) {
          inspecionarRegistroMapa(p);
          desenharSvgMapa();
        }
      });
    });

    if (membros[0]) inspecionarRegistroMapa(membros[0]);
    desenharSvgMapa();
  }

  function inspecionarRegistroMapa(item) {
    estadoMapa.selecionado = item;
    const vazio = document.getElementById("mapa-inspetor-vazio");
    const cont = document.getElementById("mapa-inspetor-conteudo");
    if (vazio) vazio.hidden = true;
    if (!cont) return;

    const precisaoBadge =
      item.precisao === "coordenada_documentada"
        ? `<span class="badge st-conf">Coordenada documentada (${escHtml(item.contexto_coordenada || "autos")})</span>`
        : item.precisao === "municipio_aproximado"
        ? `<span class="badge st-ind">Município aproximado (centroide IBGE)</span>`
        : `<span class="badge st-neg">Sem coordenada (${escHtml(MOTIVOS_GEO_ROTULO[item.motivo_sem_localizacao] || item.motivo_sem_localizacao || "")})</span>`;

    const docPrincipal = item.tipo_pessoa === "PJ" ? (item.cnpj ? `CNPJ: ${item.cnpj}` : "CNPJ não consta") : (item.cpf ? `CPF: ${item.cpf}` : "CPF não consta");
    const citFonte = formatarCitacaoFonte(item.fonte);
    const urlFonte = montarUrlFonte(item.caso, item.fonte);

    const enderecosHtml = (item.enderecos || [])
      .map(
        (e) => `
        <div style="padding:6px;background:var(--page);border:1px solid var(--line);border-radius:5px;margin-bottom:4px;font-size:11.5px">
          <div><b>${escHtml(e.texto || "(coordenada direta)")}</b></div>
          <div class="muted">
            Precisão: ${escHtml(e.precisao || "não resolvida")}
            ${e.municipio ? ` · ${escHtml(e.municipio)}/${escHtml(e.uf || "")}` : ""}
            ${e.contexto ? ` · Contexto: ${escHtml(e.contexto)}` : ""}
            ${e.data_ref ? ` · Data ref.: ${escHtml(e.data_ref)}` : ""}
          </div>
        </div>
      `
      )
      .join("");

    const vinculosHtml = (item.vinculos || [])
      .map((v) => `<div style="font-size:12px">• <b>${escHtml(v.tipo)}:</b> ${escHtml(v.nome)} ${v.cnpj ? `(${escHtml(v.cnpj)})` : ""} ${v.cpf ? `(${escHtml(v.cpf)})` : ""}</div>`)
      .join("");

    cont.innerHTML = `
      <div style="border-bottom:1px solid var(--line);padding-bottom:8px;margin-bottom:8px">
        <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin-bottom:4px">
          <span class="badge"><b>${escHtml(item.tipo_pessoa)}</b></span>
          <span class="badge">${escHtml(item.caso)}</span>
          ${precisaoBadge}
        </div>
        <h4 style="margin:4px 0">${escHtml(item.nome)}</h4>
        <div class="muted" style="font-size:12.5px"><b>${escHtml(docPrincipal)}</b> · Condição no caso: <b>${escHtml(item.papel || "—")}</b></div>
        ${item.lat != null && item.lon != null ? `<div class="muted" style="font-size:11.5px;margin-top:2px">Local: ${escHtml(item.municipio || "—")}/${escHtml(item.uf || "—")} (${item.lat}, ${item.lon})</div>` : ""}
      </div>

      <div style="margin-bottom:8px">
        <div style="font-size:12px;font-weight:600;margin-bottom:4px">Endereços e contexto (${(item.enderecos || []).length})</div>
        ${enderecosHtml || `<div class="muted" style="font-size:12px">${escHtml(item.enderecos_bruto || "Nenhum endereço documentado.")}</div>`}
      </div>

      ${vinculosHtml ? `<div style="margin-bottom:8px"><div style="font-size:12px;font-weight:600;margin-bottom:4px">Vínculos PF ↔ PJ na qualificação</div>${vinculosHtml}</div>` : ""}

      <div style="margin-bottom:10px;font-size:12px">
        <b>Fonte documental:</b> ${urlFonte ? `<a class="lk" href="${escHtml(urlFonte)}" target="_blank" rel="noopener">${escHtml(citFonte)}</a>` : escHtml(citFonte)}
      </div>

      <div class="acoes" style="margin:0;display:grid;grid-template-columns:1fr 1fr;gap:6px">
        <button type="button" class="btn sm pri" id="b-insp-qualificacao">1. Qualificação (Pessoas)</button>
        <button type="button" class="btn sm" id="b-insp-caso">2. Abrir Caso (${escHtml(item.caso)})</button>
        <button type="button" class="btn sm" id="b-insp-grafo">3. Ver no Grafo</button>
        ${
          urlFonte
            ? `<a class="btn sm" id="b-insp-fonte" href="${escHtml(urlFonte)}" target="_blank" rel="noopener" style="text-align:center">4. Abrir Fonte</a>`
            : `<button type="button" class="btn sm" id="b-insp-fonte" disabled title="Fonte sem arquivo direto">4. Fonte (${escHtml(citFonte)})</button>`
        }
      </div>
    `;

    const bQual = document.getElementById("b-insp-qualificacao");
    if (bQual) bQual.onclick = () => navegarParaQualificacao(item);

    const bCaso = document.getElementById("b-insp-caso");
    if (bCaso) bCaso.onclick = () => navegarParaCaso(item.caso);

    const bGrafo = document.getElementById("b-insp-grafo");
    if (bGrafo) bGrafo.onclick = () => navegarParaGrafo(item.cpf || item.cnpj || item.nome, item.caso);
  }

  // ---------------------------------------------------------------- Inicialização Geral

  function iniciarInteligenciaMapa() {
    construirContainersDom();

    // Estender os botões segmentados da aba Pesquisa para suportar Correlações e Mapa
    const segBtns = document.querySelectorAll("#pesquisa .seg button");
    segBtns.forEach((b) => {
      b.onclick = () => ativarModoPesquisa(b.dataset.m);
    });

    // Atalhos na barra do Grafo para abrir Radar de Correlações ou Mapa Offline mantendo a O.S. selecionada
    const bGrCorr = document.getElementById("b-gr-correlacoes");
    if (bGrCorr) {
      bGrCorr.onclick = () => {
        const casoSel = (document.getElementById("gr-caso") || {}).value || "";
        estadoCorrelacoes.filtros.caso = casoSel;
        const inp = document.getElementById("corr-f-caso");
        if (inp) inp.value = casoSel;
        if (typeof window.abrirAba === "function") window.abrirAba("pesquisa");
        ativarModoPesquisa("correlacoes");
      };
    }

    const bGrMapa = document.getElementById("b-gr-mapa");
    if (bGrMapa) {
      bGrMapa.onclick = () => {
        const casoSel = (document.getElementById("gr-caso") || {}).value || "";
        estadoMapa.filtros.caso = casoSel;
        const inp = document.getElementById("mapa-f-caso");
        if (inp) inp.value = casoSel;
        if (typeof window.abrirAba === "function") window.abrirAba("pesquisa");
        ativarModoPesquisa("mapa");
      };
    }

    // Injetar atalhos diretos "Correlações" e "Mapa" na barra superior (#nav) ao lado de Pesquisa/Grafo
    function injetarBotoesNavSuperior() {
      const nav = document.getElementById("nav");
      if (!nav || document.getElementById("nav-btn-mapa")) return;
      const btnGrafo = nav.querySelector('button[data-a="grafo"]') || nav.querySelector('button[data-a="pesquisa"]');
      if (!btnGrafo) return;

      const btnCorr = document.createElement("button");
      btnCorr.type = "button";
      btnCorr.id = "nav-btn-correlacoes";
      btnCorr.dataset.a = "correlacoes-atalho";
      btnCorr.textContent = "Correlações";
      btnCorr.onclick = () => {
        if (typeof window.abrirAba === "function") window.abrirAba("pesquisa");
        ativarModoPesquisa("correlacoes");
        nav.querySelectorAll("button").forEach((x) => x.classList.toggle("on", x === btnCorr));
      };

      const btnMapa = document.createElement("button");
      btnMapa.type = "button";
      btnMapa.id = "nav-btn-mapa";
      btnMapa.dataset.a = "mapa-atalho";
      btnMapa.textContent = "Mapa";
      btnMapa.onclick = () => {
        if (typeof window.abrirAba === "function") window.abrirAba("pesquisa");
        ativarModoPesquisa("mapa");
        nav.querySelectorAll("button").forEach((x) => x.classList.toggle("on", x === btnMapa));
      };

      btnGrafo.insertAdjacentElement("afterend", btnCorr);
      btnCorr.insertAdjacentElement("afterend", btnMapa);
    }

    injetarBotoesNavSuperior();
    const navEl = document.getElementById("nav");
    if (navEl && typeof MutationObserver !== "undefined") {
      const obs = new MutationObserver(() => injetarBotoesNavSuperior());
      obs.observe(navEl, { childList: true });
    }
  }

  window.CPJInteligenciaMapa = {
    iniciar: iniciarInteligenciaMapa,
    ativarModoPesquisa,
    carregarCorrelacoes,
    carregarMapa,
    inspecionarRegistroMapa,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", iniciarInteligenciaMapa);
  } else {
    iniciarInteligenciaMapa();
  }
})();
