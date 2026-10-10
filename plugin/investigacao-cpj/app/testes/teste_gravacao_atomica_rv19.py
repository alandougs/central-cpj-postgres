#!/usr/bin/env python3
"""RV19 — `gravar_arquivo` do executor por API não pode deixar arquivo pela metade: grava em temporário no mesmo
diretório e substitui com os.replace. Falha simulada no meio da escrita; dados fictícios, workspace temporário."""
import builtins
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))
import executores_llm as E  # noqa: E402

ORIGINAL = "seq;valor\n1;100,00\n2;200,00\n"
NOVO = "seq;valor\n1;999,99\n2;888,88\n3;777,77\n"


class FalhaNoMeio:
    """Embrulha o arquivo aberto para escrita: grava a metade e levanta OSError (disco cheio, processo morto…)."""

    def __init__(self, f):
        self._f = f

    def write(self, s):
        self._f.write(s[: len(s) // 2])
        self._f.flush()
        raise OSError("falha simulada no meio da escrita")

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self._f.close()
        return False

    def __getattr__(self, nome):
        return getattr(self._f, nome)


def abrir_com_falha(real):
    def _abrir(arq, modo="r", *a, **k):
        f = real(arq, modo, *a, **k)
        return FalhaNoMeio(f) if "w" in modo else f
    return _abrir


class GravacaoAtomica(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cpj-atomica-rv19-", ignore_cleanup_errors=True)
        self.addCleanup(self.temp.cleanup)
        self.ws = self.temp.name
        self.pasta = Path(self.ws) / "casos" / "OS-1-2099" / "02-analise"
        self.pasta.mkdir(parents=True)
        self.alvo = self.pasta / "fluxo-financeiro.csv"

    def grava(self, conteudo=NOVO, caminho="02-analise/fluxo-financeiro.csv"):
        return E._tool(self.ws, "OS-1-2099", "gravar_arquivo", {"caminho": caminho, "conteudo": conteudo})

    def sobras(self):
        return sorted(p.name for p in self.pasta.iterdir() if p.name != self.alvo.name)

    def test_01_gravacao_normal_substitui_e_nao_deixa_temporario(self):
        self.alvo.write_text(ORIGINAL, encoding="utf-8")
        r = self.grava()
        self.assertTrue(r["ok"])
        self.assertEqual(r["caminho"], "02-analise/fluxo-financeiro.csv")
        self.assertEqual(self.alvo.read_text(encoding="utf-8"), NOVO)
        self.assertEqual(self.sobras(), [])

    def test_02_arquivo_novo_e_criado_com_quebra_de_linha_unix(self):
        self.grava("a\nb\n")
        self.assertEqual(self.alvo.read_bytes(), b"a\nb\n")  # sem converter para CRLF no Windows

    def test_03_falha_no_meio_da_escrita_preserva_o_arquivo_anterior(self):
        self.alvo.write_text(ORIGINAL, encoding="utf-8")
        with mock.patch.object(builtins, "open", abrir_com_falha(builtins.open)), \
                mock.patch.object(io, "open", abrir_com_falha(io.open)):
            with self.assertRaises(OSError):
                self.grava()
        self.assertEqual(self.alvo.read_text(encoding="utf-8"), ORIGINAL, "o arquivo anterior tem de continuar inteiro")
        self.assertEqual(self.sobras(), [], "nenhum temporário pode sobrar")

    def test_04_falha_na_substituicao_preserva_o_anterior_e_limpa_o_temporario(self):
        self.alvo.write_text(ORIGINAL, encoding="utf-8")
        with mock.patch.object(E.os, "replace", side_effect=OSError("bloqueado")):
            with self.assertRaises(OSError):
                self.grava()
        self.assertEqual(self.alvo.read_text(encoding="utf-8"), ORIGINAL)
        self.assertEqual(self.sobras(), [])

    def test_05_validacoes_continuam_antes_de_tocar_o_disco(self):
        self.alvo.write_text(ORIGINAL, encoding="utf-8")
        for caminho in ("00-originais/x.md", "01-extracao/x.md", "../x.md", "02-analise/x.exe", "02-analise/../../x.md"):
            with self.assertRaises(ValueError, msg=caminho):
                self.grava(caminho=caminho)
        with self.assertRaises(ValueError):
            self.grava("x" * 2_000_001)
        self.assertEqual(self.alvo.read_text(encoding="utf-8"), ORIGINAL)
        self.assertEqual(self.sobras(), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
