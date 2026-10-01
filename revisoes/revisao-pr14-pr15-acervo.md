# Revisão dos PRs #14 (Assistente do Escrivão) e #15 (Assistente da Autoridade Policial) do acervo — GH04

Revisão em 01/10/2026 por Claude-1. Somente leitura: nada foi alterado no clone nem no GitHub. O merge é decisão do investigador.

## Base da análise

Branches remotas de `origin`, testadas com `git merge-tree` (simula o merge sem alterar nada):

| Branch | Assistente | Commits à frente do `main` | Atraso | Arquivos |
|---|---|---:|---:|---:|
| `feat/assistente-escrivao-canonico` | Escrivão (N2) — PR #14 | 24 | 0 | 20 |
| `feat/assistente-delegado-canonico` | Autoridade Policial (N3, PTCFREE) — PR #15 | 17 | 0 | 19 |
| `feat/assistente-investigador-canonico` | Investigador — **sem PR identificado** | 12 | 0 | 14 |
| `feat/fraudes-grafo-recuperacao-v2` | Fraudes/recuperação — PR #17 (ver GH03) | 13 | 0 | 58 |
| `copilot/escrivao-de-policia-ai`, `feat/delegado-ia-ptc-free` | versões antigas, portadas pelos #14/#15 | 13 e 1 | 100 e 102 | — |

Todas as branches canônicas estão **em dia com o `main`** (PR #12). As duas antigas estão 100+ commits atrasadas e não devem ser mergeadas (ver GH05).

## Conflitos (previstos pelo `merge-tree`)

Em qualquer par de PRs, os conflitos ficam em dois grupos:

1. **Arquivos gerados** — `catalogo.json`, `llms.txt`, `ROUTER.md`. Todos os PRs os regeneram. **Não resolver à mão:** depois de mergear um PR, atualizar o seguinte com o `main` e rodar `python scripts/gerar_catalogo.py`, `gerar_llms_txt.py` e `gerar_router.py`.
2. **Listas de texto escrito à mão** — `ia/agentes/README.md` (cada PR acrescenta uma linha em "Agentes disponíveis"), `melhoria/lacunas.md` e `.github/agents/README.md` (delegado × investigador). São conflitos de adição na mesma região: resolver **mantendo as duas linhas**.

| Par | Conflitos |
|---|---|
| Escrivão × Delegado | catálogo, llms, `ia/agentes/README.md`, `melhoria/lacunas.md` (4) |
| Escrivão × Investigador | ROUTER, catálogo, llms, `ia/agentes/README.md`, `lacunas.md` (5) |
| Delegado × Investigador | `.github/agents/README.md`, catálogo, llms, `ia/agentes/README.md`, `lacunas.md` (5) |
| #17 × Escrivão | ROUTER, catálogo, llms, `ia/agentes/README.md` (4) |
| #17 × Delegado | catálogo, llms, `ia/agentes/README.md` (3) |
| #17 × Investigador | ROUTER, catálogo, llms, `ia/agentes/README.md` (4) |

Não há conflito em arquivo de conteúdo substantivo (perfis, procedimentos, skills, prompts): os PRs tocam arquivos diferentes.

## Higiene dos PRs

- Cada branch teve commits `chore(ci): adicionar/remover sincronização temporária`. Conferi o diff final: **nenhum workflow temporário ficou na árvore** (nenhum arquivo em `.github/workflows/` nos três PRs). Os commits de ida e volta ficam só no histórico; usar "squash and merge" os deixa limpos.
- Cada PR traz, além do conteúdo, o espelho para agentes (`.claude/agents/…`, `.github/agents/….agent.md`), o que é esperado pelo plano de cópias canônicas.
- O assistente do escrivão remove a especificação de `_planejados/` quando passa a existir em `ia/agentes/`: coerente.

## Ordem de merge proposta

1. **PR #17 (fraudes)** — o maior e o único que altera o núcleo de skills existentes (`relatorio-fraude-estelionato`, `rastreio-financeiro-fraude`). Resolver antes os itens da revisão GH03.
2. **PR #14 (Escrivão, N2)** — o mais profundo em procedimentos de cartório e o mais antigo no plano.
3. **PR #15 (Autoridade Policial, N3)** — depende conceitualmente do nível de autonomia mais alto; entra por último entre os dois, depois de revisão humana do texto de `governanca/delegado-ia.md`.
4. **Branch do Investigador** — abrir PR (ou confirmar o número) antes; se for para entrar, vem por último, por ser o menor.

Procedimento a cada merge (do segundo em diante): atualizar a branch com o `main` → resolver as listas mantendo todas as linhas → regenerar catálogo, llms e router → `python scripts/validar.py` → merge por squash. Regeneração **no CI Linux**, porque o `validar.py` local no Windows já reprova `llms.txt` e `ROUTER.md` no próprio `main` (ver GH03).

## Pontos a ler com atenção antes do merge (decisão humana)

- **#15:** é o PR com maior risco de uso indevido, por tratar de despacho, representação e relatório final da autoridade. Conferir que o texto reafirma que toda saída é minuta, que decisão e assinatura são da autoridade e que o assistente **não** decide prisão nem medida cautelar.
- **#14 e #15:** conferir as ferramentas dos agentes gerados (mesmo problema de ferramentas amplas apontado em GH03).
- **Tratamento por gênero (regra 10 do CLAUDE.md):** nos modelos de saudação da autoridade, o gênero deve vir de campo informado, nunca do nome. Verificar `perfil-delegado.md` e o prompt do #15.

Nenhuma alteração foi feita em `acervo/` ou no GitHub.
