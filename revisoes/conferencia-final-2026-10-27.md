# Conferência independente FV01 — 27/10/2026

Responsável: Codex-FV01. **Revisão técnica concluída em 27/10/2026.** O fechamento FV01 ao final deste documento substitui as pendências históricas sobre gate final, aplicação do código e reindexação. As rodadas anteriores permanecem como histórico, com seus escopos, métodos, resultados e limites.

**Estado final vigente:** 341 fontes atuais conferidas por SHA-256. O gate de 145/145 suítes, com oito cenários ambientais ignorados, corresponde ao snapshot anterior aos deltas RG41 e títulos DOCX. RG41 tem 61 testes dirigidos registrados, incluindo 12 reexecutados por FV01; o delta de títulos tem 23 testes registrados, incluindo seis F04 reexecutados por FV01. São quatro arquivos alterados desde o gate, discriminados no último adendo; não houve novo full. A revisão distingue resultados próprios e evidências documentadas, sem certificar semântica de IA real, autos ou DOCX operacional. Esta atualização documental não declara publicação no GitHub, merge nem entrega oficial de caso.

## Escopo e método

Leitura de instruções, memória central, código de limpeza, consolidador de checkpoints, testes focais e revisões genéricas. Sem consulta a autos, configurações privadas, ZIPs/manifestos operacionais ou nomes de casos. Única escrita de produto desta frente: este documento. Testes e reprodução adicional executados exclusivamente com fixtures sintéticas em TEMP, sem API/rede, limpeza/reindexação operacional ou full concorrente.

Foram aplicadas `scope-guard`, `no-gold-plating` e `verification-before-completion`. A regra de memória central foi lida no candidato, pois ainda não existia na pasta original durante esta etapa.

## Evidência independente executada

Runtime confirmado: `F:/CPJ - TRABALHO/.venv/Scripts/python.exe`, **Python 3.12.14**. Comandos no candidato, com `PYTHONDONTWRITEBYTECODE=1`:

```powershell
& 'F:/CPJ - TRABALHO/.venv/Scripts/python.exe' -X utf8 plugin/investigacao-cpj/app/testes/teste_limpeza_sz02.py -v
& 'F:/CPJ - TRABALHO/.venv/Scripts/python.exe' -X utf8 plugin/investigacao-cpj/app/testes/teste_extracao_markdown_md01.py -v
```

| Verificação | Resultado desta frente | Alcance |
|---|---|---|
| SZ02 | 9 testes, OK, exit 0, zero skips, 0,847 s | Arquivamento/restauração com igualdade de todos os hashes fictícios; preservação PDF/MD/estado/desconhecidos; corrupção, plano alterado, escape e junction recusados. |
| MD01 | 4 testes, OK, exit 0, zero skips, 3,241 s | PDF sintético e Central produzem Markdown/O.S. e um checkpoint; retomada/qualidade/pendência preservadas; legado sem hash recusado; divergência não declarada equivalente. |
| Junction no helper isolado | Reprodução adicional em TEMP, exit 0 | `compactar_legado` aceitou `.checkpoint` como junction para outra pasta ainda interna ao documento e criou `estado.json` no alvo. Ver ressalva abaixo. |

Os testes não validam acurácia de OCR em autos reais, comportamento semântico de modelo de IA ou preservação operacional de todo o acervo.

## Preservação, equivalência e retorno

`ferramentas/limpar-derivados.py` seleciona somente nomes conhecidos sob `casos/<caso>/01-extracao/<documento>/`. PDFs, Markdown, `.checkpoint/estado.json`, estado do caso, análises, relatórios e nomes desconhecidos não integram a allowlist. Antes da seleção, exige checkpoint versão 2 com páginas de texto válidas, hash coerente com o relatório, hash correspondente a PDF original presente no mesmo caso e cabeçalhos Markdown de todas as páginas. Isto verifica presença/rastreabilidade estrutural, não equivalência semântica entre cada trecho Markdown e a imagem original.

