#!/usr/bin/env python3
"""Gera portatil\\*.md: um arquivo AUTOCONTIDO por tarefa, a partir do plugin investigacao-cpj,
para uso por qualquer agente/IA (Codex, Gemini, modelos locais, chat) quando o Claude não estiver disponível.

Uso: python exportar-portatil.py      (rode após editar o plugin; o atualizar-plugin.ps1 já chama)
Não edite portatil\\ à mão: edite o plugin e gere de novo.
"""
import datetime, os, re

WS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PL = os.path.join(WS, "plugin", "investigacao-cpj")
OUT = os.path.join(WS, "portatil")
SK = os.path.join(PL, "skills")

PACOTES = [
    ("01-processar-ip", "Receber e processar o material do IP (PDF → OCR → Markdown por página, CSV, entidades)",
     ["commands/novo-caso.md", "commands/processar-ip.md", "skills/pdf-autos-policiais/SKILL.md"]),
    ("02-analisar-ip", "Analisar IP de fraude/estelionato com rastreabilidade",
     ["commands/analisar-ip.md", "skills/analise-ip-fraude/SKILL.md", "skills/analise-documental/SKILL.md",
      "agents/analista-documental.md", "skills/analise-ip-fraude/references/tipologia-golpes.md",
      "skills/analise-ip-fraude/references/referencias-normativas.md"]),
    ("03-analista-financeiro", "Extrair tabelas financeiras e montar o caminho do dinheiro",
     ["agents/analista-financeiro.md"]),
    ("04-relatorio-ip", "Redigir o Relatório de Investigação no modelo CPJ e gerar o DOCX",
     ["commands/relatorio-ip.md", "skills/relatorio-ip-fraude/SKILL.md",
      "skills/relatorio-ip-fraude/references/modelo-cpj.md", "@calibracao/licoes-aprendidas.md"]),
    ("05-revisar-relatorio", "Revisar relatório contra as fontes e o modelo CPJ",
     ["commands/revisar-relatorio.md", "agents/revisor-de-relatorio.md", "@calibracao/licoes-aprendidas.md"]),
    ("06-entregar", "Registrar a entrega (baixa na produção)", ["commands/entregar.md", "skills/base-cpj/SKILL.md"]),
    ("07-calibrar", "Calibrar o sistema com a versão final do investigador",
     ["commands/calibrar.md", "@calibracao/licoes-aprendidas.md"]),
    ("08-buscar", "Pesquisar na base RAG e cruzar identificadores entre casos",
     ["commands/buscar.md", "skills/base-cpj/SKILL.md"]),
    ("09-painel", "Produção e painel", ["commands/painel.md", "skills/base-cpj/SKILL.md"]),
    ("10-fluxo-completo", "Pipeline completo do IP com pontos de aprovação",
     ["commands/fluxo-ip.md", "commands/processar-ip.md", "commands/analisar-ip.md", "commands/relatorio-ip.md"]),
]

SUBST = [
    (r"\$ARGUMENTS", "[ARGUMENTOS: informe o ID do caso (ex.: OS-123-2026) e observações]"),
    (r"<base da skill>\\scripts", r"C:\\CPJ - TRABALHO\\plugin\\investigacao-cpj\\skills\\<skill>\\scripts"),
    (r"(?i)delegue (a revisão )?ao agente `([\w-]+)`", r"execute as instruções do agente `\2` (seção neste arquivo ou em portatil\\)"),
]


def regras():
    t = open(os.path.join(WS, "AGENTS.md"), encoding="utf-8").read()
    m = re.search(r"## 1\. Regras.*?(?=\n## 2\.)", t, flags=re.S)
    return m.group(0).strip() if m else ""


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
        desc = f"> {d.group(1).strip()}\n\n" if d else ""
        txt = txt[m.end():]
    for a, b in SUBST: txt = re.sub(a, b, txt)
    txt = re.sub(r"^(#{1,5}) ", lambda mm: "#" + mm.group(1) + " ", txt, flags=re.M)  # rebaixa títulos
    return f"## {titulo}\n\n{desc}{txt.strip()}\n"


os.makedirs(OUT, exist_ok=True)
agora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
indice = []
for nome, titulo, partes in PACOTES:
    corpo = [f"# {titulo}", "",
             f"*Arquivo portátil gerado em {agora} a partir do plugin `investigacao-cpj`. Autocontido: serve para qualquer agente de IA. "
             "Não edite aqui — edite o plugin e rode `ferramentas\\exportar-portatil.py`.*", "",
             "## Regras obrigatórias", "", regras().split("\n", 1)[1].strip(), "",
             "## Como usar fora do Claude Code", "",
             "- Onde estiver `/comando`, siga o texto daquele comando abaixo. Onde disser \"skill X\" ou \"agente X\", as instruções estão neste arquivo ou em `portatil\\`.",
             "- Scripts Python ficam em `C:\\CPJ - TRABALHO\\plugin\\investigacao-cpj\\skills\\<skill>\\scripts\\` (PowerShell, `python`). Sem execução de comandos, peça ao usuário para rodá-los.",
             "- Sem subagentes: execute as etapas em sequência.", ""]
    corpo += [peca(p) for p in partes]
    open(os.path.join(OUT, f"{nome}.md"), "w", encoding="utf-8").write("\n".join(corpo))
    indice.append(f"| `{nome}.md` | {titulo} |")

open(os.path.join(OUT, "README.md"), "w", encoding="utf-8").write("\n".join([
    "# Procedimentos portáteis (qualquer agente de IA)", "",
    f"Gerado em {agora}. Um arquivo autocontido por tarefa. Leia também `..\\AGENTS.md`.", "",
    "| Arquivo | Tarefa |", "|---|---|", *indice, "",
    "Atualização: edite `plugin\\investigacao-cpj\\` e rode `python ferramentas\\exportar-portatil.py` "
    "(ou `ferramentas\\atualizar-plugin.ps1`, que já faz isso).", ""]))
print(f"{len(PACOTES)} arquivos portáteis -> {OUT}")
