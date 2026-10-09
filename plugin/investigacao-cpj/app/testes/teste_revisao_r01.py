#!/usr/bin/env python3
"""Revisão de código R01 (09/10/2026): regressões dos defeitos corrigidos.
Workspace temporário, dados fictícios, sem IA real e sem rede.

  R01.1 ID de caso "." / ".." não escapa da pasta casos\\ (leitura de config\\segredo.key e usuarios.json)
  R01.2 "Abrir pasta" não alcança caso vizinho com prefixo igual (OS-1-2026 x OS-1-20260)
  R01.3 GET do caso marca "visto" sem apagar gravação concorrente (lost update)
  R01.4 Definir FINAL duas vezes / escolher o próprio FINAL: sem 500 e sem entrada duplicada em relatorios[]
  R01.5 Fila de OCR sobrevive a exceção de um trabalho
  R01.6 Laço do agente de plantão sobrevive a erro transitório; cancelamento funciona fora do Windows
  R01.7 Entradas inválidas viram 4xx/erro tratado (versao_base, nome de minuta, linha de auditoria truncada)

Uso: python -X utf8 plugin/investigacao-cpj/app/testes/teste_revisao_r01.py
"""
import json, os, shutil, subprocess, sys, tempfile, threading, time

AQUI = os.path.dirname(os.path.abspath(__file__))
APP = os.path.normpath(os.path.join(AQUI, ".."))
RAIZ = os.path.normpath(os.path.join(APP, "..", "..", ".."))
S_BASE = os.path.normpath(os.path.join(APP, "..", "skills", "base-cpj", "scripts"))
WS = tempfile.mkdtemp(prefix="cpj-r01-")
os.environ["CPJ_WORKSPACE"] = WS
os.environ["CPJ_SEM_AGENTE_EMBUTIDO"] = "1"
sys.path.insert(0, APP); sys.path.insert(0, S_BASE)
falhas = []
H = {"X-CPJ": "1"}
SENHA = "Ficticia123"


def ok(cond, msg):
    print(("  OK    " if cond else "  FALHA ") + msg)
    if not cond: falhas.append(msg)


