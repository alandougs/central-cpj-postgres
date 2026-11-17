"""RP31: vínculos de fontes no inspetor, Edge real e arquivos apenas TEMP."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from teste_interface_rg26 import InterfaceFixtureRG26


class FontesMapaRP31(InterfaceFixtureRG26):
    def test_fonte_recusa_caso_divergente_e_caminho_que_troca_o_contexto(self):
        self.cenario(r'''
  await page.evaluate(()=>{
   const div=document.createElement('div');div.id='mapa-inspetor-conteudo';document.body.append(div);
  });
  for(const fonte of [
   {caso:'OS-932-2099',arquivo:'00-originais/autos.pdf'},
   {arquivo:'../OS-932-2099/00-originais/autos.pdf'},
   {arquivo:'/casos/OS-932-2099/00-originais/autos.pdf'},
   {arquivo:'C:\\casos\\OS-932-2099\\00-originais\\autos.pdf'},
   {arquivo:'casos/OS-931-2099/../OS-932-2099/00-originais/autos.pdf'}]){
   await page.evaluate(fonte=>CPJInteligenciaMapa.inspecionarRegistroMapa({caso:'OS-931-2099',
    nome:'Pessoa fictícia',fonte}),fonte);
   assert.equal(await page.locator('#b-insp-fonte').getAttribute('href'),null,JSON.stringify(fonte));
   assert.equal(await page.locator('#b-insp-fonte').isDisabled(),true);
  }
''')

    def test_pagina_pdf_requer_inteiro_positivo_sem_inferir_folhas(self):
        self.cenario(r'''
  await page.evaluate(()=>{
   const div=document.createElement('div');div.id='mapa-inspetor-conteudo';document.body.append(div);
  });
  for(const pagina of [-1,0,1.5,'fls. 30','2#page=30',true]){
   await page.evaluate(pagina=>CPJInteligenciaMapa.inspecionarRegistroMapa({caso:'OS-931-2099',
    nome:'Pessoa fictícia',fonte:{arquivo:'00-originais/autos.pdf',pagina,fls:'30'}}),pagina);
   assert.equal(await page.locator('#b-insp-fonte').getAttribute('href'),
    '/arquivo/OS-931-2099/00-originais/autos.pdf',JSON.stringify(pagina));
  }
  await page.evaluate(()=>CPJInteligenciaMapa.inspecionarRegistroMapa({caso:'OS-931-2099',
   nome:'Pessoa fictícia',fonte:{arquivo:'01-extracao/autos/transcricao.md',pagina:2,fls:'30'}}));
  assert.equal(await page.locator('#b-insp-fonte').getAttribute('href'),
   '/arquivo/OS-931-2099/01-extracao/autos/transcricao.md');
''')

    def test_fonte_de_outro_caso_nao_abre_homonimo_do_caso_atual(self):
        # Regressão: remover o prefixo de outro caso cria uma fonte falsa em A.
        for caso, marcador in (("OS-931-2099", b"FONTE_A"), ("OS-932-2099", b"FONTE_B")):
            arq = self.ws / "casos" / caso / "00-originais" / "autos.pdf"
            arq.parent.mkdir(parents=True, exist_ok=True)
            arq.write_bytes(b"%PDF-1.4\n" + marcador)
        self.cenario(r'''
  await page.evaluate(()=>{
   if(!document.getElementById('mapa-inspetor-conteudo')){
    const div=document.createElement('div');div.id='mapa-inspetor-conteudo';document.body.append(div);
   }
   CPJInteligenciaMapa.inspecionarRegistroMapa({caso:'OS-931-2099',nome:'Pessoa fictícia',
    fonte:{caso:'OS-931-2099',arquivo:'casos/OS-932-2099/00-originais/autos.pdf',pagina:2}});
  });
  const link=await page.locator('#b-insp-fonte').getAttribute('href');
  if(link){
   const r=await context.request.get(url+link);
   assert.equal(r.status(),200);
   assert.ok((await r.text()).includes('FONTE_A'),'Fixture demonstra leitura do homônimo A');
  }
  assert.equal(link,null,'Fonte de B não pode ser remapeada silenciosamente para A');
  assert.equal(await page.locator('#b-insp-fonte').isDisabled(),true);
''')

    def test_fonte_valida_preserva_caso_arquivo_pagina_e_bytes(self):
        nome = "Peça fictícia & 1.pdf"
        arq = self.ws / "casos" / "OS-931-2099" / "00-originais" / nome
        arq.parent.mkdir(parents=True, exist_ok=True)
        original = b"%PDF-1.4\nFONTE_CORRETA\n"
        arq.write_bytes(original)
        self.cenario(r'''
  await page.evaluate(()=>{
   if(!document.getElementById('mapa-inspetor-conteudo')){
    const div=document.createElement('div');div.id='mapa-inspetor-conteudo';document.body.append(div);
   }
  });
  for(const arquivo of ['casos/OS-931-2099/00-originais/Peça fictícia & 1.pdf',
                        'casos\\OS-931-2099\\00-originais\\Peça fictícia & 1.pdf',
                        '00-originais/Peça fictícia & 1.pdf']){
   await page.evaluate(arquivo=>CPJInteligenciaMapa.inspecionarRegistroMapa({caso:'OS-931-2099',
    nome:'Pessoa fictícia',fonte:{caso:'OS-931-2099',arquivo,pagina:2}}),arquivo);
   const href=await page.locator('#b-insp-fonte').getAttribute('href');
   assert.equal(href,'/arquivo/OS-931-2099/00-originais/Pe%C3%A7a%20fict%C3%ADcia%20%26%201.pdf#page=2');
   const r=await context.request.get(url+href);
   assert.equal(r.status(),200);
   assert.equal(await r.text(),'%PDF-1.4\nFONTE_CORRETA\n');
  }
''')
        self.assertEqual(arq.read_bytes(), original)


if __name__ == "__main__":
    unittest.main(verbosity=2)
