# RG41 — Checkpoint lido uma vez por documento na indexação

27/10/2026 — Codex-RG41. Correção restrita ao candidato autorizado: `indexar.py`, teste RG40 ampliado e esta evidência. O coordenador relatou que a reconstrução operacional interrompida estava desserializando repetidamente o checkpoint consolidado em `evidencia_fonte`. Esta tarefa não acessou autos, checkpoints, configuração ou banco operacionais e não reproduziu o volume real.

## Causa e alteração

Cada ocorrência documental chamava `ler_estado_extracao(..., 'relatorio_extracao.json')`. Embora só três metadados fossem usados na proveniência, o leitor real precisava desserializar o checkpoint consolidado completo em cada chamada, inclusive suas páginas/textos.

Foi adicionado `_metadados_fontes`, em memória e limitado à execução do indexador. A chave é o caminho de metadado já validado e contido no caso; cada documento retém somente `arquivo`, `sha256_original` e `gerado_em`. Páginas/textos não são guardados nesse cache. Resultado vazio, ausente ou erro já tratado também é cacheado. Não há arquivo de cache nem reutilização entre processos. A validação de caminhos e o tratamento de erros existentes continuam no lugar. Não foram alterados o leitor consolidado, as regras de incerteza, os vínculos ou o argumento `--sem-baixa`.

## Prova de chamadas reais e proveniência

TDD no teste `test_cache_checkpoint_uma_leitura_por_documento_e_execucao`:

- Fixture TEMP com 30 candidatos CPF em cada um de quatro documentos: dois checkpoints válidos, um ausente e um JSON inválido. Os válidos contêm textos extensos descartáveis, além dos metadados de origem.
- Subprocesso instrumenta `estado_extracao.ler` com um contador que delega ao leitor real e executa o indexador real via `runpy`, com `--tudo --sem-baixa`.
- **RED antes da correção:** `{'alfa': 30, 'beta': 30, 'erro': 30, 'vazio': 30}`; falha por 120 leituras contra quatro esperadas.
- **GREEN após a correção:** `{'alfa': 1, 'beta': 1, 'erro': 1, 'vazio': 1}`; 120 evidências do grafo preservadas, quatro entradas de cache somente com os campos de metadados permitidos.
- As evidências conservam arquivo PDF original e SHA-256, caminho Markdown e seu SHA-256, documento, página 7, tipo `extracao_candidata` e status `pendente de conferência`. Ausência/erro não fabrica PDF ou hash. Os bytes de `caso.json` permanecem iguais.
- O teste altera `gerado_em` de um checkpoint e executa outro subprocesso: há novamente uma leitura por documento e a nova data aparece em todas as evidências correspondentes. Isso demonstra o descarte do cache entre execuções.

A redução comprovada é de **120 para quatro chamadas** nesta fixture, não uma estimativa de tempo operacional. Cada documento consolidado ainda precisa ser lido uma vez na execução.

## Verificação dirigida

Runtime `F:/CPJ - TRABALHO/.venv/Scripts/python.exe`, candidato como diretório atual, `PYTHONDONTWRITEBYTECODE=1`. Cada suíte roda em processo separado; todos os workspaces de teste são sintéticos e temporários.

| Arquivo em `plugin/investigacao-cpj/app/testes/` | Resultado |
|---|---|
| `teste_rag_markdown_rg40.py` | 12 OK, exit 0 (4,435 s) |
| `teste_astra_ast08_index.py` | 11 OK, exit 0 |
| `teste_astra_ast14_api.py` | 15 OK, exit 0 |
| `teste_grafo_api_gf01.py` | 11 OK, exit 0 |
| `teste_integridade_vinculos_rp32.py` | 12 OK, exit 0 |

Total dirigido: **61 testes aprovados, zero falhas, zero skips**. Inclui fontes/caminhos/junções, status candidato, separação de tipos, contas sem banco, preservação de manuais e manutenção sem baixa. `git diff --check` do indexador terminou sem erro. Não foi executada suíte completa concorrente.

## Fontes congeladas

| Arquivo | SHA-256 |
|---|---|
| `plugin/investigacao-cpj/skills/base-cpj/scripts/indexar.py` | `fc214a57426619363d5db6b652c6aa9a137395ca4392edaf3741edcee6f2cf00` |
| `plugin/investigacao-cpj/app/testes/teste_rag_markdown_rg40.py` | `d7921859f29f8161994b1d4534c45d57636b13259924cee49e0ed7340744b8fa` |

Esses hashes substituem os hashes anteriores dos mesmos arquivos. Integração/cópia ao original, retomada da reconstrução real e conferência dos snapshots continuam com o coordenador. Nenhum banco real foi aberto, substituído ou removido por esta tarefa.
