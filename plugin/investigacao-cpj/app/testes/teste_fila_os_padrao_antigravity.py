"""AG05: inventário por CLI em pastas fictícias, sem O.S. reais."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

RAIZ = Path(__file__).resolve().parents[4]
FILA = RAIZ / "ferramentas/fila-os.py"


class FormatosOS(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="cpj-ag05-ficticio-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.orders = self.root / "ordens"
        self.orders.mkdir()
        self.env = dict(os.environ, PYTHONUTF8="1", CPJ_PASTA_OS=str(self.orders),
                        CPJ_WORKSPACE=str(self.root / "workspace"), CPJ_WORKSPACES=str(self.root / "workspace"))

    def folder(self, name):
        path = self.orders / name
        path.mkdir()
        return path

    def listing(self):
        result = subprocess.run([sys.executable, str(FILA), "listar", "--json"],
                                env=self.env, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_underscore_and_multiple_orders_are_listed_without_inquest_numbers(self):
        shared = self.folder("OS 9999_99 e OS 9998_99 IP 8888_99 PESSOA FICTICIA")
        self.folder("OS 2662_26 IP 603_26 PESSOA FICTICIA")
        self.folder("OS 2699_26 IP 599_26 PESSOA FICTICIA")
        result = self.listing()
        self.assertEqual(set(result), {"9999", "9998", "2662", "2699"})
        self.assertEqual(result["9999"]["pastas"], [str(shared)])
        self.assertEqual(result["9998"]["pastas"], [str(shared)])
        self.assertEqual(result["2662"]["ano"], "2026")
        self.assertEqual(result["9998"]["ano"], "2099")

    def test_explicit_ip_bo_and_process_without_order_are_ignored(self):
        for name in ("IP 8888-26 FICTICIO", "BO 8887.2026 FICTICIO", "PROCESSO 8886_26 FICTICIO", "PROC 8885-2026 FICTICIO", "INQUÉRITO 8884-26 FICTICIO"):
            self.folder(name)
        self.assertEqual(self.listing(), {})

    def test_legacy_dash_dot_and_bare_names_remain_supported(self):
        for name in ("OS 9001-26 FICTICIO", "os 9002.2026 FICTICIO", "O.S. 9003-2026 FICTICIO", "9004-2026 FICTICIO"):
            self.folder(name)
        self.assertEqual(set(self.listing()), {"9001", "9002", "9003", "9004"})

    def test_explicit_order_does_not_collect_other_numeric_pairs(self):
        self.folder("OS 9010-26 IP 9030-26 BO 9040_26 PROCESSO 9050.2026 FICTICIO")
        self.assertEqual(set(self.listing()), {"9010"})

    def test_json_listing_keeps_files_unique_and_does_not_create_notices(self):
        path = self.folder("OS 9020-2026 FICTICIO")
        pdf = path / "original-ficticio.pdf"
        pdf.write_bytes(b"pdf ficticio nao utilizado")
        result = self.listing()
        self.assertEqual(result["9020"]["pdfs"], [str(pdf)])
        self.assertEqual(result["9020"]["situacao"], "livre")
        self.assertFalse((path / "_STATUS-OS.txt").exists())
        self.assertFalse((self.orders / "_CONTROLE-OS.json").exists())
        self.assertFalse((self.orders / "_CONTROLE-OS.md").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
