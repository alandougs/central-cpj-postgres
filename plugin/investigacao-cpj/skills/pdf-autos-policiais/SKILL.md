---
name: pdf-autos-policiais
description: Prepara PDFs de inquéritos, processos e procedimentos policiais para análise por IA com segurança e rastreabilidade. Diagnostica o arquivo (páginas, camada de texto, hash), extrai transcrição Markdown página a página (texto nativo, OCR Tesseract em português ou transcrição visual), tabelas em Markdown e dados críticos conferíveis; ou divide em partes de até 100 páginas. Use sempre que o usuário enviar ou mencionar PDF de IP, autos, processo, BO, RDO, TCO, laudo, extrato ou peça digitalizada, ou disser "processa esse IP", "faz OCR", "extrai o texto", "extrai as tabelas", "transforma em markdown", "divide o PDF", "PDF muito grande", "o Claude não leu o PDF inteiro".
---

# PDF de Autos Policiais: diagnóstico, extração estruturada ou divisão

> **Antes de executar:** leia `MEMORIA.md` na raiz do workspace — entrada comum de todos os agentes — e as fontes vivas ali indicadas, em especial `AGENTS.md` (regras obrigatórias e sigilo) e `calibracao/licoes-aprendidas.md`. As regras vigentes prevalecem sobre este procedimento.

> Origem: `repo-ia-alandougs/skills/pdf-autos-policiais` (estado: rascunho). Adaptada para Claude Code no Windows (PowerShell, `python`), com extração somente em Markdown e integração ao workspace CPJ.

Prepara PDFs volumosos de inquéritos, processos e procedimentos para que a análise por IA seja completa, auditável e citável por página. Quando o modelo lê e interpreta ao mesmo tempo, um erro de leitura (um dígito de CPF, conta ou valor) entra na conclusão sem deixar registro conferível. Por isso, aqui a regra é: **primeiro transcrever com método registrado, depois analisar sobre a transcrição**.

Dois caminhos:

- **B — Extração estruturada (padrão neste ambiente):** transcrição página a página com método registrado, tabelas em Markdown, dados críticos candidatos e índice de peças em Markdown.
- **A — Dividir** em partes de até 100 páginas, preservando a leitura visual (útil para envio ao Claude.ai/Projetos ou para peças predominantemente visuais).

---

## Quando usar

- O usuário coloca/menciona PDF de IP, processo, procedimento, BO/RDO, TCO, laudo, extrato bancário, relatório de quebra, peça digitalizada.
- O usuário pede para analisar, resumir, montar cronologia, extrair qualificação, cruzar dados ou redigir relatório com base em autos em PDF.
- O usuário diz: "faz OCR", "extrai o texto", "extrai as tabelas", "transforma em markdown", "divide o PDF".

**Não use** quando o usuário já entregar a transcrição em Markdown (e/ou CSV): nesse caso, pule direto para a skill `analise-ip-fraude` — preserve tabelas no próprio Markdown, sem criar derivados CSV/JSON.

---

## Onde ficam as coisas

- **Scripts:** `$S = "plugin\investigacao-cpj\skills\pdf-autos-policiais\scripts"`.
- **Caso:** `casos\<ID>\`, onde `<ID>` deriva da **Ordem de Serviço** (O.S. `123/2026` → `OS-123-2026`).
  - `00-originais\` — arquivos originais (somente leitura), **nunca modificados**.
  - `01-extracao\<documento>\` — uma pasta por arquivo original (nome do arquivo sem extensão): `transcricao.md`, `ordens-de-servico\*.md` e um único `.checkpoint\estado.json` essencial à retomada/OCR/qualidade; o log operacional permanece quando gerado pela Central.
  - `ordens-de-servico\`, dentro da pasta de extração de cada documento — transcrições Markdown das O.S. localizadas e `indice.md` com páginas, fonte e SHA-256. `extrair.py` gera/atualiza esses arquivos Markdown. A busca começa pelas páginas finais; a posição não determina vigência. Confira integralidade, continuações e datas no PDF antes de escolher a ordem principal.
  - `02-analise\`, `03-relatorios\` — etapas seguintes.
  - `caso.json`, `processamento.json`, `registro-tratamento.md`.
- **Central CPJ** (`http://127.0.0.1:8765`, atalho `Central CPJ.bat`): o usuário normalmente envia os PDFs por ela, e ela já executa diagnóstico, extração/OCR em Markdown e indexação. **Antes de processar, verifique `processamento.json`**: se o documento já está `concluido`, não refaça — vá direto à transcrição visual das páginas pendentes/⚠ (se houver) e à análise.