try:
    shutil.copytree(os.path.join(RAIZ, "casos", "_MODELO-CASO"), os.path.join(WS, "casos", "_MODELO-CASO"))
    import servidor  # noqa: E402
    import rotas.comum as comum  # noqa: E402
    C = servidor.C
    servidor.auth.salvar_usuario("admin", "Admin Ficticio", "admin", SENHA)
    servidor.auth.salvar_usuario("inv", "Investigador Ficticio", "investigador", SENHA)
    cli = servidor.app.test_client()
    r = cli.post("/api/entrar", json={"login": "inv", "senha": SENHA}, headers=H)
    ok(r.status_code == 200, "login do investigador fictício")
    C.novo("1/2026", id_="OS-1-2026"); C.novo("1/20260", id_="OS-1-20260")

    print("R01.1 ID de caso com pontos não sai da pasta casos\\")
    for x in ("..", ".", ".oculto"):
        try: C.caminho(x); ok(False, f"caminho({x!r}) rejeitado")
        except ValueError: ok(True, f"caminho({x!r}) rejeitado")
    ok(C.caminho("OS-1-2026").endswith("OS-1-2026"), "ID normal continua aceito")
    for url in ("/arquivo/../config/segredo.key", "/arquivo/%2e%2e/config/segredo.key", "/arquivo/%2E%2E/config/usuarios.json"):
        r = cli.get(url)
        ok(r.status_code in (403, 404) and b"sal" not in r.data and len(r.data) < 200, f"{url} → {r.status_code} (sem conteúdo)")
    r = cli.post("/api/casos/%2e%2e/minuta", json={"secoes": {}}, headers=H)
    ok(r.status_code == 404, f"POST minuta com ID '..' → {r.status_code}")
    ok(not os.path.exists(os.path.join(WS, "03-relatorios")), "nenhuma pasta 03-relatorios criada na raiz do workspace")
    r = cli.get("/arquivo/OS-1-2026/caso.json")
    ok(r.status_code == 200, "download normal de arquivo do caso continua funcionando")

    print("R01.2 Abrir pasta: só dentro do próprio caso")
    r = cli.post("/api/casos/OS-1-2026/abrir", json={"sub": "../OS-1-20260"}, headers=H)
    ok(r.status_code == 404, f"caso vizinho com mesmo prefixo → {r.status_code}")
    r = cli.post("/api/casos/OS-1-2026/abrir", json={"sub": "caso.json"}, headers=H)
    ok(r.status_code == 200, f"arquivo do próprio caso → {r.status_code}")

    print("R01.3 GET do caso não sobrescreve gravação concorrente")
    C.set_campos("OS-1-2026", {"visto": "false"})
    real, chamadas = C.carregar, [0]

    def carregar_com_corrida(id_):
        chamadas[0] += 1
        if chamadas[0] == 1:
            velho = real(id_)
            C.set_campos(id_, {"observacoes": "gravado pela fila durante o GET"})  # outra thread grava aqui
            return velho
        return real(id_)

    C.carregar = carregar_com_corrida
    try:
        r = cli.get("/api/casos/OS-1-2026")
    finally:
        C.carregar = real
    atual = C.carregar("OS-1-2026")
    ok(r.status_code == 200 and atual["visto"] is True, "caso marcado como visto")
    ok(atual.get("observacoes") == "gravado pela fila durante o GET", "gravação concorrente preservada")

    print("R01.4 Definir FINAL é idempotente")
    import docx  # noqa: E402
    rel = os.path.join(C.caminho("OS-1-2026"), "03-relatorios"); os.makedirs(rel, exist_ok=True)
    d = docx.Document(); d.add_paragraph("Relatório fictício."); d.save(os.path.join(rel, "RELATORIO-OS-1-2026-v01.docx"))
    r1 = cli.post("/api/casos/OS-1-2026/final", json={"docx": "RELATORIO-OS-1-2026-v01.docx"}, headers=H)
    r2 = cli.post("/api/casos/OS-1-2026/final", json={"docx": "RELATORIO-OS-1-2026-v01.docx"}, headers=H)
    r3 = cli.post("/api/casos/OS-1-2026/final", json={"docx": "RELATORIO-OS-1-2026-FINAL.docx"}, headers=H)
    ok((r1.status_code, r2.status_code, r3.status_code) == (200, 200, 200), f"FINAL 3x → {r1.status_code}/{r2.status_code}/{r3.status_code}")
    finais = [x for x in C.carregar("OS-1-2026").get("relatorios", []) if x.get("arquivo") == "RELATORIO-OS-1-2026-FINAL.docx"]
    ok(len(finais) == 1, f"uma entrada FINAL em relatorios[] (havia {len(finais)})")
    ok(C.carregar("OS-1-2026")["status"] == "entregue", "caso com baixa")

    print("R01.5 Fila de OCR sobrevive a exceção")
    processados, original = [], comum.processar

    def processar_falho(trab, app_logger=None):
        if trab["doc"] == "quebra": raise RuntimeError("processamento.json ilegível (simulado)")
        processados.append(trab["doc"])

    comum.processar = processar_falho
    try:
        t = threading.Thread(target=comum.trabalhador, daemon=True); t.start()
        comum.fila.put({"caso": "OS-1-2026", "doc": "quebra", "arquivo": "x.pdf"})
        comum.fila.put({"caso": "OS-1-2026", "doc": "segue", "arquivo": "y.pdf"})
        comum.fila.join()
    finally:
        comum.processar = original
    ok(t.is_alive() and processados == ["segue"], "trabalho seguinte processado e thread viva")

    print("R01.6 Plantão: laço resiliente e cancelamento portátil")
    import plantao as PL  # noqa: E402
    p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    PL._matar(p)
    try: p.wait(timeout=10); ok(True, "processo do agente encerrado por _matar()")
    except subprocess.TimeoutExpired: p.kill(); ok(False, "processo do agente encerrado por _matar()")
    parar, voltas = threading.Event(), [0]
    orig_reiv, orig_pronto = PL.Plantao.reivindicar, PL.provedor_pronto

    def reivindicar_instavel(self, nome):
        voltas[0] += 1
        if voltas[0] == 1: raise PL.sqlite3.OperationalError("database is locked (simulado)")
        if voltas[0] >= 2: parar.set()
        return None

    PL.Plantao.reivindicar, PL.provedor_pronto = reivindicar_instavel, (lambda tipo: (True, ""))
    open(os.path.join(WS, "config", "plantao.json"), "w", encoding="utf-8").write(json.dumps({"expediente": {"ativo": False}}))
    try:
        t = threading.Thread(target=PL.trabalhar, args=(WS, "Agente-R01", "simulado"),
                             kwargs={"parar": parar, "aprovado": True, "intervalo": 0.05}, daemon=True)
        t.start(); t.join(timeout=30)
    finally:
        PL.Plantao.reivindicar, PL.provedor_pronto = orig_reiv, orig_pronto
    ok(voltas[0] >= 2 and not t.is_alive(), f"laço continuou após o erro ({voltas[0]} voltas) e parou sob comando")

    print("R01.7 Entradas inválidas")
    r = cli.post("/api/casos/OS-1-20260/minuta", json={"versao_base": [1], "secoes": {"CONCLUSÃO": "x"}, "gerar_docx": False}, headers=H)
    ok(r.status_code == 200, f"versao_base não numérica é ignorada → {r.status_code}")
    r = cli.post("/api/casos/OS-1-20260", json={"revisao": {"x": 1}, "observacoes": "ok"}, headers=H)
    ok(r.status_code == 200, f"revisao não numérica é ignorada → {r.status_code}")
    r = cli.post("/api/casos/OS-1-20260/docx", json={"minuta": "sem-numero.md"}, headers=H)
    ok(r.status_code == 400, f"DOCX de minuta inexistente → {r.status_code}")
    with open(os.path.join(WS, "config", "auditoria.log"), "a", encoding="utf-8") as f: f.write('{"ts": "trunc')
    try: servidor.auth.auditoria(50); ok(True, "auditoria ignora linha truncada")
    except ValueError: ok(False, "auditoria ignora linha truncada")
finally:
    try:
        import gc; gc.collect()
    except Exception:
        pass
    shutil.rmtree(WS, ignore_errors=True)

print("\nTUDO OK" if not falhas else f"\n{len(falhas)} FALHA(S)")
sys.exit(1 if falhas else 0)
