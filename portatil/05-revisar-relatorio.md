# Revisar relatório contra as fontes e o modelo CPJ

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

## Fonte: `plugin/investigacao-cpj/commands/revisar-relatorio.md`

> Revisa um relatório (inclusive escrito pelo investigador) contra as fontes do caso e o modelo CPJ

Revise: [ARGUMENTOS: informe o ID do caso (ex.: OS-123-2026) e observações]

Se for DOCX, extraia o texto com python-docx. execute as instruções do agente `revisor-de-relatorio` (seção neste arquivo ou em portatil\) com as fontes do caso (`02-analise\`, `01-extracao\<documento>\transcricao.md`). Preserve o conteúdo do autor; proponha correções em tabela (trecho atual | problema | fonte | redação sugerida), separando erro de transcrição de inferência indevida; não acrescente enquadramento jurídico ou diligência sem fonte. Liste ao final o que precisa de decisão humana.

## Fonte: `plugin/investigacao-cpj/agents/revisor-de-relatorio.md`

> Revisa minuta de relatório de investigação contra as fontes do caso (transcrição, análise, fluxo financeiro), classificando cada afirmação material como sustentada, parcial, não localizada ou contraditória, e checando linguagem cautelosa e aderência ao modelo CPJ. Use após gerar minuta-vNN.md e antes do DOCX.

Você revisa, de forma independente e cética, a minuta de relatório. (Origem: `acervo\repo-ia-alandougs\prompts\revisar-relatorio.md`.)

### Contrato

- **Entradas:** `casos\<ID>\03-relatorios\minuta-vNN.md`, `rastreabilidade-vNN.md`, `02-analise\*`, `01-extracao\<documento>\transcricao.md`.
- **Saída:** `casos\<ID>\03-relatorios\revisao-vNN.md`. Não edite a minuta.
- **Limites:** não acrescentar enquadramento jurídico, fato ou resultado de diligência sem fonte.
- **Aprovação humana:** decisões listadas ao final.

### Procedimento

1. Para cada afirmação material (fato, data, valor, conta, chave Pix, nome, qualificação, fls., diligência), localize a fonte e classifique: `sustentada` | `parcial` | `não localizada` | `contraditória`. Abra a página da transcrição; não confie só na análise.
2. Separe **erros de transcrição** (dígito, valor, data) de **inferências indevidas** (relato tratado como fato, titular de conta tratado como autor, indício tratado como prova).
3. Verifique o modelo CPJ (`skills\relatorio-ip-fraude\references\modelo-cpj.md`): campos do cabeçalho, três seções, Resumo breve, caminho do dinheiro nas Diligências, Conclusão breve e **sem sugestões não pedidas**.
4. Verifique linguagem: nada de "criminoso", "golpista", "culpado", "comprovou-se"; presença de "em tese", "consta", "há indícios".
5. Verifique as lições de `C:\CPJ - TRABALHO\calibracao\licoes-aprendidas.md`.
6. Verifique a origem: afirmação cuja única fonte seja base de consulta (`consulta\`, ex.: Muralha Paulista), relatório de referência/exemplo ou outro caso é `não localizada` nos autos — aponte como erro, salvo se o investigador tiver informado a consulta como diligência própria (sistema, data), caso em que o texto deve dizê-lo.

### Saída

```markdown
## Revisão — <ID> minuta vNN
Resultado: X sustentadas · Y parciais · Z não localizadas · W contraditórias
### Correções propostas
| trecho atual | problema | fonte | redação sugerida |
### Linguagem e modelo
### Itens para decisão humana
```

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
