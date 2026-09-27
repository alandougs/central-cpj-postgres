#!/usr/bin/env python3
"""Teste da tarefa D03 (expediente do plantão): agentes só reservam pedidos no horário configurado.
Somente agentes SIMULADOS e workspace temporário — nenhuma IA real é chamada.

Uso: python -X utf8 plugin/investigacao-cpj/app/testes/teste_expediente_claude.py
"""
import datetime as dt, json, os, shutil, subprocess, sys, tempfile, threading, time

AQUI = os.path.dirname(os.path.abspath(__file__))
APP = os.path.normpath(os.path.join(AQUI, ".."))
RAIZ = os.path.normpath(os.path.join(APP, "..", "..", ".."))
WS = tempfile.mkdtemp(prefix="cpj-d03-")
os.environ["CPJ_WORKSPACE"] = WS
os.environ["CPJ_PLANTAO_SIMULADO"] = "1"
sys.path.insert(0, APP)
import plantao as PL  # noqa: E402

CLI = os.path.join(RAIZ, "ferramentas", "agente-plantao.py")
CFG = os.path.join(WS, "config", "plantao.json")
falhas = []


def ok(cond, msg):
    print(("  OK    " if cond else "  FALHA ") + msg)
    if not cond: falhas.append(msg)


def config(**exp):
    os.makedirs(os.path.dirname(CFG), exist_ok=True)
    with open(CFG, "w", encoding="utf-8") as f: json.dump({"expediente": exp}, f)


def cli(*args):
    r = subprocess.run([sys.executable, "-X", "utf8", CLI, *args], capture_output=True, text=True, encoding="utf-8",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"), timeout=60)
    return r.returncode, r.stdout + r.stderr


def fora_de_agora():
    """Configuração cujo expediente NÃO inclui o momento atual (qualquer dia da semana em que o teste rodar)."""
    hoje = dt.date.today().weekday()
    config(dias=[d for d in range(7) if d != hoje], inicio="09:00", fim="18:00")


os.makedirs(os.path.join(WS, "casos", "OS-1-2026", "03-relatorios"), exist_ok=True)
os.makedirs(os.path.join(WS, "casos", "OS-2-2026", "03-relatorios"), exist_ok=True)
try:
    print("D03.1 Regra de horário (padrão seg–sex 9h–18h)")
    seg = dt.datetime(2026, 9, 28)   # segunda-feira
    ok(PL.em_expediente(WS, seg.replace(hour=10)), "segunda 10:00 → dentro")
    ok(not PL.em_expediente(WS, seg.replace(hour=8, minute=59)), "segunda 08:59 → fora")
    ok(not PL.em_expediente(WS, seg.replace(hour=18)), "segunda 18:00 → fora (fim exclusivo)")
    ok(not PL.em_expediente(WS, dt.datetime(2026, 9, 26, 10)), "sábado 10:00 → fora")
    ok(not PL.em_expediente(WS, dt.datetime(2026, 9, 27, 10)), "domingo 10:00 → fora")
    ok(PL.proximo_expediente(WS, dt.datetime(2026, 10, 2, 18, 30)) == dt.datetime(2026, 10, 5, 9), "sexta 18:30 → próxima segunda 09:00")
    ok(PL.proximo_expediente(WS, seg.replace(hour=8)) == seg.replace(hour=9), "segunda 08:00 → mesmo dia 09:00")
    ok(PL.descricao_expediente(WS) == "seg–sex, 09:00–18:00", "descrição legível do padrão")
    config(feriados=["2026-10-12"])
    ok(not PL.em_expediente(WS, dt.datetime(2026, 10, 12, 10)), "feriado configurado → fora")
    ok(PL.proximo_expediente(WS, dt.datetime(2026, 10, 9, 19)) == dt.datetime(2026, 10, 13, 9), "próximo expediente pula o feriado")
    config(ativo=False)
    ok(PL.em_expediente(WS, dt.datetime(2026, 9, 27, 3)), "controle desligado → sempre dentro")
    with open(CFG, "w", encoding="utf-8") as f: f.write("{inválido")
    ok(PL.em_expediente(WS, seg.replace(hour=10)) and not PL.em_expediente(WS, seg.replace(hour=20)), "config inválida → usa o padrão")

    print("D03.2 Sessão de chat (agente-plantao.py)")
    pl = PL.Plantao(WS)
    pl.registrar("Chat-X", "codex", "chat", aprovado=True)
    j = pl.enfileirar("OS-1-2026", "revisar", "investigador.teste")
    fora_de_agora()
    rc, out = cli("aguardar", "--agente", "Chat-X", "--tipo", "codex", "--minutos", "0.1")
    ok(rc == 5 and "FORA DO EXPEDIENTE" in out, "aguardar fora do expediente → código 5, sem esperar")
    ok(pl.pedido(j)["estado"] == "pendente", "pedido continua na fila")
    ok([a for a in pl.agentes() if a["nome"] == "Chat-X"][0]["estado"] == "fora do expediente", "agente aparece 'fora do expediente'")
    ok("fora do expediente" in pl.como_tarefa(pl.pedido(j))["etapa"], "barra da Central explica a espera")
    rc, out = cli("expediente")
    ok(rc == 5 and "retomam" in out, "comando 'expediente' informa fora e quando volta (código 5)")
    rc, out = cli("aguardar", "--agente", "Chat-X", "--tipo", "codex", "--minutos", "0.1", "--forcar")
    ok(rc == 0 and j in out and "FORA DO EXPEDIENTE, a pedido do usuário" in out, "--forcar atende por decisão do usuário")
    pl.falhar(j, "Chat-X", "teste")
    config(ativo=False)
    rc, out = cli("expediente")
    ok(rc == 0 and "DENTRO" in out, "comando 'expediente' informa dentro (código 0)")

    print("D03.3 Agente automático (trabalhar) espera o expediente")
    fora_de_agora()
    j2 = pl.enfileirar("OS-2-2026", "revisar", "investigador.teste")
    parar = threading.Event()
    th = threading.Thread(target=PL.trabalhar, args=(WS, "Auto-X", "simulado"),
                          kwargs={"parar": parar, "aprovado": True, "intervalo": 1}, daemon=True)
    th.start(); time.sleep(3)
    ok(pl.pedido(j2)["estado"] == "pendente", "fora do expediente o automático não reserva")
    ok([a for a in pl.agentes() if a["nome"] == "Auto-X"][0]["estado"] == "fora do expediente", "automático sinaliza 'fora do expediente'")
    parar.set(); th.join(40)
    config(ativo=False)
    parar2 = threading.Event()
    th2 = threading.Thread(target=PL.trabalhar, args=(WS, "Auto-X", "simulado"),
                           kwargs={"parar": parar2, "aprovado": True, "intervalo": 1}, daemon=True)
    th2.start()
    for _ in range(60):
        if pl.pedido(j2)["estado"] in ("concluida", "erro"): break
        time.sleep(0.5)
    ok(pl.pedido(j2)["estado"] == "concluida", "dentro do expediente o automático atende e conclui")
    parar2.set(); th2.join(40)
finally:
    time.sleep(0.5); shutil.rmtree(WS, ignore_errors=True)

print(f"\n{'TUDO OK' if not falhas else str(len(falhas)) + ' FALHA(S)'}")
sys.exit(1 if falhas else 0)
