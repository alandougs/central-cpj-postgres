#!/usr/bin/env python3
"""Relatórios de REFERÊNCIA (já elaborados pelo investigador ou por colegas) para calibração e exemplos de estilo.
Usados somente como modelo de ESTRUTURA/ESTILO/ENCADEAMENTO — nunca como fonte de fatos de outro caso.

Uso (CLI):
  referencias.py importar ARQUIVO --autor "Nome" [--modalidade falso-parente] [--natureza Estelionato]
                                  [--peso 1-5] [--obs "texto"]
  referencias.py listar [--autor NOME]
  referencias.py atualizar REF_ID [--autor ...] [--modalidade ...] [--peso N] [--obs ...]
  referencias.py remover REF_ID

Guarda em referencias\\<REF_ID>\\: original.<ext>, texto.md (texto extraído) e meta.json.
Peso (qualidade): 5 = modelo exemplar ... 1 = usar com reservas. O indexar.py indexa texto.md (tipo=referencia).
"""
import argparse, datetime, json, os, re, shutil, unicodedata

def ws_padrao():
    """Workspace CPJ: CPJ_WORKSPACE > 1ª pasta acima deste script com casos/ e modelos/ > cwd com casos/ > erro."""
    if os.environ.get("CPJ_WORKSPACE"):
        return os.environ["CPJ_WORKSPACE"]
    d = os.path.dirname(os.path.abspath(__file__))
    while True:
        if os.path.isdir(os.path.join(d, "casos")) and os.path.isdir(os.path.join(d, "modelos")):
            return d
        if os.path.dirname(d) == d:
            break
        d = os.path.dirname(d)
    if os.path.isdir(os.path.join(os.getcwd(), "casos")):
        return os.getcwd()
    raise SystemExit("Workspace CPJ não encontrado: defina CPJ_WORKSPACE ou execute a partir da pasta do workspace "
                     "(a que contém as pastas casos e modelos).")


WS = ws_padrao()
REFS = os.path.join(WS, "referencias")


def slug(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:40] or "ref"


def extrair_texto(p):
    ext = os.path.splitext(p)[1].lower()
    if ext == ".md" or ext == ".txt":
        return open(p, encoding="utf-8-sig", errors="replace").read()
    if ext == ".docx":
        import docx
        d = docx.Document(p); out = []
        for bloco in d.element.body.iterchildren():
            tag = bloco.tag.split("}")[1]
            if tag == "p":
                t = docx.text.paragraph.Paragraph(bloco, d).text.strip()
                if t: out.append(t)
            elif tag == "tbl":
                t = docx.table.Table(bloco, d)
                linhas = [[c.text.strip().replace("\n", " ") for c in r.cells] for r in t.rows]
                if linhas:
                    out.append("| " + " | ".join(linhas[0]) + " |"); out.append("|" + "---|" * len(linhas[0]))
                    out += ["| " + " | ".join(r) + " |" for r in linhas[1:]]
        return "\n\n".join(out)
    if ext == ".pdf":
        import pypdfium2 as pdfium
        pdf = pdfium.PdfDocument(p)
        partes = [f"## Página {i + 1}\n\n{pdf[i].get_textpage().get_text_range().strip()}" for i in range(len(pdf))]
        txt = "\n\n".join(partes)
        if len(re.sub(r"\s|## Página \d+", "", txt)) < 200:
            raise ValueError("PDF sem camada de texto (escaneado). Envie o DOCX ou processe o PDF com OCR antes.")
        return txt
    raise ValueError("Formato não suportado: use .docx, .pdf (com texto) ou .md")


