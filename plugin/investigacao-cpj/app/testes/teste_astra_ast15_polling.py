"""AST15: controlador real com relógio e I/O determinísticos, sem navegador/casos reais."""
from pathlib import Path
import subprocess
import unittest

APP=Path(__file__).resolve().parents[1]
NODE=Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'

class Polling(unittest.TestCase):
    def run_case(self,name):
        r=subprocess.run([str(NODE),str(Path(__file__).with_name('astra_polling')/'scheduler.cjs'),str(APP/'static/js/polling.js'),name],capture_output=True,text=True,encoding='utf-8',timeout=15)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
    def test_repouso_ativo_e_fila_ocr(self):self.run_case('intervalos')
    def test_promessa_compartilhada_sem_sobreposicao(self):self.run_case('compartilhar')
    def test_erro_backoff_teto_e_recuperacao(self):self.run_case('erros')
    def test_oculta_retorno_e_sessao(self):self.run_case('visibilidade')
    def test_timeout_de_leitura_e_nenhum_retry_post(self):self.run_case('timeout')

    def test_resposta_antiga_nao_reutiliza_sessao(self):self.run_case('sessao')
    def test_sem_progresso_apenas_observacao_e_retomada(self):self.run_case('etapa')

if __name__=='__main__':unittest.main(verbosity=2)
