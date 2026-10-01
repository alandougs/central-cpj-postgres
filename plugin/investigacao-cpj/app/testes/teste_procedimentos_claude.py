#!/usr/bin/env python3
"""Teste da tarefa L06: procedimentos (skills, comandos, agentes, portatil) coerentes com o código.
Workspace temporário, dados fictícios, sem IA.

Uso: python -X utf8 plugin/investigacao-cpj/app/testes/teste_procedimentos_claude.py
"""
import csv, os, re, shutil, subprocess, sys, tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
APP = os.path.normpath(os.path.join(AQUI, ".."))
PLUGIN = os.path.dirname(APP)
RAIZ = os.path.normpath(os.path.join(PLUGIN, "..", ".."))
S = os.path.join(PLUGIN, "skills", "base-cpj", "scripts")
falhas = []

COLUNAS = "nome;mae;pai;cpf;rg;nascimento;telefones;enderecos;empresas;cnpj;emails;placas;condicao;paginas;documento"


def ok(cond, msg):
    print(("  OK    " if cond else "  FALHA ") + msg)
    if not cond: falhas.append(msg)


def ler(*p): return open(os.path.join(*p), encoding="utf-8").read()


print("L06.1 Formato de pessoas.csv igual em skill, comando, agente de plantão e portátil")
skill_an = ler(PLUGIN, "skills", "analise-ip-fraude", "SKILL.md")
ok(f"`{COLUNAS}`" in skill_an, "skill analise-ip-fraude define o cabeçalho exato")
ok(COLUNAS in ler(PLUGIN, "commands", "analisar-ip.md"), "comando /analisar-ip repete o cabeçalho")
sys.path.insert(0, APP)
import plantao as PL  # noqa: E402
for acao in ("analisar", "completo"):
    ok(COLUNAS in PL.ACOES[acao][1].replace("\n", ""), f"pedido '{acao}' do plantão usa o mesmo cabeçalho")
ok(COLUNAS in ler(RAIZ, "portatil", "02-analisar-ip.md"), "portatil/02 atualizado (rode exportar-portatil.py)")
ok("` | `" in skill_an and "UTF-8 com BOM" in skill_an, "separador de valores ' | ' e UTF-8 com BOM documentados")
cols_ag = re.search(r"3\. Pessoas.*?`(\|[^`]+\|)`", ler(PLUGIN, "agents", "analista-documental.md"))
ok(cols_ag and [c.strip() for c in cols_ag.group(1).strip("|").split("|")] == COLUNAS.split(";")[:-1],
   "agente analista-documental usa as mesmas colunas (menos 'documento')")

print("L06.2 Regra: bases de consulta e referências não são fonte")
for rel in (("skills", "analise-ip-fraude", "SKILL.md"), ("skills", "relatorio-ip-fraude", "SKILL.md"),
            ("agents", "revisor-de-relatorio.md"), ("agents", "analista-documental.md"), ("commands", "buscar.md")):
    t = ler(PLUGIN, *rel)
    ok("consulta\\" in t and ("não são fonte" in t or "nunca o use como fonte" in t or "não é fonte" in t
                               or "como fonte de fato" in t or "não localizada" in t), "regra presente em " + "/".join(rel))
for p in ("02-analisar-ip.md", "04-relatorio-ip.md", "05-revisar-relatorio.md", "08-buscar.md"):
    ok("consulta\\" in ler(RAIZ, "portatil", p), f"regra presente em portatil/{p}")

print("L06.3 Exemplos por autor/peso e progresso")
skill_rel = ler(PLUGIN, "skills", "relatorio-ip-fraude", "SKILL.md")
ok("exemplos <modalidade> --autor" in skill_rel and "peso" in skill_rel, "skill relatorio-ip-fraude usa exemplos --autor e peso")
ok("--autor" in ler(PLUGIN, "commands", "relatorio-ip.md"), "comando /relatorio-ip usa --autor")
ok("referencias.py listar" in ler(PLUGIN, "commands", "calibrar.md"), "/calibrar usa referências por autor/peso")
for t, nome in ((skill_an, "analise-ip-fraude"), (skill_rel, "relatorio-ip-fraude")):
    ok("agente-plantao.py progresso" in t and "progresso.py" in t and "CANCELADO" in t, f"{nome}: progresso (chat e automático)")
