# TL01 — suíte completa local em ambiente isolado

Pedido do operador em 18/10/2026: instalar as dependências de teste ausentes e executar a suíte completa localmente, sem atualizar nem migrar a Central em uso.

Fonte sob teste: `codex/unificacao-cpj`, commit `ddee6986a8745e9ff0c5f3887bdd3d8d73f13683`. Alterações desta tarefa limitadas ao registro na fila, neste relatório e no PRD; sem alteração do produto.

## Ambiente e preparação

- Python 3.12.14 em ambiente virtual separado: `%LOCALAPPDATA%\CPJ\test-envs\unificacao-py312`.
- Instalação de `requirements-dev.txt` com `pip install --only-binary=:all: -r requirements-dev.txt`; nenhuma dependência instalada ou atualizada no `.venv` operacional.
- QuickJS 1.19.4, Playwright Python 1.64.0 e ReportLab 5.0.1. Manifesto completo local em `%LOCALAPPDATA%\CPJ\test-envs\tl01-environment.json`.
- `pip check`: código 0, sem dependências incompatíveis. QuickJS executou JavaScript; Playwright abriu e fechou o Microsoft Edge existente em modo headless. Sem instalação de navegador.
- Runner canônico: `ferramentas/testar-tudo.py --estrito`, invocado pelo Python desse ambiente. O runner usa workspaces temporários e dados sintéticos para as suítes e para a Central de teste.

## Resultado

Rodada completa estrita: **118/119 suítes aprovadas**, código de saída **1**, soma de tempos das suítes **639,83 s** (tempo total do comando **787,36 s**, incluindo preparação dos workspaces e verificações de skips). Log local: `%LOCALAPPDATA%\CPJ\test-envs\tl01-suite-completa.log`.

Todas as sete suítes antes reprovadas por ausência de QuickJS passaram. `teste_e2e_f03.py` e `teste_navegacao_calibracao_copilot.py` também passaram; não houve cobertura crítica ignorada por ferramenta ausente.

A única falha foi `teste_astra_ast17_e2e.py`: o servidor de teste retornou HTTP 500 ao consultar o caso sintético. O traceback do servidor mostrou `PermissionError: [WinError 5]` em `caso.py:257`, durante `os.replace` de um arquivo `.caso.*.tmp` para `caso.json` no workspace temporário AST17. Evidência local em `%TEMP%\cpj-astra-ast17-e2e-htdp9mzd\servidor.log` e `upload.log`. Os logs não identificam qual processo ou mecanismo causou a recusa; não atribuir a antivírus ou outro agente sem evidência.

Reteste pelo mesmo runner, com `--rapido --incluir teste_astra_ast17_e2e.py --estrito`: **5/5 suítes aprovadas**, código **0**, soma **48,33 s** (tempo total **54,56 s**). A AST17 executou o fluxo completo em **23,12 s**; solo, segurança, modularização e dados/O.S. também passaram. Log: `%LOCALAPPDATA%\CPJ\test-envs\tl01-reteste-astra.log`. Nenhum código ou dependência foi alterado entre as rodadas. A falha não se reproduziu; isso não comprova eliminação de recorrência, nem transforma a primeira rodada em 119/119.

Cinco testes de links simbólicos foram ignorados por falta de privilégio do Windows: um em `teste_distribuicao_un16.py` e quatro em `teste_executores_rv17.py`. São os únicos skips da rodada, tolerados pelo runner estrito após a sonda de capacidade do host. Não foram alterados privilégios, política do Windows ou testes.

## Limites

Sem atualização, instalação do aplicativo, migração, reinício ou troca de branch da Central operacional. A cópia principal permanece limpa em `codex/os-markdown-relatorio-20261014`, commit `66ea935`. Conferência final confirmou hashes de `servidor.py` e `static/index.html` e versões das dependências operacionais iguais ao registro anterior à execução; QuickJS e Playwright continuam ausentes do `.venv` operacional. Sem commit ou push nesta tarefa.
