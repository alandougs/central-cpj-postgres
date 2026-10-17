"""AST13: layout real com DOM/RAF fictícios; somente identificadores sintéticos."""
import os
from pathlib import Path
import shutil
import subprocess
import unittest

STATIC = Path(__file__).resolve().parents[1] / 'static'
HELPERS = Path(__file__).resolve().parent / 'astra_layout'


class ContratoLayout(unittest.TestCase):
    def test_determinismo_estado_fisica_desenho_e_interacao(self):
        runtime = Path.home() / '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
        node = str(runtime) if runtime.is_file() else shutil.which('node')
        if not node:
            self.skipTest('Node indisponível para executar JavaScript real')
        r = subprocess.run([node, str(HELPERS / 'test-layout.cjs'), str(STATIC / 'js/grafo.js')],
                           capture_output=True, text=True, encoding='utf-8', timeout=60)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_edge_camera_arraste_resize_visibilidade_e_expansao(self):
        runtime = Path.home() / '.cache/codex-runtimes/codex-primary-runtime/dependencies/node'
        node = runtime / 'bin/node.exe'
        if not node.is_file():
            self.skipTest('Runtime Node/Playwright indisponível')
        r = subprocess.run([str(node), str(HELPERS / 'edge-layout.cjs'), str(STATIC / 'js/grafo.js')],
                           env=dict(os.environ, NODE_PATH=str(runtime / 'node_modules')),
                           capture_output=True, text=True, encoding='utf-8', timeout=90)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == '__main__':
    unittest.main(verbosity=2)
