#!/usr/bin/env python3
"""Teste da tarefa V01: workspace resolvido sem caminho fixo (dados fictícios, pastas temporárias, porta livre).

1. Central sem --workspace e sem CPJ_WORKSPACE numa cópia temporária usa a própria pasta (config e casos lá).
2. CPJ_WORKSPACE explícito tem precedência (scripts e Central).
3. Script fora de um workspace falha com mensagem clara e não cria pastas.
4. Nada é criado nem alterado em C:\\CPJ - TRABALHO.

Uso: python -X utf8 -W ignore::ResourceWarning plugin/investigacao-cpj/app/testes/teste_workspace_v01.py
"""
import http.cookiejar, json, os, secrets, shutil, socket, string, subprocess, sys, tempfile, time
import urllib.error, urllib.parse, urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
APP = os.path.normpath(os.path.join(AQUI, ".."))
PLUGIN = os.path.dirname(APP)
RAIZ = os.path.dirname(os.path.dirname(PLUGIN))
FANTASMA = r"C:\CPJ - TRABALHO"
MSG = "Workspace CPJ não encontrado"
falhas = []


def ok(cond, msg):
    print(("  OK    " if cond else "  FALHA ") + msg)
    if not cond: falhas.append(msg)


def retrato(pasta):
    """(caminho relativo, tamanho, mtime) de tudo sob a pasta; None se não existir."""
    if not os.path.exists(pasta): return None
    r = set()
    for raiz, dirs, arqs in os.walk(pasta):
        for n in dirs + arqs:
            p = os.path.join(raiz, n); st = os.stat(p)
            r.add((os.path.relpath(p, pasta), st.st_size if n in arqs else -1, st.st_mtime_ns))
    return r


def env_limpo(**extra):
    e = {k: v for k, v in os.environ.items() if k not in ("CPJ_WORKSPACE", "CPJ_WORKSPACE_DADOS")}
    e.update(PYTHONIOENCODING="utf-8", CPJ_SEM_AGENTE_EMBUTIDO="1", PYTHONWARNINGS="ignore")
    e.update(extra)
    return e


def montar_ws(destino):
    """Workspace fictício mínimo: plugin\\, modelos\\, casos\\_MODELO-CASO (modelo vazio) e config\\ vazio."""
    ign = shutil.ignore_patterns("__pycache__", "*.pyc", "testes")
    shutil.copytree(os.path.join(RAIZ, "plugin"), os.path.join(destino, "plugin"), ignore=ign)
    shutil.copytree(os.path.join(RAIZ, "modelos"), os.path.join(destino, "modelos"))
    shutil.copytree(os.path.join(RAIZ, "casos", "_MODELO-CASO"), os.path.join(destino, "casos", "_MODELO-CASO"))
    os.makedirs(os.path.join(destino, "config"))
    return destino


class Cli:
    def __init__(self, url):
        self.url = url
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def req(self, metodo, caminho, json_=None, form=None):
        h = {"X-CPJ": "1"}; corpo = None
        if json_ is not None: corpo = json.dumps(json_).encode(); h["Content-Type"] = "application/json"
        if form is not None: corpo = urllib.parse.urlencode(form).encode(); h["Content-Type"] = "application/x-www-form-urlencoded"
        r = urllib.request.Request(self.url + caminho, data=corpo, headers=h, method=metodo)
        try:
            with self.op.open(r, timeout=60) as resp:
                b = resp.read(); return resp.status, json.loads(b or b"{}")
        except urllib.error.HTTPError as e:
            b = e.read()
            try: return e.code, json.loads(b or b"{}")
            except ValueError: return e.code, {}


def subir_central(ws, env, log, cwd):
    s = socket.socket(); s.bind(("127.0.0.1", 0)); porta = s.getsockname()[1]; s.close()
    srv = subprocess.Popen([sys.executable, os.path.join(ws, "plugin", "investigacao-cpj", "app", "servidor.py"),
                            "--porta", str(porta), "--sem-navegador", "--somente-local"],
                           env=env, cwd=cwd, stdout=log, stderr=subprocess.STDOUT)
    url = f"http://127.0.0.1:{porta}"
    for _ in range(80):
        if srv.poll() is not None: break
        try: urllib.request.urlopen(url + "/api/sessao", timeout=2); break
        except Exception: time.sleep(0.5)
    return srv, url


def parar(srv):
    srv.terminate()
    try: srv.wait(10)
    except Exception: srv.kill()


