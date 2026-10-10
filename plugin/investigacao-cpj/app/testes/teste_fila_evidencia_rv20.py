#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""RV20 — `fila-tarefas.py concluir` confere a entrega: arquivo reservado com 0 bytes impede a conclusão
(causa das reaberturas FT01/FD01/SD01/RV03–RV05); ausente impede conclusão; exceção exige justificativa registrada."""
import importlib
import io
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(RAIZ / "ferramentas"))
fila = importlib.import_module("fila-tarefas")

QUADRO = """# Fila de teste

| ID | Responsável | Estado | Entrega | Arquivos reservados |
|---|---|---|---|---|
| T01 | Agente-A | em andamento | Entrega com arquivos | `src/a.py`, `src/b.py`, `src/pacote/`, `src/gerados/*.csv`, `src/pacote/__init__.py` |
| T02 | Agente-A | em andamento | Entrega com arquivo ausente | `src/a.py`, `docs/ausente.md` |
"""


class ConferenciaDeEntrega(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="cpj-fila-rv20-", ignore_cleanup_errors=True)
        self.addCleanup(self.tmp.cleanup)
        self.raiz = Path(self.tmp.name)
        (self.raiz / "src" / "pacote").mkdir(parents=True)
        (self.raiz / "src" / "a.py").write_text("print('a')\n", encoding="utf-8")
        (self.raiz / "src" / "b.py").write_text("print('b')\n", encoding="utf-8")
        (self.raiz / "src" / "pacote" / "__init__.py").write_text("", encoding="utf-8")  # vazio legítimo
        self.quadro = self.raiz / "TAREFAS-COMPARTILHADAS.md"
        self.quadro.write_text(QUADRO, encoding="utf-8")
        p = mock.patch.object(fila, "RAIZ", self.raiz)
        p.start()
        self.addCleanup(p.stop)

    def estado(self, id_):
        return fila.linhas_tarefas(self.quadro.read_text(encoding="utf-8"))[id_][1][2]

    def concluir(self, id_="T01", **kw):
        return fila.atualizar(self.quadro, "concluir", id_, "Agente-A", "testes ok", **kw)

    def test_01_entrega_integra_conclui(self):
        self.concluir()
        self.assertEqual(self.estado("T01"), "concluída")

    def test_02_arquivo_com_zero_bytes_impede_a_conclusao(self):
        (self.raiz / "src" / "b.py").write_text("", encoding="utf-8")
        antes = self.quadro.read_bytes()
        with self.assertRaises(ValueError) as e:
            self.concluir()
        self.assertIn("src/b.py", str(e.exception))
        self.assertIn("0 bytes", str(e.exception))
        self.assertEqual(self.estado("T01"), "em andamento")
        self.assertEqual(self.quadro.read_bytes(), antes, "a fila não pode mudar quando a conclusão é recusada")

    def test_03_init_vazio_e_pasta_e_padrao_nao_contam(self):
        self.concluir()  # __init__.py vazio, src/pacote/ e src/gerados/*.csv não geram erro
        self.assertEqual(self.estado("T01"), "concluída")

    def test_04_arquivo_ausente_recusa_sem_alterar_quadro(self):
        antes = self.quadro.read_bytes()
        with self.assertRaisesRegex(ValueError, "docs/ausente.md"):
            self.concluir("T02")
        self.assertEqual(self.estado("T02"), "em andamento")
        self.assertEqual(self.quadro.read_bytes(), antes)
        self.assertFalse(self.quadro.with_name(self.quadro.name + ".lock").exists())

    def test_05_excecao_exige_justificativa_de_15_caracteres(self):
        (self.raiz / "src" / "b.py").write_text("", encoding="utf-8")
        for curta in ("", "   ", "curta"):
            with self.assertRaises(ValueError, msg=repr(curta)):
                self.concluir(sem_conferir=curta)
        self.assertEqual(self.estado("T01"), "em andamento")

    def test_06_excecao_justificada_conclui_e_fica_no_registro(self):
        (self.raiz / "src" / "b.py").write_text("", encoding="utf-8")
        self.concluir(sem_conferir="Arquivo placeholder intencional do pacote")
        self.assertEqual(self.estado("T01"), "concluída")
        ultima = self.quadro.read_text(encoding="utf-8").splitlines()[-1]
        self.assertIn("src/b.py", ultima)
        self.assertIn("placeholder intencional", ultima)

    def test_09_ausente_excecao_exige_motivo_e_registra_ambas_lacunas(self):
        (self.raiz / "src" / "a.py").write_text("", encoding="utf-8")
        antes = self.quadro.read_bytes()
        for curta in ("", "   ", "curta"):
            with self.assertRaises(ValueError):
                self.concluir("T02", sem_conferir=curta)
            self.assertEqual(self.quadro.read_bytes(), antes)
        self.concluir("T02", sem_conferir="Entrega parcial autorizada no teste ficticio")
        ultima = self.quadro.read_text(encoding="utf-8").splitlines()[-1]
        self.assertIn("Entrega parcial autorizada", ultima)
        self.assertIn("vazios: src/a.py", ultima)
        self.assertIn("ausentes: docs/ausente.md", ultima)

    def test_10_alias_de_arquivo_ausente_e_preservado(self):
        campos = ["T03", "Agente-A", "em andamento", "Alias", "`app/rotas/ficticio.py`"]
        with self.quadro.open("a", encoding="utf-8") as f:
            f.write("| " + " | ".join(campos) + " |\n")
        antes = self.quadro.read_bytes()
        with self.assertRaisesRegex(ValueError, "plugin/investigacao-cpj/app/rotas/ficticio.py"):
            self.concluir("T03")
        self.assertEqual(self.quadro.read_bytes(), antes)
        arquivo = self.raiz / "plugin/investigacao-cpj/app/rotas/ficticio.py"
        arquivo.parent.mkdir(parents=True)
        arquivo.write_text("# codigo ficticio\n", encoding="utf-8")
        self.concluir("T03")
        self.assertEqual(self.estado("T03"), "concluída")

    def test_11_init_ausente_nao_e_arquivo_vazio_legitimo(self):
        (self.raiz / "src/pacote/__init__.py").unlink()
        with self.assertRaisesRegex(ValueError, "src/pacote/__init__.py"):
            self.concluir()
        self.assertEqual(self.estado("T01"), "em andamento")

    def test_12_cli_real_isolada_recusa_ausente_e_aceita_excecao(self):
        ferramentas = self.raiz / "ferramentas"
        ferramentas.mkdir()
        script = ferramentas / "fila-tarefas.py"
        shutil.copy2(Path(fila.__file__), script)
        base = [sys.executable, str(script), "--arquivo", str(self.quadro), "concluir", "T02",
                "--agente", "Agente-A", "--resultado", "Teste ficticio"]
        antes = self.quadro.read_bytes()
        negativa = subprocess.run(base, capture_output=True, text=True, encoding="utf-8", timeout=20)
        self.assertEqual(negativa.returncode, 1, negativa.stdout + negativa.stderr)
        self.assertIn("docs/ausente.md", negativa.stdout)
        self.assertEqual(self.quadro.read_bytes(), antes)
        positiva = subprocess.run(base + ["--sem-conferir-arquivos", "Ausencia intencional autorizada em fixture"],
                                  capture_output=True, text=True, encoding="utf-8", timeout=20)
        self.assertEqual(positiva.returncode, 0, positiva.stdout + positiva.stderr)
        self.assertEqual(self.estado("T02"), "concluída")
        self.assertIn("ausentes: docs/ausente.md", self.quadro.read_text(encoding="utf-8").splitlines()[-1])

    def test_07_liberar_nao_confere_arquivos(self):
        (self.raiz / "src" / "b.py").write_text("", encoding="utf-8")
        fila.atualizar(self.quadro, "liberar", "T01", "Agente-A", "parei no meio")
        self.assertEqual(self.estado("T01"), "disponível")

    def test_08_linha_de_comando_recusa_e_aceita_a_excecao(self):
        (self.raiz / "src" / "b.py").write_text("", encoding="utf-8")
        base = ["fila-tarefas.py", "--arquivo", str(self.quadro), "concluir", "T01", "--agente", "Agente-A", "--resultado", "ok"]
        saida = io.StringIO()
        with mock.patch.object(sys, "argv", base), redirect_stdout(saida):
            codigo = fila.main()
        self.assertEqual(codigo, 1)
        self.assertIn("0 bytes", saida.getvalue())
        with mock.patch.object(sys, "argv", base + ["--sem-conferir-arquivos", "Placeholder intencional do pacote"]), \
                redirect_stdout(io.StringIO()):
            self.assertEqual(fila.main(), 0)
        self.assertEqual(self.estado("T01"), "concluída")


if __name__ == "__main__":
    unittest.main(verbosity=2)
