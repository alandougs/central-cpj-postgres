"""AST81: proveniência do grafo em índice real, somente workspaces fictícios."""
import csv
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[2] / 'skills/base-cpj/scripts'


class ProvenienciaIndice(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='cpj-astra-ast81-')
        self.addCleanup(self.temp.cleanup)
        self.ws = Path(self.temp.name)
        self.caso = 'OS-811-2099'
        self.base = self.ws / 'casos' / self.caso
        for parte in ('00-originais', '01-extracao', '02-analise'):
            (self.base / parte).mkdir(parents=True)
        (self.ws / 'modelos').mkdir()
        self.gravar_json(self.base / 'caso.json', {
            'id': self.caso, 'ordem_servico': '811/2099', 'status': 'recebido',
            'datas': {}, 'vitimas': [], 'investigados': [],
        })

    @staticmethod
    def gravar_json(path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')

    @staticmethod
    def gravar_csv(path, rows):
        path.parent.mkdir(parents=True, exist_ok=True)
        columns = list(dict.fromkeys(k for row in rows for k in row))
        with path.open('w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=columns, delimiter=';')
            writer.writeheader()
            writer.writerows(rows)

    def indexar(self):
        r = subprocess.run([sys.executable, '-B', '-X', 'utf8', str(SCRIPTS / 'indexar.py')],
                           env=dict(os.environ, CPJ_WORKSPACE=str(self.ws),
                                    CPJ_SEM_AGENTE_EMBUTIDO='1', PYTHONDONTWRITEBYTECODE='1'),
                           capture_output=True, text=True, encoding='utf-8', timeout=60)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def dados(self, sql, params=()):
        with closing(sqlite3.connect(self.ws / 'rag/cpj.sqlite')) as db:
            return db.execute(sql, params).fetchall()

    def evidencia(self, localizador):
        self.assertTrue(localizador.startswith('{'), 'Aresta precisa preservar campos de fonte em JSON.')
        meta = json.loads(localizador)
        self.assertEqual(meta['schema'], 'astra-evidencia/1')
        return meta

    def extracao(self, pasta='doc-a', original='fonte-a-ficticia.pdf'):
        file = self.base / '00-originais' / original
        file.write_bytes(b'Original ficticio apenas para hash, sem autos reais.')
        ext = self.base / '01-extracao' / pasta
        self.gravar_json(ext / 'relatorio_extracao.json', {
            'arquivo': original, 'sha256_original': hashlib.sha256(file.read_bytes()).hexdigest(),
            'gerado_em': '2099-01-02T03:04:05', 'paginas': 45,
        })
        return ext, file

    def test_qualificacoes_em_documentos_distintos_na_mesma_pagina_nao_fundem_registros(self):
        for doc in ('doc-a', 'doc-b'):
            self.extracao(doc, doc + '-ficticio.pdf')
        self.gravar_csv(self.base / '02-analise/pessoas.csv', [
            {'nome': 'Pessoa Homônima Fictícia', 'paginas': '12', 'documento': 'doc-a'},
            {'nome': 'Pessoa Homônima Fictícia', 'paginas': '12', 'documento': 'doc-b'},
        ])
        self.indexar()
        ids = {r[0] for r in self.dados('SELECT no_id FROM pessoas')}
        self.assertEqual(len(ids), 2, 'Documento da qualificação não pode desaparecer da identidade do registro.')
        refs = [self.evidencia(r[0]) for r in self.dados("SELECT localizador FROM arestas WHERE a_tipo='PESSOA' AND b_tipo='NOME'")]
        self.assertEqual({e['documento'] for e in refs}, {'doc-a', 'doc-b'})
        self.assertEqual({e['registro_origem']['linha'] for e in refs}, {2, 3})
        self.assertTrue(all(e['pagina'] == 12 and e['paginas'] == [12] for e in refs))
        self.indexar()
        self.assertEqual({r[0] for r in self.dados('SELECT no_id FROM pessoas')}, ids)

    def test_qualificacao_preserva_documento_paginas_multiplas_e_fls_literal(self):
        self.extracao()
        self.gravar_csv(self.base / '02-analise/pessoas.csv', [{
            'nome': 'Outra Pessoa Fictícia', 'paginas': '12 | 45', 'documento': 'doc-a',
            'fls': '7 verso / 8-A', 'localizador': 'Qualificação literal, conferir página 12 e 45',
            'trecho': 'Qualificação fictícia copiada literalmente.',
        }])
        self.indexar()
        e = self.evidencia(self.dados("SELECT localizador FROM arestas WHERE a_tipo='PESSOA' AND b_tipo='NOME'")[0][0])
        self.assertEqual(e['paginas'], [12, 45])
        self.assertIsNone(e['pagina'], 'Não escolher página única de referência com duas páginas.')
        self.assertEqual(e['fls'], '7 verso / 8-A')
        self.assertEqual(e['trecho'], 'Qualificação fictícia copiada literalmente.')
        self.assertIn('Qualificação literal, conferir página 12 e 45', e['localizador_original'])
        self.assertEqual(e['documento'], 'doc-a')
        self.assertEqual(e['arquivo_original'], f'casos/{self.caso}/00-originais/fonte-a-ficticia.pdf')

    def test_linhas_distintas_na_mesma_pagina_e_documento_nao_fundem_homonimos(self):
        self.gravar_csv(self.base / '02-analise/pessoas.csv', [
            {'nome': 'Homônimo Fictício', 'mae': 'Mãe Fictícia A', 'documento': 'doc-a', 'paginas': '7'},
            {'nome': 'Homônimo Fictício', 'mae': 'Mãe Fictícia B', 'documento': 'doc-a', 'paginas': '7'},
        ])
        self.indexar()
        rows = self.dados('SELECT no_id,mae FROM pessoas')
        self.assertEqual(len({r[0] for r in rows}), 2, 'Cada linha é um registro, mesmo com nome, documento e página iguais.')
        for no_id, mae in rows:
            self.assertEqual(self.dados("SELECT r.rotulo FROM arestas a JOIN rotulos r ON r.tipo=a.b_tipo AND r.valor=a.b_valor WHERE a.a_valor=? AND a.relacao LIKE 'mãe%'", (no_id,)),
                             [(mae,)])
        before = set(rows)
        self.indexar()
        self.assertEqual(set(self.dados('SELECT no_id,mae FROM pessoas')), before)

    def test_linhas_de_consulta_iguais_no_localizador_nao_fundem_qualificacoes(self):
        source = self.ws / 'consulta/base-ficticia'
        self.gravar_json(source / 'base.json', {'id': 'base-ficticia', 'nome': 'Base Fictícia'})
        (source / 'registros.jsonl').write_text(''.join(json.dumps({
            'nome': 'Homônimo Fictício', 'mae': mae, 'localizador': 'página 7',
        }, ensure_ascii=False) + '\n' for mae in ('Mãe Fictícia A', 'Mãe Fictícia B')), encoding='utf-8')
        self.indexar()
        self.assertEqual(len({r[0] for r in self.dados("SELECT no_id FROM pessoas WHERE origem='consulta'")}), 2)
        refs = [self.evidencia(r[0]) for r in self.dados("SELECT localizador FROM arestas WHERE origem='consulta' AND relacao LIKE 'nome (%'")]
        self.assertEqual({e['registro_origem']['linha'] for e in refs}, {1, 2})

    def test_entidade_guarda_trecho_status_e_metadata_explicito_sem_confirmacao_humana(self):
        ext, original = self.extracao()
        trecho = 'Trecho fictício integral do documento. ' * 9
        entity_file = ext / 'entidades.csv'
        self.gravar_csv(entity_file, [{'tipo': 'EMAIL', 'valor': 'pessoa@ficticio.invalid',
                                     'pagina_pdf': '7', 'trecho': trecho,
                                     'status': 'pendente de conferência', 'fls': '22-A'}])
        self.indexar()
        e = self.evidencia(self.dados("SELECT localizador FROM arestas WHERE b_tipo='EMAIL'")[0][0])
        self.assertEqual(e['tipo'], 'extracao_candidata')
        self.assertEqual(e['trecho'], trecho)
        self.assertEqual(e['status_fonte'], 'pendente de conferência')
        self.assertEqual(e['pagina'], 7)
        self.assertEqual(e['fls'], '22-A')
        self.assertEqual(e['extraido_em'], '2099-01-02T03:04:05')
        self.assertEqual(e['sha256_original'], hashlib.sha256(original.read_bytes()).hexdigest())
        self.assertEqual(e['sha256_derivado'], hashlib.sha256(entity_file.read_bytes()).hexdigest())
        self.assertEqual(e['arquivo_derivado'], f'casos/{self.caso}/01-extracao/doc-a/entidades.csv')
        self.assertNotIn('confirmado', e)

    def test_fluxo_sem_documento_nao_escolhe_pdf_existente_nem_inventa_hash_original(self):
        self.extracao()
        ff = self.base / '02-analise/fluxo-financeiro.csv'
        self.gravar_csv(ff, [{
            'seq': 'mov-1', 'data': '01/01/2099', 'valor': '10,00', 'meio': 'Pix',
            'origem_banco': 'Banco Fictício', 'origem_ag_conta': '001/10',
            'destino_banco': 'Banco Fictício', 'destino_ag_conta': '002/20',
            'fonte_pag': '7', 'fls': '10 verso', 'status_conferencia': 'conferido',
        }])
        self.indexar()
        e = self.evidencia(self.dados("SELECT localizador FROM arestas WHERE relacao LIKE 'transferiu%'")[0][0])
        self.assertEqual(e['tipo'], 'documental')
        self.assertIsNone(e['documento'])
        self.assertIsNone(e['arquivo_original'])
        self.assertIsNone(e['sha256_original'])
        self.assertIsNone(e['extraido_em'])
        self.assertEqual(e['data_fato'], '01/01/2099')
        self.assertEqual(e['status_fonte'], 'conferido')
        self.assertEqual(e['registro_origem'], {'linha': 2, 'seq': 'mov-1'})
        self.assertEqual(e['fls'], '10 verso')
        self.assertIsNone(e['trecho'])

    def test_caminho_de_documento_fora_do_caso_nao_vira_fonte_nem_hash(self):
        self.gravar_csv(self.base / '02-analise/pessoas.csv', [{
            'nome': 'Pessoa Fictícia', 'documento': '../outro-caso/segredo.pdf', 'paginas': '1',
        }])
        self.indexar()
        e = self.evidencia(self.dados("SELECT localizador FROM arestas WHERE a_tipo='PESSOA'")[0][0])
        self.assertEqual(e['documento'], '../outro-caso/segredo.pdf', 'Conservar o dado declarado sem abri-lo.')
        self.assertIsNone(e['arquivo_original'])
        self.assertIsNone(e['sha256_original'])
        self.assertFalse(os.path.isabs(e['arquivo_derivado']))

    def test_documento_explicito_relativo_ao_workspace_preserva_fonte_sem_busca_por_nome(self):
        self.extracao()
        documento = f'casos/{self.caso}/00-originais/fonte-a-ficticia.pdf'
        self.gravar_csv(self.base / '02-analise/pessoas.csv', [{
            'nome': 'Fonte Expressa Fictícia', 'documento': documento, 'paginas': '7',
        }])
        self.indexar()
        e = self.evidencia(self.dados("SELECT localizador FROM arestas WHERE a_tipo='PESSOA'")[0][0])
        self.assertEqual(e['arquivo_original'], documento)
        self.assertIsNone(e['sha256_original'], 'Não associar metadado de outra pasta apenas por nome de arquivo.')

    def test_pasta_de_caso_junction_externa_nao_publica_caminho_ou_hash_externo(self):
        self.extracao()
        self.gravar_csv(self.base / '02-analise/pessoas.csv', [{
            'nome': 'Pessoa Fictícia em Pasta Externa', 'paginas': '7',
            'documento': '00-originais/fonte-a-ficticia.pdf',
        }])
        externo = tempfile.TemporaryDirectory(prefix='cpj-astra-ast81-fora-')
        self.addCleanup(externo.cleanup)
        destino = Path(externo.name) / 'caso-ficticio'
        self.base.rename(destino)
        if os.name == 'nt':
            origem_ps = str(self.base).replace("'", "''")
            destino_ps = str(destino).replace("'", "''")
            r = subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-Command',
                                f"New-Item -ItemType Junction -Path '{origem_ps}' -Target '{destino_ps}' -ErrorAction Stop | Out-Null"],
                               capture_output=True, text=True, timeout=30)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        else:
            self.base.symlink_to(destino, target_is_directory=True)
        self.indexar()
        e = self.evidencia(self.dados("SELECT localizador FROM arestas WHERE a_tipo='PESSOA'")[0][0])
        self.assertIsNone(e['arquivo_original'], 'A raiz do caso também deve permanecer dentro do workspace.')
        self.assertIsNone(e['arquivo_derivado'])
        self.assertIsNone(e['sha256_original'])
        self.assertIsNone(e['sha256_derivado'])
        self.assertIsNone(e['extraido_em'])
        self.assertEqual(e['documento'], '00-originais/fonte-a-ficticia.pdf')

    def test_cadastro_e_base_de_consulta_ficam_identificados_sem_promocao_aos_autos(self):
        cj = json.loads((self.base / 'caso.json').read_text(encoding='utf-8'))
        cj['vitimas'] = ['Cadastro Fictício']
        self.gravar_json(self.base / 'caso.json', cj)
        source = self.ws / 'consulta/base-ficticia'
        self.gravar_json(source / 'base.json', {'id': 'base-ficticia', 'nome': 'Base Fictícia',
                                              'arquivo_original': 'ficha-ficticia.csv'})
        (source / 'registros.jsonl').write_text(json.dumps({
            'nome': 'Registro Fictício', 'localizador': 'Aba fictícia, linha 3',
            'texto': 'Texto de consulta fictício, não é peça do IP.',
        }, ensure_ascii=False) + '\n', encoding='utf-8')
        self.indexar()
        refs = [self.evidencia(r[0]) for r in self.dados("SELECT localizador FROM arestas WHERE a_tipo='PESSOA' AND b_tipo='NOME'")]
        consult = next(e for e in refs if e['tipo'] == 'consulta')
        cadastral = next(e for e in refs if e['tipo'] == 'cadastro')
        self.assertIsNone(consult['caso'])
        self.assertEqual(consult['documento'], 'ficha-ficticia.csv')
        self.assertEqual(consult['trecho'], 'Texto de consulta fictício, não é peça do IP.')
        self.assertIn('Aba fictícia, linha 3', consult['localizador_original'])
        self.assertIsNone(cadastral['pagina'])
        self.assertIsNone(cadastral['arquivo_original'])
        self.assertEqual(cadastral['caso'], self.caso)

    def test_manual_com_p_antigo_preserva_id_evento_evidencia_e_hipotese_sem_remapear(self):
        self.gravar_csv(self.base / '02-analise/pessoas.csv', [
            {'nome': 'Pessoa Fictícia', 'paginas': '12', 'documento': 'doc-a'},
            {'nome': 'Pessoa Fictícia', 'paginas': '12', 'documento': 'doc-b'},
        ])
        sys.path.insert(0, str(SCRIPTS))
        import vinculos_manuais as vm
        old_id = 'P:REGISTRO-ANTIGO-FICTICIO'
        manual = vm.criar(self.ws, {
            'caso': self.caso, 'a_tipo': 'PESSOA', 'a_valor': old_id, 'a_rotulo': 'Pessoa Fictícia',
            'b_tipo': 'CONTA', 'b_valor': 'banco ficticio|123', 'relacao': 'hipótese antiga',
            'evidencia': {'documento': '', 'pagina': None, 'fls': '', 'observacao': 'Não inferir identidade.'},
        }, 'operador_ficticio')
        events = self.ws / 'consulta/_grafo-manual/eventos'
        before = {p.name: p.read_bytes() for p in events.glob('*.json')}
        for _ in range(2):
            self.indexar()
        self.assertEqual({p.name: p.read_bytes() for p in events.glob('*.json')}, before)
        row = self.dados("SELECT a_valor,localizador FROM arestas WHERE origem='manual'")[0]
        self.assertEqual(row[0], old_id)
        self.assertNotIn(old_id, {r[0] for r in self.dados('SELECT no_id FROM pessoas')})
        self.assertEqual(json.loads(row[1])['schema'], 'astra-manual/1')
        reopened = vm.listar(self.ws)[0]
        self.assertEqual(reopened, manual)
        self.assertEqual(reopened['status'], 'hipotese')


if __name__ == '__main__':
    unittest.main(verbosity=2)
