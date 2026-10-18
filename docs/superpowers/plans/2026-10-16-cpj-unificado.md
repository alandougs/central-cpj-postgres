# Central CPJ unificada — plano de execução

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Sem essa skill, execute a mesma sequência e seus gates diretamente. Método escolhido: um agente responsável, execução sequencial; subagentes somente para testes/logs extensos conforme AGENTS.md.

**Goal:** consolidar a Central em uma versão oficial, corrigir as falhas verificadas e oferecer acompanhamento durável por O.S., com dados preservados, testes reproduzíveis e GitHub sincronizado.

**Architecture:** evoluir o projeto atual em Python/Flask/SQLite; integrar as correções ASTRA e as mudanças recentes antes de desenvolver a fila comum. Preservar `caso.json`, checkpoints de `processamento.json` e a fila SQLite, acrescentando correlação durável de execução e etapas. Uma interface por O.S., sem substituir os executores nem criar outro produto.

**Tech Stack:** Python 3.12, Flask, SQLite, JavaScript/CSS locais, ferramentas DOCX/OCR existentes; Node/Playwright/QuickJS somente quando necessários aos testes já adotados, sem requisito novo de Node em produção.

**Spec:** `docs/superpowers/specs/2026-10-16-cpj-unificado-design.md` — desenho aprovado pelo operador em 16/10/2026.

**Estado:** plano registrado para outro agente. Nenhuma etapa de implementação abaixo foi executada na elaboração deste documento. Publicação destes documentos não equivale à aprovação de merge ou instalação.

## Global Constraints

- Seguir `AGENTS.md`, `docs/ESPINHA-DORSAL.md`, PRD e reservas da fila; respeitar trabalho de outros agentes.
- Uma versão oficial em `main` depois de validada; não apagar branches antigas, fazer force-push, reset destrutivo ou limpeza indiscriminada.
- Python, Flask e SQLite; dados e inferência conforme consentimentos existentes; não ativar provedores nem usar autos reais nos testes.
- `caso.json` permanece fonte oficial; RAG é derivado; manter originais, checkpoints, vínculos manuais, revisão e histórico.
- `config/plantao.sqlite` é o banco da coordenação; não introduzir outro servidor de filas nem banco concorrente.
- Conclusão técnica não dá baixa automaticamente. Progresso sem base mensurável indica atividade, não percentual inventado.
- Migração versionada, idempotente e precedida de cópia local consistente; restauração testada antes de atualizar estado operacional.
- Desempenho: mesma máquina/navegador/carga, pelo menos cinco repetições após aquecimento, mediana e dispersão; regressão reproduzível acima de 10% exige investigação.
- Registrar falhas, skips e limites; zero falhas ocultadas. Mudança de expectativa de teste precisa de requisito vigente e cobertura equivalente.
- Somente código, documentação genérica e fixtures sintéticas no GitHub. Não publicar nomes/identificadores reais nem hashes de evidências operacionais.

## Review Focus

1. Queda depois de uma chamada externa e antes do registro do resultado: não cobrar/executar novamente sem reconciliação (UN14).
2. Dois pedidos simultâneos ou dois agentes reservando a mesma etapa: uma execução efetiva e nenhuma perda de estado (UN13/UN14).
3. O.S. com vários documentos, um sem OCR e histórico com mais de 24 horas: pendência preservada e visível na mesma O.S. (UN13/UN15).
4. Migração interrompida, SQLite com WAL e novos dados após atualização: recuperação consistente sem sobrescrever trabalho posterior (UN10/UN13/UN18).
5. Resposta atrasada, troca de usuário/perfil e textos contendo HTML: nenhuma troca de O.S., vazamento ou injeção na interface (UN15).

## Base conhecida e descoberta obrigatória

Código auditado: `d13db2871ac853c4e73c75ba33b505eae74d8eb2`; documentação posterior: `3ffed1647562864e26f2100d77c899ec4309e556`. PR18: `codex/os-markdown-relatorio-20261014`; PR19: `codex/astra-evolucao-20261014`, último SHA observado `f981f90929d56b2221d26302d9f3e602c349333c`. Repositório: `alandougs/central-cpj-postgres`.