antes_fantasma = retrato(FANTASMA)
TMP = tempfile.mkdtemp(prefix="cpj-v01-")
WS_A = montar_ws(os.path.join(TMP, "ws A ficticio"))
WS_B = os.path.join(TMP, "ws B ficticio"); os.makedirs(os.path.join(WS_B, "config"))
shutil.copytree(os.path.join(WS_A, "casos", "_MODELO-CASO"), os.path.join(WS_B, "casos", "_MODELO-CASO"))
NEUTRA = os.path.join(TMP, "cwd neutra"); os.makedirs(NEUTRA)          # cwd sem casos\: força a subida por __file__
SCR_A = os.path.join(WS_A, "plugin", "investigacao-cpj", "skills", "base-cpj", "scripts")
DOCX_A = os.path.join(WS_A, "plugin", "investigacao-cpj", "skills", "relatorio-ip-fraude", "scripts", "gerar_docx.py")
APP_A = os.path.join(WS_A, "plugin", "investigacao-cpj", "app")
srvs = []

try:
    print("V01.1 Central sem --workspace e sem CPJ_WORKSPACE usa a própria pasta")
    log_a = open(os.path.join(TMP, "central-a.log"), "w+", encoding="utf-8")
    srv, url = subir_central(WS_A, env_limpo(), log_a, NEUTRA); srvs.append(srv)
    ok(srv.poll() is None, "Central subiu")
    adm = Cli(url)
    st, _ = adm.req("GET", "/api/fila")
    ok(st in (200, 401, 403), f"/api/fila responde (sem sessão: {st})")
    senha = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12)) + "7k"
    st, _ = adm.req("POST", "/api/configurar", {"nome": "Admin Ficticio", "login": "adm.v01", "senha": senha})
    ok(st == 200, "administrador fictício configurado")
    st, j = adm.req("GET", "/api/fila")
    ok(st == 200, "/api/fila responde 200 com sessão")
    st, j = adm.req("POST", "/api/os", form={"os": "901/2026", "somente_cadastro": "1", "natureza": "Estelionato"})
    ok(st == 200, f"cadastro de O.S. fictícia ({st})")
    ok(os.path.isfile(os.path.join(WS_A, "casos", "OS-901-2026", "caso.json")), "O.S. gravada em <temp>\\casos")
    cfg = set(os.listdir(os.path.join(WS_A, "config")))
    ok({"segredo.key", "auditoria.log"} <= cfg, f"config criada em <temp>\\config ({sorted(cfg)})")
    log_a.flush(); log_a.seek(0); saida = log_a.read()
    ok(f"(workspace: {WS_A})" in saida, "Central informa o workspace temporário (normalizado, sem '\\.' no fim)")
    parar(srv)

    print("V01.2 CPJ_WORKSPACE explícito tem precedência")
    cod = "import caso, consulta, indexar, rag, referencias; print(caso.WS); " \
          "assert caso.WS == consulta.WS == indexar.WS == rag.WS == referencias.WS"  # gerar_painel lê a produção ao importar
    r = subprocess.run([sys.executable, "-c", cod], cwd=SCR_A, env=env_limpo(), capture_output=True, text=True, encoding="utf-8")
    ok(r.returncode == 0 and r.stdout.strip().splitlines()[-1:] == [WS_A], f"sem variável: scripts sobem de __file__ até o workspace ({(r.stdout.strip().splitlines() or [r.stderr.strip()[-200:]])[-1]})")
    r = subprocess.run([sys.executable, "-c", cod], cwd=SCR_A, env=env_limpo(CPJ_WORKSPACE=WS_B), capture_output=True, text=True, encoding="utf-8")
    ok(r.returncode == 0 and r.stdout.strip().splitlines()[-1:] == [WS_B], "com CPJ_WORKSPACE: scripts usam a variável")
    r = subprocess.run([sys.executable, os.path.join(SCR_A, "caso.py"), "novo", "--os", "902/2026"], cwd=NEUTRA,
                       env=env_limpo(CPJ_WORKSPACE=WS_B), capture_output=True, text=True, encoding="utf-8")
    ok(os.path.isfile(os.path.join(WS_B, "casos", "OS-902-2026", "caso.json"))
       and not os.path.exists(os.path.join(WS_A, "casos", "OS-902-2026")), "caso.py novo grava no workspace da variável")
    r = subprocess.run([sys.executable, "-c", "import metricas, dados_os; print(metricas.ws_padrao()); print(dados_os.ws_padrao())"],
                       cwd=NEUTRA, env=env_limpo(PYTHONPATH=os.pathsep.join([SCR_A, APP_A])), capture_output=True, text=True, encoding="utf-8")
    ok(r.stdout.strip().splitlines() == [WS_A, WS_A], "metricas.py e dados_os.py resolvem o workspace da cópia")
    with open(os.path.join(WS_A, "config", "ia-local-os.json"), "w", encoding="utf-8") as f: json.dump({"modelo": "modelo-ficticio"}, f)
    r = subprocess.run([sys.executable, "-c", "import dados_os; print(dados_os.modelo_local())"], cwd=NEUTRA,
                       env=env_limpo(PYTHONPATH=APP_A), capture_output=True, text=True, encoding="utf-8")
    ok(r.stdout.strip() == "modelo-ficticio", "dados_os lê config\\ia-local-os.json do workspace da cópia")
    minuta = os.path.join(TMP, "minuta-ficticia.md")
    with open(minuta, "w", encoding="utf-8") as f:
        f.write("---\nordem_servico: 901/2026\nnatureza: Estelionato (art. 171, CP)\n---\n## RESUMO DOS FATOS\nTexto fictício.\n"
                "## DILIGÊNCIAS REALIZADAS\nTexto fictício.\n## CONCLUSÃO\nTexto fictício.\n")
    saida_docx = os.path.join(TMP, "relatorio-ficticio.docx")
    r = subprocess.run([sys.executable, DOCX_A, minuta, "--saida", saida_docx], cwd=NEUTRA, env=env_limpo(),
                       capture_output=True, text=True, encoding="utf-8")
    ok(r.returncode == 0 and os.path.isfile(saida_docx), f"gerar_docx.py acha o modelo em <workspace>\\modelos sem variável ({r.stderr.strip()[-200:]})")
    log_b = open(os.path.join(TMP, "central-b.log"), "w+", encoding="utf-8")
    srv, url = subir_central(WS_A, env_limpo(CPJ_WORKSPACE=WS_B), log_b, NEUTRA); srvs.append(srv)
    st, _ = Cli(url).req("GET", "/api/sessao")
    log_b.flush(); log_b.seek(0)
    ok(st == 200 and f"(workspace: {WS_B})" in log_b.read(), "Central com CPJ_WORKSPACE usa a variável, não a própria pasta")
    ok("segredo.key" in os.listdir(os.path.join(WS_B, "config")), "config da Central criada no workspace da variável")
    parar(srv)

    print("V01.3 Fora de um workspace: erro claro, sem criar pastas")
    FORA = os.path.join(TMP, "fora do workspace")
    shutil.copytree(os.path.join(WS_A, "plugin", "investigacao-cpj", "skills", "base-cpj", "scripts"), os.path.join(FORA, "base"),
                    ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy(DOCX_A, os.path.join(FORA, "gerar_docx.py"))
    antes_fora = retrato(FORA)
    chamadas = {
        "caso.py": ["base/caso.py", "listar"], "consulta.py": ["base/consulta.py", "listar"],
        "gerar_painel.py": ["base/gerar_painel.py"], "indexar.py": ["base/indexar.py"], "metricas.py": ["base/metricas.py", "--json"],
        "progresso.py": ["base/progresso.py", "OS-1-2026"], "rag.py": ["base/rag.py", "buscar", "x"],
        "referencias.py": ["base/referencias.py", "listar"], "gerar_docx.py": ["gerar_docx.py", minuta, "--saida", os.path.join(FORA, "x.docx")],
    }
    for nome, args in chamadas.items():
        r = subprocess.run([sys.executable] + args, cwd=FORA, env=env_limpo(), capture_output=True, text=True, encoding="utf-8")
        ok(r.returncode != 0 and MSG in r.stderr, f"{nome}: sai com erro claro ({r.stderr.strip().splitlines()[-1][:90] if r.stderr.strip() else r.returncode})")
    ok(retrato(FORA) == antes_fora, "nenhuma pasta/arquivo criado fora do workspace pelos scripts")
    shutil.copy(os.path.join(APP_A, "dados_os.py"), os.path.join(FORA, "dados_os.py"))
    antes_fora = retrato(FORA)
    r = subprocess.run([sys.executable, "-c", "import dados_os; print(repr(dados_os.modelo_local()))"], cwd=FORA, env=env_limpo(),
                       capture_output=True, text=True, encoding="utf-8")
    ok(r.returncode == 0 and r.stdout.strip() == "''", "dados_os.modelo_local() fora do workspace = IA local não configurada (sem derrubar)")
    depois = {e for e in retrato(FORA) if "__pycache__" not in e[0]}
    ok(depois == {e for e in antes_fora if "__pycache__" not in e[0]}, "dados_os não cria pastas fora do workspace")
finally:
    for s in srvs:
        if s.poll() is None: parar(s)
    for nome in ("log_a", "log_b"):
        if nome in globals(): globals()[nome].close()
    time.sleep(0.5)
    shutil.rmtree(TMP, ignore_errors=True)

print("V01.4 Pasta fantasma C:\\CPJ - TRABALHO intocada")
ok(retrato(FANTASMA) == antes_fantasma,
   "nada criado/alterado em C:\\CPJ - TRABALHO" + (" (pasta inexistente)" if antes_fantasma is None else f" ({len(antes_fantasma)} item(ns), mtimes iguais)"))

print(f"\n{'TUDO OK' if not falhas else str(len(falhas)) + ' FALHA(S)'}")
sys.exit(1 if falhas else 0)
