# ASTRA — execução do épico #4

Missão autorizada pelo operador em 14/10/2026. Fonte dos requisitos: épico #4, issues #5–#17 e `docs/ASTRA-PLANO-AGENTES-2026-10.md` do GitHub. Todos foram consultados integralmente; estavam abertos e sem comentários. Desenvolvimento isolado, iniciado em `origin/main` (`f56653c`), branch `codex/astra-evolucao-20261014`. A branch padrão `master` não foi usada. Arquivos locais anteriores e PR #18 preservados, sem merge em produção. Somente código e dados fictícios.

## Controle de execução

| Issue | Implementação | Validação | Homologação do operador |
|---|---|---|---|
| #5 Contrato manual | API e formulário alinhados; aliases explícitos; O.S., documento, página, fls. e observação; tipos e duplicatas validados | 7 testes AST05, incluindo Edge real, aprovados; GF01 11/11 e consultas existentes aprovados; regressão rápida 4/5 suítes: falha preexistente em OCR/escrivão fictício | Pendente |
| #6 Persistência | Fonte append-only com IDs/CAS/histórico, migração e snapshots; cache regenerável; backup/export/import | Store 27/27, API 5/5, AST05 7/7; falha parcial de migração reproduzida e corrigida antes de projetar; revisão independente | Pendente |
| #7 Exclusão seletiva | API por UUID manual/O.S./versão, tombstone e confirmação; cliques seguros por DOM | 13 API + 1 Edge; AST05 7/7, GF01 11/11, GF02 10/10; regressões de persistência/importação/tarefas aprovadas | Pendente |
| #8 Evidências e confirmação | Relação com todas as referências, identidades por registro/linha e estados separados; URLs seguras | 19 API + 11 indexador + 1 Edge finais, regressões de contratos/persistência/exclusão/GF01/GF02 aprovadas | Pendente |
| #9 Jornada guiada | Material/próximo passo contextual, explorar, fontes, dinheiro, hipótese e retorno com filtros | 6 Edge repetidos pelo integrador; 49 regressões adicionais do agente, sem POST implícito e com editor protegido | Pendente |
| #10 Linguagem natural | Quatro intenções locais, contexto, desambiguação, fontes e histórico da sessão; sem LLM ou escrita de fatos | 12 HTTP/Edge finais; quatro regressões de literais/Pix/seleção/tombstones corrigidas e repetidas independentemente | Pendente |
| #11 Inspetor | Nó/aresta e referência individual; conferência original/derivado, candidato e hipótese com histórico persistente | 15 API/persistência após correção de ID com ponto e 3 Edge, mais regressões P0 e backup real | Pendente |
| #12 Rascunhos | Implementado e incorporado de branch isolada; backend existente preservado | 5 cenários Edge/HTTP e 23 regressões focadas; suíte 77/79 com duas falhas preexistentes | Pendente |
| #13 Layout | Sementes/ordem estáveis, câmera/posição/seleção por ID, proximidade, RAF/visibilidade e agrupamento expansível | 2 testes com18 verificações Node+3Edge; GF02 10/10;80 medições pareadas+80 ablações, ganhos/regressões explícitos | Pendente |
| #14 Paginação | Total exato, ordem e revisão de páginas, todas as fontes, rótulos em lote e cache invalidável | 15 API e 4 Edge; 120 GET e 24 aquecimentos atuais, seis bancos intactos; busca global ampla de 13,3 s documentada | Pendente |
| #15 Atualização adaptativa | Leitura compartilhada, intervalo por estado, pausa oculta, timeout/backoff e preservação de texto | 7 determinísticos e 5 Edge repetidos, 63 regressões do agente; 36 amostras pareadas/hashes auditados | Pendente |
| #16 Módulos | 16 scripts clássicos e CSS extraídos literalmente; módulo de perguntas acrescentado como 17º, antes do bootstrap | AST16 4/4, Edge05/07/12/Explorer e leitores afetados aprovados; rodada ampla em snapshot identificada | Pendente |
| #17 Homologação técnica | Matriz/roteiro e E2E integrado, auditoria e memória Windows medida; código congelado | Rápida 3/4 e completa 101/103 com HTTP aprovado; duas exceções anteriores e skips explícitos, 214 arquivos do plugin intactos | Pendente |

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

