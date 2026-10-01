#!/usr/bin/env python3
"""Teste da tarefa S01: squad do produto no executor automático — etapas separadas (blocos em paralelo, caminho do dinheiro,
consolidação, redação, revisão independente, ajuste condicional), conferência da saída de cada etapa, registro, retomada e
cancelamento. Somente agente SIMULADO e workspace temporário com dados fictícios — nenhuma IA real é chamada.

Uso: python -X utf8 plugin/investigacao-cpj/app/testes/teste_squad_claude.py
"""
import json, os, shutil, sys, tempfile, threading, time

AQUI = os.path.dirname(os.path.abspath(__file__))
APP = os.path.normpath(os.path.join(AQUI, ".."))
RAIZ = os.path.normpath(os.path.join(APP, "..", "..", ".."))
WS = tempfile.mkdtemp(prefix="cpj-s01-")
os.environ.update(CPJ_WORKSPACE=WS, CPJ_PLANTAO_SIMULADO="1")
sys.path.insert(0, APP)
import plantao as PL  # noqa: E402

REG = os.path.join(WS, "registro-sim.jsonl")
SIM = os.path.join(WS, "sim.py")
falhas = []


def ok(cond, msg):
    print(("  OK    " if cond else "  FALHA ") + msg)
    if not cond: falhas.append(msg)


# Agente simulado: faz o papel da etapa recebida em CPJ_ETAPA e registra início/fim (para medir paralelismo e ordem).
open(SIM, "w", encoding="utf-8").write(r'''
import json, os, time
ws, caso, etapa = os.environ["CPJ_WORKSPACE"], os.environ["CPJ_CASO"], os.environ["CPJ_ETAPA"]
arg, modo = json.loads(os.environ.get("CPJ_ETAPA_ARG") or "{}"), os.environ.get("CPJ_SIM_MODO", "ok")
c = os.path.join(ws, "casos", caso); an, rel = os.path.join(c, "02-analise"), os.path.join(c, "03-relatorios")
os.makedirs(os.path.join(an, "blocos"), exist_ok=True); os.makedirs(rel, exist_ok=True)
def reg(**k):   # uma escrita por linha, com o arquivo fechado em seguida (sessões paralelas)
    with open(os.path.join(ws, "registro-sim.jsonl"), "a", encoding="utf-8") as f: f.write(json.dumps(k) + "\n")
reg(etapa=etapa, arg=arg, t0=time.time())
time.sleep(float(os.environ.get("CPJ_SIM_ESPERA", "1")))
w = lambda p, t: open(p, "w", encoding="utf-8").write(t)
if etapa == "blocos": w(os.path.join(an, "blocos", "bloco-%02d.md" % arg["n"]), "achados do bloco %s" % arg["n"])
if etapa == "financeiro": w(os.path.join(an, "fluxo-financeiro.md"), "sem dados financeiros nos autos fictícios")
if etapa == "consolidacao" and modo != "falha-consolidacao":
    w(os.path.join(an, "ficha-caso.md"), "ficha"); w(os.path.join(an, "pessoas.csv"), "nome;mae\n")
if etapa == "redacao": w(os.path.join(rel, "minuta-v%02d.md" % arg["proxima"]), "---\ncaso: x\n---\n## RESUMO DOS FATOS\n")
if etapa == "revisao":
    res = "Resultado: 9 sustentadas · 0 parciais · 0 não localizadas · 0 contraditórias" if modo == "revisao-limpa" else \
          "Resultado: 7 sustentadas · 1 parciais · 1 não localizadas · 0 contraditórias"
    w(os.path.join(rel, "revisao-v%02d.md" % arg["versao"]), "# Revisão\n" + res + "\n")
reg(etapa=etapa, arg=arg, t1=time.time())
print(json.dumps({"type": "result", "subtype": "success", "result": "etapa %s feita" % etapa}))
''')
os.environ["CPJ_PLANTAO_SIMULADO_CMD"] = f"exec(open(r'{SIM}', encoding='utf-8').read())"


def novo_caso(id_, docs):
    """docs: {nome_documento: nº de páginas} com transcrição fictícia."""
    for d, n in docs.items():
        p = os.path.join(WS, "casos", id_, "01-extracao", d); os.makedirs(p, exist_ok=True)
        open(os.path.join(p, "transcricao.md"), "w", encoding="utf-8").write(
            "\n".join(f"---\n## Página {i}\n\ntexto fictício {i}\n" for i in range(1, n + 1)))
    os.makedirs(os.path.join(WS, "casos", id_, "03-relatorios"), exist_ok=True)


