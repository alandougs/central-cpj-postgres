# Checkpoint — execução da unificação da Central CPJ (UN10–UN18)

Único checkpoint da execução. Plano: `docs/superpowers/plans/2026-10-16-cpj-unificado.md`. Branch de integração: `codex/unificacao-cpj` (iniciada em `782563a`, de `codex/os-markdown-relatorio-20261014`). Agente: `Claude-unificacao`. Somente dados genéricos/sintéticos neste arquivo.

## Estado atual

| Tarefa | Estado | Commit/SHA | Testes |
|---|---|---|---|
| UN10 | concluída (código/teste); sem migração real | ver `git log` da branch | `teste_recuperacao_un10.py` 5/5; runner `--rapido --incluir` 5/5 suítes, saída 0 |
| UN11 | concluída (integração local; sem merge remoto/produção) | merge `8c9241d` + commit de ajustes (ver `git log`) | AST06 27/27, AST07 13/13, AST08 11/11, regressões abaixo |
| UN12 | concluída com pendência de decisão (identidade/CPF) | `1e65bfd` + este registro | suíte completa 109/112 em `1e65bfd`; 2 falhas explicadas por ambiente e reexecutadas 5/5 e 5/5; 1 suíte falha (decisão); 1 skip |
| UN13 | concluída (somente banco fictício) | ver `git log` | `teste_fluxo_store_un13.py` 15/15; 11 suítes de Plantão/fila/concorrência/consentimento/orçamento com saída 0 |
| UN14 | concluída (somente banco/workspace fictício) | ver `git log` | `teste_fluxo_execucao_un14.py` 15/15; mutações 7/7 mortas pelos testes certos; 25 suítes de regressão com saída 0 (esteira e E2E F03 via runner) |
| UN15 | concluída (API + painel, banco/workspace fictício) | ver `git log` | `teste_fila_unificada_un15.py` 15/15; `teste_fila_unificada_un15_ui.py` 5/5; mutações 7/7 mortas (4 API, 3 tela); regressões AST07–AST15, FP01, RV14, RV20, UN13, UN14, esteira e runner rápido sem queda |
| UN16–UN18 | pendentes | — | — |

