---
name: relatorio-ip-fraude
description: Redige o Relatório de Investigação no modelo oficial da CPJ (timbre SSP/PCSP, DEINTER 8, Seccional de Presidente Prudente) para inquéritos de fraude e estelionato, a partir da análise rastreável do caso - minuta Markdown com rastreabilidade por página, revisão, e geração do DOCX com timbre, dados do procedimento e assinatura. Use quando o usuário pedir "faz o relatório", "relatório de investigação do IP", "minuta do relatório", "gera o docx", "relatório para o delegado" em caso de estelionato, golpe, fraude eletrônica ou Pix.
---

# Relatório de Investigação — IP de fraude/estelionato (modelo CPJ)

Produz a minuta do relatório **sobre a análise já feita** (`02-analise\`), nunca direto do PDF bruto. Estilo e estrutura seguem o **modelo DOCX do investigador** (`C:\CPJ - TRABALHO\modelos\MODELO RELATORIO DE INVESTIGACAO - CPJ 2026.docx`) e o "Modelo Alan" da skill `relatorio-investigacao-policial` (método PTCFREE). Onde divergirem, **prevalece o modelo DOCX**.

## Antes de redigir (obrigatório)

1. Leia `C:\CPJ - TRABALHO\calibracao\licoes-aprendidas.md` e aplique cada lição.
2. Leia `references\modelo-cpj.md` (estrutura e regras extraídas do modelo DOCX).
3. **Exemplos (estilo e estrutura, nunca fatos):** `python "<scripts da base-cpj>\rag.py" exemplos <modalidade> --autor "<investigador de dados-padrao.json>" -n 3`. A lista junta relatórios `-FINAL` do sistema e **referências importadas** (`referencias\`, relatórios anteriores do investigador ou de colegas), ordenadas por mesma modalidade → autor preferido → **peso** (5 = modelo exemplar … 1 = usar com reservas). Use 1–2, preferindo peso ≥ 4 e o próprio autor; com peso ≤ 2, aproveite só a estrutura. Se o índice estiver vazio, procure `casos\*\03-relatorios\*-FINAL.md` da mesma `modalidade`. Nunca transporte nomes, números, datas ou conclusões de um exemplo para a minuta.
4. Confirme que existem `02-analise\ficha-caso.md`, `cronologia.md`, `fluxo-financeiro.md/.csv`, `matriz-achados.md`. Se faltarem, rode antes a skill `analise-ip-fraude` (ou avise e produza com ressalvas, se o usuário quiser).
5. Leia a Ordem de Serviço / determinação (escopo). O relatório responde ao que foi pedido.
6. Carregue `modelos\dados-padrao.json` (investigador, unidade, cidade, delegado padrão).
7. **Fonte dos fatos = somente os documentos do próprio caso** (IP e peças enviadas, via `02-analise\`). Bases de consulta (`consulta\`, ex.: Muralha Paulista) servem apenas para o investigador pesquisar; o que vier delas só entra no relatório se o investigador informar que fez a consulta (sistema, data, resultado) — e então como diligência dele, citada assim.

**Progresso:** se o pedido veio de botão da Central CPJ, informe os marcos (análise e exemplos lidos, minuta, rastreabilidade, revisão, DOCX) com `agente-plantao.py progresso` (agente de plantão em chat; parar se responder CANCELADO) ou `progresso.py <ID> <N> "<etapa>"` (executor automático). Em uso interativo, não é necessário.

## Esquio PTCFREE (interno, não exibir)

- **P:** Investigador de Polícia Alan Douglas Silva, CPJ Presidente Prudente, atuando por Ordem de Serviço do Delegado.
- **T:** Relatório de investigação do IP/BO indicado.
- **C:** fraude/estelionato; modalidade; diligências e análises efetivamente realizadas (consultas, análise dos autos, extratos, comprovantes).
- **F:** modelo CPJ (abaixo).
- **R:** sem invenção; sem atribuição de culpa; fato × relato × indício × conclusão; placeholders `{...}` para o que faltar.
- **E:** relatórios `-FINAL` anteriores e referências importadas (por autor e peso) + lições de calibração.
- **S:** objetivo, direto, institucional, primeira pessoa discreta ("venho apresentar", "foi realizada análise"), sem retórica.

## Estrutura da minuta (`03-relatorios\minuta-vNN.md`)

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

## RESUMO DOS FATOS
## DILIGÊNCIAS REALIZADAS
## CONCLUSÃO
```

Os campos do cabeçalho e as três seções são exatamente os lidos pelo `scripts\gerar_docx.py`. O título, saudação, fecho, assinatura e destinatário já estão no modelo DOCX — **não repita** no corpo.

### Conteúdo das seções (regras do modelo CPJ)

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

### Citações

- No texto do relatório, cite **fls. dos autos** quando conhecidas: `(fls. 45)`. Sem fls., use `(pág. 45 do arquivo)` e marque a pendência.
- Gere junto `03-relatorios\rastreabilidade-vNN.md`: `| trecho do relatório | fonte (pág./fls.) | natureza | conferido? |` para cada afirmação material.

## Fluxo

1. Minuta `minuta-vNN.md` + `rastreabilidade-vNN.md` (NN = próxima versão livre). `caso.py status <ID> minuta`.
2. Revisão pelo agente `revisor-de-relatorio` → `revisao-vNN.md` (sustentada/parcial/não localizada/contraditória). Corrija o que for erro objetivo; leve ao usuário o que depender de decisão.
3. Mostre ao usuário: resumo, pendências (`{...}`), dados críticos não conferidos.
4. Com a aprovação do usuário, gere o DOCX:

```powershell
python "<base da skill>\scripts\gerar_docx.py" "casos\<ID>\03-relatorios\minuta-vNN.md" --saida "casos\<ID>\03-relatorios\RELATORIO-<ID>-vNN.docx"
# rascunho sem assinatura: acrescente --sem-assinatura
```

O script preserva timbre, rodapé (paginação automática) e assinatura do modelo, atualiza a data do rodapé e lista campos que ficaram com texto-guia.
5. Quando o usuário disser que o relatório foi entregue/finalizado: copie a versão final para `RELATORIO-<ID>-FINAL.md` (e, se ele editou o DOCX, extraia o texto do DOCX final para esse `.md`), rode `caso.py relatorio <ID> ...` e `caso.py status <ID> entregue` (skill `base-cpj`) e sugira `/calibrar <ID>`.

## Nunca

- Inventar fatos, fls., qualificação, diligências, consultas, números de procedimento ou dispositivos legais.
- "Criminoso", "autor comprovado", "golpista", "culpado". Use "investigado(a)", "titular da conta destinatária", "suposto autor".
- Afirmar quebra de sigilo, medida cautelar ou consulta que não conste como realizada/autorizada.
- Levar dado crítico não conferido à conclusão sem marcá-lo.
- Usar base de consulta (`consulta\`) ou relatório de referência/exemplo como fonte de fato, qualificação ou antecedente.
