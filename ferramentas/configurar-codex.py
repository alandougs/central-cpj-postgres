#!/usr/bin/env python
"""Registra procedimentos CPJ como skills locais, sem ler autos ou alterar o Codex global.

python ferramentas/configurar-codex.py
python ferramentas/configurar-codex.py --instalar-usuario
python ferramentas/configurar-codex.py --verificar
"""
import argparse
import json
from pathlib import Path

MARCA = "<!-- Gerado por ferramentas/configurar-codex.py; edite o gerador. -->"
# nome, procedimento, título de interface, descrição de descoberta, resumo de interface
TAREFAS = [
    ("cpj-processar-ip", "01-processar-ip", "CPJ: processar IP", "Receber e extrair PDF, MD ou CSV de um caso CPJ, com OCR local, páginas, tabelas, entidades e registro de tratamento.", "OCR e extração local dos documentos do IP"),
    ("cpj-analisar-ip", "02-analisar-ip", "CPJ: analisar IP", "Analisar um IP de fraude ou estelionato no workspace CPJ: cronologia, pessoas, vínculos, elementos documentados e lacunas.", "Análise rastreável de fraude e estelionato"),
    ("cpj-analista-financeiro", "03-analista-financeiro", "CPJ: fluxo financeiro", "Normalizar extratos e comprovantes de um caso CPJ e reconstruir o caminho do dinheiro, com valores, camadas e fontes.", "Extratos, comprovantes e caminho do dinheiro"),
    ("cpj-relatorio-ip", "04-relatorio-ip", "CPJ: relatório", "Redigir minuta de investigação de um caso CPJ a partir da análise, revisar as fontes e gerar DOCX no modelo oficial CPJ 2026.", "Minuta, rastreabilidade e DOCX no modelo CPJ"),
    ("cpj-revisar-relatorio", "05-revisar-relatorio", "CPJ: revisar relatório", "Revisar relatório Markdown ou DOCX de um caso CPJ contra as fontes, a rastreabilidade e o modelo oficial.", "Revisão do relatório contra as fontes do IP"),
    ("cpj-entregar", "06-entregar", "CPJ: registrar entrega", "Registrar entrega ou finalização já informada pelo investigador de um relatório CPJ, com versão final, baixa e produção.", "Versão final, baixa e registro de produção"),
    ("cpj-calibrar", "07-calibrar", "CPJ: calibrar", "Comparar minuta CPJ com a versão final do investigador e propor lições genéricas de redação sem dados dos casos.", "Lições genéricas a partir das correções"),
    ("cpj-buscar", "08-buscar", "CPJ: buscar na base", "Pesquisar texto e identificadores na base local CPJ ou cruzar CPF, Pix, conta e telefone entre inquéritos indicados.", "Busca local e cruzamento de identificadores"),
    ("cpj-painel", "09-painel", "CPJ: produção e painel", "Atualizar e consultar produção, metas e indicadores no painel local do workspace CPJ.", "Produção, metas e indicadores locais CPJ"),
    ("cpj-osint-policial", "11-osint-policial", "CPJ: OSINT policial", "Pesquisar fontes abertas de forma lícita sobre empresas, pessoas, telefones, perfis, domínios e criptoativos ligados a um caso CPJ, com captura de prova e aviso em CAIXA ALTA dos dados faltantes.", "OSINT lícito e rastreável, com dados faltantes em caixa alta"),
    ("cpj-fluxo-completo", "10-fluxo-completo", "CPJ: fluxo completo", "Executar o fluxo completo de um caso CPJ, do recebimento à minuta revisada e ao DOCX, com os pontos de decisão do investigador.", "Do recebimento à minuta revisada e ao DOCX"),
]

