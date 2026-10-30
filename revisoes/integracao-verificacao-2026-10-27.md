# IV01 — verificação das falhas de integração

27/10/2026 — Codex-IV01 (Sol, substituindo executor indisponível). Escopo: duas suites do candidato isolado `F:/CPJ-BACKUPS/sync-github-20261027-023944/candidato`. A reserva IV01 existente no workspace original foi preservada. Nenhuma implantação ou publicação.

## Diagnóstico e correções

`teste_astra_ast06_store.py`: RED com 27 testes, três erros porque a fixture chamava exportação sem senha e uma falha porque usava o contrato antigo de backup/restauração. O contrato vigente SEC23 exige CPJENC autenticado; SEC25 exige origem explícita, declarações offline/mídia e restauração em destino novo. A fixture agora exporta/importa com senha fictícia, inspeciona o ZIP interno pelo leitor autenticado real e executa os wrappers PowerShell reais numa instalação TEMP com dependências genéricas. Preservadas as verificações de reimportação, conflito, eventos, versões, tombstones e anotações órfãs. A restauração reconstrói o índice em destino novo e confirma também que uma versão posterior na fonte não foi sobrescrita.

`teste_apple_ui_ap39.py`: RED com cinco testes, duas falhas. O contraste foi medido durante a transição de cores de 120 ms após trocar abas (Casos: 2,7627:1), e a medida de rótulo SVG ocorreu durante a substituição dos nós pelo ResizeObserver após resize (NaN). O teste aguarda as animações em andamento e dois frames de layout antes das respectivas medidas. Mantidos os limiares originais de contraste, tipografia, rótulo >=11 px, teclado, reflow, recursos locais e rastreabilidade. Sem sleeps fixos adicionais nem mudança de produto.

## Evidência executada

Python: `F:/CPJ - TRABALHO/.venv/Scripts/python.exe`, opção `-X utf8`, `PYTHONDONTWRITEBYTECODE=1`, fixtures exclusivamente sintéticas/TEMP. Suites executadas como scripts em processos separados.

| Suite | RED | GREEN |
|---|---|---|
| `teste_astra_ast06_store.py` | 27 testes, 3 erros + 1 falha, 4,749 s | 27/27, zero skips, 11,928 s |
| `teste_apple_ui_ap39.py` | 5 testes, 2 falhas, 22,325 s | 5/5, zero skips, 35,444 s |

AST dos dois testes e do store aprovado. `git diff --check` dos arquivos rastreados alterados aprovado. `teste_apple_ui_ap39.py` já era arquivo local não rastreado no candidato. A suite completa permanece sob coordenação, em snapshot separado; esta frente não executou full concorrente e não afirma gate global aprovado.

## Fonte congelada para o gate

| Arquivo | SHA-256 |
|---|---|
| `plugin/investigacao-cpj/app/testes/teste_astra_ast06_store.py` | `35a1f1bee8820027d887e56779da0c43873a7bd39729bb745d32ec1a6b338f14` |
| `plugin/investigacao-cpj/app/testes/teste_apple_ui_ap39.py` | `840d5800eebcd76d212c3f38539a1c2a40b12d447db1507794a8cb6f103832a5` |
| `plugin/investigacao-cpj/skills/base-cpj/scripts/vinculos_manuais.py` (sem alteração nesta frente) | `1b130b29c4d9fe1db4f9c5a0fc3b81abbe3a23a56d4bed891d4d023d9b9435b7` |

Somente os dois testes e esta evidência foram editados. Preservado o store autoritativo RP32, sem alteração de fatos, IDs, versões, documento ou observação. Nenhuma leitura de autos, configuração/modelo operacional, API externa, instalação, restart, commit ou push.

## Complemento IV01 — AST17 e F03

Escopo ampliado pelo coordenador para os dois fluxos E2E e `testes/e2e/servidor_aux.py`. Não existe `testes/e2e/fluxo.cjs`: F03 usa Python/Playwright. AST16 foi corrigido e verificado pelo coordenador, não por esta frente.