Arquivos legados de relatório, qualidade, meta e páginas só são selecionados se o JSON decodificado for igual ao valor consolidado. `compactar_legado` preserva os arquivos antigos, relê o estado gravado e retorna somente nomes cobertos por igualdade de conteúdo JSON; o estado já existente prevalece sobre legados divergentes. Essa igualdade ignora diferenças de formatação JSON e não é uma afirmação de igualdade byte a byte.

A limpeza revalida o plano e os caminhos, exige ZIP externo novo, verifica membros únicos e correspondência exata ao manifesto, CRC, tamanho e SHA-256. Verifica novamente o ZIP final e os hashes das fontes antes de iniciar a exclusão e a cada arquivo. A restauração valida o ZIP e todos os destinos antes da primeira escrita, recusa sobrescrita divergente e confere o hash restaurado. Os testes focais confirmaram restauração integral do workspace fictício e recusa de backup truncado/membro duplicado.

O limpador usa `lstat` e `FILE_ATTRIBUTE_REPARSE_POINT` em toda a ancestralidade de caminhos, além de conter caminhos resolvidos sob a raiz. O teste de junction executou efetivamente neste Windows, sem skip.

**Ressalva concreta do helper, comunicada ao coordenador:** `estado_extracao.compactar_legado`, linhas 58–95, não possui a mesma recusa geral de reparse do limpador. Sua checagem de `is_symlink` e contenção por `resolve` permite junction interna. Reprodução fictícia: `.checkpoint` apontando para `doc/destino-interno`, retorno `compactado=true`, três legados cobertos e novo estado criado no destino. Isso não demonstrou exclusão nem escape externo e não invalida a recusa do limpador. A rotina operacional deve comprovar guarda equivalente a `sem_link` antes da compactação; a evidência do chamador permanece pendente. Nenhuma correção de produto foi feita por esta frente.

## Matriz de requisitos e pendências

| Requisito | Já comprovado nesta etapa | Pendente para fechamento global |
|---|---|---|
| Combinar `origin/main` 2ce862d com mudanças locais | Revisão genérica de sincronização registra base remota e preservação local; fila registra SX01 concluída. | Conferência final do coordenador sobre snapshot integrado e resultados. Documento de sincronização lido ainda contém estado histórico anterior à integração. |
| Novos PDFs somente Markdown e checkpoint essencial | MD01 4/4 reexecutado independentemente, sem CSV/JSON analítico. | Gate integral do snapshot final e propagação operacional. |
| Excluir desnecessários preservando originais/estado | SZ02 9/9 reexecutado, restauração fictícia integral e reparse recusado pelo limpador. | Evidência agregada SZ03: total arquivado/removido, verificações ZIP/SHA-256, hashes preservados e verificação do chamador antes de compactar. Nenhum manifesto privado foi lido aqui. |
| Memória central e preferência coordenador Astra/executores Sol/Terra/Luna | `MEMORIA.md` centraliza fontes vivas e a preferência com limite de custo/capacidade, sem trocar runtime/ativar API. AV01 registra revisão independente e resolução do conflito sobre O.S. ausente. | Integração dos testes MM01/SE01 no gate final. Resultados 8/8 e 7/7 são evidência documental da outra frente, não reexecução FV01. |
| Auditor existente complementado | Revisão AV01 registra hipóteses alternativas, reconciliação financeira, lacunas e parecer fundamentado, sem percentual inventado. | Gate final e conferência humana; não há prova de cumprimento semântico por IA real. |
| RAG textual e consulta estruturada sem CSV de trabalho | Revisão RG40 inicial comprova busca textual rastreável. | Coordenador informou correção em andamento para preservar funções estruturadas; a revisão inicial ainda relatava entidades/cruzamentos vazios. Não tratar essa limitação histórica como resultado final nem a correção como aprovada sem nova evidência. |
| Suíte completa | Nenhuma execução full por FV01. Duas fixtures IV01 possuem evidência separada: AST06 27/27 e AP39 5/5, sem skips. | Full inicial ainda em execução/triagem. Segundo coordenador, AST16 ainda falhou por expectativa de um CSS diante de dois CSS locais; AST17 e E2E F03 aguardam triagem. Correção das duas fixtures iniciais não prova gate global. |

