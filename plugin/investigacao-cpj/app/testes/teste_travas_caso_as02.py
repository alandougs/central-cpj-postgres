"""AS02: aquisição malsucedida não retém travas de casos fictícios."""
from concurrent.futures import ThreadPoolExecutor
import errno
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[2] / "skills/base-cpj/scripts/caso.py"


class TravasCasoAS02(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cpj-as02-")
        self.addCleanup(self.temp.cleanup)
        with mock.patch.dict(os.environ, {"CPJ_WORKSPACE": self.temp.name}):
            spec = importlib.util.spec_from_file_location("caso_as02", SCRIPT)
            self.caso = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.caso)
        self.id = "OS-AS02-FICTICIO"
        Path(self.caso.caminho(self.id)).mkdir(parents=True)

    def adquirir_em_outra_thread(self):
        def adquirir():
            with self.caso.trava(self.id, timeout=0.25):
                return True
        with ThreadPoolExecutor(max_workers=1) as executor:
            self.assertTrue(executor.submit(adquirir).result(timeout=2))

    def test_falha_ao_abrir_arquivo_de_trava_libera_rlock_e_estado_local(self):
        trava = self.caso.trava(self.id, timeout=0.25)
        with mock.patch("builtins.open", side_effect=PermissionError(errno.EACCES, "recusa fictícia")):
            with self.assertRaises(PermissionError):
                with trava:
                    self.fail("Não deveria adquirir a trava")
        self.adquirir_em_outra_thread()
        self.assertNotIn(self.id, self.caso._get_casos_ativos())
        self.assertIsNone(trava.lock_file)

    def test_falha_ao_criar_pasta_nao_bloqueia_gravacoes_futuras(self):
        with mock.patch.object(self.caso.os, "makedirs", side_effect=OSError(errno.ENOSPC, "disco cheio fictício")):
            with self.assertRaises(OSError):
                with self.caso.trava(self.id, timeout=0.25):
                    self.fail("Não deveria adquirir a trava")
        self.adquirir_em_outra_thread()
        self.assertNotIn(self.id, self.caso._get_casos_ativos())

    def test_excecao_no_corpo_libera_trava_para_outra_thread(self):
        with self.assertRaisesRegex(ValueError, "falha fictícia no corpo"):
            with self.caso.trava(self.id, timeout=0.25):
                raise ValueError("falha fictícia no corpo")
        self.adquirir_em_outra_thread()

    def test_interrupcao_durante_espera_fecha_arquivo_e_libera_trava(self):
        trava = self.caso.trava(self.id, timeout=0.25)
        chamada_lock = "msvcrt.locking" if os.name == "nt" else "fcntl.flock"
        with mock.patch(chamada_lock, side_effect=BlockingIOError(errno.EAGAIN, "ocupado fictício")):
            with mock.patch.object(self.caso.time, "sleep", side_effect=KeyboardInterrupt):
                with self.assertRaises(KeyboardInterrupt):
                    with trava:
                        self.fail("Não deveria adquirir a trava")
        self.adquirir_em_outra_thread()
        self.assertNotIn(self.id, self.caso._get_casos_ativos())
        self.assertIsNone(trava.lock_file)

    def test_reentrancia_mantem_exclusao_ate_saida_externa(self):
        with ThreadPoolExecutor(max_workers=1) as executor:
            with self.caso.trava(self.id):
                with self.caso.trava(self.id):
                    self.assertEqual(self.caso._get_casos_ativos()[self.id], 2)
                self.assertEqual(self.caso._get_casos_ativos()[self.id], 1)

                def tentar():
                    with self.caso.trava(self.id, timeout=0.05):
                        return True

                with self.assertRaises(self.caso.CasoOcupado):
                    executor.submit(tentar).result(timeout=2)
            self.assertTrue(executor.submit(tentar).result(timeout=2))


if __name__ == "__main__":
    unittest.main(verbosity=2)