Esses SHAs são evidência, não licença para ignorar commits novos. `fetch`, conferir PRs e obter a revisão mais recente que contém este plano antes de executar. Auditoria: 79/91 suítes passaram; workspace passou em repetição isolada. O número de suítes aumentará com a integração ASTRA. O diagnóstico identifica cada falha, dependência ausente e skip.

## Mapa de arquivos e responsabilidades

Nos itens abaixo, `APP` significa `plugin/investigacao-cpj/app` e `BASE` significa `plugin/investigacao-cpj/skills/base-cpj/scripts`. Expanda esses prefixos ao reservar arquivos. Caminhos são relativos à raiz do checkout de execução, não obrigatoriamente à instalação operacional.

| Arquivos | Responsabilidade |
|---|---|
| `AGENTS.md`, `docs/ESPINHA-DORSAL.md`, `PRD.md`, `TAREFAS-COMPARTILHADAS.md` | Contratos, estado e fila única |
| `APP/rotas/consulta.py`, `BASE/indexar.py`, `BASE/vinculos_manuais.py`, `APP/grafo_evidencias.py` | Integridade do grafo e proveniência; últimos dois entram da ASTRA |
| `APP/fluxo_execucao.py` — novo | Migração e correlação durável de O.S., execução, etapa e tentativa no SQLite existente |
| `APP/plantao.py`, `APP/tarefas.py`, `APP/rotas/comum.py` | Adaptar filas/executores/checkpoints existentes à coordenação comum |
| `APP/rotas/sistema.py`, `APP/rotas/casos.py` | Contratos HTTP e autorização |
| `APP/static/js/fila-unificada.js` — novo; `fila-progresso.js`, `recebimento.js`, `polling.js`, `bootstrap.js`, `index.html` | Painel único; reaproveitar módulos ASTRA após integração |
| `ferramentas/testar-tudo.py`, `requirements-dev.txt`, `APP/testes/` | Ambiente, regressão e cobertura reproduzíveis |
| `ferramentas/atualizar-plugin.ps1`, `exportar-portatil.py`, `configurar-codex.py` | Distribuição e artefatos derivados |
| `.github/workflows/validacao.yml`, `ferramentas/verificar-publicacao.py` — novos | CI e bloqueio de publicação indevida sem executar publicador legado |
| `revisoes/unificacao-execucao.md` — novo durante execução | Checkpoint único: etapa, arquivos, commits, testes, skips, impedimentos, próximo passo |

## Procedimento comum a todas as tarefas

- [ ] Confirmar predecessora concluída e reservar o ID pelo script, com nome da sessão. Registrar dependências e alterações de contrato antes de editar consumidores.
- [ ] Trabalhar em checkout isolado, branch `codex/unificacao-cpj`; se já existir e pertencer à execução, retomar sem reset. Não copiar dados operacionais para esse checkout.
- [ ] Para mudanças de comportamento, escrever primeiro o teste específico, comprovar a falha esperada, implementar o mínimo e comprovar aprovação. Para integração de correção já testada, reproduzir o defeito na base anterior e testar a versão integrada, sem duplicar implementação.
- [ ] Executar os testes específicos em workspace fictício, registrar resultado e revisão no checkpoint. Não rodar teste que fiscaliza mtimes do workspace simultaneamente a gravações nesse workspace.
- [ ] Revisar diff, sigilo e reservas; commit por entrega e push normal da branch. Atualizar PRD e fila sem apagar histórico. Conclusão da tarefa libera arquivos; não significa homologação operacional.

Comando canônico de testes: `rtk proxy <PYTHON_VALIDO> ferramentas/testar-tudo.py --rapido --incluir <teste_arquivo.py>` para seleção isolada; esse modo também roda a seleção rápida. Suíte completa: mesmo comando sem argumentos. No computador auditado, Python válido é `C:\CPJ - TRABALHO\.venv\Scripts\python.exe`; no checkout/CI confirmar interpretador e dependências, sem depender do alias da Microsoft Store. Validar `--help` caso o runner tenha mudado. Retorno esperado: zero e teste solicitado efetivamente executado, com skips discriminados.

## UN10 — Base segura e recuperação verificável

**Arquivos:** criar `revisoes/unificacao-execucao.md`, `APP/testes/teste_recuperacao_un10.py`; examinar scripts existentes de backup e exportação, `APP/tarefas.py` e `teste_backup_antigravity.py`. Nenhum arquivo operacional versionado.