def registro():
    if not os.path.exists(REG): return []
    out = []
    for l in open(REG, encoding="utf-8"):   # sessões paralelas gravam ao mesmo tempo: ignora linha incompleta
        try: out.append(json.loads(l))
        except ValueError: pass
    return out


def rodar(caso, acao, espera_max=90):
    """Pedido executado pelo laço automático (trabalhar) com o agente simulado."""
    if os.path.exists(REG): os.remove(REG)
    j = pl.enfileirar(caso, acao, "investigador.teste")
    parar = threading.Event()
    th = threading.Thread(target=PL.trabalhar, args=(WS, "Squad-Sim", "simulado"),
                          kwargs={"parar": parar, "aprovado": True, "intervalo": 1}, daemon=True)
    th.start()
    for _ in range(espera_max * 2):
        if pl.pedido(j)["estado"] in ("concluida", "erro", "cancelada"): break
        time.sleep(0.5)
    parar.set(); th.join(30)
    return j


shutil.copytree(os.path.join(RAIZ, "modelos"), os.path.join(WS, "modelos"))   # DOCX gerado no pós-processamento
os.makedirs(os.path.join(WS, "config"), exist_ok=True)
json.dump({"expediente": {"ativo": False}}, open(os.path.join(WS, "config", "plantao.json"), "w", encoding="utf-8"))
pl = PL.Plantao(WS)
try:
    print("S01.1 Plano de etapas")
    novo_caso("OS-1-2026", {"ip": 40})
    novo_caso("OS-2-2026", {"ip-volume1": 150, "ip-volume2": 60})
    nomes = lambda plano: [e["id"] for e in plano]
    ok(nomes(PL.plano_etapas(WS, {"caso": "OS-1-2026", "acao": "analisar"})) == ["financeiro", "consolidacao"],
       "IP pequeno (40 págs.): sem blocos")
    grande = PL.plano_etapas(WS, {"caso": "OS-2-2026", "acao": "completo"})
    ok(nomes(grande) == ["blocos-01", "blocos-02", "blocos-03", "financeiro", "consolidacao", "redacao", "revisao", "ajuste"],
       "IP grande (210 págs. em 2 volumes): 3 blocos + análise + relatório")
    ok([(b["arg"]["doc"], b["arg"]["ini"], b["arg"]["fim"]) for b in grande[:3]] ==
       [("ip-volume1", 1, 90), ("ip-volume1", 91, 150), ("ip-volume2", 1, 60)], "blocos de até 90 páginas por documento")
    ok(nomes(PL.plano_etapas(WS, {"caso": "OS-1-2026", "acao": "revisar"})) == ["revisao"], "revisar = só a revisão")
    txt = PL.prompt_etapa({"id": "ia-x", "caso": "OS-2-2026", "acao": "completo"}, WS, dict(grande[6], arg={"versao": 3}))
    ok("REVISOR INDEPENDENTE" in txt and "Não altere a minuta" in txt and "NÃO são fonte" in txt,
       "prompt da revisão: papel independente, sem alterar a minuta, regra das bases de consulta")
    txt = PL.prompt_etapa({"id": "ia-x", "caso": "OS-2-2026", "acao": "completo"}, WS, dict(grande[5], arg={"proxima": 2}))
    ok("NÃO revise a própria minuta" in txt and "minuta-v02.md" in txt, "prompt da redação proíbe autorrevisão e fixa a versão")

    print("S01.2 Pedido completo em IP grande")
    os.environ["CPJ_SIM_ESPERA"] = "2"
    j = rodar("OS-2-2026", "completo")
    p = pl.pedido(j); r = registro()
    ok(p["estado"] == "concluida", f"pedido concluído ({p['estado']}: {p.get('erro')})")
    ordem = [x["etapa"] for x in r if "t0" in x]
    ok(ordem[3:] == ["financeiro", "consolidacao", "redacao", "revisao", "ajuste"] and sorted(ordem[:3]) == ["blocos"] * 3,
       f"cada etapa numa sessão própria, na ordem da squad ({ordem})")
    t_blocos = [x for x in r if x["etapa"] == "blocos"]
    ini, fim = max(x["t0"] for x in t_blocos if "t0" in x), min(x["t1"] for x in t_blocos if "t1" in x)
    ok(ini < fim, "os 3 blocos rodaram em paralelo (sessões simultâneas)")
    et = pl.etapas(j)
    ok([e["estado"] for e in et] == ["concluida"] * 8, "todas as etapas registradas como concluídas (ajuste feito: revisão com pendências)")
    ok(all(e.get("inicio") and e.get("fim") and e.get("log") for e in et), "cada etapa registra início, fim e log próprio")
    res = json.loads(p["resultado"])
    ok("Revisão independente" in res["resumo"] and "3 bloco(s)" in res["resumo"], "resumo final por etapa")
    ok(res.get("docx", "").startswith("RELATORIO-OS-2-2026-v01"), f"DOCX gerado pela Central ({res.get('docx')})")
    t = pl.como_tarefa(p)
    ok(len(t["etapas"]) == 8 and t["etapas"][6]["etapa"] == "Revisão independente", "barra da Central recebe as etapas")
    ok(len(os.listdir(os.path.join(WS, "casos", "OS-2-2026", "ia-logs"))) >= 8, "um log por sessão de etapa")

    print("S01.3 Revisão sem pendências dispensa o ajuste; relatório reaproveita a análise existente")
    os.environ.update(CPJ_SIM_ESPERA="0.2", CPJ_SIM_MODO="revisao-limpa")
    j = rodar("OS-2-2026", "relatorio")
    et = pl.etapas(j)
    ok([e["id"] for e in et] == ["redacao", "revisao", "ajuste"], "com ficha-caso.md existente, 'relatório' não refaz a análise")
    ok(pl.pedido(j)["estado"] == "concluida" and et[2]["estado"] == "dispensada", "ajuste dispensado quando a revisão não aponta problema")
    ok(os.path.exists(os.path.join(WS, "casos", "OS-2-2026", "03-relatorios", "minuta-v02.md")), "nova versão da minuta (v02)")

    print("S01.4 Etapa que não entrega a saída falha com motivo claro")
    novo_caso("OS-3-2026", {"ip": 30})
    os.environ.update(CPJ_SIM_MODO="falha-consolidacao")
    j = rodar("OS-3-2026", "analisar")
    p, et = pl.pedido(j), pl.etapas(j)
    ok(p["estado"] == "erro" and "Consolidação da análise" in p["erro"] and "ficha-caso.md" in p["erro"],
       f"erro indica a etapa e o arquivo faltante ({p['erro'][:90]})")
    ok([e["estado"] for e in et] == ["concluida", "erro"], "etapas anteriores ficam registradas como concluídas")

    print("S01.5 Retomada: etapas já concluídas não são refeitas")
    os.environ.update(CPJ_SIM_MODO="ok")
    if os.path.exists(REG): os.remove(REG)
    j = pl.enfileirar("OS-3-2026", "analisar", "investigador.teste")
    pl.registrar("Squad-Retoma", "simulado", "auto", aprovado=True)
    job = pl.reivindicar("Squad-Retoma")
    plano = PL.plano_etapas(WS, job); plano[0].update(estado="concluida", resumo="feito antes da queda")
    pl.gravar_etapas(j, plano)
    PL.executar_pedido(pl, pl.pedido(j), "Squad-Retoma", "simulado")
    ok([x["etapa"] for x in registro() if "t0" in x] == ["consolidacao"], "só a etapa pendente foi executada")
    ok([e["estado"] for e in pl.etapas(j)] == ["concluida", "concluida"], "pedido retomado completo")
    pl.concluir(j, "Squad-Retoma", {"resumo": "ok"})

    print("S01.6 Cancelar durante os blocos em paralelo")
    novo_caso("OS-4-2026", {"ip": 300})
    os.environ.update(CPJ_SIM_ESPERA="30")
    if os.path.exists(REG): os.remove(REG)
    j = pl.enfileirar("OS-4-2026", "analisar", "investigador.teste")
    parar = threading.Event()
    th = threading.Thread(target=PL.trabalhar, args=(WS, "Squad-Sim", "simulado"),
                          kwargs={"parar": parar, "aprovado": True, "intervalo": 1}, daemon=True)
    th.start()
    for _ in range(40):
        if len([x for x in registro() if "t0" in x]) >= 3: break
        time.sleep(0.5)
    t0 = time.time(); pl.cancelar(j)
    for _ in range(40):
        if pl.pedido(j)["estado"] != "executando": break
        time.sleep(0.5)
    ok(pl.pedido(j)["estado"] == "cancelada" and time.time() - t0 < 20, f"cancelado em {time.time() - t0:.1f}s")
    ok(not any("t1" in x for x in registro()), "as sessões dos blocos foram interrompidas (nenhuma terminou)")
    parar.set(); th.join(30)
finally:
    time.sleep(0.5); shutil.rmtree(WS, ignore_errors=True)

print(f"\n{'TUDO OK' if not falhas else str(len(falhas)) + ' FALHA(S)'}")
sys.exit(1 if falhas else 0)
