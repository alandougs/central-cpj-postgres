"""CL06: execute o exportador somente como subprocesso numa cópia fictícia."""
import ast
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).with_name("exportar-portatil.py")


class Exportacao(unittest.TestCase):
    def gerar(self, frontmatter):
        with tempfile.TemporaryDirectory(prefix="cpj-cl06-ficticio-") as pasta:
            raiz = Path(pasta)
            ferramentas = raiz / "ferramentas"
            ferramentas.mkdir()
            copia = ferramentas / SCRIPT.name
            shutil.copy2(SCRIPT, copia)
            # Só leitura da AST: o módulo possui geração no topo e não é importado.
            arvore = ast.parse(copia.read_text(encoding="utf-8"))
            pacotes = next(ast.literal_eval(n.value) for n in arvore.body if isinstance(n, ast.Assign)
                           and any(isinstance(t, ast.Name) and t.id == "PACOTES" for t in n.targets))
            (raiz / "AGENTS.md").write_text("## 1. Regras\n\nREGRA FICTICIA.\n\n## 2. Estrutura\n", encoding="utf-8")
            plugin = raiz / "plugin/investigacao-cpj"
            for _, _, partes in pacotes:
                for rel in partes:
                    destino = raiz / rel[1:] if rel.startswith("@") else plugin / rel
                    destino.parent.mkdir(parents=True, exist_ok=True)
                    destino.write_text("# Corpo fictício\n\nFONTE FICTICIA: " + rel + "\n", encoding="utf-8")
            alvo = plugin / "agents/analista-documental.md"
            corpo = "# Corpo preservado\n\nNÃO MODIFICAR: texto fictício, número 123 e acentuação.\n"
            alvo.write_text("---\nname: ficticio\n" + frontmatter + "\n---\n\n" + corpo, encoding="utf-8")
            original = alvo.read_bytes()
            ambiente = dict(os.environ, PYTHONUTF8="1", CPJ_WORKSPACE=str(raiz), APPDATA=str(raiz / "appdata-ficticio"))
            r = subprocess.run([sys.executable, str(copia)], cwd=raiz, env=ambiente,
                               capture_output=True, text=True, encoding="utf-8", timeout=30)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(alvo.read_bytes(), original, "O exportador não pode alterar a fonte")
            arquivos = sorted((raiz / "portatil").glob("*.md"))
            self.assertEqual(len(arquivos), 12)
            self.assertTrue(all(p.stat().st_size for p in arquivos))
            saida = (raiz / "portatil/02-analisar-ip.md").read_text(encoding="utf-8")
            self.assertIn("## Corpo preservado\n\nNÃO MODIFICAR: texto fictício, número 123 e acentuação.", saida)
            return saida

    def test_01_descricao_dobrada_completa_com_dois_pontos(self):
        saida = self.gerar("description: >-\n  Analista fictício: páginas 1-100.\n  Segunda linha preservada.\ntools: Read")
        self.assertIn("> Analista fictício: páginas 1-100. Segunda linha preservada.\n\n", saida)
        self.assertNotIn("> >-", saida)
        self.assertNotIn("tools: Read", saida)

    def test_02_descricao_literal_preserva_linhas(self):
        saida = self.gerar("description: |\n  Primeira linha fictícia.\n  Segunda linha: com detalhe.\nmodel: ficticio")
        self.assertIn("> Primeira linha fictícia.\n> Segunda linha: com detalhe.\n\n", saida)
        self.assertNotIn("model: ficticio", saida)

    def test_03_descricao_inline_existente_preservada(self):
        saida = self.gerar("description: Descrição inline fictícia sem alteração.\ntools: Read")
        self.assertIn("> Descrição inline fictícia sem alteração.\n\n", saida)

    def test_04_sem_descricao_preserva_corpo(self):
        saida = self.gerar("tools: Read")
        self.assertNotIn("> >-", saida)


if __name__ == "__main__": unittest.main(verbosity=2)