**Interfaces:** consome estado Git e mecanismos existentes de backup/importação. Produz checkpoint com SHAs iniciais, inventário genérico e evidência de restauração sintética. Inventário operacional e backup, quando autorizados na liberação final, ficam somente em armazenamento local controlado.

- [ ] Atualizar referências, inventariar commits exclusivos de main/master/PR18/PR19 e mudanças locais; manter uma cópia recuperável do código. Identificar contribuições exclusivas de master antes de retirar seu papel de branch padrão.
- [ ] Criar `test_restauracao_preserva_fontes_e_estado`: fixture com originais, caso, processamento, banco com WAL, vínculo manual e relatório; restaurar em outro diretório e comparar conteúdo, relações e `PRAGMA integrity_check == 'ok'`.
- [ ] Executar o teste; se o mecanismo existente falhar, registrar o defeito e incluir seu arquivo exato na reserva antes de corrigir. Não simular aprovação.
- [ ] Demonstrar recuperação sem modificar a fonte e sem copiar um SQLite aberto ignorando WAL: usar API SQLite de backup ou parada coordenada. Verificar também o retorno com dados novos preservados em diretório separado.
- [ ] Registrar pré-condições de liberação operacional: destino local explícito, espaço suficiente, interrupção coordenada de admissões, término/reconciliação de trabalhos em andamento e restauração ensaiada. Não parar a Central de produção nesta etapa.

**Saída:** base identificada e ensaio de recuperação aprovado; nenhuma migração real. Falha de recuperação bloqueia as etapas com mudança de estado.

## UN11 — Integração das melhorias e proteção do grafo

**Arquivos:** arquivos dos PR18/PR19; reservar expressamente os caminhos sobrepostos antes do merge local. Foco: `PRD.md`, fila, `APP/static/index.html`, `APP/rotas/consulta.py`, `APP/tarefas.py`, `BASE/indexar.py`, `BASE/vinculos_manuais.py`, `APP/grafo_evidencias.py`, testes AST06/07/08/11/12, AR01, OCR01 e GEO01. Conservar os documentos UN01/UN02.

**Interfaces:** preservar contratos ASTRA de ID manual, caso e versão esperada; exclusão de vínculo documental proibida. APIs atuais de extração/relatório e geração DOCX continuam compatíveis. Não renomear contratos já implementados para adequá-los a uma segunda solução.

- [ ] Partir da revisão atual que contém o plano e integrar ASTRA localmente; conciliar contribuições exclusivas relevantes de master mediante comparação semântica, nunca `ours/theirs` global. Registrar cada decisão de conflito.
- [ ] Demonstrar em fixture a falha anterior de perda na reindexação; executar `teste_astra_ast06_store.py`, `teste_astra_ast07_api.py`, `teste_astra_ast08_index.py` na integração e verificar vínculo manual preservado, exclusão por ID e fontes documentais intactas.
- [ ] Conciliar UI modular ASTRA com OCR01, GEO01, FP01, RP01, AR01 e EX01; verificar inclusão/ordem dos scripts, mensagens de OCR e mapa offline.
- [ ] Conferir testes removidos/renomeados entre branches. Cada exclusão precisa de justificativa e cobertura substituta; especialmente status visual e identidade, que falharam na base auditada.
- [ ] Rodar regressões de O.S./DOCX/editor/grafo/segurança afetadas e registrar o SHA integrado. Não fazer merge remoto nem mudar a instalação.

**Saída:** uma branch integrada, sem perda de mudanças úteis, fonte manual autoritativa preservada e conflitos semânticos resolvidos.

## UN12 — Ambiente e falhas conhecidas

**Arquivos:** `requirements-dev.txt`, `ferramentas/testar-tudo.py`, testes listados no diagnóstico; `APP/testes/fonte_interface.py` da ASTRA, `fixtures_docx.py` e módulos de produto apenas quando o requisito confirmar defeito. Reservar os arquivos específicos antes da correção.

**Interfaces:** runner mantém retorno não zero para falha e explicita capacidades ausentes. Fixtures continuam sintéticas; uso de helpers de leitura da interface considera os módulos JS integrados.

