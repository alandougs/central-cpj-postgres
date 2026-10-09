import os
import json
import tempfile
import shutil
import subprocess
import sys
from reportlab.pdfgen import canvas
from PIL import Image, ImageDraw

def ok(condicao, msg):
    if not condicao:
        print(f"FALHOU: {msg}")
        sys.exit(1)
    print(f"OK: {msg}")

def main():
    T = tempfile.mkdtemp(prefix="cpj-px03-")
    try:
        pdf_path = os.path.join(T, "teste.pdf")
        pasta_ext = os.path.join(T, "extracao")
        chk_dir = os.path.join(pasta_ext, ".checkpoint")
        os.makedirs(chk_dir, exist_ok=True)
        
        # Cria imagem temporária para a pag 2
        img_path = os.path.join(T, "imagem.png")
        img = Image.new("RGB", (600, 800), color="white")
        d = ImageDraw.Draw(img)
        d.text((10,10), "TESTE", fill="black")
        img.save(img_path)
        
        # Gera o PDF com 4 páginas
        c = canvas.Canvas(pdf_path)
        
        # Pag 1: digital limpa
        c.drawString(100, 700, "Esta é uma página digital limpa e bem formada.")
        c.drawString(100, 680, "Com várias linhas de texto úteis.")
        c.drawString(100, 660, "Sem nenhum problema aparente.")
        c.showPage()
        
        # Pag 2: só imagem
        c.drawImage(img_path, 0, 0, width=600, height=800)
        c.showPage()
        
        # Pag 3: texto com muitos ? / fragmentado
        c.drawString(100, 700, "? ? a ? b ? ? c")
        c.drawString(100, 680, "x ? y ? z")
        c.showPage()
        
        # Pag 4: digital com tabela bem lida
        # Desenhando uma tabela simples
        for i in range(5):
            c.drawString(100, 700 - i*20, f"Linha {i} Col 1")
            c.drawString(200, 700 - i*20, f"Linha {i} Col 2")
            c.drawString(300, 700 - i*20, f"Linha {i} Col 3")
        c.showPage()
        
        c.save()
        
        # Moca os checkpoints
        # Pag 1: digital limpa
        with open(os.path.join(chk_dir, "p0001.json"), "w", encoding="utf-8") as f:
            texto = "Esta é uma página digital limpa e bem formada.\nCom várias linhas de texto úteis.\nSem nenhum problema aparente.\n" * 2
            json.dump({"reg": {"pagina": 1, "metodo": "texto-nativo", "texto": texto}}, f)
            
        # Pag 2: só imagem
        with open(os.path.join(chk_dir, "p0002.json"), "w", encoding="utf-8") as f:
            json.dump({"reg": {"pagina": 2, "metodo": "texto-nativo", "texto": ""}}, f)
            
        # Pag 3: fragmentado
        with open(os.path.join(chk_dir, "p0003.json"), "w", encoding="utf-8") as f:
            texto = "? ? a ? b ? ? c\n" * 10
            json.dump({"reg": {"pagina": 3, "metodo": "ocr-tesseract", "confianca_media": 50.0, "texto": texto}}, f)
            
        # Pag 4: tabela bem lida
        with open(os.path.join(chk_dir, "p0004.json"), "w", encoding="utf-8") as f:
            texto = "Tabela com dados perfeitamente bem lidos e extensos.\nSegunda coluna tem dados extensos tambem\n" * 5
            json.dump({"reg": {"pagina": 4, "metodo": "texto-nativo", "texto": texto}}, f)
            
        # Moca o relatorio_extracao.json
        with open(os.path.join(pasta_ext, "relatorio_extracao.json"), "w", encoding="utf-8") as f:
            json.dump({"pendentes_transcricao_visual": [], "conferir_visualmente": []}, f)
            
        # Roda o qualidade.py
        script_qualidade = os.path.join("plugin", "investigacao-cpj", "skills", "pdf-autos-policiais", "scripts", "qualidade.py")
        cmd = [sys.executable, script_qualidade, pasta_ext, "--pdf", pdf_path]
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        if r.returncode != 0:
            print(r.stderr)
            sys.exit(1)
            
        # Verifica a saída
        out_json = os.path.join(pasta_ext, "qualidade.json")
        ok(os.path.exists(out_json), "qualidade.json gerado")
        
        with open(out_json, "r", encoding="utf-8") as f:
            res = json.load(f)
            
        p1 = res.get("1", {})
        ok(p1.get("categoria") == "digital" and not p1.get("precisa_ia"), "página digital limpa -> não precisa de IA")
        
        p2 = res.get("2", {})
        ok(p2.get("precisa_ia"), "página só imagem -> precisa de IA")
        
        p3 = res.get("3", {})
        ok(p3.get("precisa_ia") and "Muitos caracteres inválidos" in p3.get("motivos", []) or "Confiança do OCR baixa (50.0)" in p3.get("motivos", []), "texto com muitos ?/fragmentado -> precisa de IA")
        
        p4 = res.get("4", {})
        ok(p4.get("categoria") in ("digital", "hibrida") and not p4.get("precisa_ia"), "página digital com tabela bem lida -> não precisa de IA")
        
    finally:
        shutil.rmtree(T, ignore_errors=True)

if __name__ == "__main__":
    main()
