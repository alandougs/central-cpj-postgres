# FV02 — revisão independente dos deltas MD02 e espaçadores DOCX

27/10/2026. Responsável: Codex-FV02. Reserva assumida pelo script da fila. **Parecer atualizado após reauditoria: achado BOM corrigido e encerrado nas fontes identificadas no complemento final; deltas MD02 e DOCX aprovados no escopo focal examinado.** A reprodução bloqueante e a primeira rodada permanecem abaixo como histórico. O gate integral final permanece pendente com a coordenação e não é substituído por esta aprovação focal.

Escopo: leitura de fontes, testes e evidências genéricas; escrita somente deste relatório e da fila pelo script. MEMORIA, AGENTS, PRD, ESPINHA-DORSAL e skills cpj-desenvolver, scope-guard, no-gold-plating e verification-before-completion consultados. Nenhum auto, caso, configuração, modelo/assinatura real, banco ou manifesto operacional de casos foi aberto. Nenhum produto ou teste foi alterado. As reproduções usaram dados fictícios em TEMP, `.venv/Scripts/python.exe -B -X utf8`, `PYTHONDONTWRITEBYTECODE=1` e cwd explícito na raiz autorizada.

## Achado inicial — P1: BOM permite apagar Markdown preenchido

Local: `plugin/investigacao-cpj/skills/pdf-autos-policiais/scripts/extrair.py`, linhas 179–182 da fonte congelada. A leitura do arquivo visual usa `encoding="utf-8"`; `strip()` não remove o caractere U+FEFF. Assim, um arquivo com BOM seguido apenas de `[PENDENTE: transcrição visual]`, ou contendo somente BOM, satisfaz a condição de texto não vazio e diferente da pendência. A guarda ignora a divergência. O fluxo existente lê novamente o arquivo com UTF-8 na linha 314, registra a página como `transcricao-visual-llm` e reconstrói o Markdown sem o texto anterior. Na reprodução, a página também deixa de constar como pendente.

Reprodução independente, sem mudança de PDF/hash/parâmetros e sem `--refazer`:

1. Gerar PDF fictício de duas páginas em branco e executar `extrair.py --ocr visao`, usando a preparação TEMP da suíte MD01.
2. No primeiro bloco de `transcricao.md`, substituir o marcador por `TEXTO FICTICIO PRESERVAR`.
3. Criar `transcricoes_visuais/p0001.md` com `write_text('[PENDENTE: transcrição visual]', encoding='utf-8-sig')`. A variante `write_text('', encoding='utf-8-sig')` também reproduz.
4. Reexecutar exatamente o comando original. Resultado observado: retorno **0**, texto fictício **perdido**, Markdown alterado. Não houve recusa antes das gravações.

Foram reproduzidas quatro combinações: estado consolidado/legado × visual vazio/visual contendo somente a pendência, sempre com BOM UTF-8. Todas retornaram zero e perderam o texto. O estado legado foi produzido a partir dos próprios registros fictícios consolidados; não se usou dado operacional. Uma quinta execução exploratória anterior confirmou o caso consolidado com marcador e mostrou método visual e remoção da pendência da primeira página no relatório de execução.

O defeito é uma lacuna da nova guarda para o risco que ela promete impedir, embora a leitura visual permissiva seja anterior ao delta. UTF-8 com BOM é uma codificação válida, não uma transcrição preenchida. A proteção já aceita BOM no Markdown de destino, mas não o considera ao classificar o conteúdo visual. A correção deve tratar coerentemente essa codificação e acrescentar regressões para as quatro combinações, preservando fluxo visual legítimo e substituição explícita. Não foi implementada por esta auditoria.

## Conferência das fontes e do escopo

O manifesto somente de código `F:/CPJ-BACKUPS/sync-github-20261027-023944/fontes-aplicadas.json` contém **341 caminhos**. Foram normalizados separadores, recusados caminhos absolutos ou com `..`, conferida resolução contida na raiz e permitidas somente áreas de código `plugin/`, `.agents/` e `ferramentas/`, sem segmentos operacionais. **341/341 SHA-256 coincidentes**, sem ausente ou divergente, na conferência inicial.

