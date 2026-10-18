# ASTRA #13 — grafo: medições sintéticas

Execuções em 14/10/2026, no mesmo Windows e Edge headless **155.0.4283.45**, viewport **1440×1000**, DPR **1**. Janela coordenada sem suítes/Edge dos outros agentes; o computador continuou compartilhado, sem promessa de isolamento do sistema operacional. Nenhum caso, configuração, banco operacional ou serviço externo foi acessado.

## Resultado primário, completamente expandido

**80 execuções**: 40 antes e 40 depois, cada lado com 50/100/500/1000 nós × 2/10 arestas por nó × cinco repetições. Todas terminaram sem timeout, erro de página ou requisição externa. O verificador confirmou, em cada amostra, os mesmos nós/arestas recebidos, visíveis por categoria e presentes na projeção expandida: `n` e `n*d`. O ganho abaixo não vem de agrupamento ou retirada de nós/arestas. Relações não destacadas em redes com mais de 300 conexões têm menos rótulos; esse componente foi medido separadamente.

Tempos em milissegundos; FPS é derivada dos intervalos entre **ticks**, não medida do compositor/GPU.

| Nós/arestas | Montagem p50 antes → depois | Física p95 | Desenho p95 | Intervalo tick p95 | FPS derivada p50 |
|---|---:|---:|---:|---:|---:|
| 50/100 | 1,40 → 1,90 | 0,10 → 0,40 | 0,90 → 0,70 | 17,10 → 17,20 | 59,9 → 59,9 |
| 50/500 | 3,30 → 2,40 | 0,30 → 0,20 | 2,20 → 1,50 | 17,00 → 17,30 | 59,9 → 59,9 |
| 100/200 | 2,10 → 2,60 | 0,20 → 0,30 | 1,20 → 1,00 | 17,00 → 17,10 | 59,9 → 59,9 |
| 100/1000 | 5,70 → 4,00 | 0,50 → 0,30 | 25,10 → 2,00 | 16,90 → 17,00 | 59,9 → 59,9 |
| 500/1000 | 9,60 → 9,90 | 1,50 → 1,80 | 26,20 → 2,20 | 17,00 → 17,50 | 59,9 → 59,9 |
| 500/5000 | 47,10 → 18,60 | 3,20 → 2,10 | 134,40 → 10,70 | 41,20 → 24,60 | 29,1 → 49,5 |
| 1000/2000 | 20,10 → 16,70 | 4,70 → 4,20 | 29,50 → 2,80 | 17,60 → 17,60 | 60,2 → 59,9 |
| 1000/10000 | 91,20 → 42,30 | 8,40 → 6,20 | 182,30 → 16,10 | 52,20 → 35,60 | 23,6 → 34,6 |

**Limites e regressões:** 50/100 nós mantiveram aproximadamente 60 ticks/s, com pequenas regressões de montagem/física em parte dos cenários. As redes densas melhoraram, mas não atingiram 60 ticks/s nem o orçamento de 16,7 ms por frame em todos os casos. Todas as 40 execuções posteriores pararam no **teto de 360 ticks**, não por convergência medida. A versão anterior executou 213 ticks; a duração p50 passou de aproximadamente 3,56 s para 5,98 s em 50/100 e de 8,97 s para 10,52 s em 1000/10000. Não se afirma redução geral de duração ou estabilização física nessas fixtures.

CDP `TaskDuration` p50 em 50/100 aumentou de **0,480 para 1,058 s**; em 1000/10000 caiu de **9,477 para 4,404 s**, apesar da animação mais longa. São durações acumuladas do renderer durante a amostra, **não percentual de CPU do Windows/GPU**. O heap usado observado em 1000/10000 aumentou de **23,13 para 38,13 MB** (decimal); não houve GC forçado, isolamento de pico ou teste de vazamento. Não há alegação de economia geral de memória.

## Ablações separadas

Cada ablação tem mais 40 amostras, mesmas topologias/tamanhos/repetições, 3 aquecimentos e 20 chamadas medidas. **Sem animação longa e sem alegação de FPS**; não misturar seus dados com o primário.

| Cenário | Expandido adaptativo p95 desenho | Rótulos completos p95 | Agrupamento visual p95 |
|---|---:|---:|---:|
| 500/5000 | 10,70 ms | 90,10 ms | 26,00 ms |
| 1000/10000 | 16,10 ms | 117,70 ms | 106,40 ms |

O nível de texto explica parte substancial do ganho. O agrupamento preserva os dados e facilita expansão/inspeção, mas foi **mais lento** que o expandido adaptativo nessas fixtures, inclusive pelo desenho de rótulos agregados e construção da projeção. Não se afirma ganho de desempenho por agrupamento. Quantidades originais e projetadas de cada amostra constam dos brutos/comparação; relações internas de grupos continuam acessíveis no inspetor, mesmo sem segmento externo desenhado.

## Método e snapshots

O baseline histórico original permanece intacto em TEMP `cpj-astra-baseline-5f2d3d0885`; sua cópia completa está em `historical-results.json.gz`. O primário novo pareado está em `results-paired-before.json.gz` e `results-paired-after.json.gz`. O before foi repetido imediatamente antes do after na janela coordenada; não foi comparado apenas com uma execução antiga sob carga diferente.

