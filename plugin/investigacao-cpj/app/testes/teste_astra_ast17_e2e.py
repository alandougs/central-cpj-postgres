"""AST17: HTTP, Node/Edge, extração e DOCX reais; análise fictícia determinística.

Não usa modelos/assinaturas/casos reais nem executores de IA. Evidências ficam em TEMP.
"""
import csv
import hashlib
import io
import json
import os
import platform
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request

APP = Path(__file__).resolve().parents[1]
FIXTURE = Path(__file__).resolve().parent / 'astra_e2e'
RUNTIME = Path.home() / '.cache/codex-runtimes/codex-primary-runtime/dependencies/node'
sys.path.insert(0, str(APP))


class HomologacaoAST17(unittest.TestCase):
    def test_fluxo_integrado_ficticio_node_edge(self):
        from auth import Auth
        from testes.fixtures_docx import criar_modelo
        from testes.e2e.pdf_aux import gerar_pdf_sintetico_e2e
        from pypdf import PdfReader, PdfWriter
        from reportlab.pdfgen import canvas

        self.assertTrue((RUNTIME / 'bin/node.exe').is_file(), 'Node requerido: não ocultar E2E com skip')
        self.ws = Path(tempfile.mkdtemp(prefix='cpj-astra-ast17-e2e-'))
        self.process = None
        self.log = (self.ws / 'servidor.log').open('a', encoding='utf-8')
        model = self.ws / 'casos/_MODELO-CASO'
        model.mkdir(parents=True)
        (model / 'caso.json').write_text(json.dumps({'datas': {}, 'financeiro': {}, 'ip': {}, 'resultado': {}, 'relatorios': []}), encoding='utf-8')
        criar_modelo(self.ws / 'modelos')
        Auth(str(self.ws)).salvar_usuario('ast17', 'Operador fictício AST17', 'admin', 'SenhaFicticia123')
        (self.ws / 'config/solo.json').write_text('{"ativo":true}', encoding='utf-8')
        pdf = self.ws / 'autos-ficticios.pdf'
        gerar_pdf_sintetico_e2e(pdf, paginas_texto=2, paginas_imagem=0)
        # O.S. ao final e resposta bancária explícita, antes do recebimento.
        buffer = io.BytesIO()
        cv = canvas.Canvas(buffer)
        for y, text in enumerate((
            'ORDEM DE SERVICO N. 456/2026 - DOCUMENTO FICTICIO',
            'IPe n. 4562026 / Processo n. 0000001-00.2026.8.26.0000',
            'Dr. Delegado de Policia Titular',
            'Determinacao: Proceder a identificacao do titular da conta recebedora do Pix.',
            'Banco Teste S.A.: titular da conta recebedora do Pix: CARLOS TESTE SANTOS.',
        )):
            cv.drawString(40, 800 - y * 22, text)
        cv.showPage(); cv.save()
        writer = PdfWriter(clone_from=io.BytesIO(pdf.read_bytes()))
        writer.add_page(PdfReader(io.BytesIO(buffer.getvalue())).pages[0])
        with pdf.open('wb') as stream:
            writer.write(stream)
        original_hash = hashlib.sha256(pdf.read_bytes()).hexdigest()
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0)); self.port = sock.getsockname()[1]
        self.env = dict(os.environ, CPJ_WORKSPACE=str(self.ws), CPJ_SEM_AGENTE_EMBUTIDO='1',
                        CPJ_IA_LOCAL_MODELO='', PYTHONIOENCODING='utf-8',
                        APPDATA=str(self.ws / 'appdata-ficticio'), CPJ_NODE_MODULES=str(RUNTIME / 'node_modules'),
                        AST17_WS=str(self.ws), AST17_URL=f'http://127.0.0.1:{self.port}')
        self.env.pop('CPJ_WORKSPACES', None)
        started = time.monotonic()
        source_paths = [APP / p for p in ('servidor.py', 'rotas/comum.py', 'rotas/casos.py', 'rotas/consulta.py',
                        'rotas/relatorios.py', 'grafo_evidencias.py', 'static/js/astra.js', 'static/js/grafo.js',
                        'static/js/editor.js', 'static/js/recebimento.js')]
        source_paths += [Path(__file__).resolve(), FIXTURE/'fluxo.cjs']
        hashes = lambda: {str(p.relative_to(APP)): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in source_paths if p.is_file()}
        initial_hashes = hashes()
        (self.ws / 'fontes-inicio.json').write_text(json.dumps(initial_hashes, indent=2), encoding='utf-8')
        try:
            self.start_server()
            self.node('upload')
            state = json.loads((self.ws / 'estado.json').read_text(encoding='utf-8'))
            cid = state['caso']; case = self.ws / 'casos' / cid
            originals = list((case / '00-originais').glob('*.pdf'))
            self.assertEqual(len(originals), 1)
            self.assertEqual(hashlib.sha256(originals[0].read_bytes()).hexdigest(), original_hash)
            transcription = next((case / '01-extracao').glob('*/transcricao.md'))
            text = transcription.read_text(encoding='utf-8')
            self.assertIn('## Página 3', text)
            self.assertIn('CARLOS TESTE SANTOS', text)
            os_texts = [p.read_text(encoding='utf-8') for p in transcription.parent.glob('ordens-de-servico/*.md')]
            self.assertTrue(any('## Página 3' in t and 'identificacao do titular' in t for t in os_texts),
                            'A O.S. final deve estar transcrita com sua determinação e página')
            self.assertFalse(list(transcription.parent.rglob('*.csv')),
                             'Nova extração documental não gera derivados CSV.')
            self.assertEqual([p.relative_to(transcription.parent).as_posix() for p in transcription.parent.rglob('*.json')],
                             ['.checkpoint/estado.json'], 'Somente o checkpoint essencial pode ser JSON na extração.')
            # Simula somente a saída de um analista, sem afirmar execução da IA.
            analysis = case / '02-analise'; analysis.mkdir(exist_ok=True)
            (analysis / 'solicitacoes-os.md').write_text(
                '# Solicitações da O.S. — fixture de análise simulada\n\n'
                '| Item | Solicitação e fonte | Atendimento |\n|---|---|---|\n'
                '| 1 | Identificar titular recebedor (pág. 3 do PDF; fls. 3) | '
                'Diligências e conclusão: CARLOS TESTE SANTOS, conforme resposta bancária na pág. 3. |\n', encoding='utf-8')
            row = {'seq': '1', 'data': '12/03/2026', 'valor': '5.000,00', 'meio': 'Pix',
                   'origem_banco': 'Banco Teste', 'origem_ag_conta': '0001/100',
                   'destino_banco': 'Banco Teste', 'destino_ag_conta': '0001/200',
                   'origem_titular': 'MARIA TESTE SILVA', 'destino_titular': 'CARLOS TESTE SANTOS',
                   'documento': originals[0].name, 'fonte_pag': '2', 'fls': '2',
                   'trecho': 'PIX TRANSF CARLOS TESTE -5.000,00'}
            with (analysis / 'fluxo-financeiro.csv').open('w', encoding='utf-8', newline='') as stream:
                writer_csv = csv.DictWriter(stream, fieldnames=list(row), delimiter=';')
                writer_csv.writeheader(); writer_csv.writerow(row)
            self.indexar()
            self.node('fontes')
            self.indexar()
            self.stop_server(); self.start_server()
            self.node('relatorio')
            self.assertEqual(hashlib.sha256(originals[0].read_bytes()).hexdigest(), original_hash)
            self.assertTrue((case / '03-relatorios' / f'RELATORIO-{cid}-FINAL.docx').is_file())
            case_data = json.loads((case / 'caso.json').read_text(encoding='utf-8'))
            self.assertEqual(case_data['status'], 'entregue')
            result = {'ok': True, 'caso': cid, 'duracao_s': round(time.monotonic()-started, 3),
                      'ambiente': {'sistema': platform.system(), 'versao': platform.release(),
                                   'python': platform.python_version(), 'arquitetura': platform.machine()},
                      'fontes_inicio': initial_hashes, 'fontes_fim': hashes(),
                      'sha256_original_antes_depois': original_hash,
                      'simulado': ['análise e redação determinísticas; nenhum executor IA',
                                   'asset /static/brasao-pcsp.png substituído por geometria no harness'],
                      'real': ['Edge/HTTP', 'upload', 'extração PDF nativo', 'indexação/reinício',
                               'fontes/ASTRA', 'persistência e remoção manual', 'editor', 'DOCX', 'gate FINAL', 'painel']}
            (self.ws / 'resultado.json').write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
        finally:
            self.stop_server(); self.log.close()
            print(f'AST17 evidências fictícias: {self.ws}', flush=True)

    def start_server(self):
        self.process = subprocess.Popen([sys.executable, '-X', 'utf8', str(APP/'servidor.py'),
            '--workspace', str(self.ws), '--porta', str(self.port), '--somente-local', '--sem-navegador'],
            env=self.env, stdout=self.log, stderr=subprocess.STDOUT)
        end = time.monotonic()+30
        while time.monotonic() < end:
            if self.process.poll() is not None:
                self.fail('Servidor encerrou: ' + (self.ws/'servidor.log').read_text(encoding='utf-8')[-5000:])
            try:
                with urllib.request.urlopen(self.env['AST17_URL']+'/api/sessao', timeout=1) as response:
                    if json.load(response).get('solo'):
                        return
            except OSError:
                time.sleep(.15)
        self.fail('Servidor não iniciou')

    def stop_server(self):
        if self.process is not None:
            self.process.terminate()
            try: self.process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                self.process.kill(); self.process.wait(timeout=5)
            self.process = None

    def indexar(self):
        result = subprocess.run([sys.executable, '-X', 'utf8', str(APP.parent/'skills/base-cpj/scripts/indexar.py')],
                                env=self.env, capture_output=True, text=True, encoding='utf-8', timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)

    def node(self, phase):
        result = subprocess.run([str(RUNTIME/'bin/node.exe'), str(FIXTURE/'fluxo.cjs'), phase],
                                env=self.env, capture_output=True, text=True, encoding='utf-8', timeout=180)
        (self.ws / (phase+'.log')).write_text(result.stdout+result.stderr, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)


if __name__ == '__main__':
    unittest.main(verbosity=2)