- [ ] Preparar ambiente de teste com requisitos de desenvolvimento, QuickJS, Playwright/navegador e Tesseract com `por`; verificar importações, navegador e lista de idiomas. Se uma plataforma não suportar um requisito, executar a cobertura equivalente em ambiente compatível e registrar a limitação, sem marcar skip como aprovação.
- [ ] Reexecutar as seis suítes antes impedidas por QuickJS e o teste de desempenho/OCR. Corrigir dependência ou comportamento conforme a falha observada.
- [ ] Ajustar expectativas antigas de status somente-entregue, script único, fls. e assinatura aos requisitos vigentes; manter asserts sobre semântica, integridade e layout. Conferir DOCX renderizado com assinatura fictícia, sem quebra/sobreposição indesejada.
- [ ] Para cargo/CPF, confrontar AGENTS, PRD e histórico: se o requisito é vigente, corrigir o formulário com teste; se foi substituído expressamente, atualizar o teste e citar a decisão. Sem evidência, registrar a decisão pendente; não excluir o teste silenciosamente.
- [ ] Executar suíte completa uma vez sobre a integração congelada, sem gravações concorrentes; registrar falhas restantes, skips, contagem real e SHAs. Corrigir causas e repetir só os grupos afetados até nova rodada final.

**Saída:** ambiente reproduzível e falhas conhecidas resolvidas ou explicitamente bloqueadoras. Não usar o placar antigo 79/91 para certificar código novo.

## UN13 — Registro durável do fluxo e migração aditiva

**Arquivos:** criar `APP/fluxo_execucao.py` e `APP/testes/teste_fluxo_store_un13.py`; adaptar `APP/plantao.py` apenas na inicialização/migração e reservar em conjunto.

**Interfaces:** novo `Fluxos(ws: Path)` usa `ws/config/plantao.sqlite`; `migrar() -> None`; `criar(caso: str, solicitante: str, chave: str, prioridade: int = 0) -> dict`; `vincular_etapa(execucao_id: str, etapa: str, origem: str, origem_id: str, documento: str | None = None) -> dict`; `atualizar(etapa_id: str, versao: int, estado: str, progresso: float | None = None, detalhe: str = '') -> dict`; `obter(execucao_id: str) -> dict | None`; `listar(casos_permitidos: list[str], limite: int = 50, cursor: str | None = None) -> dict`. `ConflitoVersao` indica versão obsoleta; `TransicaoInvalida` indica transição proibida.

Decisões de persistência: tabelas aditivas `fluxos_migracoes`, `fluxos_execucoes`, `fluxos_etapas`; não reutilizar `PRAGMA user_version` sem conhecer seu dono. IDs UUID; unicidade `(caso, solicitante, chave)` para criação e `(origem, origem_id)` para vínculo; origem `processamento`, `tarefa` ou `plantao`. Campos de versão/tentativa, criação/atualização e erro duráveis. Prioridade maior primeiro, empate por entrada e ID; depender da elegibilidade da etapa antes de executar. Paginação por cursor opaco dessa ordem.

Estados de coordenação: `na_fila`, `em_execucao`, `aguardando_operador`, `falhou`, `cancelada`, `concluida`. Etapas: `recebimento`, `extracao`, `analise`, `relatorio`, `revisao`. Entrega é lida de `caso.json`, nunca uma escrita automática do registro de fluxo. Nova tentativa preserva tentativa anterior; conclusão exige resultado verificável, não apenas ausência de exceção.

Transições de etapa: `na_fila` → `em_execucao/aguardando_operador/cancelada`; `em_execucao` → `aguardando_operador/falhou/cancelada/concluida`; `aguardando_operador` → `na_fila/cancelada` somente por reconciliação explícita. Estados terminais são imutáveis; retentativa cria outra etapa/tentativa vinculada à anterior. Atualização de progresso no mesmo estado exige versão atual. Para extração, `origem_id` inclui caso, documento e tentativa, evitando colisão entre documentos homônimos; pedidos de plantão usam seu ID único. Os dicionários de escrita retornam ID e versão resultante. A agregação por O.S. escolhe a execução ativa mais recente, preserva acesso às anteriores e mostra todas as pendências bloqueadoras; só informa conclusão do fluxo quando todas as etapas obrigatórias daquela execução estiverem concluídas.

