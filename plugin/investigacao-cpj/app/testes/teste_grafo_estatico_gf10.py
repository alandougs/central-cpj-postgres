"""GF10: grafo calculado uma vez e exibido parado; arrastar/filtrar não move os demais. Dados fictícios."""
from pathlib import Path
import shutil
import subprocess
import unittest

STATIC = Path(__file__).resolve().parents[1] / 'static'
HELPERS = Path(__file__).resolve().parent / 'astra_layout'


class GrafoEstatico(unittest.TestCase):
    def test_layout_parado_arraste_e_filtro(self):
        runtime = Path.home() / '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
        node = str(runtime) if runtime.is_file() else shutil.which('node')
        if not node:
            self.skipTest('Node indisponível para executar JavaScript real')
        r = subprocess.run([node, str(HELPERS / 'test-estatico-gf10.cjs'), str(STATIC / 'js/grafo.js')],
                           capture_output=True, text=True, encoding='utf-8', timeout=60)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == '__main__':
    unittest.main(verbosity=2)
