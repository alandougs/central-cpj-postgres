"""Ferramentas API não podem alcançar originais ou arquivos de outro caso por links."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import executores_llm as EL


class ExecutoresRV17(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cpj-api-rv17-")
        self.addCleanup(self.temp.cleanup)
        self.ws = Path(self.temp.name)
        self.cid = "OS-FICTICIO-2099"
        self.raiz = self.ws / "casos" / self.cid
        for pasta in ("00-originais", "01-extracao", "02-analise", "03-relatorios", "ia-logs"):
            (self.raiz / pasta).mkdir(parents=True)
        self.original = self.raiz / "00-originais" / "original.md"
        self.original.write_text("Original fictício intocável", encoding="utf-8")

    def link(self, alvo, destino, diretorio=False):
        try:
            destino.symlink_to(alvo, target_is_directory=diretorio)
        except OSError:
            self.skipTest("Ambiente sem permissão para criar links simbólicos")

    def test_leitura_nao_alcanca_original_por_alias(self):
        self.link(self.original, self.raiz / "02-analise" / "alias.md")
        with self.assertRaises(ValueError):
            EL._tool(str(self.ws), self.cid, "ler_arquivo", {"caminho": "02-analise/alias.md"})

    def test_escrita_nao_altera_original_por_alias(self):
        self.link(self.original, self.raiz / "03-relatorios" / "alias.md")
        with self.assertRaises(ValueError):
            EL._tool(str(self.ws), self.cid, "gravar_arquivo", {"caminho": "03-relatorios/alias.md", "conteudo": "Alteração"})
        self.assertEqual(self.original.read_text(encoding="utf-8"), "Original fictício intocável")

    def test_geracao_docx_nao_acessa_diretorio_externo_por_link(self):
        externo = self.ws / "outro-caso"
        externo.mkdir()
        (externo / "minuta-v01.md").write_text("Fictício", encoding="utf-8")
        (self.raiz / "03-relatorios").rmdir()
        self.link(externo, self.raiz / "03-relatorios", diretorio=True)
        with patch.object(EL.subprocess, "run") as rodar:
            with self.assertRaises(ValueError):
                EL._tool(str(self.ws), self.cid, "gerar_docx", {"minuta": "minuta-v01.md"})
        rodar.assert_not_called()

    def test_listagem_so_inclui_arquivos_que_o_agente_pode_ler(self):
        (self.raiz / "02-analise" / "ficha.md").write_text("Fictício", encoding="utf-8")
        (self.raiz / "caso.json").write_text("{}", encoding="utf-8")
        (self.raiz / "ia-progresso.json").write_text("{}", encoding="utf-8")
        self.link(self.original, self.raiz / "02-analise" / "alias.md")
        self.assertEqual(EL._listar(str(self.ws), self.cid), ["02-analise/ficha.md", "caso.json"])

    def test_escrita_regular_e_atomica_mesmo_com_falha_na_substituicao(self):
        alvo = self.raiz / "02-analise" / "ficha.md"
        alvo.write_text("Versão anterior fictícia", encoding="utf-8")
        with patch.object(EL.os, "replace", side_effect=OSError("Falha fictícia")):
            with self.assertRaises(OSError):
                EL._tool(str(self.ws), self.cid, "gravar_arquivo", {"caminho": "02-analise/ficha.md", "conteudo": "Versão nova"})
        self.assertEqual(alvo.read_text(encoding="utf-8"), "Versão anterior fictícia")
        self.assertEqual([p.name for p in alvo.parent.iterdir()], ["ficha.md"])

    def test_ferramentas_continuam_lendo_e_gravando_artefatos(self):
        r = EL._tool(str(self.ws), self.cid, "gravar_arquivo", {"caminho": "02-analise/ficha.md", "conteudo": "Fictício\n"})
        self.assertTrue(r["ok"])
        r = EL._tool(str(self.ws), self.cid, "ler_arquivo", {"caminho": "02-analise/ficha.md"})
        self.assertEqual(r["conteudo"], "1: Fictício\n")


if __name__ == "__main__":
    unittest.main(verbosity=2)
