# Receber e processar o material do IP (PDF → OCR → Markdown por página, CSV, entidades)

*Arquivo portátil gerado em 2026-10-01 10:50 a partir do plugin `investigacao-cpj`. Autocontido: serve para qualquer agente de IA. Não edite aqui — edite o plugin e rode `ferramentas\exportar-portatil.py`.*

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
10. **OSINT de empresas (exceção autorizada pelo investigador, 28/09/2026):** empresa (pessoa jurídica) citada nos autos **sem dados** → pesquisar em fontes abertas o máximo de dados verdadeiros, confirmar por duas fontes e citar a fonte no relatório. Enviar à internet **somente CNPJ/razão social/cidade** — nunca nomes de investigados/vítimas, valores ou trechos dos autos. Pessoa física só com pedido expresso. Procedimento: `plugin\investigacao-cpj\skills\analise-ip-fraude\references\osint-empresas.md`; registro em `02-analise\osint-empresas.md`. Para qualquer pesquisa em fontes abertas (método, base legal, fontes, captura de prova) use a skill `osint-policial` (`plugin\investigacao-cpj\skills\osint-policial\`).
11. **Dados faltantes (aviso em CAIXA ALTA):** se faltar dado **muito importante** para apurar a infração penal, a materialidade, a autoria e as circunstâncias (CF, art. 144, § 4º; CPP, art. 6º) — qualificação, objeto, pessoa, empresa, telefone, extrato, veículo, local etc. —, **não deduza nem invente**: avise o operador em **CAIXA ALTA**, sob o título `DADOS FALTANTES — PROVIDENCIAR (OPERADOR)`, na resposta final e em `02-analise\dados-faltantes.md`, com o que falta, onde/como obter (sistema policial, ofício, ordem judicial, OSINT, diligência) e por que importa. No relatório vira ressalva objetiva na Conclusão, sem sugerir providência. Procedimento: `plugin\investigacao-cpj\skills\analise-ip-fraude\references\dados-faltantes.md`.
12. **Tratamento do(a) delegado(a):** ajuste saudação e endereçamento ao **gênero** de quem preside o feito (masculino: "EXCELENTÍSSIMO SENHOR DOUTOR DELEGADO DE POLÍCIA" e, ao final, "Ao Excelentíssimo Sr. Dr. / NOME / Delegado de Polícia / Central de Polícia Judiciária"; feminino: "EXCELENTÍSSIMA SENHORA DOUTORA DELEGADA DE POLÍCIA" e "À Excelentíssima Sra. Dra. / NOME / Delegada de Polícia / Central de Polícia Judiciária"). Descubra o gênero nos documentos do caso (ex.: "Dr."/"Dra." nas conclusões, "o/a Delegado/a"); **não infira pelo nome**. Sem base, pergunte ao operador e avise em CAIXA ALTA. Na minuta use `delegado_genero: M` ou `F`.
13. **Estilo e formatação do relatório (mão do investigador):** texto **corrido**, jurídico, objetivo e humano; **sem tópicos, marcadores, negritos de abertura e listas** no corpo (evita aparência de texto gerado por IA); tabela só para a planilha do caminho do dinheiro, quando necessária. **Resumo dos fatos** compacto: a dinâmica do golpe e, sobretudo, os **valores movimentados**. Fls. só em pontos de muita relevância e dados financeiros. Conclusão breve, sem sugestões de providência salvo pedido.
    - **Nomes de pessoas e empresas:** sempre em **NEGRITO E CAIXA ALTA** (ex.: `**JOÃO DA SILVA**`, `**BANCO BRADESCO S.A.**`).
    - **Demais informações importantes:** destacadas em negrito normal (`**dado**`).
    - **Informações super relevantes:** grifadas de amarelo (use a marcação `==texto super relevante==`).
    - **Informações que o investigador deva obter ou preencher manualmente:** escritas em **CAIXA ALTA E EM VERMELHO** para alertar (use `[PESQUISAR: DADO EM CAIXA ALTA]`, `[OBTER: ...]`, `{PREENCHER: ...}`). O gerador DOCX automaticamente aplica a cor vermelha e caixa alta.

14. **Um agente por Ordem de Serviço:** antes de extrair, analisar ou redigir qualquer O.S. de `E:\ORDENS DE SERVIÇO CPJ`, rode `python ferramentas\fila-os.py listar` e reserve com `assumir <nº> --agente <nome>` (ou `proxima --agente <nome>`). Não pegue O.S. `em_andamento` de outro agente nem refaça O.S. `concluida`/`com_relatorio` sem pedido expresso do investigador. Workspace canônico dos casos: `casos`. Ao terminar, `concluir <nº> --agente <nome> --docx "<caminho>"` e copie o DOCX final para a pasta da O.S.; se parar, `liberar ... --motivo "<onde parou>"`. A reserva vence em 4 h sem `renovar`. Quadro: `E:\ORDENS DE SERVIÇO CPJ\_CONTROLE-OS.md`.

15. **Numeração do procedimento no cabeçalho (determinação do delegado, 30/09/2026):** no campo **Referência:** e nas informações do procedimento na parte superior do relatório de inquérito policial, use **EXCLUSIVAMENTE o número do Inquérito Policial Eletrônico (IPe) e do Processo Judicial** (ex.: `Referência: IPe nº <número> / Processo nº <número>`). **NÃO coloque o número do Boletim de Ocorrência (BO)** e **NÃO coloque o número do IP local (físico/delegacia de origem)**. Esta regra é mandatória para todos os relatórios elaborados a partir de 30/09/2026.

Governança completa: `acervo\repo-ia-alandougs\governanca\seguranca-e-dados.md`.

## Como usar fora do Claude Code

- Onde estiver `/comando`, siga o texto daquele comando abaixo. Onde disser "skill X" ou "agente X", as instruções estão neste arquivo ou em `portatil\`.
- Scripts Python ficam em `plugin\investigacao-cpj\skills\<skill>\scripts\` (PowerShell, `python`). Sem execução de comandos, peça ao usuário para rodá-los.
- Sem subagentes: execute as etapas em sequência.

## Fonte: `plugin/investigacao-cpj/commands/novo-caso.md`

> Cria o caso pela Ordem de Serviço (pasta casos\OS-...), opcionalmente copiando o PDF/MD para 00-originais

Crie o caso: [ARGUMENTOS: informe o ID do caso (ex.: OS-123-2026) e observações]

Forma preferida: a **Central CPJ** (`Central CPJ.bat` → aba Entrada) cria o caso e já processa os arquivos. Use este comando quando o usuário pedir pelo Claude.

1. Sem nº de O.S., pergunte. O ID da pasta é gerado a partir dela (`123/2026` → `OS-123-2026`).
2. `python "plugin\investigacao-cpj\skills\base-cpj\scripts\caso.py" novo --os "<O.S.>" [--bo ...] [--ip ...] [--processo ...] [--natureza ...]`
3. Se foi informado arquivo, **copie** (nunca mova) para `casos\<ID>\00-originais\` e siga com `/processar-ip <ID>`.
4. Responda em até 4 linhas: pasta do caso e próximo passo.

## Fonte: `plugin/investigacao-cpj/commands/processar-ip.md`

> Processa os arquivos do caso (PDF → diagnóstico, OCR, Markdown por página, CSV, entidades; ou MD/CSV prontos) e completa a transcrição visual das páginas pendentes

Processe o material do caso: [ARGUMENTOS: informe o ID do caso (ex.: OS-123-2026) e observações]

Use a skill `pdf-autos-policiais`. Caminhos: `$S = "plugin\investigacao-cpj\skills\pdf-autos-policiais\scripts"`, `$B = "plugin\investigacao-cpj\skills\base-cpj\scripts"`, caso em `casos\<ID>\`.

1. **Verifique `processamento.json`** do caso. Documentos já `concluido` pela Central CPJ **não** devem ser reprocessados. Documentos em `na_fila`/`processando`: aguarde (a Central está trabalhando). Em `erro`: leia `01-extracao\<doc>\processamento.log`, explique e corrija.
2. Para cada arquivo de `00-originais\` ainda sem pasta em `01-extracao\` (quando o usuário não usou a Central), com `$E = "...\01-extracao\<nome do arquivo sem extensão>"`:
   - **PDF:** `$env:PATH += ";C:\Program Files\Tesseract-OCR"`; se existir `ferramentas\tessdata\por.traineddata`, `$env:TESSDATA_PREFIX = "$PWD\ferramentas\tessdata"`. Rode `diagnostico.py` → `extrair.py <pdf> --saida $E --lang por` (use `eng` só se `por` não existir, e avise) → `tabelas.py <pdf> --saida $E` → `tabelas.py $E\transcricao.md --saida $E` → `entidades.py $E\transcricao.md` → `caso.py ip <ID> $E\relatorio_extracao.json`.
   - **MD:** copie para `$E\transcricao.md` → `tabelas.py` → `entidades.py`. **CSV:** copie para `$E\tabelas\`.
3. **Complete o que a máquina não resolve:** para páginas em `pendentes_transcricao_visual` ou `conferir_visualmente` (`relatorio_extracao.json`), leia os PNGs de `$E\paginas_visao\` em lotes de ~20, grave `$E\transcricoes_visuais\pNNNN.md` pelas regras de transcrição da skill (tabelas em Markdown) e rode `extrair.py` de novo + `tabelas.py`/`entidades.py` sobre a transcrição. Se forem muitas páginas, informe o volume antes e pergunte se deve priorizar só as páginas críticas (extratos, comprovantes, qualificações).
4. Atualize `registro-tratamento.md`, rode `python "$B\indexar.py"` e resuma: páginas por método, pendências, tabelas CSV, entidades. Próximo passo: `/analisar-ip <ID>`.

## Fonte: `plugin/investigacao-cpj/skills/pdf-autos-policiais/SKILL.md`

> Prepara PDFs de inquéritos, processos e procedimentos policiais para análise por IA com segurança e rastreabilidade. Diagnostica o arquivo (páginas, camada de texto, hash), extrai transcrição Markdown página a página (texto nativo, OCR Tesseract em português ou transcrição visual), tabelas em CSV e dados críticos candidatos; ou divide em partes de até 100 páginas. Use sempre que o usuário enviar ou mencionar PDF de IP, autos, processo, BO, RDO, TCO, laudo, extrato ou peça digitalizada, ou disser "processa esse IP", "faz OCR", "extrai o texto", "extrai as tabelas", "transforma em markdown", "divide o PDF", "PDF muito grande", "o Claude não leu o PDF inteiro".

## PDF de Autos Policiais: diagnóstico, extração estruturada ou divisão

> Origem: `repo-ia-alandougs/skills/pdf-autos-policiais` (estado: rascunho). Adaptada para Claude Code no Windows (PowerShell, `python`), com etapa de tabelas → CSV e integração ao workspace CPJ.

Prepara PDFs volumosos de inquéritos, processos e procedimentos para que a análise por IA seja completa, auditável e citável por página. Quando o modelo lê e interpreta ao mesmo tempo, um erro de leitura (um dígito de CPF, conta ou valor) entra na conclusão sem deixar registro conferível. Por isso, aqui a regra é: **primeiro transcrever com método registrado, depois analisar sobre a transcrição**.

Dois caminhos:

- **B — Extração estruturada (padrão neste ambiente):** transcrição página a página com método registrado, tabelas em CSV, dados críticos candidatos, índice de peças.
- **A — Dividir** em partes de até 100 páginas, preservando a leitura visual (útil para envio ao Claude.ai/Projetos ou para peças predominantemente visuais).

---

### Quando usar

- O usuário coloca/menciona PDF de IP, processo, procedimento, BO/RDO, TCO, laudo, extrato bancário, relatório de quebra, peça digitalizada.
- O usuário pede para analisar, resumir, montar cronologia, extrair qualificação, cruzar dados ou redigir relatório com base em autos em PDF.
- O usuário diz: "faz OCR", "extrai o texto", "extrai as tabelas", "transforma em markdown", "divide o PDF".

**Não use** quando o usuário já entregar a transcrição em Markdown (e/ou CSV): nesse caso, pule direto para a skill `analise-ip-fraude` — apenas rode `tabelas.py` sobre o `.md` se houver tabelas Markdown a converter em CSV.

---

### Onde ficam as coisas

- **Scripts:** `$S = "plugin\investigacao-cpj\skills\pdf-autos-policiais\scripts"`.
- **Caso:** `casos\<ID>\`, onde `<ID>` deriva da **Ordem de Serviço** (O.S. `123/2026` → `OS-123-2026`).
  - `00-originais\` — arquivos originais (somente leitura), **nunca modificados**.
  - `01-extracao\<documento>\` — uma pasta por arquivo original (nome do arquivo sem extensão): `transcricao.md`, `tabelas\`, `entidades.csv`, `relatorio_extracao.json`, `diagnostico.json`, `processamento.log`.
  - `02-analise\`, `03-relatorios\` — etapas seguintes.
  - `caso.json`, `processamento.json`, `registro-tratamento.md`.
- **Central CPJ** (`http://127.0.0.1:8765`, atalho `Central CPJ.bat`): o usuário normalmente envia os PDFs por ela, e ela já executa diagnóstico, extração/OCR, tabelas, entidades e indexação. **Antes de processar, verifique `processamento.json`**: se o documento já está `concluido`, não refaça — vá direto à transcrição visual das páginas pendentes/⚠ (se houver) e à análise.

---

### Processo

#### Etapa 0 — Preparar o ambiente

```powershell
python -c "import pypdf, pypdfium2, pdfplumber, PIL; print('ok')"
## se faltar:
python -m pip install pypdf pypdfium2 pdfplumber pytesseract pillow
```

OCR em português exige o **Tesseract** instalado no Windows com o idioma `por`:

```powershell
python -c "import pytesseract; print(pytesseract.get_languages(config=''))"
```

Se der erro de executável não encontrado, verifique `C:\Program Files\Tesseract-OCR\tesseract.exe` e, se existir, defina antes de rodar: `$env:PATH += ";C:\Program Files\Tesseract-OCR"`. Se o idioma `por` não aparecer, baixe `por.traineddata` (tessdata_fast, ~2 MB — confira o tamanho; poucos bytes = mensagem de erro) para uma pasta `tessdata` e aponte `$env:TESSDATA_PREFIX` para ela. **Pergunte ao usuário antes de instalar ou baixar qualquer coisa.** Sem Tesseract, o script cai para transcrição visual (PNG → leitura pelo Claude).

Trabalhe **sempre sobre cópia**. Nunca modifique o arquivo em `00-originais`.

#### Etapa 1 — Preservar e diagnosticar

```powershell
python "$S\diagnostico.py" "casos\<ID>\00-originais\arquivo.pdf"
```

Apresente ao usuário um quadro curto e registre em `registro-tratamento.md`:

| Item | Resultado |
|---|---|
| Páginas | N |
| Tamanho | X MB |
| Tipo | digital / escaneado / misto (faixas sem texto) |
| SHA-256 do original | hash |

O hash registra a integridade do original e permite comprovar depois que a análise partiu daquele arquivo.

#### Etapa 2 — Decidir o caminho

**Neste ambiente (Claude Code local), o padrão é B**, porque a leitura direta de PDF pelo Claude é limitada a lotes pequenos de páginas por chamada e não deixa registro intermediário conferível. Só pergunte se houver motivo para A:

| | **A — Dividir em partes de até 100 páginas** | **B — Extração estruturada** |
|---|---|---|
| Como funciona | O PDF é fatiado; cada parte é lida com texto + imagem de cada página (ex.: Claude.ai) | Cada página vira texto (camada nativa, OCR ou transcrição visual do Claude), com página e método registrados; tabelas viram CSV; depois índice de peças e dados críticos |
| Vantagens | Mantém leitura de manuscritos, carimbos, assinaturas, fotos, croquis e tabelas tortas; rápido; não altera o conteúdo | Texto conferível e pesquisável; cita página em cada afirmação; ocupa muito menos contexto, então o IP inteiro pode ser cruzado de uma vez; busca exata de CPF, placa, telefone, conta, Pix; tabelas de extratos em CSV; material reaproveitável em relatório e na base RAG |
| Desvantagens | Partes se somam no contexto e detalhes se perdem; cruzar informação entre partes exige consolidação; erro de leitura não deixa registro | Mais demorado em PDF escaneado; OCR erra manuscrito e carimbo e pode "corrigir" palavras; tabelas escaneadas precisam de transcrição visual; exige conferência dos dados críticos |
| Indicado para | Peças com muito manuscrito, fotos ou croquis; consulta pontual | Relatório de investigação, análise de fraude/estelionato, cronologia de transferências, cruzamento de vínculos, qualquer produto que vá aos autos |

Muitos casos pedem **B com conferência visual** das páginas críticas (extratos, comprovantes Pix, qualificações): ofereça como variante de B.

#### Etapa 3A — Dividir

```powershell
python "$S\dividir.py" "arquivo.pdf" --saida "casos\<ID>\01-extracao\partes"
python "$S\dividir.py" "arquivo.pdf" --cortes "1-92,93-180,181-260" --saida "casos\<ID>\01-extracao\partes"
```

Entregue as partes e o `MANIFESTO.json`. Oriente: uma parte por conversa, ao final gerar **Ficha da Parte** e fazer a análise final a partir das fichas. Página da parte é relativa: some o início da faixa (parte 02, faixa 101-200 → pág. 5 da parte = pág. 105 do original).

**Ficha da Parte (modelo):**

```markdown
## Ficha — Parte 02 de 03 (págs. 101–200 do original)
### Peças contidas
| Peça | Data | Págs. (original) | fls. | Síntese objetiva |
### Pessoas citadas
| Nome | Qualificação como consta | Condição no procedimento | Págs. |
### Dados críticos
| Tipo | Valor como consta | Pág. | Legibilidade (legível/duvidoso) |
### Fatos relevantes (com página)
### Lacunas e pontos a conferir
```

#### Etapa 3B — Extração estruturada

Seja `$E = "casos\<ID>\01-extracao\<documento>"` (uma pasta por arquivo original).

1. **Extrair texto página a página:**

```powershell
python "$S\extrair.py" "casos\<ID>\00-originais\arquivo.pdf" --saida $E              # auto: texto nativo > Tesseract > visual
python "$S\extrair.py" "casos\<ID>\00-originais\arquivo.pdf" --saida $E --ocr visao  # força transcrição visual pelo Claude
```

Gera `$E\transcricao.md` (seção `## Página N` por página, método em comentário) e `$E\relatorio_extracao.json`. Páginas sem texto e sem OCR, ou com OCR de confiança < 75%, são renderizadas em `$E\paginas_visao\pNNNN.png`.

2. **Transcrição visual das páginas pendentes ou a conferir:** leia os PNGs em lotes (até ~20 por rodada) e grave cada transcrição em `$E\transcricoes_visuais\pNNNN.md`, seguindo as **regras de transcrição** abaixo — **tabelas sempre em Markdown** (`| col | col |`), para virarem CSV. Depois rode `extrair.py` de novo com os mesmos parâmetros: ele incorpora as transcrições (método `transcricao-visual-llm`). Se houver centenas de páginas pendentes, avise o tempo/consumo antes e sugira instalar o Tesseract.

3. **Tabelas → CSV** (extratos, relações de transferências, planilhas de quebra):

```powershell
python "$S\tabelas.py" "casos\<ID>\00-originais\arquivo.pdf" --saida $E   # tabelas das páginas digitais
python "$S\tabelas.py" "$E\transcricao.md" --saida $E                      # tabelas Markdown (OCR/visual ou MD do usuário)
```

Gera `$E\tabelas\tNNN_pagPPPP.csv` (`;`, UTF-8 BOM, coluna `pagina_pdf`) e `$E\tabelas\indice_tabelas.csv`. Para extratos bancários, aplique em seguida o agente/comando `extrair-tabela-bancaria` para normalizar colunas (data, descrição, valor, tipo, saldo) sem interpretar identidade das partes.

4. **Dados críticos candidatos:**

```powershell
python "$S\entidades.py" "$E\transcricao.md"
```

Gera `$E\entidades.csv` (CPF, CNPJ, placa, telefone, valor, data, e-mail, fls. por página). São candidatos por padrão de texto: status "pendente de conferência" até alguém confrontar com a imagem da página.

5. **Estruturar** a partir da transcrição (não do PDF bruto), em `$E\estrutura.md`:
   - **Índice de peças:** peça, data, págs. do PDF, fls. dos autos (quando legíveis), síntese de uma linha.
   - **Pessoas:** nome como consta, qualificação como consta, condição (vítima, testemunha, investigado, indiciado, comunicante), páginas.
   - **Cronologia:** data/hora, fato, fonte (peça e página), natureza (fato documentado / relato / informação de terceiro).
   - **Dados críticos a conferir:** consolidação do `entidades.csv` sem duplicatas, com todas as páginas onde cada dado aparece e divergências (ex.: mesmo nome com CPFs diferentes).
   - **Lacunas:** páginas ilegíveis, peças referidas mas ausentes, numeração de fls. com saltos.

#### Regras de transcrição visual

- Transcreva literalmente. Não corrija ortografia, não complete abreviações, não resuma.
- Marque o que não é texto corrido: `[manuscrito: ...]`, `[carimbo: ...]`, `[assinatura ilegível]`, `[rubrica]`, `[foto: descrição objetiva do que se vê]`, `[croqui]`, `[tabela]` seguido da tabela em Markdown.
- Trecho que não dá para ler: `[ilegível]`. Dígito duvidoso: `?` no lugar e `[dígito incerto]` ao lado (ex.: `123.45?.789-00 [dígito incerto]`). **Nunca complete CPF, conta, chave Pix, placa, telefone ou valor por dedução.**
- Registre a numeração de folhas (fls.) quando estiver carimbada ou impressa na página.

#### Etapa 4 — Encaminhar para análise

A análise e o relatório seguem nas skills `analise-ip-fraude` e `relatorio-ip-fraude` (comandos `/analisar-ip` e `/relatorio-ip`). Cite sempre `(pág. 137 do PDF; fls. 142)`; página do PDF e fls. dos autos costumam ser diferentes.

---

### Output

- **B:** `transcricao.md`, `estrutura.md`, `entidades.csv`, `tabelas\*.csv` + `indice_tabelas.csv`, `relatorio_extracao.json`.
- **A:** partes `NOME_parteXXdeYY_pagsINICIO-FIM.pdf` + `MANIFESTO.json` + modelo de Ficha da Parte.

Atualize `registro-tratamento.md` do caso e feche com o quadro:

| Campo | Conteúdo |
|---|---|
| Original | nome, páginas, SHA-256 |
| Caminho adotado | A ou B (e por quê) |
| Métodos | ex.: 80 págs. texto nativo, 140 OCR, 10 transcrição visual |
| Tabelas | quantidade de CSVs e páginas de origem |
| Pendências | páginas ilegíveis ou com baixa confiança; dados críticos não conferidos |
| Data e ferramentas | data/hora e bibliotecas usadas |

---

### Restrições e cautelas

- **Sigilo:** não envie conteúdo dos autos a serviços externos de OCR ou conversão. Todo o processamento de extração é local. Lembre o usuário, uma vez por conversa, de verificar se a conta usada é compatível com o sigilo do procedimento (art. 20 do CPP) e com as normas internas do órgão; ofereça anonimizar dados de vítimas quando não forem necessários.
- **Integridade:** o original não é alterado. Transcrição, CSVs, partes e fichas são material de apoio analítico e não substituem os autos. Os arts. 158-A a 158-F do CPP tratam da cadeia de custódia de vestígios; a cópia de autos em PDF em regra não é vestígio, mas adote a mesma lógica de rastreabilidade (hash, método, data, responsável).
- **Fidelidade:** não invente conteúdo de página ilegível, não "arrume" dados divergentes, não junte homônimos sem base documental. Divergência é achado a relatar, não erro a corrigir.
- **Limites:** não afirme que leu o PDF inteiro se houver páginas pendentes. Diga quais páginas ficaram de fora.
- Não use esta skill para contornar sigilo, abrir PDF protegido por senha sem autorização do usuário, nem remover assinaturas, carimbos ou marcas de autenticação.

---

### Exemplos

**1.** IP escaneado de 312 páginas; relatório de estelionato com transferências Pix → diagnóstico; B com OCR em português; transcrição visual das páginas de baixa confiança e dos comprovantes; `tabelas.py` sobre a transcrição; `entidades.csv`; segue para `/analisar-ip`.

**2.** Processo de 180 páginas, digital, com laudo com fotos e croqui; usuário quer a dinâmica do local → recomendar A com cortes nas fronteiras das peças.

**3.** Usuário entrega `IP-123.md` já transcrito com tabelas → não usar esta skill; rodar só `tabelas.py` sobre o `.md` e seguir para `analise-ip-fraude`.

---

Validação técnica: ver `VALIDACAO.md`. Os scripts estão em `scripts/` (o apêndice com o código-fonte foi removido desta versão por já estarem instalados; o original permanece em `acervo\repo-ia-alandougs`).
