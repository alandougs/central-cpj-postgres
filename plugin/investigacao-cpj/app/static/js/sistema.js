// ---------------- tarefas e sistema

async function atualizarTarefas(dados){
 const geracao=polling.geracao,login=S.usuario?.login;
 let ts;try{ts=dados||await consultarTarefas()}catch(e){if(geracao===polling.geracao&&login===S.usuario?.login)pollingAviso(e);return null}
 if(geracao!==polling.geracao||login!==S.usuario?.login)return null;
 const run=ts.filter(t=>["executando","na_fila"].includes(t.status));
 const chip=run.length?`tarefas: ${run.length} em andamento · ${run[0].progresso}%`:"tarefas: nenhuma";
 if($("#chip-tarefas").textContent!==chip)$("#chip-tarefas").textContent=chip;
 if($("#sistema").classList.contains("on")){
  const html=ts.length?ts.map(t=>{const r=["executando","na_fila"].includes(t.status);return `<div class="job" data-tarefa="${esc(t.id)}"><div class="l1"><span><b>${esc(t.titulo)}</b> <span class="muted">${esc(t.usuario)}</span></span><span>${badge(t.status)} ${r?`<button class="btn sm dan" data-cancel="${esc(t.id)}">cancelar</button>`:""}</span></div>
   ${r?barraHTML(t.progresso):""}<div class="muted">${r?`${t.progresso}% · `:""}${esc(etapaTarefa(t))}</div>${t.erro?`<div class="muted" style="color:var(--crit)">${esc(t.erro)}</div>`:""}
   ${t.resultado&&t.resultado.url?`<a class="btn sm" href="${esc(t.resultado.url)}">baixar ${esc(t.resultado.arquivo)} (${esc(t.resultado.mb)} MB)</a>`:""}${t.resultado&&!t.resultado.url&&t.status==="concluida"?`<div class="muted">${esc(JSON.stringify(t.resultado).slice(0,300))}</div>`:""}</div>`}).join(""):'<div class="vazio">Nenhuma tarefa nas últimas 24 h</div>';
  if(htmlAtualizado($("#lista-tarefas"),html))$$("#lista-tarefas [data-cancel]").forEach(b=>b.onclick=async()=>{
   try{const r=await api(`/api/tarefas/${enc(b.dataset.cancel)}/cancelar`,{method:"POST"});if(!r.ok)throw new Error("Cancelamento não confirmado pelo servidor");await acordarPolling()}catch(e){toast(e.message)}
  });
 }
 ts.forEach(t=>{if(t.status==="concluida")atualizarTarefas.vistos.add(t.id)});return ts;
}

atualizarTarefas.vistos=new Set();

$("#chip-tarefas").onclick=()=>abrirAba("sistema");

async function carregarAuditoria(){const destino=$("#lista-aud");destino.innerHTML="";
 const aviso=texto=>{const p=document.createElement("p");p.setAttribute("role","alert");p.textContent=texto;destino.append(p)};
 try{const ai=await api("/api/auditoria/integridade");if(!ai.integra)aviso("INTEGRIDADE DA AUDITORIA COMPROMETIDA. Preserve o log e a âncora para conferência.")}catch(x){aviso("Não foi possível verificar a integridade da auditoria: "+x.message)}
 try{const au=await api("/api/auditoria");destino.insertAdjacentHTML("beforeend",`<table><tbody>${au.map(a=>`<tr><td class="muted">${esc(a.ts.replace("T"," "))}</td><td>${esc(a.usuario)}</td><td>${esc(a.acao)}</td><td>${esc(a.alvo)}</td><td class="muted">${esc(a.ip)}</td></tr>`).join("")}</tbody></table>`)}catch(x){aviso("Leitura dos registros indisponível: "+x.message)}}

