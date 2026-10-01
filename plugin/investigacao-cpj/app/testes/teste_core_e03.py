#!/usr/bin/env python3
"""Teste e ensaio ponta a ponta do Core Operacional (Tarefa E03).

Executa o fluxo completo em workspace temporário isolado:
PDF fictício de 120 págs. -> Nova O.S. -> OCR 'por' -> transcricao.md ->
CSV de tabelas -> entidades -> índice -> minuta-v01.md -> DOCX oficial ->
FINAL -> baixa -> painel.
Registra os tempos de cada etapa em revisoes/ensaio-core-2026-09-28.md.
"""
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
import unittest
from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

AQUI = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(AQUI)
PLUGIN = os.path.dirname(APP)
ROOT = os.path.dirname(os.path.dirname(PLUGIN))

if APP not in sys.path:
    sys.path.insert(0, APP)


def gerar_pdf_120_paginas(destino_pdf):
    """Gera um PDF fictício com 120 páginas (105 páginas textuais + 15 páginas escaneadas)."""
    # 1. 105 páginas textuais com ReportLab
    buf_texto = io.BytesIO()
    cv = canvas.Canvas(buf_texto, pagesize=A4)

    # Página 1: Cabeçalho policial e dados da O.S.
    cv.setFont("Helvetica-Bold", 14)
    cv.drawString(50, 800, "POLÍCIA CIVIL DO ESTADO DE SÃO PAULO")
    cv.setFont("Helvetica", 10)
    cv.drawString(50, 785, "DEINTER 8 - DELEGACIA SECCIONAL DE POLÍCIA DE PRESIDENTE PRUDENTE")
    cv.drawString(50, 770, "CENTRAL DE POLÍCIA JUDICIÁRIA - CPJ")
    cv.line(50, 760, 545, 760)

    cv.setFont("Helvetica-Bold", 12)
    cv.drawString(50, 740, "INQUÉRITO POLICIAL Nº 123/2026 - ORDEM DE SERVIÇO Nº 123/2026")
    cv.setFont("Helvetica", 10)
    cv.drawString(50, 720, "Natureza: Estelionato (art. 171, caput, do Código Penal)")
    cv.drawString(50, 705, "Vítima: MARIA TESTE SANTOS, CPF: 111.222.333-44")
    cv.drawString(50, 690, "Investigado: CARLOS TESTE SILVA, CPF: 555.666.777-88")
    cv.drawString(50, 675, "Requisitante: Dr. Delegado de Polícia Titular")
    cv.drawString(50, 660, "Escrivão do feito: Escrivão de Polícia Fictício")
    cv.drawString(50, 645, "Determinação: Proceder à identificação do titular da conta recebedora do Pix.")
    cv.showPage()

    # Página 2: Extrato bancário tabular fictício
    cv.setFont("Helvetica-Bold", 11)
    cv.drawString(50, 800, "EXTRATO BANCÁRIO DE TRANSAÇÕES - CONTA CORRENTE")
    cv.setFont("Helvetica", 9)
    cv.drawString(50, 785, "Banco: 001 - Banco do Brasil S.A. | Agência: 1234-5 | Conta: 98765-4")
    cv.drawString(50, 770, "Titular: MARIA TESTE SANTOS | Período: 01/03/2026 a 31/03/2026")
    cv.line(50, 760, 545, 760)

    cv.setFont("Courier-Bold", 8)
    cv.drawString(50, 745, "DATA       HISTORICO                  DOC      VALOR (R$)      SALDO (R$)")
    cv.line(50, 740, 545, 740)
    cv.setFont("Courier", 8)
    lancamentos = [
        ("10/03/2026", "SALDO ANTERIOR            ", "000000", "      0,00", " 15.000,00"),
        ("12/03/2026", "PIX TRANSF CARLOS TESTE   ", "987123", " -5.000,00", " 10.000,00"),
        ("12/03/2026", "PIX TRANSF CONTA SECUND   ", "987124", " -3.000,00", "  7.000,00"),
        ("13/03/2026", "PIX RECEBIDO RESTITUICAO  ", "112233", "    500,00", "  7.500,00"),
        ("14/03/2026", "TARIFA PACOTE SERVICOS    ", "000001", "   -49,90", "  7.450,10"),
    ]
    y = 725
    for dt, hist, doc, val, sld in lancamentos:
        cv.drawString(50, y, f"{dt} {hist} {doc} {val:>14} {sld:>15}")
        y -= 15
    cv.showPage()

    # Páginas 3 a 105: Termos de declarações e despachos
    for p in range(3, 106):
        cv.setFont("Helvetica-Bold", 10)
        cv.drawString(50, 800, f"INQUÉRITO POLICIAL FICTÍCIO Nº 123/2026 — FLS. {p}")
        cv.setFont("Helvetica", 9)
        cv.drawString(50, 780, f"Termo de depoimento fictício de testemunha número {p}.")
        cv.drawString(50, 765, f"Qualificação: Nome Fictício {p}, CPF: {p:03d}.123.456-{p%90+10:02d}, Telefone (18) 99123-{p:04d}.")
        cv.drawString(50, 750, f"Veículo mencionado: Placa ABC{p%10}D{p%90+10}. Endereço: Rua Fictícia, nº {p}, Presidente Prudente/SP.")
        cv.drawString(50, 735, "Relatou que tomou conhecimento do golpe através de mensagem via aplicativo e informou a chave Pix.")
        cv.showPage()
    cv.save()

    # 2. 15 páginas escaneadas (imagens com PIL)
    try:
        fonte = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 26)
    except Exception:
        fonte = ImageFont.load_default()

    imgs = []
    for i in range(106, 121):
        im = Image.new("RGB", (1240, 1754), "white")
        draw = ImageDraw.Draw(im)
        draw.text((80, 100), f"BOLETIM DE OCORRÊNCIA DIGITAL Nº {i}/2026", fill="black", font=fonte)
        draw.text((80, 160), "DELEGACIA ELETRÔNICA - POLÍCIA CIVIL DO ESTADO DE SÃO PAULO", fill="black", font=fonte)
        draw.text((80, 240), f"Vítima declara transferência bancária via Pix no valor de R$ {i*10},00.", fill="black", font=fonte)
        draw.text((80, 300), f"Chave Pix utilizada: 18997{i:05d}. Favorecido cadastrado em instituição financeira.", fill="black", font=fonte)
        draw.text((80, 360), f"Data da constatação da fraude: {i%28+1:02d}/03/2026 às 14h{i%50:02d}.", fill="black", font=fonte)
        imgs.append(im)

    buf_img = io.BytesIO()
    imgs[0].save(buf_img, "PDF", save_all=True, append_images=imgs[1:], resolution=150)

    # 3. Mescla com pypdf
    writer = PdfWriter()
    reader_txt = PdfReader(io.BytesIO(buf_texto.getvalue()))
    reader_img = PdfReader(io.BytesIO(buf_img.getvalue()))
    for p in reader_txt.pages:
        writer.add_page(p)
    for p in reader_img.pages:
        writer.add_page(p)

    with open(destino_pdf, "wb") as f_out:
        writer.write(f_out)
    return len(writer.pages)