AST17 RED reproduzido em 113,698 s: a extração real concluiu, mas o harness aguardou `entidades.csv`, derivado que MD01 deixou de gerar por determinação do operador. A espera agora verifica o estado real `processamento.trabalhos[].status` da API e a transcrição Markdown. A inspeção posterior exige zero CSV e admite somente `.checkpoint/estado.json` como JSON essencial na extração. Preservados o upload, hash do original, O.S. final transcrita, fonte financeira documental, ASTRA, vínculo manual e duplicata, persistência após indexação/reinício do servidor sintético, remoção com ID/versão e proteção CSRF, editor, DOCX, bloqueio de FINAL pendente, FINAL sem forçar e painel.

F03 RED inicial: preparação exigia modelo oficial ausente (zero testes, um erro). A regressão com origem sentinela fictícia também falhou antes do reparo, demonstrando que o helper copiava um modelo existente. O helper agora sempre chama `fixtures_docx.criar_modelo` em TEMP, sem consultar/copiar modelos ou assinaturas da origem. A regressão confirma o título do modelo sintético, ausência da sentinela no destino e bytes da origem intactos. O fluxo principal passou a exigir Markdown/O.S. e ausência de CSV. Um segundo RED expôs expressão nua em `wait_for_function` do Playwright, que tentava avaliar string sob CSP; convertida em arrow function no próprio teste, sem alterar CSP, interceptar respostas de API ou esconder erros.

| Suite | GREEN final |
|---|---|
| `teste_astra_ast17_e2e.py` | 1/1, zero skips, 18,650 s; Edge/HTTP real, análise/redação determinísticas sintéticas |
| `teste_e2e_f03.py` | 2/2, zero skips, 14,753 s; fluxo Edge completo 11,09 s, OCR português real e modelo geométrico |

AST dos três Python, `node --check` do harness e `git diff --check` aprovados. AST17 registrou hashes das fontes início/fim idênticos. Evidências exclusivamente fictícias: `C:/Users/Usuario/AppData/Local/Temp/cpj-astra-ast17-e2e-hnkbw89d/resultado.json` e `C:/Users/Usuario/AppData/Local/Temp/cpj-e2e-f03-evidencias-dxk5nkru`. Os dois fluxos não incluem roundtrip de pacote; esse contrato foi exercitado por AST06/SEC23/RP30, sem afirmação de cobertura E2E inexistente. A suite completa continua com o coordenador; não houve full concorrente nem mudança de produto nesta frente.

Fonte congelada adicional:

| Arquivo | SHA-256 |
|---|---|
| `plugin/investigacao-cpj/app/testes/teste_astra_ast17_e2e.py` | `b895e5e8df1114b25a04f5b903e035426a9f6066e687597fab0aa27903949083` |
| `plugin/investigacao-cpj/app/testes/astra_e2e/fluxo.cjs` | `818d06373f778f1d80305e95bd77fb1d0f0e1b8f394d9ecdaac521a2d7480bcb` |
| `plugin/investigacao-cpj/app/testes/teste_e2e_f03.py` | `a4c512d6ca00f5f0d6efedbba3566f5e3a9f7d57a50da05225f9c61a82cfb324` |
| `plugin/investigacao-cpj/app/testes/e2e/servidor_aux.py` | `8d96158c65b84f17000e7780d4177f6fc7f0c612510288663b4627399aa40d00` |

## Complemento IV01 — interrupção real UN17

O gate final encontrou falha UN17. Reprodução antes do reparo: **1 teste, 1 falha em 153,292 s**. Além da expectativa obsoleta de `entidades.csv`, havia um defeito de produto: após matar o servidor, a reserva durável permanecia `em_execucao` por 12 horas, em nome do PID encerrado, e o novo servidor não retomava o trabalho. A reprodução terminou com `processamento.json` ainda `na_fila`, sem extração. Não foi ocultado alterando a reserva no teste nem esperando sua expiração.

Ampliação autorizada pelo coordenador: `fluxo_execucao.py`, `rotas/comum.py`, `extrair.py`, UN14 e UN17. A revisão independente RS01 identificou que modos com visão podem usar API e que um filho extrator pode sobreviver ao servidor e continuar escrevendo. O reparo ficou restrito à recuperação antecipada de extração em **modo rápido**, comprovadamente local.

