"""MQ05 — pasta única por O.S.: a fila de O.S. reconhece o PDF dos autos em casos\\<ID>\\00-originais e a O.S.
que só existe como caso. Somente dados fictícios em pasta temporária. Uso: python teste_fila_os_caso_mq05.py"""
import json
import os
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


def caso(ws, nome, status, pdf=False, docx=False):
    p = ws / "casos" / nome
    (p / "00-originais").mkdir(parents=True)
    (p / "03-relatorios").mkdir()
    (p / "caso.json").write_text(json.dumps({"status": status}), encoding="utf-8")
    if pdf:
        (p / "00-originais" / "autos.pdf").write_bytes(b"x")
    if docx:
        (p / "03-relatorios" / "RELATORIO-v01.docx").write_bytes(b"x")


with tempfile.TemporaryDirectory() as tmp:
    ordens, ws = Path(tmp, "ordens"), Path(tmp, "ws")
    for nome in ("OS 9101-26 - sem pdf na pasta", "OS 9102-26 - sem pdf e sem caso"):
        (ordens / nome).mkdir(parents=True)
    caso(ws, "OS-9101-2026", "extraido", pdf=True)            # PDF só no caso; pasta da O.S. vazia
    caso(ws, "OS-9103-2026", "extraido", pdf=True)            # O.S. que só existe como caso
    caso(ws, "OS-9104-2026", "minuta", pdf=True, docx=True)   # só caso, já com relatório
    caso(ws, "OS-9105-2026", "recebido")                      # só caso, sem PDF
    for nome in ("OS-OS-TESTE", "_MODELO-CASO", "RECEBIDO-abc123", "OS-9106"):
        caso(ws, nome, "extraido", pdf=True)                  # nomes fora do padrão OS-<nº>-<ano>: ignorados
    env = {"CPJ_PASTA_OS": str(ordens), "CPJ_WORKSPACES": str(ws)}

    c, s = roda("listar", "--json", env=env)
    itens = json.loads(s) if c == 0 else {}
    ok(c == 0 and set(itens) == {"9101", "9102", "9103", "9104", "9105"}, "inventário = pastas de O.S. + casos OS-<nº>-<ano>")
    ok(len(itens.get("9101", {}).get("pdfs", [])) == 1 and "00-originais" in itens["9101"]["pdfs"][0],
       "PDF em 00-originais conta como PDF da O.S.")
    ok(itens.get("9102", {}).get("pdfs") == [], "O.S. sem PDF na pasta e sem caso continua sem PDF")
    ok(itens.get("9103", {}).get("situacao") == "livre" and itens["9103"]["pastas"] == [], "O.S. só em casos aparece livre")
    ok(itens.get("9104", {}).get("situacao") == "com_relatorio", "caso em minuta com DOCX conta como relatório")

    c, s = roda("proxima", "--agente", "A", env=env)
    ok(c == 0 and "9101" in s, "proxima oferece O.S. cujo PDF está só no caso")
    c, s = roda("proxima", "--agente", "B", env=env)
    ok(c == 0 and "9103" in s, "proxima oferece O.S. que só existe como caso")
    c, s = roda("proxima", "--agente", "C", env=env)
    ok(c != 0 and "Nenhuma O.S. livre" in s, "sem PDF em lugar nenhum (9102, 9105) não é oferecida")
    c, s = roda("liberar", "9103", "--agente", "B", "--motivo", "teste", env=env)
    ok(c == 0, "O.S. sem pasta própria aceita alteração de estado (sem aviso por pasta)")
    c, s = roda("listar", env=env)
    ok(c == 0 and (ordens / "_CONTROLE-OS.md").exists() and "9103/2026" in (ordens / "_CONTROLE-OS.md").read_text(encoding="utf-8"),
       "quadro lista também a O.S. que só existe como caso")

print("\nTUDO OK" if not falhas else f"\n{falhas} FALHA(S)")
sys.exit(1 if falhas else 0)