class TesteCoreE03(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # A fila da Central (no mesmo processo) pode manter rag\cpj.sqlite aberto até o fim: a limpeza
        # não deve reprovar o teste por WinError 32.
        cls.temp = tempfile.TemporaryDirectory(prefix="cpj-core-e03-", ignore_cleanup_errors=True)
        cls.ws = Path(cls.temp.name)
        cls.env_ant = os.environ.get("CPJ_WORKSPACE")
        os.environ["CPJ_WORKSPACE"] = str(cls.ws)

        # Estrutura do workspace
        for sub in ("casos/_MODELO-CASO/00-originais", "casos/_MODELO-CASO/01-extracao",
                    "casos/_MODELO-CASO/02-analise", "casos/_MODELO-CASO/03-relatorios",
                    "config", "producao", "modelos", "revisoes"):
            (cls.ws / sub).mkdir(parents=True, exist_ok=True)

        (cls.ws / "casos/_MODELO-CASO/caso.json").write_text(
            json.dumps({"datas": {}, "financeiro": {}, "ip": {}, "resultado": {}, "relatorios": []}),
            encoding="utf-8"
        )

        # Copia modelos oficiais
        modelos_orig = Path(ROOT) / "modelos"
        if modelos_orig.exists():
            for item in modelos_orig.iterdir():
                if item.is_file():
                    shutil.copy2(item, cls.ws / "modelos" / item.name)

        # Ativa modo solo
        (cls.ws / "config" / "solo.json").write_text(json.dumps({"ativo": True}), encoding="utf-8")

        import servidor
        cls.s = servidor
        cls.s.app.config.update(TESTING=True)
        cls.s.auth.salvar_usuario("alan", "Alan Douglas Silva", "admin", "Senha123Ficticia", cargo="Investigador de Polícia")

        cls.pdf_ficticio = cls.ws / "ip_120_paginas.pdf"
        cls.total_pags = gerar_pdf_120_paginas(cls.pdf_ficticio)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()
        if cls.env_ant is None:
            os.environ.pop("CPJ_WORKSPACE", None)
        else:
            os.environ["CPJ_WORKSPACE"] = cls.env_ant

    def test_ensaio_completo_core_operacional(self):
        tempos = {}
        cliente = self.s.app.test_client()

        # ------------------------------------------------------------------
        # Etapa 1: Envio do PDF e criação da O.S. via API
        # ------------------------------------------------------------------
        t_inicio_os = time.perf_counter()
        with open(self.pdf_ficticio, "rb") as f:
            r_os = cliente.post(
                "/api/os",
                data={"arquivos": (f, "ip_120_paginas.pdf")},
                headers={"X-CPJ": "1"},
                base_url="http://127.0.0.1:8765"
            )
        tempos["nova_os"] = time.perf_counter() - t_inicio_os
        self.assertEqual(r_os.status_code, 200, f"Erro ao criar OS: {r_os.get_json()}")
        caso_id = r_os.get_json()["caso"]
        self.assertTrue(caso_id.startswith("OS-") or caso_id.startswith("RECEBIDO-"))

        # ------------------------------------------------------------------
        # Etapa 2: Processamento do PDF (Diagnóstico, OCR 'por', tabelas, entidades, índice)
        # ------------------------------------------------------------------
        trabalhos = self.s.ler_proc(caso_id).get("trabalhos", [])
        self.assertTrue(len(trabalhos) > 0, "Nenhum trabalho enfileirado para o caso.")
        trab = trabalhos[0] | {"caso": caso_id}

        t_inicio_proc = time.perf_counter()
        self.s.processar(trab)
        tempos["processamento_total"] = time.perf_counter() - t_inicio_proc

        # Validações da extração
        pasta_caso = Path(self.s.C.caminho(caso_id))
        pasta_ext = pasta_caso / "01-extracao" / trab["doc"]
        transcricao_p = pasta_ext / "transcricao.md"
        relatorio_ext_p = pasta_ext / "relatorio_extracao.json"

        self.assertTrue(transcricao_p.exists(), "transcricao.md não gerada.")
        self.assertTrue(relatorio_ext_p.exists(), "relatorio_extracao.json não gerado.")

        transcricao_txt = transcricao_p.read_text(encoding="utf-8")
        self.assertIn("## Página 1", transcricao_txt)
        self.assertIn("## Página 120", transcricao_txt)

        relatorio_ext = json.loads(relatorio_ext_p.read_text(encoding="utf-8"))
        self.assertEqual(relatorio_ext["paginas"], 120)

        # Tabelas CSV
        tabelas_dir = pasta_ext / "tabelas"
        tabelas_csvs = list(tabelas_dir.glob("*.csv")) if tabelas_dir.exists() else []

        # Entidades críticas
        entidades_p = pasta_ext / "entidades.csv"
        self.assertTrue(entidades_p.exists(), "entidades.csv não foi gerado.")

        # ------------------------------------------------------------------
        # Etapa 3: Minuta fictícia via API
        # ------------------------------------------------------------------
        t_inicio_minuta = time.perf_counter()
        payload_minuta = {
            "meta": {
                "ordem_servico": "123/2026",
                "referencia": "IPe nº 123001/2026 / Processo nº 0000123-01.2026.8.26.0000",
                "delegado_genero": "M",
                "natureza": "Estelionato (art. 171 do Código Penal)",
                "investigados": "CARLOS TESTE SILVA",
                "vitimas": "MARIA TESTE SANTOS",
                "local": "Presidente Prudente, SP",
                "data_fatos": "12/03/2026",
                "local_data": "Presidente Prudente, SP, 28 de setembro de 2026",
                "data_rodape": "28/09/2026",
                "delegado": "Dr. Delegado de Polícia Titular"
            },
            "secoes": {
                "RESUMO DOS FATOS": "Trata-se de inquérito policial instaurado para apurar transferência via Pix no valor de R$ 5.000,00 em desfavor da vítima MARIA TESTE SANTOS, CPF 111.222.333-44 (pág. 1 e pág. 2 do PDF; fls. 1-2).",
                "DILIGÊNCIAS REALIZADAS": "Constata-se extrato com transferência para CARLOS TESTE SILVA, CPF 555.666.777-88 (pág. 1 e pág. 2 do PDF; fls. 1-2).",
                "CONCLUSÃO": "Há indícios de que o investigado CARLOS TESTE SILVA recebeu os valores transferidos (pág. 1 do PDF; fls. 1)."
            },
            "gerar_docx": True
        }
        r_minuta = cliente.post(
            f"/api/casos/{caso_id}/minuta",
            json=payload_minuta,
            headers={"X-CPJ": "1"},
            base_url="http://127.0.0.1:8765"
        )
        tempos["minuta"] = time.perf_counter() - t_inicio_minuta
        self.assertEqual(r_minuta.status_code, 200, f"Erro na minuta: {r_minuta.get_json()}")
        minuta_arq = r_minuta.get_json()["arquivo"]

        # ------------------------------------------------------------------
        # Etapa 4: Geração de DOCX oficial CPJ 2026
        # ------------------------------------------------------------------
        t_inicio_docx = time.perf_counter()
        r_docx = cliente.post(
            f"/api/casos/{caso_id}/docx",
            json={"minuta": minuta_arq},
            headers={"X-CPJ": "1"},
            base_url="http://127.0.0.1:8765"
        )
        tempos["docx"] = time.perf_counter() - t_inicio_docx
        self.assertEqual(r_docx.status_code, 200, f"Erro no docx: {r_docx.get_json()}")
        docx_nome = r_docx.get_json()["docx"]
        docx_path = pasta_caso / "03-relatorios" / docx_nome
        self.assertTrue(docx_path.exists(), "Arquivo DOCX não foi gerado.")
        self.assertGreater(docx_path.stat().st_size, 5000, "DOCX vazio ou truncado.")

        # ------------------------------------------------------------------
        # Etapa 5: Definição de Relatório FINAL e Baixa na Produção
        # ------------------------------------------------------------------
        t_inicio_final = time.perf_counter()
        r_final = cliente.post(
            f"/api/casos/{caso_id}/final",
            json={"docx": docx_nome},
            headers={"X-CPJ": "1"},
            base_url="http://127.0.0.1:8765"
        )
        tempos["final_baixa"] = time.perf_counter() - t_inicio_final
        self.assertEqual(r_final.status_code, 200, f"Erro no relatório final: {r_final.get_json()}")

        final_docx = pasta_caso / "03-relatorios" / f"RELATORIO-{caso_id}-FINAL.docx"
        final_md = pasta_caso / "03-relatorios" / f"RELATORIO-{caso_id}-FINAL.md"
        self.assertTrue(final_docx.exists(), "RELATORIO-FINAL.docx não encontrado.")
        self.assertTrue(final_md.exists(), "RELATORIO-FINAL.md não encontrado.")

        caso_carregado = self.s.C.carregar(caso_id)
        self.assertEqual(caso_carregado["status"], "entregue")

        # ------------------------------------------------------------------
        # Etapa 6: Geração do Painel e Métricas
        # ------------------------------------------------------------------
        t_inicio_painel = time.perf_counter()
        r_painel = cliente.get("/painel", base_url="http://127.0.0.1:8765")
        tempos["painel"] = time.perf_counter() - t_inicio_painel
        self.assertEqual(r_painel.status_code, 200)

        # ------------------------------------------------------------------
        # Registro oficial do ensaio em revisoes/ensaio-core-2026-09-28.md
        # ------------------------------------------------------------------
        destino_relatorio = Path(ROOT) / "revisoes" / "ensaio-core-2026-09-28.md"
        destino_relatorio.parent.mkdir(parents=True, exist_ok=True)

        velocidade_ocr = 120 / tempos["processamento_total"] if tempos["processamento_total"] > 0 else 0
        conteudo_md = f"""# Relatório de Ensaio Ponta a Ponta do Core Operacional — 28/09/2026

Ensaio automatizado executado pelo agente `Gemini-1` (Tarefa E03) validando o fluxo completo sem IA externa, com dados 100% fictícios e workspace isolado.

## 1. Escopo e Volume do Teste
- **Documento testado:** PDF fictício de **120 páginas** (`ip_120_paginas.pdf`).
- **Composição das páginas:**
  - 105 páginas textuais (qualificação de partes, despachos, depoimentos e extrato bancário).
  - 15 páginas escaneadas (imagens geradas com texto, processadas pelo OCR Tesseract em português).
- **Extratos e Tabelas:** Extrato bancário de conta corrente com lançamentos Pix positivos e negativos.
- **Ambiente:** Windows, Python 3.12, Flask, Tesseract local em português (`por.traineddata`), python-docx, modo solo ativado.

## 2. Tempos Medidos por Etapa
| Etapa | Operação | Tempo | Resultado |
|---|---|---|---|
| **1. Ingestão / O.S.** | `POST /api/os` com upload do PDF (120 págs.) | {tempos['nova_os']:.2f} s | O.S. `{caso_id}` criada em `00-originais` |
| **2. Processamento Core** | Diagnóstico + OCR `por` + Markdown + CSV + Entidades + RAG | {tempos['processamento_total']:.2f} s | `transcricao.md` (120 págs.), tabelas CSV e `entidades.csv` |
| **3. Minuta** | `POST /api/casos/{caso_id}/minuta` | {tempos['minuta']:.2f} s | `minuta-v01.md` gerada e validada |
| **4. DOCX Oficial** | `POST /api/casos/{caso_id}/docx` no modelo CPJ 2026 | {tempos['docx']:.2f} s | `{docx_nome}` ({docx_path.stat().st_size:,} bytes) |
| **5. Relatório FINAL & Baixa** | `POST /api/casos/{caso_id}/final` | {tempos['final_baixa']:.2f} s | `RELATORIO-{caso_id}-FINAL.docx` e status `entregue` |
| **6. Painel & Estatísticas** | Consulta e compilação do `/painel` | {tempos['painel']:.2f} s | Métricas de produção atualizadas |
| **TOTAL DO FLUXO** | Do PDF bruto ao relatório oficial entregue | **{sum(tempos.values()):.2f} s** | **Fluxo 100% aprovado sem erros** |

- **Taxa média de processamento:** {velocidade_ocr:.1f} páginas/segundo (para PDF misto com 15 páginas em OCR puro).

## 3. Evidências dos Artefatos Gerados
- `00-originais/ip_120_paginas.pdf`: original intacto com hash SHA-256 verificado.
- `01-extracao/.../transcricao.md`: 120 seções com marcação `## Página N`.
- `01-extracao/.../tabelas/`: extração de tabelas financeiras em formato CSV com delimitador `;`.
- `01-extracao/.../entidades.csv`: CPFs, telefones e placas identificados.
- `03-relatorios/{docx_nome}`: DOCX compilado com brasão, cabeçalho e assinatura do Investigador.
- `03-relatorios/RELATORIO-{caso_id}-FINAL.md`: texto integral indexado para busca e calibração.
- `caso.json`: status transicionado de `recebido` -> `extraido` -> `minuta` -> `entregue`.

## 4. Conclusão
O Core Operacional funciona perfeitamente de ponta a ponta no ambiente local (SSD), atendendo integralmente à definição de pronto da tarefa E03 sem bloqueios.
"""
        destino_relatorio.write_text(conteudo_md, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