## #16 — extração incremental coordenada

A antecipação prevista na issue separou o frontend antes das mudanças de UX, sem misturar refatoração funcional. São 16 scripts clássicos na ordem original, CSS local e bootstrap único; funções e variáveis globais continuam no mesmo ambiente. O DOM fora dos blocos extraídos é igual ao anterior. Comparação independente do integrador confirmou JavaScript concatenado e CSS iguais ao commit 212a184 após normalizar LF/CRLF. Mapa de responsabilidades e hashes do snapshot Windows em `revisoes/astra-modulos.md`.

Doze leitores locais e dois HTTP usam helper que carrega recursos reais na ordem da página, sem aceitar recurso ausente/externo ou assíncrono. HTTP mantém cookies, exige 200/MIME; sintaxe compila todo o JS combinado e mantém a verificação de duplicação lexical. O teto de tamanho cobre a interface agregada. Root aprovou AST16 4/4, Edge07 1/1, GF02 10/10 e UX01 6/6. Agente aprovou Edge05 7/7, Edge12 5/5, Explorer 1/1 e leitores afetados; fixture nova fecha responses e passou HTTP 1/1 com ResourceWarning como erro.

Suíte ampla em snapshot global TEMP `cpj-ast16-global-6md0psp_/codigo`, log `cpj-ast16-global-suite.log`, ainda em coleta. A cópia capturou `teste_astra_ast08_index.py` em RED de preparação; sua falha não pertence à extração de módulos nem comprova validação de #8. A rodada final #17 será congelada sem edições concorrentes. Arquivos liberados para as próximas issues; homologação humana pendente.

## SIG02 — regressão do contrato DOCX

O teste F04 antigo reproduziu duas falhas em cinco: exigia citação PDF+fls. e quebra forçada antes da assinatura. Somente essas expectativas foram ajustadas ao pedido do operador, acrescentando verificação de manter assinatura/nome juntos. Margens, timbre, rodapé/paginação, imagem, estilos, tabela e valores continuam verificados. F04 final 5/5 com modelo sintético em TEMP; SIG01/opções 12/12 aprovados. Não houve nova alteração do produto, do modelo real ou de casos.

## Sincronização posterior

PR #19 atualizado até exclusão seletiva e SIG02, commit remoto `2bed432`, árvore idêntica ao marco local `212a184`. Publicação por API com lease e conferência de árvore, sem merge em main. Issues #5, #6, #7 e #12 receberam provas e permanecem abertas para homologação. #8 e #16 posteriores continuam em desenvolvimento/validação isolados até o próximo marco publicado.

## #8 — relação, referências e níveis distintos

Uma relação visual usa extremos direcionais e relação literal; cada referência tem ID próprio, origem/tipo, caso, documento/página(s)/fls., trecho, localizador integral, linha/seq e hashes/datas quando conhecidos. `evidencias[]` mantém todas as fontes, sem eleger uma anotação entre várias. UUID/versão manual ficam separados do ID agregado. A busca não descarta referências antes de agrupar; 405 fontes de uma mesma relação foram preservadas no geral, por caso e q. Consulta relacional respeita fonte autoritativa/tombstones mesmo com cache atrasado. Migração parcial elimina só sobreposição cache/evento correspondente, preservando duplicatas legadas reais.

Indexador mantém oito colunas e inclui JSON `astra-evidencia/1`. Qualificações de documentos ou linhas distintos não fundem registros PESSOA por nome/localizador; manuais antigos permanecem byte a byte, sem remapear pelo nome. Valores desconhecidos ficam null. Origem de consulta/cadastro/extração candidata não vira confirmação humana. CSV financeiro sem documento não escolhe um PDF. Contenção dupla caso+workspace bloqueia referência original que uma junction externa publicava; cálculo de hash externo não foi reproduzido e não é alegado.

A UI apresenta todas as referências, trechos e status declarados, inclusive divergências/ausências, e abre PDFs separados por URLs geradas no servidor. A hipótese manual continua identificada após conferência humana, com responsável/data. Remover atua na anotação específica dentro do grupo. Documentos ausentes não apagam a referência; fls. não informadas não são preenchidas. Origem legada desconhecida com caso literal cadastrado continua no caso, com ressalva de proveniência. Índice ausente mantém rótulos manuais, filtro de busca e aviso, sem escrita por GET.

