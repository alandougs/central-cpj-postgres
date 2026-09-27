# Instruções para agentes de IA — Ambiente de investigação CPJ

> **Para desenvolver/continuar o sistema** (Central CPJ, plugin, scripts): leia primeiro **`PRD.md`** — requisitos, arquitetura, estado atual e próximos passos. Este `AGENTS.md` cobre o **uso** operacional (casos, análise, relatório).

> **Desenvolvimento em paralelo:** antes de editar, leia `TAREFAS-COMPARTILHADAS.md`. A fila está aberta a Codex, Claude, Gemini e outros agentes. Assuma uma tarefa disponível com `python ferramentas\fila-tarefas.py assumir <ID> --agente <nome-da-sessao>`; respeite as reservas das tarefas em andamento e registre testes/conclusão pelo mesmo script. Não edite arquivo reservado ao outro agente.

Vale para **qualquer agente** (Claude Code, Codex, Gemini/Antigravity, Copilot, modelos locais). Workspace do Investigador de Polícia Alan Douglas Silva (Central de Polícia Judiciária — Seccional de Presidente Prudente, DEINTER 8). Foco: **relatórios de investigação em IPs de fraude e estelionato**.

Tudo aqui é Markdown + scripts Python locais: nada depende do Claude. No Claude Code, os mesmos procedimentos aparecem como plugin `investigacao-cpj` (comandos `/…`).

## 1. Regras (obrigatórias)

