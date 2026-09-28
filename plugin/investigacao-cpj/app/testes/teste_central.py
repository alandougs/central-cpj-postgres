#!/usr/bin/env python3
"""Teste de ponta a ponta da Central CPJ (API) — use SOMENTE com workspace de teste e dados fictícios.

Uso: python teste_central.py --url http://127.0.0.1:8767 --workspace <pasta-teste>
Requer em <pasta-teste>: config\\credenciais-teste.json ({"admin":{login,senha},"delegado":{...},"escrivao":{...}}),
ip_ficticio.pdf, muralha_ficticio.xlsx, referencia_ficticia.docx.
"""
import argparse, datetime, http.cookiejar, json, os, sys, time, uuid, urllib.error, urllib.parse, urllib.request

ap = argparse.ArgumentParser(); ap.add_argument("--url", required=True); ap.add_argument("--workspace", required=True)
a = ap.parse_args(); URL, W = a.url.rstrip("/"), a.workspace
CRED = json.load(open(os.path.join(W, "config", "credenciais-teste.json")))
falhas = []


def ok(cond, msg):
    print(("  OK   " if cond else "  FALHA ") + msg)
    if not cond: falhas.append(msg)


class Cli:
    def __init__(self):
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def req(self, metodo, caminho, json_=None, arquivos=None, campos=None, csrf=True, bruto=False):
        h, dados = {}, None
        if csrf: h["X-CPJ"] = "1"
        if json_ is not None: dados = json.dumps(json_).encode(); h["Content-Type"] = "application/json"
        if arquivos is not None or campos is not None:
            b = uuid.uuid4().hex; partes = []
            for k, v in (campos or {}).items():
                partes.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
            for k, p in (arquivos or []):
                partes.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"; filename="{os.path.basename(p)}"\r\n'
                              f'Content-Type: application/octet-stream\r\n\r\n'.encode() + open(p, "rb").read() + b"\r\n")
            dados = b"".join(partes) + f"--{b}--\r\n".encode(); h["Content-Type"] = f"multipart/form-data; boundary={b}"
        caminho = urllib.parse.quote(caminho, safe="/?=&:%-_.~")
        r = urllib.request.Request(URL + caminho, data=dados, headers=h, method=metodo)
        try:
            with self.op.open(r, timeout=120) as resp:
                corpo = resp.read(); return resp.status, (corpo if bruto else json.loads(corpo or b"{}"))
        except urllib.error.HTTPError as e:
            corpo = e.read()
            try: return e.code, json.loads(corpo or b"{}")
            except ValueError: return e.code, {}

    def entrar(self, perfil):
        c = CRED[perfil]; return self.req("POST", "/api/entrar", {"login": c["login"], "senha": c["senha"]})[0] == 200

    def esperar(self, tid, limite=180):
        for _ in range(limite * 2):
            t = next((x for x in self.req("GET", "/api/tarefas")[1] if x["id"] == tid), None)
            if t and t["status"] in ("concluida", "erro", "cancelada"): return t
            time.sleep(0.5)
        return None


adm, dlg, esc = Cli(), Cli(), Cli()
print("1. Configuração inicial e usuários")
st, j = adm.req("POST", "/api/configurar", {"nome": "Admin Teste", "login": CRED["admin"]["login"], "senha": CRED["admin"]["senha"]})
ok(st == 200, "admin criado na configuração inicial")
ok(adm.req("POST", "/api/configurar", {"nome": "x", "login": "outro", "senha": "abcdefg12"})[0] == 400, "configuração inicial não pode ser repetida")
for p, perfil in (("delegado", "delegado"), ("escrivao", "escrivao")):
    ok(adm.req("POST", "/api/usuarios", {"login": CRED[p]["login"], "nome": f"{p} teste", "perfil": perfil, "senha": CRED[p]["senha"]})[0] == 200, f"usuário {p} criado")
