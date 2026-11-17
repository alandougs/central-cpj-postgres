#!/usr/bin/env python3
"""Gera portatil\\*.md: um arquivo AUTOCONTIDO por tarefa, a partir do plugin investigacao-cpj,
para uso por qualquer agente/IA (Codex, Gemini, modelos locais, chat) quando o Claude não estiver disponível.

Uso: python exportar-portatil.py      (rode após editar o plugin; o atualizar-plugin.ps1 já chama)
     python exportar-portatil.py --verificar   (não escreve; 0 = confere, 1 = diverge)
Não edite portatil\\ à mão: edite o plugin e gere de novo.
"""
import argparse, datetime, os, re, textwrap

WS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PL = os.path.join(WS, "plugin", "investigacao-cpj")
OUT = os.path.join(WS, "portatil")
SK = os.path.join(PL, "skills")

PACOTES = [
    ("01-processar-ip", "Receber e processar o material do IP (PDF → OCR → Markdown por página)",
     ["commands/novo-caso.md", "commands/processar-ip.md", "skills/pdf-autos-policiais/SKILL.md"]),
    ("02-analisar-ip", "Analisar IP de fraude/estelionato com rastreabilidade",
     ["commands/analisar-ip.md", "skills/analise-ip-fraude/SKILL.md", "skills/analise-documental/SKILL.md",
      "agents/analista-documental.md", "skills/analise-ip-fraude/references/tipologia-golpes.md",
      "skills/analise-ip-fraude/references/referencias-normativas.md",
      "skills/analise-ip-fraude/references/dados-faltantes.md"]),
    ("03-analista-financeiro", "Extrair tabelas financeiras e montar o caminho do dinheiro",
     ["agents/analista-financeiro.md"]),
    ("04-relatorio-ip", "Redigir o Relatório de Investigação no modelo CPJ e gerar o DOCX",
     ["commands/relatorio-ip.md", "skills/relatorio-ip-fraude/SKILL.md",
      "skills/relatorio-ip-fraude/references/modelo-cpj.md",
      "skills/analise-ip-fraude/references/dados-faltantes.md", "@calibracao/licoes-aprendidas.md"]),
    ("05-revisar-relatorio", "Revisar relatório contra as fontes e o modelo CPJ",
     ["commands/revisar-relatorio.md", "agents/revisor-de-relatorio.md", "@calibracao/licoes-aprendidas.md"]),
    ("06-entregar", "Registrar a entrega (baixa na produção)", ["commands/entregar.md", "skills/base-cpj/SKILL.md"]),
    ("07-calibrar", "Calibrar o sistema com a versão final do investigador",
     ["commands/calibrar.md", "@calibracao/licoes-aprendidas.md"]),
    ("08-buscar", "Pesquisar na base RAG e cruzar identificadores entre casos",
     ["commands/buscar.md", "skills/base-cpj/SKILL.md"]),
    ("09-painel", "Produção e painel", ["commands/painel.md", "skills/base-cpj/SKILL.md"]),
    ("11-osint-policial", "Pesquisa OSINT policial sênior (fontes abertas, base legal, captura de prova)",
     ["skills/osint-policial/SKILL.md", "skills/osint-policial/references/base-legal-e-limites.md",
      "skills/osint-policial/references/fontes-brasil.md", "skills/osint-policial/references/tecnicas-e-captura.md",
      "skills/analise-ip-fraude/references/osint-empresas.md", "skills/analise-ip-fraude/references/dados-faltantes.md"]),
    ("10-fluxo-completo", "Pipeline completo do IP com pontos de aprovação",
     ["commands/fluxo-ip.md", "commands/processar-ip.md", "commands/analisar-ip.md", "commands/relatorio-ip.md"]),
]

SUBST = [
    (r"\$ARGUMENTS", "[ARGUMENTOS: informe o ID do caso (ex.: OS-123-2026) e observações]"),
    (r"<base da skill>\\scripts", r"plugin\\investigacao-cpj\\skills\\<skill>\\scripts"),
    (r"C:\\CPJ - TRABALHO\\", ""),
    (r"C:/CPJ - TRABALHO/", ""),
    (r"(?i)delegue (a revisão )?ao agente `([\w-]+)`", r"execute as instruções do agente `\2` (seção neste arquivo ou em portatil\\)"),
]


def regras():
    t = open(os.path.join(WS, "AGENTS.md"), encoding="utf-8").read()
    m = re.search(r"## 1\. Regras.*?(?=\n## 2\.)", t, flags=re.S)
    if not m: return ""
    reg = m.group(0).strip()
    reg = re.sub(r"C:\\CPJ - TRABALHO\\", "", reg)
    reg = re.sub(r"C:/CPJ - TRABALHO/", "", reg)
    return reg


