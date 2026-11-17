// ---------------- sessão

function formatarCpf(valor){const d=String(valor||"").replace(/\D/g,"").slice(0,11);return d.slice(0,3)+(d.length>3?"."+d.slice(3,6):"")+(d.length>6?"."+d.slice(6,9):"")+(d.length>9?"-"+d.slice(9):"")}
$$('[data-cpf-format]').forEach(campo=>campo.oninput=()=>{
 const digitos=campo.value.slice(0,campo.selectionStart).replace(/\D/g,"").length;campo.value=formatarCpf(campo.value);
 let pos=0,n=0;while(pos<campo.value.length&&n<digitos){if(/\d/.test(campo.value[pos]))n++;pos++}campo.setSelectionRange(pos,pos);
});
function atualizarCargo(form){const outro=form.querySelector('[data-cargo-outro]'),ativo=form.querySelector('[data-cargo-select]').value==="outro";outro.hidden=!ativo;outro.disabled=!ativo;outro.required=ativo}
function valorCargo(form){const select=form.querySelector('[data-cargo-select]');return select.value==="outro"?form.querySelector('[data-cargo-outro]').value.trim():select.value}
function selecionarCargo(form,valor){const select=form.querySelector('[data-cargo-select]'),v=String(valor||"").trim();select.value=[...select.options].some(o=>o.value===v&&o.value!=="outro")?v:v?"outro":"";form.querySelector('[data-cargo-outro]').value=select.value==="outro"?v:"";atualizarCargo(form)}
$$('[data-cargo-select]').forEach(select=>{select.onchange=()=>atualizarCargo(select.form);select.form.addEventListener('reset',()=>queueMicrotask(()=>atualizarCargo(select.form)));atualizarCargo(select.form)});

async function iniciar(){reiniciarPolling(true);atualizarTarefas.vistos.clear();carregarPendencias.assinatura=null;const s=await api("/api/sessao");S={usuario:s.usuario,perms:s.permissoes,solo:!!s.solo};

 $("#tela-login").hidden=!!s.usuario;$("#tela-setup").hidden=s.configurado||s.usuario||!s.local;$("#b-ir-setup").hidden=s.configurado||!s.local;$("#app").hidden=!s.usuario;

 if(!s.configurado&&!s.local){$("#tela-setup").innerHTML='<div class="card"><h1>Central CPJ</h1><p>A configuração inicial deve ser feita no computador onde a Central está instalada.</p></div>'}

 $("#tela-trocar").hidden=true;

 if(s.usuario&&s.usuario.trocar_senha){mostrarTrocar();return}

 if(s.usuario)montar()}

$("#f-trocar").onsubmit=async e=>{e.preventDefault();const f=e.target;if(f.nova.value!==f.nova2.value){$("#msg-trocar").textContent="As senhas não conferem.";return}

 try{await api("/api/minha-senha",{json:{atual:f.atual.value,nova:f.nova.value}});f.reset();iniciar()}catch(x){$("#msg-trocar").textContent=x.message}};

$("#b-sair2").onclick=async()=>{if(!confirmarSaidaEditor())return;reiniciarPolling(true);await api("/api/sair",{method:"POST"});iniciar()};

$("#f-login").onsubmit=async e=>{e.preventDefault();const f=e.target;try{await api("/api/entrar",{json:{login:f.login.value,senha:f.senha.value}});f.senha.value="";iniciar()}catch(x){$("#msg-login").textContent=x.message}};

$("#b-ir-setup").onclick=()=>{$("#tela-login").hidden=true;$("#tela-setup").hidden=false;$("#msg-login").textContent=""};

$("#b-voltar-login").onclick=()=>{$("#tela-setup").hidden=true;$("#tela-login").hidden=false;$("#msg-setup").textContent=""};

$("#f-setup").onsubmit=async e=>{e.preventDefault();const f=e.target;if(f.senha.value!==f.senha2.value){$("#msg-setup").textContent="As senhas não conferem.";return}

 try{await api("/api/configurar",{json:{nome:f.nome.value,login:f.login.value,senha:f.senha.value,cargo:valorCargo(f),cpf:f.cpf.value,email:f.email.value}});iniciar()}catch(x){$("#msg-setup").textContent=x.message}};

