import json
import os
import shutil
import tempfile
import unittest
import zipfile
import hashlib
from pathlib import Path
import sys

class TestTarefasC03(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.ws = Path(cls.temp.name)
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from tarefas import Tarefas
        import threading
        class AuthMock:
            def obter(self, uid): return {}
        class CasoMock:
            pass
        cls.tarefas = Tarefas(str(cls.ws), CasoMock(), AuthMock(), iniciar_agente=False)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_importar_escopo(self):
        # Cria pacote malicioso
        zip_path = self.ws / "malicioso.zip"
        with zipfile.ZipFile(zip_path, "w") as z:
            arqs = [
                {"caminho": "../fora.txt", "tamanho": 4, "sha256": "hash"},
                {"caminho": "nao_permitido/arquivo.txt", "tamanho": 4, "sha256": "hash"},
                {"caminho": "casos/123/arquivo.txt", "tamanho": 4, "sha256": hashlib.sha256(b"teste").hexdigest()}
            ]
            z.writestr("manifest.json", json.dumps({"schema": "cpj-export/1", "arquivos": arqs}))
            z.writestr("dados/../fora.txt", b"test")
            z.writestr("dados/nao_permitido/arquivo.txt", b"test")
            z.writestr("dados/casos/123/arquivo.txt", b"teste")

        tid = self.tarefas.nova("importar", "Teste", "user")
        with self.assertRaisesRegex(ValueError, "Pacote com caminho não permitido|Caminho inseguro"):
            self.tarefas.importar(tid, str(zip_path))

    def test_importar_cancelamento(self):
        # Cria pacote grande ficticio
        zip_path = self.ws / "cancelar.zip"
        with zipfile.ZipFile(zip_path, "w") as z:
            arqs = []
            for i in range(10):
                caminho = f"casos/123/arquivo_{i}.txt"
                arqs.append({"caminho": caminho, "tamanho": 4, "sha256": hashlib.sha256(b"test").hexdigest()})
                z.writestr("dados/" + caminho, b"test")
            z.writestr("manifest.json", json.dumps({"schema": "cpj-export/1", "arquivos": arqs}))

        tid = self.tarefas.nova("importar", "Teste", "user")
        self.tarefas.cancelar(tid)
        with self.assertRaisesRegex(ValueError, "Tarefa cancelada"):
            self.tarefas.importar(tid, str(zip_path))

        self.assertFalse((self.ws / "casos").exists() and len(list((self.ws / "casos").iterdir())) > 0)

if __name__ == "__main__":
    unittest.main()
