#!/usr/bin/env python3
"""RV08: gate de entrega confere referencia (regra 13) e delegado_genero (regra 10). Só dados fictícios."""
import os
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(RAIZ, "skills", "relatorio-ip-fraude", "scripts"))
import conferir_minuta as cm  # noqa: E402

falhas = []


def ok(cond, msg):
    print(("OK   " if cond else "FALHA ") + msg)
    if not cond:
        falhas.append(msg)


def minuta(tmp, ref, genero):
    linhas = ["---", "ordem_servico: OS 1/2026", f"referencia: {ref}", "natureza: Estelionato",
              "investigados: Fulano de Tal (fictício)", "vitimas: Beltrano (fictício)", "local: Cidade",
              "data_fatos: 01/01/2026", "local_data: Cidade, 02/01/2026", "delegado: Dr. Ficticio",
              "data_rodape: 02/01/2026"]
    if genero is not None:
        linhas.append(f"delegado_genero: {genero}")
    linhas += ["---", "", "## RESUMO DOS FATOS", "Texto sem dados verificáveis.", "",
               "## DILIGÊNCIAS REALIZADAS", "Nenhuma.", "", "## CONCLUSÃO", "Em tese, há indícios."]
    p = os.path.join(tmp, "minuta-v01.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas) + "\n")
    return p


def codigos(tmp, ref, genero):
    _, achados, _ = cm.conferir(minuta(tmp, ref, genero), [], set())
    return {(a["nivel"], a["codigo"]) for a in achados}


BLOQ = ("BLOQUEIA", "REFERENCIA_INVALIDA")
GEN = ("REVISAR", "GENERO_DELEGADO")

with tempfile.TemporaryDirectory() as tmp:
    ok(BLOQ not in codigos(tmp, "IPe nº 123456/2026 / Processo nº 0001234-56.2026.8.26.0000", "F"),
       "referência correta (IPe + Processo) não bloqueia")
    ok(BLOQ in codigos(tmp, "BO nº 12345/2026 / IPe nº 123456/2026 / Processo nº 0001234-56.2026.8.26.0000", "M"),
       "referência com BO bloqueia")
    ok(BLOQ in codigos(tmp, "Boletim de Ocorrência 12345/2026 / IPe nº 1 / Processo nº 2", "M"),
       "referência com 'Boletim de Ocorrência' bloqueia")
    ok(BLOQ in codigos(tmp, "IP nº 45/2026 / IPe nº 123456/2026 / Processo nº 0001234-56", "M"),
       "referência com IP local bloqueia")
    ok(BLOQ in codigos(tmp, "IPe nº 123456/2026", "M"), "referência sem Processo bloqueia")
    ok(BLOQ in codigos(tmp, "Processo nº 0001234-56.2026.8.26.0000", "M"), "referência sem IPe bloqueia")
    ok(BLOQ in codigos(tmp, "IPe nº / Processo nº", "M"), "IPe/Processo sem número bloqueia")
    ok(GEN in codigos(tmp, "IPe nº 1 / Processo nº 2", None), "delegado_genero ausente: REVISAR")
    ok(GEN in codigos(tmp, "IPe nº 1 / Processo nº 2", "X"), "delegado_genero inválido: REVISAR")
    ok(GEN not in codigos(tmp, "IPe nº 1 / Processo nº 2", "M"), "delegado_genero M aceito")
    ok(GEN not in codigos(tmp, "IPe nº 1 / Processo nº 2", "f"), "delegado_genero f aceito")
    ok(not any(c[0] == "BLOQUEIA" and c[1] != "SEM_EXTRACAO" for c in codigos(tmp, "IPe nº 1 / Processo nº 2", "F")),
       "minuta fictícia válida não tem bloqueios do cabeçalho/seções")
print("TUDO OK" if not falhas else f"{len(falhas)} FALHA(S)")
sys.exit(1 if falhas else 0)
