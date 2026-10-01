#!/usr/bin/env python3
"""Teste da tarefa D02 (painel "Agentes de plantão"). Servidor isolado, porta livre, dados fictícios, sem IA real.

Uso: python -X utf8 plugin/investigacao-cpj/app/testes/teste_painel_plantao_claude.py
"""
import http.cookiejar, json, os, secrets, shutil, socket, string, subprocess, sys, tempfile, time
import urllib.error, urllib.parse, urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
APP = os.path.normpath(os.path.join(AQUI, ".."))
RAIZ = os.path.normpath(os.path.join(APP, "..", "..", ".."))
WS = tempfile.mkdtemp(prefix="cpj-d02-")
sys.path.insert(0, APP); sys.path.insert(0, os.path.join(APP, "..", "skills", "base-cpj", "scripts"))
falhas = []


def ok(cond, msg):
    print(("  OK    " if cond else "  FALHA ") + msg)
    if not cond: falhas.append(msg)


def senha():
    return "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12)) + "7k"


class Cli:
    def __init__(self, url): self.url = url; self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def req(self, metodo, caminho, dados=None, bruto=False):
        h = {"X-CPJ": "1"}; corpo = None
        if dados is not None: corpo = json.dumps(dados).encode(); h["Content-Type"] = "application/json"
        r = urllib.request.Request(self.url + urllib.parse.quote(caminho, safe="/?=&:%-_.~"), data=corpo, headers=h, method=metodo)
        try:
            with self.op.open(r, timeout=60) as resp:
                b = resp.read(); return resp.status, (b.decode("utf-8") if bruto else json.loads(b or b"{}"))
        except urllib.error.HTTPError as e:
            b = e.read()
            try: return e.code, json.loads(b or b"{}")
            except ValueError: return e.code, {}


shutil.copytree(os.path.join(RAIZ, "casos", "_MODELO-CASO"), os.path.join(WS, "casos", "_MODELO-CASO"))
env = dict(os.environ, CPJ_WORKSPACE=WS, CPJ_SEM_AGENTE_EMBUTIDO="1", PYTHONIOENCODING="utf-8")
subprocess.run([sys.executable, os.path.join(APP, "..", "skills", "base-cpj", "scripts", "caso.py"), "novo", "--os", "77/2026"],
               env=env, capture_output=True, check=True)
os.environ["CPJ_WORKSPACE"] = WS
import plantao as PL  # noqa: E402
pl = PL.Plantao(WS)
pl.registrar("Agente-Livre", "codex", "chat", aprovado=True)
pl.registrar("Agente-Escolhido", "claude", "chat", aprovado=True)
pl.registrar("Agente-Novo", "outro", "chat")          # não aprovado