---

## Processo

### Etapa 0 — Preparar o ambiente

```powershell
python -c "import pypdf, pypdfium2, pdfplumber, PIL; print('ok')"
# se faltar:
python -m pip install pypdf pypdfium2 pdfplumber pytesseract pillow
```

OCR em português exige o **Tesseract** instalado no Windows com o idioma `por`:

```powershell
python -c "import pytesseract; print(pytesseract.get_languages(config=''))"
```

Se der erro de executável não encontrado, verifique `C:\Program Files\Tesseract-OCR\tesseract.exe` e, se existir, defina antes de rodar: `$env:PATH += ";C:\Program Files\Tesseract-OCR"`. Se o idioma `por` não aparecer, baixe `por.traineddata` (tessdata_fast, ~2 MB — confira o tamanho; poucos bytes = mensagem de erro) para uma pasta `tessdata` e aponte `$env:TESSDATA_PREFIX` para ela. **Pergunte ao usuário antes de instalar ou baixar qualquer coisa.** Sem Tesseract, o script cai para transcrição visual (PNG → leitura pelo Claude).

Trabalhe **sempre sobre cópia**. Nunca modifique o arquivo em `00-originais`.

### Etapa 1 — Preservar e diagnosticar

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

### Etapa 2 — Decidir o caminho

**Neste ambiente (Claude Code local), o padrão é B**, porque a leitura direta de PDF pelo Claude é limitada a lotes pequenos de páginas por chamada e não deixa registro intermediário conferível. Só pergunte se houver motivo para A:

| | **A — Dividir em partes de até 100 páginas** | **B — Extração estruturada** |
|---|---|---|
| Como funciona | O PDF é fatiado; cada parte é lida com texto + imagem de cada página (ex.: Claude.ai) | Cada página vira texto (camada nativa, OCR ou transcrição visual do Claude), com página e método registrados; tabelas permanecem em Markdown, com índice de peças e dados críticos |
| Vantagens | Mantém leitura de manuscritos, carimbos, assinaturas, fotos, croquis e tabelas tortas; rápido; não altera o conteúdo | Texto conferível e pesquisável; cita página em cada afirmação; ocupa muito menos contexto, então o IP inteiro pode ser cruzado de uma vez; busca exata de CPF, placa, telefone, conta, Pix; tabelas de extratos em Markdown; material reaproveitável em relatório e na base RAG |
| Desvantagens | Partes se somam no contexto e detalhes se perdem; cruzar informação entre partes exige consolidação; erro de leitura não deixa registro | Mais demorado em PDF escaneado; OCR erra manuscrito e carimbo e pode "corrigir" palavras; tabelas escaneadas precisam de transcrição visual; exige conferência dos dados críticos |
| Indicado para | Peças com muito manuscrito, fotos ou croquis; consulta pontual | Relatório de investigação, análise de fraude/estelionato, cronologia de transferências, cruzamento de vínculos, qualquer produto que vá aos autos |

Muitos casos pedem **B com conferência visual** das páginas críticas (extratos, comprovantes Pix, qualificações): ofereça como variante de B.

### Etapa 3A — Dividir

```powershell
python "$S\dividir.py" "arquivo.pdf" --saida "casos\<ID>\01-extracao\partes"
python "$S\dividir.py" "arquivo.pdf" --cortes "1-92,93-180,181-260" --saida "casos\<ID>\01-extracao\partes"
```

Entregue as partes e o `MANIFESTO.json`. Oriente: uma parte por conversa, ao final gerar **Ficha da Parte** e fazer a análise final a partir das fichas. Página da parte é relativa: some o início da faixa (parte 02, faixa 101-200 → pág. 5 da parte = pág. 105 do original).

**Ficha da Parte (modelo):**