## Identificação das fontes focais

SHA-256 observado após os testes; qualquer alteração posterior exige reavaliar o arquivo alterado e os testes afetados:

| Arquivo | SHA-256 |
|---|---|
| `ferramentas/limpar-derivados.py` | `3ac8a033c90dd3790efd5121ef5d9850838ec6ca30856fa6d18d141061b17f47` |
| `plugin/investigacao-cpj/skills/pdf-autos-policiais/scripts/estado_extracao.py` | `2662f86728ae150759237a1c7e8875052efc899cf9d49ebef1c53f6c98577a51` |
| `plugin/investigacao-cpj/app/testes/teste_limpeza_sz02.py` | `8ffc266cdd90dff9314842680efc9d004f0ee2ca8125ac5721b112559803d579` |
| `plugin/investigacao-cpj/app/testes/teste_extracao_markdown_md01.py` | `efece47d7def92e4bbabc09fd87c87d14b7cc09341e50ad9d2c7f13a2936e549` |

**Parecer desta etapa:** os cenários focais de extração, preservação e retorno estão aprovados nas fixtures executadas. A entrega global continua pendente das evidências discriminadas, sobretudo gate integral, RG40 e aplicação agregada SZ03. Esta revisão será complementada por evidências posteriores sem repetir verificações de fontes que não mudaram.

## Complemento FV01 — fontes corrigidas e limpeza aplicada

A FV01 foi reaberta e assumida novamente pelo script da fila, mediante pedido expresso da coordenação. As conclusões anteriores permanecem como histórico. Este complemento representa o estado mais recente examinado, ainda sem gate global.

### Nova execução independente

Mesmos runtime e comandos da primeira rodada, acrescentando `-X utf8 plugin/investigacao-cpj/app/testes/teste_rag_markdown_rg40.py -v`. Todos os subprocessos de indexação destes testes usaram `CPJ_WORKSPACE` em TEMP; nenhum índice/caso operacional foi modificado.

| Teste focal | Resultado reexecutado por FV01 | Evidência |
|---|---|---|
| SZ02 | 9/9, zero skips, exit 0, 1,088 s | Preservação, ZIP verificado, retorno integral e recusa de caminhos/junctions continuam aprovados. |
| MD01 atualizado | 5/5, zero skips, exit 0, 4,063 s | Inclui junction interna nativa Windows: compactação recusada, lista de equivalentes vazia e nenhum `estado.json` criado no destino da junction. |
| RG40 e RI01 | 11/11, zero skips, exit 0, 5,360 s | Busca textual, entidades/cruzamento/grafo provenientes do Markdown, filtros, incerteza, reconstrução e manutenção sem baixa. |

**Achado de junction encerrado nas fontes examinadas.** `estado_extracao._sem_reparse` percorre ancestrais por `lstat` e recusa symlink ou `FILE_ATTRIBUTE_REPARSE_POINT`. `arquivo` aplica a guarda; `compactar_legado` a chama antes da enumeração, valida cada legado antes da leitura e usa a mesma guarda no caminho de gravação. O teste reproduz o alvo interno da primeira rodada e confirma a recusa. Não houve mudança no limpador SZ02; seus nove testes foram repetidos após a correção do helper.

**Funções estruturadas preservadas sem intermediários documentais.** A inspeção de `entidades.iter_candidatos` e do fallback em `indexar.py`, junto dos onze testes reais de CLI/SQLite, confirma extração em memória para o índice existente. Os candidatos mantêm documento Markdown, página, linha, trecho e status `pendente de conferência`, sem converter candidato em fato confirmado. Comentários HTML, tokens com `?`/caractere de substituição e anotações de incerteza exercitadas no teste não viram identificadores completos. O mesmo trecho de CPF/CNPJ não fabrica telefone sobreposto. O CSV legado continua tendo precedência somente no próprio documento; a CLI CSV explícita permanece compatível.

O teste RI01 compara bytes, SHA-256 e status de `caso.json` antes/depois de `--tudo --sem-baixa` e `--so-base --sem-baixa`, preservados. Sem a opção, a fixture elegível continua recebendo a baixa automática prevista. Isso comprova o contrato de manutenção testado, não a execução operacional da manutenção.