s = socket.socket(); s.bind(("127.0.0.1", 0)); porta = s.getsockname()[1]; s.close()
srv = subprocess.Popen([sys.executable, os.path.join(APP, "servidor.py"), "--porta", str(porta), "--sem-navegador", "--somente-local",
                        "--workspace", WS], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
URL = f"http://127.0.0.1:{porta}"
for _ in range(60):
    try: urllib.request.urlopen(URL + "/api/sessao", timeout=2); break
    except Exception: time.sleep(0.5)

try:
    print("D02.1 Página")
    adm = Cli(URL)
    st, html = adm.req("GET", "/", bruto=True)
    for e in ('id="plantao-agentes"', 'id="ia-agente"', "/api/plantao/agentes", "/aprovacao", "PROMPT-AGENTE-PLANTAO.md"):
        ok(e in html, f"index.html contém {e}")

    print("D02.2 Permissões")
    sa, si, se = senha(), senha(), senha()
    ok(adm.req("POST", "/api/configurar", {"nome": "Admin Ficticio", "login": "adm.d02", "senha": sa})[0] == 200, "admin configurado")
    adm.req("POST", "/api/usuarios", {"login": "inv.d02", "nome": "Investigador Ficticio", "perfil": "investigador", "senha": si, "ativo": True})
    adm.req("POST", "/api/usuarios", {"login": "esc.d02", "nome": "Escrivao Ficticio", "perfil": "escrivao", "senha": se, "ativo": True})
    inv, esc = Cli(URL), Cli(URL)
    inv.req("POST", "/api/entrar", {"login": "inv.d02", "senha": si}); esc.req("POST", "/api/entrar", {"login": "esc.d02", "senha": se})
    st, g = inv.req("GET", "/api/plantao/agentes")
    nomes = {a["nome"]: a for a in g.get("agentes", [])}
    ok(st == 200 and {"Agente-Livre", "Agente-Escolhido", "Agente-Novo"} <= set(nomes), "investigador vê os agentes")
    ok(nomes["Agente-Novo"]["estado"] == "aguardando aprovação" and g["ociosos"] == 2, "situações: 2 ociosos, 1 aguardando aprovação")
    ok(esc.req("GET", "/api/plantao/agentes")[0] == 403, "escrivão (sem IA) não vê o painel de agentes")
    ok(inv.req("POST", "/api/plantao/agentes/Agente-Novo/aprovacao", {"aprovar": True})[0] == 403, "investigador não aprova agentes")
    ok(adm.req("POST", "/api/plantao/agentes/Agente-Novo/aprovacao", {"aprovar": True})[0] == 200, "admin aprova agente")
    ok([a for a in pl.agentes() if a["nome"] == "Agente-Novo"][0]["aprovado"] == 1, "aprovação gravada na fila")
    ok(adm.req("POST", "/api/plantao/agentes/Agente-Novo/aprovacao", {"aprovar": False})[0] == 200, "admin revoga agente")
    ok(adm.req("POST", "/api/plantao/agentes/Inexistente/aprovacao", {"aprovar": True})[0] == 404, "agente inexistente → 404")
    ok(any(e["acao"] == "agente_aprovado" and e["alvo"] == "Agente-Novo" for e in adm.req("GET", "/api/auditoria")[1]), "aprovação auditada")

    print("D02.3 Escolher o agente ao acionar a IA")
    st, j = inv.req("POST", "/api/casos/OS-77-2026/ia", {"acao": "revisar", "agente": "Agente-Novo"})
    ok(st == 400, "agente não aprovado (revogado) é recusado")
    st, j = inv.req("POST", "/api/casos/OS-77-2026/ia", {"acao": "revisar", "agente": "Agente-Escolhido", "observacoes": "teste"})
    ok(st == 200 and j["tarefa"].startswith("ia-"), "pedido direcionado criado")
    ok(pl.pedido(j["tarefa"])["preferido"] == "Agente-Escolhido", "pedido registra o agente escolhido")
    ok(pl.reivindicar("Agente-Livre") is None, "outro agente ocioso não pega o pedido direcionado")
    ok(pl.reivindicar("Agente-Escolhido")["id"] == j["tarefa"], "o agente escolhido pega o pedido")
    st, g = inv.req("GET", "/api/plantao/agentes")
    ok([a for a in g["agentes"] if a["nome"] == "Agente-Escolhido"][0]["estado"] == "ocupado", "painel mostra o agente ocupado")
    t = next(x for x in inv.req("GET", "/api/tarefas")[1] if x["id"] == j["tarefa"])
    ok(t["status"] == "executando" and "Agente-Escolhido" in t["detalhe"], "barra de progresso mostra quem executa")

    print("D02.4 Filtro de situação exata aplicado pelo servidor (pendência de L02/L03)")
    import consulta as Q
    Q.WS, Q.BASES = WS, os.path.join(WS, "consulta")
    Q.importar_texto("Nome: SIT ABERTO\nMandado de prisão em aberto nº 9/2026\n\nNome: SIT CUMPRIDO\nMandado de prisão cumprido em 2019", "Base D02")
    subprocess.run([sys.executable, os.path.join(APP, "..", "skills", "base-cpj", "scripts", "indexar.py")], env=env, capture_output=True)
    st, r = inv.req("GET", "/api/pesquisa/pessoas?texto=sit&mandado_estado=historico")
    ok(st == 200 and [p["nome"] for p in r["pessoas"]] == ["SIT CUMPRIDO"], "mandado_estado=historico filtrado no servidor")
finally:
    srv.terminate()
    try: srv.wait(10)
    except Exception: srv.kill()
    time.sleep(0.5); shutil.rmtree(WS, ignore_errors=True)

print(f"\n{'TUDO OK' if not falhas else str(len(falhas)) + ' FALHA(S)'}")
sys.exit(1 if falhas else 0)