O novo proprietário registra host, PID e nascimento do processo. Morte comprovada no mesmo host ou PID reutilizado com outro nascimento permite encerrar a tentativa anterior e criar exatamente uma sucessora, na transação existente. Dono vivo, inacessível, indeterminado, legado ou de outro host não é liberado antecipadamente. Origem de tarefa, etapas de IA e intenções externas abertas conservam suas guardas; o modo inteligente/IA completa não recebe esse proprietário local.

O próprio filho `extrair.py` adquire `.checkpoint/extracao.lock` antes de ler/reaproveitar/gravar a extração e o mantém até sua saída. É um arquivo persistente de um byte, com `msvcrt`/`fcntl`, sem remoção ao liberar; caminho e ancestrais são conferidos contra links/junções antes de abrir e novamente antes de escrever. O padrão espera até 30 s; `--espera-trava` aceita 0 a 300 s. Ocupação excedida falha explicitamente, sem tocar no checkpoint. Matar o servidor não libera a trava do filho que ainda escreve; o sistema operacional libera a trava quando o filho encerra.

Na retomada automática, `comum.py` consulta a etapa vigente e reutiliza o item persistido em `fila.put`, sem chamar `enfileirar`, recriar data ou zerar progresso. O worker continua obrigado a vencer a reserva atômica. Uma regressão com leitura anterior à reserva de outro executor falhou antes do reparo (`na_fila`, progresso 0 e data substituída) e passou preservando `processando`, progresso 47 e data original. Estados vivo/incerto/cancelado também permanecem intactos.

TDD adicional: quatro falhas iniciais de identidade/produtor local; falha real de sobrescrita do checkpoint na retomada; falha real do segundo extrator concluindo enquanto o filho órfão ainda escrevia; falha da janela de concorrência acima. O UN17 foi reforçado para matar o servidor **após ao menos duas páginas em checkpoint**, concluir dez páginas com oito OCR reais em português, preservar páginas já feitas e comprovar seu reaproveitamento. A fixture de filho órfão usa somente processos fictícios criados por ela, sincroniza por marcador de escrita e confirma bloqueio, timeout sem mutação, liberação ao morrer e arquivo de trava persistente. Outra fixture cria junction nativa e confirma que o destino sentinela não recebe escrita.

| Verificação final no candidato congelado | Resultado |
|---|---|
| `teste_interrupcao_real_un17.py` | 3/3, zero skips, 8,944 s |
| `teste_fluxo_execucao_un14.py` | 22/22, zero skips, 5,329 s |
| `teste_fluxo_store_un13.py` | 16/16, zero skips, 1,253 s |
| `teste_extracao_markdown_md01.py` | 5/5, zero skips, 3,195 s |
| `teste_ocr_checkpoint_claude.py` | 22 verificações aprovadas, OCR português real, `TUDO OK` |
| AST dos cinco arquivos e `git diff --check` | aprovados |

Limites: os contratos anteriores de expiração temporal permanecem; esta correção não migra donos legados sem identidade nem amplia recuperação automática de visão/API. A trava protege o extrator por documento; não afirma atomicidade global de todos os arquivos do workspace. Não houve autos reais, provedor externo, serviço operacional encerrado, reindexação operacional, publicação ou implantação. A revisão RS01 e o novo gate completo são coordenados separadamente; os testes desta frente não substituem esse gate.

Fonte congelada para auditoria e novo gate:

| Arquivo | SHA-256 |
|---|---|
| `plugin/investigacao-cpj/app/fluxo_execucao.py` | `6dc7fbdc9bda5894dc7661b996353a0bb6ff79b5842030d90e67a35b0935094e` |
| `plugin/investigacao-cpj/app/rotas/comum.py` | `bf9e81318884b9d09a34a88f2c5df0959de60cd468e44c344037f499630b1adb` |
| `plugin/investigacao-cpj/skills/pdf-autos-policiais/scripts/extrair.py` | `a84747772bf444e1a4e34c89f5757b9fb7374d007b49e78d05222d0cba23c1de` |
| `plugin/investigacao-cpj/app/testes/teste_fluxo_execucao_un14.py` | `587c8c35b4897f72583b8ba4c18cc4e73df5b03e57bbdcad0599a6a64b362e66` |
| `plugin/investigacao-cpj/app/testes/teste_interrupcao_real_un17.py` | `49da94a901e0058006555adccdd0db76fdaa72f93244661134603dff46542498` |