### Limpeza real: evidência agregada da frente SZ03

Foi lido somente o registro genérico `revisoes/limpeza-aplicada-2026-10-27.md`, confrontado com os totais comunicados pelo coordenador. FV01 não abriu o ZIP privado, seu manifesto, os 1.188 arquivos reais nem o inventário detalhado; os resultados abaixo são evidência operacional registrada pela frente responsável, distinta da restauração sintética reexecutada independentemente.

| Verificação SZ03 | Resultado registrado |
|---|---:|
| Documentos consolidados / bloqueados e preservados | 85 / 16 |
| Markdown faltantes criados sem substituir preexistentes | 89 |
| Derivados removidos | 36.878 arquivos / 981.352.481 bytes |
| ZIP privado externo | 343.180.955 bytes |
| Membros verificados contra manifesto privado | 36.878 |
| PDFs/Markdown/originais protegidos, tamanho e SHA-256 intactos | 1.188 arquivos |
| Derivados reconhecidos deliberadamente preservados | 4.705 arquivos |
| Reparse points nos 85 estados consolidados e ancestrais auditados | Zero |

O registro declara verificação do ZIP antes e depois da exclusão, igualdade de tamanho/hash dos protegidos, conservação dos documentos incompletos/divergentes e dos estados essenciais, sem remoção de diretórios ou sobrescrita dos Markdown. A rotina de compactação corrigida e a auditoria de zero reparse encerram a pendência operacional específica levantada na primeira rodada. **Não há evidência nesta frente de uma restauração real dos 36.878 itens:** há ZIP individualmente verificado pela frente SZ03 e restauração integral de fixtures comprovada por FV01. Não confundir esses alcances.

### Matriz atualizada de integração e limites

| Item | Situação no complemento |
|---|---|
| MD01/SZ02 e achado de junction | Comprovados independentemente nesta rodada: 14 testes verdes e zero skips. |
| RG40/RI01 | Comprovados independentemente: 11 testes verdes, candidatos estruturados sem CSV e manutenção que preserva o estado do caso. A limitação inicial de entidades/cruzamentos vazios foi superada. |
| Limpeza operacional SZ03 | Concluída conforme registro agregado lido e evidência da frente responsável; arquivos privados não inspecionados por FV01. |
| IV02: identificadores incertos | Coordenação informa correção de defeito real de normalização e 54 testes verdes. FV01 não reexecutou esses 54 testes nem os apresenta como resultado próprio. O teste do parser RG40 reexecutado confirma os cenários de incerteza que ele contém. |
| AST17 e F03 | Registro IV01 atualizado lido: AST17 1/1 e F03 2/2, zero skips, com fixtures sintéticas. Não reexecutados por FV01. |
| AST16 | Coordenação informa 4/4 após correção da expectativa de CSS; não reexecutado por FV01. |
| Full inicial | **Não concluído.** Coordenação registrou erro de I/O no log em F: com mensagem de volume alterado externamente. Resultados parciais servem apenas como histórico, não aprovação global. |
| Full final | Em execução segundo coordenação, log genérico em TEMP no volume C:. Sem placar final nesta revisão; não foi iniciado outro full por FV01. |
| Congelamento | Coordenação registrou 340 fontes por hashes em inventário privado. FV01 não abriu esse inventário; os hashes focais atuais estão abaixo. |
| Sincronização e instalação do código na pasta original | Pendentes de gate integral e conferência do coordenador. Nenhuma instalação executada por FV01. |
| RAG operacional | Backup SQLite consistente/fonte manual e ledger privado estão sob preparação da coordenação; reindexação de manutenção permanece pendente. O teste `--sem-baixa` não prova que o backup ou a reconstrução real já ocorreram. |

O coordenador comunicou que o volume F: é exFAT e o Windows registra `HealthStatus=Warning`. Esta frente não diagnosticou a causa, não atribui a advertência ao código e não executou reparo de volume. Os hashes agregados de arquivos protegidos foram informados como válidos. O erro de I/O não é tratado como sucesso de suíte nem como prova de dano a esses arquivos.

