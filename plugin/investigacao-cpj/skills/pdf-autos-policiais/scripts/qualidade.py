#!/usr/bin/env python3
"""Avaliação de qualidade local por página (PX03).
Grava qualidade.json na pasta de extração.
"""
import argparse
import json
import os
import re

# Limiares nomeados
MIN_CARACTERES_UTEIS = 50
MIN_CONFIANCA_OCR = 75.0
MAX_FRACAO_INVALIDOS = 0.05
MAX_FRAGMENTACAO_LINHA = 30  # se a média for MENOR que 20, ou se proporção de tokens curtos for grande, consideramos fragmentado (a instrução sugere medir média e proporção, vamos usar limites razoáveis)
MAX_FRACAO_TOKENS_1 = 0.20
MIN_FRACAO_IMAGEM = 0.3
MAX_CELULAS_VAZIAS_TABELA = 0.5

CARIMBO = re.compile(r"assinad[oa] digitalmente|certificad[oa] pel[oa]|conferir o original|esaj\.tjsp|pastadigital|abrirConferencia|"
                     r"protocolad[oa] em|liberad[oa] nos autos|c[óo]digo [0-9A-Z]{4,}|^\s*(p[áa]g\.?|fls\.?)\s*\d+\s*$", re.I)

def texto_util(txt):
    return "\n".join(l for l in txt.splitlines() if l.strip() and not CARIMBO.search(l)).strip()

