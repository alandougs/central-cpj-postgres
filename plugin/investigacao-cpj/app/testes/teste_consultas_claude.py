#!/usr/bin/env python3
"""Testes das tarefas L01 (estados de mandados/cautelares) e L02 (identidade no grafo de vínculos).
Somente dados fictícios, em workspace temporário. Não usa o servidor nem a suíte teste_central.py.

Uso: python -X utf8 plugin/investigacao-cpj/app/testes/teste_consultas_claude.py
"""
import csv, json, os, shutil, subprocess, sys, tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.normpath(os.path.join(AQUI, "..", "..", "skills", "base-cpj", "scripts"))
WS = tempfile.mkdtemp(prefix="cpj-l01l02-")
os.environ["CPJ_WORKSPACE"] = WS           # precisa valer antes de importar consulta/rag
sys.path.insert(0, SCRIPTS)
import consulta as Q  # noqa: E402
import rag as R       # noqa: E402

falhas = []


def ok(cond, msg):
    print(("  OK    " if cond else "  FALHA ") + msg)
    if not cond: falhas.append(msg)


print("L01.1 Classificação de menções (texto original preservado; estado interpretado)")
casos = {
    "Mandado de prisão: Não": "negado", "Sem mandado de prisão": "negado", "Não há medida cautelar vigente": "negado",
    "Nada consta - mandados de prisão": "negado", "Medida cautelar: nada consta": "negado",
    "Não constam mandados de prisão em aberto": "negado",
    "Mandado de prisão em aberto nº 0001234-11.2025.8.26.0482": "confirmado", "Mandado de prisão não cumprido": "confirmado",
    "Situação mandado: Em aberto": "confirmado", "Medida protetiva vigente (Lei 11.340)": "confirmado",
    "Monitoramento eletrônico em cumprimento": "confirmado", "Réu foragido — mandado de prisão": "confirmado",
    "Mandado de prisão cumprido em 10/02/2020": "historico", "Medidas cautelares revogadas em 2022": "historico",
    "Contramandado de prisão expedido": "historico", "Sem mandado em aberto; mandado anterior cumprido em 2019": "historico",
    "Mandado de prisão nº 123/2024 expedido": "indeterminado", "Mandado de prisão: Sim": "indeterminado",
    "Consta mandado de prisão": "indeterminado",
}
for trecho, esperado in casos.items():
    obtido = Q.estado_antecedente(trecho)
    ok(obtido == esperado, f"{esperado:<13} ← {trecho}" + ("" if obtido == esperado else f"  (obtido: {obtido})"))

print("L01.2 Registro de texto livre: trecho preservado, estado, localizador")
regs = Q.registros_de_texto([
    "Nome: FICTICIO NEGADO DA SILVA", "CPF: 529.982.247-00", "Sem mandado de prisão", "Medida cautelar: Não",
    "", "Nome: FICTICIA CONFIRMADA", "Mandado de prisão em aberto nº 111/2025", "Medida protetiva vigente",
    "", "Nome: FICTICIO HISTORICO", "Mandado de prisão cumprido em 2018", "Medidas cautelares revogadas",
])
por_nome = {r["nome"]: r for r in regs}
n, c, h = por_nome.get("FICTICIO NEGADO DA SILVA", {}), por_nome.get("FICTICIA CONFIRMADA", {}), por_nome.get("FICTICIO HISTORICO", {})
ok(n.get("mandados_estado") == "negado" and n.get("cautelares_estado") == "negado", "registro com negações → estados negados")
ok("Sem mandado de prisão" in (n.get("mandados") or ""), "trecho original da negação preservado")
ok(c.get("mandados_estado") == "confirmado" and c.get("cautelares_estado") == "confirmado", "registro com situação atual → confirmado")
ok(h.get("mandados_estado") == "historico" and h.get("cautelares_estado") == "historico", "registro encerrado → histórico")
ok(all(i.get("localizador") for i in c.get("antecedentes_itens", [])), "cada item de antecedente guarda o localizador")

print("L01.3 Planilha: coluna própria com 'Não'/'Sim'/'Cumprido' mantém o contexto do cabeçalho")
linhas = [["Nome", "CPF", "Mandado de Prisão", "Medida Cautelar"],
          ["PLANILHA NAO", "", "Não", "Não"], ["PLANILHA SIM", "", "Sim", ""], ["PLANILHA CUMPRIDO", "", "Cumprido em 2021", "Revogada"]]
rt, _ = Q.registros_de_tabela("Pessoas", linhas)
pt = {r["nome"]: r for r in rt}
ok(pt["PLANILHA NAO"]["mandados_estado"] == "negado" and pt["PLANILHA NAO"]["cautelares_estado"] == "negado", "'Não' na coluna → negado")
ok(pt["PLANILHA NAO"]["mandados"].startswith("Mandado de Prisão: Não"), "valor guardado com o cabeçalho (fonte legível)")
ok(pt["PLANILHA SIM"]["mandados_estado"] == "indeterminado", "'Sim' sem situação → indeterminado (vigência não presumida)")
ok(pt["PLANILHA CUMPRIDO"]["mandados_estado"] == "historico", "'Cumprido' → histórico")

