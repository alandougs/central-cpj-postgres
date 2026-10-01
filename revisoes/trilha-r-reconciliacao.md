# Reconciliação da trilha R do plano V1 com o `main` atual do acervo — GH06

Conferência em 01/10/2026 por Claude-1, no clone sincronizado (`main` = `19de498`, PR #12). Somente leitura. Referência: `revisoes/plano-v1-2026-09-28.md`, tabela de tarefas R01–R10.

## Resultado

Do plano V1, **só a R01 (sincronizar o clone) foi cumprida**, e isso aconteceu hoje (GH02). As demais (R02–R10) **continuam pendentes no `main`**: os PRs que entraram desde 26/09 (#5, #7, #9, #10, #11, #12) trataram de conteúdo (institucional, Central IA, catálogo, Copilot), não da trilha de qualidade.

| Tarefa | O que o plano pedia | Estado no `main` | Evidência |
|---|---|---|---|
| R01 | Sincronizar o clone com o remoto | **Feita** (GH02, 01/10) | `main` alinhado ao `origin/main` |
| R02 | `validar.py --estrito`; `conferir_relatorio.py` e `verificar_citacoes.py` com `--modo diagnostico\|entrega` | **Pendente** | `--estrito` só aparece na docstring do `validar.py`; `sincronizar_claude.py` é o único script com `argparse` útil; os dois verificadores não têm `--modo` |
| R03 | `scripts/testar_fluxo_fraude.py` + workflow de regressão com `requirements-ci.txt` | **Pendente** | não existe o script; o único workflow de validação roda `pip install pyyaml` + `validar.py` (sem versão fixa) |
| R04 | Cópias canônicas (`schemas/copias-canonicas.yaml`, `sincronizar_copias.py`, regra no `validar.py`) | **Pendente** | `esquema-caso-json.md` continua duplicado em 5 skills; não há `copias-canonicas.yaml` |
| R05 | Estados `testado`/`revisado` impostos pelo `validar.py` | **Pendente** | nenhuma regra por estado; só 3 skills têm `VALIDACAO.md` (`controle-de-prazos-do-inquerito`, `notificacao-intimacao-policial`, `pdf-autos-policiais`) |
| R06 | Homologar o núcleo de fraude até `testado` | **Pendente** (depende de R03 e R05) | as skills do núcleo de fraude não têm `VALIDACAO.md` |
| R07 | `requirements*.txt` e `scripts/diagnosticar_ambiente.py` no acervo | **Pendente** | nenhum dos arquivos existe no repositório do acervo (o **core** já tem os seus: RV05) |
| R08 | `verificar_sensiveis.py` (telefone, placa, Pix aleatória, tokens, DOCX/PDF) + Gitleaks no CI | **Pendente** | `validar_dados_pessoais()` só olha CPF e e-mail e só em `.md/.json/.yaml/.yml/.txt/.py/.csv` |
| R09 | `sincronizar_claude.py` com `--check`, `--dry-run`, manifesto; ferramentas por autonomia N0–N4 | **Pendente** | só há a flag `--usuario`; os agentes continuam com `Read, Write, Edit, Bash, Glob, Grep` iguais (visto na revisão do #17) |
| R10 | Hook local `pre-push` (D4: sem ruleset de proteção) | **Pendente** | `.git/hooks` sem `pre-push` |

## O que ainda falta (para registrar como tarefas, se o investigador quiser)

Ordem sugerida, por dependência e por risco:

1. **R02 + R08 (P0/P1, risco de vazamento):** estender o detector de dados sensíveis e criar o modo `entrega`. Hoje o detector **não olha PDF/DOCX** e não cobre telefone, placa nem chave Pix, e o repositório é do investigador com dados de policiais.
2. **R04 → R05 → R03 → R06:** cadeia de qualidade; só R04 e R05 desbloqueiam R06.
3. **R09:** corrigir as ferramentas amplas dos agentes gerados antes de mergear os PRs #14, #15 e #17 (todos acrescentam agentes), para não gerar mais agentes com Bash e Write irrestritos.
4. **R07 e R10:** baratos, podem ir junto com qualquer um acima.

## Interferência com os PRs abertos

Os PRs #14, #15 e #17 alteram `ia/agentes/README.md`, `catalogo.json`, `llms.txt` e `ROUTER.md`. A trilha R mexe em `scripts/validar.py` e nos geradores. Isso **não conflita** em arquivo, mas convém fazer R02/R08 **depois** dos merges, para que o endurecimento do `validar.py` não reprove os PRs por pendências antigas.

## Observação sobre o `validar.py` local

No Windows, o `validar.py` do **próprio `main`** reprova `llms.txt` e `ROUTER.md` ("desatualizados") mesmo logo após regerá-los. Provável diferença de fim de linha ou de ordenação do ambiente. Não afeta o CI (Linux), mas atrapalha quem valida no PC; vale uma tarefa pequena para tornar a comparação independente de fim de linha.

Nenhuma alteração foi feita em `acervo/` ou no GitHub.
