"""Sandbox do runner usa apenas código e modelos fictícios."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[4]
RUNNER = ROOT / "ferramentas" / "testar-tudo.py"

class HigieneSZ01(unittest.TestCase):
    def carregar(self):
        spec = importlib.util.spec_from_file_location("runner_sz01", RUNNER)
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
        except SyntaxError as exc:
            self.fail(f"runner não compilável: {exc}")
        return mod

    def test_snapshot_nao_copia_cache_nem_modelo_operacional(self):
        runner = self.carregar()
        with tempfile.TemporaryDirectory(prefix="cpj-sz01-") as td:
            base = Path(td)
            origem = base / "origem"
            plugin = origem / "plugin" / "investigacao-cpj"
            testes = plugin / "app" / "testes"
            testes.mkdir(parents=True)
            (testes / "fixtures_docx.py").write_text(
                "def criar_modelo(p):\n p.mkdir(parents=True, exist_ok=True)\n (p/'ficticio.docx').write_text('ficticio')\n", encoding="utf-8")
            for rel in ("plugin/.claude-plugin", ".github/workflows", "modelos/assinaturas", "calibracao", "ferramentas", "portatil", ".agents/skills"):
                (origem / rel).mkdir(parents=True, exist_ok=True)
            (origem / "plugin/.claude-plugin/marketplace.json").write_text("{}")
            (origem / ".github/workflows/test.yml").write_text("ficticio")
            (origem / "modelos/assinaturas/operador.png").write_text("nao copiar")
            (plugin / "app/codigo.py").write_text("pass")
            (plugin / "app/__pycache__").mkdir()
            (plugin / "app/__pycache__/codigo.pyc").write_bytes(b"cache")
            (plugin / "app/avulso.pyc").write_bytes(b"cache")
            (plugin / ".pytest_cache").mkdir()
            (plugin / ".pytest_cache/cache").write_bytes(b"cache")
            runner.ROOT, runner.PLUGIN, runner.TESTES = origem, plugin, testes
            destino = runner.clonar_codigo(base / "destino")
            self.assertTrue((destino / "plugin/investigacao-cpj/app/codigo.py").is_file())
            self.assertFalse(list(destino.rglob("*.pyc")))
            self.assertFalse(list(destino.rglob("__pycache__")))
            self.assertFalse(list(destino.rglob(".pytest_cache")))
            self.assertFalse((destino / "modelos/assinaturas").exists())
            self.assertTrue((destino / "modelos/ficticio.docx").is_file())
            self.assertTrue((destino / "plugin/.claude-plugin/marketplace.json").is_file())
            self.assertTrue((destino / ".github/workflows/test.yml").is_file())

if __name__ == "__main__":
    unittest.main()
