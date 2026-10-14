"""AR01: O.S. em MD com fonte e páginas, sem dados reais ou chamadas externas."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[4]
SCRIPTS=ROOT/'plugin/investigacao-cpj/skills/pdf-autos-policiais/scripts'
sys.path.insert(0,str(SCRIPTS))
sys.path.insert(0,str(ROOT/'plugin/investigacao-cpj/app'))


class OrdensMD(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='cpj-ar01-os-')
        self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name)
        self.pasta=self.base/'casos/OS-901-2099/01-extracao/autos-ficticios'
        self.pasta.mkdir(parents=True)

    def modulo(self):
        self.assertTrue((SCRIPTS/'ordens_servico.py').is_file(), 'Extração automática de O.S. ainda ausente')
        import ordens_servico
        return ordens_servico

    def escrever(self,texto):
        p=self.pasta/'transcricao.md'
        p.write_text(texto,encoding='utf-8')
        return p

    def test_preserva_ordem_nas_paginas_finais_e_ignora_mencao(self):
        trans=self.escrever('## Página 1\nA vítima menciona uma ordem de serviço antiga.\n\n## Página 298\nORDEM DE SERVIÇO Nº 901/2099\nData: 14/10/2099\na) Identificar o destinatário.\nb) Conferir os R$ 123,45.\n')
        sha=hashlib.sha256(trans.read_bytes()).hexdigest()
        info=self.modulo().extrair_ordens(self.pasta)
        self.assertEqual([o['paginas'] for o in info['ordens']],[[298]])
        md=(self.pasta/info['ordens'][0]['arquivo']).read_text(encoding='utf-8')
        self.assertIn('a) Identificar o destinatário.\nb) Conferir os R$ 123,45.',md)
        self.assertIn('## Página 298',md)
        self.assertIn(sha,md)
        self.assertEqual(hashlib.sha256(trans.read_bytes()).hexdigest(),sha)
        self.assertEqual(json.loads((self.pasta/'ordens-de-servico/indice.json').read_text(encoding='utf-8')),info)

    def test_multiplas_os_ultimas_paginas_primeiro_sem_presumir_vigencia(self):
        self.escrever('## Página 2\nORDEM DE SERVICO Nº 900/2099\nData: 15/10/2099\na) Primeira determinação.\n## Página 99\nORDEM DE SERVIÇO NÚMERO 901/2099\nData: 14/10/2099\na) Outra determinação.\n')
        info=self.modulo().extrair_ordens(self.pasta)
        self.assertEqual([o['paginas'] for o in info['ordens']],[[99],[2]])
        self.assertIsNone(info['vigente'])

    def test_continuacao_preservada_sem_incluir_despacho_seguinte(self):
        self.escrever('## Página 9\nORDEM DE SERVIÇO Nº 901/2099\na) Identificar a conta.\n## Página 10\nb) Apurar a destinação.\nc) Esclarecer a divergência.\n## Página 11\nDESPACHO\nConclusão ao delegado.\n')
        info=self.modulo().extrair_ordens(self.pasta)
        self.assertEqual(info['ordens'][0]['paginas'],[9,10])
        md=(self.pasta/info['ordens'][0]['arquivo']).read_text(encoding='utf-8')
        self.assertIn('c) Esclarecer a divergência.',md)
        self.assertNotIn('Conclusão ao delegado.',md)

    def test_ausencia_registrada_sem_fabricar_ordem(self):
        self.escrever('## Página 1\nTermo de declarações. Cumprir ordem de serviço não identificada.\n')
        info=self.modulo().extrair_ordens(self.pasta)
        self.assertEqual(info['ordens'],[])
        self.assertEqual(info['situacao'],'nao_localizada')
        self.assertEqual(list((self.pasta/'ordens-de-servico').glob('*.md')),[])

    def test_cabecalho_quebrado_em_linhas_e_primeiro_item_na_continuacao(self):
        self.escrever('## Página 8\nORDEM\nDE\nSERVIÇO\nNº 901/2099\nDetermino o seguinte:\n## Página 9\na) Identificar o destinatário.\nb) Conferir os comprovantes.\n')
        info=self.modulo().extrair_ordens(self.pasta)
        self.assertEqual([o['paginas'] for o in info['ordens']],[[8,9]])

    def test_md_sem_paginacao_nao_inventa_numero_de_pagina(self):
        self.escrever('ORDEM DE SERVIÇO Nº 901/2099\na) Conferir os comprovantes.\n')
        info=self.modulo().extrair_ordens(self.pasta)
        self.assertEqual(info['ordens'][0]['paginas'],[None])
        md=(self.pasta/info['ordens'][0]['arquivo']).read_text(encoding='utf-8')
        self.assertIn('Página não informada',md)

    def test_importacao_md_e_reprocessamento_atualizam_indice_sem_usar_versao_antiga(self):
        self.escrever('## Página 1\nORDEM DE SERVIÇO Nº 901/2099\na) Item antigo.\n')
        env=dict(os.environ,CPJ_WORKSPACE=str(self.base))
        for pedido in ('Item antigo','Item atualizado'):
            self.escrever(f'## Página 1\nORDEM DE SERVIÇO Nº 901/2099\na) {pedido}.\n')
            r=subprocess.run([sys.executable,'-X','utf8',str(SCRIPTS/'dados_json.py'),str(self.pasta)],env=env,capture_output=True,text=True,encoding='utf-8')
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            dados=json.loads((self.pasta/'dados_extraidos.json').read_text(encoding='utf-8'))
            self.assertIn('ordens_servico',dados)
            ordem=dados['ordens_servico']['ordens'][0]
            md=(self.pasta/ordem['arquivo']).read_text(encoding='utf-8')
            self.assertIn(pedido,md)

    def test_cli_pdf_ja_entrega_md_separado_e_preserva_original(self):
        from reportlab.pdfgen import canvas
        pdf=self.base/'autos-ficticios.pdf'
        c=canvas.Canvas(str(pdf))
        for n in range(1,7):
            lines=(['ORDEM DE SERVICO NUMERO 901/2099','a) Identificar o destinatario.','b) Conferir o valor de R$ 123,45.'] if n==6 else ['Documento ficticio para teste local. '*7]*4)
            for i,line in enumerate(lines): c.drawString(50,780-i*25,line)
            c.showPage()
        c.save()
        sha=hashlib.sha256(pdf.read_bytes()).hexdigest()
        r=subprocess.run([sys.executable,'-X','utf8',str(SCRIPTS/'extrair.py'),str(pdf),'--saida',str(self.pasta),'--sem-reaproveitar'],env=dict(os.environ,CPJ_WORKSPACE=str(self.base)),capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        indice=self.pasta/'ordens-de-servico/indice.json'
        self.assertTrue(indice.is_file(),'CLI extrai texto, mas não separa a O.S.')
        info=json.loads(indice.read_text(encoding='utf-8'))
        self.assertEqual(info['ordens'][0]['paginas'],[6])
        self.assertEqual(hashlib.sha256(pdf.read_bytes()).hexdigest(),sha)

    def test_prompts_de_consolidacao_redacao_e_revisao_apontam_os_transcrita(self):
        self.escrever('## Página 298\nORDEM DE SERVIÇO Nº 901/2099\na) Identificar o destinatário.\n')
        import plantao
        job={'id':'ia-ficticio','caso':'OS-901-2099','acao':'relatorio','observacoes':'','solicitante':'ficticio'}
        for tipo,arg in (('consolidacao',{}),('redacao',{'proxima':1}),('revisao',{'versao':1})):
            with self.subTest(tipo=tipo):
                prompt=plantao.prompt_etapa(job,str(self.base),{'tipo':tipo,'arg':arg,'etapa':tipo,'saidas':[]})
                self.assertIn('ordens-de-servico/',prompt)
                self.assertIn('298',prompt)
                self.assertIn('cada solicitação',prompt)


if __name__=='__main__': unittest.main(verbosity=2)
