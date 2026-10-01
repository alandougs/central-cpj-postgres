# Papéis e responsabilidades na Central CPJ

Este documento distingue **engenharia do sistema** de **produção policial**. Agentes de IA podem executar tarefas técnicas ou apoiar a elaboração de minutas dentro das instruções aplicáveis; não assumem atribuições legais nem substituem a decisão humana.

## Engenharia do sistema

| Atividade | Responsável | Papel dos demais agentes | Limite |
|---|---|---|---|
| Prioridades e decisões de produto | Investigador responsável pelo workspace | Apresentar evidências e opções | Decisões de escopo não são inferidas de tarefas técnicas |
| Implementação de tarefa | Agente que reservou a tarefa na fila | Respeitar arquivos reservados e contratos registrados | Trabalhar no escopo e validar com dados fictícios |
| Integração de mudanças compartilhadas | Integrador designado na fila | Registrar entrega, dependências e resultados | Não editar arquivos reservados por outro agente |
| Revisão de código e testes | Agente implementador e, quando previsto, revisor | Conferir regressões, segurança e isolamento | Não usar casos reais para testes de desenvolvimento |
| Operação da Central e dados reais | Investigador/operador autorizado | Agentes podem orientar conforme procedimentos | Não ler ou alterar casos fora da tarefa operacional autorizada |

Regras de execução: usar `TAREFAS-COMPARTILHADAS.md` e a ferramenta de fila antes de editar; observar limites de paralelismo e dependências registrados; evitar concorrência no mesmo módulo; testar em workspace temporário com dados fictícios; registrar arquivos, comandos e resultados. Alterações em documentação de estado devem refletir o que foi efetivamente verificado.

## Produção de relatório

| Etapa | Executor | Responsabilidade e limite |
|---|---|---|
| Recebimento, OCR, Markdown, tabelas e entidades | Scripts locais | Produzir artefatos reproduzíveis e registrar método, hash e pendências; preservar `00-originais` |
| Análise documental por blocos | Agente `analista-documental` ou operador | Organizar cronologia, pessoas, documentos, fatos e lacunas com indicação de página; não completar dados ausentes |
| Reconstrução financeira | Agente `analista-financeiro` ou operador | Normalizar valores e descrever transferências conforme comprovantes; não concluir autoria pela titularidade de conta |
| Redação da minuta | Skill/agente `relatorio-ip-fraude` | Redigir no padrão CPJ com base nas peças do caso; sinalizar incertezas e dados faltantes |
| Revisão probatória | Agente `revisor-de-relatorio` em execução independente | Conferir cada afirmação da minuta contra as fontes e classificar divergências, ausências e contradições |
| Revisão, decisão e assinatura | Investigador e autoridade policial, conforme atribuições | Avaliar a minuta, decidir o conteúdo final e assinar; responsabilidade não é delegada à IA |

A Central (código) coordena a sequência de etapas; não há agente gerente que decida o mérito da investigação. A revisão deve ser independente da sessão que redigiu a minuta. Novos papéis ou mudanças na squad dependem de avaliação medida, como tempo, custo, retrabalho e achados de revisão.

## Regras comuns de segurança e qualidade

- Usar somente documentos do caso indicado na tarefa operacional; fontes de consulta e relatórios de referência não são fontes de fatos do relatório.
- Separar fato documentado, relato, indício, inferência/hipótese e lacuna; citar a origem por página/folha quando disponível.
- Não inventar nem completar identificadores, valores, datas, pessoas ou diligências. Dado importante ausente deve ser comunicado ao operador conforme `AGENTS.md`.
- Não atribuir autoria, dolo ou culpa sem base documental expressa. Toda geração de IA é minuta.
- Não enviar autos, transcrições ou dados identificáveis a serviços externos; manutenção e testes de engenharia usam dados fictícios locais.
- Calibração global pode conter somente lições genéricas, sem fatos ou dados de caso, após aprovação humana. Não registrar automaticamente uma minuta ou relatório final como lição.

## Referências de governança

- Decisões de arquitetura: `governanca/decisoes/ADR-001-system-design-cpj.md`.
- Regras operacionais e de sigilo: `AGENTS.md`.
- Contratos, reservas e registro de entregas: `TAREFAS-COMPARTILHADAS.md`.
- Lições genéricas de redação: `calibracao/licoes-aprendidas.md`.