### Hashes focais que substituem versões anteriores

| Arquivo | SHA-256 atual observado |
|---|---|
| `estado_extracao.py` | `13d237ade9d8a8edd1802649e5a366cac119f431041ac5ab44c546d45aecccd3` |
| `teste_extracao_markdown_md01.py` | `df32d19e0aa4c877c4cb9833c4e457de336ab1e6cdd949f03479b465645c8c22` |
| `teste_rag_markdown_rg40.py` | `5135e73ab54b60c1747622b688ea6c5017a4691fdcb1cfcb456607f655ac0ac4` |
| `indexar.py` | `2b38f9f718bdb9f3bd485dbf2a26d683ebd8a9e118803347fccc0cb24167078d` |
| `entidades.py` | `d6ed13602d1a9eb6d5b58150fab5331c1bdd11cd6de3af5e6e916f0a56665d27` |

Hashes do limpador SZ02 e de seu teste permaneceram iguais aos registrados na primeira rodada. **Parecer atualizado:** 25 testes focais passaram nesta rodada, sem skips; o achado concreto de junction está corrigido e a perda de consultas estruturadas foi superada nos cenários testados. Nenhum novo achado concreto surgiu nesta revisão focal. A aprovação global continua pendente do full final e das verificações operacionais de sincronização/backup/reindexação expressamente discriminadas.

## Fechamento FV01 — fonte aplicada, gate final e manutenção

Retomada em 27/10/2026 após a pausa, sob a reserva existente `Codex-FV01`. Este complemento substitui os estados pendentes anteriores. Escopo de escrita restrito a este documento e registro na fila pelo script; nenhum produto, dado de caso ou configuração operacional foi alterado por FV01. Foram aplicadas as skills de limites, ausência de extras e verificação antes da conclusão. A conferência permaneceu técnica: sem abrir autos, bancos operacionais ou manifestos de dados de casos.

### Conferência independente da fonte e do delta

O manifesto privado de **fontes de código**, `F:/CPJ-BACKUPS/sync-github-20261027-023944/fontes-aplicadas.json`, foi lido exclusivamente para comparar os caminhos genéricos de código/testes com a pasta aplicada. Cada caminho foi resolvido sob a raiz autorizada, recusando áreas operacionais. Resultado: **341/341 SHA-256 coincidentes, zero ausentes e zero divergências**. O manifesto do gate, `fontes-gate-final.json`, contém os mesmos 341 caminhos após normalizar separadores. Entre aquele snapshot e o aplicado mudaram somente os dois arquivos do delta RG41, cujos hashes coincidem com a evidência RG41:

| Arquivo | SHA-256 aplicado e conferido |
|---|---|
| `plugin/investigacao-cpj/skills/base-cpj/scripts/indexar.py` | `fc214a57426619363d5db6b652c6aa9a137395ca4392edaf3741edcee6f2cf00` |
| `plugin/investigacao-cpj/app/testes/teste_rag_markdown_rg40.py` | `d7921859f29f8161994b1d4534c45d57636b13259924cee49e0ed7340744b8fa` |

A inspeção confirma cache em memória de `arquivo`, `sha256_original` e `gerado_em`, inclusive resultado vazio/erro, por documento e execução. O leitor consolidado continua sendo chamado; páginas e textos não são mantidos no cache. Foi executado novamente na pasta aplicada, com `PYTHONDONTWRITEBYTECODE=1`, o comando:

```powershell
& 'F:/CPJ - TRABALHO/.venv/Scripts/python.exe' -X utf8 plugin/investigacao-cpj/app/testes/teste_rag_markdown_rg40.py -v
```

**Resultado próprio desta retomada: 12/12 testes, exit 0, zero falhas e zero skips, 6,315 s.** Todos os casos/índices usados são sintéticos em TEMP. O teste RG41 instrumenta o leitor real: uma leitura para cada um dos quatro documentos, 120 evidências preservadas e nova execução observando data modificada. A suíte também confirma manutenção sem baixa, proveniência, candidatos incertos, precedência documental do CSV legado, filtros e reconstrução. Os outros 49 testes do total dirigido de 61 constam da evidência `indexacao-cache-2026-10-27.md`; não foram reexecutados nesta frente nem somados como testes próprios.

