#!/usr/bin/env python3
"""Teste da tarefa L03 (interface): contrato entre index.html e as rotas que ele consome.
Sobe um servidor isolado (workspace temporário, porta livre), usa só dados fictícios e credenciais geradas na hora.

Uso: python -X utf8 plugin/investigacao-cpj/app/testes/teste_interface_claude.py
"""
import http.cookiejar, json, os, re, secrets, shutil, socket, string, subprocess, sys, tempfile, time
import urllib.error, urllib.parse, urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
APP = os.path.normpath(os.path.join(AQUI, ".."))
RAIZ = os.path.normpath(os.path.join(APP, "..", "..", ".."))   # workspace real: só para copiar o modelo de caso
WS = tempfile.mkdtemp(prefix="cpj-l03-")
falhas = []


def ok(cond, msg):
    print(("  OK    " if cond else "  FALHA ") + msg)
    if not cond: falhas.append(msg)


def senha():
    a = string.ascii_letters + string.digits
    return "".join(secrets.choice(a) for _ in range(12)) + "9z"


class Cli:
    def __init__(self, url):
        self.url = url; self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def req(self, metodo, caminho, dados=None, bruto=False):
        h = {"X-CPJ": "1"}; corpo = None
        if dados is not None: corpo = json.dumps(dados).encode(); h["Content-Type"] = "application/json"
        r = urllib.request.Request(self.url + urllib.parse.quote(caminho, safe="/?=&:%-_.~|"), data=corpo, headers=h, method=metodo)
        try:
            with self.op.open(r, timeout=120) as resp:
                b = resp.read(); return resp.status, (b.decode("utf-8") if bruto else json.loads(b or b"{}"))
        except urllib.error.HTTPError as e:
            b = e.read()
            try: return e.code, json.loads(b or b"{}")
            except ValueError: return e.code, {}

    def esperar(self, tid, limite=120):
        for _ in range(limite * 2):
            t = next((x for x in self.req("GET", "/api/tarefas")[1] if x["id"] == tid), None)
            if t and t["status"] in ("concluida", "erro", "cancelada"): return t
            time.sleep(0.5)


