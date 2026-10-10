"""Normalização derivada de transcrições fictícias, sem alterar a fonte."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[2] / "skills/pdf-autos-policiais/scripts/normalizar.py"


class Normalizacao(unittest.TestCase):
    def executar(self, texto):
        with tempfile.TemporaryDirectory(prefix="cpj-px07-") as pasta:
            fonte = Path(pasta) / "transcricao.md"
            dados = texto.replace("\n", "\r\n").encode("utf-8")
            fonte.write_bytes(dados)
            r = subprocess.run([sys.executable, "-X", "utf8", str(SCRIPT), str(fonte)],
                               capture_output=True, text=True, encoding="utf-8", timeout=30)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(fonte.read_bytes(), dados)
            resultado = (fonte.parent / "transcricao-normalizada.md").read_text(encoding="utf-8")
            registro = json.loads((fonte.parent / "normalizacao.json").read_text(encoding="utf-8"))
            self.assertEqual(registro["sha256_fonte"], hashlib.sha256(dados).hexdigest())
            self.assertEqual(registro["sha256_derivado"], hashlib.sha256(
                (fonte.parent / "transcricao-normalizada.md").read_bytes()).hexdigest())
            return resultado, registro

    def test_texto_carimbo_e_rastreabilidade(self):
        texto = '# Transcrição fictícia\n- SHA-256 do original: `123`\n\n---\n## Página 1\n<!-- método: texto-nativo -->\n\ninvesti-\ngação fictícia\n\n\n\nCarimbo: CÓPIA FICTÍCIA\nCarimbo: CÓPIA FICTÍCIA\n'
        saida, reg = self.executar(texto)
        self.assertIn("investigação fictícia", saida)
        self.assertEqual(saida.count("Carimbo: CÓPIA FICTÍCIA"), 1)
        self.assertIn('<!-- método: texto-nativo -->', saida)
        self.assertIn('- SHA-256 do original: `123`', saida)
        self.assertNotIn("\n\n\n", saida)
        self.assertEqual(reg["paginas"], [1])
        self.assertTrue(all(c["pagina"] == 1 and c["linhas_fonte"] for c in reg["alteracoes"]))

    def test_duplicatas_so_complemento_identico_mesma_pagina(self):
        saida, reg = self.executar('## Página 1\nTexto nativo fictício\nTexto nativo fictício\n[OCR da imagem da página]\nTexto nativo fictício\n Texto nativo fictício\n[Transcrição visual complementar]\nTexto nativo fictício\n## Página 2\n[OCR da imagem da página]\nTexto nativo fictício\nCarimbo: CÓPIA FICTÍCIA\n## Página 3\nCarimbo: CÓPIA FICTÍCIA\n')
        self.assertEqual(saida.splitlines().count("Texto nativo fictício"), 3)
        self.assertIn("\n Texto nativo fictício\n", saida)
        self.assertEqual(saida.count("Carimbo: CÓPIA FICTÍCIA"), 2)
        self.assertEqual(reg["paginas"], [1, 2, 3])
        self.assertEqual(sum(c["regra"] == "duplicata_complemento" for c in reg["alteracoes"]), 2)

    def test_digitos_tabelas_financas_e_blocos_preservados(self):
        linhas = ['Pix R$ 1.234,56', '| Titular | Valor |', '| FICTÍCIO | R$ 100,00 |',
                  'Conta 123-', '456', 'valor transferido', 'CPF 123.456.789-00',
                  'Carimbo: folha 2', 'coluna\ttexto', 'nome  valor', 'devolução de cem reais']
        corpo = '\n'.join(linhas)
        saida, reg = self.executar('## Página 1\n' + corpo + '\n[OCR da imagem da página]\n' + corpo + '\n```\nexem-\nplo\n```\n## Página 2\nfraude-\n## Página 3\neletrônica\n')
        for linha in linhas:
            self.assertEqual(saida.splitlines().count(linha), 2, linha)
        self.assertIn('exem-\nplo', saida)
        self.assertIn('fraude-\n## Página 3\neletrônica', saida)
        self.assertEqual(reg["alteracoes"], [])

    def test_recusa_derivado_como_fonte_sem_escrever(self):
        with tempfile.TemporaryDirectory(prefix="cpj-px07-limite-") as pasta:
            fonte = Path(pasta) / "transcricao-normalizada.md"
            original = b"## Pagina ficticia\nNAO SOBRESCREVER\n"
            fonte.write_bytes(original)
            r = subprocess.run([sys.executable, str(SCRIPT), str(fonte)],
                               capture_output=True, text=True, encoding="utf-8", timeout=30)
            self.assertEqual(r.returncode, 2)
            self.assertEqual(fonte.read_bytes(), original)
            self.assertFalse((fonte.parent / "normalizacao.json").exists())


if __name__ == "__main__":
    unittest.main()