print("L01.4 Ingestão por texto colado + filtros da pesquisa (negado nunca entra no positivo)")
colado = "\n".join([
    "Nome: COLADO NEGADO", "Mãe: MAE FICTICIA UM", "Sem mandado de prisão", "Sem medida cautelar", "",
    "Nome: COLADO ABERTO", "Mãe: MAE FICTICIA DOIS", "Mandado de prisão em aberto nº 222/2025", "",
    "Nome: COLADO ANTIGO", "Mãe: MAE FICTICIA TRES", "Mandado de prisão cumprido em 2017", "Medida cautelar revogada em 2019",
])
meta = Q.importar_texto(colado, "Colado teste")
ok(meta["registros"] == 3, f"texto colado virou 3 registros ({meta['registros']})")
ok(meta["com_antecedentes"]["mandados"]["negado"] == 1, "resumo da importação conta por estado")

# ---- caso fictício com pessoas.csv (homônimos) e fluxo financeiro (bancos distintos, chave Pix)
caso = os.path.join(WS, "casos", "OS-1-2026")
for d in ("02-analise", "01-extracao/doc"): os.makedirs(os.path.join(caso, d), exist_ok=True)
json.dump({"id": "OS-1-2026", "status": "analisado", "datas": {}, "ip": {}, "financeiro": {}, "resultado": {}, "relatorios": []},
          open(os.path.join(caso, "caso.json"), "w", encoding="utf-8"))
with open(os.path.join(caso, "02-analise", "pessoas.csv"), "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["nome", "mae", "pai", "cpf", "rg", "nascimento", "telefones", "enderecos", "empresas", "cnpj", "emails", "placas",
                "condicao", "paginas", "documento"])
    w.writerow(["JOAO FICTICIO HOMONIMO", "MARIA A", "", "111.444.777-00", "", "", "(18) 99111-2222", "", "", "", "", "", "investigado", "10", "doc"])
    w.writerow(["JOAO FICTICIO HOMONIMO", "MARIA B", "", "529.982.247-00", "", "", "(18) 99333-4444", "", "", "", "", "", "testemunha", "20", "doc"])
with open(os.path.join(caso, "02-analise", "fluxo-financeiro.csv"), "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f, delimiter=";")
    cab = ["seq", "data", "hora", "valor", "meio", "id_transacao", "origem_titular", "origem_banco", "origem_ag_conta", "origem_chave",
           "destino_titular", "destino_banco", "destino_ag_conta", "destino_chave", "camada", "fonte_pag", "fls", "status_conferencia"]
    w.writerow(cab)
    w.writerow(["1", "10/03/2026", "", "1000.00", "Pix", "E1", "VITIMA FICTICIA", "BANCO ALFA", "0001/12345-6", "", "RECEBEDOR UM",
                "BANCO BETA", "0002/99999-1", "", "1", "30", "31", "pendente"])
    w.writerow(["2", "11/03/2026", "", "500.00", "Pix", "E2", "VITIMA FICTICIA", "BANCO ALFA", "0001/12345-6", "", "RECEBEDOR DOIS",
                "BANCO GAMA", "0002/99999-1", "", "1", "32", "", "pendente"])
    w.writerow(["3", "12/03/2026", "", "200.00", "Pix", "E3", "VITIMA FICTICIA", "BANCO ALFA", "0001/12345-6", "", "RECEBEDOR TRES",
                "", "", "recebedor.tres@exemplo.com", "1", "33", "", "pendente"])

r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "indexar.py")], env=dict(os.environ, PYTHONIOENCODING="utf-8"),
                   capture_output=True, text=True, encoding="utf-8")
ok(r.returncode == 0, "indexar.py executou" + ("" if r.returncode == 0 else f": {r.stderr[-400:]}"))

ps, _ = R.pesquisa_relacional({"texto": "colado"}, origem="consulta")
est = {p["nome"]: p for p in ps}
ok(est["COLADO NEGADO"]["mandado_estado"] == "negado", "estado do mandado gravado na base")
ps, _ = R.pesquisa_relacional({"texto": "colado", "mandado": "1"}, origem="consulta")
nomes = {p["nome"] for p in ps}
ok("COLADO NEGADO" not in nomes, "filtro 'com mandado' NÃO retorna quem tem 'Sem mandado de prisão'")
ok({"COLADO ABERTO", "COLADO ANTIGO"} <= nomes, "filtro 'com mandado' retorna atual e histórico (tem ou teve)")
ps, _ = R.pesquisa_relacional({"texto": "colado", "cautelar": "1"}, origem="consulta")
ok({p["nome"] for p in ps} == {"COLADO ANTIGO"}, "filtro 'com cautelar' exclui negado e traz o histórico")
ps, _ = R.pesquisa_relacional({"texto": "colado", "mandado_estado": "confirmado"}, origem="consulta")
ok({p["nome"] for p in ps} == {"COLADO ABERTO"}, "filtro por estado exato (confirmado)")
ok(isinstance(json.loads(ps[0]["antecedentes_itens"]), list) and ps[0]["no_id"].startswith("P:"),
   "resultado traz itens de antecedentes e id do registro")

