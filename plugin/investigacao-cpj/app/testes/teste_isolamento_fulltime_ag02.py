"""Regressão do isolamento Full-Time; nenhuma Startup real é usada."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


FULLTIME = Path(__file__).with_name("teste_fulltime.py")
STARTUP = Path("Microsoft/Windows/Start Menu/Programs/Startup/Central-CPJ-24-7.lnk")


class IsolamentoFullTime(unittest.TestCase):
    def test_atalho_herdado_permanece_intacto(self):
        with tempfile.TemporaryDirectory(prefix="cpj-ag02-sentinela-") as pasta:
            appdata = Path(pasta) / "appdata-herdado"
            atalho = appdata / STARTUP
            atalho.parent.mkdir(parents=True)
            # Atalho válido: o teste legado o substituiria e depois o apagaria.
            comando = ("$w=New-Object -ComObject WScript.Shell;"
                       f"$s=$w.CreateShortcut('{atalho}');"
                       "$s.TargetPath='notepad.exe';"
                       "$s.Description='SENTINELA FICTICIA AG02';$s.Save()")
            criado = subprocess.run(["powershell", "-NoProfile", "-Command", comando],
                                    capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(criado.returncode, 0, criado.stderr)
            antes = atalho.read_bytes()
            ambiente = dict(os.environ, APPDATA=str(appdata),
                            CPJ_WORKSPACE=str(Path(pasta) / "workspace-herdado"), PYTHONUTF8="1")
            rodado = subprocess.run([sys.executable, "-X", "utf8", str(FULLTIME),
                                     "TesteFullTime.test_05_instalacao_remocao_atalho_boot"],
                                    env=ambiente, capture_output=True, text=True,
                                    encoding="utf-8", errors="replace", timeout=60)
            self.assertEqual(rodado.returncode, 0, rodado.stdout + rodado.stderr)
            self.assertTrue(atalho.exists(), "Teste apagou Startup herdada fictícia")
            self.assertEqual(atalho.read_bytes(), antes, "Teste substituiu o atalho herdado")

    def test_ambiente_restaurado_apos_teardown(self):
        spec = importlib.util.spec_from_file_location("fulltime_ag02", FULLTIME)
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)
        with tempfile.TemporaryDirectory(prefix="cpj-ag02-env-") as pasta:
            for presente in (True, False):
                with self.subTest(variaveis_presentes=presente):
                    with patch.dict(os.environ):
                        for chave in ("APPDATA", "CPJ_WORKSPACE"):
                            if presente:
                                os.environ[chave] = str(Path(pasta) / chave)
                            else:
                                os.environ.pop(chave, None)
                        antes = {chave: os.environ.get(chave) for chave in ("APPDATA", "CPJ_WORKSPACE")}
                        caso = modulo.TesteFullTime("test_02_status_parado")
                        caso.setUp()
                        try:
                            self.assertEqual(Path(os.environ["CPJ_WORKSPACE"]), Path(caso.tmp))
                            self.assertTrue(Path(os.environ["APPDATA"]).is_relative_to(Path(caso.tmp)))
                        finally:
                            caso.tearDown()
                        self.assertEqual({chave: os.environ.get(chave) for chave in antes}, antes)


if __name__ == "__main__":
    unittest.main()