TDD reproduziu perda de segunda fonte, colisões de registros, caminhos/legados, tombstone atravessado em busca e regressões de fallback. Provas finais do integrador: API 19/19 (21,804 s), indexador 11/11, Edge de quatro fontes/uma relação 1/1 e Edge de exclusão 1/1. GF01 11/11, GF02 10/10, AST05 7/7 e AST06 5/5 aprovados; agente repetiu Store 27/27, exclusão API 13/13 e consultas completas. Uma falha WinError32 na limpeza da fixture AST05 revelou conexões SQLite de teste sem close: corrigidas as conexões da fixture/contagem, mantendo todos os asserts; repetição 7/7 sem erro. Nenhum banco operacional envolvido.

Limite atual: cada relação selecionada tem referências completas, mas busca/expansão sem comprovação global retorna truncado null e completude não aferida; corte confirmado é explícito. Paginação/total/SQL pertencem à #14. Abertura de base de consulta e conferência/histórico de referência documental pertencem à #11.

## Rodadas amplas históricas e whitespace

AST07: rodada composta 86/89, não execução única: 41 aprovações do runner oficial interrompido + 45/48 na continuação do snapshot global TEMP cpj-astra-ast70-global-oyj25hib. Falhas: OCR/escrivão, mtimes operacionais e F04 antigo, posteriormente corrigido pela SIG02. Central HTTP aprovada em 16,03 s. Método/logs preservados no snapshot.

AST16: 88/91 em 393,03 s no snapshot global TEMP cpj-ast16-global-6md0psp_. Falhas: teste08index em RED capturado durante cópia, OCR/escrivão e mtimes operacionais. Leitores adaptados e todos os Edge executados passaram; F04 já ajustado passou. Essa rodada não certifica a versão final de #8. Nova rodada partirá de snapshot congelado após integração completa; #17 repetirá a suíte final aplicável.

Extração literal AST16 conservou linhas de espaços em casos.js e linhas vazias finais dos blocos. `git diff --check` padrão apontou essas ocorrências herdadas; não foi alegado como limpo. Comparação independente LF/CRLF provou conteúdo igual, e checagem transitória com core.whitespace=-blank-at-eof,-blank-at-eol passou sem outros problemas. A mudança atual AST08 passou no diff-check padrão; nenhuma reformatação adicional foi feita.

## Marco publicado e suíte P0 final

#8 e #16 publicadas no PR #19, commit remoto `5db7542`, árvore `42baa433a53c9f3d4ffaf723967aaa40bea9ebd4` idêntica ao marco local `aa0d7be`. Ref atualizada com lease, sem merge remoto. Issues #8 e #16 receberam evidências. A triagem de padrões identificou um e-mail de fixture; revisão confirmou nome fictício e domínio reservado, sem conteúdo de caso ou segredo.

Runner oficial integral executado de um snapshot global congelado antes das novas edições: TEMP `cpj-astra-p0-final-gv3i_4fi/codigo`, log `cpj-astra-p0-final-suite.log`. Resultado **91/93 suítes em 475,68 s**. As duas falhas são `teste_dados_os_codex.py` (escrivão não recuperado no OCR sintético) e `teste_workspace_v01.py` (observação do workspace primário em atividade); ambas reproduzidas antes da evolução. Central HTTP aprovada. Não houve teste08 intermediário neste snapshot. Skips declarados pelo runner: OCR sem idioma local na sandbox, quatro symlinks sem permissão e E2E Python sem Playwright; os testes Node/Edge foram executados. Isso valida o marco P0/#12/#16 com essas exceções, não a homologação final das etapas posteriores.

## #11 — inspetor e conferência humana individual

Clique no nó ou na aresta abre todas as referências da relação, com trecho, origem, documento, página/fls. e acesso seguro aos recursos disponíveis. Metadados internos JSON permanecem na referência, sem ocupar o lugar do localizador legível na interface. Conferir original e conferir extração/registro são ações distintas; candidato e observação são registros humanos independentes e não alteram tipo, origem, identidade nem autoria.

