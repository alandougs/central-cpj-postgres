# ASTRA #14 — SQL/API: antes e depois

Baseline: revisão `f56653cb2c0081f4815d9bccbd0edc1cdfef74fb`. Depois: snapshot dos arquivos de trabalho da AST14, com hashes em `after.json`; os cinco arquivos registrados foram comparados com o worktree e permanecem idênticos. O snapshot anterior em TEMP não foi modificado. `baseline_method.py` é cópia binária idêntica do script original (SHA-256 `85d276d3a24d4e0f0780a24b415a953e502374b791ddc6185d6c10aeb0a1bc34`).

Os seis datasets fictícios de 100/500/1.000 O.S., esparsos/densos, usaram o mesmo gerador e worker: quatro consultas, um aquecimento e cinco amostras por consulta, totalizando **120 GET medidos + 24 aquecimentos**. Todos retornaram HTTP 200; os totais atuais coincidiram com o oráculo em todas as amostras. Os seis SQLite mantiveram seus hashes antes/depois. A medição foi executada em janela sem outras suítes/benchmarks da equipe. Não houve autos, usuários, credenciais operacionais ou API externa.

Os novos índices foram aplicados antes da medição; criação de índice não faz parte da latência de GET. O helper constrói a contagem e a página na mesma transação de leitura, hidrata todas as fontes das relações selecionadas e lê rótulos em lote. A listagem do cadastro continua verificando stat a cada GET; apenas JSON inalterado é reutilizado. Alterações externas, inclusão/remoção de O.S. e mudança concorrente em WAL foram testadas. Nenhum GET executa DDL/DML; BEGIN é somente de leitura.

## Resultados completos

Valores de latência em ms. SQL = número de instruções por GET, incluindo BEGIN de leitura. p50/p95 usam cinco amostras; p95 nearest-rank equivale ao máximo. O callback SQLite de contagem acrescenta custo.

| Casos | Densidade | Consulta | p50 antes | p95 antes | p50 depois | p95 depois | SQL antes → depois |
|---:|---|---|---:|---:|---:|---:|---:|
| 100 | sparse | general | 55.28 | 64.47 | 116.71 | 137.12 | 105 → 11 |
| 100 | sparse | case | 37.53 | 40.50 | 14.55 | 14.87 | 31 → 8 |
| 100 | sparse | partial-global | 110.62 | 138.76 | 205.13 | 222.78 | 307 → 12 |
| 100 | sparse | partial-case | 81.65 | 83.62 | 21.65 | 21.73 | 236 → 9 |
| 100 | dense | general | 325.34 | 423.24 | 265.00 | 284.01 | 57 → 10 |
| 100 | dense | case | 120.97 | 136.66 | 95.80 | 97.45 | 207 → 11 |
| 100 | dense | partial-global | 142.56 | 167.85 | 1292.29 | 1346.35 | 304 → 11 |
| 100 | dense | partial-case | 562.25 | 629.80 | 111.74 | 120.36 | 304 → 12 |
| 500 | sparse | general | 397.81 | 575.93 | 189.78 | 204.62 | 105 → 11 |
| 500 | sparse | case | 231.38 | 249.60 | 25.97 | 26.28 | 31 → 8 |
| 500 | sparse | partial-global | 460.00 | 617.49 | 613.15 | 638.51 | 307 → 12 |
| 500 | sparse | partial-case | 271.61 | 356.29 | 37.61 | 42.56 | 236 → 9 |
| 500 | dense | general | 1357.61 | 1451.15 | 918.68 | 959.34 | 57 → 10 |
| 500 | dense | case | 403.18 | 461.47 | 111.06 | 124.84 | 207 → 11 |
| 500 | dense | partial-global | 382.23 | 447.83 | 6528.27 | 6599.03 | 304 → 11 |
| 500 | dense | partial-case | 955.15 | 1631.54 | 123.90 | 140.28 | 304 → 12 |
| 1000 | sparse | general | 698.32 | 2136.46 | 261.53 | 276.10 | 105 → 11 |
| 1000 | sparse | case | 380.44 | 408.57 | 40.31 | 46.73 | 31 → 8 |
| 1000 | sparse | partial-global | 409.97 | 713.16 | 1190.88 | 1198.93 | 307 → 12 |
| 1000 | sparse | partial-case | 494.43 | 584.33 | 48.08 | 48.82 | 236 → 9 |
| 1000 | dense | general | 2379.63 | 2813.19 | 1882.01 | 2017.14 | 57 → 10 |
| 1000 | dense | case | 690.78 | 804.50 | 128.73 | 150.67 | 207 → 11 |
| 1000 | dense | partial-global | 703.47 | 717.61 | 13312.49 | 13432.95 | 304 → 11 |
| 1000 | dense | partial-case | 1174.51 | 1261.24 | 142.67 | 152.84 | 304 → 12 |

