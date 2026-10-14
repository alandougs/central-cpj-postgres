# ASTRA — execução do épico #4

Missão autorizada pelo operador em 14/10/2026. Fonte dos requisitos: épico #4, issues #5–#17 e `docs/ASTRA-PLANO-AGENTES-2026-10.md` do GitHub. Todos foram consultados integralmente; estavam abertos e sem comentários. Desenvolvimento isolado, iniciado em `origin/main` (`f56653c`), branch `codex/astra-evolucao-20261014`. A branch padrão `master` não foi usada. Arquivos locais anteriores e PR #18 preservados, sem merge em produção. Somente código e dados fictícios.

## Controle de execução

| Issue | Implementação | Validação | Homologação do operador |
|---|---|---|---|
| #5 Contrato manual | API e formulário alinhados; aliases explícitos; O.S., documento, página, fls. e observação; tipos e duplicatas validados | 7 testes AST05, incluindo Edge real, aprovados; GF01 11/11 e consultas existentes aprovados; regressão rápida 4/5 suítes: falha preexistente em OCR/escrivão fictício | Pendente |
| #6 Persistência | Fonte append-only com IDs/CAS/histórico, migração e snapshots; cache regenerável; backup/export/import | Store 27/27, API 5/5, AST05 7/7; falha parcial de migração reproduzida e corrigida antes de projetar; revisão independente | Pendente |
| #7 Exclusão seletiva | API por UUID manual/O.S./versão, tombstone e confirmação; cliques seguros por DOM | 13 API + 1 Edge; AST05 7/7, GF01 11/11, GF02 10/10; regressões de persistência/importação/tarefas aprovadas | Pendente |
| #8 Evidências e confirmação | Pendente | Pendente | Pendente |
| #9 Jornada guiada | Pendente | Pendente | Pendente |
| #10 Linguagem natural | Pendente | Pendente | Pendente |
| #11 Inspetor | Pendente | Pendente | Pendente |
| #12 Rascunhos | Implementado e incorporado de branch isolada; backend existente preservado | 5 cenários Edge/HTTP e 23 regressões focadas; suíte 77/79 com duas falhas preexistentes | Pendente |
| #13 Layout | Baseline anterior às mudanças concluído; otimização pendente | 40 execuções (8 cenários × 5), métricas brutas em TEMP | Pendente |
| #14 Paginação | Baseline anterior às mudanças concluído; implementação pendente | 6 datasets, 120 GETs e 24 aquecimentos; SQL somente leitura e hashes preservados | Pendente |
| #15 Atualização adaptativa | Pendente; consultas duplicadas e erros silenciosos identificados | Pendente | Pendente |
| #16 Módulos | Pendente; fronteiras e testes dependentes do HTML inventariados | Pendente | Pendente |
| #17 Homologação técnica | Pendente | Pendente | Pendente |

## #5 — plano, execução e prova

Causa reproduzida: formulário enviava `caso_id`/`fonte`, enquanto a rota lia `caso`/`obs`; o filtro de caso no grafo não era copiado ao formulário. O teste HTTP demonstrou fonte perdida, duplicata aceita, O.S. inexistente aceita e escrita disponível ao leitor. O teste do navegador falhou inicialmente porque a O.S. selecionada não preenchia o vínculo.

Contrato: `a_tipo`, `a_valor`, `b_tipo`, `b_valor`, `relacao`, `caso`, `documento`, `pagina`, `fls`, `observacao`. Aceitos aliases `caso_id`, `fonte`, `obs`; pares divergentes são recusados. `PESSOA` exige ID de registro; nome sem identidade é `NOME`, candidato. O cadastro manual é hipótese, sem confirmação automática. Índice mantém O.S. em `fonte` para compatibilidade e localizador estruturado para as referências. API GET expõe os campos estruturados e localizador legível. A fonte autoritativa e IDs estáveis pertencem à issue #6, seguinte.

Arquivos: `app/rotas/consulta.py`, `app/static/index.html`, `app/testes/astra_fixture.py`, `app/testes/teste_astra_ast05.py`, PRD e controle compartilhado. Tests: Python do ambiente existente, processo e workspace temporários; Edge headless do runtime local. Nenhuma API de IA utilizada. QuickJS declarado em requirements-dev foi instalado exclusivamente em pasta TEMP de dependências de teste; não alterou o ambiente operacional.

