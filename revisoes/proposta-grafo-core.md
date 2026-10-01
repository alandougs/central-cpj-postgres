# Proposta: incorporar ao core o percurso L0→Ln e os estados patrimoniais — GH07

Proposta de 01/10/2026 por Claude-1. **Só proposta e tarefas; nenhum código do core foi alterado.** Base: skill `recuperacao-ativos-fraude` do PR #17 (ver `revisoes/revisao-pr17-acervo.md`) e o estado real do core (RV02 concluída: o fluxograma já sai do `fluxo-financeiro.csv` e entra no DOCX). Só vale depois que o PR #17 for aprovado e mergeado.

## O que o core já tem

- `fluxo-financeiro.csv` com `camada` (1 = saída da vítima), valor, data, origem/destino, `fonte_pag`, `fls` e `status_conferencia`.
- Agente `analista-financeiro` e fluxograma PNG (RV02) que só desenha o que está no CSV.
- Regra de ouro já aplicada: não completar dado; "último destino documentado" ≠ beneficiário final.

## O que o PR #17 acrescenta e vale trazer

1. **Estados patrimoniais** com vocabulário fixo: identificado, rastreado, localizado, bloqueado, devolvido, liberado, apreendido, pendente. Regra: "bloqueado" nunca é "recuperado" e não reduz o prejuízo.
2. **Quantificação padrão:** desembolsado, devolvido, **prejuízo líquido documentado** (= desembolsado − devolvido), rastreado, bloqueado.
3. **Percurso L0→Ln** (raiz, L1, L2…) por ramo, com onde o rastro termina e padrões de dispersão/concentração.
4. **Matriz de recuperação** (valor, estado, fonte, finalidade, providência) e seção "Recuperação de valores e ativos" no relatório.

## Proposta de incorporação (em fatias pequenas)

| Fatia | Mudança | Arquivos do core | Risco |
|---|---|---|---|
| A | Duas colunas **opcionais** no CSV: `estado_patrimonial` (vocabulário acima) e `valor_devolvido`. CSV antigo continua válido (colunas ausentes = vazio, nunca presumidas). | `analista-financeiro.md`, `gerar_diagrama_financeiro.py` | baixo |
| B | Fluxograma: contorno ou selo por estado (ex.: bloqueado, devolvido) e rodapé com os totais da quantificação padrão, calculados só de linhas com valor documentado. | `gerar_diagrama_financeiro.py`, `teste_diagrama_docx.py` | baixo |
| C | Totais no `fluxo-financeiro.md` e no gate: `conferir_minuta.py` confere que valor devolvido/bloqueado citado na minuta consta do CSV. | `conferir_minuta.py` | médio |
| D | Seção opcional "Recuperação de valores e ativos" no modelo de minuta, preenchida só quando houver MED, bloqueio ou devolução nos autos; ausente caso contrário. | skill `relatorio-ip-fraude`, `gerar_docx.py` | médio |
| E | Matriz de recuperação como saída do analista financeiro (CSV/Markdown), sem gerar medida jurídica: providências ficam como **sugestão à autoridade** | `analista-financeiro.md` | baixo |

## Condições (não negociáveis)

- **Regra 3/4 do CLAUDE.md:** estado e valor só com fonte nos autos; ausência vira lacuna em caixa alta ("DADOS FALTANTES"), nunca dedução. Nunca chamar o último destino de beneficiário final nem atribuir ativo a pessoa só por titularidade formal.
- **Reserva jurisdicional:** o texto de providências deve registrar que movimentação bancária e quebra de sigilo exigem ordem judicial (LC 105/2001): a lacuna apontada na revisão do PR #17 precisa estar corrigida antes de copiar a skill.
- **Compatibilidade:** casos já feitos continuam gerando DOCX idêntico; as colunas e a seção novas são opcionais.
- **Estilo (regra 13/AGENTS §1.13):** texto corrido, conciso, focado na dinâmica e nos valores; a matriz fica em `02-analise`, não entra inteira no relatório.
- **Dados de caso** nunca vão para o acervo: o core importa a **metodologia**, não casos.

## Tarefas propostas (para o quadro, se o investigador aprovar)

- **GR01** (A+B): colunas opcionais e fluxograma por estado. Arquivos: `analista-financeiro.md`, `gerar_diagrama_financeiro.py`, `teste_diagrama_docx.py`.
- **GR02** (C): conferência dos valores devolvidos/bloqueados no gate. Arquivo: `conferir_minuta.py`.
- **GR03** (D+E): seção opcional e matriz de recuperação. Depende de GR01 e da correção jurídica do PR #17.

Pré-requisito comum: merge do PR #17 (ou decisão expressa de incorporar sem esperar o merge).