Eventos append-only em `consulta/_grafo-manual/conferencias` guardam referência, versão esperada, usuário/data do servidor e histórico. A conferência mantém seu próprio autor/data mesmo depois de outra pessoa anotar. Resolver consulta a tupla direcionada e a evidência no caso, sem depender do corte visual. Fonte alterada ou manual excluída exige nova referência; histórico antigo permanece acessível. Fonte ausente aceita observação/candidato e não aceita conferência de recurso indisponível. Cadeia corrompida devolve 503, sem aparentar ausência de conferência.

Provas independentes do integrador: **14/14 API/persistência em 13,242 s** e **3/3 Edge em 24,235 s**; GF02 10/10 e fontes08 Edge 1/1 aprovados. TDD reproduziu ausência do clique na aresta, descarte de texto não salvo ao registrar outra fonte e mensagem contraditória de conferência logo após salvar, todos corrigidos. Edge cobre três referências, PDF ausente, divergência/OCR, observação editada com histórico, reabertura, filtros, conflito409 com texto preservado e leitor sem escrita. Originais sintéticos permanecem com hashes iguais.

Backend também testou CAS entre processos, reinício, backup/restauração PowerShell real, pacotes dados/completo, reimportação idempotente e rejeição de pacote conflitante antes de publicar caso. Regressões Store27, API08 19, API07 13 e AST06 5 aprovadas pelo agente. Referência de base de consulta sem caso ou URL segura continua com aviso: não há abertura inventada nem escolha aproximada de PDF. Homologação humana e suíte final #17 continuam pendentes.

## #9 — jornada pelo caso

A ficha mostra arquivos originais, documentos/páginas registrados, disponibilidade de extração/análise e lacunas documentadas, com próximo passo conforme status e processamento real. Explorar envia a O.S. antes de abrir o grafo e faz uma consulta; retorno mantém filtros e distingue contagens do recorte de dados ainda não consultados. Índice indisponível não aparece como zero vínculos. Fontes, fluxo financeiro e hipótese usam as ações existentes; navegar não inicia IA nem grava vínculos. Editor com texto não salvo bloqueia saída e mudança de seleção.

Respostas antigas da ficha/grafo não substituem a O.S. atual; erro da ficha tem tentativa explícita. Controles de FINAL e geração permanecem explícitos. TDD reproduziu ausência da jornada; seis cenários Edge finais repetidos pelo integrador em 70,594 s. Agente aprovou mais 37 testes GF02/UX01/navegação/F01 e 12 testes Edge/HTTP de editor, Explorer, AR01 e módulos. Sem dados reais, alterações operacionais ou homologação automática. Próxima #10: quatro intenções locais, consultas parametrizadas, desambiguação e referências, sem LLM remoto.

## Trabalho em andamento após #9/#11

Marco remoto atual `e5ad860` no PR #19, árvore `7ed4ac87d1f368701149d198701fc35ca0334a5b` igual ao marco local `d2daf5d`. #9/#11 publicadas, comentários nas issues com provas; sem merge nem aplicação operacional. Triagem de padrões das linhas adicionadas nesse marco não encontrou dados sensíveis.

AST10 reservada ao integrador: novo serviço/rota e módulo local com quatro intenções, desambiguação e histórico por sessão/caso. Primeira rodada foi 4 API verdes; após UI, 6 HTTP/Edge verdes em 16,980 s. Revisão posterior reproduziu falta de invalidação de consulta antiga ao exibir recorte; ajuste e teste de consulta Pix entre O.S. aguardam repetição final. Rótulos usam o helper em lote da AST14 ainda não commitada: integrar AST14 antes do commit AST10. Nada disso é conclusão final/homologação da #10.

AST13 e AST14 estão reservadas a agentes distintos, sem arquivos compartilhados. Grafo: 80 medições pareadas before/after completas, ablações separadas em coleta; não há ganho final proclamado. Força/desenho/agrupamento testados; uma correção posterior de projeção agrupada terá snapshot separado do primário expandido. Scripts/resultados sintéticos em `revisoes/metricas-astra/grafo/`; JSON brutos serão comprimidos sem perda com hashes. Utilitários de teste vão para `app/testes/astra_layout/` porque o runner oficial não copia revisoes para a sandbox. SQL: paginação, fonte autoritativa, marca de revisão e rótulos em lote em desenvolvimento; provas finais e benchmark posterior ainda pendentes. Janela de benchmark do grafo começou 19:01:29 UTC; testes pesados paralelos foram pausados para reduzir interferência.

