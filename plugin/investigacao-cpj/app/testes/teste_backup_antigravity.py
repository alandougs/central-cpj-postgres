"""Teste L04: python -X utf8 app/testes/teste_backup_antigravity.py.

Usa workspace temporário e dados fictícios para validar backup e restauração.
"""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


@unittest.skipUnless(os.name == "nt" and shutil.which("powershell.exe"),
                     "Integração PowerShell/robocopy requer Windows")
class TesteBackup(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_ws = tempfile.TemporaryDirectory(prefix="cpj-backup-ws-")
        cls.temp_bkp = tempfile.TemporaryDirectory(prefix="cpj-backup-dest-")
        cls.ws = Path(cls.temp_ws.name)
        cls.bkp = Path(cls.temp_bkp.name)

        # Criar estrutura
        cls.pastas = ['casos', 'calibracao', 'producao', 'modelos', 'consulta', 'referencias', 'config', 'usuarios']
        for p in cls.pastas:
            (cls.ws / p).mkdir(parents=True, exist_ok=True)
            (cls.ws / p / f"{p}_teste.txt").write_text(f"Conteudo original de {p}", encoding="utf-8")

        # Copiar scripts
        ferramentas = cls.ws / "ferramentas"
        ferramentas.mkdir(exist_ok=True)
        
        orig_ferramentas = Path(__file__).resolve().parents[4] / "ferramentas"
        shutil.copy(orig_ferramentas / "backup.ps1", ferramentas / "backup.ps1")
        shutil.copy(orig_ferramentas / "restaurar.ps1", ferramentas / "restaurar.ps1")

    @classmethod
    def tearDownClass(cls):
        cls.temp_ws.cleanup()
        cls.temp_bkp.cleanup()

    def test_backup_e_restauracao(self):
        # 1. Executar backup
        cmd_bkp = ["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", str(self.ws / "ferramentas" / "backup.ps1"), "-Destino", str(self.bkp)]
        res_bkp = subprocess.run(cmd_bkp, capture_output=True, text=True)
        self.assertEqual(res_bkp.returncode, 0, f"Erro no backup:\n{res_bkp.stderr}\n{res_bkp.stdout}")

        # Verifica se as pastas existem no backup
        alvo = self.bkp / "CPJ-TRABALHO-backup"
        self.assertTrue(alvo.exists(), "Pasta de backup nao foi criada no destino")
        for p in self.pastas:
            self.assertTrue((alvo / p).exists(), f"Pasta {p} ausente no backup")
            self.assertTrue((alvo / p / f"{p}_teste.txt").exists(), f"Arquivo {p}_teste.txt ausente no backup")

        # 2. Modificar workspace original (apagar alguns, alterar outros)
        (self.ws / "casos" / "casos_teste.txt").write_text("Conteudo alterado de casos", encoding="utf-8")
        (self.ws / "config" / "config_teste.txt").unlink()
        (self.ws / "config" / "config_novo.txt").write_text("Novo", encoding="utf-8")

        # 3. Executar restauracao
        cmd_rest = ["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", str(self.ws / "ferramentas" / "restaurar.ps1"), "-Origem", str(alvo)]
        res_rest = subprocess.run(cmd_rest, capture_output=True, text=True)
        self.assertEqual(res_rest.returncode, 0, f"Erro na restauracao:\n{res_rest.stderr}\n{res_rest.stdout}")

        # 4. Verificar se a restauracao trouxe os arquivos antigos sem apagar os novos (robocopy nao apaga arquivos extras por padrão com as flags usadas /E /XO /R:1 /W:1 /XD __pycache__)
        self.assertEqual((self.ws / "casos" / "casos_teste.txt").read_text(encoding="utf-8"), "Conteudo original de casos")
        self.assertTrue((self.ws / "config" / "config_teste.txt").exists(), "Arquivo apagado nao foi restaurado")
        self.assertEqual((self.ws / "config" / "config_teste.txt").read_text(encoding="utf-8"), "Conteudo original de config")
        self.assertTrue((self.ws / "config" / "config_novo.txt").exists(), "Arquivo novo foi apagado incorretamente")

if __name__ == "__main__":
    unittest.main(verbosity=2)