```markdown
# Ficha — Parte 02 de 03 (págs. 101–200 do original)
## Peças contidas
| Peça | Data | Págs. (original) | fls. | Síntese objetiva |
## Pessoas citadas
| Nome | Qualificação como consta | Condição no procedimento | Págs. |
## Dados críticos
| Tipo | Valor como consta | Pág. | Legibilidade (legível/duvidoso) |
## Fatos relevantes (com página)
## Lacunas e pontos a conferir
```

### Etapa 3B — Extração estruturada

Seja `$E = "casos\<ID>\01-extracao\<documento>"` (uma pasta por arquivo original).

1. **Extrair texto página a página:**

```powershell
python "$S\extrair.py" "casos\<ID>\00-originais\arquivo.pdf" --saida $E              # auto: texto nativo > Tesseract > visual
python "$S\extrair.py" "casos\<ID>\00-originais\arquivo.pdf" --saida $E --ocr visao  # força transcrição visual pelo Claude
```

Gera `$E\transcricao.md` (seção `## Página N` por página, método em comentário) e um único `$E\.checkpoint\estado.json` para retomada e controle de qualidade, sem relatório JSON separado. Páginas sem texto e sem OCR, ou com OCR de confiança < 75%, são renderizadas em `$E\paginas_visao\pNNNN.png`.

2. **Transcrição visual das páginas pendentes ou a conferir:** leia os PNGs em lotes (até ~20 por rodada) e grave cada transcrição em `$E\transcricoes_visuais\pNNNN.md`, seguindo as **regras de transcrição** abaixo — **tabelas sempre em Markdown** (`| col | col |`), sem conversão em CSV. Depois rode `extrair.py` de novo com os mesmos parâmetros: ele incorpora as transcrições (método `transcricao-visual-llm`). Se houver centenas de páginas pendentes, avise o tempo/consumo antes e sugira instalar o Tesseract.

   **Pela Central CPJ:** na ficha do caso, use **Transcrever páginas a conferir**. O servidor seleciona a união de `pendentes_transcricao_visual`, `conferir_visualmente` e páginas com `precisa_ia` no checkpoint essencial (leitura lógica `qualidade.json` pelo leitor compatível). O aviso lista os destinos possíveis; Aceitar autoriza somente o escopo `transcricao_visual`, e Recusar/Esc não cria pedido. Somente o PNG de cada página selecionada e uma instrução fixa são enviados, pelo roteador com capacidade `vision`; o modelo configurado também deve aceitar imagens. Não são enviados o PDF inteiro, nomes de arquivos nem textos das outras páginas. DeepSeek/Groq sem visão não participam dessa rota.

   `scripts/transcrever_visual.py` grava arquivos novos com origem (provedor/modelo, página, hash do PNG) e aviso **CONFERIR**; nunca sobrescreve transcrição existente, inclusive gravação concorrente. Dígitos duvidosos devem ser `? [dígito incerto]`; a conferência humana continua obrigatória. O pedido compartilha o orçamento entre páginas, retries e fallback. A chamada enviada pode ultrapassar um teto antes da medição; a próxima é bloqueada, sem prometer limite rígido de faturamento.

   A Central valida o hash do original, os checkpoints e a disponibilidade de Tesseract antes do envio. Com os mesmos parâmetros, incorpora as transcrições sem novo OCR e atualiza a transcrição Markdown, o índice das O.S. em Markdown e a qualidade no checkpoint essencial. Se original/checkpoint/ambiente mudou, interrompe com aviso para executar processamento local primeiro. Retomar preserva arquivos já transcritos e incorpora também resultados de um pedido interrompido.

3. **Tabelas e dados críticos:** mantenha as tabelas no próprio Markdown, com página de origem e marcações de legibilidade. Não execute `tabelas.py`, `entidades.py` nem `dados_json.py` no fluxo de novos PDFs. Esses utilitários continuam disponíveis para compatibilidade com trabalho anterior, sem conversão ou exclusão indiscriminada do legado.

4. **Encaminhar a transcrição para análise:** índices, cronologia e dados críticos necessários à análise permanecem em Markdown no caso. Não gere consolidações JSON ou CSV da extração. O checkpoint essencial mantém a assinatura dos parâmetros, o SHA-256, registros por página, pendências OCR/visuais e qualidade em um único arquivo. `estado_extracao.ler()` e `transcrever_visual.ler_json()` leem também os formatos legados; não alteram nem apagam esses arquivos.