`benchmark-original.cjs` é a cópia literal do harness histórico. `prepare_benchmark.py` expande recursos CSS/JS locais na ordem clássica do HTML, registra hashes e neutraliza somente o bootstrap `iniciar()`, como o harness original. HTML anterior inline e posterior modular passam pelo mesmo carregador. Não há framework, CDN, backend ou provedor externo. O resto do HTML/JS foi congelado, inclusive funções não executadas; diferenças de código entre snapshots estão documentadas pelos hashes de assets em `snapshots/*.sources.json`.

`benchmark-expanded.cjs` conserva o gerador circular de IDs `P:FICTICIO-*`, densidades, 3 aquecimentos, 20 microchamadas, cinco repetições, viewport/DPR, CDP e loop RAF. Desativa agrupamento, limpa apenas o cache de layout posterior antes de cada repetição para medir montagem de novo, mantém contexto/JIT e mede atualização síncrona de `grMontarGrafo()+grDesenhar()`. Não introduz contadores por operação de canvas no intervalo medido. A primeira montagem fria não foi descartada; p95 nearest-rank de cinco montagens equivale ao máximo. `comparison.json` contém p50/p95 e dados ambientais, além das verificações de contagem. Não inclui rede/SQLite nem latência visual de primeira apresentação.

O layout anterior continua aleatório; o posterior usa sementes por ID, ordem canônica e física de passo fixo. Mudança de semente faz parte da implementação e não foi disfarçada como fixture idêntica em coordenadas. A topologia e os identificadores são idênticos. A repulsão mantém raio de 400, fórmula e pares, com comparação de referência por teste; a grade ainda tem pior caso quadrático se todos os nós estiverem próximos. A lista `limits` herdada do harness menciona o layout original aleatório; isso descreve o **before**, não o algoritmo posterior.

O primário mediu `snapshots/after.html`, grafo SHA-256 **11cabe61d640a6e3697cd2b701620605733a0d914f08ed0b6d8fb1e5f6a3b882**. Depois dele houve uma correção TDD exclusivamente em `grProjetar`: ao selecionar aresta com agrupamento ativo, os extremos originais ficam individuais e invalidam a projeção anterior. O modo primário tem `grAgrupar=false` e retorna antes dessas linhas, sem mudança do caminho executado, física ou desenho. O snapshot final **after-final.html**, usado nas ablações, contém grafo SHA-256 **39e1b09fe0d95e89d6ec59d1d3909699b64226f55dc1edd00526905d669f8d3d**. Ambos estão preservados, sem substituir a entrada medida.

## Testes funcionais

`app/testes/teste_astra_ast13.py`: dois testes agregam **18 verificações Node/VM** e **3 cenários com Edge/canvas/eventos reais**, incluindo determinismo, forças/ponto de corte, seleção por ID/relacao_id, zoom/pan, arraste fixo, atualização, resize, aba oculta, contagens, hit test, agrupamento/expansão e inspeção de membros. O teste de extremos da aresta observou RED antes da correção. Scripts estão em `app/testes/astra_layout/`, para que o runner que clona apenas `plugin/` possa executá-los. A fixture Edge bloqueia toda rede e usa identificadores fictícios.

GF02: **10/10** após a versão final, sem reduzir expectativas. AST11 UI: **3/3**, com clique de aresta, fontes, conferência, rascunhos, histórico, reabertura e conflito, após o patch principal; a correção posterior atua somente na projeção agrupada. `root11-preserved.json` registra funções de inspeção/evidência preservadas. Toda entrega continua sujeita à homologação humana.

## Integridade e reprodução

`pack_results.py` comprime JSON brutos/HTML com gzip **mtime=0**, verifica round-trip e preserva os bytes originais completos em TEMP `cpj-astra-ast13-raw-20261014`. `package-manifest.json` registra SHA-256 e tamanhos dos bytes originais e comprimidos; nenhum campo ou amostra é eliminado. `unpack.py` verifica ambos os hashes, extrai em TEMP novo e copia os runners. O baseline original não é apagado.

```powershell
python revisoes/metricas-astra/grafo/unpack.py
# Use o diretório TEMP impresso acima; escolha rótulos novos para não sobrescrever resultados.
$nodeRuntime = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/node'
$env:NODE_PATH = Join-Path $nodeRuntime 'node_modules'
$env:ASTRA_RUN_LABEL = 'repro-before'
$env:ASTRA_GROUPED = '0'
$env:ASTRA_LABELS = 'adaptive'
& (Join-Path $nodeRuntime 'bin/node.exe') '<TEMP>/benchmark-expanded.cjs' '<TEMP>/snapshots/before.html' --execute-frozen
$env:ASTRA_RUN_LABEL = 'repro-after'
& (Join-Path $nodeRuntime 'bin/node.exe') '<TEMP>/benchmark-expanded.cjs' '<TEMP>/snapshots/after.html' --execute-frozen
```

Para ler o JSON sem extrair arquivo: `python -c "import gzip,json; print(json.loads(gzip.decompress(open('revisoes/metricas-astra/grafo/results-paired-after.json.gz','rb').read()))['summary'])"`. Para ablações use `benchmark-ablation.cjs` e `after-final.html`: rótulos completos com `ASTRA_LABELS=all, ASTRA_GROUPED=0`; agrupado com `ASTRA_LABELS=adaptive, ASTRA_GROUPED=1`. Compare somente execuções no mesmo host/runtime e registre carga concorrente.
