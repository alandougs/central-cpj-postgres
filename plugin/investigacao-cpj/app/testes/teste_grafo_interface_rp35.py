"""RP35: consumidor do grafo no Edge, sessão real, histórico apenas TEMP."""
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from teste_interface_rg26 import InterfaceFixtureRG26


class GrafoInterfaceRP35(InterfaceFixtureRG26):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        for numero in (351, 352):
            caso = cls.ws / "casos" / f"OS-{numero}-2099"
            caso.mkdir()
            (caso / "caso.json").write_text(json.dumps({
                "id": caso.name, "ordem_servico": f"{numero}/2099", "status": "recebido",
            }), encoding="utf-8")
        script = Path(__file__).resolve().parents[2] / "skills/base-cpj/scripts/indexar.py"
        r = subprocess.run([sys.executable, str(script)], env=dict(os.environ), capture_output=True,
                           text=True, timeout=40)
        if r.returncode:
            raise AssertionError(r.stdout + r.stderr)

    def test_relacao_apostrofe_e_html_nao_executam_script_ao_remover(self):
        self.cenario(r'''
  const rel="x');window.rp35=1;// <img src=x onerror=window.rp35=2>";
  const dados={caso:'OS-351-2099',a_tipo:'EMAIL',a_valor:'inj-a@example.invalid',
   b_tipo:'EMAIL',b_valor:'inj-b@example.invalid',relacao:rel};
  const r=await context.request.post(url+'/api/grafo/vinculo',{headers:{'X-CPJ':'1'},data:dados});
  assert.equal(r.status(),200);
  await page.evaluate(async()=>{abrirAba('grafo');await carregarGrafo();grInspecionarNo(grNodes.find(n=>n.valor==='inj-a@example.invalid'))});
  assert.ok((await page.locator('#gr-detalhes-conteudo').textContent()).includes(rel));
  assert.equal(await page.locator('#gr-detalhes-conteudo img').count(),0);
  page.on('dialog',d=>d.accept());
  const resposta=page.waitForResponse(r=>r.url().endsWith('/api/grafo/vinculo/remover'));
  await page.locator('#gr-detalhes-conteudo button').filter({hasText:'remover'}).click();
  assert.equal((await resposta).status(),200,'Remove a relação integral, sem interpretar seu conteúdo');
  assert.equal(await page.evaluate(()=>window.rp35||0),0,'Rótulo é texto, nunca programa');
  const g=await (await context.request.get(url+'/api/grafo')).json();
  assert.equal(g.arestas.filter(a=>a.relacao===rel).length,0);
''')

    def test_formulario_preserva_os_e_anotacao_da_fonte(self):
        self.cenario(r'''
  await page.evaluate(()=>{abrirAba('grafo');grAbrirModalVinculo()});
  await page.locator('#f-vinculo [name=a_tipo]').selectOption('CHAVE_PIX');
  await page.locator('#f-vinculo [name=a_valor]').fill('cadastro@example.invalid');
  await page.locator('#f-vinculo [name=b_tipo]').selectOption('CHAVE_PIX');
  await page.locator('#f-vinculo [name=b_valor]').fill('destino@example.invalid');
  await page.locator('#f-vinculo [name=relacao]').fill('ligação fictícia');
  await page.locator('#f-vinculo [name=caso_id]').fill('OS-351-2099');
  await page.locator('#f-vinculo [name=observacao]').fill("Anotação do operador: conferir D'Ávila, Fls. 40");
  const req=page.waitForRequest(r=>r.url().endsWith('/api/grafo/vinculo')&&r.method()==='POST');
  const res=page.waitForResponse(r=>r.url().endsWith('/api/grafo/vinculo')&&r.request().method()==='POST');
  await page.locator('#f-vinculo button[type=submit]').click();
  const pedido=await req;assert.equal((await res).status(),200);
  const payload=pedido.postDataJSON();
  assert.equal(payload.caso,'OS-351-2099');
  assert.equal(payload.observacao,"Anotação do operador: conferir D'Ávila, Fls. 40");
''')
        import vinculos_manuais as VM
        registros = [r for r in VM.listar(self.ws) if r["a_valor"] == "cadastro@example.invalid"]
        self.assertEqual(len(registros), 1)
        self.assertEqual(registros[0]["caso"], "OS-351-2099")
        self.assertEqual(registros[0]["evidencia"]["observacao"], "Anotação do operador: conferir D'Ávila, Fls. 40")

    def test_remover_pelo_destino_preserva_direcao_e_outro_caso(self):
        self.cenario(r'''
  const base={a_tipo:'EMAIL',a_valor:'origem@example.invalid',b_tipo:'EMAIL',
   b_valor:'fim-remocao@example.invalid',relacao:'relação conferida pelo operador'};
  for(const caso of ['OS-351-2099','OS-352-2099']){
   const r=await context.request.post(url+'/api/grafo/vinculo',{headers:{'X-CPJ':'1'},data:{...base,caso}});
   assert.equal(r.status(),200);
  }
  await page.evaluate(async()=>{abrirAba('grafo');await carregarGrafo();
   grInspecionarNo(grNodes.find(n=>n.valor==='fim-remocao@example.invalid'))});
  page.on('dialog',d=>d.accept());
  const selecionado=await page.locator('#gr-detalhes-conteudo [data-gr-manual]').first().evaluate(b=>{const [i,j]=b.dataset.grManual.split(':').map(Number);const aresta=grEdges.find(e=>e.source.valor==='origem@example.invalid'&&e.target.valor==='fim-remocao@example.invalid');return grFontes(aresta)[j]});
  const req=page.waitForRequest(r=>r.url().endsWith('/api/grafo/vinculo/remover'));
  const res=page.waitForResponse(r=>r.url().endsWith('/api/grafo/vinculo/remover'));
  await page.locator('#gr-detalhes-conteudo button').filter({hasText:'remover'}).first().click();
  const payload=(await req).postDataJSON(), resposta=await res;
  assert.deepEqual(Object.keys(payload).sort(),['caso','id','versao']);
  assert.equal(payload.id,selecionado.manual_id,'Usa a fonte selecionada mesmo ao inspecionar o destino');
  assert.equal(payload.versao,selecionado.manual_versao);
  assert.equal(payload.caso,selecionado.caso);
  assert.ok(['OS-351-2099','OS-352-2099'].includes(payload.caso),'Usa o caso da aresta selecionada');
  assert.equal(resposta.status(),200);
  const g=await (await context.request.get(url+'/api/grafo')).json();
  const restantes=g.arestas.filter(a=>a.relacao===base.relacao);
  assert.equal(restantes.length,1,'Remove apenas o vínculo da O.S. selecionada');
  assert.equal(restantes[0].a_valor,'origem@example.invalid','Direção da relação preservada');
  assert.equal(restantes[0].b_valor,'fim-remocao@example.invalid');
  const fontes=restantes[0].evidencias||[restantes[0]];
  assert.ok(fontes.every(e=>e.caso!==payload.caso),'A fonte da outra O.S. permanece');
''')

    def test_nome_com_apostrofe_preservado_ao_criar_vinculo_do_no(self):
        self.cenario(r'''
  const valor="P:D'Ávila",rotulo="D'Ávila <fictício>";
  const r=await context.request.post(url+'/api/grafo/vinculo',{headers:{'X-CPJ':'1'},
   data:{caso:'OS-351-2099',a_tipo:'PESSOA',a_valor:valor,a_rotulo:rotulo,
    b_tipo:'EMAIL',b_valor:'nome@example.invalid',relacao:'qualificação fictícia'}});
  assert.equal(r.status(),200);
  await page.evaluate(async valor=>{abrirAba('grafo');await carregarGrafo();grInspecionarNo(grNodes.find(n=>n.valor===valor))},valor);
  assert.ok((await page.locator('#gr-detalhes-conteudo').textContent()).includes(rotulo));
  await page.locator('#gr-detalhes-conteudo button').filter({hasText:'+ Criar Vínculo deste Nó'}).click();
  assert.equal(await page.locator('#modal-vinculo').isVisible(),true);
  assert.equal(await page.locator('#f-vinculo [name=a_valor]').inputValue(),valor);
''')


if __name__ == "__main__":
    unittest.main(verbosity=2)