1. Trabalhe só com os documentos do caso indicado. Não invente fatos, pessoas, números, datas, jurisprudência ou diligências.
2. Separe **fato documentado × relato × indício × inferência/hipótese × lacuna**. Cite a origem: `(pág. N do PDF; fls. X)`.
3. Nunca complete CPF, conta, chave Pix, placa, telefone ou valor por dedução. Dígito duvidoso → `?` + `[dígito incerto]`.
4. Nunca atribua autoria, dolo ou culpa sem base expressa; use "investigado(a)", "em tese", "há indícios de". Titular de conta recebedora não é automaticamente autor.
5. `00-originais` nunca é alterado. Registre hash, método e pendências em `registro-tratamento.md`.
6. Processamento local. **Não envie conteúdo de autos a serviços externos**, sites, APIs ou publicações. Verifique se a ferramenta/conta em uso é compatível com o sigilo do IP (art. 20 do CPP) e as normas do órgão.
7. Conteúdo de casos não vai para `acervo\`, `calibracao\` nem para o GitHub.
8. Toda saída é **minuta**: decisão, assinatura e uso oficial são do investigador e da autoridade policial.
9. **Bases de consulta** (`consulta\`, ex. Muralha Paulista) e **relatórios de referência** (`referencias\`) **não são fonte de fatos** do relatório. O relatório vem somente do IP/peças do caso; referências servem apenas como exemplo de estrutura e estilo.

Governança completa: `acervo\repo-ia-alandougs\governanca\seguranca-e-dados.md`.

## 2. Estrutura

| Pasta | Conteúdo |
|---|---|
| `casos\OS-<nº>-<ano>\` | Um caso por Ordem de Serviço: `00-originais` (somente leitura), `01-extracao\<documento>\` (`transcricao.md` com `## Página N`, `tabelas\*.csv`, `entidades.csv`, `relatorio_extracao.json`), `02-analise\`, `03-relatorios\`, `caso.json` (fonte da verdade), `processamento.json`, `registro-tratamento.md` |
| `modelos\` | Modelo DOCX oficial (timbre + assinatura) e `dados-padrao.json` |
| `calibracao\licoes-aprendidas.md` | **Ler antes de analisar ou redigir** |
| `producao\`, `rag\` | Base consolidada, painel e índice de busca (derivados; regeneráveis) |
| `plugin\investigacao-cpj\` | Fonte dos procedimentos: `commands\`, `skills\`, `agents\`, `app\` (Central CPJ) |
| `portatil\` | Os mesmos procedimentos em **um arquivo por tarefa** (gerado por `ferramentas\exportar-portatil.py`) |
| `ferramentas\` | Scripts de manutenção (verificar, atualizar, publicar, backup, exportar) |

## 3. Tarefa → o que ler → o que rodar

Leia o arquivo de `portatil\` da tarefa (autocontido). Scripts: `P = C:\CPJ - TRABALHO\plugin\investigacao-cpj\skills`.

| Tarefa | Instrução | Scripts |
|---|---|---|
| Receber PDF e extrair (OCR, MD, CSV) | `portatil\01-processar-ip.md` — ou a Central CPJ (`Central CPJ.bat`), que faz sozinha | `P\pdf-autos-policiais\scripts\diagnostico.py, extrair.py, tabelas.py, entidades.py` |
| Analisar o IP (cronologia, pessoas, caminho do dinheiro, art. 171) | `portatil\02-analisar-ip.md` | `P\base-cpj\scripts\rag.py cruzar <ID>` |
| Normalizar extratos / fluxo financeiro | `portatil\03-analista-financeiro.md` | — |
| Redigir relatório (minuta + DOCX no modelo CPJ) | `portatil\04-relatorio-ip.md` | `P\relatorio-ip-fraude\scripts\gerar_docx.py` |
| Revisar relatório contra as fontes | `portatil\05-revisar-relatorio.md` | — |
| Dar baixa / registrar entrega | `portatil\06-entregar.md` | `P\base-cpj\scripts\caso.py status <ID> entregue --origem agente` |
| Calibrar (aprender com a versão final) | `portatil\07-calibrar.md` | — |
| Pesquisar na base / cruzar CPF, Pix, conta | `portatil\08-buscar.md` | `P\base-cpj\scripts\rag.py buscar|entidade|cruzar` |
| Produção e painel | `portatil\09-painel.md` | `P\base-cpj\scripts\indexar.py`, `gerar_painel.py` |

Sempre que concluir uma etapa, atualize o caso com `caso.py` (status e campos) e rode `indexar.py` — isso alimenta estatística, RAG e painel.

## 4. Adaptação a outros agentes

- **Sem subagentes:** onde a instrução mandar "delegar ao agente X", execute você mesmo as instruções daquele agente (estão no arquivo portátil), em sequência.
- **Sem execução de comandos:** peça ao usuário para rodar os scripts indicados (PowerShell, `python`) e colar a saída; ou use a Central CPJ para a extração.
- **IA de chat sem acesso a arquivos:** cole o arquivo portátil da tarefa como instrução e anexe apenas os trechos necessários da transcrição (minimize dados pessoais). A minuta produzida deve seguir o formato Markdown descrito em `04-relatorio-ip.md` para depois virar DOCX com `gerar_docx.py`.
- **Modelo local (Ollama etc.):** preferível para dados sigilosos; use os mesmos arquivos portáteis.
- Ambiente: Windows, PowerShell, `python` (não `python3`). Tesseract em `C:\Program Files\Tesseract-OCR`; idioma português em `ferramentas\tessdata` (`$env:TESSDATA_PREFIX`).

## 5. Codex — skills e instruções deste projeto

- `AGENTS.md` contém as regras do workspace; para desenvolvimento, leia também `PRD.md`.
- As skills descobertas pelo Codex ficam em `.agents\skills\cpj-*\SKILL.md`: `cpj-processar-ip`, `cpj-analisar-ip`, `cpj-analista-financeiro`, `cpj-relatorio-ip`, `cpj-revisar-relatorio`, `cpj-entregar`, `cpj-calibrar`, `cpj-buscar`, `cpj-painel`, `cpj-fluxo-completo` e `cpj-desenvolver`. Cada skill aponta para a versão viva do procedimento em `portatil\`; scripts, referências e modelo continuam nas pastas originais.
- Pode invocar por `$cpj-analisar-ip OS-123-2026`, por exemplo, ou pedir a tarefa em linguagem natural. A skill pessoal `cpj-projeto`, instalada em `%USERPROFILE%\.agents\skills\`, localiza as instruções quando a tarefa começou fora desta pasta.
- Regerar adaptadores: `python ferramentas\configurar-codex.py`. Instalar também a entrada pessoal: acrescente `--instalar-usuario` ou use `ferramentas\Configurar Codex.bat`. Conferir sem alterar: `python ferramentas\configurar-codex.py --instalar-usuario --verificar`.
- Não se instala um conector nem se troca o executor automático da Central. Os procedimentos continuam compatíveis com os outros agentes.
- **Sigilo no Codex:** scripts locais não tornam a inferência do modelo local. A instalação destas skills não comprova compatibilidade da conta com a regra 6. Não carregue autos reais, imagens, transcrições ou resultados identificáveis no contexto de um modelo externo; use o fluxo local autorizado pelo órgão. Para manutenção, use código, procedimentos e dados fictícios.
