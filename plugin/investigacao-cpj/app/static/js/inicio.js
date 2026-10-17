// ---------------- início

async function carregarInicio(){const p=await api("/api/pendencias");

 $("#ini-sub").textContent=`${S.usuario.nome} — ${new Date().toLocaleDateString("pt-BR",{weekday:"long",day:"numeric",month:"long"})}`;

 const k=(l,v,cls,f)=>`<div class="kpi ${cls||""} ${f?"clic":""}" ${f?`data-f="${f}"`:""}><div class="l">${l}</div><div class="kv">${v}</div></div>`;

 const aberto=Object.values(p.em_andamento).reduce((a,b)=>a+b,0);

 $("#ini-kpis").innerHTML=(pode("trabalho")?k("O.S. novas",p.novas.length,p.novas.length?"atencao":""):"")+k("Prazos vencidos",p.vencidos.length,p.vencidos.length?"alerta":"","vencido")+k("Vencem hoje",p.hoje.length,p.hoje.length?"atencao":"","hoje")+

  k("Próximos 3 dias",p.proximos.length,"","proximo")+k("Em aberto",aberto)+k("Entregues hoje",p.entregues_hoje)+k("Entregues no mês",p.entregues_mes);

 $$("#ini-kpis .kpi.clic").forEach(e=>e.onclick=()=>{abrirAba("casos");$("#pz-casos").value=e.dataset.f;carregarCasos()});

 const lista=(t,arr,vazio)=>`<div class="card"><h4>${t}</h4><div class="lista-os">${arr.length?arr.slice(0,12).map(c=>`<div class="it" data-id="${esc(c.id)}"><span><b>${esc(c.ordem_servico||c.id)}</b> <span class="muted">${esc(c.bo||c.inquerito||"")}</span></span>${prazoBadge(c)}</div>`).join(""):`<div class="vazio">${vazio}</div>`}</div></div>`;

 let h="";if(pode("trabalho"))h+=lista("O.S. novas (não vistas)",p.novas,"Nenhuma O.S. nova");

 h+=lista("Prazos críticos",[...p.vencidos,...p.hoje,...p.proximos],"Nenhum prazo crítico");

 h+=pode("trabalho")?`<div class="card"><h4>Andamento</h4><table><tbody>${Object.entries(p.em_andamento).map(([s,n])=>`<tr><td>${s}</td><td class="n">${n}</td></tr>`).join("")}</tbody></table></div>`:lista("Minhas O.S.",p.minhas,"Você ainda não cadastrou O.S.");

 $("#ini-listas").innerHTML=h;$$("#ini-listas .it").forEach(e=>e.onclick=()=>{abrirAba("casos");abrirCaso(e.dataset.id,true)});

 if(pode("trabalho")){$("#n-inicio").hidden=!(p.novas.length+p.vencidos.length+p.hoje.length);$("#n-inicio").textContent=p.novas.length+p.vencidos.length+p.hoje.length}

 $("#ini-proc").innerHTML=p.processando.length?p.processando.map(c=>`<div class="job"><div class="l1"><b>${esc(c.ordem_servico||c.id)}</b><span class="muted">${c.progresso_proc??0}%</span></div>${barraHTML(c.progresso_proc)}</div>`).join(""):'<div class="vazio">Nada em processamento</div>';window.FilaUnificada?.atualizarPainel().catch(pollingAviso)}