ok(adm.req("POST", "/api/usuarios", {"login": "fraca", "nome": "x", "perfil": "escrivao", "senha": "123"})[0] == 400, "senha fraca recusada")
ok(adm.req("POST", "/api/usuarios", {"login": "x"}, csrf=False)[0] == 403, "POST sem cabeçalho anti-CSRF bloqueado")

print("2. Delegado cadastra O.S. com prazo vencido e envia o PDF")
ok(dlg.entrar("delegado"), "delegado entrou")
ontem = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
st, j = dlg.req("POST", "/api/os", campos={"os": "901/2026", "bo": "AB0001/2026", "inquerito": "0001/2026", "prazo": ontem,
                                             "requisitante": "Dr. Delegado Teste", "determinacao": "Identificar o titular da chave Pix."},
                arquivos=[("arquivos", os.path.join(W, "ip_ficticio.pdf"))])
ok(st == 200 and j.get("caso") == "OS-901-2026" and j.get("recebidos"), f"O.S. cadastrada ({j})")
ok(dlg.req("POST", "/api/exportar", {"modo": "dados"})[0] == 403, "delegado NÃO pode exportar")
ok(dlg.req("POST", "/api/casos/OS-901-2026/ia", {"acao": "relatorio"})[0] == 403, "delegado NÃO aciona IA")
ok(esc.entrar("escrivao"), "escrivão entrou")
ok(esc.req("GET", "/api/pesquisa/pessoas?nome=fulano")[0] == 403, "escrivão NÃO acessa pesquisa")
ok(esc.req("GET", "/api/casos")[0] == 200, "escrivão vê a lista de O.S.")

print("3. Processamento e pendências")
for _ in range(120):
    f = adm.req("GET", "/api/fila")[1]["trabalhos"] if adm.entrar("admin") or True else []
    t = next((x for x in f if x["caso"] == "OS-901-2026"), None)
    if t and t["status"] in ("concluido", "erro"): break
    time.sleep(1)
ok(t and t["status"] == "concluido", f"PDF processado (status {t and t['status']}, progresso {t and t.get('progresso')})")
p = adm.req("GET", "/api/pendencias")[1]
ok(any(c["id"] == "OS-901-2026" for c in p["vencidos"]), "O.S. aparece em prazos vencidos")
ok(any(c["id"] == "OS-901-2026" for c in p["novas"]), "O.S. aparece como nova para o investigador/admin")
d = adm.req("GET", "/api/casos/OS-901-2026")[1]
ok(d["trabalho"] and any(a["caminho"].endswith("transcricao.md") for a in d["arquivos"]), "admin vê transcrição do caso")
ok(adm.req("GET", "/api/pendencias")[1]["novas"] == [], "ao abrir o caso, deixa de ser 'nova'")
dd = dlg.req("GET", "/api/casos/OS-901-2026")[1]
ok(not dd["trabalho"] and all(a["caminho"].startswith("00-originais/") for a in dd["arquivos"]), "delegado vê só originais e dados de gestão")
arq = next(a["caminho"] for a in d["arquivos"] if a["caminho"].endswith("transcricao.md"))
ok(dlg.req("GET", f"/arquivo/OS-901-2026/{arq}", bruto=True)[0] == 403, "delegado NÃO baixa a transcrição")

print("4. Base de consulta (Muralha fictício) e pesquisa relacional")
st, j = adm.req("POST", "/api/consulta/importar", campos={"nome": "Muralha teste"}, arquivos=[("arquivo", os.path.join(W, "muralha_ficticio.xlsx"))])
t = adm.esperar(j.get("tarefa"))
ok(t and t["status"] == "concluida" and t["resultado"]["registros"] == 2, f"base importada ({t and (t.get('resultado') or t.get('erro'))})")
r = adm.req("GET", "/api/pesquisa/pessoas?mae=beltrana ficticia")[1]
ok(len(r["pessoas"]) == 2, f"pesquisa pela mãe encontra 2 pessoas ({len(r['pessoas'])})")
r = adm.req("GET", "/api/pesquisa/pessoas?telefone=99777-1122")[1]
ok(any("FULANO" in p["nome"] for p in r["pessoas"]), "pesquisa por telefone encontra o titular")
r = adm.req("GET", "/api/pesquisa/pessoas?nome=fulano&mae=beltrana")[1]
ok(len(r["pessoas"]) == 1, "nome + mãe combinados")
r = adm.req("GET", "/api/pesquisa/pessoas?cpf=999.888.777-66")[1]
ok(any(o["caso"] == "OS-901-2026" for o in r["ocorrencias"]), "CPF da base também localizado nos autos do caso (ocorrências)")

