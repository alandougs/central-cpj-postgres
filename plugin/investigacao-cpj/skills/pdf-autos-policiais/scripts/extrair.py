#!/usr/bin/env python3
"""Extração estruturada de PDF para Markdown, página a página, com rastreabilidade.
Uso: extrair.py arquivo.pdf [--saida pasta] [--ocr auto|tesseract|visao] [--lang por] [--dpi 200]

Por página: texto nativo -> usa direto; sem texto -> OCR Tesseract (se houver idioma) ou
renderiza PNG em <saida>/paginas_visao/ para transcrição visual pelo Claude.
Transcrições visuais salvas em <saida>/transcricoes_visuais/pNNNN.md são incorporadas ao rodar de novo.

Checkpoints (L05): páginas e metadados essenciais ficam em <saida>/.checkpoint/estado.json. Se o processamento cair ou o
documento for reprocessado, as páginas já feitas são reaproveitadas — valem só para o MESMO PDF (SHA-256) e os mesmos
parâmetros (idioma, dpi, limiares, modo de OCR, Tesseract disponível); qualquer diferença descarta os checkpoints.
Mesmo PDF já extraído em outro caso (workspace C: ou o paralelo em E:) é reaproveitado (--sem-reaproveitar desliga).
--refazer ignora os checkpoints. OCR: uma única passada do Tesseract por página (image_to_data dá confiança e texto).
"""
import argparse, datetime, errno, hashlib, json, os, re, shutil, stat, sys, time
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing, contextmanager
import pypdfium2 as pdfium
import estado_extracao as estado