def calcula_metricas(texto, metodo, confianca, tem_imagem, tem_tabela_inconsistente, estava_pendente, estava_conferir):
    motivos = []
    pontuacao = 100
    
    txt_util = texto_util(texto)
    tam_util = len(txt_util)
    
    if tam_util < MIN_CARACTERES_UTEIS:
        motivos.append("Poucos caracteres úteis")
        pontuacao -= 30
        
    if metodo == "ocr-tesseract":
        if confianca < MIN_CONFIANCA_OCR:
            motivos.append(f"Confiança do OCR baixa ({confianca})")
            pontuacao -= 40
            
    # Proporção de caracteres inválidos ( e controle)
    invalidos = sum(1 for c in txt_util if c == '' or (ord(c) < 32 and c not in '\n\r\t'))
    fracao_inv = invalidos / max(1, tam_util)
    if fracao_inv > MAX_FRACAO_INVALIDOS:
        motivos.append("Muitos caracteres inválidos")
        pontuacao -= max(20, int(fracao_inv * 100))
        
    # Fragmentação
    linhas = [l for l in txt_util.splitlines() if l.strip()]
    media_chars_linha = tam_util / max(1, len(linhas))
    
    tokens = txt_util.split()
    tokens_1_char = sum(1 for t in tokens if len(t) == 1 and t.isalnum())
    fracao_tokens_1 = tokens_1_char / max(1, len(tokens))
    
    if len(linhas) > 3 and media_chars_linha < 25:
        motivos.append("Texto fragmentado (linhas curtas)")
        pontuacao -= 20
    if fracao_tokens_1 > MAX_FRACAO_TOKENS_1:
        motivos.append("Texto fragmentado (muitos tokens isolados)")
        pontuacao -= 20
        
    if tem_imagem:
        motivos.append("Imagem grande")
        # Se tem texto útil, perde menos, se não, perde mais
        if tam_util < MIN_CARACTERES_UTEIS:
            pontuacao -= 50
        else:
            pontuacao -= 10
            
    if tem_tabela_inconsistente:
        motivos.append("Tabela inconsistente")
        pontuacao -= 30
        
    if estava_pendente:
        motivos.append("Pendente de transcrição visual")
        pontuacao -= 50
        
    if estava_conferir:
        motivos.append("Marcada para conferência visual")
        pontuacao -= 30
        
    pontuacao = max(0, min(100, pontuacao))
    
    precisa_ia = pontuacao < 70 or estava_pendente or estava_conferir or tem_imagem or tem_tabela_inconsistente or (metodo == "ocr-tesseract" and confianca < MIN_CONFIANCA_OCR)
    
    # Categoria
    if metodo == "texto-nativo":
        if tem_tabela_inconsistente or tem_imagem:
            categoria = "hibrida"
        else:
            categoria = "digital"
    elif metodo == "texto-nativo+ocr-imagem":
        categoria = "hibrida"
    elif tem_imagem and tam_util < MIN_CARACTERES_UTEIS:
        categoria = "escaneada"
    elif tem_imagem and tam_util >= MIN_CARACTERES_UTEIS:
        categoria = "hibrida"
    elif precisa_ia:
        categoria = "complexa"
    else:
        categoria = "escaneada" # se foi OCR e passou bem, ou algo assim
        
    return {
        "categoria": categoria,
        "pontuacao": pontuacao,
        "motivos": list(set(motivos)),
        "precisa_ia": precisa_ia
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pasta")
    ap.add_argument("--pdf")
    a = ap.parse_args()
    
    chk_dir = os.path.join(a.pasta, ".checkpoint")
    rel_file = os.path.join(a.pasta, "relatorio_extracao.json")
    
    pendentes = []
    conferir = []
    if os.path.exists(rel_file):
        with open(rel_file, "r", encoding="utf-8") as f:
            rel = json.load(f)
            pendentes = rel.get("pendentes_transcricao_visual", [])
            conferir = rel.get("conferir_visualmente", [])
            
    paginas = []
    if os.path.exists(chk_dir):
        for f in os.listdir(chk_dir):
            if f.endswith(".json") and f.startswith("p"):
                try:
                    num = int(f[1:5])
                    paginas.append((num, os.path.join(chk_dir, f)))
                except:
                    pass
    paginas.sort()
    
    pdf_doc = None
    pdfplumb = None
    if a.pdf and os.path.exists(a.pdf):
        try:
            import pypdfium2 as pdfium
            pdf_doc = pdfium.PdfDocument(a.pdf)
        except:
            pass
        try:
            import pdfplumber
            pdfplumb = pdfplumber.open(a.pdf)
        except:
            pass
            
    resultado = {}
    
    for num, p_file in paginas:
        with open(p_file, "r", encoding="utf-8") as f:
            chk = json.load(f)
            
        reg = chk.get("reg", {})
        texto = reg.get("texto", "")
        metodo = reg.get("metodo", "desconhecido")
        confianca = reg.get("confianca_media", 100.0)
        
        tem_imagem = False
        tem_tabela = False
        
        idx = num - 1
        if pdf_doc and idx < len(pdf_doc):
            pag = pdf_doc[idx]
            w, h = pag.get_size()
            maior = 0.0
            for obj in pag.get_objects(filter=[pdfium.raw.FPDF_PAGEOBJ_IMAGE], max_depth=2):
                l, b, r, t = obj.get_bounds()
                maior = max(maior, abs((r - l) * (t - b)) / (max(1, w * h)))
            if maior >= MIN_FRACAO_IMAGEM:
                tem_imagem = True
                
        if pdfplumb and idx < len(pdfplumb.pages):
            pp = pdfplumb.pages[idx]
            extraidas = pp.extract_tables() or []
            if not extraidas:
                extraidas = pp.extract_tables(table_settings={"vertical_strategy": "text", "text_x_tolerance": 1, "text_y_tolerance": 5}) or []
            
            for tb in extraidas:
                # Checa inconsistência
                vazias = 0
                total = 0
                for linha in tb:
                    for cel in linha:
                        total += 1
                        if not cel or not cel.strip():
                            vazias += 1
                if total > 0 and vazias / total > MAX_CELULAS_VAZIAS_TABELA:
                    tem_tabela = True
                    break
                    
        est_pendente = num in pendentes
        est_conferir = num in conferir
        
        met = calcula_metricas(texto, metodo, confianca, tem_imagem, tem_tabela, est_pendente, est_conferir)
        resultado[str(num)] = met
        
    if pdfplumb:
        pdfplumb.close()
        
    out_file = os.path.join(a.pasta, "qualidade.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
