#!/usr/bin/env python3
"""Teste da tarefa C05: gravações concorrentes no mesmo caso e reserva de versões de minuta.
Workspace temporário, dados fictícios, servidor isolado em porta livre, sem IA.

Uso: python -X utf8 plugin/investigacao-cpj/app/testes/teste_concorrencia_claude.py
"""
import glob, http.cookiejar, json, os, secrets, shutil, socket, string, subprocess, sys, tempfile, threading, time
import urllib.error, urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
APP = os.path.normpath(os.path.join(AQUI, ".."))
RAIZ = os.path.normpath(os.path.join(APP, "..", "..", ".."))
S = os.path.normpath(os.path.join(APP, "..", "skills", "base-cpj", "scripts"))
WS = tempfile.mkdtemp(prefix="cpj-c05-")
os.environ["CPJ_WORKSPACE"] = WS
sys.path.insert(0, S)
env = dict(os.environ, CPJ_WORKSPACE=WS, CPJ_SEM_AGENTE_EMBUTIDO="1", PYTHONIOENCODING="utf-8")
falhas = []


def ok(cond, msg):
    print(("  OK    " if cond else "  FALHA ") + msg)
    if not cond: falhas.append(msg)


shutil.copytree(os.path.join(RAIZ, "casos", "_MODELO-CASO"), os.path.join(WS, "casos", "_MODELO-CASO"))
import caso as C  # noqa: E402
C.novo("91/2026"); ID = "OS-91-2026"
PASTA = C.caminho(ID)

INCREMENTA = r"""
import os, sys
sys.path.insert(0, {s!r})
import caso as C
for _ in range({n}):
    with C.transacao({id!r}) as c:
        c["contador"] = int(c.get("contador") or 0) + 1
"""
RESERVA = r"""
import os, sys
sys.path.insert(0, {s!r})
import caso as C
for _ in range({n}):
    with C.reservar_arquivo_versao({pasta!r}, "minuta-v") as (nome, p):
        open(p, "w", encoding="utf-8").write("{tag} " + nome)
"""
SEGURA = r"""
import sys, time
sys.path.insert(0, {s!r})
import caso as C
with C.trava({id!r}):
    print("TRAVADO", flush=True); time.sleep(3)
"""