### Gate integral e limites de ambiente

Foi conferido o log `C:/Users/Usuario/AppData/Local/Temp/cpj-full-gate3-20261027.log`, SHA-256 `b1ddf42f83cda29ec9e66efc808fb6da49d0f47ea43d937442447034145b1af8`. Seu encerramento registra **145/145 suítes aprovadas em 686,80 s**, incluindo a Central isolada. O retorno zero está registrado pela coordenação em `sincronizacao-github-2026-10-27.md` e `reindexacao-aplicada-2026-10-27.md`. FV01 não iniciou outro full e não apresenta essa execução como própria. O gate refere-se à fonte anterior ao cache; o delta posterior é coberto pelos 61 testes dirigidos registrados e pelos 12 testes reexecutados acima.

Oito cenários permanecem explicitamente ignorados: um symlink em UN16, quatro em RV17, dois em RP33 e um cenário físico de volume em SEC22. O log resume este último apenas como `skipped=1`; a fonte de SEC22 e o registro do coordenador identificam o requisito exFAT indisponível no volume da execução. Não se atribui aprovação a esses oito cenários. Junctions nativas e recuperação concorrente possuem execuções efetivas nas evidências já discriminadas. O alerta histórico do volume F: e os limites de POSIX, IA real e renderização oficial não são eliminados pelo placar de testes.

### Aplicação e preservação operacional registradas

O registro genérico RI02 informa aplicação na branch local `codex/sincronizacao-enxuta-20261027` sobre `origin/main` 2ce862d, backup SQLite pela API online com `integrity_check=ok`, preservação da fonte manual e reconstrução `--tudo --sem-baixa` concluída com retorno zero. Registra 74 arquivos de estado com bytes/SHA intactos, os mesmos 1.188 PDFs/Markdown/originais protegidos intactos, índice íntegro e nenhuma aresta manual preexistente perdida. Estes são resultados operacionais da frente responsável, confrontados com a fila e a revisão genérica; FV01 não reabriu os arquivos protegidos, o banco ou os inventários privados para repeti-los.

A remoção registrada de 981.352.481 bytes em 36.878 derivados permanece distinta da economia líquida: o SQLite cresceu de 583.909.376 para 1.491.718.144 bytes com proveniência/candidatos. A redução de arquivos dispersos foi obtida sem tratar o crescimento do índice como espaço livre. Preservação de incompletos/divergentes e restauração real não ensaiada mantêm os limites registrados anteriormente.

A coordenação também corrigiu descrições documentais antigas em PRD/AGENTS para extração somente Markdown e informou regeneração dos portáteis e verificação dos adaptadores. Essa atualização documental não modifica o produto conferido nos 341 hashes. Não foi sobrescrita por FV01. Não houve commit, publicação, merge/default branch, reinício de serviço, ativação de provedor ou entrega oficial/baixa nesta frente.

**Parecer final:** a conferência técnica FV01 está concluída, sem novo achado bloqueante no escopo examinado. Gate integral, aplicação e reindexação possuem evidências finais e deixam de ser pendências desta auditoria. Permanecem os oito cenários ambientais não executados e os limites de verificação operacional/documental acima; este parecer não certifica conteúdo de autos, qualidade semântica de IA real ou assinatura/entrega oficial de relatório. A continuidade de casos pertence à fila operacional, fora desta reserva.


## Adendo FV01 — delta posterior de títulos DOCX

27/10/2026 — FV01 reaberta e assumida pelo script, sob Codex-FV01, para conferir o delta genérico posterior ao fechamento anterior. Escrita restrita a esta revisão e registro da fila. O gerador e o teste foram somente lidos; nenhum auto, caso, configuração ou DOCX operacional foi consultado nesta frente. A correção operacional de relatório, informada pela coordenação, não foi auditada por este analista.

### Escopo efetivamente comparado