AST15 tem plano somente TEMP `cpj-astra15-plan-20261014/plano-ast15.md`, aguardando validação final10 e reserva. Roteiro humano17 e matriz em TEMP `cpj-astra17-homologacao-20261014/`, ainda não executados e sem homologação presumida. O pedido DOCX SIG01 permanece aplicado à Central primária, independente desta branch experimental.

## #13 — layout e medição completa

Posições iniciais por ID e ordem canônica eliminam Math.random; atualização conserva posição/arraste fixo, câmera e seleção de nó/aresta. Grade de proximidade mantém raio400 e força de referência, com pior caso quadrático declarado. RAF coalescido pausa quando oculto e por movimento/teto; agrupamento é projeção visual com membros/relações/fontes e expansão, sem alterar grNodes/grEdges. Aresta selecionada tira seus extremos do grupo para identificação. Inspetor11 foi preservado.

Integrador repetiu AST13 **2/2 em2,972s**, agregando18 verificações Node e3 cenários Edge; agente aprovou GF02 10/10 e AST11 UI3/3. Utilitários ficam em app/testes/astra_layout e clone sem revisoes foi validado. Oito gzip com mtime0 foram verificados pelo integrador contra SHA e backup bruto completo em TEMP, sem perda de campos/amostras. Fontes e método em `revisoes/metricas-astra/grafo/README.md`.

Comparação coordenada:40 before+40 after expandidos, mesmos50/100/500/1000nós e densidades2/10, contagens n/n*d verificadas; mais80 ablações separadas. Desenho p95 em500/5000 passou134,4→10,7ms e1000/10000 passou182,3→16,1ms; FPS derivada de ticks29,1→49,5 e23,6→34,6, sem alegar compositor/GPU. Nível de rótulos explica parte substancial do ganho; rótulos completos1000denso117,7ms e agrupado106,4ms, ambos piores que expandido adaptativo. Agrupamento melhora exploração, sem ganho de desempenho alegado.

Regressões/limites: cenários pequenos têm pequenas pioras de montagem/física; todas40 after pararam no teto360ticks, sem comprovação de convergência. Animação mais longa e heap observado1000denso23,13→38,13MB; TaskDuration melhora no denso e piora no pequeno, sem percentual de CPU ou promessa de economia geral. Snapshot primário e correção agrupada posterior preservados separadamente; o ramo expandido medido não mudou. Homologação humana e validação17 seguem pendentes.

Atualização AST10: repetição final **8/8 HTTP/Edge em15,636s**, incluindo recorte Pix entre O.S., invalidação de respostas antigas e histórico/reconexão; AST16 com novo módulo4/4 em5,315s. AST15 foi reservada após esses resultados e está em implementação; a fonte/commit10 aguarda integração do helper14. Não há confirmação de suíte final do projeto.

## Revisão adicional de #10 e integração #14

A auditoria independente posterior aos oito testes encontrou três lacunas em perguntas Pix: literal parcial podia selecionar outra chave no caso atual; cache manual antigo podia reapresentar hipótese excluída; ocorrência somente em extração candidata era omitida. Também foi identificado por leitura que uma seleção anterior prevalecia sobre literal explícito. Novos testes de regressão foram escritos antes da correção; sua execução aguarda a janela exclusiva de medição15. Os oito testes anteriores não constituem validação desses cenários.

Backend14 passou15 testes repetidos pelo integrador em5,713s. Interface14 passou4 cenários Edge em16,755s: próxima página mantém câmera/seleção/fontes; revisão alterada409 preserva recorte; erro503 permite nova tentativa; resposta antiga não troca O.S. e recorte explícito de pergunta não herda erro de paginação. A quarta regressão foi reproduzida antes de associar o estado de paginação à geração da consulta.