- [ ] Escrever `test_criar_idempotente`, `test_vinculo_unico`, `test_versao_obsoleta_nao_sobrescreve`, `test_migracao_interrompida_reexecutavel` e `test_pendente_antigo_nao_expira`: criar duas vezes retorna mesmo ID; conflito não altera dados; interrupção não perde pedidos antigos; pendência de 48h permanece visível.
- [ ] Comprovar falha antes do módulo; implementar transações curtas, busy timeout e migração idempotente. Duas escritas concorrentes usam conexões independentes em teste.
- [ ] Importar correlação de pedidos/checkpoints existentes sem disparar trabalho nem inventar término. Preservar `processamento.json` como checkpoint da extração; diferenças são reconciliadas por origem/versão e marcadas quando incertas.
- [ ] Garantir que falha de escrita da coordenação impede novo despacho; trabalho já concluído com registro incerto entra em reconciliação. Não fazer dual write silencioso que perde a atualização de um lado.
- [ ] Rodar os testes do módulo e compatibilidade com plantão. Migração ocorre somente em banco fictício nesta etapa.

**Saída:** armazenamento recuperável, idempotente e compatível com estado legado, sem segunda fonte editável do caso.

## UN14 — Encadeamento, reservas, cancelamento e recuperação

**Arquivos:** `APP/plantao.py`, `APP/tarefas.py`, `APP/rotas/comum.py`, `APP/rotas/casos.py`, `APP/rotas/sistema.py`, `APP/fluxo_execucao.py`; criar `APP/testes/teste_fluxo_execucao_un14.py`.

**Interfaces:** preservar assinaturas públicas existentes `Tarefas.nova/at/rodar/enfileirar_ia/cancelar`, `Plantao.reivindicar/concluir/falhar/cancelar`, `comum.enfileirar/processar/atualizar_trabalho/retomar_pendentes`. Acrescentar contexto opcional `execucao_id` sem remover campos antigos; correlacionar IDs retornados com UN13. Reservas IA continuam atômicas em Plantao; extração usa reserva durável por etapa, com proprietário e validade, validada antes de escrita de resultado. Reserva expirada não autoriza repetir resultado externo incerto.

- [ ] Criar `test_dois_workers_uma_etapa`, `test_cancelar_impede_proxima`, `test_falha_na_gravacao_nao_despacha`, `test_queda_apos_resposta_nao_repete_api`, `test_checkpoint_retoma_sem_reextrair_pronto` e `test_prioridade_respeita_dependencia`; usar barreiras de concorrência e provedor falso que conta chamadas.
- [ ] Integrar os hooks sem substituir os executores. Persistir intenção de despacho antes de executar e resultado antes de liberar dependentes; retomar checkpoints válidos de extração.
- [ ] Na inicialização, conciliar tarefas/processamento/pedidos duráveis; tarefa externa incerta vai para `aguardando_operador`, com motivo e ação explícita de reconciliação. Não prometer execução exatamente uma vez entre SQLite, arquivos e API externa.
- [ ] Preservar todos os gates de consentimento, limite, revisão e permissões. Cancelamento de grupo cancela dependentes ainda não executados, preservando resultados já produzidos; nova tentativa tem identidade rastreável.
- [ ] Rodar UN14 e regressões de plantão, concorrência, esteira, consentimento e gates. Inspecionar que geração automática de relatório não promove `entregue`.

**Saída:** execução coordenada com recuperação segura e histórico, mantendo paralelismo permitido entre O.S.

## UN15 — API e painel único por O.S.

**Arquivos:** `APP/rotas/sistema.py`, `APP/rotas/casos.py`, `APP/static/index.html`, `APP/static/js/fila-unificada.js` novo, `recebimento.js`, `fila-progresso.js`, `polling.js`, `bootstrap.js`; criar `APP/testes/teste_fila_unificada_un15.py`.

**Interfaces:** adicionar `GET /api/fluxos?limite=50&cursor=...&estado=...` com `{schema:'cpj-fluxos/1', itens:[], proximo_cursor:null|string}`. Item por caso: `{caso, execucao_id, versao, estado, etapa, progresso, atualizado_em, pendencias, documentos, acoes}`. `progresso` é número entre 0 e 100 ou null; texto operacional é mínimo e autorizado por perfil. Detalhe `GET /api/fluxos/<execucao_id>` fornece histórico paginado de etapas/tentativas. Valores de limite aceitos 1–100, padrão 50; inválidos retornam 400.