async function carregarSistema(leve){atualizarTarefas();preencherConta();carregarLLM();carregarConfigIA();

 const mp=await api("/api/minha-pasta");$("#minha-pasta").innerHTML=mp.arquivos.map(a=>`<div><a href="/minha-pasta/${a.caminho.split("/").map(enc).join("/")}">${esc(a.caminho)}</a><span class="muted">${kb(a.tamanho)}</span></div>`).join("")||`<span class="muted">Vazia${mp.pasta?" — "+esc(mp.pasta):""}</span>`;

 $("#b-abrir-pasta").hidden=!mp.pasta;

 if(pode("usuarios")&&!leve){carregarPerfis();const cfg=await api("/api/os/ia-local");$("#os-modelo-local").value=cfg.modelo;$("#os-modelo-local").disabled=cfg.ambiente;$("#b-os-modelo").disabled=cfg.ambiente;$("#os-modelo-msg").textContent=cfg.ambiente?"Modelo definido pelo ambiente":"";}

 if(pode("dados")){const ex=await api("/api/exportacoes");$("#lista-exp").innerHTML=ex.map(e=>`<div><a href="${esc(e.url)}">${esc(e.arquivo)}</a><span class="muted">${e.mb} MB${e.arquivo.toLowerCase().endsWith('.zip')?' · ZIP legado — sem criptografia':' · criptografado'}</span></div>`).join("")||'<span class="muted">—</span>';

  const resumoAnt=b=>{const a=b.com_antecedentes||{};const est=x=>x&&typeof x==="object"?Object.entries(x).filter(([,n])=>n).map(([e,n])=>`${n} ${e}`).join(", "):"";

   const p=[a.processos?`${a.processos} c/ processos`:"",a.bos?`${a.bos} c/ BO`:"",est(a.mandados)?`mandados: ${est(a.mandados)}`:"",est(a.cautelares)?`cautelares: ${est(a.cautelares)}`:""].filter(Boolean);return p.length?" · "+p.join(" · "):""};

  const bs=await api("/api/consulta/bases");$("#lista-bc").innerHTML=bs.length?`<table><tbody>${bs.map(b=>`<tr><td><b>${esc(b.nome)}</b><div class="muted">${esc(b.arquivo_original)} · ${dt(b.importado_em)}${Object.keys(b.mapeamento||{}).length?" · colunas: "+esc(Object.entries(b.mapeamento).map(([k,v])=>k+"→"+v).join(", ")):""}${esc(resumoAnt(b))}</div></td><td class="n">${b.registros}</td><td><button class="btn sm dan" data-rmbc="${esc(b.id)}">remover</button></td></tr>`).join("")}</tbody></table>`:'<span class="muted">Nenhuma base.</span>';

  $$("[data-rmbc]").forEach(b=>b.onclick=async()=>{if(confirm("Remover esta base de consulta?")){await api(`/api/consulta/bases/${enc(b.dataset.rmbc)}/remover`,{method:"POST"});carregarSistema()}});

  await listarRefs()}

 if(pode("ia")&&!leve){checarClaude();carregarAgentes()}

 if(pode("usuarios")&&!leve){const us=await api("/api/usuarios");$("#lista-usuarios").innerHTML=`<div style="overflow:auto"><table><thead><tr><th>Login</th><th>Nome / cargo</th><th>Perfil</th><th>CPF</th><th>E-mail</th><th>Situação</th><th>Último acesso</th><th></th></tr></thead><tbody>${us.map(u=>`<tr><td>${esc(u.login)}</td><td>${esc(u.nome)}<div class="muted">${esc(u.cargo||"")}</div></td><td>${esc(u.perfil_nome)}</td><td class="muted">${esc(u.cpf_mascarado||"—")}</td><td class="muted">${esc(u.email||"—")}</td>

  <td>${u.ativo?"ativo":"desativado"}${u.trocar_senha?' <span class="badge b-wait"><i aria-hidden="true"></i>senha temporária</span>':""}</td><td class="muted">${esc((u.ultimo_acesso||"").replace("T"," "))}</td><td><button class="btn sm" data-edu='${esc(JSON.stringify(u))}'>editar</button> <button class="btn sm dan" data-rmu="${esc(u.login)}">remover</button></td></tr>`).join("")}</tbody></table></div>`;

  $$("[data-edu]").forEach(b=>b.onclick=()=>{const u=JSON.parse(b.dataset.edu),f=$("#f-usuario");f.reset();f.login.value=u.login;f.login.readOnly=true;f.nome.value=u.nome;f.perfil.value=u.perfil;f.ativo.value=u.ativo?"1":"0";selecionarCargo(f,u.cargo);f.email.value=u.email||"";f.cpf.placeholder=u.cpf_mascarado||"";f.senha.value="";f.nome.focus()});

  $$("[data-rmu]").forEach(b=>b.onclick=async()=>{if(!confirm(`Remover o usuário ${b.dataset.rmu}?`))return;try{await api(`/api/usuarios/${enc(b.dataset.rmu)}/remover`,{method:"POST"});carregarSistema()}catch(x){toast(x.message)}});

   await carregarAuditoria();

   const rd=await api("/api/rede");$("#rede-on").checked=rd.compartilhar;$("#rede-https").checked=rd.https;

   $("#rede-info").innerHTML=rd.ativo_agora?`Compartilhamento <b>ativo</b>. Endereços para os outros computadores: ${rd.enderecos.map(e=>`<code>${esc(e)}</code>`).join(" ")}`:"Compartilhamento desligado: a Central atende somente este computador."}

  if(S.solo){const u=$("#card-usuarios"),p=$("#card-perfis"),r=$("#card-rede");if(u)u.hidden=true;if(p)p.hidden=true;if(r)r.hidden=true}}

