#!/usr/bin/env python3
"""Extração estruturada de PDF para Markdown, página a página, com rastreabilidade.
Uso: extrair.py arquivo.pdf [--saida pasta] [--ocr auto|tesseract|visao] [--lang por] [--dpi 200]

Por página: texto nativo -> usa direto; sem texto -> OCR Tesseract (se houver idioma) ou
renderiza PNG em <saida>/paginas_visao/ para transcrição visual pelo Claude.
Transcrições visuais salvas em <saida>/transcricoes_visuais/pNNNN.md são incorporadas ao rodar de novo.
"""
import argparse, datetime, hashlib, json, os, sys
import pypdfium2 as pdfium

ap = argparse.ArgumentParser()
ap.add_argument("pdf"); ap.add_argument("--saida", default="extracao")
ap.add_argument("--ocr", default="auto", choices=["auto", "tesseract", "visao"])
ap.add_argument("--lang", default="por"); ap.add_argument("--dpi", type=int, default=200)
ap.add_argument("--min-chars", type=int, default=50); ap.add_argument("--conf-min", type=float, default=75)
a = ap.parse_args()

h = hashlib.sha256()
with open(a.pdf, "rb") as f:
    for b in iter(lambda: f.read(1 << 20), b""): h.update(b)

tess_ok = False
if a.ocr in ("auto", "tesseract"):
    try:
        import pytesseract
        tess_ok = a.lang in pytesseract.get_languages(config="")
    except Exception:
        tess_ok = False
    if a.ocr == "tesseract" and not tess_ok:
        raise SystemExit(f"Tesseract sem o idioma '{a.lang}'. Instale o pacote de idioma ou use --ocr visao.")

os.makedirs(a.saida, exist_ok=True)
dir_png = os.path.join(a.saida, "paginas_visao"); dir_tv = os.path.join(a.saida, "transcricoes_visuais")
os.makedirs(dir_tv, exist_ok=True)
pdf = pdfium.PdfDocument(a.pdf); n = len(pdf)
esc = a.dpi / 72
paginas, pendentes, conferir = [], [], []

for i in range(n):
    num = i + 1
    tv = os.path.join(dir_tv, f"p{num:04d}.md")
    txt = pdf[i].get_textpage().get_text_range().strip()
    reg = {"pagina": num}
    if len(txt) >= a.min_chars:
        reg.update(metodo="texto-nativo", texto=txt)
    elif os.path.exists(tv):
        reg.update(metodo="transcricao-visual-llm", texto=open(tv, encoding="utf-8").read().strip())
    else:
        img = pdf[i].render(scale=esc).to_pil()
        if tess_ok:
            import pytesseract
            d = pytesseract.image_to_data(img, lang=a.lang, output_type=pytesseract.Output.DICT)
            confs = [float(c) for c, w in zip(d["conf"], d["text"]) if w.strip() and float(c) >= 0]
            conf = round(sum(confs) / len(confs), 1) if confs else 0.0
            t = pytesseract.image_to_string(img, lang=a.lang).strip()
            reg.update(metodo="ocr-tesseract", confianca_media=conf, texto=t)
            if conf < a.conf_min or len(t) < a.min_chars:
                conferir.append(num)
                os.makedirs(dir_png, exist_ok=True); img.save(os.path.join(dir_png, f"p{num:04d}.png"))
        else:
            os.makedirs(dir_png, exist_ok=True); img.save(os.path.join(dir_png, f"p{num:04d}.png"))
            reg.update(metodo="pendente-transcricao-visual", texto="[PENDENTE: transcrição visual]")
            pendentes.append(num)
    paginas.append(reg)
    print(f"progresso {num}/{n}", file=sys.stderr, flush=True)

agora = datetime.datetime.now().isoformat(timespec="seconds")
cab = [f"# Transcrição — {os.path.basename(a.pdf)}", "",
       f"- SHA-256 do original: `{h.hexdigest()}`",
       f"- Páginas: {n} | Gerado em: {agora}",
       "- Numeração: `Página N` = página do arquivo PDF (não confundir com fls. dos autos).",
       "- Documento de apoio analítico. Não substitui o original; conferir dados críticos na imagem da página.", ""]
corpo = []
for p in paginas:
    extra = f" | confiança OCR {p['confianca_media']}%" if "confianca_media" in p else ""
    alerta = " | ⚠ CONFERIR" if p["pagina"] in conferir else ""
    corpo += [f"---", f"## Página {p['pagina']}", f"<!-- método: {p['metodo']}{extra}{alerta} -->", "", p["texto"], ""]
with open(os.path.join(a.saida, "transcricao.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(cab + corpo))

from collections import Counter
rel = {"arquivo": os.path.basename(a.pdf), "sha256_original": h.hexdigest(), "paginas": n, "gerado_em": agora,
       "ferramentas": {"texto": "pypdfium2", "ocr": f"tesseract ({a.lang})" if tess_ok else "indisponível"},
       "metodos": dict(Counter(p["metodo"] for p in paginas)),
       "pendentes_transcricao_visual": pendentes, "conferir_visualmente": conferir}
with open(os.path.join(a.saida, "relatorio_extracao.json"), "w", encoding="utf-8") as f:
    json.dump(rel, f, ensure_ascii=False, indent=2)
print(json.dumps(rel, ensure_ascii=False, indent=2))
