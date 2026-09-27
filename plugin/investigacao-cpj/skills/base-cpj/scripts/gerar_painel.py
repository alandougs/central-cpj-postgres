#!/usr/bin/env python3
"""Gera producao\\painel.html (arquivo local, autocontido, sem internet) a partir de producao\\base.json.
Uso: gerar_painel.py   (rode indexar.py antes para atualizar a base)
Não exibe nomes de pessoas: só ID do caso, ordem de serviço, modalidade e números agregados.
"""
import datetime, json, os, sys

WS = os.environ.get("CPJ_WORKSPACE", r"C:\CPJ - TRABALHO")
PROD = os.path.join(WS, "producao")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def ws_dados():
    """Pasta com casos\\ e config\\ para as métricas de qualidade. A Central gera o painel numa pasta de preparo
    (producao\\.painel-*) que só tem base.json; nesse caso os dados ficam dois níveis acima.
    CPJ_WORKSPACE_DADOS, se definido, tem precedência."""
    cand = [os.environ.get("CPJ_WORKSPACE_DADOS"), WS]
    if os.path.basename(WS).startswith(".painel-") and os.path.basename(os.path.dirname(WS)) == "producao":
        cand.append(os.path.dirname(os.path.dirname(WS)))
    return next((c for c in cand if c and os.path.isdir(os.path.join(c, "casos"))), None)


def qualidade():
    """Métricas de qualidade anônimas (sem id, nomes, solicitante ou agente). None se indisponíveis."""
    try:
        import metricas as MQ
        wd = ws_dados()
        if not wd: return None
        m = MQ.calcular(wd)
    except Exception:
        return None
    return {"casos": [{k: c[k] for k in ("recebido", "entregue", "versoes", "revisao", "etapas", "datas_etapas")}
                      for c in m["casos"]],
            "ia": [{k: p[k] for k in ("acao", "estado", "criado", "espera_min", "execucao_min")} for p in m["ia"]]}



base = json.load(open(os.path.join(PROD, "base.json"), encoding="utf-8"))
cfg_p = os.path.join(PROD, "config.json")
cfg = json.load(open(cfg_p, encoding="utf-8")) if os.path.exists(cfg_p) else {"meta_mensal": 40}
CAMPOS = ["id", "ordem_servico", "modalidade", "status", "recebido", "entregue", "dias_ate_entrega", "paginas_ip",
          "paginas_ocr", "valor_rastreado", "prejuizo_documentado", "autoria", "versoes_ultimo", "horas_trabalho",
          "prazo", "situacao_prazo", "no_prazo"]
dados = [{k: c.get(k) for k in CAMPOS} for c in base["casos"]]
payload = json.dumps({"casos": dados, "cfg": cfg, "q": qualidade(), "gerado": datetime.datetime.now().strftime("%d/%m/%Y %H:%M")},
                     ensure_ascii=False).replace("</", "<\\/")