# ---------------------------------------------------------------- ambiente isolado
shutil.copytree(os.path.join(RAIZ, "casos", "_MODELO-CASO"), os.path.join(WS, "casos", "_MODELO-CASO"))
s = socket.socket(); s.bind(("127.0.0.1", 0)); porta = s.getsockname()[1]; s.close()
srv = subprocess.Popen([sys.executable, os.path.join(APP, "servidor.py"), "--porta", str(porta), "--sem-navegador", "--somente-local",
                        "--workspace", WS], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
URL = f"http://127.0.0.1:{porta}"
for _ in range(60):
    try: urllib.request.urlopen(URL + "/api/sessao", timeout=2); break
    except Exception: time.sleep(0.5)

try:
    print("L03.1 Página contém os controles novos")
    adm = Cli(URL)
    st, html = adm.req("GET", "/", bruto=True)
    for elem in ('name="mandado_sel"', 'name="cautelar_sel"', 'name="processo"', 'name="bo"', 'name="placa"', 'id="r-vinc"',
                 'id="bc-texto"', 'id="b-bc-colar"', 'accept=".xlsx,.xls,.xlsm,.csv,.docx,.pdf,.txt"', 'name="temporaria"',
                 'name="cpf"', 'name="email"', 'name="cargo"', 'id="f-conta"', 'id="tela-trocar"', "/api/vinculos?tipo=",
                 "/api/consulta/colar", "/api/minha-conta", "mandado_estado", "antecedentes_itens", "no_id"):
        ok(elem in html, f"index.html contém {elem}")
    ok(html.count("<script>") == 1 and html.count("</script>") == 1, "um único bloco de script")
    ok(not re.search(r"https?://(?!127\.0\.0\.1|localhost|github\.com|learn\.)", re.sub(r"<!--.*?-->", "", html, flags=re.S)),
       "interface sem recursos externos (CDN)")

    print("L03.2 Usuários: CPF, e-mail, cargo e senha temporária (como a interface envia)")
    s_adm = senha()
    st, _ = adm.req("POST", "/api/configurar", {"nome": "Admin Ficticio", "login": "adm.teste", "senha": s_adm,
                                                "cargo": "Investigador de Polícia", "cpf": "529.982.247-00", "email": "adm.teste@exemplo.gov.br"})
    ok(st == 200, "configuração inicial com cargo/CPF/e-mail")
    s_tmp = "Temp" + "1"  # provisória simples, aceita só como temporária
    st, u = adm.req("POST", "/api/usuarios", {"login": "esc.teste", "nome": "Escrivao Ficticio", "perfil": "escrivao", "senha": s_tmp,
                                              "ativo": True, "cargo": "Escrivão de Polícia", "email": "esc.teste@exemplo.gov.br",
                                              "temporaria": True, "cpf": "111.444.777-00"})
    ok(st == 200 and u.get("trocar_senha") and u.get("cpf_mascarado"), "usuário com senha temporária criado; CPF mascarado na resposta")
    st, u2 = adm.req("POST", "/api/usuarios", {"login": "esc.teste", "nome": "Escrivao Ficticio", "perfil": "escrivao", "senha": "",
                                               "ativo": True, "cargo": "Escrivão de Polícia", "email": "esc.teste@exemplo.gov.br", "temporaria": False})
    ok(st == 200 and u2.get("cpf_mascarado") == u.get("cpf_mascarado"), "editar sem CPF (campo em branco) mantém o CPF")
    esc = Cli(URL)
    ok(esc.req("POST", "/api/entrar", {"login": "111.444.777-00", "senha": s_tmp})[0] == 200, "login pelo CPF")
    ok(esc.req("GET", "/api/casos")[0] == 428, "com senha temporária, as rotas respondem 428 (tela de troca)")
    nova = senha()
    ok(esc.req("POST", "/api/minha-senha", {"atual": s_tmp, "nova": nova})[0] == 200, "troca da senha temporária")
    ok(esc.req("GET", "/api/casos")[0] == 200, "após a troca, acesso liberado")
    e2 = Cli(URL)
    ok(e2.req("POST", "/api/entrar", {"login": "esc.teste@exemplo.gov.br", "senha": nova})[0] == 200, "login pelo e-mail institucional")
    ok(e2.req("POST", "/api/entrar", {"login": "Escrivao Ficticio", "senha": nova})[0] == 200, "login pelo nome completo")
    st, c = esc.req("POST", "/api/minha-conta", {"email": "esc.novo@exemplo.gov.br", "cargo": "Escrivão Chefe"})
    ok(st == 200 and c.get("email") == "esc.novo@exemplo.gov.br", "Minha conta: e-mail e cargo atualizados")

    print("L03.3 Texto colado → pesquisa com os filtros da interface → vínculos por registro")
    colado = "\n".join(["Nome: FICTICIO NEGADO", "Mãe: MAE FICTICIA", "CPF: 390.533.447-00", "Telefone: (18) 99777-1111",
                        "Sem mandado de prisão", "",
                        "Nome: FICTICIO ABERTO", "Mãe: MAE FICTICIA", "Mandado de prisão em aberto nº 555/2025",
                        "Processo: 1500123-45.2026.8.26.0482", "Placa: ABC1D23", "",
                        "Nome: FICTICIO CUMPRIDO", "Mandado de prisão cumprido em 2018", "Medida protetiva revogada"])
    st, j = adm.req("POST", "/api/consulta/colar", {"texto": colado, "nome": "Colado L03"})
    t = adm.esperar(j.get("tarefa"))
    ok(t and t["status"] == "concluida", f"importação do texto colado ({t and (t.get('erro') or t['status'])})")
    b = next((x for x in adm.req("GET", "/api/consulta/bases")[1] if x["nome"] == "Colado L03"), {})
    ok(b.get("com_antecedentes", {}).get("mandados", {}).get("negado") == 1, "lista de bases traz o resumo por estado")

    def pesq(params):
        return adm.req("GET", "/api/pesquisa/pessoas?" + urllib.parse.urlencode(params))[1]
    r = pesq({"texto": "ficticio", "mandado": "1"})
    nomes = {p["nome"] for p in r["pessoas"]}
    ok(nomes == {"FICTICIO ABERTO", "FICTICIO CUMPRIDO"}, f"'tem ou teve' exclui o negado ({sorted(nomes)})")
    r = pesq({"texto": "ficticio", "mandado_estado": "confirmado"})
    ps = [p for p in r["pessoas"] if p["mandado_estado"] == "confirmado"]   # a interface também filtra no navegador
    ok([p["nome"] for p in ps] == ["FICTICIO ABERTO"], "estado exato 'em aberto' (com filtro do navegador)")
    ok(all(k in r["pessoas"][0] for k in ("antecedentes_itens", "no_id", "mandado_estado", "texto")), "resultado traz campos usados pela tela")
    r = pesq({"processo": "1500123-45.2026"}); ok([p["nome"] for p in r["pessoas"]] == ["FICTICIO ABERTO"], "filtro por processo")
    r = pesq({"placa": "abc-1d23"}); ok([p["nome"] for p in r["pessoas"]] == ["FICTICIO ABERTO"], "filtro por placa")
    r = pesq({"mae": "mae ficticia"}); ok(len(r["pessoas"]) == 2, "dois registros com a mesma mãe")
    p = next(x for x in r["pessoas"] if x["nome"] == "FICTICIO NEGADO")
    st, g = adm.req("GET", "/api/vinculos?" + urllib.parse.urlencode({"tipo": "PESSOA", "valor": p["no_id"], "niveis": 2}))
    tipos = {n["tipo"] for n in g["nos"]}
    ok(st == 200 and {"CPF", "TELEFONE", "NOME"} <= tipos, f"vínculos do registro: CPF, telefone e nomes ({sorted(tipos)})")
    ok(all(n.get("rotulo") for n in g["nos"]), "nós com rótulo para exibição")
    outro = [n for n in g["nos"] if n["tipo"] == "PESSOA" and n["valor"] != p["no_id"]]
    ok(not any(n["tipo"] == "PLACA" for n in g["nos"]), "vínculo pela mãe (nome) não traz a placa do outro registro")
    ok(len(outro) <= 1, "o outro filho aparece no máximo como candidato pelo nome da mãe")
    ok(esc.req("GET", "/api/vinculos?tipo=CPF&valor=39053344700")[0] == 403, "escrivão sem permissão de pesquisa não vê vínculos")
finally:
    srv.terminate()
    try: srv.wait(10)
    except Exception: srv.kill()
    shutil.rmtree(WS, ignore_errors=True)

print(f"\n{'TUDO OK' if not falhas else str(len(falhas)) + ' FALHA(S)'}")
sys.exit(1 if falhas else 0)