ok("--autor" in ler(RAIZ, "portatil", "04-relatorio-ip.md"), "portatil/04 com exemplos por autor")

print("L06.4 Comandos citados existem nos scripts")
env = dict(os.environ, PYTHONIOENCODING="utf-8")
def ajuda(script, *args):
    r = subprocess.run([sys.executable, os.path.join(S, script), *args, "-h"], capture_output=True, text=True, env=env)
    return r.stdout + r.stderr
ok("--autor" in ajuda("rag.py", "exemplos"), "rag.py exemplos --autor")
ok("--mae" in ajuda("rag.py", "pessoas"), "rag.py pessoas --mae")
ok("--nome" in ajuda("consulta.py", "importar"), "consulta.py importar --nome")
h = ajuda("referencias.py", "importar"); ok("--autor" in h and "--peso" in h, "referencias.py importar --autor --peso")
h = ajuda("referencias.py", "atualizar"); ok("--peso" in h, "referencias.py atualizar --peso")
cli = os.path.join(RAIZ, "ferramentas", "agente-plantao.py")
h = subprocess.run([sys.executable, cli, "progresso", "-h"], capture_output=True, text=True, env=env).stdout
ok("--pct" in h and "--etapa" in h and "--agente" in h, "agente-plantao.py progresso --agente --pct --etapa")

print("L06.5 pessoas.csv no formato documentado é indexado e pesquisável")
WS = tempfile.mkdtemp(prefix="cpj-l06-")
try:
    shutil.copytree(os.path.join(RAIZ, "casos", "_MODELO-CASO"), os.path.join(WS, "casos", "_MODELO-CASO"))
    env_ws = dict(env, CPJ_WORKSPACE=WS)
    subprocess.run([sys.executable, os.path.join(S, "caso.py"), "novo", "--os", "61/2026"], env=env_ws, capture_output=True, check=True)
    an = os.path.join(WS, "casos", "OS-61-2026", "02-analise"); os.makedirs(an, exist_ok=True)
    with open(os.path.join(an, "pessoas.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(COLUNAS.split(";"))
        w.writerow(["FULANO FICTICIO DE TAL", "MAE FICTICIA", "", "000.000.001-00", "", "", "(18) 90000-0001 | (18) 90000-0002",
                    "Rua Ficticia, 1 | Av. Inexistente, 2", "", "", "", "", "titular de conta destinatária", "12 | 45", "ip-teste"])
        w.writerow(["FULANO FICTICIO DE TAL", "", "", "", "", "", "(18) 90000-0003", "", "", "", "", "", "testemunha", "80", "ip-teste"])
    r = subprocess.run([sys.executable, os.path.join(S, "indexar.py")], env=env_ws, capture_output=True, text=True)
    ok(r.returncode == 0, "indexar.py aceita o pessoas.csv documentado")
    os.environ["CPJ_WORKSPACE"] = WS
    sys.path.insert(0, S)
    import rag  # noqa: E402
    pes, _ = rag.pesquisa_relacional({"telefone": "900000002"})
    ok(len(pes) == 1 and pes[0]["nome"] == "FULANO FICTICIO DE TAL", "segundo telefone (após ' | ') é pesquisável")
    pes, _ = rag.pesquisa_relacional({"nome": "fulano ficticio"})
    ok(len(pes) == 2, "homônimos em fontes diferentes continuam como dois registros")
    ok(any("pág. 12 | 45" in (p.get("localizador") or "") for p in pes), "localizador traz as páginas documentadas")
finally:
    shutil.rmtree(WS, ignore_errors=True)

print(f"\n{'TUDO OK' if not falhas else str(len(falhas)) + ' FALHA(S)'}")
sys.exit(1 if falhas else 0)
