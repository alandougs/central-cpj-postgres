---
name: relatorio-ip-fraude
description: Redige o RelatÃ³rio de InvestigaÃ§Ã£o no modelo oficial da CPJ (timbre SSP/PCSP, DEINTER 8, Seccional de Presidente Prudente) para inquÃ©ritos de fraude e estelionato, a partir da anÃ¡lise rastreÃ¡vel do caso - minuta Markdown com rastreabilidade por pÃ¡gina, revisÃ£o, e geraÃ§Ã£o do DOCX com timbre, dados do procedimento e assinatura. Use quando o usuÃ¡rio pedir "faz o relatÃ³rio", "relatÃ³rio de investigaÃ§Ã£o do IP", "minuta do relatÃ³rio", "gera o docx", "relatÃ³rio para o delegado" em caso de estelionato, golpe, fraude eletrÃ´nica ou Pix.
---

# RelatÃ³rio de InvestigaÃ§Ã£o â€” IP de fraude/estelionato (modelo CPJ)

Produz a minuta do relatório **sobre a análise já feita** (`02-analise\`), nunca direto do PDF bruto. Estilo e estrutura seguem o **modelo DOCX do investigador** (`modelos\MODELO RELATORIO DE INVESTIGACAO - CPJ 2026.docx`) e o "Modelo Alan" da skill `relatorio-investigacao-policial` (método PTCFREE). Onde divergirem, **prevalece o modelo DOCX**.

## Antes de redigir (obrigatório)

1. Leia `calibracao\licoes-aprendidas.md` e aplique cada lição.
2. Leia `references\modelo-cpj.md` (estrutura e regras extraÃ­das do modelo DOCX).
3. **Exemplos (estilo e estrutura, nunca fatos):** `python "<scripts da base-cpj>\rag.py" exemplos <modalidade> --autor "<investigador de dados-padrao.json>" -n 3`. A lista junta relatÃ³rios `-FINAL` do sistema e **referÃªncias importadas** (`referencias\`, relatÃ³rios anteriores do investigador ou de colegas), ordenadas por mesma modalidade â†’ autor preferido â†’ **peso** (5 = modelo exemplar â€¦ 1 = usar com reservas). Use 1â€“2, preferindo peso â‰¥ 4 e o prÃ³prio autor; com peso â‰¤ 2, aproveite sÃ³ a estrutura. Se o Ã­ndice estiver vazio, procure `casos\*\03-relatorios\*-FINAL.md` da mesma `modalidade`. Nunca transporte nomes, nÃºmeros, datas ou conclusÃµes de um exemplo para a minuta.
4. Confirme que existem `02-analise\ficha-caso.md`, `cronologia.md`, `fluxo-financeiro.md/.csv`, `matriz-achados.md`. Se faltarem, rode antes a skill `analise-ip-fraude` (ou avise e produza com ressalvas, se o usuÃ¡rio quiser).
5. Leia a Ordem de ServiÃ§o / determinaÃ§Ã£o (escopo). O relatÃ³rio responde ao que foi pedido.
6. Carregue `modelos\dados-padrao.json` (investigador, unidade, cidade, delegado padrÃ£o).
7. **Fonte dos fatos = somente os documentos do próprio caso** (IP e peças enviadas, via `02-analise\`). Bases de consulta (`consulta\`, ex.: Muralha Paulista) servem apenas para o investigador pesquisar; o que vier delas só entra no relatório se o investigador informar que fez a consulta (sistema, data, resultado) — e então como diligência dele, citada assim.
8. **Dados do procedimento:** Sempre insira o nome do escrivão/escrivã e do Delegado de Polícia nos dados do procedimento/cabeçalho ou no início do relatório, conforme orientação do investigador.
9. **Numeração no cabeçalho (determinação do delegado, 30/09/2026):** no campo `referencia` e na identificação do procedimento no topo do relatório, use **EXCLUSIVAMENTE o número do Inquérito Policial Eletrônico (IPe) e do Processo Judicial** (ex.: `IPe nº <número> / Processo nº <número>`). **NUNCA coloque o número do Boletim de Ocorrência (BO)** e **NUNCA coloque o número do IP local (físico/delegacia de origem)**. Esta regra é mandatória para todos os relatórios elaborados daqui para frente.

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
referencia: IPe nº <número> / Processo nº <número>   # DETERMINAÇÃO DO DELEGADO (30/09/2026): SOMENTE IPe e Processo Judicial; NUNCA colocar número de BO nem IP local
natureza: Estelionato ...      # como consta nos autos
investigados: ...              # nomes como constam; "nÃ£o identificado(s)" se for o caso
vitimas: ...
local: ...
data_fatos: DD/MM/AAAA
local_data: Presidente Prudente, SP, <data por extenso>
data_rodape: DD/MM/AAAA
delegado: <NOME do(a) delegado(a) destinatÃ¡rio(a), sem "Dr.">
delegado_genero: M             # M ou F, conforme os documentos do caso (Dr./Dra.); NÃƒO inferir pelo nome; sem base, perguntar ao operador
---

## RESUMO DOS FATOS
## DILIGÃŠNCIAS REALIZADAS
## CONCLUSÃƒO
```

Os campos do cabeÃ§alho e as trÃªs seÃ§Ãµes sÃ£o exatamente os lidos pelo `scripts\gerar_docx.py`. O tÃ­tulo, saudaÃ§Ã£o, fecho, assinatura e destinatÃ¡rio jÃ¡ estÃ£o no modelo DOCX â€” **nÃ£o repita** no corpo.

### ConteÃºdo das seÃ§Ãµes (regras do modelo CPJ)

- **RESUMO DOS FATOS:** compacto, enxuto, objetivo e lÃ³gico: a **dinÃ¢mica dos fatos** (como a vÃ­tima foi induzida, por qual meio, para quem pagou) e, sobretudo, os **valores movimentados** (quanto, quando, para onde seguiu, quanto chegou ao destino), em linguagem cautelosa ("consta do boletim de ocorrÃªncia que...", "em tese"); em seguida, o que a Ordem de ServiÃ§o determinou. 1â€“2 parÃ¡grafos, **texto corrido**.
- **DILIGÃŠNCIAS REALIZADAS** (**texto corrido**, sem tÃ³picos, marcadores nem negritos de abertura; tabela sÃ³ para a planilha do caminho do dinheiro): o que foi feito e o que se obteve, em ordem lÃ³gica/cronolÃ³gica. Inclua, conforme o caso:
  - anÃ¡lise dos autos e documentos (quais, com fls.);
  - qualificaÃ§Ã£o das pessoas relevantes (nome, RG, CPF, filiaÃ§Ã£o, naturalidade, endereÃ§os, telefones) **somente como constam nos autos/consultas realizadas**;
  - **caminho do dinheiro**: vÃ­tima â†’ conta(s) de passagem â†’ destinatÃ¡rio, com datas, valores, bancos, chaves Pix e IDs de transaÃ§Ã£o, citando fls.;
  - **planilha** (tabela Markdown) quando necessÃ¡ria para demonstrar a dinÃ¢mica financeira â€” ela vira tabela no DOCX;
  - cruzamento de dados (mesmo telefone/conta/endereÃ§o entre pessoas) e identificaÃ§Ã£o de **supostos** autores, com base indicada;
  - descriÃ§Ã£o objetiva de fotos/vÃ­deos/prints, se houver.
  NÃ£o inclua diligÃªncia que nÃ£o foi realizada. Consultas a sistemas sÃ³ se o usuÃ¡rio informar que as fez (sistema, data, resultado).
- **CONCLUSÃƒO:** breve descriÃ§Ã£o do resultado (o que foi apurado, o que nÃ£o foi possÃ­vel e por quÃª; indÃ­cios de autoria/materialidade em linguagem condicional). **SugestÃµes de providÃªncias: por padrÃ£o, NÃƒO sugerir** â€” o modelo determina ponderar e preferir deixar Ã  discricionariedade do delegado. SÃ³ inclua sugestÃ£o se o usuÃ¡rio pedir ou se for claramente cabÃ­vel e delimitada Ã  Ordem de ServiÃ§o; nesse caso, uma frase, sinalizando quando depende de autorizaÃ§Ã£o judicial (ex.: afastamento de sigilo bancÃ¡rio/fiscal, busca e apreensÃ£o).

### Estilo (mÃ£o do investigador) e tratamento

- **Texto corrido**, voz do investigador (primeira pessoa discreta, direta, jurÃ­dica e humana). Sem tÃ³picos, listas, negritos de abertura ("**Claudia (Inter).**") ou frases paralelas em sÃ©rie, para que o texto nÃ£o pareÃ§a gerado por IA. Frases variadas, sem jargÃ£o desnecessÃ¡rio, sem adjetivaÃ§Ã£o.
- **Delegado(a):** o modelo DOCX traz "(A)" nas flexÃµes; `gerar_docx.py` corrige saudaÃ§Ã£o e endereÃ§amento final pelo campo `delegado_genero` (M: "EXCELENTÃSSIMO SENHOR DOUTOR DELEGADO DE POLÃCIA," e "Ao ExcelentÃ­ssimo Sr. Dr. / NOME / Delegado de PolÃ­cia / Central de PolÃ­cia JudiciÃ¡ria"; F: "EXCELENTÃSSIMA SENHORA DOUTORA DELEGADA DE POLÃCIA," e "Ã€ ExcelentÃ­ssima Sra. Dra. / NOME / Delegada de PolÃ­cia / Central de PolÃ­cia JudiciÃ¡ria"). Descubra o gÃªnero nos documentos do caso; nÃ£o infira pelo nome.
- **Formatação de texto no DOCX (Regra mandatória do investigador):**
  - **Nomes de pessoas e empresas:** sempre em **NEGRITO E CAIXA ALTA** (ex.: `**JOÃO DA SILVA**`, `**BANCO BRADESCO S.A.**`).
  - **Demais informações importantes:** destacadas em negrito normal (`**dado**`).
  - **Informações super relevantes:** grifadas de amarelo (use a marcação `==texto super relevante==`).
  - **Informações que o investigador deva obter ou preencher manualmente:** escritas em **CAIXA ALTA E EM VERMELHO** para alertar (use a marcação `[PESQUISAR: QUALIFICAÇÃO COMPLETA]`, `[OBTER: COMPROVANTE]`, `{PREENCHER: DADO EM FALTA}`).

### Citações

- No texto do relatÃ³rio, cite **fls. dos autos** sÃ³ em pontos de muita relevÃ¢ncia e nos dados financeiros: `(fls. 45)`. Sem fls., use `(pÃ¡g. 45 do arquivo)` e marque a pendÃªncia. A rastreabilidade completa fica em `rastreabilidade-vNN.md`, nÃ£o no texto.
- Gere junto `03-relatorios\rastreabilidade-vNN.md`: `| trecho do relatÃ³rio | fonte (pÃ¡g./fls.) | natureza | conferido? |` para cada afirmaÃ§Ã£o material.

## Fluxo

1. Minuta `minuta-vNN.md` + `rastreabilidade-vNN.md` (NN = prÃ³xima versÃ£o livre). `caso.py status <ID> minuta`.
2. RevisÃ£o pelo agente `revisor-de-relatorio` â†’ `revisao-vNN.md` (sustentada/parcial/nÃ£o localizada/contraditÃ³ria). Corrija o que for erro objetivo; leve ao usuÃ¡rio o que depender de decisÃ£o.
3. Mostre ao usuÃ¡rio: resumo, pendÃªncias (`{...}`), dados crÃ­ticos nÃ£o conferidos.
4. Com a aprovaÃ§Ã£o do usuÃ¡rio, gere o DOCX:

```powershell
python "<base da skill>\scripts\gerar_docx.py" "casos\<ID>\03-relatorios\minuta-vNN.md" --saida "casos\<ID>\03-relatorios\RELATORIO-<ID>-vNN.docx"
# rascunho sem assinatura: acrescente --sem-assinatura
```

O script preserva timbre, rodapÃ© (paginaÃ§Ã£o automÃ¡tica) e assinatura do modelo, atualiza a data do rodapÃ© e lista campos que ficaram com texto-guia.
5. Quando o usuÃ¡rio disser que o relatÃ³rio foi entregue/finalizado: copie a versÃ£o final para `RELATORIO-<ID>-FINAL.md` (e, se ele editou o DOCX, extraia o texto do DOCX final para esse `.md`), rode `caso.py relatorio <ID> ...` e `caso.py status <ID> entregue` (skill `base-cpj`) e sugira `/calibrar <ID>`.

## Nunca

- Inventar fatos, fls., qualificaÃ§Ã£o, diligÃªncias, consultas, nÃºmeros de procedimento ou dispositivos legais.
- "Criminoso", "autor comprovado", "golpista", "culpado". Use "investigado(a)", "titular da conta destinatÃ¡ria", "suposto autor".
- Afirmar quebra de sigilo, medida cautelar ou consulta que nÃ£o conste como realizada/autorizada.
- Levar dado crÃ­tico nÃ£o conferido Ã  conclusÃ£o sem marcÃ¡-lo.
- Usar base de consulta (`consulta\`) ou relatÃ³rio de referÃªncia/exemplo como fonte de fato, qualificaÃ§Ã£o ou antecedente.




