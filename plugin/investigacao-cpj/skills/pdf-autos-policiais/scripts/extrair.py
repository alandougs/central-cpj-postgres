#!/usr/bin/env python3
"""Extrai PDF por página, com checkpoints para retomar OCR sem repetir páginas prontas."""
import argparse, datetime, hashlib, json, os, sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import pypdfium2 as pdfium

p=argparse.ArgumentParser(); p.add_argument("pdf"); p.add_argument("--saida",default="extracao"); p.add_argument("--ocr",default="auto",choices=["auto","tesseract","visao"]); p.add_argument("--lang",default="por"); p.add_argument("--dpi",type=int,default=200); p.add_argument("--min-chars",type=int,default=50); p.add_argument("--conf-min",type=float,default=75); p.add_argument("--workers",type=int,choices=[1,2],default=min(2,os.cpu_count() or 1),help="OCR paralelo limitado a 2 processos Tesseract"); a=p.parse_args()
def sha(c):
 h=hashlib.sha256()
 with open(c,"rb") as f:
  for b in iter(lambda:f.read(1<<20),b""): h.update(b)
 return h.hexdigest()
def salvar(c,d):
 t=c+".tmp"
 with open(t,"w",encoding="utf-8") as f: json.dump(d,f,ensure_ascii=False,indent=2)
 os.replace(t,c)
def texto(d):
 out=[]; atual=[]; chave=None
 for i,w in enumerate(d["text"]):
  w=(w or "").strip()
  if not w: continue
  nova=tuple(d[k][i] for k in ("block_num","par_num","line_num"))
  if chave is not None and nova!=chave: out.append(" ".join(atual)); atual=[]
  chave=nova; atual.append(w)
 if atual: out.append(" ".join(atual))
 return "\n".join(out).strip()

def reconhecer(img, lang):
 import pytesseract
 dados=pytesseract.image_to_data(img,lang=lang,output_type=pytesseract.Output.DICT)
 confs=[float(c) for c,w in zip(dados["conf"],dados["text"]) if (w or "").strip() and float(c)>=0]
 conteudo=texto(dados); conf=round(sum(confs)/len(confs),1) if confs else 0
 return conteudo,conf

os.makedirs(a.saida,exist_ok=True); tvd=os.path.join(a.saida,"transcricoes_visuais"); pngd=os.path.join(a.saida,"paginas_visao"); os.makedirs(tvd,exist_ok=True)
h=sha(a.pdf); params={"ocr":a.ocr,"lang":a.lang,"dpi":a.dpi,"min_chars":a.min_chars,"conf_min":a.conf_min}; estado_p=os.path.join(a.saida,"checkpoints-extracao.json")
try: estado=json.load(open(estado_p,encoding="utf-8"))
except (OSError,ValueError): estado={}
if estado.get("schema")!="cpj-extracao/2" or estado.get("sha256_original")!=h or estado.get("parametros")!=params: estado={"schema":"cpj-extracao/2","sha256_original":h,"parametros":params,"paginas":{}}
tess=False
if a.ocr in ("auto","tesseract"):
 try:
  import pytesseract; tess=a.lang in pytesseract.get_languages(config="")
 except Exception: tess=False
 if a.ocr=="tesseract" and not tess: raise SystemExit(f"Tesseract sem o idioma '{a.lang}'. Instale o pacote de idioma ou use --ocr visao.")
pdf=pdfium.PdfDocument(a.pdf); paginas=[None]*len(pdf); pend=[]; conferir=[]; retomadas=0; pendentes_ocr=[]; concluidas=0
for i in range(len(pdf)):
 n=i+1; chave=str(n); tv=os.path.join(tvd,f"p{n:04d}.md"); reg=estado["paginas"].get(chave)
 if reg and not(reg.get("metodo")=="pendente-transcricao-visual" and os.path.exists(tv)):
  retomadas+=1; paginas[i]=reg
 else:
  native=pdf[i].get_textpage().get_text_range().strip(); reg={"pagina":n}
  if len(native)>=a.min_chars: reg.update(metodo="texto-nativo",texto=native)
  elif os.path.exists(tv): reg.update(metodo="transcricao-visual-llm",texto=open(tv,encoding="utf-8").read().strip())
  else:
   img=pdf[i].render(scale=a.dpi/72).to_pil()
   if tess:
    pendentes_ocr.append((i,n,img))
   else:
    os.makedirs(pngd,exist_ok=True); img.save(os.path.join(pngd,f"p{n:04d}.png")); reg.update(metodo="pendente-transcricao-visual",texto="[PENDENTE: transcrição visual]")
  if paginas[i] is None and not any(x[1]==n for x in pendentes_ocr):
   estado["paginas"][chave]=reg; salvar(estado_p,estado); paginas[i]=reg
   concluidas+=1; print(f"progresso {concluidas}/{len(pdf)}",file=sys.stderr,flush=True)
if pendentes_ocr:
 os.environ["OMP_THREAD_LIMIT"]="1"
 trabalhadores=min(a.workers,len(pendentes_ocr))
 with ThreadPoolExecutor(max_workers=trabalhadores) as pool:
  futuros={pool.submit(reconhecer,img,a.lang):(i,n,img) for i,n,img in pendentes_ocr}
  for futuro in as_completed(futuros):
   i,n,img=futuros[futuro]; t,conf=futuro.result(); reg={"pagina":n,"metodo":"ocr-tesseract","confianca_media":conf,"texto":t}
   if conf<a.conf_min or len(t)<a.min_chars:
    reg["conferir"]=True; os.makedirs(pngd,exist_ok=True); img.save(os.path.join(pngd,f"p{n:04d}.png"))
   estado["paginas"][str(n)]=reg; salvar(estado_p,estado); paginas[i]=reg
   concluidas+=1; print(f"progresso {concluidas}/{len(pdf)}",file=sys.stderr,flush=True)
for x in paginas:
 if x.get("metodo")=="pendente-transcricao-visual": pend.append(x["pagina"])
 if x.get("conferir"): conferir.append(x["pagina"])
agora=datetime.datetime.now().isoformat(timespec="seconds"); cab=[f"# Transcrição — {os.path.basename(a.pdf)}","",f"- SHA-256 do original: `{h}`",f"- Páginas: {len(pdf)} | Gerado em: {agora}","- Numeração: `Página N` = página do arquivo PDF (não confundir com fls. dos autos).","- Documento de apoio analítico. Não substitui o original; conferir dados críticos na imagem da página.",""]; corpo=[]
for x in paginas:
 extra=f" | confiança OCR {x['confianca_media']}%" if "confianca_media" in x else ""; alerta=" | ⚠ CONFERIR" if x.get("conferir") else ""; corpo += ["---",f"## Página {x['pagina']}",f"<!-- método: {x['metodo']}{extra}{alerta} -->","",x["texto"],""]
with open(os.path.join(a.saida,"transcricao.md"),"w",encoding="utf-8") as f:f.write("\n".join(cab+corpo))
rel={"arquivo":os.path.basename(a.pdf),"sha256_original":h,"paginas":len(pdf),"gerado_em":agora,"ferramentas":{"texto":"pypdfium2","ocr":f"tesseract ({a.lang})" if tess else "indisponível"},"ocr_workers":min(a.workers,len(pendentes_ocr)) if pendentes_ocr else 0,"metodos":dict(Counter(x["metodo"] for x in paginas)),"pendentes_transcricao_visual":pend,"conferir_visualmente":conferir,"checkpoints_reutilizados":retomadas}; salvar(os.path.join(a.saida,"relatorio_extracao.json"),rel); print(json.dumps(rel,ensure_ascii=False,indent=2))
