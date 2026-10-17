# Central CPJ unificada — desenho para revisão

Data: 16/10/2026. Tarefa: UN01. Estado: desenho aprovado pelo operador em 16/10/2026; implementação ainda não iniciada. Plano e prompt registrados pela UN02 em `docs/superpowers/plans/2026-10-16-cpj-unificado.md` e `docs/superpowers/plans/2026-10-16-cpj-unificado-prompt.md`; o operador determinou que outro agente execute mediante pedido posterior.

## Resultado solicitado

O operador quer um único projeto, leve, rápido e fácil de usar. Confirmou que a unificação deve abranger desenvolvimento e painel de processamento. Deve ser possível abrir a Central, localizar uma O.S. e acompanhar seu caminho até o relatório revisado, sem escolher entre versões concorrentes do sistema.

O projeto continuará no repositório existente e com Python, Flask e SQLite. A organização interna em arquivos permanece útil à manutenção; para o operador haverá uma Central, uma versão oficial e um fluxo de trabalho reconhecível.

## Evidências e alternativas

A branch atual está sincronizada com seu remoto, mas não concentra toda a evolução. Há dois PRs abertos para `main` (#18 e #19), enquanto o padrão remoto continua em `master`. A integração simulada entre a branch atual e ASTRA conflita em `PRD.md`, `TAREFAS-COMPARTILHADAS.md` e `app/static/index.html`. O diagnóstico detalhado e os limites dos testes estão em `revisoes/diagnostico-unificacao-2026-10-16.md`.

Alternativas consideradas:

| Abordagem | Vantagem | Custo ou limite |
|---|---|---|
| Somente juntar as branches | Recupera melhorias já feitas com menor alteração | Mantém estados e acompanhamento do processamento fragmentados |
| Consolidar código e unificar o acompanhamento sobre a base atual — escolhida | Atende às duas partes do pedido e preserva o funcionamento local | Exige conciliar contratos, persistência e testes de recuperação |
| Reescrever com outra infraestrutura | Permite redesenho total | Aumenta migração, dependências e risco sem evidência de necessidade |

## Uma versão oficial

`main` será a referência oficial após a integração validada das mudanças úteis dos PRs #18 e #19. A branch `master` deixará de ser a entrada padrão do repositório. Branches de trabalho serão temporárias; seus nomes não representarão produtos separados para o operador.

A integração preservará as melhorias recentes de O.S., relatórios, OCR e mapa, assim como as correções ASTRA de persistência, fontes e editor. Não basta resolver conflitos textuais: a compatibilidade das rotas, indexador e consumidores será verificada conjuntamente. A atualização do padrão remoto ocorre somente após a versão integrada estar validada. Branches antigas não serão apagadas automaticamente.

O instalador, os procedimentos portáteis e os adaptadores serão derivados da mesma versão do código. A distribuição deve incluir os recursos estáticos usados pela aplicação, inclusive JavaScript e CSS quando presentes. O pacote precisa declarar a revisão distribuída e ser conferido contra seus arquivos de origem, sem incorporar dados locais.

## Uma fila de desenvolvimento

`TAREFAS-COMPARTILHADAS.md` e seu script existente continuarão sendo a fonte de prioridade, reserva e responsabilidade. Issues e PRs do GitHub referenciarão os mesmos IDs; não haverá uma segunda lista independente de prioridades.

O estado da entrega distinguirá: implementado, validado, integrado e homologado pelo operador. A conclusão de uma reserva de arquivos não significará automaticamente que a funcionalidade está na versão oficial ou que passou pela homologação. Esses marcos serão registrados no acompanhamento da entrega sem quebrar os estados usados pelo script de reservas.

As issues ASTRA existentes serão reconciliadas com suas tarefas locais e evidências antes de qualquer fechamento. Problemas de produto descobertos durante a auditoria entram nessa mesma fila, com prioridade e dependências claras.

## Um acompanhamento por O.S.

O painel apresentará uma linha principal por O.S., com a execução atual e histórico acessível. Dentro dela, a sequência será visível: recebimento → extração/OCR → análise → relatório → revisão → entrega pelo operador. Documentos, blocos e tentativas serão detalhes da mesma execução, evitando linhas concorrentes que pareçam trabalhos diferentes.

Cada linha mostrará etapa atual, estado, atividade recente, progresso conhecido, pendência e ação disponível. Um clique abrirá a O.S. no ponto correspondente. Progresso sem base mensurável será apresentado como atividade em andamento; estimativas indicarão que são estimativas. A conclusão técnica do relatório não dará baixa na O.S. automaticamente.

O painel poderá filtrar pendentes, em execução, aguardando operador, falhas e concluídos. A ordem seguirá a prioridade explícita e, no empate, a entrada na fila; dependências impedem execução antecipada. Paralelismo seguro entre casos poderá continuar: fila única significa coordenação e visibilidade únicas, sem obrigar toda a máquina a executar apenas uma tarefa por vez.

## Persistência e recuperação

Hoje `tarefas.py` concatena tarefas mantidas em memória com pedidos persistidos pelo `Plantao`. O desenho aproveita a fila SQLite existente em `config/plantao.sqlite` e acrescenta o vínculo durável de execução, etapa e documento necessário para o acompanhamento comum. Não introduz um novo servidor de filas nem outro banco concorrente.

`caso.json` permanece a fonte dos dados e do estado oficial do caso. O banco do plantão registra execução, dependências, tentativas e atividade. O RAG permanece derivado. O estado mostrado na tela será obtido dessas fontes, com regras explícitas para divergência e interrupção, sem uma cópia independente editável pelo navegador.

Contratos obrigatórios:

- IDs estáveis ligam a O.S., execução, etapa e tentativa; repetição de requisição não cria a mesma execução duas vezes.
- Reserva atômica impede dois executores de assumir a mesma etapa. Dependências, limites e consentimentos existentes continuam sendo conferidos.
- Reinício preserva histórico e distingue tarefa recuperável de resultado incerto. Não repete automaticamente chamada paga ou operação com efeito externo sem reconciliação do resultado anterior.
- Cancelamento interrompe o encadeamento posterior e mantém a explicação e o histórico; nova tentativa é rastreável.
- Falta de OCR, O.S. ausente, revisão reprovada e bloqueio de provedor aparecem como pendências específicas, sem status de sucesso enganoso.
- Migração do SQLite é versionada, idempotente e precedida de cópia local; recuperação e compatibilidade com trabalhos existentes são verificadas em cópia fictícia antes da atualização operacional.

Os detalhes do esquema e da transição de `/api/tarefas` serão definidos no plano de implementação, com atualização conjunta do consumidor e testes de compatibilidade. O painel atual continuará consumindo o contrato existente até a transição validada.

## Leveza e velocidade

Primeiro serão reaproveitadas as melhorias já desenvolvidas na ASTRA, incluindo atualização adaptativa da tela, paginação e separação de recursos estáticos. O acompanhamento terá uma consulta coordenada de estado por ciclo da tela, sem sondagens duplicadas por componente. Execução pesada continua fora do atendimento das requisições web.

A comparação usará a mesma máquina, navegador, conjunto fictício e carga: abertura da Central, consulta de tarefas, resposta da navegação durante OCR, memória do servidor e navegador. Serão registradas ao menos cinco repetições após aquecimento, mediana e dispersão. Diferenças pequenas não serão anunciadas como ganho; regressão reproduzível acima de 10% exige investigação antes da entrega. Testes de tempo dependentes do hardware serão separados dos testes determinísticos de CI.

## Integridade e sigilo

A primeira integração funcional protege vínculos manuais contra reindexação e impede que exclusão manual apague relações documentais. As correções existentes na ASTRA serão verificadas por testes de preservação e exclusão por identificador.

Casos, bases de consulta, transcrições, assinaturas, credenciais, configurações e bancos operacionais continuam locais. Testes e CI usam apenas dados sintéticos. O pacote de distribuição contém código e modelos sintéticos de teste quando necessários, nunca o modelo de produção com assinatura. A atualização não altera `00-originais`, não ativa provedores e não registra entregas.

## Critérios de aceitação

1. Uma versão integrada em `main`, padrão remoto alinhado e revisão instalada identificável; nenhuma mudança útil perdida dos dois PRs.
2. Uma fila de desenvolvimento com IDs vinculados às issues e PRs; marcos de implementação, validação, integração e homologação verificáveis.
3. Uma linha por O.S. permite acompanhar documentos e etapas até relatório/revisão; entrega continua ação do operador.
4. Reinício, cancelamento, nova tentativa, reservas concorrentes e dependências testados sem duplicação de execução nem perda silenciosa de histórico.
5. Vínculo manual fictício sobrevive à reindexação; exclusão manual não apaga evidência documental; controle de versão do editor preservado.
6. Suíte completa aprovada no ambiente declarado. Dependência ausente ou teste ignorado aparece explicitamente e não conta como aprovação. Navegador testado no fluxo fictício de ponta a ponta.
7. CI executa verificações de sigilo, testes automatizados e conferência dos artefatos gerados em cada PR. Regras de merge serão verificadas com acesso suficiente antes de declarar proteção ativa.
8. Portáteis e adaptadores conferem com a fonte; instalador inclui todos os recursos necessários; teste local de distribuição passa.
9. Medições de desempenho reproduzíveis e sem regressão relevante nos cenários definidos. Ganhos anunciados somente quando medidos.
10. Backup e restauração demonstrados em ambiente de teste antes de migrar o estado operacional.

## Sequência de entrega e limites

O plano posterior deve ordenar: integrar proteções de dados e mudanças existentes; corrigir a base de testes; reconciliar fila e distribuição; implementar acompanhamento persistente e interface; medir, homologar e tornar a versão validada oficial. Cada etapa terá evidência e possibilidade de retorno sem descartar dados produzidos após atualização.

Este documento não autoriza reescrita completa, troca de banco, novos serviços, migração de autos para nuvem ou mudanças em funcionalidades de investigação alheias ao pedido. Nesta tarefa foram feitos diagnóstico e desenho; alterações de produto, merge e instalação permanecem por executar.
