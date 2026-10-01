#!/usr/bin/env python3
"""Teste da tarefa L05: checkpoints por página no extrair.py e OCR com uma única passada do Tesseract.
PDF escaneado FICTÍCIO gerado no próprio teste; pasta temporária; sem IA.

Uso: python -X utf8 plugin/investigacao-cpj/app/testes/teste_ocr_checkpoint_claude.py
"""
import glob, json, os, shutil, subprocess, sys, tempfile, time

AQUI = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.normpath(os.path.join(AQUI, "..", ".."))
RAIZ = os.path.normpath(os.path.join(PLUGIN, "..", ".."))
SP = os.path.join(PLUGIN, "skills", "pdf-autos-policiais", "scripts")
T = tempfile.mkdtemp(prefix="cpj-l05-")
falhas = []

env = dict(os.environ, PYTHONIOENCODING="utf-8")
TESS_DIR = r"C:\Program Files\Tesseract-OCR"
if os.path.isdir(TESS_DIR): env["PATH"] = env.get("PATH", "") + ";" + TESS_DIR
td = os.path.join(RAIZ, "ferramentas", "tessdata")
if os.path.exists(os.path.join(td, "por.traineddata")): env["TESSDATA_PREFIX"] = td
os.environ.update(env)


def ok(cond, msg):
    print(("  OK    " if cond else "  FALHA ") + msg)
    if not cond: falhas.append(msg)


def extrair(pdf, saida, *extra):
    r = subprocess.run([sys.executable, "-X", "utf8", os.path.join(SP, "extrair.py"), pdf, "--saida", saida, "--lang", "por", *extra],
                       env=env, capture_output=True, text=True, encoding="utf-8", timeout=600)
    if r.returncode != 0: print(r.stderr[-800:])
    return r, json.load(open(os.path.join(saida, "relatorio_extracao.json"), encoding="utf-8"))


def transcricao(saida):
    """Transcrição sem a linha 'Gerado em' (única parte que muda entre execuções)."""
    return "\n".join(l for l in open(os.path.join(saida, "transcricao.md"), encoding="utf-8").read().splitlines()
                     if not l.startswith("- Páginas:"))


def pagina(linhas):
    from PIL import Image, ImageDraw, ImageFont
    try: f = ImageFont.truetype("arial.ttf", 30)
    except OSError: f = ImageFont.load_default()
    img = Image.new("RGB", (1700, 2200), "white"); d = ImageDraw.Draw(img); y = 160
    for l in linhas: d.text((150, y), l, fill="black", font=f); y += 55
    return img


try:
    import pytesseract
    tem_tess = "por" in pytesseract.get_languages(config="")
except Exception:
    tem_tess = False
if not tem_tess:
    print("Tesseract com idioma 'por' indisponível — teste de OCR não executado."); sys.exit(0)