def importar(arquivo, autor, modalidade=None, natureza="Estelionato", peso=3, obs="", enviado_por=""):
    if not (autor or "").strip(): raise ValueError("Informe o autor do relatório.")
    peso = max(1, min(5, int(peso or 3)))
    texto = extrair_texto(arquivo)
    ref_id = f"{datetime.date.today():%Y%m%d}-{slug(autor)}-{slug(os.path.splitext(os.path.basename(arquivo))[0])[:20]}"
    base, k = ref_id, 2
    while os.path.exists(os.path.join(REFS, ref_id)): ref_id = f"{base}_{k}"; k += 1
    d = os.path.join(REFS, ref_id); os.makedirs(d)
    shutil.copyfile(arquivo, os.path.join(d, "original" + os.path.splitext(arquivo)[1].lower()))
    meta = {"id": ref_id, "autor": autor.strip(), "modalidade": modalidade or None, "natureza": natureza or "",
            "peso": peso, "obs": obs or "", "arquivo_original": os.path.basename(arquivo), "enviado_por": enviado_por,
            "importado_em": datetime.datetime.now().isoformat(timespec="seconds"),
            "uso": "exemplo de estrutura e estilo — nunca fonte de fatos de outro caso"}
    cab = "---\n" + "\n".join(f"{k}: {v}" for k, v in (("tipo", "referencia"), ("autor", meta["autor"]),
                              ("modalidade", meta["modalidade"] or ""), ("peso", peso))) + "\n---\n\n"
    open(os.path.join(d, "texto.md"), "w", encoding="utf-8").write(cab + texto)
    json.dump(meta, open(os.path.join(d, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return meta


def listar(autor=None):
    if not os.path.isdir(REFS): return []
    out = []
    for r in sorted(os.listdir(REFS)):
        p = os.path.join(REFS, r, "meta.json")
        if os.path.exists(p):
            m = json.load(open(p, encoding="utf-8"))
            if not autor or slug(autor) in slug(m.get("autor")): out.append(m)
    return sorted(out, key=lambda m: (-m.get("peso", 3), m.get("autor", "")))


def atualizar(ref_id, **campos):
    p = os.path.join(REFS, ref_id, "meta.json")
    if not os.path.exists(p): raise FileNotFoundError(ref_id)
    m = json.load(open(p, encoding="utf-8"))
    for k in ("autor", "modalidade", "natureza", "obs"):
        if campos.get(k) is not None: m[k] = campos[k]
    if campos.get("peso") is not None: m["peso"] = max(1, min(5, int(campos["peso"])))
    json.dump(m, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    t = os.path.join(REFS, ref_id, "texto.md")  # mantém o cabeçalho do texto coerente (reindexa)
    corpo = re.sub(r"^---\n.*?\n---\n\n", "", open(t, encoding="utf-8").read(), flags=re.S)
    cab = f"---\ntipo: referencia\nautor: {m['autor']}\nmodalidade: {m.get('modalidade') or ''}\npeso: {m['peso']}\n---\n\n"
    open(t, "w", encoding="utf-8").write(cab + corpo)
    return m


def remover(ref_id):
    d = os.path.normpath(os.path.join(REFS, ref_id))
    if not d.startswith(os.path.normpath(REFS) + os.sep) or not os.path.isdir(d): raise FileNotFoundError(ref_id)
    shutil.rmtree(d)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("importar"); s.add_argument("arquivo"); s.add_argument("--autor", required=True)
    s.add_argument("--modalidade"); s.add_argument("--natureza", default="Estelionato"); s.add_argument("--peso", type=int, default=3)
    s.add_argument("--obs", default="")
    s = sub.add_parser("listar"); s.add_argument("--autor")
    s = sub.add_parser("atualizar"); s.add_argument("ref_id"); s.add_argument("--autor"); s.add_argument("--modalidade")
    s.add_argument("--natureza"); s.add_argument("--peso", type=int); s.add_argument("--obs")
    s = sub.add_parser("remover"); s.add_argument("ref_id")
    a = ap.parse_args()
    if a.cmd == "importar":
        m = importar(a.arquivo, a.autor, a.modalidade, a.natureza, a.peso, a.obs); print(f"Referência {m['id']} importada. Rode indexar.py.")
    elif a.cmd == "listar":
        for m in listar(a.autor): print(f"{m['id']:<50} peso {m['peso']}  {m['autor']:<25} {m.get('modalidade') or '-'}")
    elif a.cmd == "atualizar":
        atualizar(a.ref_id, autor=a.autor, modalidade=a.modalidade, natureza=a.natureza, peso=a.peso, obs=a.obs); print("Atualizado. Rode indexar.py.")
    else:
        remover(a.ref_id); print("Removida. Rode indexar.py.")
