// Medição de uma execução (uma árvore de código, um workspace fictício). Chamado por medir-desempenho.py.
// Entrada por ambiente: CPJ_NODE_MODULES, MD_URL, MD_WS, MD_PID (servidor), MD_PDF (autos fictícios com páginas escaneadas),
// MD_PERFIL (diretório do perfil do navegador). Saída: um JSON em stdout. Nada é gravado fora de MD_WS/MD_PERFIL.
const {chromium}=require(process.env.CPJ_NODE_MODULES+'/playwright');
const {execFileSync}=require('node:child_process');
const base=process.env.MD_URL,pid=Number(process.env.MD_PID),pdf=process.env.MD_PDF,perfil=process.env.MD_PERFIL;
const ABAS=['nova','casos','pendencias','painel'];       // as que existirem no menu; ausentes são ignoradas
const mediana=a=>{const s=[...a].sort((x,y)=>x-y);const m=s.length>>1;return s.length?(s.length%2?s[m]:(s[m-1]+s[m])/2):null};
const ps=cmd=>{try{return execFileSync('powershell.exe',['-NoProfile','-NonInteractive','-Command',cmd],{encoding:'utf8',timeout:20000}).trim()}catch(e){return ''}};
const num=t=>{const n=Number(t);return Number.isFinite(n)&&t!==''?n:null};
const mb=b=>b==null?null:Math.round(b/1048576*10)/10;
const memServidor=()=>mb(num(ps(`$p=Get-CimInstance Win32_Process|Where-Object{$_.ProcessId -eq ${pid} -or $_.ParentProcessId -eq ${pid}};[int64](($p|Measure-Object WorkingSetSize -Sum).Sum)`)));
const picoServidor=()=>mb(num(ps(`$ids=@(${pid})+@(Get-CimInstance Win32_Process|Where-Object{$_.ParentProcessId -eq ${pid}}|ForEach-Object{$_.ProcessId});[int64](($ids|ForEach-Object{(Get-Process -Id $_ -ErrorAction SilentlyContinue).PeakWorkingSet64}|Measure-Object -Sum).Sum)`)));
const memNavegador=()=>mb(num(ps(`$d='${perfil.replace(/'/g,"''")}';$p=Get-CimInstance Win32_Process -Filter "Name='msedge.exe'"|Where-Object{$_.CommandLine -like ('*'+$d+'*')};[int64](($p|Measure-Object WorkingSetSize -Sum).Sum)`)));
(async()=>{
 const contexto=await chromium.launchPersistentContext(perfil,{channel:'msedge',headless:true,viewport:{width:1440,height:1000}});
 const page=contexto.pages()[0]||await contexto.newPage();page.setDefaultTimeout(20000);
 const externos=[],erros=[];
 page.on('pageerror',e=>erros.push(e.message));
 await contexto.route('**/*',async r=>{const u=new URL(r.request().url());
   if(!['127.0.0.1','localhost'].includes(u.hostname)){externos.push(u.origin);await r.abort();return}
   if(u.pathname==='/static/brasao-pcsp.png'){await r.fulfill({status:200,contentType:'image/svg+xml',body:'<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40"><rect width="40" height="40" fill="white"/></svg>'});return}
   await r.continue()});
 const out={};
 try{
  await page.addInitScript(()=>{window.__longtasks=[];try{new PerformanceObserver(l=>{for(const e of l.getEntries())window.__longtasks.push(e.duration)}).observe({entryTypes:['longtask']})}catch(e){}});
  // 1. abertura da aplicação
  const t0=Date.now();await page.goto(base);await page.locator('#app:not([hidden])').waitFor();out.abertura_ms=Date.now()-t0;
  await page.waitForTimeout(1500);
  out.mem_servidor_ocioso_mb=memServidor();out.mem_navegador_ocioso_mb=memNavegador();
  // 2. consultas leves de tarefas, a partir do navegador
  out.tarefas_ms=await page.evaluate(async()=>{const v=[];for(let i=0;i<20;i++){const t=performance.now();const r=await fetch('/api/tarefas');await r.text();v.push(performance.now()-t)}return v});
  out.tarefas_mediana_ms=mediana(out.tarefas_ms);
  out.casos_ms=await page.evaluate(async()=>{const t=performance.now();const r=await fetch('/api/casos');await r.text();return performance.now()-t});
  // 3. navegação entre abas, sem carga
  const abas=await page.evaluate(a=>a.filter(x=>document.querySelector('#nav [data-a="'+x+'"]')),ABAS);
  const navega=async()=>{const r={};for(const a of abas){
     r[a]=await page.evaluate(async x=>{const t=performance.now();document.querySelector('#nav [data-a="'+x+'"]').click();
        await new Promise(f=>requestAnimationFrame(()=>requestAnimationFrame(f)));return performance.now()-t},a)}return r};
  out.abas=abas;out.navegacao_ocioso_ms=await navega();
  // 4. navegação durante OCR/fila: envia autos fictícios com páginas escaneadas e navega até concluir
  await page.locator('#nav [data-a="nova"]').click();
  const deteccao=page.waitForResponse(r=>r.url().endsWith('/api/os/detectar'));
  await page.locator('#arqs').setInputFiles(pdf);await deteccao;
  await page.locator('#f-os [name="os"]').fill('901/2026');
  await page.locator('#f-os [name="modo_processamento"]').selectOption('rapido');
  await page.evaluate(()=>{window.__longtasks.length=0});
  const tEnvio=Date.now();
  const [resp]=await Promise.all([page.waitForResponse(r=>r.url().endsWith('/api/os')&&r.request().method()==='POST'),page.locator('#b-enviar').click()]);
  out.envio_status=resp.status();const caso=(await resp.json()).caso;
  const duranteOcr=[],memS=[],memN=[];let concluiu=false;const fim=Date.now()+120000;let ciclo=0;
  while(Date.now()<fim){
    const n=await navega();for(const a of abas)duranteOcr.push(n[a]);
    if(ciclo%3===0){memS.push(memServidor());memN.push(memNavegador())}
    ciclo++;
    const j=await (await contexto.request.get(base+'/api/casos/'+caso)).json();
    const raw=JSON.stringify(j.processamento||{});
    if(raw.includes('"status":"erro"')){out.erro_processamento=true;break}
    if((j.arquivos||[]).some(a=>a.caminho.endsWith('/entidades.csv'))&&raw.includes('"status":"concluido"')){concluiu=true;break}
    await page.waitForTimeout(300);
  }
  out.ocr_concluiu=concluiu;out.ocr_duracao_s=Math.round((Date.now()-tEnvio)/100)/10;
  out.navegacao_durante_ocr_ms=duranteOcr;out.navegacao_durante_ocr_mediana_ms=mediana(duranteOcr);
  out.navegacao_durante_ocr_max_ms=duranteOcr.length?Math.max(...duranteOcr):null;
  const lt=await page.evaluate(()=>window.__longtasks.slice());
  out.longtasks_n=lt.length;out.longtasks_max_ms=lt.length?Math.max(...lt):0;
  // 5. memória: pico do servidor (SO) e amostras durante o OCR; heap JS do navegador ao final
  out.mem_servidor_ocr_max_mb=memS.filter(x=>x!=null).length?Math.max(...memS.filter(x=>x!=null)):null;
  out.mem_navegador_ocr_max_mb=memN.filter(x=>x!=null).length?Math.max(...memN.filter(x=>x!=null)):null;
  out.pico_servidor_mb=picoServidor();out.mem_navegador_final_mb=memNavegador();
  out.heap_js_mb=await page.evaluate(()=>performance.memory?Math.round(performance.memory.usedJSHeapSize/1048576*10)/10:null);
  out.recursos_externos=[...new Set(externos)];out.erros_pagina=erros.slice(0,5);
 }finally{await contexto.close()}
 process.stdout.write(JSON.stringify(out));
})().catch(e=>{process.stderr.write(String(e&&e.stack||e));process.exit(1)});
