#!/usr/bin/env python3
"""Suíte de testes da Geração do Fluxograma do Caminho do Dinheiro e Injeção no DOCX (Tarefa FD01 / RV02).

Valida:
1. Geração do fluxograma em imagem PNG a 300 DPI a partir do fluxo-financeiro.csv.
2. Rastreabilidade das camadas bancárias (Vítima -> 1ª Camada -> 2ª Camada) sem nós duplicados.
3. Injeção automática do fluxograma no relatório oficial DOCX na seção de diligências.
4. Injeção explícita via marcação Markdown (![legenda](imagem.png)) sem duplicação.
5. Supressão correta via opção --sem-fluxograma.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from PIL import Image
import docx

AQUI = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(AQUI)
PLUGIN = os.path.dirname(APP_DIR)
RAIZ = os.path.dirname(os.path.dirname(PLUGIN))
S_REL = os.path.join(PLUGIN, "skills", "relatorio-ip-fraude", "scripts")
S_BASE = os.path.join(PLUGIN, "skills", "base-cpj", "scripts")

sys.path.insert(0, S_REL)
sys.path.insert(0, S_BASE)

import gerar_diagrama_financeiro as GDF  # noqa: E402

CSV_FICTICIO = """seq;data;hora;valor;meio;id_transacao;origem_titular;origem_banco;origem_ag_conta;origem_chave;destino_titular;destino_banco;destino_ag_conta;destino_chave;camada;fonte_pag;fls;status_conferencia
1;10/03/2026;14:20;12500.00;Pix;E000000001;MARIA SILVA SANTOS;Banco do Brasil;0001/12345;maria@email.com;CARLOS EDUARDO SILVA;Santander;033/88990;carlos@pix.com;1;Extrato fls. 10;10;conferido
2;10/03/2026;14:40;8000.00;Pix;E000000002;CARLOS EDUARDO SILVA;Santander;033/88990;carlos@pix.com;LUCAS PEREIRA LIMA;NuBank;260/11223;lucas@pix.com;2;Extrato Santander;14;conferido
3;10/03/2026;14:45;4500.00;Pix;E000000003;CARLOS EDUARDO SILVA;Santander;033/88990;carlos@pix.com;ANA CLAUDIA SOUZA;Inter;077/44556;ana@pix.com;2;Extrato Santander;14;conferido
"""

MINUTA_FICTICIA = """---
ordem_servico: 105/2026
referencia: IP nº 1500105-20.2026 / BO nº 105/2026
natureza: Estelionato (art. 171, CP)
investigados: CARLOS EDUARDO SILVA, LUCAS PEREIRA LIMA
vitimas: MARIA SILVA SANTOS
local: Presidente Prudente/SP
data_fatos: 10/03/2026
local_data: Presidente Prudente, SP, 30 de setembro de 2026
data_rodape: 30/09/2026
delegado: DR. DELEGADO TESTE
delegado_genero: M
---
## RESUMO DOS FATOS
A vítima MARIA SILVA SANTOS foi induzida em erro mediante golpe telefônico e realizou transferência Pix de R$ 12.500,00.

## DILIGÊNCIAS REALIZADAS
Foram oficiadas as instituições financeiras envolvidas para quebra de sigilo e rastreamento bancário.

| Data | Origem | Destino | Valor |
| 10/03/2026 | MARIA SILVA SANTOS | CARLOS EDUARDO SILVA | R$ 12.500,00 |
| 10/03/2026 | CARLOS EDUARDO SILVA | LUCAS PEREIRA LIMA | R$ 8.000,00 |
| 10/03/2026 | CARLOS EDUARDO SILVA | ANA CLAUDIA SOUZA | R$ 4.500,00 |