async function listarRefs(){const rs=await api("/api/referencias?autor="+enc($("#rf-filtro").value||""));

 $("#lista-rf").innerHTML=rs.length?`<table><thead><tr><th>Autor</th><th>Modalidade</th><th>Peso</th><th>Arquivo</th><th></th></tr></thead><tbody>${rs.map(r=>`<tr><td>${esc(r.autor)}</td><td>${esc(r.modalidade||"—")}</td>

 <td><select data-peso="${esc(r.id)}" style="width:auto">${[5,4,3,2,1].map(p=>`<option ${p==r.peso?"selected":""}>${p}</option>`).join("")}</select></td><td class="muted">${esc(r.arquivo_original)}</td><td><button class="btn sm dan" data-rmrf="${esc(r.id)}">remover</button></td></tr>`).join("")}</tbody></table>`:'<span class="muted">Nenhuma referência.</span>';

 $$("[data-peso]").forEach(s=>s.onchange=async()=>{await api(`/api/referencias/${enc(s.dataset.peso)}`,{json:{peso:+s.value}});toast("Peso atualizado")});

 $$("[data-rmrf]").forEach(b=>b.onclick=async()=>{if(confirm("Remover esta referência?")){await api(`/api/referencias/${enc(b.dataset.rmrf)}/remover`,{method:"POST"});listarRefs()}})}

$("#rf-filtro").oninput=()=>{clearTimeout(tq);tq=setTimeout(listarRefs,300)};

$("#b-exportar").onclick=async()=>{const modo=document.querySelector('input[name=modo]:checked').value,senha=$("#exp-senha").value;if(senha.length<12||senha.length>1024){toast("Informe uma senha de 12 a 1024 caracteres");return}$("#exp-senha").value="";try{await api("/api/exportar",{json:{modo,incluir_modelo:$("#exp-modelo").checked,senha}});toast("Exportação criptografada iniciada — acompanhe em Tarefas");atualizarTarefas()}catch(x){toast(x.message)}};

$("#b-importar").onclick=async()=>{const f=$("#imp-zip").files[0];if(!f){toast("Escolha o pacote .cpjenc ou .zip legado");return}const legado=f.name.toLowerCase().endsWith(".zip"),senha=$("#imp-senha").value;if(legado&&!confirm("Este ZIP legado está sem criptografia e pode expor dados sigilosos. Confirma que a origem é autorizada e deseja importar?"))return;if(!legado&&(senha.length<12||senha.length>1024)){toast("Informe a senha de 12 a 1024 caracteres do pacote");return}const fd=new FormData();fd.append("arquivo",f);if(legado)fd.append("permitir_legado","true");else fd.append("senha",senha);$("#imp-senha").value="";

 try{await enviar("/api/importar",fd,$("#prog-imp"),$("#msg-imp"));$("#msg-imp").textContent="Enviado — verificação e importação em Tarefas";$("#imp-zip").value=""}catch(x){$("#msg-imp").textContent=x.message}};

$("#b-bc").onclick=async()=>{const f=$("#bc-arq").files[0];if(!f){toast("Escolha o arquivo");return}const fd=new FormData();fd.append("arquivo",f);fd.append("nome",$("#bc-nome").value);

 try{await enviar("/api/consulta/importar",fd,$("#prog-bc"),$("#msg-bc"));$("#msg-bc").textContent="Enviado — importação em Tarefas";$("#bc-arq").value="";$("#bc-nome").value=""}catch(x){$("#msg-bc").textContent=x.message}};

$("#b-bc-colar").onclick=async()=>{const t=$("#bc-texto").value.trim();if(!t){toast("Cole o texto");return}

 try{await api("/api/consulta/colar",{json:{texto:t,nome:$("#bc-nome").value||"Texto colado"}});$("#msg-bc-colar").textContent="Enviado — importação em Tarefas";$("#bc-texto").value="";atualizarTarefas()}catch(x){$("#msg-bc-colar").textContent=x.message}};