try:
    pdf = os.path.join(T, "ip_escaneado_ficticio.pdf")
    pags = [pagina(["TERMO DE DECLARAÇÕES — DOCUMENTO FICTÍCIO", "", f"Página de teste número {n}.",
                    "Declarou que transferiu R$ 1.234,56 via Pix para chave aleatória.",
                    "Data        Valor        Banco", "05/03/2026  R$ 1.234,56  BANCO FICTÍCIO S.A."]) for n in (1, 2, 3)]
    pags.append(pagina([]))   # página em branco: vai para conferência visual
    pags[0].save(pdf, save_all=True, append_images=pags[1:], resolution=200)
    s1 = os.path.join(T, "saida")

    print("L05.1 Primeira extração (OCR de 4 páginas escaneadas)")
    t0 = time.time(); r, rel = extrair(pdf, s1); t_cheio = time.time() - t0
    ok(r.returncode == 0 and rel["metodos"].get("ocr-tesseract") == 4, f"4 páginas por OCR ({rel['metodos']})")
    ok(rel["paginas_reaproveitadas"] == 0, "nada reaproveitado na primeira vez")
    ok(len(glob.glob(os.path.join(s1, ".checkpoint", "p*.json"))) == 4, "um checkpoint por página")
    ok(rel["conferir_visualmente"] == [4] and os.path.exists(os.path.join(s1, "paginas_visao", "p0004.png")),
       "página em branco marcada para conferência com imagem")
    base = transcricao(s1)
    ok("Página de teste número 2" in base and "R$ 1.234,56" in base, "texto reconhecido na transcrição")

    print("L05.2 Uma única passada do Tesseract, mesmo texto do image_to_string")
    esperado = pytesseract.image_to_string(pags[0], lang="por").strip()
    ck = json.load(open(os.path.join(s1, ".checkpoint", "p0001.json"), encoding="utf-8"))
    ok(ck["reg"]["texto"] == esperado, "texto de image_to_data reconstruído = image_to_string (página 1)")
    src = open(os.path.join(SP, "extrair.py"), encoding="utf-8").read()
    ok("pytesseract.image_to_string(" not in src and src.count("pytesseract.image_to_data(") == 1,
       "extrair.py faz uma única chamada ao Tesseract por página")

    print("L05.3 Reprocessar o mesmo documento reaproveita tudo")
    tabs = sorted(os.listdir(os.path.join(s1, "tabelas"))) if os.path.isdir(os.path.join(s1, "tabelas")) else []
    subprocess.run([sys.executable, os.path.join(SP, "tabelas.py"), os.path.join(s1, "transcricao.md"), "--saida", s1], env=env, capture_output=True)
    tab1 = {f: open(os.path.join(s1, "tabelas", f), encoding="utf-8-sig").read() for f in os.listdir(os.path.join(s1, "tabelas"))}
    t0 = time.time(); r, rel = extrair(pdf, s1); t_rep = time.time() - t0
    ok(rel["paginas_reaproveitadas"] == 4 and "reaproveitada" in r.stderr, "4 páginas reaproveitadas, aviso no log")
    ok(transcricao(s1) == base, "transcrição idêntica à da primeira execução")
    ok(rel["conferir_visualmente"] == [4], "lista de conferência preservada")
    ok(t_rep < t_cheio, f"mais rápido ({t_rep:.1f}s × {t_cheio:.1f}s)")
    subprocess.run([sys.executable, os.path.join(SP, "tabelas.py"), os.path.join(s1, "transcricao.md"), "--saida", s1], env=env, capture_output=True)
    tab2 = {f: open(os.path.join(s1, "tabelas", f), encoding="utf-8-sig").read() for f in os.listdir(os.path.join(s1, "tabelas"))}
    ok(tab1 == tab2, "tabelas (CSV) idênticas após o reaproveitamento")

    print("L05.4 Queda no meio: só as páginas faltantes são refeitas")
    os.remove(os.path.join(s1, ".checkpoint", "p0002.json"))
    open(os.path.join(s1, ".checkpoint", "p0003.json"), "w", encoding="utf-8").write('{"reg": {"pagina": 3, "met')  # gravação interrompida
    r, rel = extrair(pdf, s1)
    ok(rel["paginas_reaproveitadas"] == 2, "checkpoint ausente e corrompido são refeitos; os íntegros reaproveitados")
    ok(transcricao(s1) == base, "resultado idêntico ao da extração completa")
    s2 = os.path.join(T, "saida-interrompida")
    p = subprocess.Popen([sys.executable, "-X", "utf8", os.path.join(SP, "extrair.py"), pdf, "--saida", s2, "--lang", "por"],
                         env=env, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True, encoding="utf-8")
    for ln in p.stderr:
        if ln.startswith("progresso 2/"): p.kill(); break
    p.wait(30)
    feitas = len(glob.glob(os.path.join(s2, ".checkpoint", "p*.json")))
    ok(feitas >= 2 and not os.path.exists(os.path.join(s2, "transcricao.md")), f"processo morto após 2 páginas deixou {feitas} checkpoint(s)")
    r, rel = extrair(pdf, s2)
    ok(rel["paginas_reaproveitadas"] >= 2 and transcricao(s2) == base, "retomada termina só o que faltava, com o mesmo texto")

    print("L05.5 Checkpoint não vale para outro documento nem outros parâmetros")
    r, rel = extrair(pdf, s1, "--dpi", "150")
    ok(rel["paginas_reaproveitadas"] == 0, "dpi diferente descarta os checkpoints")
    r, rel = extrair(pdf, s1)
    ok(rel["paginas_reaproveitadas"] == 0, "voltar ao dpi original também refaz (checkpoints são do último conjunto de parâmetros)")
    r, rel = extrair(pdf, s1, "--refazer")
    ok(rel["paginas_reaproveitadas"] == 0, "--refazer ignora checkpoints")
    pdf2 = os.path.join(T, "outro_documento.pdf")
    pags[1].save(pdf2, save_all=True, append_images=[pags[0], pags[2], pags[3]], resolution=200)
    r, rel = extrair(pdf2, s1)
    ok(rel["paginas_reaproveitadas"] == 0 and "número 2" in transcricao(s1).split("## Página 2")[0],
       "outro PDF na mesma pasta não herda páginas do anterior")

    print("L05.6 Transcrição visual feita depois prevalece sobre o checkpoint")
    r, rel = extrair(pdf, s1)
    open(os.path.join(s1, "transcricoes_visuais", "p0004.md"), "w", encoding="utf-8").write("Página em branco no original (conferido).")
    r, rel = extrair(pdf, s1)
    ok(rel["metodos"].get("transcricao-visual-llm") == 1 and "conferido" in transcricao(s1), "transcrição visual incorporada")
    ok(rel["conferir_visualmente"] == [], "página deixa de constar como pendente de conferência")
finally:
    shutil.rmtree(T, ignore_errors=True)

print(f"\n{'TUDO OK' if not falhas else str(len(falhas)) + ' FALHA(S)'}")
sys.exit(1 if falhas else 0)
