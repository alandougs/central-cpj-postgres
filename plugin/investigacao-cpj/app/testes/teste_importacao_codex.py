"""Regressões C03: execute com `python -X utf8 app/testes/teste_importacao_codex.py`.

Usa pacotes e workspaces temporários; não lê autos nem inicia servidor ou IA.
"""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tarefas import EXPORT_SCHEMA, Tarefas  # noqa: E402


class ImportacaoCPJ(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cpj-importacao-codex-")
        self.ws = Path(self.temp.name)
        (self.ws / "casos").mkdir()
        self.tarefas = Tarefas(str(self.ws), None, None, iniciar_agente=False)

    def tearDown(self):
        self.temp.cleanup()

    def pacote(self, arquivos, extra=None, hashes=None):
        destino = self.ws / "entrada.zip"
        manifesto = []
        with zipfile.ZipFile(destino, "w") as z:
            for caminho, conteudo in arquivos.items():
                b = conteudo if isinstance(conteudo, bytes) else conteudo.encode("utf-8")
                z.writestr("dados/" + caminho, b)
                manifesto.append({"caminho": caminho, "tamanho": len(b), "sha256": (hashes or {}).get(caminho, hashlib.sha256(b).hexdigest())})
            if extra: z.writestr(extra, b"fora do manifesto")
            z.writestr("manifest.json", json.dumps({"schema": EXPORT_SCHEMA, "arquivos": manifesto}))
        return destino

    def importar(self, pacote):
        tid = self.tarefas.nova("importacao", "Importação fictícia", "teste")
        return tid, self.tarefas.importar(tid, str(pacote))

    def test_recusa_escopo_invalido_antes_de_escrever(self):
        pacote = self.pacote({"config/usuarios.json": "NAO IMPORTAR"})
        with self.assertRaisesRegex(ValueError, "fora do escopo"):
            self.importar(pacote)
        self.assertFalse((self.ws / "config" / "usuarios.json").exists())

    def test_recusa_arquivo_extra_e_checksum_invalido_sem_caso_parcial(self):
        pacote = self.pacote({"casos/OS-1-2099/caso.json": "{}"}, extra="dados/casos/OS-1-2099/intruso.txt")
        with self.assertRaisesRegex(ValueError, "fora do manifesto"):
            self.importar(pacote)
        self.assertFalse((self.ws / "casos" / "OS-1-2099").exists())

        pacote = self.pacote({"casos/OS-2-2099/caso.json": "{}"}, hashes={"casos/OS-2-2099/caso.json": "0" * 64})
        with self.assertRaisesRegex(ValueError, "corrompido"):
            self.importar(pacote)
        self.assertFalse((self.ws / "casos" / "OS-2-2099").exists())

    def test_cancelamento_interrompe_antes_da_confirmacao_sem_gravar(self):
        pacote = self.pacote({"casos/OS-3-2099/caso.json": "x" * (2 << 20)})
        tid = self.tarefas.nova("importacao", "Importação fictícia", "teste")
        original = self.tarefas.at
        cancelou = False
        def acompanhar(tarefa, **kw):
            nonlocal cancelou
            original(tarefa, **kw)
            if tarefa == tid and kw.get("etapa", "").startswith("verificando") and not cancelou:
                cancelou = self.tarefas.cancelar(tid)
        self.tarefas.at = acompanhar
        self.assertIsNone(self.tarefas.importar(tid, str(pacote)))
        self.assertTrue(cancelou)
        self.assertFalse((self.ws / "casos" / "OS-3-2099").exists())

    def test_confirma_caso_inteiro_nao_sobrescreve_e_propaga_indexacao(self):
        existente = self.ws / "casos" / "OS-4-2099"; existente.mkdir()
        (existente / "caso.json").write_text('{"original": true}', encoding="utf-8")
        pacote = self.pacote({
            "casos/OS-4-2099/caso.json": '{"substituido": true}',
            "casos/OS-5-2099/caso.json": '{"novo": true}',
        })
        self.tarefas.indexar = lambda: None
        _, resultado = self.importar(pacote)
        self.assertEqual(resultado["casos_novos"], ["OS-5-2099"])
        self.assertEqual(resultado["casos_ja_existentes"], ["OS-4-2099"])
        self.assertEqual((existente / "caso.json").read_text(encoding="utf-8"), '{"original": true}')
        self.assertEqual((self.ws / "casos" / "OS-5-2099" / "caso.json").read_text(encoding="utf-8"), '{"novo": true}')

        pacote = self.pacote({"casos/OS-6-2099/caso.json": "{}"})
        self.tarefas.indexar = lambda: (_ for _ in ()).throw(RuntimeError("índice fictício indisponível"))
        with self.assertRaisesRegex(RuntimeError, "Importação confirmada, mas a indexação falhou"):
            self.importar(pacote)
        self.assertTrue((self.ws / "casos" / "OS-6-2099" / "caso.json").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
