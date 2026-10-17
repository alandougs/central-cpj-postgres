# Checkpoint — execução da unificação da Central CPJ (UN10–UN18)

Único checkpoint da execução. Plano: `docs/superpowers/plans/2026-10-16-cpj-unificado.md`. Branch de integração: `codex/unificacao-cpj` (iniciada em `782563a`, de `codex/os-markdown-relatorio-20261014`). Agente: `Claude-unificacao`. Somente dados genéricos/sintéticos neste arquivo.

## Estado atual

| Tarefa | Estado | Commit/SHA | Testes |
|---|---|---|---|
| UN10 | concluída (código/teste); sem migração real | ver `git log` da branch | `teste_recuperacao_un10.py` 5/5; runner `--rapido --incluir` 5/5 suítes, saída 0 |
| UN11 | próxima | — | — |
| UN12–UN18 | pendentes | — | — |

**Próximo comando seguro:** reservar UN11 (`python ferramentas/fila-tarefas.py assumir UN11 --agente Claude-unificacao`) e integrar `origin/codex/astra-evolucao-20261014` no checkout isolado.
**Autorização pendente:** merge em `main`, troca da branch padrão e instalação/migração operacional (liberação final em UN18). Nada disso foi feito.
**Processos de teste ativos:** nenhum.

## UN10 — base e inventário (16/10/2026)

Interpretador: `C:\CPJ - TRABALHO\.venv\Scripts\python.exe` (Python 3.12.14). `fetch --all` feito; árvore principal limpa no início.

Remoto (heads): `main` f56653c · `master` 7e537c4 · `codex/os-markdown-relatorio-20261014` (PR18) 782563a · `codex/astra-evolucao-20261014` (PR19) f981f90 · `codex/final-sync-20261010`, `consolidacao-2026-10-01`, `codex/revisao-bugs-2026-10-04` (ancestrais da base: zero commits exclusivos) · `rodada-enxuta-core` 90dbdc8 e `copilot/revise-entire-code` (= master) · `revisao-dev-senior-2026-10-09` 8d8ac0e.

Contagem de commits exclusivos em relação à base `782563a` (história, não funcionalidades):

| Ref | Exclusivos do ref | Exclusivos da base |
|---|---|---|
| `origin/main` | 0 | 10 |
| `origin/master` | 12 | 29 |
| `origin/codex/astra-evolucao-20261014` | 11 | 6 |
| `origin/rodada-enxuta-core` | 11 | 29 |
| `origin/revisao-dev-senior-2026-10-09` | 13 | 29 |

Exclusivos de `master` (12): migração Docker/PostgreSQL (stack Docker, adaptador e migração de documentos textuais, login antes do cadastro, modelo de caso no container, teste de leitura SSD) e a "rodada enxuta do core" com a correção dos quatro P1 do PR #1. **Pendente UN11:** decidir por comparação semântica o que da trilha Docker/PostgreSQL entra; o contrato vigente é Python/Flask/SQLite, sem novo banco.

Worktrees Codex locais com um commit cada ainda não integrado à base: `codex/astra-editor-20261014` (`6436719` editor/rascunhos/DOCX), `codex/docx-fls-assinatura-20261014` (`f941acb` fls./assinatura), `codex/fila-progresso-20261014` (`0e64fd6` atividade/previsão da fila). Estão fora desta branch; confirmar em UN11 se já constam em PR19 (o PR19 lista "protege rascunhos"/FP01) antes de qualquer decisão. Nenhum foi alterado.

Cópia recuperável do código: `git bundle --all` (verificado) em `C:\CPJ - TRABALHO\.claude\recuperacao\codigo-pre-unificacao-20261016.bundle` — local, ignorado pelo Git.

## UN10 — defeito do mecanismo legado e correção

Ensaio com fixture fictícia (WAL aberto) sobre `ferramentas/backup.ps1` + `restaurar.ps1`:

1. Restaurar por cima de um workspace com dados posteriores **sobrescreve** arquivo mais novo com a versão do backup (arquivo alterado após o backup voltou à versão antiga) e **perdeu uma linha** do banco criada depois do backup (201 → 200). Contraria "nunca restaurar cegamente sobre dados criados depois do backup".
2. `restaurar.ps1` só restaura no próprio workspace do script e exige `producao\` existente (falha com código 1 em destino novo sem a pasta).
3. Copia `-wal`/`-shm` por robocopy, não por snapshot atômico; não há manifesto/hash nem verificação de integridade.

Correção: novo `ferramentas/backup_consistente.py` (arquivo reservado em UN10) — snapshot SQLite pela API de backup (fonte aberta `mode=ro`, WAL incluso, sem copiar `-wal/-shm`), manifesto SHA-256, backup sempre em pasta nova, verificação antes de restaurar, restauração em diretório escolhido sem sobrescrever divergentes (versão do backup vai para `_restauracao/<id>/` e o conflito é informado). Testes: `plugin/investigacao-cpj/app/testes/teste_recuperacao_un10.py` (RED confirmado: módulo ausente; GREEN após a implementação).

Os scripts legados `backup.ps1`/`restaurar.ps1` e `teste_backup_antigravity.py` **não foram alterados** (o teste legado exige sobrescrita; mudar exige decisão sobre o requisito). **Risco aberto:** `restaurar.ps1` continua destrutivo sobre workspace vivo. Regra para UN18: usar somente `backup_consistente.py`; sugerir ao operador aposentar ou proteger o `.ps1` (decisão dele; não feito para não ultrapassar o escopo).

## Pré-condições da liberação operacional (UN18) — registradas, nada executado

- Destino local explícito e espaço livre suficiente (somar `casos`, `config`, `producao` etc. + margem).
- Admissões interrompidas de forma coordenada; trabalhos em andamento terminados ou reconciliados (sem processo escrevendo durante a transição).
- Backup via `backup_consistente.py backup`, `verificar` e restauração ensaiada em diretório separado antes de migrar.
- Operar a Central de produção apenas após liberação final do operador. Nesta etapa a Central de produção não foi parada nem tocada.

## Limites e skips desta etapa

Nenhum skip na UN10. Não coberto: restauração sobre Central em execução real, volumes grandes, permissões/ACL do Windows em destino de rede.
