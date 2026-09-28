"""Gerador de PDF sintético para testes E2E da Central CPJ."""
import io
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def gerar_pdf_sintetico_e2e(destino_pdf, paginas_texto=3, paginas_imagem=1):
    """Gera um PDF fictício com páginas textuais (incluindo extrato tabular) e páginas escaneadas (OCR).

    Garante validação completa:
    1. Texto nativo + detecção automática de O.S., vítima, investigado, delegado e escrivão.
    2. Extrato bancário formatado para detecção e extração de tabelas CSV.
    3. Imagem escaneada sintética para acionar o motor de OCR Tesseract.
    """
    buf_texto = io.BytesIO()
    cv = canvas.Canvas(buf_texto, pagesize=A4)

    # Página 1: Cabeçalho policial, O.S. e qualificação das partes
    cv.setFont("Helvetica-Bold", 14)
    cv.drawString(50, 800, "POLÍCIA CIVIL DO ESTADO DE SÃO PAULO")
    cv.setFont("Helvetica", 10)
    cv.drawString(50, 785, "DEINTER 8 - DELEGACIA SECCIONAL DE POLÍCIA DE PRESIDENTE PRUDENTE")
    cv.drawString(50, 770, "CENTRAL DE POLÍCIA JUDICIÁRIA - CPJ")
    cv.line(50, 760, 545, 760)

    cv.setFont("Helvetica-Bold", 12)
    cv.drawString(50, 740, "INQUÉRITO POLICIAL Nº 456/2026 - ORDEM DE SERVIÇO Nº 456/2026")
    cv.setFont("Helvetica", 10)
    cv.drawString(50, 720, "Natureza: Estelionato (art. 171, caput, do Código Penal)")
    cv.drawString(50, 705, "Vítima: MARIA TESTE SILVA, CPF: 111.222.333-44")
    cv.drawString(50, 690, "Investigado: CARLOS TESTE SANTOS, CPF: 555.666.777-88")
    cv.drawString(50, 675, "Requisitante: Dr. Delegado de Polícia Titular")
    cv.drawString(50, 660, "Escrivão do feito: Escrivão de Polícia Fictício")
    cv.drawString(50, 645, "Determinação: Proceder à identificação do titular da conta recebedora do Pix.")
    cv.showPage()

    # Página 2: Extrato bancário tabular para teste de tabelas.py -> CSV
    cv.setFont("Helvetica-Bold", 11)
    cv.drawString(50, 800, "EXTRATO BANCÁRIO DE TRANSAÇÕES - CONTA CORRENTE")
    cv.setFont("Helvetica", 9)
    cv.drawString(50, 785, "Banco: 001 - Banco do Brasil S.A. | Agência: 1234-5 | Conta: 98765-4")
    cv.drawString(50, 770, "Titular: MARIA TESTE SILVA | Período: 01/03/2026 a 31/03/2026")
    cv.line(50, 760, 545, 760)

    cv.setFont("Courier-Bold", 8)
    cv.drawString(50, 745, "DATA       HISTORICO                  DOC      VALOR (R$)      SALDO (R$)")
    cv.line(50, 740, 545, 740)
    cv.setFont("Courier", 8)
    lancamentos = [
        ("10/03/2026", "SALDO ANTERIOR            ", "000000", "      0,00", " 15.000,00"),
        ("12/03/2026", "PIX TRANSF CARLOS TESTE   ", "987123", " -5.000,00", " 10.000,00"),
        ("12/03/2026", "PIX TRANSF SEGUNDA CAMADA ", "987124", " -2.500,00", "  7.500,00"),
        ("13/03/2026", "PIX RECEBIDO RESTITUICAO  ", "112233", "    300,00", "  7.800,00"),
        ("14/03/2026", "TARIFA BANCARIA PACOTE    ", "000001", "   -49,90", "  7.750,10"),
    ]
    y = 725
    for dt, hist, doc, val, sld in lancamentos:
        cv.drawString(50, y, f"{dt} {hist} {doc} {val:>14} {sld:>15}")
        y -= 15
    cv.showPage()

    # Páginas textuais adicionais (se paginas_texto > 2)
    for p in range(3, paginas_texto + 1):
        cv.setFont("Helvetica-Bold", 10)
        cv.drawString(50, 800, f"TERMO DE DECLARAÇÕES FICTÍCIO — FLS. {p}")
        cv.setFont("Helvetica", 9)
        cv.drawString(50, 780, f"Depoimento da testemunha {p}, qualificada nos autos.")
        cv.drawString(50, 765, f"Telefone de contato: (18) 99123-456{p}. Placa do veículo citado: ABC{p}D23.")
        cv.drawString(50, 750, "Declarou ter efetuado transferência via Pix conforme comprovante anexado.")
        cv.showPage()
    cv.save()

    # Páginas escaneadas (imagens geradas com PIL para disparar OCR)
    imgs = []
    try:
        fonte = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 26)
    except Exception:
        fonte = ImageFont.load_default()

    for idx in range(1, paginas_imagem + 1):
        im = Image.new("RGB", (1240, 1754), "white")
        draw = ImageDraw.Draw(im)
        draw.text((80, 100), f"BOLETIM DE OCORRÊNCIA DIGITAL Nº {idx+1000}/2026", fill="black", font=fonte)
        draw.text((80, 160), "DELEGACIA ELETRÔNICA - POLÍCIA CIVIL DO ESTADO DE SÃO PAULO", fill="black", font=fonte)
        draw.text((80, 240), f"Vítima relata transferência Pix de R$ 5.000,00 para investigado fictício.", fill="black", font=fonte)
        draw.text((80, 300), f"Chave Pix utilizada: 18991234567. Instituição Financeira: Banco Teste S.A.", fill="black", font=fonte)
        draw.text((80, 360), "Documento digitalizado para instrução do inquérito policial.", fill="black", font=fonte)
        imgs.append(im)

    buf_img = io.BytesIO()
    if imgs:
        imgs[0].save(buf_img, "PDF", save_all=True, append_images=imgs[1:], resolution=150)

    # Mescla tudo em destino_pdf
    writer = PdfWriter()
    reader_txt = PdfReader(io.BytesIO(buf_texto.getvalue()))
    for p in reader_txt.pages:
        writer.add_page(p)

    if imgs:
        reader_img = PdfReader(io.BytesIO(buf_img.getvalue()))
        for p in reader_img.pages:
            writer.add_page(p)

    dest = Path(destino_pdf)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as f_out:
        writer.write(f_out)

    return len(writer.pages)