`POST /api/fluxos/<execucao_id>/cancelar` recebe `{versao}`; 409 para versão divergente; usa mesma autorização/cancelamento existente e exige `X-CPJ: 1`. Retentativa/reconciliação chama ação existente somente após verificar resultado anterior; não disparar nova chamada ao renderizar a página. Listagem e detalhe filtram por casos autorizados no servidor. APIs `/api/tarefas` e `/api/fila` mantêm contrato legado durante transição e testes; painel novo usa uma consulta coordenada de fluxos por ciclo, sem sondagem duplicada por widget.

- [ ] Testar uma O.S. com dois documentos e duas tentativas: uma linha principal, detalhes completos, OCR pendente claramente visível, sem entrega automática.
- [ ] Testar caso inacessível, ID inválido, CSRF, cancelamento obsoleto, cursor inválido, histórico antigo e textos com HTML; nenhum dado de caso alheio ou execução de markup.
- [ ] Implementar API e consumidor juntos; reaproveitar polling adaptativo ASTRA. Preservar foco, seleção e abertura da O.S. durante atualizações; estados de erro e vazio explícitos.
- [ ] No navegador, testar resposta atrasada após trocar O.S./usuário, atualização fora de ordem, aba oculta, perda/reconexão de rede e progresso desconhecido; resultado antigo não substitui contexto atual.
- [ ] Rodar UN15, FP01, testes AST15 e fluxo E2E fictício. Screenshot de teste deve conter só dados sintéticos.

**Saída:** uma experiência por O.S., com acompanhamento confiável e compatibilidade temporária dos consumidores antigos.

## UN16 — Distribuição fiel à fonte e fila de desenvolvimento

**Arquivos:** `ferramentas/atualizar-plugin.ps1`, `ferramentas/exportar-portatil.py`, `ferramentas/configurar-codex.py`, `portatil/`, adaptadores gerados, `TAREFAS-COMPARTILHADAS.md`, PRD; criar `APP/testes/teste_distribuicao_un16.py`.

**Interfaces:** acrescentar verificação sem escrita ao exportador (`--verificar`, saída 0 quando confere, 1 quando diverge, ignorando somente timestamp de geração). Preparação de pacote separada de instalação, manifestando revisão e hashes dos arquivos genéricos. O atualizador não instala só para testar a lista de extensões.

- [ ] Testar pacote com `.py/.md/.json/.html/.png/.js/.css` usados pela fonte integrada, todos os recursos locais referenciados e arquivos sensíveis fictícios que devem ser excluídos. Extensões adicionais apenas quando referenciadas e justificadas.
- [ ] Corrigir whitelist e conferir manifesto/referências; não empacotar assinatura real, configurações locais ou modelo operacional.
- [ ] Regenerar portáteis/adaptadores a partir da fonte atual; verificar regras de fls., assinatura, O.S. e relatório. Testar entrada pessoal Codex em destino temporário; instalação pessoal real fica na liberação operacional.
- [ ] Relacionar IDs locais às issues #4–#17 e PR18/19 no checkpoint. Registrar implementado/testado/integrado/homologado como marcos distintos, preservando estados aceitos pelo script de reservas. Não encerrar issue só porque sua tarefa local está concluída.
- [ ] Executar teste de distribuição e verificadores. Publicar apenas a fonte e derivados genéricos revisados.

**Saída:** distribuição completa e conferível, sem backlog paralelo nem instalação divergente oculta.

## UN17 — CI, revisão completa e desempenho

**Arquivos:** `.github/workflows/validacao.yml`, `ferramentas/verificar-publicacao.py`, `ferramentas/testar-tudo.py`, `APP/testes/teste_publicacao_un17.py`, `revisoes/unificacao-execucao.md`; usar harnesses ASTRA de navegador/desempenho existentes.

**Interfaces:** verificador local somente leitura, `python ferramentas/verificar-publicacao.py --staged` ou `--ref HEAD`; 0 aprovado, 1 achado proibido, 2 erro de verificação. Inspecionar caminhos e blobs da seleção explícita; reportar caminho/regra, nunca imprimir segredo. CI valida revisão candidata e arquivos gerados, sem chamar publicador legado ou acessar ambiente operacional.