O manifesto `fontes-aplicadas-antes-titulos.json` e as duas cópias genéricas em `delta-titulos-paginacao/`, no backup privado de sincronização, foram confrontados com os arquivos atuais. Os hashes das cópias anteriores coincidem com o pré-estado registrado. A comparação mostra exatamente três linhas adicionadas a `gerar_docx.py`, no laço final dos parágrafos: se `normalizar_titulo(p.text)` pertence a `SECOES_CANONICAS`, definir `keep_with_next=True` e `keep_together=True`. Não houve remoção ou alteração de outras linhas do gerador. O efeito é aplicar ao título canônico as propriedades de manter com o parágrafo seguinte e manter suas linhas juntas, sem acrescentar quebra forçada ou mudar os parâmetros tipográficos.

O único delta do F04 é o teste dos três títulos canônicos: exige três títulos e confere ambas as propriedades em cada um. Os demais testes e suas asserções permanecem iguais. A fixture cria modelo, imagem e documento fictícios em TEMP, com `CPJ_WORKSPACE` isolado, sem copiar modelo ou assinatura operacional.

### Verificação própria e evidência da coordenação

Executado na pasta aplicada, com `PYTHONDONTWRITEBYTECODE=1`:

```powershell
& 'F:/CPJ - TRABALHO/.venv/Scripts/python.exe' -B -X utf8 plugin/investigacao-cpj/app/testes/teste_docx_f04.py -v
```

**Resultado independente FV01: F04 6/6, exit 0, zero falhas e zero skips, 0,328 s.** Verifica propriedades do DOCX e preservação de modelo, tabela, valores, assinatura geométrica e citações nas fixtures. Não é inspeção visual de paginação de um relatório operacional no Word.

O registro privado genérico `delta-titulos-validado.json` informa RED do novo teste nos três títulos antes da correção e GREEN F04 6/6, SIG01 12/12 e RG28 5/5: 23 testes sintéticos, zero skips. O RED, SIG01 e RG28 são evidência registrada pela coordenação; não foram reexecutados por FV01. Os seis testes próprios são subconjunto desse total, não seis testes adicionais a somar aos 23.

### Snapshot atual e alcance do gate

Conferência independente do manifesto atualizado `fontes-aplicadas.json`: **341/341 hashes atuais coincidentes, sem arquivo divergente**. O conjunto de caminhos é o mesmo nos manifestos atual, anterior aos títulos e do gate; separadores foram normalizados somente para a comparação.

| Comparação | Arquivos diferentes |
|---|---|
| Atual versus pré-títulos | `gerar_docx.py` e `teste_docx_f04.py` |
| Atual versus gate integral | Os dois acima, mais `indexar.py` e `teste_rag_markdown_rg40.py` do RG41 |

| Fonte do novo delta | SHA-256 atual conferido |
|---|---|
| `plugin/investigacao-cpj/skills/relatorio-ip-fraude/scripts/gerar_docx.py` | `09d3d20691f04b02d3b6ab67a46e04c3e7888a301441f0a26a2fc3d194289c97` |
| `plugin/investigacao-cpj/app/testes/teste_docx_f04.py` | `1cdf9b7ad9ac26d4b73255f5168f9e3b8b1003983357350ce3bea0def61c07b8` |

O placar 145/145 em 686,80 s continua sendo o gate histórico do snapshot anterior aos dois deltas. Não foi repetido e não é apresentado como full executado sobre os quatro arquivos posteriores. Os oito cenários ambientais não executados e os demais limites registrados permanecem explícitos. RG41 conserva a evidência dirigida de 61 testes e 12 reexecutados; títulos DOCX acrescenta a evidência dirigida distinta de 23 testes e seis reexecutados.

**Parecer do adendo:** delta genérico de títulos conferido, com escopo mínimo e F04 independente aprovado nas fixtures. Não surgiu achado bloqueante nesse delta. O fechamento técnico permanece concluído com o snapshot e os limites acima; sem certificação semântica de IA, conteúdo de autos, paginação de DOCX operacional ou entrega oficial. Nenhuma publicação, merge ou alteração de branch padrão foi realizada por esta frente.
