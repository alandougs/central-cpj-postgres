#!/usr/bin/env python3
"""Teste da tarefa D01 (plantão de agentes). Somente agentes SIMULADOS e workspace temporário — nenhuma IA real é chamada.

Uso: python -X utf8 plugin/investigacao-cpj/app/testes/teste_plantao_claude.py
"""
import json, os, shutil, subprocess, sys, tempfile, threading, time

AQUI = os.path.dirname(os.path.abspath(__file__))
APP = os.path.normpath(os.path.join(AQUI, ".."))
RAIZ = os.path.normpath(os.path.join(APP, "..", "..", ".."))
WS = tempfile.mkdtemp(prefix="cpj-d01-")
os.environ["CPJ_WORKSPACE"] = WS
os.environ["CPJ_PLANTAO_SIMULADO"] = "1"
sys.path.insert(0, APP); sys.path.insert(0, os.path.join(APP, "..", "skills", "base-cpj", "scripts"))
import plantao as PL  # noqa: E402

CLI = os.path.join(RAIZ, "ferramentas", "agente-plantao.py")
falhas = []


def ok(cond, msg):
    print(("  OK    " if cond else "  FALHA ") + msg)
    if not cond: falhas.append(msg)


def cli(*args, timeout=60):
    r = subprocess.run([sys.executable, "-X", "utf8", CLI, *args], capture_output=True, text=True, encoding="utf-8",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"), timeout=timeout)
    return r.returncode, r.stdout + r.stderr


for c in ("OS-1-2026", "OS-2-2026", "OS-3-2026", "OS-4-2026", "OS-5-2026", "OS-6-2026"):
    os.makedirs(os.path.join(WS, "casos", c, "03-relatorios"), exist_ok=True)
# Este teste cobre a fila; o horário de expediente tem teste próprio (teste_expediente_claude.py).
os.makedirs(os.path.join(WS, "config"), exist_ok=True)
json.dump({"expediente": {"ativo": False}}, open(os.path.join(WS, "config", "plantao.json"), "w", encoding="utf-8"))
pl = PL.Plantao(WS)

try:
    print("D01.1 Fila e regras básicas")
    j1 = pl.enfileirar("OS-1-2026", "revisar", "investigador.teste", "foco no Pix")
    ok(pl.pedido(j1)["estado"] == "pendente", "pedido criado como pendente")
    try: pl.enfileirar("OS-1-2026", "analisar", "investigador.teste"); ok(False, "segundo pedido ativo no mesmo caso recusado")
    except ValueError: ok(True, "segundo pedido ativo no mesmo caso recusado")
    try: pl.enfileirar("OS-2-2026", "apagar-tudo", "x"); ok(False, "ação inválida recusada")
    except ValueError: ok(True, "ação inválida recusada")
    ok(PL.provedor_pronto("simulado")[0], "agente simulado pronto somente com CPJ_PLANTAO_SIMULADO=1")

    print("D01.2 Sessão de chat: aprovação, reserva, instruções")
    rc, out = cli("aguardar", "--agente", "Chat-A", "--tipo", "codex", "--minutos", "0.05")
    ok(rc == 2 and "NÃO APROVADO" in out, "agente novo não aprovado não pega pedido")
    ok(pl.pedido(j1)["estado"] == "pendente", "pedido continua na fila")
    rc, out = cli("aprovar", "Chat-A"); ok(rc == 0, "administrador aprova o agente")
    rc, out = cli("aguardar", "--agente", "Chat-A", "--tipo", "codex", "--minutos", "0.5")
    ok(rc == 0 and f"PEDIDO: {j1}" in out, "agente ocioso e aprovado reserva o pedido")
    for trecho in ("Não acesse a internet", "portatil\\05-revisar-relatorio.md", "progresso " + j1, "concluir " + j1,
                   "foco no Pix", "NÃO são fonte de fatos", "CANCELADO"):
        ok(trecho in out, f"instrução contém: {trecho}")
    p = pl.pedido(j1); ok(p["estado"] == "executando" and p["agente"] == "Chat-A", "pedido marcado como executando por Chat-A")

    print("D01.3 Dois agentes nunca pegam o mesmo pedido")
    pl.registrar("Chat-B", "claude", "chat", aprovado=True); pl.registrar("Chat-C", "claude", "chat", aprovado=True)
    j2 = pl.enfileirar("OS-2-2026", "analisar", "investigador.teste"); j3 = pl.enfileirar("OS-3-2026", "relatorio", "investigador.teste")
    ps = [subprocess.Popen([sys.executable, "-X", "utf8", CLI, "aguardar", "--agente", n, "--tipo", "claude", "--minutos", "0.3"],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                           env=dict(os.environ, PYTHONIOENCODING="utf-8")) for n in ("Chat-B", "Chat-C")]
    saidas = [p.communicate(timeout=60)[0] for p in ps]
    pegos = [l.split(": ")[1] for s in saidas for l in s.splitlines() if l.startswith("PEDIDO: ")]
    ok(sorted(pegos) == sorted([j2, j3]), f"cada agente pegou um pedido diferente ({pegos})")
    rc, out = cli("aguardar", "--agente", "Chat-A", "--tipo", "codex", "--minutos", "0.05")
    ok(rc == 1, "agente ocupado não pega outro pedido")

    print("D01.4 Progresso, cancelamento e conclusão pela linha de comando")
    rc, out = cli("progresso", j1, "--agente", "Chat-A", "--pct", "40", "--etapa", "metade conferida")
    ok(rc == 0 and pl.pedido(j1)["progresso"] == 40 and pl.pedido(j1)["etapa"] == "metade conferida", "progresso reflete na fila")
    rc, out = cli("progresso", j1, "--agente", "Chat-B", "--pct", "90")
    ok(rc == 4, "outro agente não pode mexer no pedido alheio")
    dono = {pl.pedido(j2)["agente"]: j2, pl.pedido(j3)["agente"]: j3}
    pl.cancelar(j2)
    rc, out = cli("progresso", j2, "--agente", pl.pedido(j2)["agente"], "--pct", "50")
    ok(rc == 3 and "CANCELADO" in out, "cancelamento pela Central chega ao agente (código 3)")
    rc, out = cli("concluir", j2, "--agente", pl.pedido(j2)["agente"], "--resumo", "não deveria concluir")
    ok(rc == 3 and pl.pedido(j2)["estado"] == "cancelada", "pedido cancelado não é concluído")
    rc, out = cli("concluir", j1, "--agente", "Chat-A", "--resumo", "Revisão feita: 3 ajustes propostos.")
    r = pl.pedido(j1)
    ok(rc == 0 and r["estado"] == "concluida" and "3 ajustes" in json.loads(r["resultado"])["resumo"], "conclusão registrada com resumo")
    ok([a for a in pl.agentes() if a["nome"] == "Chat-A"][0]["estado"] == "ocioso", "agente volta a ficar ocioso")

    print("D01.5 Pedido direcionado a um agente específico")
    j4 = pl.enfileirar("OS-4-2026", "analisar", "investigador.teste", preferido="Chat-A")
    ok(pl.reivindicar(pl.pedido(j3)["agente"]) is None, "agente ocupado não pega; e outros não pegam pedido direcionado")
    pl.registrar("Chat-D", "outro", "chat", aprovado=True)
    ok(pl.reivindicar("Chat-D") is None, "agente ocioso NÃO pega pedido direcionado a outro")
    ok(pl.reivindicar("Chat-A")["id"] == j4, "o agente escolhido pega o pedido direcionado")

    print("D01.6 Agente que para de responder devolve o pedido à fila")
    with pl._c() as c: c.execute("UPDATE agentes SET visto_em='2000-01-01T00:00:00' WHERE nome='Chat-A'")
    ok(pl.reivindicar("Chat-D")["id"] == j4, "pedido abandonado volta à fila e é pego por outro agente ocioso")
    with pl._c() as c: c.execute("UPDATE agentes SET visto_em='2000-01-01T00:00:00' WHERE nome='Chat-D'")
    pl.registrar("Chat-E", "outro", "chat", aprovado=True)
    pl.reivindicar("Chat-E")
    ok(pl.pedido(j4)["estado"] == "erro" and "parou de responder" in pl.pedido(j4)["erro"], "após as tentativas, o pedido falha com motivo claro")

    print("D01.7 Modo automático (executor simulado) e cancelamento em execução")
    os.environ["CPJ_PLANTAO_SIMULADO_CMD"] = (
        "import json,os,time;ws=os.environ['CPJ_WORKSPACE'];"
        "open(os.path.join(ws,'casos','OS-5-2026','ia-progresso.json'),'w').write(json.dumps({'pct':60,'etapa':'metade','ts':''}));"
        "time.sleep(6);print(json.dumps({'type':'result','subtype':'success','result':'resumo simulado'}))")
    parar = threading.Event()
    th = threading.Thread(target=PL.trabalhar, args=(WS, "Auto-Sim", "simulado"), kwargs={"parar": parar, "aprovado": True, "intervalo": 1}, daemon=True)
    th.start()
    j5 = pl.enfileirar("OS-5-2026", "revisar", "investigador.teste")
    visto60 = False
    for _ in range(40):
        p = pl.pedido(j5)
        if p["progresso"] == 60: visto60 = True
        if p["estado"] in ("concluida", "erro"): break
        time.sleep(0.5)
    ok(visto60, "progresso informado pelo agente automático aparece na Central")
    ok(pl.pedido(j5)["estado"] == "concluida" and json.loads(pl.pedido(j5)["resultado"])["resumo"] == "resumo simulado",
       "agente automático concluiu o pedido")
    os.environ["CPJ_PLANTAO_SIMULADO_CMD"] = "import time; time.sleep(60)"
    j6 = pl.enfileirar("OS-6-2026", "revisar", "investigador.teste")
    for _ in range(20):
        if pl.pedido(j6)["estado"] == "executando": break
        time.sleep(0.5)
    t0 = time.time(); pl.cancelar(j6)
    for _ in range(30):
        if pl.pedido(j6)["estado"] != "executando": break
        time.sleep(0.5)
    ok(pl.pedido(j6)["estado"] == "cancelada" and time.time() - t0 < 15, f"cancelamento interrompe o executor ({time.time() - t0:.1f}s)")
    parar.set(); th.join(10)

    print("D01.8 Botões atuais da Central passam pelo plantão (tarefas.py)")
    import tarefas as T
    tr = T.Tarefas(WS, None, None, iniciar_agente=False)
    shutil.rmtree(os.path.join(WS, "config", "plantao.sqlite"), ignore_errors=True)
    tid = tr.enfileirar_ia("OS-1-2026", "relatorio", "investigador.teste", "obs")
    t = tr.obter(tid)
    ok(tid.startswith("ia-") and t["tipo"] == "ia" and t["status"] == "na_fila", "botão cria pedido e a tarefa aparece como 'na fila'")
    ok("aguardando agente de plantão" in t["etapa"], f"etapa explica a espera ({t['etapa']})")
    ok(any(x["id"] == tid for x in tr.listar("investigador.teste")), "pedido aparece na lista de tarefas do solicitante")
    ok(not any(x["id"] == tid for x in tr.listar("outro.usuario")), "e não aparece para outro usuário sem permissão de ver todas")
    ok(tr.cancelar(tid) and tr.obter(tid)["status"] == "cancelada", "cancelar pela Central funciona para pedidos do plantão")
    ok(tr.ACOES is PL.ACOES, "ações de IA vêm de um único lugar (plantao.ACOES)")
finally:
    shutil.rmtree(WS, ignore_errors=True)

print(f"\n{'TUDO OK' if not falhas else str(len(falhas)) + ' FALHA(S)'}")
sys.exit(1 if falhas else 0)
