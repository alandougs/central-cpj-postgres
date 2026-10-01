"""Concorrência de processamento.json em workspace fictício e temporário."""
import concurrent.futures
import errno
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest import mock

APP = Path(__file__).resolve().parents[1]
if str(APP) not in sys.path:
    sys.path.insert(0, str(APP))


class ConcorrenciaProcessamentoF10(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="cpj-f10-")
        cls.ws = Path(cls.temp.name)
        cls.env_anterior = os.environ.get("CPJ_WORKSPACE")
        os.environ["CPJ_WORKSPACE"] = str(cls.ws)
        import servidor
        from rotas import comum

        cls.servidor = servidor
        cls.comum = comum
        cls.paths_anteriores = {
            "comum_ws": cls.comum.WS,
            "caso_ws": cls.comum.C.WS,
            "casos": cls.comum.C.CASOS,
            "modelo": cls.comum.C.MODELO,
        }
        cls.comum.WS = str(cls.ws)
        cls.comum.C.WS = str(cls.ws)
        cls.comum.C.CASOS = str(cls.ws / "casos")
        cls.comum.C.MODELO = str(cls.ws / "casos" / "_MODELO-CASO")
        Path(cls.comum.C.MODELO).mkdir(parents=True)
        (Path(cls.comum.C.MODELO) / "caso.json").write_text(
            json.dumps({"datas": {}, "financeiro": {}, "ip": {}, "resultado": {}, "relatorios": []}),
            encoding="utf-8",
        )
        cls.caso = "OS-F10-CONCORRENCIA"
        cls.comum.C.novo("F10/2099", id_=cls.caso)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()
        cls.comum.WS = cls.paths_anteriores["comum_ws"]
        cls.comum.C.WS = cls.paths_anteriores["caso_ws"]
        cls.comum.C.CASOS = cls.paths_anteriores["casos"]
        cls.comum.C.MODELO = cls.paths_anteriores["modelo"]
        if cls.env_anterior is None:
            os.environ.pop("CPJ_WORKSPACE", None)
        else:
            os.environ["CPJ_WORKSPACE"] = cls.env_anterior

    def test_leitores_e_gravadores_simultaneos_mantem_json_valido(self):
        self.comum.gravar_proc(self.caso, {"trabalhos": [], "sequencia": 0})
        barreira = threading.Barrier(12)
        erros = []
        erros_lock = threading.Lock()

        def gravar(indice):
            barreira.wait()
            for sequencia in range(50):
                self.comum.gravar_proc(self.caso, {
                    "trabalhos": [{"doc": f"ficticio-{indice}", "status": "processando"}],
                    "sequencia": sequencia,
                })

        def ler(_):
            barreira.wait()
            for _ in range(100):
                try:
                    dados = self.comum.ler_proc(self.caso)
                    if not isinstance(dados.get("trabalhos"), list):
                        raise AssertionError("campo trabalhos ausente ou inválido")
                    if not isinstance(dados.get("sequencia"), int):
                        raise AssertionError("JSON parcial ou inválido")
                except Exception as erro:
                    with erros_lock:
                        erros.append(repr(erro))

        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
            futuros = [pool.submit(gravar, i) for i in range(4)]
            futuros += [pool.submit(ler, i) for i in range(8)]
            for futuro in futuros:
                futuro.result(timeout=30)

        self.assertEqual(erros, [])
        self.assertIsInstance(self.comum.ler_proc(self.caso)["sequencia"], int)

    def test_replace_repete_permission_error_transitorio(self):
        replace_real = os.replace
        chamadas = 0

        def replace_com_falha_transitoria(origem, destino):
            nonlocal chamadas
            chamadas += 1
            if chamadas == 1:
                raise PermissionError(errno.EACCES, "arquivo temporariamente bloqueado")
            return replace_real(origem, destino)

        with mock.patch("rotas.comum.os.replace", side_effect=replace_com_falha_transitoria):
            self.comum.gravar_proc(self.caso, {"trabalhos": [], "sequencia": 99})

        self.assertEqual(chamadas, 2)
        self.assertEqual(self.comum.ler_proc(self.caso)["sequencia"], 99)


if __name__ == "__main__":
    unittest.main(verbosity=2)
