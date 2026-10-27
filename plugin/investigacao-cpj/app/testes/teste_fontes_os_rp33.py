"""RP33: fonte de outro diretório e campos pendentes nunca aprovam entrega.

Somente arquivos fictícios em TEMP; sem servidor, modelos ou contas reais.
"""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / 'plugin/investigacao-cpj/skills/relatorio-ip-fraude/scripts/conferir_minuta.py'


class FontesOSRP33(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='cpj-rp33-')
        self.addCleanup(self.temp.cleanup)
        self.ws = Path(self.temp.name)
        self.env = patch.dict(os.environ, CPJ_WORKSPACE=str(self.ws), CPJ_SEM_AGENTE_EMBUTIDO='1')
        self.env.start()
        self.addCleanup(self.env.stop)
        self.ext = self.ws / 'casos/OS-933-2099/01-extracao'
        self.rel = self.ext.parent / '03-relatorios'
        self.ext.mkdir(parents=True)
        self.rel.mkdir()

    def fonte(self, pasta):
        pasta.mkdir(parents=True, exist_ok=True)
        (pasta / 'transcricao.md').write_text('## Página 1\nRecebido R$ 123,45.\n', encoding='utf-8')

    def junction(self, link, alvo):
        if os.name == 'nt':
            criado = subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(alvo)],
                                     capture_output=True, text=True)
            self.assertEqual(criado.returncode, 0, criado.stdout + criado.stderr)
        else:
            link.symlink_to(alvo, target_is_directory=True)

    def conferencia(self, resumo, informar_caso=True):
        minuta = self.rel / 'minuta-v01.md'
        minuta.write_text('''---
ordem_servico: 933/2099
referencia: IPe nº 9999999/2099 / Processo nº 9999999-99.2099.8.26.9999
natureza: Fraude
investigados: Pessoa fictícia
vitimas: Pessoa fictícia
local: Cidade fictícia
data_fatos: 01/01/2099
local_data: Cidade fictícia, 02/01/2099
data_rodape: 02/01/2099
delegado: Autoridade fictícia
delegado_genero: F
---
## RESUMO DOS FATOS
''' + resumo + '''
## DILIGÊNCIAS REALIZADAS
Examinados os documentos fictícios.
## CONCLUSÃO
Registrado o alcance documental.
''', encoding='utf-8')
        proc = subprocess.run([sys.executable, '-X', 'utf8', str(SCRIPT), *(['OS-933-2099'] if informar_caso else []),
                               '--minuta', str(minuta), '--extracao', str(self.ext), '--modo', 'entrega'],
                              env=dict(os.environ), capture_output=True, text=True, encoding='utf-8')
        saida = self.rel / 'conferencia-v01.json'
        return proc, json.loads(saida.read_text(encoding='utf-8')) if saida.exists() else {}

    def test_transcricao_interna_continua_conferida(self):
        self.fonte(self.ext / 'autos')
        proc, conf = self.conferencia('Recebido R$ 123,45 (pág. 1).')
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertTrue(conf['aprovado'])
        self.assertEqual(conf['resumo']['confirmados'], 1)

    def test_junction_externa_nao_comprova_fato_do_caso(self):
        fora = self.ws / 'outro-caso-ficticio'
        self.fonte(fora)
        link = self.ext / 'autos'
        self.junction(link, fora)
        proc, conf = self.conferencia('Recebido R$ 123,45 (pág. 1).')
        self.assertFalse(conf.get('aprovado'), proc.stdout + proc.stderr)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(conf.get('resumo', {}).get('confirmados', 0), 0)

    def test_raiz_extracao_junction_nao_comprova_fato_do_caso(self):
        fora = self.ws / 'outro-caso-ficticio'
        self.fonte(fora / 'autos')
        self.ext.rmdir()
        self.junction(self.ext, fora)
        proc, conf = self.conferencia('Recebido R$ 123,45 (pág. 1).')
        self.assertFalse(conf.get('aprovado'), proc.stdout + proc.stderr)
        self.assertNotEqual(proc.returncode, 0)

    def ancestral_junction(self, nivel):
        caso = self.ext.parent
        self.rel.rmdir()
        self.ext.rmdir()
        caso.rmdir()
        origem = caso if nivel == 'caso' else caso.parent
        if nivel == 'casos':
            origem.rmdir()
        fora = self.ws / 'outra-arvore-ficticia'
        alvo_caso = fora if nivel == 'caso' else fora / caso.name
        (alvo_caso / '01-extracao').mkdir(parents=True)
        (alvo_caso / '03-relatorios').mkdir()
        self.junction(origem, fora)
        self.fonte(self.ext / 'autos')
        proc, conf = self.conferencia('Recebido R$ 123,45 (pág. 1).')
        self.assertFalse(conf.get('aprovado'), proc.stdout + proc.stderr)
        self.assertNotEqual(proc.returncode, 0)

    def test_caso_ancestral_junction_nao_comprova_fato_do_caso(self):
        self.ancestral_junction('caso')

    def test_casos_ancestral_junction_nao_comprova_fato_do_caso(self):
        self.ancestral_junction('casos')

    def test_extracao_custom_normal_sem_id_continua_autorizada(self):
        self.ext = self.ws / 'extracao-custom-ficticia'
        self.fonte(self.ext / 'autos')
        proc, conf = self.conferencia('Recebido R$ 123,45 (pág. 1).', informar_caso=False)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertTrue(conf['aprovado'])
        self.assertEqual(conf['resumo']['confirmados'], 1)

    def arquivo_ligado(self, nome):
        pasta = self.ext / 'autos'
        self.fonte(pasta)
        fora = self.ws / ('outro-' + nome)
        fora.write_text('## Página 1\nRecebido R$ 123,45.\n' if nome.endswith('.md') else '{}', encoding='utf-8')
        destino = pasta / nome
        if destino.exists():
            destino.unlink()
        try:
            destino.symlink_to(fora)
        except OSError as exc:
            if os.name == 'nt' and exc.winerror == 1314:
                self.skipTest('Windows sem privilégio para symlink de arquivo; junctions testadas de verdade.')
            raise
        proc, conf = self.conferencia('Recebido R$ 123,45 (pág. 1).')
        self.assertFalse(conf.get('aprovado'), proc.stdout + proc.stderr)
        self.assertNotEqual(proc.returncode, 0)

    def test_transcricao_isolada_externa_nao_comprova_fato(self):
        self.arquivo_ligado('transcricao.md')

    def test_metadados_isolados_externos_nao_comprovam_fato(self):
        self.arquivo_ligado('relatorio_extracao.json')

    def test_pendencias_canonicas_obter_e_pesquisar_bloqueiam(self):
        self.fonte(self.ext / 'autos')
        for campo in ('[OBTER: FOLHAS DOS AUTOS]', '[PESQUISAR: CNPJ]'):
            with self.subTest(campo=campo):
                proc, conf = self.conferencia('Documentação consultada. ' + campo)
                self.assertFalse(conf.get('aprovado'), proc.stdout + proc.stderr)
                self.assertEqual(proc.returncode, 1)
                self.assertTrue(any(a['codigo'] == 'PENDENTE' for a in conf['achados']))

    def test_decimo_item_na_continuacao_da_os_e_preservado(self):
        pasta = self.ext / 'autos'
        pasta.mkdir()
        spec = importlib.util.spec_from_file_location('os_rp33',
                    ROOT / 'plugin/investigacao-cpj/skills/pdf-autos-policiais/scripts/ordens_servico.py')
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)
        for numero in (2, 9, 10, 11, 99):
            with self.subTest(numero=numero):
                (pasta / 'transcricao.md').write_text('## Página 4\nORDEM DE SERVIÇO Nº 933/2099\n'
                    '1. Conferir comprovantes.\n## Página 5\n'
                    f'{numero}. Esclarecer a divergência documental.\n'
                    '## Página 6\nDESPACHO\nConclusão.\n', encoding='utf-8')
                info = modulo.extrair_ordens(pasta)
                self.assertEqual(info['ordens'][0]['paginas'], [4, 5])
                texto = (pasta / info['ordens'][0]['arquivo']).read_text(encoding='utf-8')
                self.assertIn(f'{numero}. Esclarecer a divergência documental.', texto)
                self.assertNotIn('Conclusão.', texto)
                self.assertIsNone(info['vigente'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
