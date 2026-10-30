"""MD01: PDFs fictícios; saídas analíticas Markdown e checkpoint essencial único."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject

SCRIPTS = Path(__file__).resolve().parents[2] / 'skills/pdf-autos-policiais/scripts'
sys.path.insert(0, str(SCRIPTS))
import transcrever_visual as visual
import estado_extracao as estado


class ExtracaoMarkdown(unittest.TestCase):
    def preparar_retomada_ficticia(self, raiz):
        pdf = raiz / 'ficticio.pdf'
        w = PdfWriter()
        for _ in range(2):
            w.add_blank_page(width=200, height=250)
        w.write(pdf)
        saida = raiz / 'extracao'
        cmd = [sys.executable, '-B', '-X', 'utf8', str(SCRIPTS / 'extrair.py'), str(pdf), '--saida', str(saida), '--ocr', 'visao']
        env = dict(os.environ, CPJ_WORKSPACE=str(raiz), CPJ_WORKSPACES=str(raiz), PYTHONDONTWRITEBYTECODE='1')
        primeira = subprocess.run(cmd, env=env, capture_output=True, text=True, encoding='utf-8', timeout=30)
        self.assertEqual(primeira.returncode, 0, primeira.stdout + primeira.stderr)
        return pdf, saida, cmd, env

    def test_retomada_recusa_placeholder_sobre_markdown_preenchido_sem_alterar_estado(self):
        for metodo in ('ocr-windows-local', 'transcricao-visual-llm'):
            for legado in (False, True):
                with self.subTest(metodo=metodo, legado=legado), tempfile.TemporaryDirectory(prefix='cpj-md02-') as temp:
                    pdf, saida, cmd, env = self.preparar_retomada_ficticia(Path(temp))
                    md = saida / 'transcricao.md'
                    trecho = '## Página 2\n<!-- método: pendente-transcricao-visual -->\n\n[PENDENTE: transcrição visual]'
                    md.write_text(md.read_text(encoding='utf-8').replace(trecho, f'## Página 2\n<!-- método: {metodo} | ⚠ CONFERIR -->\n\nTexto fictício acrescentado localmente; exige conferência no original.'), encoding='utf-8')
                    if legado:
                        dados = json.loads(estado.arquivo(saida).read_text(encoding='utf-8'))
                        (saida / '.checkpoint/meta.json').write_text(json.dumps(dados['meta']), encoding='utf-8')
                        for numero, registro in dados['paginas'].items():
                            (saida / f'.checkpoint/p{int(numero):04d}.json').write_text(json.dumps(registro), encoding='utf-8')
                        estado.arquivo(saida).unlink()
                    protegidos = {p: p.read_bytes() for p in saida.rglob('*') if p.is_file()}
                    original = pdf.read_bytes()
                    resultado = subprocess.run(cmd, env=env, capture_output=True, text=True, encoding='utf-8', timeout=30)
                    self.assertEqual(md.read_bytes(), protegidos[md], 'Retomada perdeu o texto local ao reconstruir o Markdown de um checkpoint desatualizado.')
                    self.assertNotEqual(resultado.returncode, 0, resultado.stdout + resultado.stderr)
                    self.assertIn('transcricao.md', resultado.stderr)
                    self.assertIn('2', resultado.stderr)
                    self.assertIn('--refazer', resultado.stderr)
                    self.assertEqual({p: p.read_bytes() for p in saida.rglob('*') if p.is_file()}, protegidos)
                    self.assertEqual(pdf.read_bytes(), original)

    def test_retomada_importa_transcricao_visual_legitima_sobre_placeholder(self):
        with tempfile.TemporaryDirectory(prefix='cpj-md02-visual-') as temp:
            _, saida, cmd, env = self.preparar_retomada_ficticia(Path(temp))
            md = saida / 'transcricao.md'
            md.write_text(md.read_text(encoding='utf-8').replace('[PENDENTE: transcrição visual]', 'Transcrição fictícia local a conferir.'), encoding='utf-8')
            texto = 'Transcrição visual fictícia fornecida pelo fluxo autorizado; conferir no original.'
            for numero in (1, 2):
                (saida / f'transcricoes_visuais/p{numero:04d}.md').write_text(texto, encoding='utf-8')
            resultado = subprocess.run(cmd, env=env, capture_output=True, text=True, encoding='utf-8', timeout=30)
            self.assertEqual(resultado.returncode, 0, resultado.stdout + resultado.stderr)
            self.assertEqual(json.loads(resultado.stdout)['metodos'], {'transcricao-visual-llm': 2})
            self.assertEqual(md.read_text(encoding='utf-8').count(texto), 2)
            self.assertNotIn('[PENDENTE:', md.read_text(encoding='utf-8'))

    def test_transcricao_visual_vazia_ou_pendente_nao_libera_perda_do_markdown(self):
        for visual_pendente, encoding in (('', 'utf-8'), ('[PENDENTE: transcrição visual]', 'utf-8'), ('[PENDENTE: transcrição visual]', 'utf-8-sig')):
            with self.subTest(visual_pendente=visual_pendente, encoding=encoding), tempfile.TemporaryDirectory(prefix='cpj-md02-tv-pendente-') as temp:
                _, saida, cmd, env = self.preparar_retomada_ficticia(Path(temp))
                md = saida / 'transcricao.md'
                md.write_text(md.read_text(encoding='utf-8').replace('[PENDENTE: transcrição visual]', 'X', 1), encoding='utf-8')
                (saida / 'transcricoes_visuais/p0001.md').write_text(visual_pendente, encoding=encoding)
                antes = {p: p.read_bytes() for p in saida.rglob('*') if p.is_file()}
                resultado = subprocess.run(cmd, env=env, capture_output=True, text=True, encoding='utf-8', timeout=30)
                self.assertNotEqual(resultado.returncode, 0, resultado.stdout + resultado.stderr)
                self.assertEqual({p: p.read_bytes() for p in saida.rglob('*') if p.is_file()}, antes)

    def test_tv_placeholder_com_ou_sem_bom_mantem_pagina_originalmente_pendente(self):
        for encoding in ('utf-8', 'utf-8-sig'):
            with self.subTest(encoding=encoding), tempfile.TemporaryDirectory(prefix='cpj-md02-tv-bom-') as temp:
                _, saida, cmd, env = self.preparar_retomada_ficticia(Path(temp))
                (saida / 'transcricoes_visuais/p0001.md').write_text('[PENDENTE: transcrição visual]', encoding=encoding)
                resultado = subprocess.run(cmd, env=env, capture_output=True, text=True, encoding='utf-8', timeout=30)
                self.assertEqual(resultado.returncode, 0, resultado.stdout + resultado.stderr)
                self.assertEqual(json.loads(resultado.stdout)['pendentes_transcricao_visual'], [1, 2])
                self.assertEqual(estado.ler(saida, '.checkpoint/p0001.json')['reg']['metodo'], 'pendente-transcricao-visual')
                self.assertEqual(estado.ler(saida, '.checkpoint/p0001.json')['flag'], 'pendente')

    def test_tv_bom_legitima_incorpora_texto_sem_caractere_bom(self):
        with tempfile.TemporaryDirectory(prefix='cpj-md02-tv-bom-texto-') as temp:
            _, saida, cmd, env = self.preparar_retomada_ficticia(Path(temp))
            md = saida / 'transcricao.md'
            md.write_text(md.read_text(encoding='utf-8').replace('[PENDENTE: transcrição visual]', 'Texto local fictício a conferir.', 1), encoding='utf-8')
            texto = 'Transcrição visual fictícia com BOM; conferir no original.'
            (saida / 'transcricoes_visuais/p0001.md').write_text(texto, encoding='utf-8-sig')
            resultado = subprocess.run(cmd, env=env, capture_output=True, text=True, encoding='utf-8', timeout=30)
            self.assertEqual(resultado.returncode, 0, resultado.stdout + resultado.stderr)
            self.assertEqual(json.loads(resultado.stdout)['pendentes_transcricao_visual'], [2])
            self.assertEqual(estado.ler(saida, '.checkpoint/p0001.json')['reg']['texto'], texto)
            self.assertIn(texto, md.read_text(encoding='utf-8'))
            self.assertNotIn('\ufeff', md.read_text(encoding='utf-8'))

    def test_refazer_explicito_permite_substituir_markdown_local(self):
        with tempfile.TemporaryDirectory(prefix='cpj-md02-refazer-') as temp:
            _, saida, cmd, env = self.preparar_retomada_ficticia(Path(temp))
            md = saida / 'transcricao.md'
            md.write_text(md.read_text(encoding='utf-8').replace('[PENDENTE: transcrição visual]', 'Transcrição fictícia local a conferir.'), encoding='utf-8')
            resultado = subprocess.run([*cmd, '--refazer'], env=env, capture_output=True, text=True, encoding='utf-8', timeout=30)
            self.assertEqual(resultado.returncode, 0, resultado.stdout + resultado.stderr)
            self.assertEqual(json.loads(resultado.stdout)['paginas_reaproveitadas'], 0)
            self.assertEqual(md.read_text(encoding='utf-8').count('[PENDENTE: transcrição visual]'), 2)

    def test_retomada_checkpoint_invalido_ainda_reprocessa_pagina(self):
        with tempfile.TemporaryDirectory(prefix='cpj-md02-invalido-') as temp:
            _, saida, cmd, env = self.preparar_retomada_ficticia(Path(temp))
            dados = json.loads(estado.arquivo(saida).read_text(encoding='utf-8'))
            dados['paginas']['1'] = {'reg': None, 'flag': 'pendente'}
            estado.gravar(saida, dados)
            resultado = subprocess.run(cmd, env=env, capture_output=True, text=True, encoding='utf-8', timeout=30)
            self.assertEqual(resultado.returncode, 0, resultado.stdout + resultado.stderr)
            self.assertEqual(json.loads(resultado.stdout)['paginas_reaproveitadas'], 1)
            self.assertEqual(estado.ler(saida, '.checkpoint/p0001.json')['reg']['texto'], '[PENDENTE: transcrição visual]')

    @unittest.skipUnless(os.name == 'nt', 'Requer junction nativa Windows.')
    def test_compactar_recusa_junction_interna_antes_gravar_estado(self):
        with tempfile.TemporaryDirectory(prefix='cpj-md01-junction-') as temp:
            pasta = Path(temp)
            alvo = pasta / 'interno'
            alvo.mkdir()
            meta = {'versao': 2, 'sha256': 'b' * 64}
            (alvo / 'meta.json').write_text(json.dumps(meta))
            (alvo / 'p0001.json').write_text(json.dumps({'reg': {'pagina': 1, 'texto': 'fictício'}}))
            (pasta / 'relatorio_extracao.json').write_text(json.dumps({'paginas': 1, 'sha256_original': 'b' * 64}))
            r = subprocess.run(['cmd', '/c', 'mklink', '/J', str(pasta / '.checkpoint'), str(alvo)], capture_output=True)
            self.assertEqual(r.returncode, 0, 'Fixture não criou junction nativa.')
            resultado = estado.compactar_legado(pasta)
            self.assertFalse(resultado['compactado'])
            self.assertEqual(resultado['cobertos'], [])
            self.assertFalse((alvo / 'estado.json').exists())

    def test_compactar_legado_preserva_arquivos_e_nao_cobre_dados_divergentes(self):
        with tempfile.TemporaryDirectory(prefix='cpj-md01-legado-') as temp:
            pasta = Path(temp)
            (pasta / '.checkpoint').mkdir()
            dados = {
                '.checkpoint/meta.json': {'versao': 2, 'sha256': 'a' * 64},
                '.checkpoint/p0001.json': {'reg': {'pagina': 1, 'metodo': 'texto-nativo', 'texto': 'Texto fictício'}, 'flag': None},
                'relatorio_extracao.json': {'arquivo': 'autos.pdf', 'paginas': 1, 'sha256_original': 'a' * 64},
                'qualidade.json': {'1': {'precisa_ia': False}},
            }
            for nome, valor in dados.items():
                (pasta / nome).write_text(json.dumps(valor), encoding='utf-8')
            antes = {nome: (pasta / nome).read_bytes() for nome in dados}
            leituras_estado = []
            ler_texto = Path.read_text
            def contar_leitura(arquivo, *args, **kwargs):
                if arquivo == estado.arquivo(pasta):
                    leituras_estado.append(arquivo)
                return ler_texto(arquivo, *args, **kwargs)
            with patch.object(Path, 'read_text', contar_leitura):
                resultado = estado.compactar_legado(pasta)
            self.assertEqual(len(leituras_estado), 1, 'Verificação deve reler o estado uma única vez por documento, sem I/O quadrático.')
            self.assertTrue(resultado['compactado'])
            self.assertEqual(set(resultado['cobertos']), set(dados))
            for nome, valor in dados.items():
                self.assertEqual(estado.ler(pasta, nome), valor)
                self.assertEqual((pasta / nome).read_bytes(), antes[nome])
            (pasta / 'qualidade.json').write_text('{"1":{"precisa_ia":true}}')
            self.assertNotIn('qualidade.json', estado.compactar_legado(pasta)['cobertos'])

    def test_compactar_nao_cobre_checkpoint_antigo_sem_hash(self):
        with tempfile.TemporaryDirectory(prefix='cpj-md01-meta1-') as temp:
            pasta = Path(temp)
            (pasta / '.checkpoint').mkdir()
            antigo = pasta / '.checkpoint/meta.json'
            antigo.write_text('{"versao":1}')
            resultado = estado.compactar_legado(pasta)
            self.assertFalse(resultado['compactado'])
            self.assertEqual(resultado['cobertos'], [])
            self.assertTrue(antigo.exists())
            self.assertFalse(estado.arquivo(pasta).exists())

    def test_central_pdf_nao_recria_csv_ou_json_analiticos(self):
        with tempfile.TemporaryDirectory(prefix='cpj-md01-central-') as temp:
            codigo = '''
import json, os, sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, sys.argv[1])
from app.servidor import app
from rotas import comum
C = comum.C
raiz = Path(os.environ['CPJ_WORKSPACE'])
modelo = raiz / 'casos/_MODELO-CASO'
for nome in ('00-originais', '01-extracao', '02-analise', '03-relatorios'):
    (modelo / nome).mkdir(parents=True)
(modelo / 'caso.json').write_text(json.dumps({'datas': {}}))
C.novo('999/2099', '', '', '', '', id_='OS-999-2099')
pdf = Path(C.caminho('OS-999-2099')) / '00-originais/autos.pdf'
from pypdf import PdfWriter
w = PdfWriter(); w.add_blank_page(width=600, height=800); w.write(pdf)
comum.gravar_proc('OS-999-2099', {'trabalhos': [{'doc': 'autos', 'arquivo': 'autos.pdf', 'status': 'na_fila'}]})
with patch.object(comum, 'idioma_ocr', return_value='idioma-inexistente'), patch.object(comum.D_OS, 'aplicar'):
    comum.processar({'caso': 'OS-999-2099', 'doc': 'autos', 'arquivo': 'autos.pdf', 'modo': 'inteligente'})
t = comum.ler_proc('OS-999-2099')['trabalhos'][0]
assert t['status'] == 'concluido', t
assert 'OCR indisponível' in t['limitacao'], t
assert C.carregar('OS-999-2099')['documentos'][0]['pendentes'] == 1
extracao = pdf.parent.parent / '01-extracao/autos'
assert not list(extracao.rglob('*.csv'))
assert [p.relative_to(extracao).as_posix() for p in extracao.rglob('*.json')] == ['.checkpoint/estado.json']
assert (extracao / 'transcricao.md').exists()
C.importar_ip('OS-999-2099', str(extracao / '.checkpoint/estado.json'))
d = C.carregar('OS-999-2099')['documentos'][0]
assert d['arquivo'] == 'autos.pdf' and d['pasta'] == 'autos' and d['pendentes'] == 1, d
'''
            env = dict(os.environ, CPJ_WORKSPACE=temp, PYTHONDONTWRITEBYTECODE='1')
            r = subprocess.run([sys.executable, '-X', 'utf8', '-c', codigo, str(SCRIPTS.parents[2])], env=env, capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_pdf_markdown_retomada_e_pendencia_visual_sem_derivados(self):
        with tempfile.TemporaryDirectory(prefix='cpj-md01-') as temp:
            raiz = Path(temp)
            pdf = raiz / 'ficticio.pdf'
            w = PdfWriter()
            page = w.add_blank_page(width=600, height=800)
            font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
            page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): w._add_object(font)})})
            stream = DecodedStreamObject()
            stream.set_data(b'BT /F1 12 Tf 60 760 Td (ORDEM DE SERVICO 999/2099) Tj 0 -30 Td (Determino conferir os documentos ficticios e seus valores na fonte original.) Tj ET')
            page[NameObject('/Contents')] = w._add_object(stream)
            w.add_blank_page(width=600, height=800)
            w.write(pdf)
            original = hashlib.sha256(pdf.read_bytes()).hexdigest()
            saida = raiz / 'extracao'
            cmd = [sys.executable, '-X', 'utf8', str(SCRIPTS / 'extrair.py'), str(pdf), '--saida', str(saida), '--ocr', 'visao', '--sem-reaproveitar']
            env = dict(os.environ, CPJ_WORKSPACE=temp)
            subprocess.run(cmd, env=env, check=True, capture_output=True)
            self.assertFalse((saida / 'relatorio_extracao.json').exists())
            self.assertFalse(list(saida.rglob('*.csv')))
            self.assertEqual([p.relative_to(saida).as_posix() for p in saida.rglob('*.json')], ['.checkpoint/estado.json'])
            self.assertIn('## Página 2', (saida / 'transcricao.md').read_text(encoding='utf-8'))
            self.assertTrue((saida / 'ordens-de-servico/indice.md').exists())
            self.assertEqual(visual.paginas_pendentes(saida), [2])
            visual.validar_replay(saida, pdf)
            subprocess.run([sys.executable, str(SCRIPTS / 'qualidade.py'), str(saida), '--pdf', str(pdf)], env=env, check=True, capture_output=True)
            self.assertTrue(visual.ler_json(saida, 'qualidade.json')['2']['precisa_ia'])
            replay = subprocess.run(cmd, env=env, check=True, capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(json.loads(replay.stdout)['paginas_reaproveitadas'], 2)
            self.assertEqual(hashlib.sha256(pdf.read_bytes()).hexdigest(), original)
            self.assertEqual(len(list(saida.rglob('*.json'))), 1)


if __name__ == '__main__':
    unittest.main()