### Regras de transcrição visual

- Transcreva literalmente. Não corrija ortografia, não complete abreviações, não resuma.
- Marque o que não é texto corrido: `[manuscrito: ...]`, `[carimbo: ...]`, `[assinatura ilegível]`, `[rubrica]`, `[foto: descrição objetiva do que se vê]`, `[croqui]`, `[tabela]` seguido da tabela em Markdown.
- Trecho que não dá para ler: `[ilegível]`. Dígito duvidoso: `?` no lugar e `[dígito incerto]` ao lado (ex.: `123.45?.789-00 [dígito incerto]`). **Nunca complete CPF, conta, chave Pix, placa, telefone ou valor por dedução.**
- Registre a numeração de folhas (fls.) quando estiver carimbada ou impressa na página.

### Etapa 4 — Encaminhar para análise

A análise e o relatório seguem nas skills `analise-ip-fraude` e `relatorio-ip-fraude` (comandos `/analisar-ip` e `/relatorio-ip`). Cite sempre `(pág. 137 do PDF; fls. 142)`; página do PDF e fls. dos autos costumam ser diferentes.

---

## Output

- **B:** `transcricao.md` e `ordens-de-servico\*.md` (incluindo `indice.md`); checkpoint essencial único em `.checkpoint\estado.json`, metadados do caso/processamento e rastreabilidade preservados.
- **A:** partes `NOME_parteXXdeYY_pagsINICIO-FIM.pdf` + `MANIFESTO.json` + modelo de Ficha da Parte.

Atualize `registro-tratamento.md` do caso e feche com o quadro:

| Campo | Conteúdo |
|---|---|
| Original | nome, páginas, SHA-256 |
| Caminho adotado | A ou B (e por quê) |
| Métodos | ex.: 80 págs. texto nativo, 140 OCR, 10 transcrição visual |
| Tabelas | páginas de origem das tabelas no Markdown |
| Pendências | páginas ilegíveis ou com baixa confiança; dados críticos não conferidos |
| Data e ferramentas | data/hora e bibliotecas usadas |

---

## Restrições e cautelas

- **Sigilo:** não envie conteúdo dos autos a serviços externos de OCR ou conversão. Todo o processamento de extração é local. Lembre o usuário, uma vez por conversa, de verificar se a conta usada é compatível com o sigilo do procedimento (art. 20 do CPP) e com as normas internas do órgão; ofereça anonimizar dados de vítimas quando não forem necessários.
- **Integridade:** o original não é alterado. Transcrição, CSVs, partes e fichas são material de apoio analítico e não substituem os autos. Os arts. 158-A a 158-F do CPP tratam da cadeia de custódia de vestígios; a cópia de autos em PDF em regra não é vestígio, mas adote a mesma lógica de rastreabilidade (hash, método, data, responsável).
- **Fidelidade:** não invente conteúdo de página ilegível, não "arrume" dados divergentes, não junte homônimos sem base documental. Divergência é achado a relatar, não erro a corrigir.
- **Limites:** não afirme que leu o PDF inteiro se houver páginas pendentes. Diga quais páginas ficaram de fora.
- Não use esta skill para contornar sigilo, abrir PDF protegido por senha sem autorização do usuário, nem remover assinaturas, carimbos ou marcas de autenticação.

---

## Exemplos

**1.** IP escaneado de 312 páginas; relatório de estelionato com transferências Pix → diagnóstico; B com OCR em português; transcrição visual das páginas de baixa confiança e dos comprovantes; tabelas e dados críticos na transcrição Markdown; segue para `/analisar-ip`.

**2.** Processo de 180 páginas, digital, com laudo com fotos e croqui; usuário quer a dinâmica do local → recomendar A com cortes nas fronteiras das peças.

**3.** Usuário entrega `IP-123.md` já transcrito com tabelas → não usar esta skill; preservar as tabelas no `.md` e seguir para `analise-ip-fraude`.

---

Validação técnica: ver `VALIDACAO.md`. Os scripts estão em `scripts/` (o apêndice com o código-fonte foi removido desta versão por já estarem instalados; o original permanece em `acervo\repo-ia-alandougs`).
