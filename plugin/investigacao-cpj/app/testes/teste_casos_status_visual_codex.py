"""Status concluídos: células e temas conferidos no navegador real."""
import unittest
from teste_interface_rg26 import InterfaceFixtureRG26


CASOS = r'''
  const estados=['entregue','concluido','Concluído','em_analise','minuta','arquivado'];
  await page.route('**/api/casos?*',route=>route.fulfill({json:estados.map((status,i)=>({
    id:'OS-'+(i+1)+'-2099',ordem_servico:(i+1)+'/2099',status,visto:true,
    vitimas:['<img src=x onerror="window.injetado=true">'],investigados:[]
  }))}));
  await page.evaluate(()=>carregarCasos());
'''


class CasosStatusVisualTests(InterfaceFixtureRG26):
    def test_somente_status_finalizados_destacados_e_texto_escapado(self):
        self.cenario(CASOS + r'''
  const classes=await page.locator('#t-casos tr').evaluateAll(es=>es.map(e=>e.classList.contains('linha-concluida')));
  assert.deepEqual(classes,[true,true,true,false,false,false]);
  assert.equal(await page.locator('#t-casos img').count(),0);
  assert.equal(await page.evaluate(()=>window.injetado),undefined);
  assert.ok((await page.locator('#t-casos tr').first().innerText()).includes('<img'));
''')

    def test_todas_celulas_concluidas_verdes_nos_dois_temas_inclusive_hover(self):
        self.cenario(CASOS + r'''
  for(const tema of ['light','dark']){
   await page.locator('html').evaluate((e,t)=>e.dataset.theme=t,tema);
   const esperado=await page.evaluate(()=>{
    const e=document.createElement('span');e.style.background='var(--good-soft)';document.body.append(e);
    const cor=getComputedStyle(e).backgroundColor;e.remove();return cor;
   });
   for(let linha=0;linha<3;linha++){
    const tr=page.locator('#t-casos tr').nth(linha);await tr.hover();
    const cores=await tr.locator('td').evaluateAll(es=>es.map(e=>getComputedStyle(e).backgroundColor));
    assert.ok(cores.every(c=>c===esperado),tema+': todas as células devem ficar verdes');
   }
   const aberta=await page.locator('#t-casos tr').nth(3).locator('td').first().evaluate(e=>getComputedStyle(e).backgroundColor);
   assert.notEqual(aberta,esperado,'Caso aberto deve continuar distinguível');
  }
''')


if __name__ == "__main__":
    unittest.main()
