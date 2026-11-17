"""MQ06 — pedido de dilação de prazo não é autos nem relatório: a fila de O.S. não conta o PDF do pedido como PDF dos
autos nem o DOCX do pedido como relatório. Somente dados fictícios em pasta temporária.
Uso: python teste_fila_os_pedido_mq06.py"""
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[4]
FILA = RAIZ / "ferramentas" / "fila-os.py"
falhas = 0


def ok(cond, nome):
    global falhas
    print(("  OK    " if cond else "  FALHA ") + nome)
    falhas += not cond


def roda(*args, env):
    r = subprocess.run([sys.executable, "-B", str(FILA), *args], capture_output=True, text=True, encoding="utf-8",
                       env={**os.environ, "PYTHONIOENCODING": "utf-8", **env})
    return r.returncode, r.stdout + r.stderr


def caso(ws, nome, status, pdf=False, docxs=()):
    p = ws / "casos" / nome
    (p / "00-originais").mkdir(parents=True)
    (p / "03-relatorios").mkdir()
    (p / "caso.json").write_text(json.dumps({"status": status}), encoding="utf-8")
    if pdf:
        (p / "00-originais" / "autos.pdf").write_bytes(b"x")
    for d in docxs:
        (p / "03-relatorios" / d).write_bytes(b"x")


def pasta_os(ordens, nome, *arquivos):
    p = ordens / nome
    p.mkdir(parents=True)
    for a in arquivos:
        (p / a).write_bytes(b"x")


with tempfile.TemporaryDirectory() as tmp:
    ordens, ws = Path(tmp, "ordens"), Path(tmp, "ws")
    ordens.mkdir()
    PEDIDO_PDF = "PEDIDO-DILACAO-PRAZO-OS-9201-2026.pdf"
    PEDIDO_DOCX = "PEDIDO-DILACAO-PRAZO-OS-{}-2026.docx"

    # a) só o PDF do pedido na pasta da O.S.; caso recebido sem autos, com DOCX do pedido
    pasta_os(ordens, "OS 9201-26 - so pedido", PEDIDO_PDF)
    caso(ws, "OS-9201-2026", "recebido", docxs=[PEDIDO_DOCX.format(9201)])
    # b) caso em minuta com autos e só o DOCX do pedido
    caso(ws, "OS-9202-2026", "minuta", pdf=True, docxs=[PEDIDO_DOCX.format(9202)])
    # c) caso em minuta com autos, relatório e o DOCX do pedido
    caso(ws, "OS-9203-2026", "minuta", pdf=True, docxs=["RELATORIO-OS-9203-2026-v01.docx", PEDIDO_DOCX.format(9203)])
    # d) pasta da O.S. com autos e PDF do pedido lado a lado
    pasta_os(ordens, "OS 9204-26 - autos e pedido", "autos.pdf", "PEDIDO-DILACAO-PRAZO-OS-9204-2026.pdf")
    # e) variações de nome do pedido; nome com "relat" e "pedido" no DOCX também não é relatório
    pasta_os(ordens, "OS 9205-26 - variacoes", "autos.pdf", "Pedido de Dilação de Prazo.pdf", "DILACAO OS 9205.pdf",
             "RELATORIO-PEDIDO-DILACAO-9205.docx")
    env = {"CPJ_PASTA_OS": str(ordens), "CPJ_WORKSPACES": str(ws)}

    c, s = roda("listar", "--json", env=env)
    itens = json.loads(s) if c == 0 else {}
    ok(c == 0 and set(itens) == {"9201", "9202", "9203", "9204", "9205"}, "inventário traz as cinco O.S. fictícias")

    i = itens.get("9201", {})
    ok(i.get("pdfs") == [], "a) PDF do pedido na pasta da O.S. não conta como autos")
    ok(i.get("situacao") == "livre", "a) situação livre")
    ok(all(c_["docx"] == [] for c_ in i.get("casos", [])), "a) DOCX do pedido fora da lista docx do caso")

    i = itens.get("9202", {})
    ok(i.get("situacao") == "livre", "b) caso em minuta só com DOCX de pedido não é com_relatorio")
    ok(all(c_["docx"] == [] for c_ in i.get("casos", [])) and i.get("casos"), "b) DOCX do pedido fora da lista docx do caso")

    i = itens.get("9203", {})
    ok(i.get("situacao") == "com_relatorio", "c) relatório real + pedido: com_relatorio")
    nomes = [Path(d).name for c_ in i.get("casos", []) for d in c_["docx"]]
    ok(nomes == ["RELATORIO-OS-9203-2026-v01.docx"], "c) lista docx do caso traz só o relatório")

    i = itens.get("9204", {})
    ok([Path(p).name for p in i.get("pdfs", [])] == ["autos.pdf"], "d) autos e pedido lado a lado: pdfs traz só autos.pdf")

    i = itens.get("9205", {})
    ok([Path(p).name for p in i.get("pdfs", [])] == ["autos.pdf"],
       "e) 'Pedido de Dilação de Prazo.pdf' e 'DILACAO OS 9205.pdf' reconhecidos como pedido")
    ok(i.get("relatorios") == [] and i.get("situacao") == "livre", "e) RELATORIO-PEDIDO-DILACAO...docx na pasta não é relatório")

    # proxima: percorre a fila até esgotar e anota as O.S. oferecidas
    oferecidas = []
    for k in range(8):
        c, s = roda("proxima", "--agente", f"Ag{k}", env=env)
        m = re.search(r"O\.S\. (\d+): assumir", s)
        if c != 0 or not m:
            break
        oferecidas.append(m.group(1))
    ok("9201" not in oferecidas, "a) proxima não oferece a O.S. que só tem o PDF do pedido")
    ok("9202" in oferecidas, "b) proxima oferece a O.S. com autos e só pedido (livre)")
    ok("9203" not in oferecidas, "c) proxima não oferece a O.S. com relatório")

    c, s = roda("listar", env=env)
    quadro = ordens / "_CONTROLE-OS.md"
    texto = quadro.read_text(encoding="utf-8") if quadro.exists() else ""
    linha = next((l for l in texto.splitlines() if l.startswith("| 9202/")), "")
    ok(c == 0 and linha != "" and "PEDIDO" not in linha.upper(), "f) quadro não cita o pedido na linha da 9202")

print("\nTUDO OK" if not falhas else f"\n{falhas} FALHA(S)")
sys.exit(1 if falhas else 0)
