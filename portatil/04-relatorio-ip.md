# Redigir o Relatório de Investigação no modelo CPJ e gerar o DOCX

*Arquivo portátil gerado em 2026-09-27 09:53 a partir do plugin `investigacao-cpj`. Autocontido: serve para qualquer agente de IA. Não edite aqui — edite o plugin e rode `ferramentas\exportar-portatil.py`.*

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

## Fonte: `plugin/investigacao-cpj/commands/relatorio-ip.md`

> Redige a minuta do Relatório de Investigação no modelo CPJ, revisa contra as fontes e gera o DOCX com timbre e assinatura

Elabore o relatório do caso: [ARGUMENTOS: informe o ID do caso (ex.: OS-123-2026) e observações]

Use a skill `relatorio-ip-fraude`.

1. Leia `calibracao\licoes-aprendidas.md`, `modelos\dados-padrao.json`, a análise do caso (`02-analise\`) e exemplos da mesma modalidade por autor e peso (`rag.py exemplos <modalidade> --autor "<investigador>" -n 3` — FINAL do sistema + referências importadas; só estilo/estrutura, nunca fatos). Fatos: somente os documentos do caso; bases de consulta não são fonte.
2. Se o investigador informou diligências próprias (consultas a sistemas, oitivas, campana), inclua **somente** o que ele informou. Se faltar dado do cabeçalho (O.S., delegado destinatário), use `{...}` e liste.
3. Grave `03-relatorios\minuta-vNN.md` e `rastreabilidade-vNN.md`; `caso.py status <ID> minuta`.
4. execute as instruções do agente `revisor-de-relatorio` (seção neste arquivo ou em portatil\) → `revisao-vNN.md`. Corrija erros objetivos na minuta (mesma versão) e liste o que depende de decisão.
5. Gere o DOCX (rascunho): `python "C:\CPJ - TRABALHO\plugin\investigacao-cpj\skills\relatorio-ip-fraude\scripts\gerar_docx.py" "<minuta>" --saida "casos\<ID>\03-relatorios\RELATORIO-<ID>-vNN.docx"`.
6. Apresente: caminho do DOCX, resumo da revisão, campos pendentes, dados críticos não conferidos. Diga que, após revisar/editar no Word e entregar, basta rodar `/entregar <ID>`.

## Fonte: `plugin/investigacao-cpj/skills/relatorio-ip-fraude/SKILL.md`

> Redige o Relatório de Investigação no modelo oficial da CPJ (timbre SSP/PCSP, DEINTER 8, Seccional de Presidente Prudente) para inquéritos de fraude e estelionato, a partir da análise rastreável do caso - minuta Markdown com rastreabilidade por página, revisão, e geração do DOCX com timbre, dados do procedimento e assinatura. Use quando o usuário pedir "faz o relatório", "relatório de investigação do IP", "minuta do relatório", "gera o docx", "relatório para o delegado" em caso de estelionato, golpe, fraude eletrônica ou Pix.

## Relatório de Investigação — IP de fraude/estelionato (modelo CPJ)

Produz a minuta do relatório **sobre a análise já feita** (`02-analise\`), nunca direto do PDF bruto. Estilo e estrutura seguem o **modelo DOCX do investigador** (`C:\CPJ - TRABALHO\modelos\MODELO RELATORIO DE INVESTIGACAO - CPJ 2026.docx`) e o "Modelo Alan" da skill `relatorio-investigacao-policial` (método PTCFREE). Onde divergirem, **prevalece o modelo DOCX**.

### Antes de redigir (obrigatório)

1. Leia `C:\CPJ - TRABALHO\calibracao\licoes-aprendidas.md` e aplique cada lição.
2. Leia `references\modelo-cpj.md` (estrutura e regras extraídas do modelo DOCX).
3. **Exemplos (estilo e estrutura, nunca fatos):** `python "<scripts da base-cpj>\rag.py" exemplos <modalidade> --autor "<investigador de dados-padrao.json>" -n 3`. A lista junta relatórios `-FINAL` do sistema e **referências importadas** (`referencias\`, relatórios anteriores do investigador ou de colegas), ordenadas por mesma modalidade → autor preferido → **peso** (5 = modelo exemplar … 1 = usar com reservas). Use 1–2, preferindo peso ≥ 4 e o próprio autor; com peso ≤ 2, aproveite só a estrutura. Se o índice estiver vazio, procure `casos\*\03-relatorios\*-FINAL.md` da mesma `modalidade`. Nunca transporte nomes, números, datas ou conclusões de um exemplo para a minuta.
4. Confirme que existem `02-analise\ficha-caso.md`, `cronologia.md`, `fluxo-financeiro.md/.csv`, `matriz-achados.md`. Se faltarem, rode antes a skill `analise-ip-fraude` (ou avise e produza com ressalvas, se o usuário quiser).
5. Leia a Ordem de Serviço / determinação (escopo). O relatório responde ao que foi pedido.
6. Carregue `modelos\dados-padrao.json` (investigador, unidade, cidade, delegado padrão).
7. **Fonte dos fatos = somente os documentos do próprio caso** (IP e peças enviadas, via `02-analise\`). Bases de consulta (`consulta\`, ex.: Muralha Paulista) servem apenas para o investigador pesquisar; o que vier delas só entra no relatório se o investigador informar que fez a consulta (sistema, data, resultado) — e então como diligência dele, citada assim.

**Progresso:** se o pedido veio de botão da Central CPJ, informe os marcos (análise e exemplos lidos, minuta, rastreabilidade, revisão, DOCX) com `agente-plantao.py progresso` (agente de plantão em chat; parar se responder CANCELADO) ou `progresso.py <ID> <N> "<etapa>"` (executor automático). Em uso interativo, não é necessário.

### Esquio PTCFREE (interno, não exibir)

- **P:** Investigador de Polícia Alan Douglas Silva, CPJ Presidente Prudente, atuando por Ordem de Serviço do Delegado.
- **T:** Relatório de investigação do IP/BO indicado.
- **C:** fraude/estelionato; modalidade; diligências e análises efetivamente realizadas (consultas, análise dos autos, extratos, comprovantes).
- **F:** modelo CPJ (abaixo).
- **R:** sem invenção; sem atribuição de culpa; fato × relato × indício × conclusão; placeholders `{...}` para o que faltar.
- **E:** relatórios `-FINAL` anteriores e referências importadas (por autor e peso) + lições de calibração.
- **S:** objetivo, direto, institucional, primeira pessoa discreta ("venho apresentar", "foi realizada análise"), sem retórica.

### Estrutura da minuta (`03-relatorios\minuta-vNN.md`)

```markdown
---
caso: <ID>
versao: NN
gerado_em: AAAA-MM-DD
ordem_servico: ...
referencia: ...                # BO nº / IP nº / processo digital nº, como consta
natureza: Estelionato ...      # como consta nos autos
investigados: ...              # nomes como constam; "não identificado(s)" se for o caso
vitimas: ...
local: ...
data_fatos: DD/MM/AAAA
local_data: Presidente Prudente, SP, <data por extenso>
data_rodape: DD/MM/AAAA
delegado: <nome do(a) delegado(a) destinatário(a)>
---

### RESUMO DOS FATOS
### DILIGÊNCIAS REALIZADAS
### CONCLUSÃO
```

Os campos do cabeçalho e as três seções são exatamente os lidos pelo `scripts\gerar_docx.py`. O título, saudação, fecho, assinatura e destinatário já estão no modelo DOCX — **não repita** no corpo.

#### Conteúdo das seções (regras do modelo CPJ)

- **RESUMO DOS FATOS:** brevíssima síntese do BO/autos (e quebras de sigilo, se houver), em linguagem cautelosa ("consta do boletim de ocorrência que...", "em tese"); se houver, o que a Ordem de Serviço determinou. 1–3 parágrafos.
- **DILIGÊNCIAS REALIZADAS:** o que foi feito e o que se obteve, em ordem lógica/cronológica:
  - análise dos autos e documentos (quais, com fls.);
  - qualificação das pessoas relevantes (nome, RG, CPF, filiação, naturalidade, endereços, telefones) **somente como constam nos autos/consultas realizadas**;
  - **caminho do dinheiro**: vítima → conta(s) de passagem → destinatário, com datas, valores, bancos, chaves Pix e IDs de transação, citando fls.;
  - **planilha** (tabela Markdown) quando necessária para demonstrar a dinâmica financeira — ela vira tabela no DOCX;
  - cruzamento de dados (mesmo telefone/conta/endereço entre pessoas) e identificação de **supostos** autores, com base indicada;
  - descrição objetiva de fotos/vídeos/prints, se houver.
  Não inclua diligência que não foi realizada. Consultas a sistemas só se o usuário informar que as fez (sistema, data, resultado).
- **CONCLUSÃO:** breve descrição do resultado (o que foi apurado, o que não foi possível e por quê; indícios de autoria/materialidade em linguagem condicional). **Sugestões de providências: por padrão, NÃO sugerir** — o modelo determina ponderar e preferir deixar à discricionariedade do delegado. Só inclua sugestão se o usuário pedir ou se for claramente cabível e delimitada à Ordem de Serviço; nesse caso, uma frase, sinalizando quando depende de autorização judicial (ex.: afastamento de sigilo bancário/fiscal, busca e apreensão).

#### Citações

- No texto do relatório, cite **fls. dos autos** quando conhecidas: `(fls. 45)`. Sem fls., use `(pág. 45 do arquivo)` e marque a pendência.
- Gere junto `03-relatorios\rastreabilidade-vNN.md`: `| trecho do relatório | fonte (pág./fls.) | natureza | conferido? |` para cada afirmação material.

### Fluxo

1. Minuta `minuta-vNN.md` + `rastreabilidade-vNN.md` (NN = próxima versão livre). `caso.py status <ID> minuta`.
2. Revisão pelo agente `revisor-de-relatorio` → `revisao-vNN.md` (sustentada/parcial/não localizada/contraditória). Corrija o que for erro objetivo; leve ao usuário o que depender de decisão.
3. Mostre ao usuário: resumo, pendências (`{...}`), dados críticos não conferidos.
4. Com a aprovação do usuário, gere o DOCX:

```powershell
python "C:\CPJ - TRABALHO\plugin\investigacao-cpj\skills\<skill>\scripts\gerar_docx.py" "casos\<ID>\03-relatorios\minuta-vNN.md" --saida "casos\<ID>\03-relatorios\RELATORIO-<ID>-vNN.docx"
## rascunho sem assinatura: acrescente --sem-assinatura
```

O script preserva timbre, rodapé (paginação automática) e assinatura do modelo, atualiza a data do rodapé e lista campos que ficaram com texto-guia.
5. Quando o usuário disser que o relatório foi entregue/finalizado: copie a versão final para `RELATORIO-<ID>-FINAL.md` (e, se ele editou o DOCX, extraia o texto do DOCX final para esse `.md`), rode `caso.py relatorio <ID> ...` e `caso.py status <ID> entregue` (skill `base-cpj`) e sugira `/calibrar <ID>`.

### Nunca

- Inventar fatos, fls., qualificação, diligências, consultas, números de procedimento ou dispositivos legais.
- "Criminoso", "autor comprovado", "golpista", "culpado". Use "investigado(a)", "titular da conta destinatária", "suposto autor".
- Afirmar quebra de sigilo, medida cautelar ou consulta que não conste como realizada/autorizada.
- Levar dado crítico não conferido à conclusão sem marcá-lo.
- Usar base de consulta (`consulta\`) ou relatório de referência/exemplo como fonte de fato, qualificação ou antecedente.

## Fonte: `plugin/investigacao-cpj/skills/relatorio-ip-fraude/references/modelo-cpj.md`

## Modelo CPJ 2026 — estrutura extraída do DOCX do investigador

Fonte: `C:\CPJ - TRABALHO\modelos\MODELO RELATORIO DE INVESTIGACAO - CPJ 2026.docx` (A4, margens 2 cm, Arial 12, justificado).

### Cabeçalho (timbre — preservado pelo gerador)

Brasão + tabela: SECRETARIA DA SEGURANÇA PÚBLICA / POLÍCIA CIVIL DO ESTADO DE SÃO PAULO / Departamento de Polícia Judiciária de São Paulo Interior 8 – DEINTER 8 / Delegacia Seccional de Polícia de Presidente Prudente / Central de Polícia Judiciária.

### Rodapé (preservado)

Endereço e telefones da CPJ; data (texto fixo, atualizado por `data_rodape`); "Página X de Y" (campos automáticos).

### Corpo

| Ordem | Elemento | Formato | Campo da minuta |
|---|---|---|---|
| 1 | RELATÓRIO DE INVESTIGAÇÃO | centralizado, negrito, 16 pt | — |
| 2 | Ordem de Serviço: … | negrito | `ordem_servico` |
| 3 | Referência: {BO, ofício, IP, processo digital, Carta Precatória} | negrito | `referencia` |
| 4 | Natureza: {tipificação que constar nos autos} | negrito | `natureza` |
| 5 | Investigado (s): … | negrito | `investigados` |
| 6 | Vítima(s): … | negrito | `vitimas` |
| 7 | Local: {endereço dos fatos} | negrito | `local` |
| 8 | Data dos Fatos: … | negrito | `data_fatos` |
| 9 | EXCELENTÍSSIMO (A) SENHOR (A) DOUTOR (A) DELEGADO (A) DE POLÍCIA, | negrito | — |
| 10 | Cumprimento respeitosamente Vossa Excelência e venho apresentar este relatório de investigação, conforme segue: | — | — |
| 11 | **RESUMO DOS FATOS** | negrito | `## RESUMO DOS FATOS` |
| 12 | **DILIGÊNCIAS REALIZADAS** | negrito | `## DILIGÊNCIAS REALIZADAS` |
| 13 | **CONCLUSÃO** | negrito | `## CONCLUSÃO` |
| 14 | Portanto, submeto o presente relatório… / Era o que me cumpria informar. É o relatório. | — | — |
| 15 | [local, Estado], {data} | à direita | `local_data` |
| 16 | Assinatura (imagem) / Alan Douglas Silva / Investigador de Polícia | centralizado | — |
| 17 | A(o) Excelentíssimo (a) / {Nome do Delegado} / Delegado (a) de Polícia Civil / Central de Polícia Judiciária | negrito | `delegado` |

### Instruções do próprio modelo (normativas para a redação)

- **Resumo dos fatos:** resumir os fatos investigados (BO, autos, IP, quebras de sigilo bancário/fiscal etc.) em **brevíssima síntese**; se declarado, descrever o que foi solicitado na Ordem de Serviço pela autoridade policial.
- **Diligências realizadas:** elencar e descrever as diligências, dados analisados e obtidos; qualificação (nome, RG, CPF, filiação, naturalidade, endereços, telefone); **cruzar dados**; **percorrer o caminho do dinheiro (vítima, conta de passagem, até chegar ao destinatário)**, identificando supostos autores; **elaborar planilha** se necessário à demonstração da dinâmica financeira; analisar e descrever fotos ou vídeos.
- **Conclusão:** breve descrição do resultado. Sugestão de providências **delimitada ao objetivo da Ordem de Serviço e ao escopo da investigação** (ex.: em caso especial e cabível, representação por quebra de sigilo bancário/fiscal do investigado; busca e apreensão domiciliar quando preenchidos os requisitos) — **sempre ponderar; preferível não sugerir, deixando o delegado atuar em sua discricionariedade.**

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
