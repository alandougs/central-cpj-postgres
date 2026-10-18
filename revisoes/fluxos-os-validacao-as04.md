# AS04 — validação das ações de processamento por O.S.

Continuidade autorizada pelo operador em 18/10/2026, preservando UN14/UN15 e a Central em uso.

## Reprodução e correção

As ações de cancelar e conferir uma etapa usavam `.get` diretamente no corpo JSON. Corpos válidos como JSON, mas que eram listas, textos, números ou booleanos, causavam exceção interna em vez de erro de entrada. A regressão formal reproduziu **oito AttributeError** nas duas ações.

Os dois pontos agora verificam se o corpo é um objeto antes de acessar os campos e devolvem HTTP 400 em caso contrário. Autenticação, visibilidade da O.S., permissões e conferência da etapa permanecem antes dessa validação; versões e transições não foram alteradas.

## Validação

- API UN15: **16/16 testes**, **8,52 s**, sem skips. A nova regressão cobre **18 combinações** de entrada inválida nas duas ações, resposta JSON com erro e banco/checkpoint intactos; a fixture também confere os bytes de `caso.json`.
- Código final cumulativo de AS03/AS04 na suíte completa estrita: **120/121**, saída **1**, soma **641,67 s**, total **786,39 s**. API e navegador por O.S. aprovados; única falha: V01.4, comparação de todos os mtimes da árvore operacional compartilhada. A atividade externa nesse guard já foi demonstrada por observação de metadados em AS02; esta rodada não identificou o processo gravador nem os caminhos alterados. Código e documentação permaneceram congelados durante a rodada.
- Reteste sem mudar código, runner `--rapido --incluir teste_workspace_v01.py --estrito`: **5/5**, saída **0**, soma **40,65 s**, total **46,81 s**. Não converte a rodada completa em 121/121. O guard não foi enfraquecido e a Central não foi parada.
- Permanecem cinco skips locais de links simbólicos por privilégio do Windows; nenhum skip crítico de dependência ausente. Logs locais em `%LOCALAPPDATA%\CPJ\test-envs\as04-api-final.log`, `as04-suite-completa.log` e `as04-reteste-workspace.log`.

## Publicação e estado operacional

Correção `45becaf`, [PR #24](https://github.com/alandougs/central-cpj-postgres/pull/24), após o histórico do [PR #23](https://github.com/alandougs/central-cpj-postgres/pull/23). Integração condicionada aos checks obrigatórios do head final; resultados e merge ficam rastreáveis nos PRs. AS02 já integrada no [PR #22](https://github.com/alandougs/central-cpj-postgres/pull/22), merge `3f6a6444f4e1800df6de42dd66f6b013f8d304b0`, [CI 121/121](https://github.com/alandougs/central-cpj-postgres/actions/runs/39100231481), **1006,03 s**, sem testes pulados.

Somente código, documentação genérica e dados fictícios nos testes. Nenhuma instalação, atualização, migração ou reinicialização operacional. A fonte da Central em uso permanece na branch `codex/os-markdown-relatorio-20261014`, commit `66ea935`; sincronizar o GitHub não autoriza substituí-la.

AS03 integrada após os checks, merge `91e711fa8597aebd2f4fa083a8421fbe6c45babc`; [CI 121/121](https://github.com/alandougs/central-cpj-postgres/actions/runs/39101399159), 660,28 s, sem skips de testes. Conferência operacional após a publicação: checkout limpo, hashes de servidor/interface e versões dos pacotes iguais à referência TL01. AS04 aguarda os checks do head final no PR #24; o resultado local permanece 120/121 com reteste 5/5.