## Retomada

Executar issues na ordem de dependência. Antes de editar, conferir reserva no controle compartilhado da pasta principal e assumir a próxima tarefa. Não duplicar contratos existentes do editor/FINAL nem alterações do PR #18. Fonte e instruções do caso não podem ser substituídas por coincidências do grafo. Manter as issues abertas até a revisão/homologação humana; implementação e testes são estados distintos.

Regressão rápida AST05: `ferramentas/testar-tudo.py --rapido --incluir teste_astra_ast05.py`, 4/5 suítes aprovadas; `teste_dados_os_codex.py::test_pdf_imagem_preenche_escrivao_depois_do_ocr_real` falha com escrivão vazio, reproduzida antes desta missão. Log local TEMP `cpj-astra-ast05-rapido.log`. Nenhuma afirmação de suíte inteira verde.

## #6 — persistência e recuperação

A fonte autoritativa fica em `consulta/_grafo-manual/eventos/`, com eventos imutáveis e trava entre processos. A API salva a fonte antes da projeção, retorna ID/versão e informa indexação pendente. Leitura sem fonte não cria diretórios. A migração precede a reconstrução transacional; snapshots em `legados/<sha256>.json` preservam rótulos e linhas integrais sem inventar proveniência. Pacotes e backup incluem fonte e snapshots; a importação valida a cadeia e recusa ID com conteúdo divergente.

A revisão independente reproduziu duplicata por rótulo legado, ausência de snapshot de anotação órfã posterior e captura parcial seguida de projeção. Foram corrigidas com regressões. Na falha ao gravar o segundo de dois legados, a API agora devolve HTTP 503 antes de criar/projetar, mantém ambos no índice e permite retomar a captura. Observação em formato JSON permanece texto literal, sem redefinir documento ou página.

Provas finais diretas: armazenamento 27/27, API 5/5, AST05 7/7. O agente também aprovou importação 5/5, tarefas 2/2 e consultas. Suíte intermediária: 79/81, com falhas conhecidas em OCR (`teste_dados_os_codex.py`) e mtimes (`teste_workspace_v01.py`). Essa rodada antecedeu as últimas correções; os focais finais foram repetidos. Logs em TEMP: `cpj-astra-ast06-store-integrado.log`, `cpj-astra-ast05-integrado.log`, `cpj-astra-ast60-suite.log`. Informação já apagada antes desta versão exige backup; não foi inventada recuperação.

## #12 — rascunhos

Commit do agente `6436719`, incorporado como `f09e25d`. Salvar/autosave usa a revisão esperada, sem DOCX; gerar DOCX é uma ação explícita da versão salva. Conflito HTTP 409 mantém texto e exige comparação/conciliação. Cinco cenários reais Edge/HTTP e 23 regressões focadas aprovados; suíte geral 77/79, com as duas falhas conhecidas acima. Log: TEMP `cpj-ast12-suite.log`. O E2E Python antigo precisa refletir salvar → aguardar confirmação → gerar DOCX → fechar; adaptação prevista na homologação. O editor permanece no worktree, sem aplicação operacional até integração autorizada.

## Métricas anteriores às otimizações

Canvas: TEMP `cpj-astra-baseline-5f2d3d0885/`, com `benchmark.cjs`, `results.json`, `README.md` e `index-before.html`. Edge 155 headless, viewport 1440×1000, DPR 1; cinco repetições por cenário, 40 execuções. Em 1.000 nós/10.000 arestas: montagem p50/p95 de 102,2/104,4 ms; física 7,0/9,0 ms; desenho 23,1/207,7 ms; intervalo de frame p95 de 65,1 ms; mediana de 21,98 FPS. Caso aberto produziu 8 GETs de tarefas em quatro ciclos/5,2 s, inclusive em outra aba; HTTP 503 ficou sem feedback. Limites: APIs sintéticas, tempos do renderer e host compartilhado; não são FPS do compositor nem percentual de CPU.