O integrador verificou cinco hashes de fonte, método original,120 amostras e24 aquecimentos SQL: HTTP200, totais iguais ao oráculo, uma conexão e nenhum cadastro JSON relido nas amostras aquecidas; seis bancos mantiveram hashes. Em1.000 O.S. densas, consulta por O.S. p50/p95128,73/150,67ms; busca global ampla13.312,49/13.432,95ms para contar490.000 relações e devolver400 com fontes. O baseline devolvia90 sem total e cortava30 sementes: não é comparação de trabalho idêntico nem ganho universal. Método,24 cenários e planos atuais em `revisoes/metricas-astra/sql/README.md`.

Triagem de padrões do commit local13 encontrou19 correspondências de telefone: três constantes numéricas do hash do grafo e16 valores decimais de tempo no JSON de comparação. Contextos conferidos: falsos positivos, sem telefones ou conteúdo de autos. Os gzip contêm somente medições fictícias e foram conferidos por hash/roundtrip; a triagem não foi descrita como zero achados nem como execução do scanner YAML completo.

## #15 — atualização adaptativa e medição

Cinco módulos mantêm uma leitura de tarefas compartilhada por rodada; intervalo ativo1,6s e ocioso8s, erro com backoff até60s, timeout12s e pausa quando oculto. Mudança de sessão/caso e respostas antigas têm guardas. Painéis só reescrevem HTML diferente e mantêm details abertos; resultado de IA oferece atualização explícita da ficha. Cancelamento exige confirmação positiva do servidor; POST não é repetido pelo controlador.

Integrador revisou o diff e repetiu7 testes de política em0,889s e5 HTTP/Edge em21,570s; agente63 regressões verdes. Trinta e seis amostras pareadas, janela exclusiva, seis cenários/três repetições antes/depois com mesmo instrumento e fontes congeladas. Integrador verificou cinco hashes de JS e gzip bruto,36 contagens de pedidos, métodosGET/respostas e18 amostras after sem mutações estáveis; não houve erro JS ou pedido externo no raw.

Caso ocioso8→1GET, ativo8→4, outra aba com caso aberto8→1, erro4→2, oculto emulado8→0; início tarefas/fila4→1 cada. CDP TaskDuration não melhora universalmente, por exemplo erro p5063,1→79,5ms. Oculação foi emulada, DOM não mede repaint e heap não é RAM total; não se alegam CPU/FPS de sistema. Fontes, raw gzip, hashes, método e limites em `revisoes/metricas-astra/polling/README.md`. Sem aplicação operacional ou homologação humana automática.

Marco13 publicado como `b0c489d`, árvore `1d5941229ef19c84313a39e4fc68cbbeb3675805` igual ao commit local anterior. A base `f56653c` continua ancestral; nenhuma integração em main. Preparação17 usa testes fictícios e execução de análise/redação simulada explicitamente separada da extração e HTTP/Edge reais. Auditoria17 identificou divergência de ID com ponto em conferências11, reservada em AST171 para TDD; não há afirmação de suíte global final.

## #10 — auditoria e regressões finais

Três novos testes falharam antes do patch (1,505s): Pix literal selecionava outra chave, candidato não aparecia e hipótese excluída reaparecia. Literal Pix usa igualdade canônica no universo das O.S.; fonte autoritativa é conciliada antes de agrupar e filtro exato é reaplicado aos manuais. Ocorrências candidatas/hipóteses mantêm tipo e aviso, sem afirmar transferência ou autoria. Revisão independente repetiu três cenários corrigidos e verificou SQLite intacto.

Quarta regressão de seleção foi reproduzida antes do patch: conta antiga substituía pessoa entre aspas. Agora seleção só é aceita se estiver entre as opções compatíveis com o literal, preservando escolha explícita entre homônimos. Integrador repetiu **12/12 HTTP/Edge em26,778s**. AST16 isolada **4/4 em4,370s**; tentativa de combinar módulos no mesmo processo falhou no isolamento do harness e no PYTHONPATH de QuickJS, resolvida executando processos separados com dependência TEMP já disponível, sem mudança do produto para ocultar falhas.

Quatro intenções e histórico permanecem locais, sem IA externa ou gravação de fatos/vínculos; cada relação exibida mantém todas as fontes. A integração10/14 é um marco conjunto porque10 usa o helper de rótulos em lote14 e o quarto teste UI14 verifica o recorte explícito10. Nenhum intermediário incompleto é publicado.

