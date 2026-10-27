"""SEC25/L04: executa os wrappers PowerShell reais somente com dados fictícios."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[4]


@unittest.skipUnless(os.name == "nt" and shutil.which("powershell.exe"), "Integração PowerShell requer Windows")
class TesteBackup(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="cpj-backup-ps-sec25-")
        self.base = Path(self.tmp.name)
        self.instalacao = self.base / "instalacao"
        self.ferramentas = self.instalacao / "ferramentas"
        self.ferramentas.mkdir(parents=True)
        for nome in ("backup.ps1", "restaurar.ps1", "backup_consistente.py"):
            shutil.copy2(ROOT / "ferramentas" / nome, self.ferramentas / nome)
        app = self.instalacao / "plugin/investigacao-cpj/app"
        app.mkdir(parents=True)
        for nome in ("auth.py", "seguranca_local.py"):
            shutil.copy2(ROOT / "plugin/investigacao-cpj/app" / nome, app / nome)
        self.ws = self.base / "fonte"
        self.pastas = ("casos", "calibracao", "producao", "modelos", "consulta", "referencias", "config", "usuarios")
        for p in self.pastas:
            d = self.ws / p; d.mkdir(parents=True)
            (d / "ficticio.txt").write_text("original " + p, encoding="utf-8")
        self.midia = self.base / "midia"
        self.midia.mkdir()
        self.env = dict(os.environ, CPJ_WORKSPACE=str(self.ws), CPJ_SEM_AGENTE_EMBUTIDO="1", PYTHONIOENCODING="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def ps(self, nome, *args):
        return subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                               "-File", str(self.ferramentas / nome), *map(str, args)],
                              capture_output=True, text=True, errors="replace", env=self.env, timeout=30)

    def snapshot(self):
        r = self.ps("backup.ps1", "-Origem", self.ws, "-Destino", self.midia, "-Offline", "-MidiaProtegida", "-Python", sys.executable)
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        snapshots = list(self.midia.glob("CPJ-*"))
        self.assertEqual(len(snapshots), 1)
        self.assertTrue((snapshots[0] / "manifest.json").is_file())
        return snapshots[0]

    def test_backup_e_restauracao_nova_preservam_dados_posteriores_da_fonte(self):
        snap = self.snapshot()
        for p in self.pastas:
            self.assertEqual((snap / "dados" / p / "ficticio.txt").read_text(encoding="utf-8"), "original " + p)
        (self.ws / "casos/ficticio.txt").write_text("mais novo", encoding="utf-8")
        (self.ws / "config/ficticio.txt").unlink()
        (self.ws / "config/novo.txt").write_text("posterior", encoding="utf-8")
        destino = self.base / "restaurado & ficticio"
        r = self.ps("restaurar.ps1", "-Origem", snap, "-Destino", destino, "-MidiaProtegida", "-Python", sys.executable)
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        for p in self.pastas:
            self.assertEqual((destino / p / "ficticio.txt").read_text(encoding="utf-8"), "original " + p)
        self.assertFalse((destino / "config/novo.txt").exists())
        self.assertEqual((self.ws / "casos/ficticio.txt").read_text(encoding="utf-8"), "mais novo")
        self.assertFalse((self.ws / "config/ficticio.txt").exists())
        self.assertEqual((self.ws / "config/novo.txt").read_text(encoding="utf-8"), "posterior")

    def test_restauracao_recusa_sem_destino_ou_confirmacao_e_destino_existente(self):
        snap = self.snapshot()
        novo = self.base / "novo"
        argumentos = ["-Origem", snap, "-Python", sys.executable]
        for extras in (["-MidiaProtegida"], ["-Destino", novo], ["-Destino", self.ws, "-MidiaProtegida"]):
            r = self.ps("restaurar.ps1", *argumentos, *extras)
            self.assertNotEqual(r.returncode, 0)
            self.assertFalse(novo.exists())
            self.assertEqual((self.ws / "casos/ficticio.txt").read_text(encoding="utf-8"), "original casos")
        self.assertFalse((self.instalacao / "casos").exists(), "Nunca usar instalação como destino implícito")

    def test_backup_recusa_sem_confirmacoes_e_restore_verifica_integridade(self):
        for extras in ([], ["-Offline"], ["-MidiaProtegida"]):
            r = self.ps("backup.ps1", "-Origem", self.ws, "-Destino", self.midia, *extras)
            self.assertNotEqual(r.returncode, 0)
            self.assertEqual(list(self.midia.iterdir()), [])
        snap = self.snapshot()
        (snap / "dados/casos/ficticio.txt").write_text("adulterado", encoding="utf-8")
        novo = self.base / "novo"
        r = self.ps("restaurar.ps1", "-Origem", snap, "-Destino", novo, "-MidiaProtegida", "-Python", sys.executable)
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse(novo.exists())


if __name__ == "__main__": unittest.main(verbosity=2)