try:
    print("C05.1 Ler-alterar-gravar entre PROCESSOS (6 processos × 15 incrementos)")
    ps = [subprocess.Popen([sys.executable, "-c", INCREMENTA.format(s=S, n=15, id=ID)], env=env) for _ in range(6)]
    for p in ps: p.wait(120)
    c = C.carregar(ID)
    ok(all(p.returncode == 0 for p in ps), "todos os processos terminaram sem erro")
    ok(c["contador"] == 90, f"nenhuma atualização perdida (contador {c.get('contador')} = 90)")
    rev1 = c["revisao"]; ok(rev1 >= 91, f"revisão avança a cada gravação ({rev1})")

    print("C05.2 Entre THREADS do mesmo processo (8 threads × 15)")
    def inc():
        for _ in range(15):
            with C.transacao(ID) as c_: c_["contador"] = int(c_.get("contador") or 0) + 1
    ths = [threading.Thread(target=inc) for _ in range(8)]
    for t in ths: t.start()
    for t in ths: t.join(120)
    ok(C.carregar(ID)["contador"] == 210, f"threads: contador {C.carregar(ID)['contador']} = 210")

    print("C05.3 Cópia antiga não sobrescreve alteração alheia")
    velho = C.carregar(ID)
    C.set_campos(ID, {"observacoes": "alterado por outra pessoa"})
    velho["observacoes"] = "cópia antiga"
    try: C.salvar(velho); ok(False, "salvar cópia antiga → ConflitoRevisao")
    except C.ConflitoRevisao: ok(True, "salvar cópia antiga → ConflitoRevisao")
    ok(C.carregar(ID)["observacoes"] == "alterado por outra pessoa", "alteração alheia preservada")
    atual = C.carregar(ID)["revisao"]
    try:
        with C.transacao(ID, esperada=atual - 1) as c_: c_["observacoes"] = "x"
        ok(False, "transacao com revisão esperada antiga → ConflitoRevisao")
    except C.ConflitoRevisao: ok(True, "transacao com revisão esperada antiga → ConflitoRevisao")
    with C.transacao(ID, esperada=atual) as c_: c_["observacoes"] = "ok"
    ok(C.carregar(ID)["observacoes"] == "ok", "transacao com a revisão certa grava")

    print("C05.4 Trava: reentrância e tempo limite")
    with C.trava(ID):
        with C.trava(ID):
            C.status(ID, "em_analise"); C.registrar_relatorio(ID, "x.md")
    ok(C.carregar(ID)["status"] == "em_analise", "funções do caso podem ser chamadas dentro da trava (reentrante)")
    p = subprocess.Popen([sys.executable, "-c", SEGURA.format(s=S, id=ID)], env=env, stdout=subprocess.PIPE, text=True)
    ok(p.stdout.readline().strip() == "TRAVADO", "outro processo segura a trava")
    t0 = time.monotonic()
    try:
        with C.trava(ID, timeout=0.5): ok(False, "trava ocupada → CasoOcupado")
    except C.CasoOcupado: ok(True, "trava ocupada → CasoOcupado após o tempo limite")
    ok(time.monotonic() - t0 < 2, "espera limitada ao tempo pedido")
    p.wait(10)
    with C.trava(ID, timeout=2): ok(True, "trava liberada quando o outro processo termina")

    print("C05.5 Reserva de versão de minuta (threads + processos)")
    rel = os.path.join(PASTA, "03-relatorios")
    nomes, trava_l = [], threading.Lock()
    def reserva():
        for _ in range(5):
            with C.reservar_arquivo_versao(rel, "minuta-v") as (nome, p_):
                open(p_, "w", encoding="utf-8").write("thread " + nome)
                with trava_l: nomes.append(nome)
    ths = [threading.Thread(target=reserva) for _ in range(4)]
    ps = [subprocess.Popen([sys.executable, "-c", RESERVA.format(s=S, n=5, pasta=rel, tag="proc")], env=env) for _ in range(3)]
    for t in ths: t.start()
    for t in ths: t.join(60)
    for p in ps: p.wait(60)
    ms = sorted(f for f in os.listdir(rel) if f.startswith("minuta-v"))
    ok(len(ms) == 35 and len(nomes) == len(set(nomes)) == 20, f"35 versões distintas, nenhuma sobrescrita ({len(ms)})")
    ok(ms == [f"minuta-v{i:02d}.md" for i in range(1, 36)], "numeração contínua v01…v35")
    ok(all(open(os.path.join(rel, f), encoding="utf-8").read().endswith(f) for f in ms), "cada arquivo tem o conteúdo de quem o reservou")
    try:
        with C.reservar_arquivo_versao(rel, "minuta-v") as (nome, p_): raise RuntimeError("falhou ao escrever")
    except RuntimeError: pass
    ok(not os.path.exists(os.path.join(rel, "minuta-v36.md")), "reserva abandonada por erro não deixa arquivo vazio")
    for f in ms: os.remove(os.path.join(rel, f))
    ok(not glob.glob(os.path.join(PASTA, "*.tmp")), "nenhum temporário deixado na pasta do caso")

    print("C05.6 Central CPJ (servidor isolado)")
    porta = (lambda s: (s.bind(("127.0.0.1", 0)), s.getsockname()[1], s.close())[1])(socket.socket())
    srv = subprocess.Popen([sys.executable, os.path.join(APP, "servidor.py"), "--porta", str(porta), "--sem-navegador", "--somente-local",
                            "--workspace", WS], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    URL = f"http://127.0.0.1:{porta}"
    for _ in range(60):
        try: urllib.request.urlopen(URL + "/api/sessao", timeout=2); break
        except Exception: time.sleep(0.5)
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    def req(m, cam, dados=None):
        r = urllib.request.Request(URL + cam, data=json.dumps(dados).encode() if dados is not None else None,
                                   headers={"X-CPJ": "1", "Content-Type": "application/json"}, method=m)
        try:
            with op.open(r, timeout=60) as resp: return resp.status, json.loads(resp.read() or b"{}")
        except urllib.error.HTTPError as e: return e.code, json.loads(e.read() or b"{}")
    try:
        senha = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12)) + "9z"
        ok(req("POST", "/api/configurar", {"nome": "Admin Ficticio", "login": "adm.c05", "senha": senha})[0] == 200, "admin fictício configurado")
        st, j = req("GET", f"/api/casos/{ID}")
        rev = j["caso"]["revisao"]
        ok(st == 200 and not any(a["caminho"].endswith(".caso.lock") for a in j["arquivos"]), "arquivo de trava não aparece na lista de arquivos")
        C.set_campos(ID, {"observacoes": "gravado pelo indexador/IA enquanto a ficha estava aberta"})
        st, j2 = req("POST", f"/api/casos/{ID}", {"revisao": rev, "requisitante": "EDIÇÃO SOBRE CÓPIA ANTIGA"})
        ok(st == 409 and j2.get("conflito"), "salvar ficha aberta antes de outra gravação → 409")
        ok(C.carregar(ID)["requisitante"] != "EDIÇÃO SOBRE CÓPIA ANTIGA", "nada foi gravado no conflito")
        rev = req("GET", f"/api/casos/{ID}")[1]["caso"]["revisao"]
        st, j3 = req("POST", f"/api/casos/{ID}", {"revisao": rev, "requisitante": "EDIÇÃO VÁLIDA"})
        ok(st == 200 and C.carregar(ID)["requisitante"] == "EDIÇÃO VÁLIDA" and j3.get("revisao") == rev + 1,
           "com a revisão atual grava e devolve a nova revisão")
        st, _ = req("POST", f"/api/casos/{ID}", {"requisitante": "SEM REVISÃO (cliente antigo)"})
        ok(st == 200, "cliente sem 'revisao' continua funcionando (compatível)")

        corpo = lambda n: {"meta": {"natureza": "Estelionato"}, "secoes": {"RESUMO DOS FATOS": f"texto {n}"}, "gerar_docx": False}
        res = []
        ths = [threading.Thread(target=lambda n=n: res.append(req("POST", f"/api/casos/{ID}/minuta", corpo(n)))) for n in range(6)]
        for t in ths: t.start()
        for t in ths: t.join(60)
        arqs = sorted(r[1].get("arquivo") for r in res if r[0] == 200)
        ok(arqs == [f"minuta-v{i:02d}.md" for i in range(1, 7)], f"6 salvamentos simultâneos → 6 versões distintas ({arqs})")
        ok(all(f"versao: {a[8:10]}" in open(os.path.join(PASTA, "03-relatorios", a), encoding="utf-8").read() for a in arqs),
           "cabeçalho 'versao' coincide com o nome do arquivo")
        st, m = req("GET", f"/api/casos/{ID}/minuta")
        ok(m.get("ultima") == "minuta-v06.md", "editor recebe a última versão existente")
        req("POST", f"/api/casos/{ID}/minuta", corpo("outro editor"))
        st, j4 = req("POST", f"/api/casos/{ID}/minuta", corpo("eu") | {"ultima_vista": m["ultima"]})
        ok(st == 409 and j4.get("ultima") == "minuta-v07.md", "salvar sobre editor desatualizado → 409 com a versão nova")
        st, j5 = req("POST", f"/api/casos/{ID}/minuta", corpo("eu") | {"ultima_vista": m["ultima"], "forcar": True})
        ok(st == 200 and j5["arquivo"] == "minuta-v08.md", "'salvar mesmo assim' cria nova versão sem sobrescrever")
    finally:
        srv.terminate()
        try: srv.wait(10)
        except Exception: srv.kill()
finally:
    time.sleep(0.5); shutil.rmtree(WS, ignore_errors=True)

print(f"\n{'TUDO OK' if not falhas else str(len(falhas)) + ' FALHA(S)'}")
sys.exit(1 if falhas else 0)