Reteste independente também confirmou a quarta correção: seleção antigaCONTA100/200 devolve as duas opções da pessoa citada; seleção compatívelA mantém duas relações eB nenhuma. Triagem de padrões das linhas novas10/14/15 encontrou cinco ocorrências de e-mail, todas nos testes novos com domínio reservado `ficticio.invalid`, conferidas como dados sintéticos. Nenhuma correspondência de token, CPF/CNPJ ou telefone neste marco; não se trata da execução integral do scanner YAML.

## #17 — integração e auditoria antes da rodada global

AST170: integrador revisou o harness e repetiu o E2E real Node/Edge **1/1 em22,582s**; evidências TEMP `cpj-astra-ast17-e2e-b12xdkj3`. Três fases com console/pageerror/5xx/pedidos externos vazios e12 hashes fonte início/fim iguais. Original permaneceu idêntico; O.S. final transcrita na página3 e determinação conferidas, fonte financeira página2/fls2. Manual sobrevive reindexação/reinício, exclusão por ID/CAS deixa documental, rascunho salva sem DOCX, geração é explícita, FINAL com pendência409 e depois corrigido200 sem forçar; painel confirma entregue.

Análise/CSV/redação foram simulados deterministicamente, não execução de IA; extração foi de PDF nativo, sem certificar OCR. Brasão oficial ignorado ausente no checkout: rodada estrita404 preservada e só essa URL recebeu geometria no harness, com demais asserções mantidas. F03 adaptado ao contrato salvar/DOCX, execução0testes/1skip por PythonPlaywright ausente; o NodeE2E novo executou de fato. Matriz, ambiente, comandos e roteiro humano em `revisoes/astra-homologacao-2026-10.md`.

AST171: auditoria reproduziu HTTP400 para conferência de caso com ponto que já abria no grafo. Uma linha alinha ID canônico, rejeitando explicitamente `.`/`..`; novo RED antes do patch e integrador **15/15 API/persistência em8,881s**, mais33 regressões do agente. Revisão, overlay, histórico, CAS409 e recusas de traversal/separadores/percent-encoded sem escrita estão testados. Auditoria não encontrou novo bypass de autorização/CSRF/XSS, promoção de hipótese/candidato ou escrita de originais nos controles examinados; isso não é prova absoluta de ausência de falhas.

Marco10/14/15 publicado como `23a16c7`, árvore `2350a492e9ee9902fc99bdcb148f721f7dd0f6c7` exatamente igual ao commit local `1cf3af6`; issues comentadas com evidências/limites e continuam abertas. Próximos passos desta issue: complemento de memória Windows com método/limites, snapshot congelado e runner rápido seguido da suíte completa. Nenhum resultado global final alegado até obter os retornos.

### Memória Windows e início da rodada final

AST172 mede WorkingSet64 dos PIDs retornados pelo CDP da instância Edge, com snapshots13 congelados e graphs fictícios totalmente expandidos.24 amostras completas mais3 inválidas preservadas na execução principal, por processo auxiliar encerrado; tentativas preliminares também preservadas. Integrador executou o verificador e conferiu8 hashes/bytes dos artefatos. p50 em MB decimais, antes→depois:50nós508,31→498,19;100nós527,45→510,07;500nós565,92→542,05;1000nós601,08→632,56. Não há melhoria geral de memória. Soma pode duplicar páginas compartilhadas; leitura pontual/não atômica, sem pico/GC, três repetições e retries com viés explícito. Heap é separado. Método, p95 e brutos em `revisoes/metricas-astra/memoria/README.md`; não é medida da versão final inteira ou da API/Python.

Código congelado em TEMP `cpj-astra-final-x3dl_pa5/codigo`,214 arquivos do plugin com manifesto SHA-256; fonte após AST170/171, antes de novos ajustes apenas documentais. Runner rápido **3/4 suítes em24,40s**, retorno1: única falha conhecida OCR/escrivão fictício vazio, mesma reprodução anterior. Suíte completa iniciada depois, no mesmo snapshot, com QuickJS TEMP já disponível; ainda em coleta. Nenhum código do produto será alterado durante essa rodada.

