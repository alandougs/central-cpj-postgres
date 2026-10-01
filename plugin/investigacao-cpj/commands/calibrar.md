---
description: Calibra o sistema comparando a minuta da IA com a versão final do investigador e registra lições genéricas
argument-hint: <ID do caso> | geral
---

Calibre a partir de: $ARGUMENTS

**Caso específico:**
1. Compare `03-relatorios\minuta-vNN.md` (última da IA) com `RELATORIO-<ID>-FINAL.md` (versão do investigador) e com `revisao-vNN.md`.
2. Classifique cada diferença: estilo/redação, estrutura, conteúdo acrescentado pelo investigador, conteúdo removido, erro factual da IA, excesso de cautela, termo preferido.
3. Converta em **lições genéricas e acionáveis**, sem nomes, números, contas ou fatos do caso (ex.: "Na Conclusão, não usar 'restou comprovado'; usar 'foram reunidos elementos indicativos'").
4. Mostre as lições propostas e **peça aprovação**. Aprovadas → acrescente em `calibracao\licoes-aprendidas.md` (seção adequada, com data e ID do caso de origem) e registre em `calibracao\historico-calibracao.md` (data, caso, nº de diferenças por categoria, lições aprovadas/rejeitadas).
5. Se uma lição exigir mudança de procedimento (skill, agente, comando), proponha a edição exata no arquivo do plugin em `plugin\investigacao-cpj\`, aplique só com aprovação, aumente a versão em `.claude-plugin\plugin.json` e informe que é preciso rodar `claude plugin update investigacao-cpj@cpj-local` (ou reiniciar a sessão).

**`geral`:** leia `historico-calibracao.md` e os últimos relatórios FINAL (via `producao\base.json`), identifique padrões recorrentes, consolide/remova lições duplicadas ou obsoletas e proponha as mudanças — sempre com aprovação.

**Referências por autor e peso** (relatórios anteriores do investigador ou de colegas, importados na Central → Sistema → Relatórios de referência ou por `referencias.py importar <arquivo> --autor "<Nome>" --modalidade <código> --peso 1-5`):
- Liste com `referencias.py listar [--autor "<Nome>"]`. Peso 5 = modelo exemplar … 1 = usar com reservas.
- Extraia lições de **estilo, estrutura e encadeamento** das referências de peso ≥ 4, priorizando o próprio investigador; registre o autor de origem no histórico. Divergência de estilo entre autores vira preferência declarada (qual prevalece), não mistura.
- Referência nunca é fonte de fato para caso algum e seus dados nunca entram em `calibracao\`.
- Para mudar o peso de uma referência: `referencias.py atualizar <REF_ID> --peso N` (com aprovação do investigador).

Nunca grave dados de casos em `calibracao\`.