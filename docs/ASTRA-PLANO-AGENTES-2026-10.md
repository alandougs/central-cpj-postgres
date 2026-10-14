# ASTRA — Plano de execução por agentes (14/10/2026)

**Projeto:** Central CPJ / ASTRA — Grafo de Vínculos e Inteligência Relacional  
**Repositório:** [alandougs/central-cpj-postgres](https://github.com/alandougs/central-cpj-postgres)  
**Épico:** [#4](https://github.com/alandougs/central-cpj-postgres/issues/4)  
**Branch base obrigatória:** `main` (commit-base auditado `323181327`, de 10/10/2026). A branch padrão `master` está desatualizada.  
**Status deste plano:** backlog registrado; implementação e testes novos **ainda pendentes**.

## Objetivo

Fazer o ASTRA deixar de ser um grafo/painel meramente técnico e funcionar como **copiloto investigativo guiado**: responder consultas, explicar a origem dos vínculos, apoiar exploração de hipóteses sem criar fatos, preservar as anotações do operador e operar de forma rápida e previsível.

## Backlog — abrir e executar uma issue por vez

| Ordem | Fase | Issue | Entrega | Dependência |
|---:|---|---|---|---|
| 1 | P0 — integridade | [#5 — P0-01](https://github.com/alandougs/central-cpj-postgres/issues/5) | Corrigir payload/API para vínculos manuais | — |
| 2 | P0 — integridade | [#6 — P0-02](https://github.com/alandougs/central-cpj-postgres/issues/6) | Persistência independente da reindexação, backup e migração | #5 |
| 3 | P0 — integridade | [#7 — P0-03](https://github.com/alandougs/central-cpj-postgres/issues/7) | Exclusão segura somente de vínculo manual identificado | #6 |
| 4 | P0 — integridade | [#8 — P0-04](https://github.com/alandougs/central-cpj-postgres/issues/8) | Todas as fontes preservadas + confirmação distinta de hipótese | #5, #6 |
| 5 | P1 — UX | [#9 — P1-01](https://github.com/alandougs/central-cpj-postgres/issues/9) | Jornada guiada O.S. → ASTRA → próxima ação | #5 a #8 |
| 6 | P1 — UX | [#10 — P1-02](https://github.com/alandougs/central-cpj-postgres/issues/10) | Perguntas em linguagem natural com consulta determinística e fontes | #8, #9 |
| 7 | P1 — UX | [#11 — P1-03](https://github.com/alandougs/central-cpj-postgres/issues/11) | Inspetor de evidências, páginas/fls. e validação humana | #8 |
| 8 | P1 — UX | [#12 — P1-04](https://github.com/alandougs/central-cpj-postgres/issues/12) | Rascunho protegido, salvamento separado do DOCX e FINAL | — |
| 9 | P2 — desempenho | [#13 — P2-01](https://github.com/alandougs/central-cpj-postgres/issues/13) | Layout determinístico, renderização, agrupamento e FPS | #8 |
| 10 | P2 — desempenho | [#14 — P2-02](https://github.com/alandougs/central-cpj-postgres/issues/14) | Paginação, limites declarados e SQL otimizado | #8 |
| 11 | P2 — desempenho | [#15 — P2-03](https://github.com/alandougs/central-cpj-postgres/issues/15) | Polling adaptativo, erros e progresso contextual | #9, #10 |
| 12 | P2 — manutenção | [#16 — P2-04](https://github.com/alandougs/central-cpj-postgres/issues/16) | Extrair JS/CSS em módulos sem framework nem regressões | #9 a #12 |
| 13 | P3 — homologação | [#17 — P3-01](https://github.com/alandougs/central-cpj-postgres/issues/17) | Suíte E2E, segurança, UX e benchmarks antes/depois | demais issues |

O conteúdo integral de **plano → execução → validação** está na descrição de cada issue, que é a fonte de verdade de cada tarefa. Atualize a issue com evidências e PR/commit para facilitar revisão.

## Protocolo obrigatório para Codex / Claude Code / OpenCode / Antigravity

1. **Inspecionar antes de alterar:** `AGENTS.md`, `PRD.md`, `TAREFAS-COMPARTILHADAS.md` e issue selecionada. Conferir `git status`, `git branch` e reservas dos outros agentes; não apagar trabalho não commitado.
2. **Plano:** verificar código existente, reproduzir defeito com fixture fictícia e registrar causa/arquivos previstos. Não tratar hipótese de revisão estática como bug comprovado até reproduzi-la.
3. **Execução:** alterar apenas arquivos necessários ao escopo; preservar rotas e compatibilidade; incluir teste que falhava antes da correção e passa depois. Não reescrever frontend ou backend inteiro.
4. **Validação:** teste próprio, regressão das partes afetadas, `git diff --check`, logs seguros; quando viável `python ferramentas/testar-tudo.py --rapido`, na homologação final suíte completa e Playwright.
5. **Entrega:** registrar arquivos alterados, testes/tempo/resultados, riscos e próximos passos. Não declarar concluído sem teste reproduzível. Não fazer push/merge sem autorização do operador.
6. **Dados e sigilo:** **somente dados sintéticos** na manutenção; não ler/publicar autos reais, produção, credenciais ou chaves no GitHub. Não chamar APIs de IA com conteúdos sigilosos sem autorização compatível e consentimento previsto no CPJ.
7. **Integridade probatória:** separar vínculo documental, correspondência candidata (homônimos), hipótese manual e conferência humana. Titular de conta não é presumido autor; relatar limites e origem de cada inferência.

### Coordenação de múltiplos agentes
- Cada issue deve ser implementada em **branch/worktree isolado** criado a partir de `origin/main`, com arquivos reservados na fila quando exigido pelo projeto.
- Várias issues mexem em `index.html`, `consulta.py` e `indexar.py`: não editar o mesmo arquivo em paralelo sem um integrador dedicado.
- Ordem segura: **#5 → #6 → #7 → #8**; depois distribuir #9/#11/#12/#14 conforme conflitos; #10 e #15 após suas dependências; #16 depois de estabilização da UX; #17 no fechamento.
- No início de cada issue, comparar alterações atuais para evitar duplicar correção de outro agente; integrar via revisão/PR com regressões.

## Início seguro no VS Code (PowerShell aberto dentro do repositório CPJ)

```powershell
git fetch origin main
git worktree add -b astra/p0-01 ..\CPJ-ASTRA-P0-01 origin/main
Set-Location ..\CPJ-ASTRA-P0-01
codex "Leia docs/ASTRA-PLANO-AGENTES-2026-10.md, AGENTS.md e o épico GitHub #4. Execute exclusivamente a issue #5 (P0-01): primeiro plano e reprodução com dados fictícios; depois correção e testes; por último validação e resumo. Respeite reservas da fila, não use autos reais e não faça push nem merge."
```

Se o agente preferido for Claude Code, na última linha usar `claude "Leia docs/ASTRA-PLANO-AGENTES-2026-10.md e execute somente a issue #5 conforme as regras do repositório..."`. No OpenCode, usar o comando correspondente à instalação, com o mesmo prompt. Não é preciso instalar GitHub CLI (`gh`) para seguir os links das issues.

**Atenção:** `git worktree add -b astra/p0-01` serve para a **primeira execução**; se a branch ou pasta já existir, abrir o worktree existente, não criar cópia por cima. Para outras issues, mudar o identificador da pasta/branch e o número da issue. Não fazer `git pull` dentro de um workspace com alterações não salvas.

## Critérios finais

- **P0:** vínculo manual sobrevive a reindexação/reinício/backup; exclusão nunca apaga relações extraídas; todas as fontes da mesma ligação continuam acessíveis.
- **P1:** usuário pode sair da O.S., consultar, explorar e conferir evidência na interface, sem precisar entender filas, scripts ou SQL; rascunho não se perde.
- **P2:** desempenho medido no mesmo equipamento/fixtures antes/depois, nenhum recorte silencioso, interface sem requisições desnecessárias; módulos testáveis.
- **P3:** fluxos E2E e testes negativos completos, documentação, segurança e autorização de uso; entrega sob decisão humana.

> Este arquivo organiza trabalho futuro. A existência das issues ou de histórico de testes não equivale à implementação nem à homologação das melhorias.
