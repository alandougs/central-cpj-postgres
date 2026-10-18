// Integração real local; o Python prepara apenas a saída fictícia de análise.
const {chromium}=require(process.env.CPJ_NODE_MODULES+'/playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');const path=require('node:path');
const ws=process.env.AST17_WS,base=process.env.AST17_URL,phase=process.argv[2];
const statePath=path.join(ws,'estado.json');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const context=await browser.newContext({viewport:{width:1440,height:1000}});
 const page=await context.newPage();page.setDefaultTimeout(15000);
 const errors=[],consoleErrors=[],http5=[],external=[];
 page.on('pageerror',e=>errors.push(e.message));
 page.on('console',m=>{if(m.type()==='error')consoleErrors.push(m.text())});
 page.on('response',r=>{if(r.status()>=500)http5.push(r.url()+':'+r.status())});
 await context.route('**/*',async route=>{const u=new URL(route.request().url());
   if(!['127.0.0.1','localhost'].includes(u.hostname)){external.push(u.origin);await route.abort();return}
   // Asset oficial ignorado ausente no checkout: substituição geométrica só no harness.
   if(u.pathname==='/static/brasao-pcsp.png'){await route.fulfill({status:200,contentType:'image/svg+xml',body:'<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40"><rect width="40" height="40" fill="white"/><rect x="5" y="5" width="30" height="30" fill="none" stroke="black"/></svg>'});return}
   await route.continue()});
 const get=async url=>{const r=await context.request.get(base+url);assert.equal(r.status(),200,await r.text());return r.json()};
 const post=async(url,data)=>context.request.post(base+url,{headers:{'X-CPJ':'1'},data});
 const ready=async()=>{await page.goto(base);await page.locator('#app:not([hidden])').waitFor()};
 const saveState=s=>fs.writeFileSync(statePath,JSON.stringify(s,null,2));
 let state=fs.existsSync(statePath)?JSON.parse(fs.readFileSync(statePath,'utf8')):{};
 try{
 await ready();
 if(phase==='upload'){
   await page.locator('#nav [data-a="nova"]').click();
   const detection=page.waitForResponse(r=>r.url().endsWith('/api/os/detectar'));
   await page.locator('#arqs').setInputFiles(path.join(ws,'autos-ficticios.pdf'));await detection;
   await page.locator('#f-os [name="os"]').fill('456/2026');
   await page.locator('#f-os [name="modo_processamento"]').selectOption('rapido');
   const [r]=await Promise.all([page.waitForResponse(r=>r.url().endsWith('/api/os')&&r.request().method()==='POST'),page.locator('#b-enviar').click()]);
   assert.equal(r.status(),200,await r.text());state.caso=(await r.json()).caso;saveState(state);
   const end=Date.now()+110000;let done=false;
   while(Date.now()<end){
     const j=await get('/api/casos/'+state.caso);
     const raw=JSON.stringify(j.processamento);
     assert.ok(!raw.includes('"status":"erro"'),raw);
     if(j.arquivos.some(a=>a.caminho.endsWith('/entidades.csv'))&&raw.includes('"status":"concluido"')){done=true;break}
     await page.waitForTimeout(500);
   }
   assert.ok(done,'Extração real não terminou');
   await page.locator('#nav [data-a="casos"]').click();await page.locator(`#t-casos tr[data-id="${state.caso}"]`).click();
   await page.waitForFunction(()=>document.querySelector('#detalhe').textContent.includes('transcricao.md'));
 }else if(phase==='fontes'){
   await page.goto(base+'/#grafo');await page.locator('#gr-caso').selectOption(state.caso);
   await page.waitForFunction(()=>grEstado==='pronto'&&grDados.arestas.some(a=>a.relacao.startsWith('transferiu')));
   const edge=await page.evaluate(()=>grDados.arestas.find(a=>a.relacao.startsWith('transferiu')));
   const evidence=edge.evidencias.find(e=>e.documento==='autos-ficticios.pdf');
   assert.ok(evidence);assert.equal(evidence.pagina,2);assert.equal(evidence.fls,'2');
   state.edge=Object.fromEntries(['a_tipo','a_valor','b_tipo','b_valor','relacao'].map(k=>[k,edge[k]]));
   await page.evaluate(()=>grInspecionarAresta(grEdges.find(a=>a.relacao.startsWith('transferiu'))));
   const panel=page.locator('#gr-detalhes-conteudo');
   assert.ok(await panel.locator('.gr-evidencia').count());assert.match(await panel.innerText(),/autos-ficticios\.pdf/);
   const source=panel.locator('a[href^="/arquivo/"]').first();const href=await source.getAttribute('href');
   const sourceResponse=await context.request.get(base+href);assert.equal(sourceResponse.status(),200);
   state.documental=edge.evidencias.map(e=>e.id);
   await page.evaluate(valor=>grInspecionarNo(grNodes.find(n=>n.valor===valor)),edge.a_valor);
   await page.locator('#astra-pergunta').fill('Quais documentos sustentam este caminho do dinheiro?');
   const [answer]=await Promise.all([page.waitForResponse(r=>r.url().endsWith('/api/astra/perguntar')),page.locator('#b-astra-perguntar').click()]);
   assert.equal(answer.status(),200,await answer.text());assert.ok((await answer.json()).grafo.arestas.length);
   const payload={...state.edge,caso:state.caso,documento:'autos-ficticios.pdf',pagina:2,fls:'2',observacao:'Hipótese fictícia do operador AST17'};
   let r=await post('/api/grafo/vinculo',payload);assert.equal(r.status(),200,await r.text());state.manual=await r.json();
   r=await post('/api/grafo/vinculo',payload);assert.equal(r.status(),409,'Duplicata exata deve ser recusada');
   saveState(state);
 }else if(phase==='relatorio'){
   const graph=await get('/api/grafo?caso='+state.caso);
   const edge=graph.arestas.find(a=>a.relacao===state.edge.relacao&&a.a_valor===state.edge.a_valor);
   assert.ok(edge.evidencias.some(e=>e.manual_id===state.manual.id),'Manual preservado após reindexar e reiniciar');
   assert.ok(edge.evidencias.some(e=>state.documental.includes(e.id)),'Fonte documental preservada');
   let r=await post('/api/grafo/vinculo/remover',{...state.edge,caso:state.caso});assert.equal(r.status(),400);
   r=await post('/api/grafo/vinculo/remover',{id:state.manual.id,caso:state.caso,versao:state.manual.versao});assert.equal(r.status(),200,await r.text());
   r=await post('/api/grafo/vinculo/remover',{id:state.manual.id,caso:state.caso,versao:state.manual.versao});assert.equal(r.status(),409);
   const after=await get('/api/grafo?caso='+state.caso);
   const retained=after.arestas.find(a=>a.relacao===state.edge.relacao&&a.a_valor===state.edge.a_valor);
   assert.ok(retained.evidencias.some(e=>state.documental.includes(e.id)));assert.ok(!retained.evidencias.some(e=>e.manual_id===state.manual.id));
   r=await context.request.post(base+'/api/grafo/vinculo/remover',{data:{id:state.manual.id,caso:state.caso,versao:state.manual.versao}});assert.equal(r.status(),403);
   await page.locator('#nav [data-a="casos"]').click();await page.locator(`#t-casos tr[data-id="${state.caso}"]`).click();
   await page.locator('#b-nova-minuta').waitFor();
   await page.locator('#b-nova-minuta').click();await page.locator('#ed-secoes textarea').first().waitFor();
   const meta={ordem_servico:'456/2026',referencia:'IPe nº 4562026 / Processo nº 0000001-00.2026.8.26.0000',natureza:'Estelionato',investigados:'CARLOS TESTE SANTOS',vitimas:'MARIA TESTE SILVA',local:'Presidente Prudente, SP',data_fatos:'12/03/2026',local_data:'Presidente Prudente, 12 de março de 2026',delegado:'Delegado de Polícia Titular',delegado_genero:'M'};
   for(const [k,v]of Object.entries(meta))await page.locator(`#ed-meta input[data-m="${k}"]`).fill(v);
   const resumo=page.locator('#ed-secoes textarea[data-s="RESUMO DOS FATOS"]');
   await resumo.fill('O extrato de **MARIA TESTE SILVA** registra transferência via Pix de R$ 5.000,00 em 12/03/2026 (pág. 2 do PDF; fls. 2).');
   await page.locator('#ed-secoes textarea[data-s="DILIGÊNCIAS REALIZADAS"]').fill('A O.S. determina a identificação do titular da conta recebedora do Pix; o documento bancário fictício identifica **CARLOS TESTE SANTOS** como titular (pág. 3 do PDF; fls. 3). A análise do extrato confirma o lançamento de R$ 5.000,00 (pág. 2 do PDF; fls. 2).');
   await page.locator('#ed-secoes textarea[data-s="CONCLUSÃO"]').fill('A solicitação da O.S. foi atendida com a identificação documental de **CARLOS TESTE SANTOS** como titular da conta recebedora, sem atribuir autoria exclusivamente pela titularidade (pág. 3 do PDF; fls. 3).');
   await page.locator('#ed-salvar').click();await page.waitForFunction(()=>document.querySelector('#editor').dataset.estado==='salvo');
   assert.ok(await page.locator('#editor').isVisible());
   assert.equal((await get('/api/casos/'+state.caso)).arquivos.filter(a=>a.caminho.endsWith('.docx')).length,0);
   const saved=await resumo.inputValue();await page.locator('#ed-cancelar').click();await page.locator('#b-nova-minuta').click();
   await page.locator('#ed-secoes textarea').first().waitFor();assert.equal(await resumo.inputValue(),saved);
   const conclusion=page.locator('#ed-secoes textarea[data-s="CONCLUSÃO"]'),complete=await conclusion.inputValue();
   await conclusion.fill('[PENDENTE]');
   const [pendingDocx]=await Promise.all([page.waitForResponse(r=>r.url().endsWith('/docx')&&r.request().method()==='POST'),page.locator('#ed-docx').click()]);
   assert.equal(pendingDocx.status(),200,await pendingDocx.text());
   r=await post('/api/casos/'+state.caso+'/final',{docx:(await pendingDocx.json()).docx});
   state.bloqueio={status:r.status(),dados:await r.json()};saveState(state);
   assert.equal(r.status(),409);assert.equal(state.bloqueio.dados.bloqueado,true);
   assert.ok(!(await get('/api/casos/'+state.caso)).arquivos.some(a=>a.caminho.includes('-FINAL.')));
   await conclusion.fill(complete);
   const [docx]=await Promise.all([page.waitForResponse(r=>r.url().endsWith('/docx')&&r.request().method()==='POST'),page.locator('#ed-docx').click()]);
   assert.equal(docx.status(),200,await docx.text());state.docx=(await docx.json()).docx;
   await page.waitForFunction(()=>document.querySelector('#ed-msg').textContent.includes('DOCX gerado'));await page.locator('#ed-cancelar').click();
   assert.ok(!(await get('/api/casos/'+state.caso)).arquivos.some(a=>a.caminho.includes('-FINAL.')),'Nenhum FINAL automático');
   page.on('dialog',d=>d.accept());
   const [final]=await Promise.all([page.waitForResponse(r=>r.url().endsWith('/final')&&r.request().method()==='POST'),page.locator(`#detalhe [data-final=${JSON.stringify(state.docx)}]`).click()]);
   state.final={status:final.status(),dados:await final.json()};saveState(state);
   assert.equal(final.status(),200,JSON.stringify(state.final));assert.ok(!final.request().postDataJSON().forcar,'Gate não pode ser forçado');
   await page.locator(`#detalhe a:has-text("RELATORIO-${state.caso}-FINAL.docx")`).first().waitFor();
   await page.locator('#nav [data-a="estatisticas"]').click();await page.locator('#if-painel[src]').waitFor();
   let html='';const end=Date.now()+30000;
   while(Date.now()<end){const panel=await context.request.get(base+'/painel');assert.equal(panel.status(),200);html=await panel.text();if(html.includes('"id": "'+state.caso+'"'))break;await page.waitForTimeout(400)}
   assert.match(html,/Painel de Produção/);assert.ok(html.includes('"id": "'+state.caso+'"'));
 }else throw Error('Fase desconhecida: '+phase);
 await page.screenshot({path:path.join(ws,phase+'.png'),fullPage:true});
 assert.deepEqual(errors,[]);assert.deepEqual(consoleErrors,[]);assert.deepEqual(http5,[]);assert.deepEqual(external,[]);
 console.log(JSON.stringify({fase:phase,ok:true,edge:browser.version(),asset_ficticio:'/static/brasao-pcsp.png',erros:errors,consoleErrors,http5,externos:external}));
 }catch(e){await page.screenshot({path:path.join(ws,phase+'-falha.png'),fullPage:true});throw e}
 finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