## Fechamento técnico — 14/10/2026

Runner rápido e completo executados nessa ordem, ambos no snapshot congelado. Comandos: Python da venv com `-X utf8`, `ferramentas/testar-tudo.py --rapido` e depois `ferramentas/testar-tudo.py`, com `PYTHONPATH` apontando apenas para QuickJS de teste em TEMP. A rodada completa terminou **101/103 suítes aprovadas**, retorno1; soma de tempos de execução **592,15s**, sem incluir toda a preparação/cópia das sandboxes. A integração HTTP da Central isolada passou. Todos os novos testes ASTRA e os focais DOCX SIG01/F04/opções passaram.

Exceções preexistentes reproduzidas antes desta missão e mantidas visíveis: `teste_dados_os_codex.py`, escrivão fictício vazio após OCR; e `teste_workspace_v01.py`, assert de mtime sobre `C:\CPJ - TRABALHO`, pasta operacional ativa. O segundo teste aprovou resolução/precedência do workspace e recusas fora dele, mas o retrato global detectou mudança e não isola seu autor. Não é certificação de ausência absoluta de escrita na pasta operacional; a implementação foi restrita ao worktree e testes fictícios, e seus originais foram conferidos por hash. Essas duas exceções não foram corrigidas fora do escopo ASTRA.

Skips explicitados pelo runner: paralelismo OCR de `teste_desempenho_f02.py` sem Tesseract local na sandbox; F03 Python sem Playwright; quatro cenários de symlink em `teste_executores_rv17.py` por permissão; OCR português de `teste_ocr_checkpoint_claude.py` indisponível. O Node/Edge E2E novo executou e passou também dentro da rodada completa (26,23s); não foi substituído pelo skip do F03. Não houve execução real de modelo/provedor de IA.

Logs locais: TEMP `cpj-astra-final-rapida.log` e `cpj-astra-final-completa.log`. SHA-256 do log completo: `7e7be2d28485a7a6e03a5c639864d8c509c7c16e33d1eb3f782dee0289ff82c8`; manifesto do plugin no snapshot: `a339ca8ae2d8db57dcdfc4415ad93ba530d0fd931f8f73fc15a089c3b0aa1f27`. Comparação final com os214 arquivos atuais: **zero divergências**. Nenhuma alteração de código foi feita durante/depois da suíte; os últimos commits acrescentam somente documentação, controle e métricas.

As issues #5–#17 têm implementação e evidências técnicas registradas, com as exceções acima; permanecem abertas para revisão/homologação do operador. Ganhos mensurados de desenho, consultas por O.S. e redução de polling coexistem com limites de animação, memória e busca global ampla. O roteiro de uso, aceitação e integração está em `astra-homologacao-2026-10.md`. Não houve merge ou implantação ASTRA. A correção DOCX SIG01 já aplicada na Central primária permanece em `0931782`; HTTP200 conferido ao finalizar. Modelos, assinatura e conteúdo real de casos não foram publicados.

## Pedido posterior — FP01

Após o fechamento acima, o operador pediu atividade e estimativas na fila de extração. Módulo novo `fila-progresso.js`, descrições por etapa, tempo decorrido, estimativa por arquivo/espera/término e total, com cálculo insuficiente e atraso explícitos; CSV não repete página antiga do OCR. Aplicado somente à interface da Central primária, sem reiniciar servidor/worker; RP01 e demais trechos preservados. Portado ao ASTRA mantendo broker/geração/intervalos do polling. Descrição, limites e evidências em `fila-progresso-2026-10-14.md`.

Validação posterior: nove FP01 na primária e na ASTRA,26 testes F01/UX01/consentimento,7 RP01,4 AST16,7 política15,5 UI15 e E2E17 repetido1/1 em25,101s. A fixture15 foi ajustada à nova descrição com verificação de todas as transições/status e página40/70. Etapa desconhecida e cancelamento foram reproduzidos antes de corrigir a apresentação. A rodada101/103, o manifesto214 e os benchmarks acima permanecem evidências do snapshot anterior; não foram repetidos integralmente para FP01. O último ajuste de cancelamento teve os9 testes FP01 repetidos nas duas fontes.
