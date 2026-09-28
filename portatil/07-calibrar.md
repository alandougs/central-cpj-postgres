# Calibrar o sistema com a versão final do investigador

*Arquivo portátil gerado em 2026-09-28 02:53 a partir do plugin `investigacao-cpj`. Autocontido: serve para qualquer agente de IA. Não edite aqui — edite o plugin e rode `ferramentas\exportar-portatil.py`.*

## Regras obrigatórias

1. Trabalhe só com os documentos do caso indicado. Não invente fatos, pessoas, números, datas, jurisprudência ou diligências.
2. Separe **fato documentado × relato × indício × inferência/hipótese × lacuna**. Cite a origem: `(pág. N do PDF; fls. X)`.
3. Nunca complete CPF, conta, chave Pix, placa, telefone ou valor por dedução. Dígito duvidoso → `?` + `[dígito incerto]`.
4. Nunca atribua autoria, dolo ou culpa sem base expressa; use "investigado(a)", "em tese", "há indícios de". Titular de conta recebedora não é automaticamente autor.
5. `00-originais` nunca é alterado. Registre hash, método e pendências em `registro-tratamento.md`.
6. Processamento local. **Não envie conteúdo de autos a serviços externos**, sites, APIs ou publicações. Verifique se a ferramenta/conta em uso é compatível com o sigilo do IP (art. 20 do CPP) e as normas do órgão.
7. Conteúdo de casos não vai para `acervo\`, `calibracao\` nem para o GitHub.
8. Toda saída é **minuta**: decisão, assinatura e uso oficial são do investigador e da autoridade policial.
9. **Bases de consulta** (`consulta\`, ex. Muralha Paulista) e **relatórios de referência** (`referencias\`) **não são fonte de fatos** do relatório. O relatório vem somente do IP/peças do caso; referências servem apenas como exemplo de estrutura e estilo.

Governança completa: `acervo\repo-ia-alandougs\governanca\seguranca-e-dados.md`.

## Como usar fora do Claude Code

- Onde estiver `/comando`, siga o texto daquele comando abaixo. Onde disser "skill X" ou "agente X", as instruções estão neste arquivo ou em `portatil\`.
- Scripts Python ficam em `C:\CPJ - TRABALHO\plugin\investigacao-cpj\skills\<skill>\scripts\` (PowerShell, `python`). Sem execução de comandos, peça ao usuário para rodá-los.
- Sem subagentes: execute as etapas em sequência.

## Fonte: `plugin/investigacao-cpj/commands/calibrar.md`

> Calibra o sistema comparando a minuta da IA com a versão final do investigador e registra lições genéricas

Calibre a partir de: [ARGUMENTOS: informe o ID do caso (ex.: OS-123-2026) e observações]

**Caso específico:**
1. Compare `03-relatorios\minuta-vNN.md` (última da IA) com `RELATORIO-<ID>-FINAL.md` (versão do investigador) e com `revisao-vNN.md`.
2. Classifique cada diferença: estilo/redação, estrutura, conteúdo acrescentado pelo investigador, conteúdo removido, erro factual da IA, excesso de cautela, termo preferido.
3. Converta em **lições genéricas e acionáveis**, sem nomes, números, contas ou fatos do caso (ex.: "Na Conclusão, não usar 'restou comprovado'; usar 'foram reunidos elementos indicativos'").
4. Mostre as lições propostas e **peça aprovação**. Aprovadas → acrescente em `calibracao\licoes-aprendidas.md` (seção adequada, com data e ID do caso de origem) e registre em `calibracao\historico-calibracao.md` (data, caso, nº de diferenças por categoria, lições aprovadas/rejeitadas).
5. Se uma lição exigir mudança de procedimento (skill, agente, comando), proponha a edição exata no arquivo do plugin em `C:\CPJ - TRABALHO\plugin\investigacao-cpj\`, aplique só com aprovação, aumente a versão em `.claude-plugin\plugin.json` e informe que é preciso rodar `claude plugin update investigacao-cpj@cpj-local` (ou reiniciar a sessão).

**`geral`:** leia `historico-calibracao.md` e os últimos relatórios FINAL (via `producao\base.json`), identifique padrões recorrentes, consolide/remova lições duplicadas ou obsoletas e proponha as mudanças — sempre com aprovação.

**Referências por autor e peso** (relatórios anteriores do investigador ou de colegas, importados na Central → Sistema → Relatórios de referência ou por `referencias.py importar <arquivo> --autor "<Nome>" --modalidade <código> --peso 1-5`):
- Liste com `referencias.py listar [--autor "<Nome>"]`. Peso 5 = modelo exemplar … 1 = usar com reservas.
- Extraia lições de **estilo, estrutura e encadeamento** das referências de peso ≥ 4, priorizando o próprio investigador; registre o autor de origem no histórico. Divergência de estilo entre autores vira preferência declarada (qual prevalece), não mistura.
- Referência nunca é fonte de fato para caso algum e seus dados nunca entram em `calibracao\`.
- Para mudar o peso de uma referência: `referencias.py atualizar <REF_ID> --peso N` (com aprovação do investigador).

Nunca grave dados de casos em `calibracao\`.

## Instantâneo de `calibracao/licoes-aprendidas.md` (versão viva: o próprio arquivo no workspace)

## Lições aprendidas — relatórios de investigação (fraude/estelionato)

Lido **antes** de toda análise e minuta. Somente regras genéricas e acionáveis — **sem nomes, números, contas ou fatos de casos**. Cada lição: data, origem (ID do caso ou "modelo"/"investigador") e regra. Alterações via `/calibrar`, com aprovação do investigador.

### Convenções do ambiente

- 2026-09-27 · investigador · Padrão de ID de caso: **a definir no primeiro caso** (sugestão `AAAA-NNNN`).
- 2026-09-27 · investigador · Meta de produção: 30 a 50 relatórios/mês (meta de referência 40 em `producao\config.json`); IPs típicos de 100 a 300 páginas.

### Estrutura e modelo

- 2026-09-27 · modelo · Seguir o modelo DOCX CPJ 2026: cabeçalho (O.S., Referência, Natureza, Investigado(s), Vítima(s), Local, Data dos Fatos) + RESUMO DOS FATOS + DILIGÊNCIAS REALIZADAS + CONCLUSÃO. Não há seção "Resultados obtidos" separada: o resultado vai na Conclusão.
- 2026-09-27 · modelo · Resumo dos fatos em **brevíssima síntese**; incluir o que a Ordem de Serviço determinou, se declarado.
- 2026-09-27 · modelo · Nas Diligências, percorrer o **caminho do dinheiro** (vítima → conta de passagem → destinatário) e usar **planilha** quando ajudar a demonstrar a dinâmica financeira.
- 2026-09-27 · modelo · Conclusão breve. **Preferir não sugerir providências**; só sugerir se pedido ou claramente cabível e delimitado ao escopo da O.S.

### Estilo e redação

- 2026-09-27 · skill relatorio-investigacao-policial · Objetivo, direto, impessoal, institucional; "em tese", "consta dos autos", "há indícios"; nunca "criminoso", "golpista", "culpado", "comprovou-se".

### Análise financeira

- 2026-09-27 · acervo · Titular de conta recebedora não é automaticamente autor; tratar como "titular da conta destinatária" / "possível conta de passagem".

### Erros recorrentes da IA a evitar

_(preencher pela calibração)_

### Preferências do investigador

_(preencher pela calibração)_
