# AS02 — recuperação após falha ao adquirir a trava do caso

Ciclo de confiabilidade autorizado pelo operador em 18/10/2026, após AS01. A próxima prioridade indicada pelo operador é o fluxo de processamento por O.S. A Central em uso permanece fora de atualização/migração.

## Reprodução e correção

`ReentrantFileLock.__enter__` adquiria o `RLock` e registrava a profundidade da thread antes de criar a pasta e abrir `.caso.lock`. Falhas nessas operações ou interrupção durante a espera escapavam sem liberar os recursos. O teste demonstrou outra thread recebendo `CasoOcupado` depois da falha original; a interrupção também deixava o arquivo aberto.

A aquisição passou a ter limpeza em todos os caminhos de exceção: fecha o arquivo quando aberto, remove o estado local e libera o `RLock`, preservando a exceção original. Mantidos o timeout, a exclusão entre threads/processos e as transações reentrantes. Não altera o registro de dados nem repete operações de IA.

TDD: antes da correção, três cenários de falha reproduziram a retenção, com erro adicional da limpeza do temporário do teste pelo arquivo aberto. Depois: **5/5 testes AS02 aprovados** (abrir arquivo, criar pasta, interromper espera, falha no corpo e reentrância/exclusão). A regressão AS01 permaneceu **5/5**.

## Suíte local e interferência operacional

- Primeira rodada completa estrita: **120/121**, saída **1**, soma **657,61 s**, total **801,22 s**. Única falha: comparação de mtimes de toda a pasta operacional em `teste_workspace_v01.py`; todos os demais testes passaram, inclusive AST17 e AS02.
- Reteste pelo runner `--rapido --incluir teste_workspace_v01.py --estrito`: **5/5**, saída **0**, **41,50 s**, sem mudança de código.
- Rodada completa final: **120/121**, saída **1**, soma **653,78 s**, total **798,27 s**; novamente somente a comparação de mtimes. Log: `%LOCALAPPDATA%\CPJ\test-envs\as02-suite-final.log`. A primeira rodada e o reteste estão nos arquivos `as02-suite-completa.log` e `as02-reteste-workspace.log` na mesma pasta.
- Observador local somente de metadados, sem mudar testes ou ler conteúdo de bancos/casos: identificou alterações no banco operacional `config/plantao.sqlite` durante a janela da V01. Uma observação separada de **45 s sem suíte local em execução** também detectou mudança nos metadados desse banco. Portanto, a comparação da árvore compartilhada sofre interferência da atividade fora da suíte. A identidade do processo gravador não foi apurada.
- O observador não altera o resultado do runner. O guard foi preservado, sem ignorar o banco, retirar asserts ou declarar 121/121 local. A validação completa do candidato usa também o CI isolado, sem o banco operacional desta máquina. A Central não foi parada para obter placar verde.
- Permanecem os cinco skips locais de links simbólicos por privilégio do Windows (UN16: um; RV17: quatro); nenhum skip crítico de ferramenta ausente.

## Publicação e continuidade

AS01 foi integrada em `main` no [PR #21](https://github.com/alandougs/central-cpj-postgres/pull/21), merge `748213a48f325c554d17ff2087c5ef9edc266fad`. Seu [CI](https://github.com/alandougs/central-cpj-postgres/actions/runs/39098239936) aprovou sigilo/distribuição e **120/120 suítes**, **638,34 s**, sem skips de testes.

AS02 é publicada em `codex/astra-travas-recuperaveis`; o PR desta branch registra os checks obrigatórios e a integração. Código e testes permaneceram congelados durante as rodadas completas; os documentos foram atualizados depois. Nenhum dado real de caso, banco, configuração, credencial ou assinatura foi incluído. A cópia operacional permanece na branch `codex/os-markdown-relatorio-20261014`, commit `66ea935`.
