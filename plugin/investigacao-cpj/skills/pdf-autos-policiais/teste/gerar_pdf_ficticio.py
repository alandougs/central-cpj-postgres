# Gera PDF 100% fictício para validar a skill: 230 págs. (1-80 com texto, 81-230 só imagem)
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfWriter, PdfReader
import io
buf=io.BytesIO(); c=canvas.Canvas(buf,pagesize=A4)
for i in range(1,81):
    c.setFont("Helvetica",12)
    c.drawString(72,800,f"INQUERITO POLICIAL FICTICIO - fls. {i+1}")
    c.drawString(72,770,f"Termo de declaracoes de TESTEMUNHA FICTICIA {i}. CPF 000.000.000-{i%100:02d}")
    c.drawString(72,750,"Placa ABC1D23. Telefone (18) 99999-0000. Data 12/03/2026.")
    c.showPage()
c.save()
imgs=[]
try: font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",28)
except: font=ImageFont.load_default()
for i in range(81,231):
    im=Image.new("RGB",(1240,1754),"white"); d=ImageDraw.Draw(im)
    d.text((120,120),f"BOLETIM DE OCORRENCIA FICTICIO - fls. {i+1}",fill="black",font=font)
    d.text((120,200),f"Valor transferido: R$ 1.{i:03d},00 via Pix em 0{i%9+1}/04/2026",fill="black",font=font)
    imgs.append(im)
ib=io.BytesIO(); imgs[0].save(ib,"PDF",save_all=True,append_images=imgs[1:],resolution=150)
w=PdfWriter()
for r in (PdfReader(io.BytesIO(buf.getvalue())),PdfReader(io.BytesIO(ib.getvalue()))):
    for p in r.pages: w.add_page(p)
w.write("ip_teste.pdf")
print("ok")