**Próximo comando seguro:** `python ferramentas/fila-tarefas.py assumir UN16 --agente Claude-unificacao` (distribuição/portáteis/`atualizar-plugin.ps1` devem incluir `fluxo_execucao.py`, `fila-unificada.js` e o CSS; mapear as issues #4–#17).
**Autorização pendente:** merge em `main`, troca da branch padrão e instalação/migração operacional (liberação final em UN18). Nada disso foi feito.
**Processos de teste ativos:** nenhum.

## UN10 — base e inventário (16/10/2026)

Interpretador: `C:\CPJ - TRABALHO\.venv\Scripts\python.exe` (Python 3.12.14). `fetch --all` feito; árvore principal limpa no início.

Remoto (heads): `main` f56653c · `master` 7e537c4 · `codex/os-markdown-relatorio-20261014` (PR18) 782563a · `codex/astra-evolucao-20261014` (PR19) f981f90 · `codex/final-sync-20261010`, `consolidacao-2026-10-01`, `codex/revisao-bugs-2026-10-04` (ancestrais da base: zero commits exclusivos) · `rodada-enxuta-core` 90dbdc8 e `copilot/revise-entire-code` (= master) · `revisao-dev-senior-2026-10-09` 8d8ac0e.

Contagem de commits exclusivos em relação à base `782563a` (história, não funcionalidades):

| Ref | Exclusivos do ref | Exclusivos da base |
|---|---|---|
| `origin/main` | 0 | 10 |
| `origin/master` | 12 | 29 |
| `origin/codex/astra-evolucao-20261014` | 11 | 6 |
| `origin/rodada-enxuta-core` | 11 | 29 |
| `origin/revisao-dev-senior-2026-10-09` | 13 | 29 |

Exclusivos de `master` (12): migração Docker/PostgreSQL (stack Docker, adaptador e migração de documentos textuais, login antes do cadastro, modelo de caso no container, teste de leitura SSD) e a "rodada enxuta do core" com a correção dos quatro P1 do PR #1. **Pendente UN11:** decidir por comparação semântica o que da trilha Docker/PostgreSQL entra; o contrato vigente é Python/Flask/SQLite, sem novo banco.

Worktrees Codex locais com um commit cada ainda não integrado à base: `codex/astra-editor-20261014` (`6436719` editor/rascunhos/DOCX), `codex/docx-fls-assinatura-20261014` (`f941acb` fls./assinatura), `codex/fila-progresso-20261014` (`0e64fd6` atividade/previsão da fila). Estão fora desta branch; confirmar em UN11 se já constam em PR19 (o PR19 lista "protege rascunhos"/FP01) antes de qualquer decisão. Nenhum foi alterado.

Cópia recuperável do código: `git bundle --all` (verificado) em `C:\CPJ - TRABALHO\.claude\recuperacao\codigo-pre-unificacao-20261016.bundle` — local, ignorado pelo Git.

## UN10 — defeito do mecanismo legado e correção

Ensaio com fixture fictícia (WAL aberto) sobre `ferramentas/backup.ps1` + `restaurar.ps1`:

1. Restaurar por cima de um workspace com dados posteriores **sobrescreve** arquivo mais novo com a versão do backup (arquivo alterado após o backup voltou à versão antiga) e **perdeu uma linha** do banco criada depois do backup (201 → 200). Contraria "nunca restaurar cegamente sobre dados criados depois do backup".
2. `restaurar.ps1` só restaura no próprio workspace do script e exige `producao\` existente (falha com código 1 em destino novo sem a pasta).
3. Copia `-wal`/`-shm` por robocopy, não por snapshot atômico; não há manifesto/hash nem verificação de integridade.

Correção: novo `ferramentas/backup_consistente.py` (arquivo reservado em UN10) — snapshot SQLite pela API de backup (fonte aberta `mode=ro`, WAL incluso, sem copiar `-wal/-shm`), manifesto SHA-256, backup sempre em pasta nova, verificação antes de restaurar, restauração em diretório escolhido sem sobrescrever divergentes (versão do backup vai para `_restauracao/<id>/` e o conflito é informado). Testes: `plugin/investigacao-cpj/app/testes/teste_recuperacao_un10.py` (RED confirmado: módulo ausente; GREEN após a implementação).

Os scripts legados `backup.ps1`/`restaurar.ps1` e `teste_backup_antigravity.py` **não foram alterados** (o teste legado exige sobrescrita; mudar exige decisão sobre o requisito). **Risco aberto:** `restaurar.ps1` continua destrutivo sobre workspace vivo. Regra para UN18: usar somente `backup_consistente.py`; sugerir ao operador aposentar ou proteger o `.ps1` (decisão dele; não feito para não ultrapassar o escopo).

## Pré-condições da liberação operacional (UN18) — registradas, nada executado

- Destino local explícito e espaço livre suficiente (somar `casos`, `config`, `producao` etc. + margem).
- Admissões interrompidas de forma coordenada; trabalhos em andamento terminados ou reconciliados (sem processo escrevendo durante a transição).
- Backup via `backup_consistente.py backup`, `verificar` e restauração ensaiada em diretório separado antes de migrar.
- Operar a Central de produção apenas após liberação final do operador. Nesta etapa a Central de produção não foi parada nem tocada.

## Limites e skips desta etapa

Nenhum skip na UN10. Não coberto: restauração sobre Central em execução real, volumes grandes, permissões/ACL do Windows em destino de rede.

## UN11 — integração das melhorias (16/10/2026)

Integrado `origin/codex/astra-evolucao-20261014` (f981f90) à branch (base PR18 + UN10) em `8c9241d`. PR18 já era ancestral. Histórias: `master` **não tem ancestral comum** com esta linha (merge-base inexistente), portanto não foi feito merge dela; a comparação foi por árvore.

Decisões de conflito:

| Arquivo | Decisão |
|---|---|
| `PRD.md`, `TAREFAS-COMPARTILHADAS.md` | União dos dois lados, sem duplicar parágrafos idênticos (FP01 aparecia nos dois). Linha "Última atualização" recomposta. |
| `app/static/index.html` | Base = versão modular da ASTRA (CSS/JS externos). Reaplicado o que só o PR18 tinha: regra `caso-entregue` (central.css), abas Correlações/Mapa na Pesquisa e botões no grafo, contêineres `m-correlacoes`/`m-mapa`, cartão "Relatório de O.S. cumpridas" + seu JS (`estatisticas.js`), classe `caso-entregue` na linha (`casos.js`), `motivo` na pendência (`casos.js`), script `inteligencia-mapa.js` por último. `fila-progresso.js` idêntico nos dois lados. |

Rulings:
- Ruling: `inteligencia-mapa.js` carregado após `bootstrap.js` (mesma posição relativa que o PR18 tinha após `iniciar()`) — custo se errado: mapa/correlações sem handlers; coberto por `teste_correlacoes_mapa_etapa1.py` (passou).
- Ruling: comentário "Projeção Equiretangular" → "Projeção Plate Carrée" em `inteligencia-mapa.js`, porque `teste_interface_f01` (proibição de frameworks) casa a substring "angular" e agora a verificação expande os scripts. Preferida a ajuste do comentário a enfraquecer o teste. Custo: nenhum funcional.
- Ruling: `teste_astra_ast16.py` passou a esperar `inteligencia-mapa.js?v=ibge5570` ao final da lista; mantida a verificação de ordem, HTTP 200 e MIME. Requisito vigente (GEO01) exige o script.
- Ruling: exclusivos de `master` — (a) pilha Docker/PostgreSQL já presente em `legado/postgres-docker` (renomeações idênticas, R100): nada a integrar, contrato vigente é SQLite; (b) `teste_revisao_pr1_f12.py` (correções P1 do PR #1) passa na integração; (c) `ferramentas/tessdata/*.traineddata` só existem em `master` e são ignorados pelo `.gitignore` desta linha: não incorporados; (d) demais diferenças de texto são versões antigas superseded (master é de 28/09). Custo se errado: perder uma correção de master que não tenha teste — mitigação: suíte completa em UN12.
- Nenhum teste foi removido ou renomeado pela integração (verificado: `git diff --name-status`; zero `D`). 16 testes existentes foram adaptados pela ASTRA (leitor `fonte_interface.py`, fls., sem quebra forçada antes da assinatura, salvar sem DOCX); lidos, mantêm as asserções semânticas.

Reprodução do defeito de perda de vínculo manual (fixture fictícia, mesmo script nas duas revisões): base `782563a` → **0** vínculos após `indexar.py --tudo`; integração → **1** (vínculo preservado na fonte autoritativa de eventos). Script descartável no diretório temporário da sessão; AST06/07/08 aprovados (27, 13, 11 testes).

Regressões executadas na integração (saída 0 salvo indicado): AR01, OS-markdown, pendências OCR, OCR indisponível, correlações/mapa, Explorer (dados e UI), FP01, RP01, visualizador de relatórios, fila de O.S. e tarefas, AST05/09/11/12/13/14/15, interface_claude, interface_f01, minuta_campos, painel_plantao, segurança_codex, DOCX F04 (via runner).
**Falhas conhecidas, tratadas em UN12 (não ocultas):** `teste_casos_status_visual_codex.py` (2 falhas: helper `casoEstaFinalizado`/classe `linha-concluida` — expectativa antiga vs. determinação UX03 "entregue"), `teste_identidade_form_codex.py` (8 subfalhas: cargo/CPF), e dependência ausente `quickjs` em `teste_relatorios_interface_ux01`, `teste_grafo_interface_gf02`, e no teste de `fonte_interface` do AST16 (1 erro), além de modelo DOCX oficial ausente quando o teste é executado direto no worktree (o runner gera o modelo sintético).
Não executado em UN11: suíte completa, navegador (Playwright ausente), OCR com `por` — ficam para UN12.


## UN12 — ambiente reproduzível e suíte completa (17/10/2026)

Ambiente de teste (venv separado, fora do Git): Python 3.12, `quickjs`, Playwright + Edge (`msedge`), Tesseract com `por` (dados em `ferramentas/tessdata`, `TESSDATA_PREFIX`), runner `ferramentas/testar-tudo.py` (sandbox com modelo DOCX sintético). Dados exclusivamente fictícios; nenhum caso real tocado.

Correções por requisito (nenhum teste enfraquecido nem removido): `teste_casos_status_visual_codex.py` reescrito conforme UX03 (somente `entregue` recebe `caso-entregue`; 3 testes) — commit `1e65bfd`.

Suíte completa em `1e65bfd` (worktree sem o brasão ignorado pelo Git): **109/112 suítes aprovadas em 747 s**, saída 1. Falhas e causas:

| Suíte | Causa | Situação |
|---|---|---|
| `teste_astra_ast11_ui.py` (clique na aresta) | `static/brasao-pcsp.png` é ignorado pelo Git (`*.png`); no clone/sandbox dá 404, o texto alternativo estoura o cabeçalho fixo (≈390 px) e o canvas sai da viewport de 720 px. Prova: no baseline ASTRA passa (canvas a 468 px); com o script do mapa e os 2 atalhos de menu o canvas desce 75 px (543 px) e o clique cai fora. | Com o brasão presente o teste **original** passa (runner, 5/5). Teste não alterado. |
| `teste_e2e_f03.py` | O mesmo 404 do brasão (imagem + favicon) = 2 erros de console; o teste exige zero. | Com o brasão presente passa (runner, 5/5). |
| `teste_identidade_form_codex.py` (8 subfalhas) | Seletor de cargo e máscara de CPF no cadastro não existem em nenhuma linha integrada nem em requisito registrado. | **Pendente de decisão do operador**: implementar a funcionalidade ou aposentar o teste. Teste mantido como está. |

Skip (não conta como aprovação): `teste_executores_rv17.py::test_escrita_nao_altera_original_por_alias` — este Windows nega link simbólico (WinError 1314: sem privilégio); hardlink funciona. Cobertura do bloqueio por alias fica não demonstrada nesta máquina.

Consequência para UN17: o CI (clone limpo) não terá `brasao-pcsp.png`; a suíte do CI precisa fornecer um PNG sintético ou o teste precisa tolerar a ausência, sob decisão registrada. Hoje, em clone limpo, F03 e AST11 falham.

Limites: renderização visual do DOCX não verificável (sem Word/LibreOffice); suíte completa não foi repetida após copiar o brasão (nenhuma mudança funcional no código desde `1e65bfd`; reexecutadas só as 2 suítes afetadas).


## UN13 — registro durável de fluxos (17/10/2026)

`app/fluxo_execucao.py` (novo): tabelas `fluxos_migracoes`, `fluxos_execucoes`, `fluxos_etapas` em `config/plantao.sqlite` (mesmo banco; nada de outro servidor de filas). Migração aditiva, idempotente, versionada por tabela própria (não usa `PRAGMA user_version`); cada versão é tudo-ou-nada. Versão otimista por etapa; terminais imutáveis; `aguardando_operador` só sai por `reconciliar`; nova tentativa cria etapa ligada à anterior; precedência de estados na agregação; paginação por cursor com filtro de casos permitidos; `importar_legado` correlaciona `processamento.json` e `pedidos` sem alterar nenhum deles e sem inventar término (pedido pendente continua `na_fila`).

`plantao.py`: única mudança é `Fluxos(ws).migrar()` ao final de `Plantao.__init__` (falha propaga, não é engolida). Assinaturas e comportamento de fila inalterados.

Testes: 15/15 no módulo novo (inclui migração sobre banco legado com pedidos, idempotência, concorrência, importação sem tocar `processamento.json`, instância nova do `Plantao`). Compatibilidade com saída 0: plantão, painel de plantão, concorrência (claude/f10/gemini), orçamento de IA, consentimento (se01/px01), fila de tarefas RV14, evidência RV20, gravação atômica RV19, tarefas C03, FP01.

Limites: nenhum banco real migrado. A migração roda sempre que o `Plantao` é instanciado, então a primeira execução da Central instalada migra o `plantao.sqlite` real — por isso a UN18 exige backup verificado antes. Para a UN16: `fluxo_execucao.py` precisa ir junto na distribuição/portáteis (`agente-plantao.py` importa `plantao`, que agora importa o módulo).


## UN14 — reservas, cancelamento e recuperação (17/10/2026)

Integração aos executores existentes, sem substituí-los e sem mudar assinaturas públicas (`Plantao.reivindicar/concluir/falhar/cancelar/enfileirar`, `comum.enfileirar/processar/retomar_pendentes`). A reserva atômica da IA continua sendo a do Plantão (`BEGIN IMMEDIATE`); o registro de fluxos a espelha.

- `fluxo_execucao.py` (migração v2, aditiva): `fluxos_reservas` (dono + validade por etapa) e `fluxos_intencoes` (chave única por chamada externa, com resultado). Novos: `reservar/renovar/atualizar_reservado` (resultado só é gravado por quem detém reserva válida), `registrar_intencao/registrar_resultado`, `cancelar_execucao` (preserva etapas terminais; pede o cancelamento ao pedido correlacionado), `proximas` (prioridade respeitando dependência), `espelhar_pedido`, `registrar_extracao`, `reconciliar_inicializacao`.
- `plantao.py`: `enfileirar` só despacha se o registro durável aceitar (senão cancela o grupo recém-criado e levanta `RuntimeError`, que as rotas devolvem como 503); `reivindicar` devolve o pedido à fila, sem despachar, se o registro recusar a reserva (motivo em `detalhe`); abandono pelo silêncio do agente **nunca** devolve à fila um pedido com chamada externa sem resultado (vai a `erro` e a etapa a `aguardando_operador`); chamada de API paga grava intenção antes e resultado logo depois (`_chamar_sessao`), e resultado já registrado é reaproveitado sem nova chamada; `como_tarefa` ganhou `execucao_id` (campo opcional, nada removido).
- `rotas/comum.py`: `enfileirar` registra a tentativa de extração (e não despacha se o registro falhar; o trabalho fica `erro` com o motivo); o trabalhador reserva a etapa antes de `processar` e registra o resultado; `retomar_pendentes` importa o legado e reconcilia órfãs antes de reenfileirar (documento `concluido` não é reenfileirado nem reextraído). `rotas/sistema.py` e `rotas/casos.py`: 503 para falha de coordenação e `execucao_id` na resposta.
- `tarefas.py` **não precisou mudar** (cancelamento de pedido já passa por `Plantao.cancelar`).

Inspeção: nenhum caminho novo escreve `caso.json`/`entregue`; `pos_processar` só gera DOCX e reindexa.

Testes (`teste_fluxo_execucao_un14.py`, 15): `test_dois_workers_uma_etapa` (8 threads em barreira + dois agentes), `test_cancelar_impede_proxima`, `test_falha_na_gravacao_nao_despacha`, `test_queda_apos_resposta_nao_repete_api` (provedor falso que conta chamadas: 1 chamada no total), `test_checkpoint_retoma_sem_reextrair_pronto` (subprocesso com a fila real), `test_prioridade_respeita_dependencia`, mais reserva expirada, cancelamento de grupo preservando concluído, reconciliação na inicialização, intenção aberta e resultado reaproveitado. Mutação (7): sem intenção, incerta volta à fila, sem devolução, enfileirar sem abortar, reserva expirada vale, cancelar sem pedido, extração sem reserva — todas mortas pelos testes correspondentes.

Teste UN13 ajustado por requisito novo: `Plantao.enfileirar` agora já correlaciona o pedido; o pedido "legado" do teste de importação passou a ser inserido direto no SQL e foi acrescentado teste de que o pedido novo já nasce correlacionado (cobertura mantida).

Regressões com saída 0: plantão, painel de plantão, concorrência (claude/f10/gemini), orçamento, consentimento (se01 ×2, px01), fila (RV14, RV20, O.S. ×2, FP01), gravação atômica, tarefas C03, executores RV17 (1 skip de link simbólico, ver UN12), gates (v04, v05, RV08, RV18), relatórios RV17; esteira completa e E2E F03/OF03 pelo runner.

Limites e riscos abertos:
- Queda real do processo não foi reproduzida; foi simulada com `BaseException` e com remoção de reservas. Não há promessa de "exatamente uma vez" entre SQLite, arquivos e API externa.
- Espelhamentos terminais (`concluir/falhar/cancelar`) gravam aviso no log se falharem e se realinham no próximo evento ou na inicialização; só `enfileirar` e `reivindicar` bloqueiam o despacho.
- A ação explícita do operador (`reconciliar`) existe no módulo, mas só ganha rota/painel na UN15; depois de reconciliar, o pedido de IA em `erro` precisa ser solicitado de novo (não é reaberto automaticamente).
- Dois registros por O.S. podem coexistir (execução `legado-importado` e `extracao`); a visão agregada por O.S. é tarefa da UN15.
- Reserva de plantão vale 1 h, renovada a cada ≥30 s de progresso; a de extração vale 12 h.
- Concorrência entre processos (duas Centrais no mesmo `plantao.sqlite`) não foi testada.


## UN15 — fila única por O.S. e painel (17/10/2026)

Somente leitura no GET; ações só por clique do operador. Nada grava `caso.json`, nada entrega relatório e nenhuma IA é acionada.

- `fluxo_execucao.py`: `listar(..., estados)` agrega as execuções ativas da O.S. (estado pela precedência falhou > aguardando_operador > em_execução > na_fila; documentos e pendências de todas, com `execucao_id`); `etapas_paginadas` (histórico completo por cursor opaco); `cancelar_execucao` devolve as etapas canceladas; pendência passou a carregar `etapa_versao`.
- `rotas/sistema.py`, contrato `cpj-fluxos/1`: `GET /api/fluxos` (limite 1–100, cursor, `estado=` com validação, 400 para parâmetro inválido), `GET /api/fluxos/<id>` (histórico paginado), `POST /api/fluxos/<id>/cancelar` (dono ou perfil com `trabalho`; exige `versao` inteira; 409 se obsoleta; marca como `cancelado` o trabalho de extração que ainda estava na fila, sem apagar nada), `POST /api/fluxos/<id>/etapas/<etapa>/reconciliar` (perfil `trabalho`; motivo 3–300 caracteres; só `na_fila` ou `cancelada`; não dispara nova chamada). 401 sem sessão, 403 sem `X-CPJ`/perfil, 404 para ID inexistente **ou** de O.S. fora da lista autorizada (sem distinguir), 400 para ID malformado. Perfil sem `trabalho` vê estado e tipo da pendência, mas não o texto operacional/diagnóstico e não recebe ações de reconciliação. `Cache-Control: no-store`.
- `static/js/fila-unificada.js` (módulo UMD, render puro com `esc`; controlador no Início): uma linha por O.S.; barra só se `progresso` for número válido, senão "progresso não informado"; pendências (OCR aguardando/falha) visíveis na linha; "próximas etapas" só nos detalhes; histórico só é pedido quando o operador abre `<details>`, com "Carregar mais"; cancelar (confirmação) e conferir (formulário com motivo). Uma consulta `/api/fluxos` por ciclo de `polling.js` (e uma ao entrar no Início), com guarda de sequência, descarte de resposta atrasada após troca de usuário/aba oculta, aviso de indisponibilidade mantendo os últimos dados e preservação de detalhes abertos, texto digitado e foco ao redesenhar. Filtro "todas / exigem atenção / em andamento" (a lista mostra até 100 O.S. e avisa se houver mais).
- `polling.js`: usa `typeof FilaUnificada` (o teste AST15 roda o arquivo numa VM sem `window`; a primeira versão com `window.` quebrava 3 testes e foi corrigida).

Testes: API 15 (contrato, duas tentativas em uma linha, perfil delegado, 400/401/403/404/409, paginação com histórico antigo, GET sem mutação, legados `/api/tarefas` e `/api/fila` intactos, `caso.json` inalterado); navegador 5 (HTML não executa, ordem das respostas, resposta tardia após troca de usuário, aba oculta sem consulta, falha de rede e recuperação, foco/aberto/texto preservados, cancelar e reconciliar). Mutações: sem restrição de texto operacional, sem checagem de dono, ações a perfil sem permissão, sem marcação do checkpoint; HTML sem escape, sem guarda de ordem, sem restauração do texto digitado — todas mortas pelos testes correspondentes.

Limites e riscos abertos:
- O histórico detalhado é o da execução principal da O.S.; a execução `legado-importado` coexistente aparece apenas agregada na linha (pendências/documentos) e nas ações.
- `reconciliar → na_fila` não reenfileira: a nova solicitação é ação explícita do operador (UN14).
- A etapa `recebimento` ainda não é registrada por ninguém; uma O.S. com todas as demais etapas concluídas continua exibindo "próximas etapas".
- Navegador testado só com Edge (Playwright); nenhuma verificação visual por captura (layout apenas por CSS reaproveitado).
- A abertura do Início faz uma consulta extra de fluxos (além da do ciclo); duas consultas simultâneas são unificadas por `lerAtualizacao`.
- Teste de navegador não prova comportamento com milhares de O.S.; o limite é 100 por consulta.