O conjunto de caminhos coincide com `fontes-aplicadas-antes-espacadores-md02.json` e `fontes-gate-final.json`. Contra o pré-estado há quatro fontes diferentes: extrair.py, teste_extracao_markdown_md01.py, gerar_docx.py e teste_docx_f04.py. Contra o gate histórico há seis: as quatro anteriores e os dois arquivos RG41, indexar.py e teste_rag_markdown_rg40.py. RG41 não foi reauditado nesta reserva.

Para MD02, os hashes das fontes anteriores em `candidato/` coincidem com o pré-estado: o diff contém 38 linhas adicionadas no extrator e 85 no teste, sem remoções. `estado_extracao.py` permanece com SHA-256 `13d237ade9d8a8edd1802649e5a366cac119f431041ac5ab44c546d45aecccd3`. A guarda antecede gravação de estado/consolidação legada e execução das páginas; a trava e a criação de diretórios preexistentes no fluxo continuam anteriores à guarda. Não é correto interpretar “antes da primeira gravação” como inexistência de qualquer operação de filesystem: a garantia examinada é anterior à gravação documental/checkpoint.

Para DOCX, os backups de `delta-titulos-espacadores/` têm hashes iguais ao pré-estado. O novo diff acrescenta sete linhas ao gerador e dezesseis linhas à fixture/teste F04, sem remoção de asserções anteriores. Contra o candidato histórico, o delta acumulado inclui também as três linhas anteriores de proteção dos títulos. O candidato histórico DOCX não é o pré-estado imediato, distinção confirmada por hash.

| Fonte congelada | SHA-256 observado |
|---|---|
| extrair.py | `c3d5d2d77a76c2117226112f2adfa30da7b530a9f6111852947f09a973d60cf1` |
| teste_extracao_markdown_md01.py | `59d7123e83ff47532743249b53bd8ffc4825bacbebdd3c57398524a0208255d2` |
| gerar_docx.py | `d656db0293aa76ef50cb326f73e8618f322641e4d4ad6b3484db1713d6ec266a` |
| teste_docx_f04.py | `5d1813c7c78a736248ab49d444c41bee4085df77f5c0517e4b8b8db0b9b3709c` |

## Verificações executadas por FV02

| Verificação própria | Resultado |
|---|---|
| `.venv/Scripts/python.exe -B -X utf8 plugin/investigacao-cpj/app/testes/teste_extracao_markdown_md01.py` | 10/10, 6,222 s, zero falhas/skips |
| `.venv/Scripts/python.exe -B -X utf8 plugin/investigacao-cpj/app/testes/teste_docx_f04.py` | 7/7, 0,340 s, zero falhas/skips |
| Reprodução extra MD02 com BOM | Quatro combinações confirmam perda de texto; não são testes aprovados de preservação |
| Ensaio em memória do bloco AST real de paginação DOCX | Sete limites conferidos: texto, tabela, `w:drawing`, `w:pict`, `w:br`, `w:fldChar`, `w:sectPr` |

MD01 cobre recusa antes de alterar bytes nos casos sem BOM, estados consolidado/legado, métodos locais/visuais, texto de um caractere, arquivo visual vazio/pendente, `reg=None`, transcrição visual legítima, retomada normal e `--refazer` explícito. Esses resultados verdes não cobrem a falha adicional encontrada.

F04 usa modelo/assinatura geométricos em TEMP. Confere título com keepNext/keepLines, espaçador com keepNext, margens, timbre, rodapé, campos de paginação, tabelas, valores e bloco assinatura/nome/cargo. O ensaio adicional executou somente o bloco AST da fonte real, sem importar o programa inteiro, sobre documentos sintéticos em memória: dois separadores vazios recebem keepNext e a propagação para antes do conteúdo/elemento delimitador. Não houve renderização no Word ou LibreOffice nem inspeção de relatório operacional; propriedades XML não certificam paginação visual em toda situação. Não se generaliza a proteção para quaisquer objetos OOXML diferentes dos tipos explicitamente examinados.

## Evidências lidas e limites

O relatório MD02 e o resumo genérico `delta-espacadores-md02-validado.json` registram testes dirigidos de terceiros: MD01 10, PX05 11, UN17 3, SZ02 9 e extração Codex 1, mais 22 verificações OCR; DOCX F04 7, SIG01 12 e RG28 5. FV02 repetiu apenas MD01 e F04, além dos ensaios descritos, e não soma essa repetição como cobertura distinta. O histórico RED foi examinado documentalmente; não foi reexecutado nesta auditoria.

