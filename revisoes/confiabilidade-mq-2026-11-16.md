# Meta de entrega pré-aprovada — plano e andamento (MQ01–MQ04)

Pedido expresso do operador em 16/11/2026: implementar por fases as melhorias aceitas, com coordenador (Fable-Orquestrador) e executores por complexidade. Este arquivo é o ponto de retomada: leia-o antes de continuar em outra sessão. Não contém dado de caso.

## Critério de pronto

1. A confiabilidade passa a ter número: percentual da primeira e da última minuta mantido no relatório entregue (PDF do relatório = versão entregue), calculado por script local.
2. O conferidor confirma dado citado só por folhas, sem perder a falha fechada.
3. Redação e revisão rodam o conferidor antes de a minuta chegar ao operador e citam folhas em toda frase com dado verificável.
4. PRD e fila ficam menores, sem perda de conteúdo e com os testes aprovados.
5. Suíte completa (`ferramentas/testar-tudo.py`) sem falha nova em relação à linha de base.

## Fases

| Fase | Tarefa | Executor | Estado |
|---|---|---|---|
| 1 | MQ01 — métrica de entrega (`medir_entrega.py`, `/calibrar`, regra em AGENTS.md) | Sonnet | em andamento |
| 1 | MQ02 — conferidor por folhas (`conferir_minuta.py`) | Opus | em andamento |
| 1 | MQ04 — enxugar PRD; arquivamento da fila preparado em simulação | Sonnet | em andamento |
| 2 | MQ03 — procedimentos de redação/revisão e `portatil/` (depende do contrato de MQ02) | Sonnet | aguardando MQ02 |
| 3 | Revisão dos diffs, suíte completa, medição real só numérica, aplicação do arquivamento da fila, registro na fila | Coordenador | pendente |

## Fora desta rodada (dependem do operador)

