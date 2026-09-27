#!/usr/bin/env python3
"""Teste da tarefa M01: métricas de qualidade do fluxo e exibição no painel, sem nomes de pessoas.
Workspace temporário, dados fictícios, sem IA.

Uso: python -X utf8 plugin/investigacao-cpj/app/testes/teste_metricas_claude.py
"""
import json, os, re, shutil, subprocess, sys, tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
APP = os.path.normpath(os.path.join(AQUI, ".."))
RAIZ = os.path.normpath(os.path.join(APP, "..", "..", ".."))
S = os.path.join(APP, "..", "skills", "base-cpj", "scripts")
WS = tempfile.mkdtemp(prefix="cpj-m01-")
env = dict(os.environ, CPJ_WORKSPACE=WS, PYTHONIOENCODING="utf-8")
falhas = []


def ok(cond, msg):
    print(("  OK    " if cond else "  FALHA ") + msg)
    if not cond: falhas.append(msg)


def caso(*args): subprocess.run([sys.executable, os.path.join(S, "caso.py"), *args], env=env, capture_output=True, check=True)


def escrever(p, t):
    os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "w", encoding="utf-8").write(t)


try:
    shutil.copytree(os.path.join(RAIZ, "casos", "_MODELO-CASO"), os.path.join(WS, "casos", "_MODELO-CASO"))
    # Caso A: entregue, 3 minutas, duas revisões (conta a primeira)
    caso("novo", "--os", "11/2026", "--recebido", "2026-03-02")
    for st, d in (("extraido", "2026-03-02"), ("em_analise", "2026-03-04"), ("analisado", "2026-03-09"),
                  ("minuta", "2026-03-10"), ("entregue", "2026-03-16")):
        caso("status", "OS-11-2026", st, "--data", d)
    caso("set", "OS-11-2026", "vitimas=VITIMA FICTICIA SIGILOSA", "investigados=INVESTIGADO FICTICIO SIGILOSO")
    r = os.path.join(WS, "casos", "OS-11-2026", "03-relatorios")
    for v in (1, 2, 3): escrever(os.path.join(r, f"minuta-v{v:02d}.md"), "---\ncaso: OS-11-2026\n---\n")
    escrever(os.path.join(r, "revisao-v01.md"), "# Revisão — OS-11-2026 minuta v01\nResultado: 8 sustentadas · 2 parciais · 1 não localizadas · 1 contraditórias\n")
    escrever(os.path.join(r, "revisao-v02.md"), "# Revisão\n**Resultado:** 12 sustentadas · 0 parciais · 0 não localizadas · 0 contraditórias\n")
    # Caso B: em minuta, revisão sem linha de resultado reconhecível; versões registradas no caso.json
    caso("novo", "--os", "12/2026", "--recebido", "2026-03-05")
    caso("status", "OS-12-2026", "em_analise", "--data", "2026-03-06")
    caso("status", "OS-12-2026", "minuta", "--data", "2026-03-12")
    caso("relatorio", "OS-12-2026", "--arquivo", "minuta-v02.md", "--versoes", "2")
    escrever(os.path.join(WS, "casos", "OS-12-2026", "03-relatorios", "revisao-v01.md"), "texto livre sem contagem\n")

    sys.path.insert(0, APP); sys.path.insert(0, S)
    import plantao as PL  # noqa: E402
    pl = PL.Plantao(WS)
    pl.registrar("Agente-Teste", "outro", "chat", aprovado=True)
    j = pl.enfileirar("OS-11-2026", "revisar", "SOLICITANTE FICTICIO")
    pl.reivindicar("Agente-Teste"); pl.concluir(j, "Agente-Teste", {"resumo": "ok"})
    j2 = pl.enfileirar("OS-12-2026", "analisar", "SOLICITANTE FICTICIO")
    pl.reivindicar("Agente-Teste"); pl.falhar(j2, "Agente-Teste", "erro fictício")

    print("M01.1 metricas.calcular")
    import metricas as MQ  # noqa: E402
    m = MQ.calcular(WS)
    A = next(c for c in m["casos"] if c["id"] == "OS-11-2026"); B = next(c for c in m["casos"] if c["id"] == "OS-12-2026")
    ok(A["versoes"] == 3 and A["minutas"] == 3, "versões até o FINAL contadas pelas minutas (3)")
    ok(B["versoes"] == 2, "versões registradas no caso.json têm precedência (2)")
    ok(A["revisao"] == {"sustentada": 8, "parcial": 2, "nao_localizada": 1, "contraditoria": 1}, "primeira revisão lida por classificação")
    ok(B["revisao"] is None, "revisão sem 'Resultado:' reconhecível é ignorada, sem erro")
    ok(A["etapas"] == {"extraido": 0, "em_analise": 2, "analisado": 5, "minuta": 1, "entregue": 6}, "dias por etapa do caso A")
    ok(B["etapas"] == {"em_analise": 1, "minuta": 6} and B["entregue"] is None, "etapa pulada mede desde a anterior registrada")
    ia = {p["acao"]: p for p in m["ia"]}
    ok(ia["revisar"]["estado"] == "concluida" and ia["revisar"]["execucao_min"] is not None, "tarefa de IA concluída com tempo de execução")
    ok(ia["analisar"]["estado"] == "erro" and ia["analisar"]["execucao_min"] is None, "tarefa com erro não conta tempo de execução")
    txt = json.dumps(m, ensure_ascii=False)
    ok("SOLICITANTE" not in txt and "Agente-Teste" not in txt and "SIGILOSA" not in txt and "SIGILOSO" not in txt,
       "métricas não contêm solicitante, agente nem nomes de partes")

    print("M01.2 CLI grava producao\\metricas.json")
    r_ = subprocess.run([sys.executable, os.path.join(S, "metricas.py")], env=env, capture_output=True, text=True)
    ok(r_.returncode == 0 and os.path.isfile(os.path.join(WS, "producao", "metricas.json")), "metricas.py gera producao\\metricas.json")
    ok("Versões até o FINAL" in r_.stdout, "resumo impresso")

    print("M01.3 Painel gerado como a Central faz (pasta de preparo producao\\.painel-*)")
    subprocess.run([sys.executable, os.path.join(S, "indexar.py")], env=env, capture_output=True, check=True)
    stage = os.path.join(WS, "producao", ".painel-teste"); os.makedirs(os.path.join(stage, "producao"))
    shutil.copyfile(os.path.join(WS, "producao", "base.json"), os.path.join(stage, "producao", "base.json"))
    r_ = subprocess.run([sys.executable, os.path.join(S, "gerar_painel.py")], env=dict(env, CPJ_WORKSPACE=stage),
                        capture_output=True, text=True)
    ok(r_.returncode == 0, "gerar_painel.py roda na pasta de preparo")
    html = open(os.path.join(stage, "producao", "painel.html"), encoding="utf-8").read()
    dados = json.loads(re.search(r"const D = (\{.*?\});\n", html, re.S).group(1).replace("<\\/", "</"))
    ok(dados["q"] and len(dados["q"]["casos"]) == 2 and len(dados["q"]["ia"]) == 2, "painel recebe as métricas lendo os casos do workspace real")
    ok(all("id" not in c for c in dados["q"]["casos"]), "casos das métricas vão ao painel sem id")
    ok("SOLICITANTE" not in html and "Agente-Teste" not in html and "SIGILOS" not in html, "painel sem nomes de pessoas nem de agentes")
    for e in ('id="q-kpis"', 'id="c-rev"', 'id="c-etapas"', 'id="tab-ia"', "Versões até o FINAL", "Sustentadas na 1ª revisão"):
        ok(e in html, f"painel contém {e}")

    print("M01.4 Sem casos acessíveis o painel continua funcionando")
    iso = tempfile.mkdtemp(prefix="cpj-m01b-"); os.makedirs(os.path.join(iso, "producao"))
    shutil.copyfile(os.path.join(WS, "producao", "base.json"), os.path.join(iso, "producao", "base.json"))
    r_ = subprocess.run([sys.executable, os.path.join(S, "gerar_painel.py")], env=dict(env, CPJ_WORKSPACE=iso), capture_output=True, text=True)
    h2 = open(os.path.join(iso, "producao", "painel.html"), encoding="utf-8").read()
    ok(r_.returncode == 0 and '"q": null' in h2, "sem casos → q nulo e painel gerado (seção mostra 'dados indisponíveis')")
    shutil.rmtree(iso, ignore_errors=True)
finally:
    shutil.rmtree(WS, ignore_errors=True)

print(f"\n{'TUDO OK' if not falhas else str(len(falhas)) + ' FALHA(S)'}")
sys.exit(1 if falhas else 0)