def peca(rel):
    if rel.startswith("@"):
        p = os.path.join(WS, rel[1:].replace("/", os.sep)); origem = rel[1:]
        titulo = f"Instantâneo de `{origem}` (versão viva: o próprio arquivo no workspace)"
    else:
        p = os.path.join(PL, rel.replace("/", os.sep)); origem = f"plugin/investigacao-cpj/{rel}"
        titulo = f"Fonte: `{origem}`"
    txt = open(p, encoding="utf-8").read()
    desc = ""
    m = re.match(r"---\n(.*?)\n---\n", txt, flags=re.S)
    if m:
        d = re.search(r"^description:\s*(.+)$", m.group(1), flags=re.M)
        if d:
            descricao = d.group(1).strip()
            if re.fullmatch(r"[>|][+-]?", descricao):
                linhas = []
                for linha in m.group(1)[d.end():].splitlines():
                    if linha.strip() and not linha[:1].isspace(): break
                    linhas.append(linha)
                bloco = textwrap.dedent("\n".join(linhas)).strip()
                descricao = re.sub(r"(?<=\S)\n(?=\S)", " ", bloco) if descricao.startswith(">") else bloco
            if descricao:
                desc = "\n".join("> " + linha for linha in descricao.splitlines()) + "\n\n"
        txt = txt[m.end():]
    for a, b in SUBST: txt = re.sub(a, b, txt)
    txt = re.sub(r"^(#{1,5}) ", lambda mm: "#" + mm.group(1) + " ", txt, flags=re.M)  # rebaixa títulos
    return f"## {titulo}\n\n{desc}{txt.strip()}\n"


def gerar(agora):
    """Conteúdo esperado de cada arquivo de portatil\\, sem escrever nada."""
    saidas, indice = {}, []
    for nome, titulo, partes in PACOTES:
        corpo = [f"# {titulo}", "", "No workspace, comece pela memória central `MEMORIA.md` e pelas fontes vivas ali indicadas; este portátil é um instantâneo para uso fora dele.", "",
                 f"*Arquivo portátil gerado em {agora} a partir do plugin `investigacao-cpj`. Autocontido: serve para qualquer agente de IA. "
                 "Não edite aqui — edite o plugin e rode `ferramentas\\exportar-portatil.py`.*", "",
                 "## Regras obrigatórias", "", regras().split("\n", 1)[1].strip(), "",
                 "## Como usar fora do Claude Code", "",
                 "- Onde estiver `/comando`, siga o texto daquele comando abaixo. Onde disser \"skill X\" ou \"agente X\", as instruções estão neste arquivo ou em `portatil\\`.",
                 "- Scripts Python ficam em `plugin\\investigacao-cpj\\skills\\<skill>\\scripts\\` (PowerShell, `python`). Sem execução de comandos, peça ao usuário para rodá-los.",
                 "- Sem subagentes: execute as etapas em sequência.", ""]
        corpo += [peca(p) for p in partes]
        saidas[f"{nome}.md"] = "\n".join(corpo)
        indice.append(f"| `{nome}.md` | {titulo} |")
    saidas["README.md"] = "\n".join([
        "# Procedimentos portáteis (qualquer agente de IA)", "",
        f"Gerado em {agora}. Um arquivo autocontido por tarefa. Leia também `..\\AGENTS.md`.", "",
        "| Arquivo | Tarefa |", "|---|---|", *indice, "",
        "Atualização: edite `plugin\\investigacao-cpj\\` e rode `python ferramentas\\exportar-portatil.py` "
        "(ou `ferramentas\\atualizar-plugin.ps1`, que já faz isso).", ""])
    return saidas


DATA_GERACAO = re.compile(r"(?i)\b(gerado em) \d{4}-\d{2}-\d{2} \d{2}:\d{2}")


def normalizar(texto):
    """Único trecho que pode divergir entre gerações: o carimbo de data/hora (e o fim de linha do Windows)."""
    return DATA_GERACAO.sub(r"\1 <data>", texto.replace("\r\n", "\n"))


def divergencias(saidas):
    """Arquivos de portatil\\ ausentes, desatualizados ou que sobram em relação à fonte atual."""
    achados = []
    for nome, esperado in saidas.items():
        alvo = os.path.join(OUT, nome)
        if not os.path.isfile(alvo):
            achados.append(f"ausente: {nome}")
        elif normalizar(open(alvo, encoding="utf-8", newline="").read()) != normalizar(esperado):
            achados.append(f"desatualizado: {nome}")
    if os.path.isdir(OUT):
        achados += [f"sobra: {n}" for n in sorted(os.listdir(OUT)) if n.endswith(".md") and n not in saidas]
    return achados


def main(argv=None):
    global WS, PL, OUT, SK
    ap = argparse.ArgumentParser(description="Gera portatil\\*.md a partir do plugin investigacao-cpj.")
    ap.add_argument("--verificar", action="store_true",
                    help="não escreve: sai com 0 se portatil\\ confere com a fonte (ignorando só o carimbo de geração) e 1 se diverge")
    ap.add_argument("--workspace", help="raiz CPJ alternativa (testes em cópia fictícia)")
    args = ap.parse_args(argv)
    if args.workspace:
        WS = os.path.abspath(args.workspace)
        PL = os.path.join(WS, "plugin", "investigacao-cpj")
        OUT, SK = os.path.join(WS, "portatil"), os.path.join(PL, "skills")
    saidas = gerar(datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
    if args.verificar:
        achados = divergencias(saidas)
        for a in achados:
            print(a)
        print(f"portatil: {'diverge da fonte' if achados else 'confere com a fonte'} ({len(saidas)} arquivos esperados)")
        return 1 if achados else 0
    os.makedirs(OUT, exist_ok=True)
    for nome, texto in saidas.items():
        open(os.path.join(OUT, nome), "w", encoding="utf-8").write(texto)
    print(f"{len(PACOTES)} arquivos portáteis -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