- Tipo de relatório antes de redigir e correção de status dos casos: dependem de o operador dizer o que são os 16 PDFs de uma página de 22/10/2026.
- Limpeza de `casos\` (pastas de teste, duplicidade da OS 2650): mexe em dado de produção; só com lista conferida e confirmação.
- Atualização instalada do plugin, commit e publicação: só com pedido expresso.

## Linha de base das medições manuais (16/11/2026)

Dez relatórios completos com PDF: primeira minuta mantida em 80% ou mais em 5; última minuta em 9. Conferidor: rodou em 15 de 29 casos com minuta; 131 de 141 bloqueios eram dado sem referência de folha.

## Andamento

- 16/11/2026 — tarefas reservadas na fila; fase 1 disparada.
- 16/11/2026 — **MQ01 revisada e aprovada.** `medir_entrega.py` criado; `teste_medir_entrega_mq01.py` com 10 testes OK. Execução real só numérica reproduziu a medição manual: 26 casos com minuta e PDF; nos 9 relatórios no modelo, primeira minuta mantida em 80% ou mais em 5 e a última em 9 (média 93,8%). O coordenador separou o agregado em "relatórios no modelo" e "outros documentos" (17 PDFs sem as seções do modelo, fora da meta) e tornou a detecção de "RESUMO DOS FATOS" tolerante a letras espaçadas. Regra 24 acrescentada ao AGENTS.md. Ainda não foi rodado `--gravar` nos casos reais.
- 16/11/2026 — **MQ02 revisada e aprovada.** O conferidor lê a seção `## Mapa de folhas` de `rastreabilidade-vNN.md` (tabela `| Fls. | Pág. do PDF | Documento |`) e, com todas as folhas citadas mapeadas, confere o dado como na citação por página; mapa ausente, ilegível ou ambíguo mantém `CITA_SO_FLS` (REVISAR). Schema `cpj-conferencia/1` com campo aditivo `mapa_fls`. `teste_conferir_fls_mq02.py`: 9 testes OK (1 pulado por falta de privilégio de symlink); os 7 testes de gate existentes seguem iguais. Limite conhecido: mapa errado confirma errado; a folha continua sujeita à revisão humana.
- 16/11/2026 — **MQ04 parte A revisada e aprovada.** PRD de 117.626 para 34.572 bytes; histórico literal em `docs/historico/PRD-historico-2026.md` (85.035 bytes); prova de não perda por script (295 de 296 linhas não vazias; a única ausente é a linha "Última atualização", trocada de propósito). **Parte B** só simulada: arquivar as 234 linhas concluídas reduz a fila de 350 KB para 220 KB; o restante é o log "Registro de entregas", não coberto. `reabrir` deixa de achar tarefa arquivada.
- Falha pré-existente anotada: `teste_distribuicao_un16.py` com 3 falhas por `portatil/` divergente da fonte (antes desta rodada); deve sumir ao regenerar os portáteis.
- Determinações do operador em 16/11/2026: relatórios seguem a O.S. no modelo uniforme; pasta única por O.S., sem duplicidade (inventário feito, exclusão depende de lista confirmada); atualização do plugin e publicação no GitHub autorizadas.
- 16/11/2026 — **MQ03 revisada e integrada.** Gate em modo entrega e citação de folhas nos procedimentos; texto do mapa de folhas inserido no `SKILL.md`; `fluxo-ip.md` e passo 4 de `relatorio-ip.md` alinhados; `portatil/` regenerado. Para o plugin atualizar: `pacote-plugin.py` passou a aceitar `.svg` e a `LICENSE` do Leaflet e a excluir `.pytest_cache`; `teste_distribuicao_un16.py` ajustado; `argument-hint` de `relatorio-ip.md` entre aspas (o validador recusava). **Plugin 0.3.4 instalado.**
- 16/11/2026 — **Suíte completa:** 144 de 166 suítes aprovadas. As 22 que falham são todas de interface (JS, mapa, grafo, fila na tela); nenhuma usa arquivo desta rodada. Causas vistas no log: script do Kaspersky injetado no navegador de teste ("recurso externo") e trabalho de interface de outros agentes em andamento. Não havia linha de base anterior para comparar.
- 16/11/2026 — **Fila:** 234 linhas concluídas arquivadas em `docs/historico/TAREFAS-concluidas-2026.md` (350.058 para 219.770 bytes); MQ01 a MQ04 concluídas na fila.
- 16/11/2026 — **PAUSA pedida pelo operador.** Nada foi commitado nem enviado ao GitHub.
- **Ao retomar, nesta ordem:** (1) `git add` somente dos arquivos desta rodada: `AGENTS.md`, `PRD.md`, `TAREFAS-COMPARTILHADAS.md`, `docs/historico/`, `ferramentas/pacote-plugin.py`, `plugin/.claude-plugin/marketplace.json`, `plugin/investigacao-cpj/.claude-plugin/plugin.json`, `plugin/investigacao-cpj/agents/revisor-de-relatorio.md`, `plugin/investigacao-cpj/commands/{calibrar,fluxo-ip,relatorio-ip,revisar-relatorio}.md`, `plugin/investigacao-cpj/skills/relatorio-ip-fraude/SKILL.md`, `.../scripts/{conferir_minuta,medir_entrega}.py`, `plugin/investigacao-cpj/app/testes/{teste_conferir_fls_mq02,teste_medir_entrega_mq01,teste_distribuicao_un16}.py`, `portatil/`, `revisoes/confiabilidade-mq-2026-11-16.md`; NÃO incluir `.gitignore`, `app/` (rotas, static), nem testes de outros agentes; (2) `ferramentas/verificar-publicacao.py --staged`; (3) commit e `git push` na branch atual `codex/sincronizacao-enxuta-20261027` (publicação autorizada pelo operador em 16/11/2026; sem merge em `main`); (4) apresentar ao operador o plano de pasta única (inventário: 141 arquivos idênticos entre `casos\` e `ordens-de-servico\`, 0,88 GB; pastas de caso em dobro das O.S. 2650 e 2672) e só excluir com lista confirmada; (5) decidir com o operador se roda `medir_entrega.py --todos --gravar` nos casos reais.
- (histórico) Passo previsto antes da pausa: receber MQ03; inserir no `SKILL.md` o texto do mapa de folhas; rodar `ferramentas/testar-tudo.py`; atualizar plugin (`ferramentas/atualizar-plugin.ps1`, que regenera `portatil/`); commit seletivo dos arquivos MQ e publicação; aplicar o arquivamento da fila.