A intermitência UN17 registrada (`interrompido=False`) teve reteste isolado verde com as mesmas fontes, mas sua causa e eliminação não foram demonstradas. Não foi repetido UN17 nem executado full concorrente. O gate 145/145 com oito cenários ambientais ignorados é histórico e anterior aos seis arquivos posteriores: não certifica o snapshot atual. Novo full cabe à coordenação quando cessarem operações concorrentes, depois da correção bloqueante e da respectiva reauditoria.

Esta conclusão não aprova publicação/instalação, não certifica conteúdo ou qualidade de transcrições, não altera flags/imagens e não registra entrega oficial. O relatório genérico e o registro FV02 são as únicas escritas públicas da auditoria.

## Complemento — correção BOM reauditada independentemente

A coordenação reabriu MD02 ao executor e pediu continuidade da FV02. A tarefa FV02 foi reaberta e assumida pelo script; este complemento substitui o bloqueio da primeira rodada. A correção foi feita pelo executor MD02, não pelo auditor.

O extrator agora centraliza a leitura em `ler_transcricao_visual`, com `encoding="utf-8-sig"`, remoção de espaços periféricos e retorno `None` para vazio ou marcador de pendência. Tanto a pré-checagem quanto a incorporação usam esse leitor. Um BOM de codificação não é mais contado como texto. O visual vazio/pendente continua pelo caminho normal de checkpoint/extração, preservando a pendência quando a página já era pendente; o texto visual legítimo com BOM entra sem o caractere de codificação. A guarda continua sob a trava e antes da consolidação/gravação documental. Não há leitura/alteração de caso real nesta verificação.

Verificações próprias novas:

| Verificação | Resultado independente |
|---|---|
| MD01 pelo mesmo entrypoint/runtime anterior | **12/12**, 7,855 s, zero falhas/skips |
| Reexecução das quatro reproduções exatas da perda | **4/4 recusadas**, retorno 1, mensagem sobre transcricao.md, todos os bytes da extração e do PDF preservados |
| Integridade do conjunto de fontes | 341 caminhos conferidos: snapshot anterior com apenas os dois hashes corrigidos explicitamente substituídos; zero divergências adicionais |

Os quatro cenários adicionais continuam sendo consolidado/legado × visual apenas BOM/visual BOM com placeholder. O auditor repetiu o mesmo preparo e adicionou a comparação integral dos arquivos da extração e do PDF: não ocorreu consolidação tardia do legado, alteração do texto, flags ou imagens. Os 12 testes permanentes incluem ainda `--refazer` explícito, `reg=None`, fluxo visual legítimo com e sem BOM e placeholders com e sem BOM em página originalmente pendente. Não foi necessária repetição de DOCX, cujas fontes e hashes permaneceram iguais.

Hashes corrigidos conferidos após os testes:

| Fonte | SHA-256 |
|---|---|
| extrair.py | `b8efde6ea98e739df6b543eac2c181c1e53adfa6de72907cd2f37aeb1521036a` |
| teste_extracao_markdown_md01.py | `58a5cd6dcdba9c2c6bc06542aa39438b1dcd5b6ebeb344eea581c4773e85b60e` |

O manifesto de fontes anterior ainda identificava os dois hashes reprovados durante esta conferência; foram usados os hashes congelados comunicados pelo executor e confirmados diretamente para o override explícito. Sua atualização/publicação cabe à coordenação. O conjunto permanece com os mesmos seis caminhos diferentes em relação ao gate histórico. Nenhuma fonte fora dos dois arquivos MD02 mudou durante a reauditoria.

**Achado P1 encerrado para a fonte corrigida acima.** Não surgiu outro bloqueante na revisão focal. A preservação comprovada é a dos cenários delimitados, não proteção geral contra qualquer edição/corrupção ou escrita concorrente que ignore a trava. A intermitência UN17 e os cenários ambientais do gate histórico permanecem sem certificação adicional por FV02; não houve novo full. A aprovação global depende do fechamento da coordenação e do gate final programado após cessar a concorrência operacional.