SQL/API: TEMP `cpj-astra-sql-baseline-f75e3828aa/`, com `benchmark_sql.py`, `results.json` e `README.md`; snapshot `f56653c`. Foram seis datasets de 100/500/1.000 casos fictícios, 120 GETs medidos e 24 aquecimentos, todos HTTP 200; somente SELECT e hashes SQLite preservados. Em 1.000 casos densos, p50/p95 em ms: geral 2.379,6/2.813,2; uma O.S. 690,8/804,5; busca 703,5/717,6; busca com O.S. 1.174,5/1.261,2. A busca abriu 31 conexões e executou 304 SQLs, dos quais 211 SELECTs de rótulo. Todo GET releu 1.000 cadastros. Geral mostrou 200 relações por corte antes da deduplicação; O.S. densa 470/490; busca 90, sem total, truncamento ou paginação declarados. Resultados completos nos JSONs; com cinco amostras, p95 é o máximo. Nenhuma melhoria foi alegada antes da comparação.

## SIG01 — pedido adicional atendido

Citação dupla vira `(fls. ...)` só na apresentação DOCX; o Markdown preserva PDF e folhas, sem inferir folhas ausentes. A assinatura existente no modelo acompanha o nome; a entrega final não pula o modelo por já existir DOCX recente. Três falhas iniciais reproduzidas; 12 testes DOCX/opções e 12 de squad aprovados. Exemplo fictício conferido visualmente no Word isolado (duas páginas), modelo preservado por SHA-256. Aplicado na Central primária após confirmar ausência de tarefas/processamento; HTTP saudável. Commit `f941acb`, integrado aqui como `8620345` e publicado no PR #18 (head `0931782`). Nenhuma imagem de assinatura foi enviada ao GitHub.

## Sincronização

PR #19 em rascunho: https://github.com/alandougs/central-cpj-postgres/pull/19. Publicação inicial contém #5; as seguintes incluem somente código, procedimentos e fixtures validados. PR #18 mantém extração, O.S., Explorer e DOCX; incorporado localmente como dependência para preservar as entregas, sem merge remoto em main. Conflitos somente no PRD e fila foram conciliados preservando os registros das duas linhas e usando a fila canônica. Issues permanecem abertas até revisão do operador.

## #7 — exclusão seletiva

A rota anterior apagava por extremos/relação, sem restringir origem. Agora recebe somente ID manual imutável, O.S. cadastrada e versão esperada, exige trabalho/CSRF e verifica snapshot e CAS final. Não aceita tupla legada; 404 para vínculo desconhecido/automático/outra O.S., 409 para versão obsoleta ou exclusão repetida. Tombstone é salvo antes do cache; falha de projeção informa pendência, sem ressuscitar anotação. A UI confirma a operação, mantém a direção da aresta e liga handlers DOM aos IDs, sem inserir nomes/apóstrofos em código JavaScript.

TDD: quatro falhas iniciais na API; navegador reproduziu clique quebrado por apóstrofo antes do ajuste. Validação final: 13 testes API e 1 Edge, repetidos pelo integrador, AST05 7/7, GF01 11/11, GF02 10/10. A fixture QuickJS GF02 recebeu permissão de leitura e querySelectorAll vazio para o novo limite de DOM; sua cobertura de desenho/fonte permanece, e eventos são verificados no Edge. Regressões do agente: AST06 5/5, importação 5/5, tarefas 2/2.

Rodada ampla iniciou no runner oficial e continuou em snapshot global congelado para permitir desenvolvimento isolado; relatório agregado ainda em coleta. Falha nova de teste antigo F04 identificada: exige citação dupla e quebra antes da assinatura, contratos alterados pelo pedido SIG01. Será adaptado com reserva SIG02, mantendo margens/timbre/rodapé/assinatura. Não é falha preexistente nem suíte geral verde. Baselines OCR e mtimes continuam registrados.

## Preparação de #8 e #16

Reprodução independente #8: duas referências documentais viram uma no geral, caso e busca; localizador de pessoas perde documento e duas qualificações em documentos distintos, mesmo nome e página, colidem no mesmo P:. Plano e provas fictícias em TEMP cpj-astra-ast08-plan-148a20be13. Nenhum remapeamento de manuais por nome será feito. #16 será antecipada por coordenação explicitamente permitida na issue, para separar arquivos de frontend antes das demais mudanças; extração literal, sem mudança funcional no mesmo commit. Plano TEMP cpj-astra16-plan-20261014.
