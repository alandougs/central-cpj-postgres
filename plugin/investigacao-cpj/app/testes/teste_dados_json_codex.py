"""Regressão DJ01: JSON consolidado da extração com origem preservada."""
import csv
import json
import shutil
import subprocess
import sys
import unittest
import uuid
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[4]
SCRIPT = RAIZ / "plugin" / "investigacao-cpj" / "skills" / "pdf-autos-policiais" / "scripts" / "dados_json.py"


class DadosJsonDaExtracao(unittest.TestCase):
    def test_consolida_paginas_tabelas_e_entidades_sem_perder_origem(self):
        saida = RAIZ / f".tmp-dados-json-{uuid.uuid4().hex}"
        saida.mkdir()
        try:
            (saida / "transcricao.md").write_text(
                "# Transcrição — ficticio.pdf\n\n"
                "---\n## Página 1\n<!-- método: texto-nativo -->\n\nPrimeira página.\n\n"
                "---\n## Página 2\n<!-- método: ocr-tesseract | confiança OCR 81.5% | ⚠ CONFERIR -->\n\nSegunda página.\n",
                encoding="utf-8",
            )
            (saida / "relatorio_extracao.json").write_text(json.dumps({
                "arquivo": "ficticio.pdf",
                "sha256_original": "abc123",
                "paginas": 2,
                "conferir_visualmente": [2],
            }), encoding="utf-8")
            with (saida / "entidades.csv").open("w", newline="", encoding="utf-8-sig") as arquivo:
                writer = csv.DictWriter(arquivo, fieldnames=["tipo", "valor", "pagina_pdf", "trecho", "status"], delimiter=";")
                writer.writeheader()
                writer.writerow({"tipo": "CPF", "valor": "999.888.777-66", "pagina_pdf": 2,
                                 "trecho": "CPF candidato", "status": "pendente de conferência"})
            tabelas = saida / "tabelas"
            tabelas.mkdir()
            with (tabelas / "t001_pag0002.csv").open("w", newline="", encoding="utf-8-sig") as arquivo:
                writer = csv.DictWriter(arquivo, fieldnames=["pagina_pdf", "col1", "col2"], delimiter=";")
                writer.writeheader()
                writer.writerow({"pagina_pdf": 2, "col1": "01/01/2099", "col2": "R$ 10,00"})

            resultado = subprocess.run([sys.executable, str(SCRIPT), str(saida)], capture_output=True, text=True)
            self.assertEqual(resultado.returncode, 0, resultado.stderr)

            dados = json.loads((saida / "dados_extraidos.json").read_text(encoding="utf-8"))
            self.assertEqual(dados["schema"], "cpj-dados-extraidos/1")
            self.assertEqual(dados["extracao"]["sha256_original"], "abc123")
            self.assertEqual(dados["paginas"], [
                {"pagina_pdf": 1, "metodo": "texto-nativo", "texto": "Primeira página."},
                {"pagina_pdf": 2, "metodo": "ocr-tesseract", "texto": "Segunda página."},
            ])
            self.assertEqual(dados["tabelas"], [{
                "arquivo": "t001_pag0002.csv", "pagina_pdf": 2,
                "linhas": [{"pagina_pdf": "2", "col1": "01/01/2099", "col2": "R$ 10,00"}],
            }])
            self.assertEqual(dados["entidades"][0]["valor"], "999.888.777-66")
            self.assertEqual(dados["entidades"][0]["status"], "pendente de conferência")
        finally:
            shutil.rmtree(saida)


if __name__ == "__main__":
    unittest.main(verbosity=2)