print("5. Relatório de referência")
st, j = adm.req("POST", "/api/referencias/importar", campos={"autor": "Colega Teste", "modalidade": "falso-parente", "peso": "5"},
                arquivos=[("arquivo", os.path.join(W, "referencia_ficticia.docx"))])
t = adm.esperar(j.get("tarefa")); ok(t and t["status"] == "concluida", "referência importada")
ok(any(x["autor"] == "Colega Teste" and x["peso"] == 5 for x in adm.req("GET", "/api/referencias")[1]), "referência listada com autor e peso")

print("6. Minuta → DOCX → FINAL → baixa")
m = adm.req("GET", "/api/casos/OS-901-2026/minuta")[1]
ok(m["meta"]["ordem_servico"] == "901/2026", "minuta nova já vem com dados da O.S.")
m["meta"].update(delegado="Dr. Delegado Teste", investigados="FULANO FICTICIO DE TAL", vitimas="MARIA FICTICIA DA SILVA")
sec = {"RESUMO DOS FATOS": "Consta do boletim de ocorrência (fls. 2) que a vítima, em tese, foi induzida a erro.",
       "DILIGÊNCIAS REALIZADAS": "### Caminho do dinheiro\n| Data | Valor | Destino | Fls. |\n|---|---|---|---|\n| 10/03/2026 | R$ 2.500,00 | FULANO FICTICIO | 4 |",
       "CONCLUSÃO": "Foram reunidos elementos indicativos de que o valor foi destinado à conta acima."}
st, j = adm.req("POST", "/api/casos/OS-901-2026/minuta", {"meta": m["meta"], "secoes": sec})
ok(st == 200 and j.get("docx") == "RELATORIO-OS-901-2026-v01.docx", f"minuta salva e DOCX gerado ({j})")
st, j = adm.req("POST", "/api/casos/OS-901-2026/final", {"docx": "RELATORIO-OS-901-2026-v01.docx"})
ok(st == 200, "relatório definido como FINAL")
c = adm.req("GET", "/api/casos/OS-901-2026")[1]["caso"]
ok(c["status"] == "entregue" and c["baixa"]["origem"] == "central", "baixa registrada (origem central)")
fin = [r for r in dlg.req("GET", "/api/casos/OS-901-2026")[1]["relatorios"]]
ok(fin and all(r["tipo"] == "final" for r in fin), "delegado vê somente o relatório FINAL")
ok(dlg.req("GET", "/arquivo/OS-901-2026/03-relatorios/RELATORIO-OS-901-2026-FINAL.docx", bruto=True)[0] == 200, "delegado baixa o FINAL")
ok(adm.req("GET", "/api/pendencias")[1]["entregues_hoje"] >= 1, "produção do dia contabilizada")

print("7. Exportar e importar")
st, j = adm.req("POST", "/api/exportar", {"modo": "dados"}); t = adm.esperar(j["tarefa"])
ok(t and t["status"] == "concluida" and t["resultado"]["casos"] == 1, f"exportação concluída ({t and (t.get('resultado') or t.get('erro'))})")
zp = os.path.join(W, "exportacoes", t["resultado"]["arquivo"])
st, j = adm.req("POST", "/api/importar", arquivos=[("arquivo", zp)]); t = adm.esperar(j["tarefa"])
ok(t and t["status"] == "concluida" and "OS-901-2026" in t["resultado"]["casos_ja_existentes"], f"importação não sobrescreve caso existente ({t and (t.get('resultado') or t.get('erro'))})")
ok(adm.req("GET", "/api/planilha", bruto=True)[0] == 200, "planilha CSV disponível")
ok(adm.req("GET", "/painel", bruto=True)[0] == 200, "painel de estatísticas disponível")