- [ ] Testar com segredos fictícios, `.env` realista fictício, caminhos de casos/config/bancos/assinaturas e `.env.example` genérico permitido; varredura não deve alterar arquivos.
- [ ] Configurar workflow com dependências e ferramentas disponíveis: suíte Python, navegador, OCR português, verificação de distribuição e sigilo. Conferir versões/documentação oficial das actions durante execução, fixar revisões e usar permissões mínimas de leitura.
- [ ] Separar regressão determinística de medição temporal dependente da máquina; CI não pode aprovar cobertura crítica ignorada. Garantir um ambiente compatível para testes de links e navegador; registrar capacidades por job.
- [ ] Congelar a revisão, rodar suíte completa e E2E sintético: recebimento, OCR, O.S., análise com executor falso, relatório, revisão, interrupção/retomada e entrega somente por ação explícita. Não escrever documentação durante testes que fiscalizam mtimes; registrar resultados depois.
- [ ] Medir abertura, consulta de tarefas, navegação durante OCR e memória servidor/navegador; cinco repetições após aquecimento, baseline e candidato com mesma massa/configuração. Investigar regressões reproduzíveis >10%, sem esconder dispersão ou custo de memória compartilhada.
- [ ] Revisar diff completo e matriz de contratos da espinha dorsal. Corrigir achados, repetir testes afetados e repetir rodada final quando houver mudanças funcionais posteriores. Registrar revisão exata e CI correspondente.

**Saída:** candidato revisado, CI verde, cobertura crítica executada e desempenho demonstrado; falha ou skip crítico bloqueia liberação.

## UN18 — Sincronização final, liberação e retomada segura

**Arquivos:** checkpoint, PRD, fila e metadados do GitHub; artefatos operacionais somente locais.

**Interfaces:** produzir revisão candidata com pacote genérico identificado, relatório de testes, instrução de atualização e retorno. Operador recebe uma decisão concreta; não pedir aprovação de um plano ainda sem implementação.

- [ ] Fazer push da branch de integração sem força, abrir/atualizar PR para main e associar os PRs anteriores. Se a ferramenta Codex estiver disponível, anexar o PR ao chat. Comparar HEAD local com SHA remoto e conferir CI nessa revisão.
- [ ] Apresentar ao operador: revisão, testes/skips, desempenho, distribuição, plano de backup/restauração, mudanças de estado e riscos residuais. Solicitar somente a liberação final que ainda não tenha sido explicitamente concedida: merge, default branch e instalação/migração operacional.
- [ ] Após liberação, fazer backup consistente local e validar restauração antes de migrar; não operar com processos ativos escrevendo durante a transição. Capturar manifesto local de originais e fontes autoritativas sem enviar ao GitHub.
- [ ] Integrar em main conforme política do repositório, sem reescrita de história; tornar main padrão. Verificar proteção com acesso suficiente e habilitar checks obrigatórios se permitido pela conta; 403 significa não verificado, não protegido. Não apagar master/branches para simular unificação.
- [ ] Instalar exatamente a revisão aprovada, migrar aditivamente e fazer smoke local que não executa IA nem baixa O.S. Conferir integridade, contagens e hashes de originais/fontes; mudanças esperadas de esquema têm evidência própria.
- [ ] Se falhar, suspender novas admissões, preservar estado posterior e reconciliar antes de restaurar; voltar código somente se compatível com esquema. Não substituir banco vivo por backup antigo nem apagar arquivos novos.
- [ ] Confirmar revisão instalada/local/remota e testes após o merge na revisão efetiva; atualizar issues/PRs/tarefas segundo evidência e homologação, sem fechar trabalho residual. Deixar checkpoint preciso se alguma etapa depender de permissão/capacidade externa.

**Saída:** uma versão oficial e operacional validada, fontes preservadas e sincronização comprovada. Se a liberação final não vier, a entrega correta é candidato testado e sincronizado, com implantação explicitamente pendente.

## Critério de encerramento e retomada

O agente só declara unificação concluída quando os dez critérios do desenho estiverem comprovados. A matriz de cobertura é: versão oficial UN11/18; fila dev UN16; painel UN15; recuperação UN10/13/14; grafo UN11; testes UN12/17; CI UN17; distribuição UN16; desempenho UN17; backup UN10/18.

Ao parar: registrar no checkpoint último commit, tarefas concluídas, falhas/skips, processos de teste ativos, arquivos alterados, próximo comando seguro e autorização pendente. Liberar reserva pelo script quando não estiver trabalhando. O agente seguinte lê esse checkpoint e retoma; não repete tarefas concluídas sem mudança de base ou evidência que justifique.