REGRAS = """## Uso no Codex

- Leia `AGENTS.md` na raiz antes de acessar material do caso. Siga as regras de fonte, sigilo, originais imutáveis e saída como minuta.
- Execução de arquivos no PC não implica inferência local: não carregue autos reais, imagens, extrações, consultas ou resultados identificáveis no contexto de um modelo externo. Sem ambiente/conta compatível com a regra 6 de `AGENTS.md`, limite-se a procedimentos, código e dados fictícios; processamento de autos permanece no fluxo local autorizado.
- Confirme o ID e a etapa solicitada; não selecione um caso por proximidade ou data. Leia a versão viva de `calibracao/licoes-aprendidas.md` antes de analisar ou redigir, em vez de depender do instantâneo portátil.
- Comandos `/...` e `$ARGUMENTS` nos procedimentos significam a tarefa e os argumentos do usuário; não exigem Claude CLI. Skills e agentes citados são instruções no plugin/portátil, não dependências instaladas do Codex. Use os scripts existentes no plugin; não copie scripts nem o modelo DOCX para a skill.
- Execute as instruções de agentes em sequência, conforme a adaptação do `AGENTS.md`. Em IP extenso, trabalhe por blocos e consolide as fontes. Não inicie tarefas automáticas da Central ao atender uma tarefa interativa.
- Resolva caminhos relativos à raiz CPJ. Se aparecer `<base da skill>`, use a pasta original em `plugin/investigacao-cpj/skills/`, nunca esta pasta adaptadora. Scripts usam `python` em PowerShell; confira `--help` quando necessário. Em teste isolado, defina `CPJ_WORKSPACE` para a pasta fictícia.
- Atualize status/campos documentados com `caso.py` e indexe após concluir a etapa. Não registre entrega nem crie arquivo `FINAL` ao apenas produzir minuta: a indexação pode dar baixa automaticamente por esse nome.
- Preserve pontos de aprovação explícitos do procedimento quando não houver autorização prévia. Produza o resultado concreto revisável antes de solicitar aprovação. Calibração só guarda lições genéricas aprovadas; aprovação de uma minuta não autoriza divulgação externa.
"""


def manifesto(nome, descricao, corpo):
    return f"---\nname: {nome}\ndescription: {json.dumps(descricao, ensure_ascii=False)}\n---\n\n{MARCA}\n\n{corpo.strip()}\n"


def interface(titulo, resumo):
    # Somente metadados de apresentação; seleção automática usa o padrão do Codex.
    return (f"# {MARCA}\ninterface:\n"
            f"  display_name: {json.dumps(titulo, ensure_ascii=False)}\n"
            f"  short_description: {json.dumps(resumo, ensure_ascii=False)}\n")


def arquivos_projeto(ws):
    arquivos = {}
    base = ws / ".agents" / "skills"
    for nome, procedimento, titulo, descricao, resumo in TAREFAS:
        fonte = ws / "portatil" / f"{procedimento}.md"
        if not fonte.is_file():
            raise ValueError(f"Procedimento ausente: {fonte}. Gere portatil primeiro.")
        corpo = f"# {titulo}\n\nLeia e execute [o procedimento desta tarefa](../../../portatil/{procedimento}.md). Esse arquivo é a fonte do fluxo; não use apenas este resumo.\n\n{REGRAS}"
        arquivos[base / nome / "SKILL.md"] = manifesto(nome, descricao, corpo)
        arquivos[base / nome / "agents" / "openai.yaml"] = interface(titulo, resumo)
    corpo = """# Manutenção da Central CPJ

Leia [PRD.md](../../../PRD.md) e [AGENTS.md](../../../AGENTS.md) na raiz antes de alterar o sistema. O PRD descreve a arquitetura, o estado e os próximos passos; consulte os arquivos atuais para confirmar o que está implementado.

- Trabalhe apenas no escopo solicitado. Central: `plugin/investigacao-cpj/app/`; procedimentos: `commands/`, `skills/`, `agents/`; manutenção: `ferramentas/`.
- Preserve `caso.json` como fonte da verdade, índice SQLite regenerável, permissões por perfil, auditoria, cabeçalho `X-CPJ: 1` em POST e acesso local por padrão. Alterações de integração do Codex não autorizam trocar o executor Claude em `tarefas.py`.
- Não leia autos, bases de consulta, relatórios reais, credenciais ou arquivos de `config/` para desenvolver. Teste com dados fictícios em workspace isolado, com `CPJ_WORKSPACE` nos scripts e `--workspace`/`--porta 8766 --somente-local --sem-navegador` no servidor.
- Procedimentos operacionais continuam no plugin. Após editá-los, gere `portatil/` com `python ferramentas/exportar-portatil.py`. Os adaptadores Codex apontam para esses arquivos vivos.
- Após editar este gerador, rode `python ferramentas/configurar-codex.py`; para conferir os adaptadores sem escrever, use `--verificar`.
- Valide o comportamento afetado; atualize a seção 9 e o Registro de mudanças do PRD a cada entrega. Publicação, alterações de rede, instalação do plugin Claude ou envio externo dependem do pedido correspondente; não fazem parte de uma manutenção local automaticamente.
"""
    nome = "cpj-desenvolver"
    arquivos[base / nome / "SKILL.md"] = manifesto(nome, "Desenvolver ou manter a Central CPJ, o plugin investigacao-cpj e seus scripts locais conforme PRD, com validação em dados fictícios.", corpo)
    arquivos[base / nome / "agents" / "openai.yaml"] = interface("CPJ: desenvolver sistema", "Manutenção da Central, plugin e scripts CPJ")
    return arquivos