print("L02.1 Homônimos não se fundem")
hs, _ = R.pesquisa_relacional({"nome": "joao ficticio homonimo"})
ok(len(hs) == 2 and hs[0]["no_id"] != hs[1]["no_id"], "dois registros de mesmo nome → dois nós PESSOA distintos")
um = next(p for p in hs if p["cpf"] == "111.444.777-00")
g = R.vinculos("PESSOA", um["no_id"], 2)
cpfs = {n["valor"] for n in g["nos"] if n["tipo"] == "CPF"}
tels = {n["valor"] for n in g["nos"] if n["tipo"] == "TELEFONE"}
ok(cpfs == {"11144477700"}, f"vínculos do registro 1 trazem só o seu CPF ({cpfs})")
ok("18993334444" not in tels, "telefone do homônimo NÃO aparece como vínculo do registro 1")
ok(any(n["tipo"] == "NOME" for n in g["nos"]), "nome aparece como nó candidato (NOME), não como identidade")
gn = R.vinculos("NOME", "JOAO FICTICIO HOMONIMO", 2)
ok(sum(1 for n in gn["nos"] if n["tipo"] == "PESSOA") == 2, "a partir do nome: os 2 registros aparecem como candidatos")
rel_nome = [a["relacao"] for a in gn["arestas"] if "NOME" in (a["a_tipo"], a["b_tipo"])]
ok(rel_nome and all("conferir" in x for x in rel_nome), "ligação por nome sempre marcada 'conferir'")
compat = R.vinculos("PESSOA", "JOAO FICTICIO HOMONIMO", 1)
ok(sum(1 for n in compat["nos"] if n["tipo"] == "PESSOA") == 2, "compatibilidade: tipo PESSOA com nome vira busca por NOME")

print("L02.2 Mesmo CPF liga registros de fontes diferentes")
Q.importar_texto("Nome: J. FICTICIO HOMONIMO\nCPF: 111.444.777-00\nTelefone: (18) 99555-6666", "Base CPF")
subprocess.run([sys.executable, os.path.join(SCRIPTS, "indexar.py")], env=dict(os.environ, PYTHONIOENCODING="utf-8"), capture_output=True)
g = R.vinculos("CPF", "111.444.777-00", 2)
ok(sum(1 for n in g["nos"] if n["tipo"] == "PESSOA") == 2, "CPF idêntico conecta os 2 registros (autos + consulta)")
ok(any(n["tipo"] == "TELEFONE" and n["valor"] == "18995556666" for n in g["nos"]), "e traz o telefone da outra fonte")

print("L02.3 Contas com banco; chave Pix mantém o tipo; fontes nos vínculos")
g = R.vinculos("CONTA", "0002/99999-1", 1)
contas = {n["valor"] for n in g["nos"] if n["tipo"] == "CONTA"}
ok("banco beta|0002999991" in contas and "banco gama|0002999991" in contas, f"mesmos dígitos em bancos distintos = 2 contas ({contas})")
g = R.vinculos("CONTA", "banco beta|0002999991", 1)
ok("banco gama|0002999991" not in {n["valor"] for n in g["nos"]}, "conta do Banco Beta não se liga à do Banco Gama")
g = R.vinculos("CHAVE_PIX", "recebedor.tres@exemplo.com", 1)
ok(any(n["tipo"] == "CHAVE_PIX" for n in g["nos"]) and not any(n["tipo"] == "CONTA" and "@" in n["valor"] for n in g["nos"]),
   "chave Pix sem conta permanece CHAVE_PIX")
ok(all("pág." in (a["localizador"] or "") for a in g["arestas"]), "vínculos do fluxo guardam documento e página")
ok(any(n.get("rotulo", "").startswith("recebedor") for n in g["nos"]), "nós trazem rótulo legível")
ents = R.entidade("0002/99999-1")
ok(len({e["valor"] for e in ents}) == 2, "busca de conta sem banco lista as duas contas (bancos distintos)")

shutil.rmtree(WS, ignore_errors=True)
print(f"\n{'TUDO OK' if not falhas else str(len(falhas)) + ' FALHA(S)'}")
sys.exit(1 if falhas else 0)
