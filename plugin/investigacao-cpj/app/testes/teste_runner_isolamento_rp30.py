"""Clonagem de testes não pode carregar modelos/assinaturas do operador."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]


class RunnerIsolamentoRP30(unittest.TestCase):
    def test_clone_gera_modelo_ficticio_sem_copiar_ativos_operacionais(self):
        spec = importlib.util.spec_from_file_location('runner_rp30', ROOT / 'ferramentas/testar-tudo.py')
        runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)
        with tempfile.TemporaryDirectory(prefix='cpj-runner-rp30-') as td:
            base = Path(td)
            origem = base / 'origem-ficticia'
            plugin = origem / 'plugin/investigacao-cpj'
            plugin.mkdir(parents=True)
            marketplace = origem / 'plugin/.claude-plugin'
            marketplace.mkdir()
            (marketplace / 'marketplace.json').write_text('{"name":"fixture-ficticia","plugins":[]}', encoding='utf-8')
            (origem / 'MEMORIA.md').write_text('# Memoria ficticia de teste\n', encoding='utf-8')
            for pasta in ('modelos/assinaturas', 'calibracao', 'ferramentas', 'portatil', '.agents/skills'):
                (origem / pasta).mkdir(parents=True)
            marcador = b'ATIVO PRIVADO FICTICIO QUE NAO PODE ENTRAR NO CLONE'
            (origem / 'modelos/assinaturas/privada.png').write_bytes(marcador)
            (origem / 'modelos/outro-modelo.docx').write_bytes(marcador)
            (origem / 'modelos/dados-padrao.json').write_bytes(b'{"operador":"PRIVADO FICTICIO"}')
            destino = base / 'sandbox'
            with patch.object(runner, 'ROOT', origem), patch.object(runner, 'PLUGIN', plugin):
                codigo = runner.clonar_codigo(destino)
            self.assertEqual((codigo / 'plugin/.claude-plugin/marketplace.json').read_text(encoding='utf-8'), '{"name":"fixture-ficticia","plugins":[]}')
            self.assertEqual((codigo / 'MEMORIA.md').read_text(encoding='utf-8'), '# Memoria ficticia de teste\n')
            self.assertFalse((codigo / 'modelos/assinaturas/privada.png').exists())
            self.assertFalse((codigo / 'modelos/outro-modelo.docx').exists())
            self.assertTrue(list((codigo / 'modelos').glob('*.docx')), 'A sandbox precisa de modelo geométrico utilizável.')
            for arquivo in (codigo / 'modelos').rglob('*'):
                if arquivo.is_file():
                    self.assertNotIn(marcador, arquivo.read_bytes())
                    self.assertNotIn(b'PRIVADO FICTICIO', arquivo.read_bytes())


if __name__ == '__main__':
    unittest.main(verbosity=2)