def arquivos_usuario(ws, destino):
    linhas = ["# Projeto CPJ", "", f"Workspace local: `{ws}`.", "",
              "Use somente para pedidos sobre este projeto. Leia o `AGENTS.md` desse workspace; para desenvolvimento, leia também `PRD.md`. Não aplique as regras CPJ a projetos alheios.", "",
              "Escolha a skill da etapa na pasta `.agents/skills/` do workspace e leia seu `SKILL.md` antes de agir. Os caminhos abaixo são locais; não exigem conectores ou Claude CLI.", "", "| Pedido | Instrução local |", "|---|---|"]
    for nome, _, titulo, _, _ in TAREFAS:
        linhas.append(f"| {titulo} | `{ws / '.agents' / 'skills' / nome / 'SKILL.md'}` |")
    linhas += [f"| Manter a Central/plugin/scripts | `{ws / '.agents' / 'skills' / 'cpj-desenvolver' / 'SKILL.md'}` |", "",
               "Não carregue conteúdo de autos reais em modelo externo. Execução local de scripts não é inferência local. Use ambiente autorizado pelo órgão para material sigiloso e dados fictícios para manutenção.", "",
               "Se o workspace não existir, informe o caminho ausente; não crie casos nem reconstrua documentos por dedução."]
    return {
        destino / "cpj-projeto" / "SKILL.md": manifesto("cpj-projeto", "Localizar os procedimentos e skills do projeto Central CPJ / investigacao-cpj no computador do investigador. Use somente para este workspace CPJ.", "\n".join(linhas)),
        destino / "cpj-projeto" / "agents" / "openai.yaml": interface("CPJ: projeto do investigador", "Acesso às instruções e skills do projeto CPJ"),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--instalar-usuario", action="store_true", help="Instala cpj-projeto em ~/.agents/skills (ou --skills-usuario).")
    parser.add_argument("--skills-usuario", type=Path, default=Path.home() / ".agents" / "skills")
    parser.add_argument("--verificar", action="store_true", help="Confere arquivos esperados sem escrever.")
    args = parser.parse_args()
    ws = args.workspace.resolve()
    try:
        for nome in ("AGENTS.md", "PRD.md"):
            if not (ws / nome).is_file():
                raise ValueError(f"Raiz CPJ inválida: falta {ws / nome}")
        arquivos = arquivos_projeto(ws)
        if args.instalar_usuario:
            arquivos.update(arquivos_usuario(ws, args.skills_usuario.resolve()))
        # Preflight: não sobrescrever arquivos que não pertencem ao gerador.
        for caminho in arquivos:
            if caminho.is_file() and MARCA not in caminho.read_text(encoding="utf-8"):
                raise ValueError(f"Arquivo não gerenciado; preservado: {caminho}")
        divergentes = [p for p, t in arquivos.items() if not p.is_file() or p.read_text(encoding="utf-8") != t]
        if args.verificar:
            for caminho in divergentes:
                print(f"Ausente ou desatualizado: {caminho}")
            if divergentes:
                return 1
        else:
            for caminho in divergentes:
                caminho.parent.mkdir(parents=True, exist_ok=True)
                caminho.write_text(arquivos[caminho], encoding="utf-8", newline="\n")
        print(f"Skills CPJ: {len(arquivos) // 2}; arquivos {'conferidos' if args.verificar else 'atualizados'}: {0 if args.verificar else len(divergentes)}.")
        print(f"Projeto: {ws / '.agents' / 'skills'}")
        if args.instalar_usuario:
            print(f"Usuário: {args.skills_usuario.resolve() / 'cpj-projeto'}")
        return 0
    except (OSError, ValueError) as exc:
        print(f"Erro: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
