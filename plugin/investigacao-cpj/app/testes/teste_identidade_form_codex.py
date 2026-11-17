"""Identificação: preenchimento, máscara, edição e payloads no Edge."""
import unittest
from teste_interface_rg26 import InterfaceFixtureRG26


class IdentidadeFormTests(InterfaceFixtureRG26):
    def test_nome_permite_autopreenchimento_e_cpf_formata_sem_inventar_digitos(self):
        self.cenario(r'''
  for(const id of ['f-setup','f-usuario']){
   const form=page.locator('#'+id);
   assert.equal(await form.locator('[name=nome]').getAttribute('autocomplete'),'name');
   const campo=form.locator('[name=cpf]');
   for(const [entrada,esperado] of [['52998224700','529.982.247-00'],['12x34','123.4'],['123','123'],['','']]){
    await campo.evaluate((e,v)=>{e.value=v;e.dispatchEvent(new Event('input',{bubbles:true}))},entrada);
    assert.equal(await campo.inputValue(),esperado);
   }
  }
''')

    def test_cargos_comuns_outro_e_reset_em_todos_os_formularios(self):
        self.cenario(r'''
  for(const id of ['f-setup','f-usuario','f-conta']){
   const form=page.locator('#'+id),select=form.locator('[data-cargo-select]'),outro=form.locator('[data-cargo-outro]');
   for(const cargo of ['Delegado de Polícia','Escrivão de Polícia','Investigador de Polícia','Agente de Polícia']){
    await select.selectOption({label:cargo}, {force:true});
    assert.equal(await form.evaluate(f=>valorCargo(f)),cargo);
    assert.equal(await outro.evaluate(e=>e.hidden),true);
   }
   await form.evaluate(f=>selecionarCargo(f,'Escrivão Chefe Fictício'));
   assert.equal(await select.inputValue(),'outro');
   assert.equal(await outro.inputValue(),'Escrivão Chefe Fictício');
   assert.equal(await outro.evaluate(e=>e.hidden||e.disabled),false);
   assert.equal(await form.evaluate(f=>valorCargo(f)),'Escrivão Chefe Fictício');
   await form.evaluate(f=>f.reset());
   await page.waitForFunction(id=>document.querySelector('#'+id+' [data-cargo-outro]').hidden,id);
   assert.equal(await form.evaluate(f=>valorCargo(f)),'');
  }
''')

    def test_submissoes_usam_cargo_e_cpf_mascarado_uma_unica_vez(self):
        self.cenario(r'''
  const enviados=[];
  await page.route('**/api/configurar',async route=>{enviados.push({url:'/api/configurar',data:route.request().postDataJSON()});await route.fulfill({json:{ok:true}})});
  await page.locator('#tela-setup').evaluate(e=>e.hidden=false);
  const setup=page.locator('#f-setup');
  await setup.locator('[name=nome]').fill('Policial Fictício');await setup.locator('[name=login]').fill('setup.ficticio');
  await setup.locator('[name=senha]').fill('Ficticia123');await setup.locator('[name=senha2]').fill('Ficticia123');
  await setup.locator('[name=cpf]').fill('52998224700');await setup.locator('[data-cargo-select]').selectOption({label:'Investigador de Polícia'});
  await Promise.all([page.waitForResponse(r=>r.url().endsWith('/api/configurar')),setup.locator('button:not([type])').click()]);
  assert.equal(enviados[0].data.cpf,'529.982.247-00');assert.equal(enviados[0].data.cargo,'Investigador de Polícia');
  await page.locator('#tela-setup').evaluate(e=>e.hidden=true);
  await page.evaluate(()=>abrirAba('sistema'));
  await page.locator('#lista-usuarios [data-edu]').first().waitFor();
  await page.route('**/api/usuarios',async route=>{
   if(route.request().method()==='POST'){enviados.push({url:'/api/usuarios',data:route.request().postDataJSON()});await route.fulfill({json:{ok:true}})}
   else await route.continue();
  });
  const usuario=page.locator('#f-usuario');
  await usuario.locator('[name=nome]').fill('Usuário Fictício');await usuario.locator('[name=login]').fill('usuario.ficticio');
  await usuario.locator('[name=cpf]').fill('11144477700');await usuario.locator('[data-cargo-select]').selectOption('outro');
  await usuario.locator('[data-cargo-outro]').fill('Cargo Fictício');
  await usuario.locator('button:not([type])').click();
  await page.waitForFunction(()=>document.querySelector('#msg-usr').textContent==='Salvo');
  assert.equal(enviados[1].data.cargo,'Cargo Fictício');assert.equal(enviados[1].data.cpf,'111.444.777-00');
  assert.equal(enviados.length,2);
''')

    def test_edicao_cargo_personalizado_e_cpf_em_branco_preserva_contrato(self):
        self.cenario(r'''
  await context.request.post(url+'/api/minha-conta',{headers:{'X-CPJ':'1'},data:{cargo:'Investigador Chefe Fictício'}});
  await page.reload();await page.waitForLoadState('networkidle');await page.evaluate(()=>abrirAba('sistema'));
  const conta=page.locator('#f-conta');
  assert.equal(await conta.locator('[data-cargo-select]').inputValue(),'outro');
  assert.equal(await conta.locator('[data-cargo-outro]').inputValue(),'Investigador Chefe Fictício');
  await page.locator('#lista-usuarios [data-edu]').first().click();
  const f=page.locator('#f-usuario');
  assert.equal(await f.locator('[data-cargo-outro]').inputValue(),'Investigador Chefe Fictício');
  assert.equal(await f.locator('[name=cpf]').inputValue(),'');
  let dado;
  await page.route('**/api/usuarios',async route=>{
   if(route.request().method()==='POST'){dado=route.request().postDataJSON();await route.fulfill({json:{ok:true}})}
   else await route.continue();
  });
  await f.locator('button:not([type])').click();
  await page.waitForFunction(()=>document.querySelector('#msg-usr').textContent==='Salvo');
  assert.equal(dado.cargo,'Investigador Chefe Fictício');assert.equal(Object.hasOwn(dado,'cpf'),false);
  await page.locator('#b-usr-novo').click();
  assert.equal(await f.locator('[data-cargo-select]').inputValue(),'');
  assert.equal(await f.locator('[data-cargo-outro]').evaluate(e=>e.hidden),true);
''')


if __name__ == "__main__":
    unittest.main()
