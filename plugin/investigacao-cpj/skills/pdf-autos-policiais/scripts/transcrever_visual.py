"""Transcrição visual por página; a Central fornece executor com aceite e orçamento."""
import datetime
import hashlib
import json
from pathlib import Path
import tempfile
import os


def caminho(pasta, relativo):
    raiz = Path(pasta).resolve()
    p = (raiz / relativo).resolve()
    if not p.is_relative_to(raiz): raise ValueError("Caminho fora da extração.")
    return p


def ler_json(pasta, nome):
    p = caminho(pasta, nome)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def paginas_pendentes(pasta):
    r = ler_json(pasta, "relatorio_extracao.json")
    q = ler_json(pasta, "qualidade.json")
    n = r.get("paginas", 0)
    ps = set(r.get("pendentes_transcricao_visual", []) + r.get("conferir_visualmente", []))
    ps.update(int(k) for k, v in q.items() if v.get("precisa_ia") is True)
    if not isinstance(n, int) or any(type(p) is not int or not 1 <= p <= n for p in ps):
        raise ValueError("Diagnóstico com página inválida.")
    return sorted(ps)


def validar_replay(pasta, original, ambiente=None):
    """Recusa mudanças que obrigariam o extrator a descartar checkpoints e rodar OCR."""
    meta = ler_json(pasta, ".checkpoint/meta.json")
    campos = {"versao", "sha256", "texto_misto", "lang", "dpi", "min_chars", "conf_min", "ocr", "tesseract"}
    if not campos.issubset(meta) or meta.get("versao") != 2:
        raise RuntimeError("Checkpoint de extração ausente ou incompatível.")
    with open(original, "rb") as f:
        h = hashlib.file_digest(f, "sha256").hexdigest()
    if h != meta.get("sha256"): raise RuntimeError("SHA do original mudou; execute processamento local antes da transcrição visual.")
    r = ler_json(pasta, "relatorio_extracao.json")
    for n in range(1, r.get("paginas", 0) + 1):
        c = ler_json(pasta, f".checkpoint/p{n:04d}.json").get("reg", {})
        if c.get("pagina") != n or not isinstance(c.get("texto"), str) or c.get("metodo") not in {
            "texto-nativo", "texto-nativo+ocr-imagem", "ocr-tesseract", "pendente-transcricao-visual", "texto-nativo+transcricao-visual", "transcricao-visual-llm"}:
            raise RuntimeError("Página com checkpoint ausente ou inválido; execute processamento local primeiro.")
        if c["metodo"] == "ocr-tesseract" and not isinstance(c.get("confianca_media"), (float, int)):
            raise RuntimeError("Confiança OCR ausente no checkpoint.")
    tess_ok = False
    if meta.get("ocr") in ("auto", "tesseract"):
        try:
            if ambiente is not None:
                import subprocess, sys
                r = subprocess.run([sys.executable, "-c", "import json,pytesseract,sys; print(json.dumps(sys.argv[1] in pytesseract.get_languages(config='')))", meta["lang"]],
                                   env=ambiente, capture_output=True, text=True, timeout=20,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                tess_ok = r.returncode == 0 and json.loads(r.stdout) is True
            else:
                import pytesseract
                tess_ok = meta["lang"] in pytesseract.get_languages(config="")
        except Exception: pass
    if tess_ok != meta.get("tesseract"):
        raise RuntimeError("Disponibilidade de Tesseract mudou; execute processamento local antes da transcrição visual.")
    return meta


def assinatura_checkpoints(pasta):
    raiz = caminho(pasta, ".checkpoint")
    h = hashlib.sha256()
    for p in sorted(raiz.glob("*.json")):
        if p.name != "meta.json" and not (p.name.startswith("p") and p.name[1:5].isdigit()): continue
        seguro = caminho(pasta, ".checkpoint/" + p.name)
        h.update(p.name.encode()); h.update(seguro.read_bytes())
    return h.hexdigest()


def png_pagina(pasta, numero, original=None):
    p = caminho(pasta, f"paginas_visao/p{numero:04d}.png")
    if not p.exists():
        if original is None: raise ValueError("PNG da página ausente; informe o PDF original local.")
        import pypdfium2 as pdfium
        from contextlib import closing
        meta = ler_json(pasta, ".checkpoint/meta.json")
        with closing(pdfium.PdfDocument(str(original))) as doc:
            if not 1 <= numero <= len(doc): raise ValueError("Página fora do PDF original.")
            with closing(doc[numero - 1]) as pag:
                bitmap = pag.render(scale=meta.get("dpi", 200) / 72)
                try:
                    p.parent.mkdir(parents=True, exist_ok=True)
                    bitmap.to_pil().save(p)
                finally: bitmap.close()
    dados = p.read_bytes()
    if not dados.startswith(b"\x89PNG\r\n\x1a\n"): raise ValueError("Imagem da página não é PNG.")
    return dados


def transcrever(pasta, executor, original=None, progresso=None, paginas=None):
    paginas = paginas_pendentes(pasta) if paginas is None else paginas
    total = ler_json(pasta, "relatorio_extracao.json").get("paginas", 0)
    if any(type(n) is not int or not 1 <= n <= total for n in paginas): raise ValueError("Página inválida.")
    gravadas, existentes = [], []
    for i, n in enumerate(paginas):
        p = caminho(pasta, f"transcricoes_visuais/p{n:04d}.md")
        if p.exists():
            existentes.append(n)
            continue
        dados = png_pagina(pasta, n, original)
        if progresso: progresso(i, len(paginas), n)
        r = executor(dados)
        texto = r.get("texto")
        if not isinstance(texto, str) or not texto.strip(): raise RuntimeError("Provedor não retornou transcrição.")
        cab = (f"<!-- origem: API visual {r['provedor']}/{r['modelo']}; página {n}; "
               f"PNG sha256 {hashlib.sha256(dados).hexdigest()}; {datetime.datetime.now().isoformat(timespec='seconds')} -->\n"
               "[CONFERIR — TRANSCRIÇÃO VISUAL POR IA; DÍGITOS INCERTOS DEVEM SER ?]\n\n")
        p.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".visual-", dir=p.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f: f.write(cab + texto.strip() + "\n")
            # Publicação exclusiva: outro pedido/humano pode ter gravado durante HTTP.
            try: os.link(tmp, p)
            except FileExistsError: existentes.append(n)
            else: gravadas.append(n)
        finally: os.unlink(tmp)
    return {"gravadas": gravadas, "existentes": existentes, "paginas": len(paginas)}
