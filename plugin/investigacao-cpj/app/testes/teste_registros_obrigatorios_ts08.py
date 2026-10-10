"""TS08: fila/etapas/CLI subprocesso reais; conteúdo inteiramente fictício."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import plantao as PL

CONS=['02-analise/ficha-caso.md','02-analise/pessoas.csv','02-analise/solicitacoes-os.md','02-analise/dados-faltantes.md']


class RegistrosObrigatorios(unittest.TestCase):
    def preparar(self,acao,target=None,modo=None):
        tmp=tempfile.TemporaryDirectory(prefix='cpj-ts08-');self.addCleanup(tmp.cleanup)
        ws=Path(tmp.name);base=ws/'casos/OS-FAKE-2026';extr=base/'01-extracao/ficticio';extr.mkdir(parents=True)
        (extr/'transcricao.md').write_text('## Página 1\nO.S. FICTÍCIA: identificar titular e registrar limites; todos os dados são fictícios.',encoding='utf-8')
        if acao=='relatorio':
            for rel in CONS+['03-relatorios/minuta-v02.md']:
                p=base/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('registro fictício anterior',encoding='utf-8')
        if target and modo=='antigo':
            p=base/target;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('registro anterior que não será alterado',encoding='utf-8')
        pl=PL.Plantao(str(ws));pl.registrar('Teste','simulado','auto',aprovado=True)
        pl.enfileirar('OS-FAKE-2026',acao,'usuario-ficticio');job=pl.reivindicar('Teste')
        return ws,base,pl,job

    def executar(self,ws,pl,job,target=None,modo=None,etapa_alvo=None):
        original=PL._executar_sessao;calls=[]
        def sessao(p,j,n,t):
            e=j['_etapa'];calls.append(e['id'])
            # Produtos definidos independentemente do plano em teste.
            v=e['arg'].get('proxima',e['arg'].get('versao',3))
            saidas={'financeiro':['02-analise/fluxo-financeiro.md','02-analise/fluxo-financeiro.csv'],'consolidacao':CONS,'redacao':[f'03-relatorios/minuta-v{v:02d}.md',f'03-relatorios/rastreabilidade-v{v:02d}.md'],'revisao':[f'03-relatorios/revisao-v{v:02d}.md'],'ajuste':[f'03-relatorios/minuta-v{v:02d}.md',f'03-relatorios/rastreabilidade-v{v:02d}.md']}[e['tipo']]
            alvo=target if etapa_alvo is None or etapa_alvo==e['tipo'] else None
            revisao='Resultado: 4 sustentadas · '+('0' if getattr(self,'revisao_limpa',True) else '1')+' parciais · 0 não localizadas · 0 contraditórias'
            itens=[(s,'' if s==alvo and modo=='vazio' else revisao if e['tipo']=='revisao' else 'registro fictício conferido; fontes pág. 1/fls. 1; sem lacunas relevantes identificadas') for s in saidas if not(s==alvo and modo in ('ausente','antigo'))]
            script='import json,os;from pathlib import Path;b=Path(os.environ["CPJ_WORKSPACE"])/"casos/OS-FAKE-2026";itens='+repr(itens)+';[( (b/s).parent.mkdir(parents=True,exist_ok=True),(b/s).write_text(txt,encoding="utf-8")) for s,txt in itens];print(json.dumps({"type":"result","subtype":"success","is_error":False,"result":"fictício"}))'
            with patch.dict(os.environ,{'CPJ_PLANTAO_SIMULADO':'1','CPJ_PLANTAO_SIMULADO_CMD':script}):return original(p,j,n,t)
        with patch.object(PL,'_executar_sessao',side_effect=sessao):
            return PL.executar_pedido(pl,job,'Teste','simulado'),calls

    def test_consolidacao_bloqueia_cada_registro_ausente_vazio_ou_antigo(self):
        for target in CONS[2:]:
            for modo in ('ausente','vazio','antigo'):
                with self.subTest(target=target,modo=modo):
                    ws,base,pl,job=self.preparar('analisar',target,modo)
                    with self.assertRaisesRegex(RuntimeError,Path(target).name):self.executar(ws,pl,job,target,modo)
                    etapas=pl.etapas(job['id']);self.assertEqual(etapas[-1]['estado'],'erro');self.assertTrue(etapas[-1]['log'])

    def test_redacao_bloqueia_rastreabilidade_ausente_vazia_ou_antiga_antes_revisao(self):
        target='03-relatorios/rastreabilidade-v03.md'
        for modo in ('ausente','vazio','antigo'):
            with self.subTest(modo=modo):
                ws,base,pl,job=self.preparar('relatorio',target,modo)
                with self.assertRaisesRegex(RuntimeError,'rastreabilidade-v03.md'):self.executar(ws,pl,job,target,modo)
                etapas=pl.etapas(job['id']);self.assertEqual([e['estado'] for e in etapas],['erro','pendente','pendente'])
                self.assertFalse((base/'03-relatorios/revisao-v03.md').exists())

    def test_produtos_completos_concluem_com_versao_e_revisao_independente(self):
        ws,base,pl,job=self.preparar('analisar');self.executar(ws,pl,job)
        for rel in CONS:self.assertTrue((base/rel).stat().st_size)
        pl.concluir(job['id'],'Teste',{'resumo':'análise fictícia concluída'})
        (base/'03-relatorios').mkdir(exist_ok=True);(base/'03-relatorios/minuta-v02.md').write_text('versão anterior',encoding='utf-8')
        pl.enfileirar('OS-FAKE-2026','relatorio','usuario-ficticio');job=pl.reivindicar('Teste')
        res,calls=self.executar(ws,pl,job);self.assertEqual(calls,['redacao','revisao'])
        self.assertTrue((base/'03-relatorios/rastreabilidade-v03.md').stat().st_size)
        self.assertFalse((base/'03-relatorios/rastreabilidade-v01.md').exists());self.assertEqual(pl.etapas(job['id'])[-1]['estado'],'dispensada')

    def test_prompt_informa_conteudo_sem_inventar_lacunas_e_fontes_por_versao(self):
        ws,base,pl,job=self.preparar('analisar');e=PL.plano_etapas(str(ws),job)[-1];p=PL.prompt_etapa(job,str(ws),e)
        for termo in ('solicitacoes-os.md','dados-faltantes.md','trecho','onde','não houver','não invente'):self.assertIn(termo,p)
        ws,base,pl,job=self.preparar('relatorio');e=PL.plano_etapas(str(ws),job)[0];p=PL.prompt_etapa(job,str(ws),e)
        for termo in ('rastreabilidade-v03.md','afirmação','fonte','página','fls.','NÃO revise'):self.assertIn(termo,p)

    def test_ficha_isolada_nao_permite_pular_registros_na_redacao(self):
        ws,base,pl,job=self.preparar('relatorio');(base/'02-analise/solicitacoes-os.md').unlink()
        self.assertIn('consolidacao',[e['tipo'] for e in PL.plano_etapas(str(ws),job)])

    def test_ajuste_bloqueia_rastreabilidade_antiga_da_mesma_versao(self):
        ws,base,pl,job=self.preparar('relatorio');self.revisao_limpa=False
        with self.assertRaisesRegex(RuntimeError,'rastreabilidade-v03.md'):
            self.executar(ws,pl,job,'03-relatorios/rastreabilidade-v03.md','antigo','ajuste')
        self.assertEqual([e['estado'] for e in pl.etapas(job['id'])],['concluida','concluida','erro'])

    def test_retomada_de_checkpoint_antigo_exige_registros_sem_trocar_versao(self):
        ws,base,pl,job=self.preparar('relatorio')
        plano=PL.plano_etapas(str(ws),job)
        for e in plano:
            if e['tipo']=='redacao':
                e['saidas']=[s for s in e['saidas'] if 'rastreabilidade' not in s]
                e.update(estado='concluida',log='anterior')
                (base/'03-relatorios/minuta-v03.md').write_text('minuta antiga',encoding='utf-8')
        pl.gravar_etapas(job['id'],plano)
        self.executar(ws,pl,job)
        self.assertTrue((base/'03-relatorios/rastreabilidade-v03.md').stat().st_size)
        self.assertFalse((base/'03-relatorios/minuta-v04.md').exists())

    def test_retomada_de_relatorio_sem_registros_refaz_consolidacao(self):
        ws,base,pl,job=self.preparar('relatorio');plano=PL.plano_etapas(str(ws),job)
        pl.gravar_etapas(job['id'],plano)
        (base/'02-analise/solicitacoes-os.md').unlink()
        self.executar(ws,pl,job)
        self.assertTrue((base/'02-analise/solicitacoes-os.md').is_file())
        self.assertEqual(pl.etapas(job['id'])[1]['tipo'],'consolidacao')
        self.assertTrue((base/'03-relatorios/minuta-v03.md').is_file())
        self.assertFalse((base/'03-relatorios/minuta-v04.md').exists())


if __name__=='__main__':unittest.main(verbosity=2)