@contextmanager
def trava_extracao(saida, espera):
    """O filho mantém a exclusividade durante a extração, mesmo se o servidor pai morrer."""
    caminho = estado.arquivo(saida).parent / "extracao.lock"
    estado._sem_reparse(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    estado._sem_reparse(caminho)
    fd = os.open(caminho, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "r+b") as f:
        estado._sem_reparse(caminho)
        info, atual = os.fstat(f.fileno()), caminho.stat()
        if not stat.S_ISREG(info.st_mode) or (info.st_dev, info.st_ino) != (atual.st_dev, atual.st_ino):
            raise ValueError("Trava da extração inválida.")
        if info.st_size == 0:
            f.write(b"\0"); f.flush()
        fim = time.monotonic() + espera
        while True:
            try:
                f.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as erro:
                if erro.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                    raise
                if time.monotonic() >= fim:
                    raise TimeoutError("Extração ocupada por outro processo; nenhum checkpoint foi alterado.") from erro
                time.sleep(.05)
        try:
            yield
        finally:
            f.seek(0)
            if os.name == "nt":
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            # Não remover o arquivo: outro processo pode já esperar pelo mesmo inode.


ap = argparse.ArgumentParser()
ap.add_argument("pdf"); ap.add_argument("--saida", default="extracao")
ap.add_argument("--ocr", default="auto", choices=["auto", "tesseract", "visao"])
ap.add_argument("--lang", default="por"); ap.add_argument("--dpi", type=int, default=200)
ap.add_argument("--min-chars", type=int, default=50); ap.add_argument("--conf-min", type=float, default=75)
ap.add_argument("--refazer", action="store_true", help="ignora checkpoints e refaz todas as páginas")
ap.add_argument("--texto-misto", type=int, default=600, help="abaixo disso (sem carimbos), página com imagem grande recebe OCR da imagem e vai para conferência")
ap.add_argument("--sem-reaproveitar", action="store_true", help="não busca o mesmo PDF já extraído em outro caso")
ap.add_argument("--workers", type=int, choices=(1, 2), default=2, help="processos OCR simultâneos (máximo 2); PDFium permanece sequencial")
ap.add_argument("--espera-trava", type=float, default=30, help="segundos de espera por outro extrator do mesmo documento (0 a 300)")
a = ap.parse_args()
if not 0 <= a.espera_trava <= 300:
    ap.error("--espera-trava deve estar entre 0 e 300 segundos")
# O escopo léxico libera a trava também no retorno/erro de runpy, sem encerrar o chamador.
with trava_extracao(a.saida, a.espera_trava):
    os.environ.setdefault("OMP_THREAD_LIMIT", "1")
    METODOS = {"texto-nativo", "texto-nativo+ocr-imagem", "ocr-tesseract", "pendente-transcricao-visual", "texto-nativo+transcricao-visual", "transcricao-visual-llm"}


    def texto_de_data(d):
        """Texto no mesmo formato do image_to_string, a partir do image_to_data (evita a 2ª passada do Tesseract):
        palavras da linha separadas por espaço, linhas por \\n, parágrafos/blocos por linha em branco."""
        out, ult = [], None
        for i, w in enumerate(d["text"]):
            if int(d["level"][i]) != 5: continue
            chave = (d["block_num"][i], d["par_num"][i], d["line_num"][i])
            if ult is not None: out.append("\n\n" if chave[:2] != ult[:2] else "\n" if chave != ult else " ")
            out.append(w); ult = chave
        return "".join(out).strip()


    def ler_checkpoint(p, num):
        """Registro da página se o checkpoint for íntegro; None se ausente ou inválido (a página é refeita)."""
        try:
            r = checkpoints.get("paginas", {}).get(str(num), {})
            reg = r["reg"]
            if reg.get("pagina") != num or reg.get("metodo") not in METODOS or not isinstance(reg.get("texto"), str): return None
            if reg["metodo"] == "ocr-tesseract" and not isinstance(reg.get("confianca_media"), (int, float)): return None
            return r
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            return None

    def ler_transcricao_visual(caminho):
        """BOM é codificação; vazio e placeholder não concluem uma página."""
        if not os.path.isfile(caminho):
            return None
        with open(caminho, encoding="utf-8-sig") as f:
            texto = f.read().strip()
        return texto if texto and texto != "[PENDENTE: transcrição visual]" else None

    h = hashlib.sha256()
    with open(a.pdf, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)

    tess_ok = False
    if a.ocr in ("auto", "tesseract"):
        try:
            import pytesseract
            raiz_ocr = os.path.abspath(os.path.join(os.path.dirname(__file__), *[".."] * 5))
            raizes_ocr = [os.environ.get("CPJ_WORKSPACE", raiz_ocr), raiz_ocr]
            candidatos_ocr = [os.environ.get("CPJ_TESSERACT", ""),
                              *[os.path.join(r, "ferramentas", "tesseract") for r in raizes_ocr],
                              r"C:\Program Files\Tesseract-OCR", r"C:\Program Files\PDF24\tesseract"]
            for pasta_ocr in candidatos_ocr:
                exe_ocr = pasta_ocr if pasta_ocr.lower().endswith("tesseract.exe") else os.path.join(pasta_ocr, "tesseract.exe")
                if pasta_ocr and os.path.isfile(exe_ocr):
                    pytesseract.pytesseract.tesseract_cmd = exe_ocr
                    break
            if not os.environ.get("TESSDATA_PREFIX"):
                for raiz_local in raizes_ocr:
                    idiomas_ocr = os.path.join(raiz_local, "ferramentas", "tessdata")
                    if os.path.isfile(os.path.join(idiomas_ocr, a.lang + ".traineddata")):
                        os.environ["TESSDATA_PREFIX"] = idiomas_ocr
                        break
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

    # checkpoints: válidos só para o mesmo PDF e os mesmos parâmetros
    dir_ck = os.path.join(a.saida, ".checkpoint")
    assinatura = {"versao": 2, "texto_misto": a.texto_misto, "sha256": h.hexdigest(), "lang": a.lang, "dpi": a.dpi, "min_chars": a.min_chars,
                  "conf_min": a.conf_min, "ocr": a.ocr, "tesseract": tess_ok}
    try:
        valido = estado.ler(a.saida, ".checkpoint/meta.json") == assinatura
    except (OSError, ValueError):
        valido = False

    # Um checkpoint legado pode ainda conter a pendência já preenchida no Markdown.
    # Conferir antes de qualquer gravação, inclusive da consolidação do estado legado.
    md_existente = os.path.join(a.saida, "transcricao.md")
    if valido and not a.refazer and os.path.isfile(md_existente):
        with open(md_existente, encoding="utf-8-sig") as f:
            partes = re.split(r"(?m)^## Página (\d+)[ \t]*$", f.read())
        estado_atual = estado.arquivo(a.saida)
        if estado_atual.exists():
            with open(estado_atual, encoding="utf-8") as f:
                registros = json.load(f).get("paginas", {})
        else:
            registros = {str(i): estado.ler(a.saida, f".checkpoint/p{i:04d}.json") for i in range(1, n + 1)}
        divergentes = []
        for numero, bloco in zip(partes[1::2], partes[2::2]):
            registro = registros.get(numero, {}) or {}
            reg = registro.get("reg") if isinstance(registro, dict) else None
            if not isinstance(reg, dict) or not isinstance(reg.get("texto"), str):
                continue  # Registro inválido continua sujeito ao reprocessamento normal.
            if reg["texto"].strip() != "[PENDENTE: transcrição visual]":
                continue
            texto = re.sub(r"\A\s*<!-- método:[^\n]*-->\s*", "", bloco)
            texto = re.sub(r"\n---\s*$", "", texto).strip()
            if not texto or texto == "[PENDENTE: transcrição visual]":
                continue
            tv = os.path.join(dir_tv, f"p{int(numero):04d}.md")
            if ler_transcricao_visual(tv) is not None:
                continue  # A transcrição visual será incorporada pelo fluxo existente.
            divergentes.append(numero)
        if divergentes:
            pdf.close()
            raise SystemExit("Retomada recusada: transcricao.md contém texto onde o checkpoint mantém uma pendência "
                             f"(página(s): {', '.join(divergentes)}). Nenhum Markdown ou checkpoint foi alterado. "
                             "Confira no original e reconcilie a transcrição pelo fluxo transcricoes_visuais/pNNNN.md; "
                             "use --refazer somente se desejar substituir explicitamente a extração existente.")


    def importar_de_outro_caso():
        """O mesmo PDF (SHA-256 e parâmetros iguais) já extraído em outro caso: copia checkpoints e transcrições visuais
        em vez de refazer OCR. Comum quando a mesma peça volta em nova O.S. ou pasta duplicada."""
        raiz = os.path.abspath(os.path.join(os.path.dirname(__file__), *[".."] * 5))
        destino = os.path.abspath(a.saida)
        raizes = os.environ.get("CPJ_WORKSPACES") or os.environ.get("CPJ_WORKSPACE") or os.pathsep.join([raiz, r"E:\CPJ - TRABALHO"])
        for ws in dict.fromkeys(raizes.split(os.pathsep)):
            base = os.path.join(ws, "casos")
            if not os.path.isdir(base): continue
            for caso in os.listdir(base):
                dir_ext = os.path.join(base, caso, "01-extracao")
                if not os.path.isdir(dir_ext): continue
                for doc in os.listdir(dir_ext):
                    origem = os.path.join(dir_ext, doc)
                    if os.path.abspath(origem) == destino: continue
                    try:
                        if estado.ler(origem, ".checkpoint/meta.json") != assinatura: continue
                    except (OSError, ValueError):
                        continue
                    importados = {"meta": assinatura, "paginas": {}}
                    for numero in range(1, n + 1):
                        registro = estado.ler(origem, f".checkpoint/p{numero:04d}.json")
                        if registro: importados["paginas"][str(numero)] = registro
                    estado.gravar(a.saida, importados)
                    tv_origem = os.path.join(origem, "transcricoes_visuais")
                    if os.path.isdir(tv_origem): shutil.copytree(tv_origem, dir_tv, dirs_exist_ok=True)
                    print(f"reaproveitando extração do mesmo PDF em {origem}", file=sys.stderr, flush=True)
                    return True
        return False


    if not a.refazer and not valido and not a.sem_reaproveitar:
        valido = importar_de_outro_caso()
    if a.refazer or not valido:
        estado.gravar(a.saida, {"meta": assinatura, "paginas": {}})
    elif not estado.arquivo(a.saida).exists():
        estado.gravar(a.saida, {"meta": assinatura, "paginas": {str(i): estado.ler(a.saida, f".checkpoint/p{i:04d}.json") for i in range(1, n + 1)}})
    checkpoints = json.loads(estado.arquivo(a.saida).read_text(encoding="utf-8"))
    checkpoints.pop("qualidade", None)
    checkpoints.pop("relatorio", None)
    reaproveitadas = 0


    def salvar_png(img, num):
        os.makedirs(dir_png, exist_ok=True); img.save(os.path.join(dir_png, f"p{num:04d}.png"))


    # Carimbos do e-SAJ/assinatura digital: não contam como conteúdo (página escaneada só com o rodapé é imagem).
    CARIMBO = re.compile(r"assinad[oa] digitalmente|certificad[oa] pel[oa]|conferir o original|esaj\.tjsp|pastadigital|abrirConferencia|"
                         r"protocolad[oa] em|liberad[oa] nos autos|c[óo]digo [0-9A-Z]{4,}|^\s*(p[áa]g\.?|fls\.?)\s*\d+\s*$", re.I)


    def texto_util(txt):
        return "\n".join(l for l in txt.splitlines() if l.strip() and not CARIMBO.search(l)).strip()


    def fracao_imagem(pag):
        """Fração da área da página coberta pela maior imagem (0 se não houver)."""
        try:
            w, h = pag.get_size(); maior = 0.0
            for obj in pag.get_objects(filter=[pdfium.raw.FPDF_PAGEOBJ_IMAGE], max_depth=2):
                l, b, r, t = (getattr(obj, "get_bounds", None) or obj.get_pos)(); maior = max(maior, abs((r - l) * (t - b)) / (w * h))
            return maior
        except Exception:
            return 0.0


    def ocr(img):
        """Uma passada do Tesseract: (confiança média, texto)."""
        import pytesseract
        d = pytesseract.image_to_data(img, lang=a.lang, output_type=pytesseract.Output.DICT)
        confs = [float(c) for c, w in zip(d["conf"], d["text"]) if w.strip() and float(c) >= 0]
        return (round(sum(confs) / len(confs), 1) if confs else 0.0), texto_de_data(d)


    def registrar(reg, flag=None, visual_hash=None):
        num = reg["pagina"]
        obj = {"reg": reg, "flag": flag}
        if visual_hash is not None:
            obj["visual_sha256"] = visual_hash
        checkpoints["paginas"][str(num)] = obj
        estado.gravar(a.saida, checkpoints)
        paginas.append(reg)
        if flag == "conferir": conferir.append(num)
        elif flag == "pendente": pendentes.append(num)
        print(f"progresso {len(paginas)}/{n}", file=sys.stderr, flush=True)


    def renderizar(pag):
        # Somente a thread principal toca em PDFium. O OCR recebe uma imagem independente.
        with closing(pag.render(scale=esc)) as bitmap:
            return bitmap.to_pil().copy()


    def processar_ocr(img, num, nativo=None):
        try:
            conf, txt = ocr(img)
            flag = None
            if nativo is not None:
                reg = {"pagina": num, "metodo": "texto-nativo+ocr-imagem" if txt else "texto-nativo",
                       "texto": nativo + (f"\n\n[OCR da imagem da página]\n{txt}" if txt else "")}
                flag = "conferir"
            else:
                reg = {"pagina": num, "metodo": "ocr-tesseract", "confianca_media": conf, "texto": txt}
                if conf < a.conf_min or len(txt) < a.min_chars: flag = "conferir"
            if flag: salvar_png(img, num)
            return reg, flag
        finally:
            img.close()


    ocr_jobs = 0
    fila_ocr = []
    try:
        with ThreadPoolExecutor(max_workers=a.workers) as pool:
            for i in range(n):
                num = i + 1
                tv = os.path.join(dir_tv, f"p{num:04d}.md")
                ck = os.path.join(dir_ck, f"p{num:04d}.json")
                anterior = ler_checkpoint(ck, num)
                with closing(pdf[i]) as pag:
                    visual = ler_transcricao_visual(tv)
                    if visual is not None:
                        visual_hash = hashlib.sha256(visual.encode("utf-8")).hexdigest()
                        if anterior and anterior.get("visual_sha256") == visual_hash:
                            reg = anterior["reg"]
                            reaproveitadas += 1
                        else:
                            with closing(pag.get_textpage()) as textpage: txt = textpage.get_text_range().strip()
                            reg = ({"pagina": num, "metodo": "texto-nativo+transcricao-visual",
                                    "texto": txt + "\n\n[Transcrição visual complementar]\n" + visual}
                                   if len(texto_util(txt)) >= a.min_chars else
                                   {"pagina": num, "metodo": "transcricao-visual-llm", "texto": visual})
                        registrar(reg, visual_hash=visual_hash)
                        continue
                    # Remover uma transcrição também invalida o registro visual anterior.
                    if anterior and anterior["reg"]["metodo"] in ("texto-nativo+transcricao-visual", "transcricao-visual-llm"):
                        anterior = None
                    if anterior:
                        reg, flag = anterior["reg"], anterior.get("flag")
                        if flag in ("conferir", "pendente") and not os.path.exists(os.path.join(dir_png, f"p{num:04d}.png")):
                            with renderizar(pag) as img: salvar_png(img, num)
                        registrar(reg, flag)
                        reaproveitadas += 1
                        continue
                    with closing(pag.get_textpage()) as textpage: txt = textpage.get_text_range().strip()
                    util = texto_util(txt)
                    misto = len(util) >= a.min_chars and len(util) < a.texto_misto and fracao_imagem(pag) >= 0.3
                    if len(util) >= a.min_chars and not misto:
                        registrar({"pagina": num, "metodo": "texto-nativo", "texto": txt})
                        continue
                    img = renderizar(pag)
                    if tess_ok:
                        # Até dois bitmaps em voo: memória limitada, sem PDFs compartilhados entre threads.
                        fila_ocr.append(pool.submit(processar_ocr, img, num, txt if misto else None))
                        ocr_jobs += 1
                        if len(fila_ocr) >= a.workers:
                            registrar(*fila_ocr.pop(0).result())
                    else:
                        with img: salvar_png(img, num)
                        registrar({"pagina": num, "metodo": "texto-nativo" if misto else "pendente-transcricao-visual",
                                   "texto": txt if misto else "[PENDENTE: transcrição visual]"},
                                  "conferir" if misto else "pendente")
            for futuro in fila_ocr: registrar(*futuro.result())
    finally:
        pdf.close()
    paginas.sort(key=lambda p: p["pagina"])
    pendentes.sort()
    conferir.sort()
    if reaproveitadas:
        print(f"checkpoint: {reaproveitadas} de {n} página(s) reaproveitada(s) sem novo OCR", file=sys.stderr, flush=True)

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

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from ordens_servico import extrair_ordens
    ordens_extraidas = extrair_ordens(a.saida)

    from collections import Counter
    rel = {"arquivo": os.path.basename(a.pdf), "sha256_original": h.hexdigest(), "paginas": n, "gerado_em": agora,
           "ferramentas": {"texto": "pypdfium2", "ocr": f"tesseract ({a.lang})" if tess_ok else "indisponível"},
           "metodos": dict(Counter(p["metodo"] for p in paginas)),
           "pendentes_transcricao_visual": pendentes, "conferir_visualmente": conferir, "paginas_reaproveitadas": reaproveitadas,
           "checkpoints_reutilizados": reaproveitadas, "ocr_workers": min(a.workers, ocr_jobs),
           "ordens_servico": ordens_extraidas}
    estado.atualizar(a.saida, "relatorio", rel)
    print(json.dumps(rel, ensure_ascii=False, indent=2))