print("8. IA sem login do Claude e segurança de login")
st, j = adm.req("POST", "/api/casos/OS-901-2026/ia", {"acao": "analisar"})
if st == 200:
    t = adm.esperar(j["tarefa"], 60)
    if not t:
        # Sem agente de plantão ativo (fila multiagente/D01): o pedido aguarda em vez de falhar.
        t = next((x for x in adm.req("GET", "/api/tarefas")[1] if x["id"] == j["tarefa"]), None)
        etapa = (t or {}).get("etapa") or ""
        ok(t and t["status"] == "na_fila" and ("aguardando agente de plantão" in etapa or "fora do expediente" in etapa),
           f"tarefa de IA finaliza com status claro ({t and (t.get('erro') or t['status'])})")
    else:
        ok(t["status"] in ("erro", "concluida"), f"tarefa de IA finaliza com status claro ({t.get('erro') or t['status']})")
x = Cli()
for _ in range(5): x.req("POST", "/api/entrar", {"login": CRED["escrivao"]["login"], "senha": "errada123"})
st, j = x.req("POST", "/api/entrar", {"login": CRED["escrivao"]["login"], "senha": CRED["escrivao"]["senha"]})
ok(st == 401 and "tentativas" in j.get("erro", ""), "bloqueio após 5 tentativas erradas")
ok(any(e["acao"] == "os_cadastrada" for e in adm.req("GET", "/api/auditoria")[1]), "auditoria registrou o cadastro da O.S.")

print("9. Perfis editáveis, pasta pessoal e responsáveis")
mp = dlg.req("GET", "/api/minha-pasta")[1]
ok(any(a["caminho"] == "relatorios/RELATORIO-OS-901-2026-FINAL.docx" for a in mp["arquivos"]), "FINAL copiado para a pasta pessoal de quem cadastrou a O.S.")
ok(dlg.req("GET", "/minha-pasta/relatorios/RELATORIO-OS-901-2026-FINAL.docx", bruto=True)[0] == 200, "delegado baixa da própria pasta")
ok(dlg.req("GET", "/minha-pasta/../../config/usuarios.json", bruto=True)[0] in (400, 403, 404), "pasta pessoal não permite sair do diretório")
m = adm.req("GET", "/api/perfis")[1]["matriz"]
ok(dlg.req("GET", "/api/pesquisa/pessoas?nome=fulano")[0] == 200, "delegado pesquisa (permissão padrão)")
m["delegado"] = sorted(set(m["delegado"]) - {"pesquisa"})
ok(adm.req("POST", "/api/perfis", {"matriz": m})[0] == 200, "admin retira 'pesquisa' do perfil delegado")
ok(dlg.req("GET", "/api/pesquisa/pessoas?nome=fulano")[0] == 403, "delegado deixa de pesquisar imediatamente")
ok(dlg.req("POST", "/api/perfis", {"matriz": m})[0] == 403, "delegado NÃO altera perfis")
m["delegado"] = sorted(set(m["delegado"]) | {"pesquisa"}); adm.req("POST", "/api/perfis", {"matriz": m})
ok(dlg.req("GET", "/api/pesquisa/pessoas?nome=fulano")[0] == 200, "permissão devolvida pelo admin")
rs = adm.req("GET", "/api/responsaveis")[1]
ok(any(r["login"] == CRED["admin"]["login"] for r in rs), "lista de responsáveis disponível")
ok(adm.req("POST", "/api/casos/OS-901-2026", {"responsavel": CRED["admin"]["login"]})[0] == 200, "responsável atribuído ao caso")
ok(any(c["id"] == "OS-901-2026" for c in adm.req("GET", "/api/casos?meus=1")[1]), "filtro 'meus casos'")

print(f"\n{'TUDO OK' if not falhas else str(len(falhas)) + ' FALHA(S)'}")
sys.exit(1 if falhas else 0)