HTML = r"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Painel de Produção</title>
<style>
:root{color-scheme:light;--page:#f9f9f7;--surface:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--muted:#898781;--grid:#e1e0d9;
--axis:#c3c2b7;--ring:rgba(11,11,11,.10);--s1:#2a78d6;--s1soft:#cde2fb;--good:#0ca30c;--warn:#fab219;--crit:#d03b3b;--up:#006300}
@media (prefers-color-scheme:dark){:root:where(:not([data-theme="light"])){color-scheme:dark;--page:#0d0d0d;--surface:#1a1a19;
--ink:#fff;--ink2:#c3c2b7;--grid:#2c2c2a;--axis:#383835;--ring:rgba(255,255,255,.10);--s1:#3987e5;--s1soft:#184f95;--up:#0ca30c}}
:root[data-theme="dark"]{color-scheme:dark;--page:#0d0d0d;--surface:#1a1a19;--ink:#fff;--ink2:#c3c2b7;--grid:#2c2c2a;
--axis:#383835;--ring:rgba(255,255,255,.10);--s1:#3987e5;--s1soft:#184f95;--up:#0ca30c}
*{box-sizing:border-box}body{margin:0;background:var(--page);color:var(--ink);font:14px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:28px 16px 48px}
header{display:flex;flex-wrap:wrap;gap:12px;align-items:flex-end;justify-content:space-between;margin-bottom:20px}
h1{font-size:22px;margin:0;font-weight:650;letter-spacing:-.01em}.sub{color:var(--ink2);font-size:13px}
.ctl{display:flex;gap:8px;align-items:center}select,button{font:inherit;color:var(--ink);background:var(--surface);
border:1px solid var(--ring);border-radius:8px;padding:6px 10px}button{cursor:pointer}
.grid{display:grid;gap:14px}.kpis{grid-template-columns:repeat(auto-fit,minmax(150px,1fr));margin-bottom:14px}
.card{background:var(--surface);border:1px solid var(--ring);border-radius:14px;padding:16px 18px}
.k-l{color:var(--ink2);font-size:12.5px}.k-v{font-size:30px;font-weight:650;margin-top:4px;letter-spacing:-.02em}
.k-s{color:var(--muted);font-size:12px;margin-top:2px}.bar{height:6px;background:var(--grid);border-radius:4px;margin-top:10px;overflow:hidden}
.bar>i{display:block;height:100%;background:var(--s1);border-radius:4px}
.two{grid-template-columns:repeat(auto-fit,minmax(340px,1fr));margin-bottom:14px}
h2{font-size:14px;margin:0 0 10px;font-weight:600}svg{display:block;width:100%;height:auto;overflow:visible}
svg text{fill:var(--muted);font-size:11px;font-variant-numeric:tabular-nums}.gl{stroke:var(--grid)}.bl{stroke:var(--axis)}
.m{fill:var(--s1)}.m:hover{opacity:.8}.meta{stroke:var(--ink2);stroke-dasharray:4 4}
table{width:100%;border-collapse:collapse;font-size:13px}th,td{text-align:left;padding:7px 8px;border-bottom:1px solid var(--grid)}
th{color:var(--ink2);font-weight:600}td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}
.tip{position:fixed;pointer-events:none;background:var(--ink);color:var(--page);padding:6px 9px;border-radius:8px;font-size:12px;
opacity:0;transition:opacity .08s;z-index:9}.vazio{color:var(--muted);padding:24px 0;text-align:center}
.st{display:inline-flex;gap:6px;align-items:center}.dot{width:8px;height:8px;border-radius:50%}
h2.sec{font-size:16px;margin:22px 0 10px}
</style></head><body><div class="wrap">
<header><div><h1>Produção — Relatórios de Investigação</h1><div class="sub" id="sub"></div></div>
<div class="ctl"><select id="ano" aria-label="Ano"></select><select id="mes" aria-label="Mês"></select>
<button id="tema" title="Alternar tema">◐</button></div></header>
<section class="grid kpis" id="kpis"></section>
<section class="grid two"><div class="card"><h2 id="t-dia">Entregas por dia</h2><div id="c-dia"></div></div>
<div class="card"><h2 id="t-mes">Entregas por mês</h2><div id="c-mes"></div></div></section>
<section class="grid two"><div class="card"><h2>Modalidades no ano</h2><div id="c-mod"></div></div>
<div class="card"><h2>Em aberto por etapa</h2><div id="c-aberto"></div></div></section>
<h2 class="sec" id="t-q">Qualidade do fluxo</h2>
<section class="grid kpis" id="q-kpis"></section>
<section class="grid two"><div class="card"><h2>Achados da 1ª revisão</h2><div id="c-rev"></div></div>
<div class="card"><h2>Tempo por etapa — mediana em dias</h2><div id="c-etapas"></div></div></section>
<section class="card" style="margin-bottom:14px"><h2>Tarefas de IA</h2><div id="tab-ia"></div></section>
<section class="card"><h2>Últimas entregas</h2><div id="tab"></div></section>
</div><div class="tip" id="tip"></div>
<script>
const D = __DADOS__;
const MESES=["jan","fev","mar","abr","mai","jun","jul","ago","set","out","nov","dez"];
const ETAPAS=[["recebido","Recebido"],["extraido","Extraído"],["em_analise","Em análise"],["analisado","Analisado"],["minuta","Minuta"],["devolvido","Devolvido"]];
const nf=new Intl.NumberFormat("pt-BR"),brl=new Intl.NumberFormat("pt-BR",{style:"currency",currency:"BRL",maximumFractionDigits:0});
const $=id=>document.getElementById(id), tip=$("tip");
const C=D.casos, meta=D.cfg.meta_mensal||40;
const ent=C.filter(c=>c.entregue);
const anos=[...new Set(ent.map(c=>+c.entregue.slice(0,4)).concat([new Date().getFullYear()]))].sort();
$("ano").innerHTML=anos.map(a=>`<option>${a}</option>`).join("");$("ano").value=new Date().getFullYear();
$("mes").innerHTML=MESES.map((m,i)=>`<option value="${i+1}">${m}</option>`).join("");$("mes").value=new Date().getMonth()+1;
$("sub").textContent=`${D.cfg.investigador||""} · ${D.cfg.unidade||""} · atualizado em ${D.gerado}`;
$("tema").onclick=()=>{const r=document.documentElement,d=r.dataset.theme==="dark"||(!r.dataset.theme&&matchMedia("(prefers-color-scheme: dark)").matches);r.dataset.theme=d?"light":"dark"};
const med=a=>{if(!a.length)return null;const s=[...a].sort((x,y)=>x-y),m=s.length>>1;return s.length%2?s[m]:(s[m-1]+s[m])/2};
const soma=(a,k)=>a.reduce((t,c)=>t+(+c[k]||0),0);
function dica(el,txt){el.addEventListener("mousemove",e=>{tip.textContent=txt;tip.style.opacity=1;tip.style.left=(e.clientX+12)+"px";tip.style.top=(e.clientY-30)+"px"});el.addEventListener("mouseleave",()=>tip.style.opacity=0)}
function kpi(l,v,s,prog){return `<div class="card"><div class="k-l">${l}</div><div class="k-v">${v}</div><div class="k-s">${s||"&nbsp;"}</div>${prog!=null?`<div class="bar"><i style="width:${Math.min(100,prog)}%"></i></div>`:""}</div>`}
function colunas(el,rot,val,{ref=null,fmt=v=>v}={}){
  const W=560,H=200,L=30,B=22,T=10,n=rot.length,mx=Math.max(1,...val,ref||0),bw=(W-L)/n,y=v=>T+(H-T-B)*(1-v/mx);
  let s=`<svg viewBox="0 0 ${W} ${H}" role="img">`;const passo=Math.max(1,Math.ceil(mx/4));
  for(let g=0;g<=mx;g+=passo)s+=`<line class="gl" x1="${L}" x2="${W}" y1="${y(g)}" y2="${y(g)}"/><text x="${L-6}" y="${y(g)+4}" text-anchor="end">${g}</text>`;
  val.forEach((v,i)=>{const x=L+i*bw+bw*.18,w=Math.max(2,bw*.64),h=(H-T-B)-(y(v)-T);
    if(v>0)s+=`<path class="m" data-i="${i}" d="M${x},${H-B}V${y(v)+Math.min(4,h)}q0,-4 4,-4h${w-8}q4,0 4,4V${H-B}Z"/>`;
    if(n<=12||(i+1)%5===0||i===0)s+=`<text x="${x+w/2}" y="${H-6}" text-anchor="middle">${rot[i]}</text>`});
  if(ref)s+=`<line class="meta" x1="${L}" x2="${W}" y1="${y(ref)}" y2="${y(ref)}"/><text x="${W}" y="${y(ref)-5}" text-anchor="end">meta ${ref}</text>`;
  s+=`<line class="bl" x1="${L}" x2="${W}" y1="${H-B}" y2="${H-B}"/></svg>`;el.innerHTML=s;
  el.querySelectorAll(".m").forEach(p=>dica(p,`${rot[p.dataset.i]}: ${fmt(val[p.dataset.i])}`))}
function barrasH(el,itens){
  if(!itens.length){el.innerHTML='<div class="vazio">Sem dados no período</div>';return}
  const mx=Math.max(1e-9,...itens.map(i=>i[1])),W=560,rh=26,H=itens.length*rh+4,L=130;
  let s=`<svg viewBox="0 0 ${W} ${H}" role="img">`;
  itens.forEach(([r,v],i)=>{const w=Math.max(3,(W-L-40)*v/mx),y=i*rh+4;
    s+=`<text x="${L-8}" y="${y+15}" text-anchor="end" style="fill:var(--ink2)">${r}</text><path class="m" data-i="${i}" d="M${L},${y+4}h${w-4}q4,0 4,4v6q0,4 -4,4h${-(w-4)}Z"/><text x="${L+w+6}" y="${y+15}">${nf.format(v)}</text>`});
  el.innerHTML=s+"</svg>";el.querySelectorAll(".m").forEach(p=>dica(p,`${itens[p.dataset.i][0]}: ${itens[p.dataset.i][1]}`))}
function render(){
  const A=+$("ano").value,M=+$("mes").value,pm=`${A}-${String(M).padStart(2,"0")}`;
  const noAno=ent.filter(c=>c.entregue.startsWith(A+"")),noMes=ent.filter(c=>c.entregue.startsWith(pm));
  const abertos=C.filter(c=>!["entregue","arquivado"].includes(c.status));
  const pz=med(noMes.map(c=>c.dias_ate_entrega).filter(v=>v!=null));
  const comAut=noAno.filter(c=>c.autoria==="identificada"||c.autoria==="indicios").length;
  const rastreado=soma(noAno,"valor_rastreado");
  $("kpis").innerHTML=
    kpi(`Entregues em ${MESES[M-1]}/${A}`,nf.format(noMes.length),`meta ${meta} · ${Math.round(100*noMes.length/meta)}%`,100*noMes.length/meta)+
    kpi(`Entregues em ${A}`,nf.format(noAno.length),`média ${nf.format(Math.round(noAno.length/Math.max(1,new Set(noAno.map(c=>c.entregue.slice(0,7))).size)))}/mês`)+
    kpi("Páginas analisadas no mês",nf.format(soma(noMes,"paginas_ip")),`${nf.format(Math.round(soma(noMes,"paginas_ip")/Math.max(1,noMes.length)))} págs./IP`)+
    kpi("Prazo mediano no mês",pz==null?"—":`${nf.format(pz)} d`,"recebido → entregue")+
    kpi("Em aberto",nf.format(abertos.length),"casos não entregues")+
    kpi(`Entregues no prazo (${A})`,(()=>{const cp=noAno.filter(c=>c.no_prazo!==null&&c.no_prazo!==undefined);return cp.length?`${Math.round(100*cp.filter(c=>c.no_prazo).length/cp.length)}%`:"—"})(),`vencidos em aberto: ${C.filter(c=>c.situacao_prazo==="vencido").length}`)+
    kpi(`Retrabalho (${A})`,(()=>{const v=noAno.map(c=>c.versoes_ultimo).filter(x=>x);return v.length?(v.reduce((a,b)=>a+b,0)/v.length).toFixed(1).replace(".",","):"—"})(),"versões por relatório (média)")+
    kpi(`Autoria indicada em ${A}`,noAno.length?`${Math.round(100*comAut/noAno.length)}%`:"—",`valor rastreado ${brl.format(rastreado)}`);
  const nd=new Date(A,M,0).getDate(),porDia=Array(nd).fill(0);noMes.forEach(c=>porDia[+c.entregue.slice(8,10)-1]++);
  $("t-dia").textContent=`Entregas por dia — ${MESES[M-1]}/${A}`;colunas($("c-dia"),porDia.map((_,i)=>i+1),porDia,{fmt:v=>`${v} relatório(s)`});
  const porMes=Array(12).fill(0);noAno.forEach(c=>porMes[+c.entregue.slice(5,7)-1]++);
  $("t-mes").textContent=`Entregas por mês — ${A}`;colunas($("c-mes"),MESES,porMes,{ref:meta,fmt:v=>`${v} relatório(s)`});
  const mod={};noAno.forEach(c=>{const k=c.modalidade||"não classificada";mod[k]=(mod[k]||0)+1});
  let mi=Object.entries(mod).sort((a,b)=>b[1]-a[1]);if(mi.length>8){const o=mi.slice(7).reduce((t,x)=>t+x[1],0);mi=mi.slice(0,7).concat([["outras",o]])}
  barrasH($("c-mod"),mi);
  barrasH($("c-aberto"),ETAPAS.map(([k,r])=>[r,abertos.filter(c=>c.status===k).length]).filter(x=>x[1]>0));
  qualidade(A);
  const ult=[...ent].sort((a,b)=>b.entregue.localeCompare(a.entregue)).slice(0,12);
  $("tab").innerHTML=ult.length?`<table><thead><tr><th>Caso</th><th>O.S.</th><th>Modalidade</th><th class="n">Págs.</th><th class="n">Dias</th><th class="n">Entregue</th></tr></thead><tbody>${
    ult.map(c=>`<tr><td>${c.id}</td><td>${c.ordem_servico||"—"}</td><td>${c.modalidade||"—"}</td><td class="n">${c.paginas_ip??"—"}</td><td class="n">${c.dias_ate_entrega??"—"}</td><td class="n">${c.entregue.split("-").reverse().join("/")}</td></tr>`).join("")}</tbody></table>`:'<div class="vazio">Nenhum relatório entregue ainda</div>';
}
function qualidade(A){
  const Q=D.q,a=A+"",vazio='<div class="vazio">Sem dados no período</div>';
  $("t-q").textContent=`Qualidade do fluxo — ${A}`;
  if(!Q){$("q-kpis").innerHTML=kpi("Qualidade do fluxo","—","dados indisponíveis");["c-rev","c-etapas","tab-ia"].forEach(i=>$(i).innerHTML=vazio);return}
  const doAno=c=>(c.entregue||c.recebido||"").startsWith(a);
  const ent=Q.casos.filter(c=>(c.entregue||"").startsWith(a)),vers=ent.map(c=>c.versoes).filter(v=>v);
  const pv=f=>vers.length?`${Math.round(100*vers.filter(f).length/vers.length)}%`:"—";
  const revs=Q.casos.filter(c=>c.revisao&&doAno(c)),R={sustentada:0,parcial:0,nao_localizada:0,contraditoria:0};
  revs.forEach(c=>Object.keys(R).forEach(k=>R[k]+=c.revisao[k]||0));const tot=Object.values(R).reduce((x,y)=>x+y,0);
  const ia=Q.ia.filter(p=>(p.criado||"").startsWith(a)),fim=ia.filter(p=>p.estado==="concluida"||p.estado==="erro");
  const md=v=>{const m=med(v.filter(x=>x!=null));return m==null?"—":nf.format(Math.round(m*10)/10)};
  $("q-kpis").innerHTML=
    kpi("Versões até o FINAL",md(vers),`mediana · 1 versão: ${pv(v=>v===1)} · 3 ou mais: ${pv(v=>v>=3)}`)+
    kpi("Sustentadas na 1ª revisão",tot?`${Math.round(100*R.sustentada/tot)}%`:"—",`${nf.format(tot)} afirmações em ${revs.length} revisão(ões)`,tot?100*R.sustentada/tot:null)+
    kpi("Não localizadas + contraditórias",nf.format(R.nao_localizada+R.contraditoria),"na 1ª revisão — corrigir antes do DOCX")+
    kpi("Tarefas de IA concluídas",fim.length?`${Math.round(100*fim.filter(p=>p.estado==="concluida").length/fim.length)}%`:"—",`${ia.length} pedido(s) · espera mediana ${md(ia.map(p=>p.espera_min))} min`);
  barrasH($("c-rev"),tot?[["Sustentadas",R.sustentada],["Parciais",R.parcial],["Não localizadas",R.nao_localizada],["Contraditórias",R.contraditoria]].filter(x=>x[1]>0):[]);
  const NOMES={extraido:"Até extraído",em_analise:"Até em análise",analisado:"Até analisado",minuta:"Até minuta",entregue:"Até entregue"};
  barrasH($("c-etapas"),Object.entries(NOMES).map(([k,r])=>{const v=med(Q.casos.filter(c=>(c.datas_etapas[k]||"").startsWith(a)).map(c=>c.etapas[k]).filter(x=>x!=null));return [r,v==null?null:Math.round(v*10)/10]}).filter(x=>x[1]!=null));
  const acoes={analisar:"Análise",relatorio:"Relatório",completo:"Análise + relatório",revisar:"Revisão"},por={};ia.forEach(p=>(por[p.acao]=por[p.acao]||[]).push(p));
  $("tab-ia").innerHTML=ia.length?`<table><thead><tr><th>Ação</th><th class="n">Pedidos</th><th class="n">Concluídas</th><th class="n">Erros</th><th class="n">Espera (min)</th><th class="n">Execução (min)</th></tr></thead><tbody>${
    Object.entries(por).map(([k,ps])=>`<tr><td>${acoes[k]||k}</td><td class="n">${ps.length}</td><td class="n">${ps.filter(p=>p.estado==="concluida").length}</td><td class="n">${ps.filter(p=>p.estado==="erro").length}</td><td class="n">${md(ps.map(p=>p.espera_min))}</td><td class="n">${md(ps.map(p=>p.execucao_min))}</td></tr>`).join("")}</tbody></table>`:vazio}
$("ano").onchange=render;$("mes").onchange=render;render();
</script></body></html>"""

saida = os.path.join(PROD, "painel.html")
open(saida, "w", encoding="utf-8").write(HTML.replace("__DADOS__", payload))
print(f"Painel -> {saida} ({len(dados)} caso(s))")
