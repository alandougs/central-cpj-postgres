"""CL02: SQLite e orquestracao reais; somente sessoes IA simuladas."""
import json, os, subprocess, sys, tempfile, threading, time, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import plantao as PL
import executores_llm as EL

class Squad(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='cpj-cl02-')
        self.addCleanup(self.tmp.cleanup)
        self.ws, self.caso = self.tmp.name, 'OS-1-2026'
        self.base = Path(self.ws) / 'casos' / self.caso
        self.pl = PL.Plantao(self.ws)
        self.pl.registrar('Teste', 'simulado', 'auto', aprovado=True)
        self.calls, self.omitir, self.limpa, self.barreira = [], None, False, None
        self.mock = patch.object(PL, '_executar_sessao', side_effect=self.simular)
        self.mock.start(); self.addCleanup(self.mock.stop)
    def gravar(self, rel, texto='ficticio'):
        p = self.base / rel; p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(texto, encoding='utf-8')
    def documento(self, nome, n):
        self.gravar('01-extracao/' + nome + '/transcricao.md', '\n'.join(f'## Página {i}\nFicticio' for i in range(1,n+1)))
    def simular(self, pl, job, nome, tipo):
        e = job['_etapa']; self.calls.append(e['id'])
        if e['tipo'] == 'blocos' and self.barreira: self.barreira.wait(timeout=5)
        if e['tipo'] != self.omitir:
            for saida in e['saidas']:
                texto = 'ficticio'
                if e['tipo'] == 'revisao':
                    texto = 'Resultado: 9 sustentadas · 0 parciais · 0 não localizadas · 0 contraditórias' if self.limpa else 'Resultado: 7 sustentadas · 1 parciais · 1 não localizadas · 0 contraditórias'
                self.gravar(saida, texto)
        return {'resumo': 'simulado', 'log': 'ia-logs/' + e['id'] + '.jsonl'}
    def pedido(self, acao='analisar'):
        self.pl.enfileirar(self.caso, acao, 'teste', consentimento=json.dumps(EL.criar_consentimento('teste',sorted(EL.DESTINOS_EXTERNOS))))
        return self.pl.reivindicar('Teste')
    def executar(self, job):
        r = PL.executar_pedido(self.pl, job, 'Teste', 'simulado')
        self.pl.concluir(job['id'], 'Teste', r)
        return r
    def test_blocos_paralelos_e_cadeia_completa(self):
        self.documento('a',150); self.documento('b',60)
        self.barreira = threading.Barrier(3)
        job = self.pedido('completo'); grupo = job['grupo']
        while job:
            self.executar(job); job = self.pl.reivindicar('Teste')
        ps = sorted((p for p in self.pl.pedidos() if p['grupo']==grupo), key=lambda p:p['ordem'])
        self.assertEqual([p['acao'] for p in ps], ['analisar','financeiro','relatorio','revisar'])
        self.assertTrue(all(p['estado']=='concluida' for p in ps))
        et = self.pl.etapas(ps[0]['id'])
        self.assertEqual([(e['arg']['doc'],e['arg']['ini'],e['arg']['fim']) for e in et[:3]], [('a',1,90),('a',91,150),('b',1,60)])
        self.assertEqual(self.calls[3:], ['financeiro','consolidacao','financeiro','redacao','revisao','ajuste','revisao'])
        for p in ps:
            for e in self.pl.etapas(p['id']):
                self.assertEqual(e['estado'],'concluida')
                self.assertTrue(e['inicio'] and e['fim'] and e['log'])
            self.assertEqual(len(self.pl.como_tarefa(p)['etapas']),len(self.pl.etapas(p['id'])))
    def test_saida_ausente_interrompe_cadeia(self):
        self.documento('ip',40); self.omitir='consolidacao'; job=self.pedido('esteira')
        with self.assertRaisesRegex(RuntimeError,'ficha-caso.md') as erro: self.executar(job)
        self.pl.falhar(job['id'],'Teste',erro.exception)
        self.assertEqual([e['estado'] for e in self.pl.etapas(job['id'])],['concluida','erro'])
        self.assertIsNone(self.pl.reivindicar('Teste'))
        self.assertTrue(all(p['estado'] in ('erro','cancelada') for p in self.pl.pedidos()))
    def test_arquivo_antigo_nao_comprova_entrega(self):
        self.documento('ip',40); self.gravar('02-analise/ficha-caso.md','antigo'); self.gravar('02-analise/pessoas.csv','antigo')
        self.omitir='consolidacao'
        with self.assertRaisesRegex(RuntimeError,'não atualizado'): self.executar(self.pedido())
    def test_retomada_preserva_checkpoint(self):
        self.documento('ip',40); job=self.pedido(); plano=PL.plano_etapas(self.ws,job)
        self.simular(self.pl,dict(job,_etapa=plano[0]),'Teste','simulado')
        plano[0].update(estado='concluida',inicio=PL.agora(),fim=PL.agora(),log='anterior')
        self.pl.gravar_etapas(job['id'],plano); self.calls.clear(); self.executar(job)
        self.assertEqual(self.calls,['consolidacao'])
    def test_retomada_refaz_saida_perdida(self):
        self.documento('ip',40); job=self.pedido(); plano=PL.plano_etapas(self.ws,job); plano[0].update(estado='concluida')
        self.pl.gravar_etapas(job['id'],plano); self.executar(job)
        self.assertEqual(self.calls,['financeiro','consolidacao'])
    def test_revisao_limpa_dispensa_ajuste(self):
        for saida in PL.SAIDAS_CONSOLIDACAO: self.gravar(saida)
        self.gravar('03-relatorios/minuta-v01.md'); self.limpa=True
        job=self.pedido('relatorio'); self.executar(job)
        self.assertEqual(self.calls,['redacao','revisao'])
        self.assertEqual(self.pl.etapas(job['id'])[-1]['estado'],'dispensada')
        self.assertTrue((self.base/'03-relatorios/minuta-v02.md').is_file())
    def test_cancelamento_impede_etapas(self):
        self.documento('ip',40); job=self.pedido(); self.pl.cancelar(job['id'])
        with self.assertRaisesRegex(RuntimeError,'Cancelado'): self.executar(job)
        self.assertEqual(self.calls,[])
    def test_cancelado_nao_pode_concluir(self):
        self.documento('ip',40); job=self.pedido(); self.pl.cancelar(job['id'])
        with self.assertRaisesRegex(ValueError,'cancelado'):
            self.pl.concluir(job['id'],'Teste',{'resumo':'antigo'})
    def test_indexacao_com_erro_impede_conclusao(self):
        with patch.object(PL.subprocess,'run',return_value=subprocess.CompletedProcess([],1,'','falha ficticia')):
            with self.assertRaisesRegex(RuntimeError,'Indexação falhou'):
                PL.pos_processar(self.ws,self.caso,'analisar')
    def test_api_recebe_prompt_etapa(self):
        import executores_llm as EL
        self.mock.stop()
        self.documento('ip',40); job=self.pedido(); recebido=[]
        def api(ws,j,nome,prov,cfg,pl):
            recebido.append(PL.montar_prompt(j,ws,'api',nome)); return self.simular(pl,j,nome,'simulado')
        with patch.object(EL,'executar',side_effect=api), patch.object(EL,'executar_com_fallback',side_effect=lambda ws,prov,fn,dest:fn(prov,{})):
            PL.executar_pedido(self.pl,job,'Teste','openai-api')
        self.assertEqual(len(recebido),2)
        self.assertIn('Analista financeiro',recebido[0]); self.assertIn('Consolidação',recebido[1]); self.assertIn('NÃO são fonte',recebido[1])
    def test_cancelamento_interrompe_processos_blocos(self):
        self.mock.stop(); self.documento('ip',210); job=self.pedido()
        script = "import os,time,json;from pathlib import Path;p=Path(os.environ['CPJ_WORKSPACE'])/('start-'+str(json.loads(os.environ['CPJ_ETAPA_ARG'])['n']));p.write_text('inicio');time.sleep(30);p.with_suffix('.fim').write_text('fim')"
        erros=[]
        def executar():
            try: PL.executar_pedido(self.pl,job,'Teste','simulado')
            except Exception as e: erros.append(str(e))
        with patch.dict(os.environ, {'CPJ_PLANTAO_SIMULADO_CMD':script}):
            th=threading.Thread(target=executar); th.start()
            limite=time.monotonic()+10
            while len(list(Path(self.ws).glob('start-*')))<3 and th.is_alive() and time.monotonic()<limite: time.sleep(.05)
            self.assertEqual(len(list(Path(self.ws).glob('start-*'))),3,erros)
            self.pl.cancelar(job['id']); th.join(12)
            self.assertFalse(th.is_alive()); self.assertTrue(any('Cancelado' in e for e in erros))
            self.assertEqual(list(Path(self.ws).glob('*.fim')),[])
    def test_logs_api_blocos_independentes(self):
        import executores_llm as EL
        self.documento('ip',210); job=self.pedido(); plano=PL.plano_etapas(self.ws,job)
        resposta={'id':'ficticio','output':[{'type':'message','content':[{'type':'output_text','text':'feito'}]}]}
        with patch.object(EL,'_http_json',return_value=resposta), patch.object(EL.time,'time',return_value=1000):
            a=EL.executar(self.ws,dict(job,_etapa=plano[0]),'Teste','openai',{'modelo':'ficticio','chave':'ficticia'},self.pl)
            b=EL.executar(self.ws,dict(job,_etapa=plano[1]),'Teste','openai',{'modelo':'ficticio','chave':'ficticia'},self.pl)
        self.assertNotEqual(a['log'],b['log'])

if __name__=='__main__': unittest.main(verbosity=2)
