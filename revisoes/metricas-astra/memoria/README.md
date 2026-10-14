# AST172 — memória dos processos Edge

Complemento da issue 17 aos benchmarks do grafo AST13, executado em **14/10/2026**, Edge headless **155.0.4283.45**, Windows. Janela coordenada sem outras suítes/Edge da equipe, com dados fictícios e os snapshots congelados de `../grafo/snapshots/before.html.gz` e `after.html.gz`. Os hashes comprimidos e originais foram conferidos contra o manifesto AST13 antes de abrir o navegador; os hashes e metadados dos assets estão no resultado bruto. O código do produto não foi alterado.

São 24 amostras: 50/100/500/1000 nós × 10 arestas por nó × três repetições × before/after. Cada par usa a mesma topologia circular determinística e um Edge headless novo por lado, viewport 1440×1000/DPR1. Ordem por tamanho: before/after, after/before, before/after. Não se reaproveita o browser de uma amostra anterior.

O adaptador neutraliza apenas o bootstrap `iniciar()`. Monta o grafo completamente expandido, suprime RAF, executa os mesmos três aquecimentos e vinte chamadas física/desenho do microbenchmark AST13, espera **1.000 ms fixos** e coleta os processos. Confere nós/arestas recebidos, visíveis por categoria e projetados: `n` e `n×10`. O layout anterior é aleatório; o posterior usa sementes por ID e rótulos adaptativos. Isto mede o estado depois desse trabalho fixo, sem afirmar convergência ou igualdade de coordenadas.

`SystemInfo.getProcessInfo` da sessão CDP do browser fornece os PIDs e tipos dos processos pertencentes àquela instância. `working-set.ps1` chama `Get-Process -Id` somente para esses PIDs e lê `WorkingSet64`. O JSON conserva cada PID, tipo CDP, nome, valor individual, total por tipo, soma e horários. Falha/saída de processo invalida a amostra; não se substitui por zero. O instrumento permite até três tentativas, cada uma com browser e montagem novos, para completar a mesma amostra lógica; todas são preservadas, mas o resumo usa somente as completas. **Este critério pode enviesar o resultado em favor de estados sem processos transitórios encerrando durante a leitura.** Heap JavaScript é coletado separadamente por `Performance.getMetrics` da página. O campo CDP `cpuTime` é preservado como dado de origem, sem conversão para percentual ou comparação de CPU.

**A soma dos working sets pode contar páginas compartilhadas várias vezes. Não representa memória privada nem RAM total do sistema.** Não inclui Node, PowerShell ou outros programas. É uma leitura pontual sequencial, sem GC forçado; não mede pico, vazamento, carga operacional ou economia geral de memória. Três repetições são poucas: p95 nearest-rank é o máximo das três observações. O host permanece sujeito a ruído do Windows e caches, mesmo durante a janela sem outras suítes/Edge.

Para reproduzir, coordenar uma nova janela e escolher uma saída absoluta ainda inexistente:

```powershell
$runtimeAstra = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/node'
$env:NODE_PATH = Join-Path $runtimeAstra 'node_modules'
& (Join-Path $runtimeAstra 'bin/node.exe') revisoes/metricas-astra/memoria/measure-memory.cjs "$env:TEMP\astra-memoria-nova.json" --execute-frozen
```

O script recusa sobrescrever resultados.

## Resultado observado

`results-working-set-complete.json`: execução principal de **19:49:31 a 19:51:33 UTC**, **24 amostras completas e três tentativas incompletas**, todas preservadas. Cada amostra completa apresentou nove processos: browser, dois renderers, GPU e serviços auxiliares CDP (rede, armazenamento, extração, identidade e coleções). Os três processos que encerraram antes da leitura eram `PooledProcess2`; suas leituras ausentes continuam `null`. Não houve erro de página nem requisição externa. Nós/arestas recebidos, visíveis por categoria e projetados foram conferidos em todas as tentativas, incluindo as inválidas.

Valores em **MB decimais** (1 MB = 1.000.000 bytes). A soma de working sets e o heap são métricas separadas:

| Nós/arestas | Soma working sets p50 antes → depois | Soma working sets p95 antes → depois | Heap usado p50 antes → depois |
|---|---:|---:|---:|
| 50/500 | 508,31 → 498,19 | 511,43 → 505,60 | 3,22 → 3,16 |
| 100/1000 | 527,45 → 510,07 | 528,83 → 512,71 | 3,44 → 4,44 |
| 500/5000 | 565,92 → 542,05 | 566,12 → 543,72 | 9,90 → 10,86 |
| 1000/10000 | 601,08 → 632,56 | 604,40 → 643,13 | 14,27 → 17,96 |

Nesta coleta pontual, a soma dos working sets diminuiu em 50/100/500 nós e aumentou em 1000. O heap usado aumentou em 100/500/1000. **Não há evidência de melhoria geral de memória**, nem comparação de RAM privada ou pico. Os valores de heap diferem dos brutos AST13, que usavam outro ciclo de vida (contexto mantido e animação longa); não misturar as duas metodologias. Este complemento mede carga de montagem/desenho, sem executar a fila/API operacional nem o backend Python.

## Tentativas preservadas e integridade

`attempt-1-reader-array.json`: primeira tentativa interrompida antes de armazenar amostras, porque o leitor PowerShell 5 recebeu o array JSON como item único. Atribuição direta de `ConvertFrom-Json` corrigiu o instrumento; não houve alteração do produto.

`attempt-2-process-exit.json`: segunda execução interrompida na 11ª amostra (dez completas e uma incompleta), por `PooledProcess2` que encerrou entre enumeração e leitura. Os valores existentes foram preservados, sem substituir o ausente por zero. Em seguida foi acrescentada a repetição limitada com browser fresco; a execução principal recomeçou inteira em arquivo novo. Nenhuma dessas dez amostras preliminares entra na tabela. Ao todo há **38 registros brutos de tentativas com inventário de processos** nas duas execuções, dos quais **quatro incompletos**, além da falha inicial do leitor sem amostra. Repetir somente inventários completos pode selecionar estados menos transitórios; os dados não eliminam esse viés.

`verify-results.py` verifica, sem iniciar navegador: 24 amostras completas únicas, três repetições por lado/tamanho, contagens expandidas, PIDs únicos, somas individuais e por tipo, ausência preservada, resumo p50/p95, erros/rede e hashes dos snapshots. `checksums.json` registra SHA-256 dos scripts, brutos e README. A fonte HTML anterior tem SHA-256 `5763aa11d30773986793694394bef1c66af7c895e2e9bf24e942e4131188933f`; a posterior, `7839418c48885281d5c18ac5f08d9efb1c1cfe5dacdb2e60ea0cbc9be9d629fd` (snapshot primário13, grafo `11cabe61d640a6e3697cd2b701620605733a0d914f08ed0b6d8fb1e5f6a3b882`). Nenhum snapshot anterior foi sobrescrito.