$("#b-sair").onclick=async()=>{if(!confirmarSaidaEditor())return;reiniciarPolling(true);await api("/api/sair",{method:"POST"});location.hash="";iniciar()};



const ABAS=[["inicio","Início","casos"],["nova","Nova O.S.","os"],["pendencias","Pendentes","trabalho"],["casos","Casos","casos"],["fluxograma","Fluxograma","casos"],["pesquisa","Pesquisa","pesquisa"],["grafo","Grafo","pesquisa"],["mapa","Mapa","pesquisa"],["estatisticas","Estatísticas","estatisticas"],["sistema","Sistema",null]];

const MOD=["","falso-parente","whatsapp-clonado","falsa-central","boleto-falso","falso-vendedor","falso-intermediario","falso-investimento","falso-emprego","emprestimo-falso","golpe-afetivo","falso-sequestro","maquininha","fraude-cartao","fraude-documental","outro"];

const ST=["recebido","extraido","em_analise","analisado","minuta","entregue","devolvido","arquivado"];

function montar(){$("#u-nome").textContent=S.usuario.cargo?`${S.usuario.nome} · ${S.usuario.cargo}`:`${S.usuario.nome} · ${S.usuario.perfil_nome}`;

 $("#b-sair").hidden=!!S.solo;

 if(S.solo){const u=$("#card-usuarios"),p=$("#card-perfis"),r=$("#card-rede");if(u)u.hidden=true;if(p)p.hidden=true;if(r)r.hidden=true}

 $("#nav").innerHTML=ABAS.filter(a=>!a[2]||pode(a[2])).map(a=>`<button data-a="${a[0]}"${a[0]==="mapa"?' id="nav-btn-mapa"':''}>${a[1]}<span class="n" id="n-${a[0]}" hidden></span></button>`).join("");

 $$("#nav button").forEach(b=>b.onclick=()=>abrirAba(b.dataset.a));

 $$("[data-perm]").forEach(e=>e.hidden=!pode(e.dataset.perm));

 if(S.solo){const u=$("#card-usuarios"),p=$("#card-perfis"),r=$("#card-rede");if(u)u.hidden=true;if(p)p.hidden=true;if(r)r.hidden=true}

 $("#st-casos").innerHTML='<option value="">todos os status</option>'+ST.map(s=>`<option>${s}</option>`).join("");

 $("#rf-mod").innerHTML=MOD.map(m=>`<option value="${m}">${m||"—"}</option>`).join("");

 $("#f-os").recebido.value=hoje();if(S.usuario.perfil==="delegado")$("#f-os").requisitante.value=S.usuario.nome;

 const hash=location.hash.slice(1),ini=hash==="mapa-atalho"?"mapa":hash;abrirAba(ABAS.some(a=>a[0]===ini&&(!a[2]||pode(a[2])))?ini:(pode("casos")?"inicio":"nova"));ciclo()}

function abrirAba(a){if(a==="mapa-atalho")a="mapa";if(!confirmarSaidaEditor()){history.replaceState(null,"","#"+($("section.aba.on")?.id||"inicio"));return}$$("#nav button").forEach(x=>{const ativa=x.dataset.a===a;x.classList.toggle("on",ativa);if(ativa)x.setAttribute("aria-current","page");else x.removeAttribute("aria-current")});$$("section.aba").forEach(s=>s.classList.toggle("on",s.id===a));history.replaceState(null,"","#"+a);

 if(a==="inicio")carregarInicio();if(a==="casos")carregarCasos();if(a==="pendencias")carregarPendencias().catch(pollingAviso);if(a==="fluxograma")carregarAbaFluxograma();if(a==="nova")atualizarFila().catch(pollingAviso);if(a==="grafo")carregarGrafo();if(a==="mapa"&&window.CPJInteligenciaMapa)window.CPJInteligenciaMapa.carregarMapa();if(a==="estatisticas")$("#if-painel").src="/painel?t="+Date.now();if(a==="sistema")carregarSistema();if(typeof acordarPolling==="function")acordarPolling()}