$("#b-rf").onclick=async()=>{const f=$("#rf-arq").files[0];if(!f||!$("#rf-autor").value.trim()){toast("Informe autor e arquivo");return}const fd=new FormData();fd.append("arquivo",f);

 fd.append("autor",$("#rf-autor").value);fd.append("modalidade",$("#rf-mod").value);fd.append("peso",$("#rf-peso").value);fd.append("obs",$("#rf-obs").value);

 try{await enviar("/api/referencias/importar",fd,$("#prog-rf"),$("#msg-rf"));$("#msg-rf").textContent="Enviado — importação em Tarefas";$("#rf-arq").value=""}catch(x){$("#msg-rf").textContent=x.message}};

const EST_AG={"ocioso":["b-ok","ocioso"],"ocupado":["b-run","ocupado"],"indisponível":["b-wait","indisponível"],"aguardando aprovação":["b-wait","aguardando aprovação"],"fora do ar":["","fora do ar"]};

const tempoSinal=s=>s==null?"—":s<90?`${s}s`:s<5400?`${Math.round(s/60)} min`:`${Math.round(s/3600)} h`;

async function carregarAgentes(estrito=false){if(!pode("ia"))return null;let g;try{g=await lerAtualizacao("/api/plantao/agentes");polling.erroAgentes=false}catch(x){polling.erroAgentes=true;pollingAviso(x);if(estrito)throw x;return null}

 if($("#plantao-agentes")){

  $("#plantao-resumo").textContent=`${g.ociosos} ocioso(s) · ${g.ocupados} ocupado(s) · ${g.pendentes} pedido(s) aguardando agente`;

  $("#plantao-agentes").innerHTML=g.agentes.length?`<table><thead><tr><th>Agente</th><th>Tipo</th><th>Situação</th><th>Pedido atual</th><th>Último sinal</th><th></th></tr></thead><tbody>${g.agentes.map(a=>{const e=EST_AG[a.estado]||["",a.estado];

   return `<tr><td><b>${esc(a.nome)}</b><div class="muted">${esc(a.host||"")}</div></td><td>${esc(a.tipo)}<div class="muted">${a.modo==="chat"?"sessão de chat":"automático"}</div></td>

   <td><span class="badge ${e[0]}"><i aria-hidden="true"></i>${esc(e[1])}</span>${a.detalhe?`<div class="muted">${esc(a.detalhe)}</div>`:""}</td><td class="muted">${esc(a.job||"—")}</td><td class="muted">${tempoSinal(a.silencio_s)}</td>

   <td>${S.solo ? "" : (pode("usuarios")?(a.aprovado?`<button class="btn sm dan" data-agrev="${esc(a.nome)}">revogar</button>`:`<button class="btn sm pri" data-agapr="${esc(a.nome)}">aprovar</button>`):(a.aprovado?"aprovado":"aguarda o admin"))}</td></tr>`}).join("")}</tbody></table>`

   :'<div class="vazio">Nenhum agente registrado. Abra uma sessão com o PROMPT-AGENTE-PLANTAO.md ou rode ferramentas\\Agente de plantao.bat.</div>';

  const muda=async(nome,aprovar)=>{if(!aprovar&&!confirm(`Revogar o agente ${nome}? Ele deixará de pegar pedidos.`))return;

   try{await api(`/api/plantao/agentes/${enc(nome)}/aprovacao`,{json:{aprovar}});toast(aprovar?"Agente aprovado":"Aprovação revogada");carregarAgentes()}catch(x){toast(x.message)}};

  if(!S.solo){

   $$("[data-agapr]").forEach(b=>b.onclick=()=>{if(confirm(`Aprovar o agente ${b.dataset.agapr}? Ele poderá processar autos. Confirme que a conta e o provedor dele são compatíveis com o sigilo.`))muda(b.dataset.agapr,true)});

   $$("[data-agrev]").forEach(b=>b.onclick=()=>muda(b.dataset.agrev,false))}}

 return g}

async function checarClaude(){$("#ia-status").textContent="verificando…";try{const s=await api("/api/ia/status");$("#ia-status").innerHTML=!s.instalado?"Claude Code não encontrado neste computador.":s.logado?`${badge("concluido")} Claude conectado${s.email?" ("+esc(s.email)+")":""}.`:`${badge("erro")} Claude <b>não conectado</b>: clique em “Entrar no Claude” e conclua o login no navegador.`}catch(x){$("#ia-status").textContent=x.message}}

$("#b-abrir-pasta").onclick=()=>api("/api/minha-pasta/abrir",{method:"POST"}).catch(x=>toast(x.message));

let PADRAO=null;

