#!/usr/bin/env python3
"""Diagnóstico de PDF: hash, páginas, tamanho e camada de texto por página."""
import hashlib, json, os, sys
import pypdfium2 as pdfium

MIN_CHARS = 50  # abaixo disso a página é tratada como imagem (escaneada)

def faixas(nums):
    out, ini, ant = [], None, None
    for n in nums:
        if ini is None: ini = ant = n
        elif n == ant + 1: ant = n
        else: out.append(f"{ini}-{ant}" if ini != ant else str(ini)); ini = ant = n
    if ini is not None: out.append(f"{ini}-{ant}" if ini != ant else str(ini))
    return ", ".join(out)

def classificar_erro_pdfium(erro):
    mensagem = str(erro).casefold()
    if "password" in mensagem or "encrypted" in mensagem:
        return "senha", "O PDF está protegido por senha ou criptografia e não pôde ser aberto."
    if "data format error" in mensagem or "file not found or corrupted" in mensagem:
        return "corrompido", "O arquivo está corrompido, incompleto ou não é um PDF válido."
    return "desconhecido", f"Não foi possível abrir o PDF; motivo não identificado: {erro}"

def main(caminho):
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""): h.update(bloco)
    try:
        pdf = pdfium.PdfDocument(caminho)
    except pdfium.PdfiumError as e:
        motivo, mensagem = classificar_erro_pdfium(e)
        print(json.dumps({"erro": mensagem, "motivo_erro": motivo}, ensure_ascii=False)); return
    n = len(pdf)
    sem_texto = []
    total_chars = 0
    for i in range(n):
        txt = pdf[i].get_textpage().get_text_range().strip()
        total_chars += len(txt)
        if len(txt) < MIN_CHARS: sem_texto.append(i + 1)
    com_texto = n - len(sem_texto)
    mb = os.path.getsize(caminho) / 1_048_576
    if not sem_texto:
        tipo = "digital (camada de texto em todas as páginas)"
    elif com_texto == 0:
        tipo = "escaneado (nenhuma página com texto)"
    else:
        tipo = "misto (parte digital, parte escaneada)"
    r = {
        "arquivo": os.path.basename(caminho),
        "sha256": h.hexdigest(),
        "tamanho_mb": round(mb, 1),
        "paginas": n,
        "paginas_com_texto": com_texto,
        "paginas_sem_texto": len(sem_texto),
        "faixas_sem_texto": faixas(sem_texto),
        "tipo": tipo,
        "acima_100_paginas": n > 100,
        "acima_30mb_projetos": mb > 30,
        "partes_necessarias_100pg": -(-n // 100),
    }
    print(json.dumps(r, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main(sys.argv[1])
