"""AS01: gravação de caso.json com bloqueios Windows, sempre em dados fictícios."""
import copy
import errno
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[2] / "skills/base-cpj/scripts/caso.py"


class GravacaoCasoAS01(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cpj-as01-")
        self.addCleanup(self.temp.cleanup)
        self.ws = Path(self.temp.name)
        with mock.patch.dict(os.environ, {"CPJ_WORKSPACE": str(self.ws)}):
            spec = importlib.util.spec_from_file_location("caso_as01", SCRIPT)
            self.caso = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.caso)
        self.id = "OS-AS01-FICTICIO"
        self.pasta = self.ws / "casos" / self.id
        self.pasta.mkdir(parents=True)
        self.path = self.pasta / "caso.json"
        self.anterior = {"id": self.id, "revisao": 7, "visto": False,
                         "atualizado_em": "2026-01-01T00:00:00"}
        self.path.write_text(json.dumps(self.anterior), encoding="utf-8")
        self.original = self.path.read_bytes()

    def alterado(self):
        return dict(self.anterior, visto=True)

    def assert_gravado(self, registro):
        self.assertEqual(json.loads(self.path.read_text(encoding="utf-8")), registro)
        self.assertEqual(registro["revisao"], 8)
        self.assertTrue(registro["visto"])
        self.assertEqual(list(self.pasta.glob(".caso.*.tmp")), [])

    def test_recusa_transitoria_preserva_original_ate_troca_atomica(self):
        replace = os.replace
        chamadas = 0

        def recusar_uma_vez(origem, destino):
            nonlocal chamadas
            chamadas += 1
            self.assertEqual(self.path.read_bytes(), self.original)
            if chamadas == 1:
                erro = PermissionError(errno.EACCES, "bloqueio fictício de arquivo Windows")
                erro.winerror = 5
                raise erro
            return replace(origem, destino)

        registro = self.alterado()
        with mock.patch.object(self.caso.os, "replace", side_effect=recusar_uma_vez):
            self.assertIs(self.caso.salvar(registro, revisao_esperada=7), registro)
        self.assertEqual(chamadas, 2)
        self.assert_gravado(registro)

    @unittest.skipUnless(os.name == "nt", "Bloqueio de exclusão nativo do Windows")
    def test_leitor_windows_sem_delete_share_nao_produz_falha_transitoria(self):
        # O open padrão do Windows permite leitura/escrita, mas impede a troca do
        # destino enquanto o leitor está aberto. A pausa libera esse leitor real.
        leitor = self.path.open("rb")
        registro = self.alterado()
        try:
            with mock.patch.object(self.caso.time, "sleep", side_effect=lambda _: leitor.close()) as pausa:
                self.caso.salvar(registro, revisao_esperada=7)
            pausa.assert_called_once()
        finally:
            leitor.close()
        self.assert_gravado(registro)

    def test_recusa_persistente_nao_avanca_revisao_e_libera_trava_para_nova_tentativa(self):
        registro = self.alterado()
        antes = copy.deepcopy(registro)
        with mock.patch.object(self.caso.os, "replace", side_effect=PermissionError(errno.EACCES, "negado")) as trocar:
            with mock.patch.object(self.caso.time, "sleep"):
                with self.assertRaises(PermissionError):
                    self.caso.salvar(registro, revisao_esperada=7)
        self.assertEqual(trocar.call_count, 3)
        self.assertEqual(self.path.read_bytes(), self.original)
        self.assertEqual(registro, antes)
        self.assertEqual(list(self.pasta.glob(".caso.*.tmp")), [])
        self.caso.salvar(registro, revisao_esperada=7)
        self.assert_gravado(registro)

    def test_outro_erro_de_io_nao_e_retentado_nem_deixa_temporario(self):
        registro = self.alterado()
        antes = copy.deepcopy(registro)
        with mock.patch.object(self.caso.os, "replace", side_effect=OSError(errno.ENOSPC, "disco cheio fictício")) as trocar:
            with mock.patch.object(self.caso.time, "sleep") as pausa:
                with self.assertRaises(OSError) as erro:
                    self.caso.salvar(registro)
        self.assertEqual(erro.exception.errno, errno.ENOSPC)
        trocar.assert_called_once()
        pausa.assert_not_called()
        self.assertEqual(self.path.read_bytes(), self.original)
        self.assertEqual(registro, antes)
        self.assertEqual(list(self.pasta.glob(".caso.*.tmp")), [])

    def test_conflito_de_revisao_nao_tenta_substituir_arquivo(self):
        registro = self.alterado()
        with mock.patch.object(self.caso.os, "replace") as trocar:
            with self.assertRaises(self.caso.ConflitoRevisao):
                self.caso.salvar(registro, revisao_esperada=6)
        trocar.assert_not_called()
        self.assertEqual(self.path.read_bytes(), self.original)
        self.assertEqual(list(self.pasta.glob(".caso.*.tmp")), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