## Completude e limites

Cada página atual contém no máximo 400 relações lógicas, cada qual com todas as evidências. `total` é o universo exato do escopo; a ordenação binária crescente é `(a_tipo,a_valor,b_tipo,b_valor,relacao)`. Busca considera todas as sementes e até dois saltos, sem propagar identidade pelo nó NOME. `truncado` indica página parcial; `proxima_pagina` permite continuar. O parâmetro opcional `revisao` vincula páginas ao mesmo estado/escopo/limite e responde 409 quando índice, manuais ou conferências mudam. Sem índice, `total:null` e `total_disponivel` representam somente manuais acessíveis, com aviso de incompletude.

As amostras atuais abriram uma conexão SQLite, executaram de 8 a 12 instruções e não releram cadastros JSON após o aquecimento. A leitura/stat de diretórios continua incluída no tempo. O baseline abria até 31 conexões e executava até 307 instruções; relia todos os N cadastros.

**Não há ganho universal de latência.** Em 1.000 casos densos, a busca global subiu de p50/p95 703,47/717,61 ms para 13.312,49/13.432,95 ms. O código anterior mostrava somente 90 relações, com corte de 30 sementes e sem total; o atual conta 490.000 relações e devolve 400 com fontes completas. A busca global ampla tem custo material; não é adequado descrevê-la como rápida. Na mesma escala, consultas por O.S. ficaram em p50/p95 128,73/150,67 ms e busca por O.S. em 142,67/152,84 ms.

O baseline é anterior às mudanças de proveniência/conferência P0/P1: conteúdo e tamanho de resposta diferem. Os dados não demonstram uma comparação de trabalho idêntico nem uma melhoria isolada por índice. Tempos incluem rota, SQL, cadastro, serialização e corpo da resposta Flask; não incluem TCP, navegador, OCR ou indexação. Caches do SO não foram esvaziados. A janela atual foi controlada pela equipe, mas carga externa do host e a carga da janela histórica não são controladas retrospectivamente.

Os campos antigos `omittedUniqueRelations`/`omittedReferences`, mantidos pelo worker, são diferenças em relação à página retornada; na versão atual não significam perda de fontes nem perda das páginas seguintes. Não houve medição de todas as páginas ou de carga concorrente.

O campo `fixture.queryPlans` foi herdado do gerador original: contém sondas SQL antigas, coletadas antes de aplicar os índices atuais. Não descreve a consulta atual da API. `currentSourceIndexPlan` registra a sonda simples por fonte após os índices; os planos reais das quatro consultas atuais estão em `planos-atuais.json`.

## Artefatos e reprodução

- `baseline.json`: todas as amostras anteriores; fonte original preservada em TEMP.
- `after.json`: todas as amostras atuais, hashes, índices, metadados e limites retornados.
- `comparacao.json`: comparação estruturada dos 24 cenários.
- `planos-atuais.json`: 24 EXPLAIN QUERY PLAN das consultas atuais, compilados fora das medições, sem GET adicional e sem executar o SELECT principal; hashes dos bancos novamente conferidos. O hash do template SQL e o hash de rag.py permitem reconstruir a consulta pelo script.
- `benchmark_sql.py`: wrapper do gerador/worker original, aplica somente índices atuais antes das medições e exige totais corretos.
- `planos_sql.py`: gera os planos atuais sem executar as consultas principais.

Use uma cópia congelada do código e uma pasta TEMP nova/vazia; os workers recusam sobrescrever datasets. Nenhum caminho de dados operacionais deve ser passado.

```powershell
& 'C:\CPJ - TRABALHO\.venv\Scripts\python.exe' -X utf8 benchmark_sql.py --codigo '<SNAPSHOT-CODIGO>' --saida '<TEMP-NOVA>'
& 'C:\CPJ - TRABALHO\.venv\Scripts\python.exe' -X utf8 planos_sql.py --codigo '<SNAPSHOT-CODIGO>' --medicao '<TEMP-NOVA>'
```