## Complemento IV01 — tempo de vida da trava no replay PX05

O segundo gate completo do coordenador terminou com 144/145 suites aprovadas e uma falha PX05. Reprodução desta frente: nove testes, oito aprovados e um erro em 3,349 s. O replay com `runpy.run_path` concluía a extração, mas o `ExitStack` registrado em `atexit` mantinha o descritor e a trava abertos até encerrar o chamador; a limpeza TEMP falhava com `PermissionError [WinError 32]` em `extracao.lock`. A primeira correção da trava não atendia corretamente a esse uso em processo.

Dois novos testes falharam antes do reparo: após retorno normal e após exceção controlada na gravação final, o processo chamador continuava vivo e um segundo extrator recebia timeout de ocupação. O reparo substitui o estado global `ExitStack`/`atexit` por `with trava_extracao(...)`, cobrindo todo o corpo da extração depois de analisar os argumentos. O contexto libera e fecha a trava tanto no sucesso quanto na exceção. A indentação preserva funções e variáveis no escopo de módulo e inclui o término das threads OCR, fechamento do PDF, escrita final do estado e emissão do relatório.

A fixture do filho órfão também foi corrigida: o marcador e a escrita contínua agora ocorrem **dentro** de `estado.gravar`, chamado pelo extrator real após a primeira página persistida. Assim, o filho permanece numa extração ativa quando o servidor pai morre. A prova de bloqueio/timeout do segundo escritor continua válida; já não depende de manter uma trava depois que `runpy` terminou. A trava permanece no disco com um byte, sem `unlink` no desbloqueio.

| Verificação desta revisão congelada | Resultado |
|---|---|
| `teste_transcricao_visual_px05.py` | 11/11, zero skips, 4,657 s; nove cenários originais e dois de lifetime |
| `teste_interrupcao_real_un17.py` | 3/3, zero skips, 7,992 s |
| `teste_fluxo_execucao_un14.py` | 22/22, zero skips, 5,458 s |
| `teste_extracao_markdown_md01.py` | 5/5, zero skips, 3,356 s |
| `teste_ocr_checkpoint_claude.py` | 22 verificações aprovadas, OCR português real, `TUDO OK` |
| AST dos três arquivos e `git diff --check` | aprovados |

A execução PX05 ainda emitiu avisos anteriores de `pypdfium2.get_text_range` e `ResourceWarning` sobre stdout de `comum.rodar`; não foram ocultados nem corrigidos nesta alteração de lifetime. Não houve erro nessa execução. A revisão independente RS01 e o terceiro gate completo ficam registrados pelo coordenador antes de qualquer conclusão global.

Estes hashes substituem os três arquivos correspondentes da tabela anterior; `fluxo_execucao.py`, `comum.py` e UN14 permanecem com os hashes anteriores:

| Arquivo | SHA-256 |
|---|---|
| `plugin/investigacao-cpj/skills/pdf-autos-policiais/scripts/extrair.py` | `a48b71add61f7b4f388decffeef949ee1a398071b0c130b6d1524ac1d0661077` |
| `plugin/investigacao-cpj/app/testes/teste_interrupcao_real_un17.py` | `2862a7ba35a62611125ff686ed19bf72de64be53b8261b8433d8bd19562a79cf` |
| `plugin/investigacao-cpj/app/testes/teste_transcricao_visual_px05.py` | `37872bff154a5d5a9acbbb5f847821cb1ca0653a7ae2f448c7e5efed30b568fa` |

RS01 renovou a aprovação após leitura do lifetime e execução independente de PX05 11/11, UN17 3/3 e UN14 22/22: 36 testes frescos, zero skips, hashes acima conferidos e nenhum bloqueio novo. Evidência em `revisoes/recuperacao-lease-auditoria-2026-10-27.md`. O gate completo permanece necessário e sob responsabilidade do coordenador.
