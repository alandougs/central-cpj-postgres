# Proposta de limpeza das branches do acervo — GH05

Levantamento em 01/10/2026 por Claude-1, a partir de `git fetch` e das refs remotas. **Somente proposta: nenhuma branch foi apagada, movida ou alterada.** Apagar branch remota é decisão do investigador (`git push origin --delete <branch>`, ou o botão "Delete branch" no GitHub, que ainda permite restaurar).

`À frente` = commits da branch que não estão no `main`; `Atraso` = commits do `main` que a branch não tem.

## A. Seguras para apagar — 0 commits à frente (tudo já está no `main`)

Nada se perde: o conteúdo já é alcançável pelo `main`.

| Branch | Atraso | Observação |
|---|---:|---|
| `conteudo/fraude-estelionato` | 93 | já integrada |
| `estrutura/policia-judiciaria` | 77 | já integrada |
| `prd/estrutura-acervo` | 99 | já integrada |
| `skill/pdf-autos-policiais` | 101 | já integrada (PR #1) |
| `review/contexto-persistencia-caso` | 78 | PR #4 já fechado |
| `fix/validacao-acervo-atual` | 0 | aponta para o mesmo commit do `main`; sem PR |
| `fix/exportacao-central-ia` | 1 | PR #12 integrado |
| `fix/validacao-central-ia` | 5 | já integrada |
| `institucional/catalogo-ms365-v2` | 15 | já integrada |
| `institucional/central-ia-delegacia` | 67 | já integrada |
| `produto-kiwify-mvp` | 39 | já integrada; confirmar que o produto não precisa da branch para referência |

## B. Substituídas por outra branch — apagar depois que a substituta entrar

Têm commits à frente, mas o conteúdo foi portado por PR mais novo. Apagar **só depois** do merge do substituto.

| Branch | À frente / atraso | Substituta |
|---|---|---|
| `copilot/escrivao-de-policia-ai` | 13 / 100 | `feat/assistente-escrivao-canonico` (PR #14) |
| `feat/delegado-ia-ptc-free` | 1 / 102 | `feat/assistente-delegado-canonico` (PR #15) |
| `feat/grafo-rastreamento-recuperacao-ativos` | 73 / 28 | `feat/fraudes-grafo-recuperacao-v2` (PR #17); PRs #8/#13 fechados |
| `feat/grafo-rastreamento-recuperacao-ativos-v2` | 7 / 0 | `feat/fraudes-grafo-recuperacao-v2` (PR #17); PR #16 fechado |

Antes de apagar a `...-recuperacao-ativos` (73 commits), vale guardar uma tag de arquivo (`git tag arquivo/grafo-v1 origin/feat/grafo-rastreamento-recuperacao-ativos` e `git push origin arquivo/grafo-v1`) caso algo daquela linha ainda seja consultado.

## C. Manter (trabalho em andamento / em revisão)

| Branch | À frente / atraso | Motivo |
|---|---|---|
| `feat/fraudes-grafo-recuperacao-v2` | 13 / 0 | PR #17 (draft), revisado em GH03 |
| `feat/assistente-escrivao-canonico` | 24 / 0 | PR #14 (draft) |
| `feat/assistente-delegado-canonico` | 17 / 0 | PR #15 (draft) |
| `feat/assistente-investigador-canonico` | 12 / 0 | **sem PR identificado**: abrir PR ou decidir |
| `feat/integracao-agentes-operacionais` | 10 / 0 | recente, sem PR identificado: **decisão do investigador** |
| `feat/github-copilot-agents-adapters` | 5 / 24 | recente e atrasada: precisa atualizar com o `main` ou ser reavaliada |

## Resumo

- 11 branches podem sair já (grupo A), 4 depois dos merges (grupo B), 6 ficam (grupo C), 2 delas pedem decisão sobre PR.
- Antes de qualquer exclusão remota, a regra prática: grupo A é exclusão sem perda; grupo B só com tag de arquivo ou depois do merge.
- Não confirmei o estado dos PRs fechados (#8, #13, #16, #4) pela interface do GitHub (sem `gh` aqui): a classificação usou as refs e a lista de PRs registrada na fila.