async function carregarPerfis(){const p=await api("/api/perfis");if(!PADRAO)PADRAO=null;const ps=Object.keys(p.matriz);

 $("#matriz").innerHTML=`<table><thead><tr><th>Permissão</th><th class="n">Administrador</th>${ps.map(x=>`<th class="n">${esc(p.perfis[x])}</th>`).join("")}</tr></thead><tbody>${p.editaveis.map(perm=>`<tr><td>${esc(p.descricao[perm]||perm)}</td><td class="n">✔</td>${ps.map(x=>`<td class="n"><input type="checkbox" style="width:auto" data-pf="${x}" data-pm="${perm}" ${p.matriz[x].includes(perm)?"checked":""}></td>`).join("")}</tr>`).join("")}</tbody></table>`}

$("#b-perfis").onclick=async()=>{const m={};$$("[data-pf]").forEach(c=>{m[c.dataset.pf]=m[c.dataset.pf]||[];if(c.checked)m[c.dataset.pf].push(c.dataset.pm)});

 try{await api("/api/perfis",{json:{matriz:m}});$("#msg-perfis").textContent="Permissões salvas (valem no próximo acesso de cada usuário)"}catch(x){$("#msg-perfis").textContent=x.message}};

$("#b-perfis-padrao").onclick=async()=>{if(!confirm("Restaurar as permissões padrão?"))return;const pad={investigador:["os","casos","trabalho","ia","pesquisa","estatisticas","dados","relatorio_final"],delegado:["os","casos","pesquisa","estatisticas","relatorio_final"],escrivao:["os","casos","relatorio_final"]};

 await api("/api/perfis",{json:{matriz:pad}});carregarPerfis();$("#msg-perfis").textContent="Padrão restaurado"};

$("#b-os-modelo").onclick=async()=>{try{await api("/api/os/ia-local",{json:{modelo:$("#os-modelo-local").value.trim()}});$("#os-modelo-msg").textContent="Salvo. Vale para os próximos documentos ou ao reprocessar um caso."}catch(x){$("#os-modelo-msg").textContent=x.message}};

$("#b-claude-login").onclick=async()=>{try{await api("/api/ia/login",{method:"POST"});toast("Janela de login aberta neste computador")}catch(x){toast(x.message)}};$("#b-claude-rec").onclick=checarClaude;

$("#f-usuario").onsubmit=async e=>{e.preventDefault();const f=e.target;

 // CPF só é enviado quando preenchido (em branco = manter o atual); e-mail e cargo sempre refletem o formulário

 const d={login:f.login.value,nome:f.nome.value,perfil:f.perfil.value,senha:f.senha.value,ativo:f.ativo.value==="1",cargo:valorCargo(f),email:f.email.value,temporaria:f.temporaria.checked};

 if(f.cpf.value.trim())d.cpf=f.cpf.value.trim();

 if(d.temporaria&&!d.senha){$("#msg-usr").textContent="Informe a senha provisória.";return}

 try{await api("/api/usuarios",{json:d});$("#msg-usr").textContent="Salvo";f.reset();f.login.readOnly=false;f.cpf.placeholder="";carregarSistema()}catch(x){$("#msg-usr").textContent=x.message}};

$("#b-usr-novo").onclick=()=>{const f=$("#f-usuario");f.reset();f.login.readOnly=false;f.cpf.placeholder="";$("#msg-usr").textContent="";f.login.focus()};

function preencherConta(){const u=S.usuario;if(!u)return;$("#conta-info").textContent=`${u.nome} · ${u.cargo||u.perfil_nome} · login ${u.login}${u.cpf_mascarado?" · CPF "+u.cpf_mascarado:""}`;

 const f=$("#f-conta");f.email.value=u.email||"";selecionarCargo(f,u.cargo)}

$("#f-conta").onsubmit=async e=>{e.preventDefault();const f=e.target;try{const u=await api("/api/minha-conta",{json:{email:f.email.value,cargo:valorCargo(f)}});S.usuario=Object.assign(S.usuario,u);preencherConta();$("#msg-conta").textContent="Dados salvos"}catch(x){$("#msg-conta").textContent=x.message}};

$("#b-rede").onclick=async()=>{try{await api("/api/rede",{json:{compartilhar:$("#rede-on").checked,https:$("#rede-https").checked}});$("#msg-rede").textContent="Salvo. Feche e abra a Central para aplicar."}catch(x){$("#msg-rede").textContent=x.message}};

$("#f-senha").onsubmit=async e=>{e.preventDefault();const f=e.target;try{await api("/api/minha-senha",{json:{atual:f.atual.value,nova:f.nova.value}});$("#msg-senha").textContent="Senha alterada";f.reset()}catch(x){$("#msg-senha").textContent=x.message}};