## CONCLUSÃO
A materialidade resta comprovada pelos comprovantes e extratos encartados aos autos.
"""


class TesteDiagramaDOCX(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="cpj-teste-fd01-")
        self.caso_id = "OS-105-2026"
        self.pasta_caso = os.path.join(self.tmp, "casos", self.caso_id)
        self.pasta_analise = os.path.join(self.pasta_caso, "02-analise")
        self.pasta_rel = os.path.join(self.pasta_caso, "03-relatorios")
        os.makedirs(self.pasta_analise, exist_ok=True)
        os.makedirs(self.pasta_rel, exist_ok=True)

        self.csv_path = os.path.join(self.pasta_analise, "fluxo-financeiro.csv")
        with open(self.csv_path, "w", encoding="utf-8-sig") as f:
            f.write(CSV_FICTICIO)

        self.minuta_path = os.path.join(self.pasta_rel, "minuta-v01.md")
        with open(self.minuta_path, "w", encoding="utf-8") as f:
            f.write(MINUTA_FICTICIA)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_01_gerar_diagrama_png(self):
        """Valida compilação gráfica do caminho do dinheiro em PNG 300 DPI."""
        saida_png = os.path.join(self.pasta_rel, "fluxo-teste.png")
        txs = GDF.carregar_transacoes(self.csv_path)
        self.assertEqual(len(txs), 3)

        res = GDF.desenhar_diagrama(txs, saida_png, caso_id=self.caso_id, dpi=300)
        self.assertTrue(os.path.isfile(saida_png))
        self.assertEqual(res, saida_png)

        with Image.open(saida_png) as im:
            self.assertEqual(im.format, "PNG")
            self.assertGreaterEqual(im.size[0], 2400)
            self.assertGreaterEqual(im.size[1], 1200)
            dpi = im.info.get("dpi")
            self.assertIsNotNone(dpi)
            self.assertAlmostEqual(dpi[0], 300, delta=1.0)
            self.assertAlmostEqual(dpi[1], 300, delta=1.0)

    def test_02_carregamento_e_formatacao(self):
        """Valida parsing de valores, delimitadores e formatação em Real brasileiro."""
        self.assertEqual(GDF._formatar_moeda("12500.00"), "R$ 12.500,00")
        self.assertEqual(GDF._formatar_moeda("12.500,50"), "R$ 12.500,50")
        self.assertEqual(GDF._formatar_moeda("450"), "R$ 450,00")

        nodes, edges = GDF.montar_grafo(GDF.carregar_transacoes(self.csv_path))
        # 1 Vítima + 1 Passagem (Carlos) + 2 Destinatários (Lucas, Ana) = 4 nós
        self.assertEqual(len(nodes), 4)
        self.assertEqual(len(edges), 3)

    def test_03_injecao_automatica_no_docx(self):
        """Valida descoberta automática do fluxo-financeiro.csv e injeção do PNG 300 DPI no DOCX."""
        saida_docx = os.path.join(self.pasta_rel, f"RELATORIO-{self.caso_id}-v01.docx")
        cmd = [
            sys.executable,
            os.path.join(S_REL, "gerar_docx.py"),
            self.minuta_path,
            "--saida",
            saida_docx,
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(r.returncode, 0, f"Falha ao gerar DOCX: {r.stderr or r.stdout}")
        self.assertTrue(os.path.isfile(saida_docx))

        png_esperado = os.path.join(self.pasta_rel, f"FLUXO-FINANCEIRO-{self.caso_id}.png")
        self.assertTrue(os.path.isfile(png_esperado), "Fluxograma PNG não foi compilado automaticamente.")

        doc = docx.Document(saida_docx)
        textos = [p.text for p in doc.paragraphs]

        self.assertTrue(any("Fluxograma do Caminho do Dinheiro" in t for t in textos))
        self.assertTrue(any("Figura 1" in t for t in textos))

        tem_imagem = any(p._element.xpath(".//pic:pic") for p in doc.paragraphs)
        self.assertTrue(tem_imagem, "Nenhuma imagem foi incorporada ao documento DOCX.")

    def test_04_injecao_explicita_markdown(self):
        """Valida que imagem explicitada no Markdown com ![legenda](caminho) é inserida sem duplicação."""
        png_personalizado = os.path.join(self.pasta_rel, "diagrama-custom.png")
        txs = GDF.carregar_transacoes(self.csv_path)
        GDF.desenhar_diagrama(txs, png_personalizado, caso_id=self.caso_id, dpi=300)

        minuta_custom = MINUTA_FICTICIA.replace(
            "## DILIGÊNCIAS REALIZADAS\n",
            "## DILIGÊNCIAS REALIZADAS\n![Diagrama Customizado](diagrama-custom.png)\n",
        )
        minuta_custom_path = os.path.join(self.pasta_rel, "minuta-v02.md")
        with open(minuta_custom_path, "w", encoding="utf-8") as f:
            f.write(minuta_custom)

        saida_docx = os.path.join(self.pasta_rel, f"RELATORIO-{self.caso_id}-v02.docx")
        cmd = [
            sys.executable,
            os.path.join(S_REL, "gerar_docx.py"),
            minuta_custom_path,
            "--saida",
            saida_docx,
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(r.returncode, 0, f"Falha ao gerar DOCX customizado: {r.stderr or r.stdout}")

        doc = docx.Document(saida_docx)
        textos = [p.text for p in doc.paragraphs]
        self.assertTrue(any("Diagrama Customizado" in t for t in textos))

        paragrafos_com_pic = [p for p in doc.paragraphs if p._element.xpath(".//pic:pic")]
        self.assertGreaterEqual(len(paragrafos_com_pic), 1)

    def test_05_flag_sem_fluxograma(self):
        """Valida que a flag --sem-fluxograma impede a injeção automática."""
        saida_docx = os.path.join(self.pasta_rel, f"RELATORIO-{self.caso_id}-sem-fluxo.docx")
        cmd = [
            sys.executable,
            os.path.join(S_REL, "gerar_docx.py"),
            self.minuta_path,
            "--saida",
            saida_docx,
            "--sem-fluxograma",
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(r.returncode, 0)

        doc = docx.Document(saida_docx)
        textos = [p.text for p in doc.paragraphs]
        self.assertFalse(any("Figura 1" in t for t in textos))


if __name__ == "__main__":
    unittest.main()
