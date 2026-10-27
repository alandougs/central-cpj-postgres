# MD02 — proteção de Markdown na retomada

27/10/2026. Manutenção local solicitada pelo coordenador; código e fixtures fictícias, sem leitura ou alteração de autos, casos, bancos, configurações ou assinaturas operacionais. Reserva MD02: Codex-MD02. PRD e integração geral permanecem com o coordenador.

## Reprodução e causa

Um PDF fictício de duas páginas em branco é extraído por `extrair.py --ocr visao`. O checkpoint guarda `[PENDENTE: transcrição visual]`. A segunda página de `transcricao.md` recebe texto fictício posterior, com método `ocr-windows-local` ou `transcricao-visual-llm` e aviso de conferência, sem arquivo em `transcricoes_visuais`.

Rodar novamente o mesmo comando, sem `--refazer`, com o mesmo PDF, SHA-256 e parâmetros, antes da correção retornou sucesso e substituiu o texto local pelo placeholder. Foram quatro falhas RED: dois métodos no Markdown × estado consolidado/legado. No legado, a consolidação também era gravada antes da substituição. O método indicado no Markdown não era consultado; a ausência de `ocr-windows-local` em `METODOS` não precisava ser alterada para corrigir o cenário comprovado.

A causa é a reconstrução final do Markdown exclusivamente a partir dos registros usados pelo extrator. Um checkpoint estruturalmente válido pode estar desatualizado em relação ao texto documental local. A correção não transforma esse texto em transcrição validada nem presume fidelidade, qualidade ou completude.

## Alteração mínima

`extrair.py` recebe pré-checagem sob a trava de extração, após validar a assinatura e antes de gravar qualquer checkpoint ou consolidar legado. Na retomada válida sem `--refazer`, se a página do Markdown contém texto diferente da pendência, mas o checkpoint ainda contém exatamente essa pendência, o script recusa com código não zero, páginas afetadas e orientação para conferir o original/reconciliar pelo fluxo visual existente. Markdown, estado consolidado/legado, imagens, flags e PDF permanecem byte a byte intactos.

Se há transcrição visual preenchida em `transcricoes_visuais/pNNNN.md`, o fluxo de incorporação existente prossegue. Um leitor comum ao preflight e à incorporação lê UTF-8 com ou sem BOM; o BOM de codificação não vira texto documental. Arquivo visual vazio ou contendo apenas a própria pendência não libera a substituição nem conclui uma página originalmente pendente: segue a retomada/extração normal, preservando método e flag de pendência quando aplicáveis. Texto de um único caractere no Markdown também é protegido: não há limiar de qualidade. Registros inválidos continuam sendo reprocessados normalmente. `--refazer` explícito mantém o contrato de substituição.

Escopo da proteção: formato de páginas gerado pelo extrator, assinatura de checkpoint válida e divergência específica de placeholder. Não é proteção geral contra toda edição de Markdown, PDF/parâmetros diferentes, corrupção arbitrária ou alterações concorrentes por programas que não respeitem a trava. Não migra casos, adiciona métodos, copia texto para caches, remove flags/imagens nem cria backups por página. `estado_extracao.py` não foi editado.

## TDD e verificação

As regressões foram incorporadas à suíte MD01 já incluída no runner integral. Os quatro cenários principais falharam antes da implementação pela perda observável dos bytes do Markdown. Um RED adicional demonstrou que arquivo visual contendo somente o placeholder não pode liberar a perda. Outro RED identificou `reg=None` na pré-checagem; o tratamento mínimo preservou a recuperação normal de checkpoint inválido.

Comando MD01: `.venv/Scripts/python.exe -B -X utf8 plugin/investigacao-cpj/app/testes/teste_extracao_markdown_md01.py`: **12/12**, zero falhas e zero skips. Inclui retomada normal, quatro combinações de recusa, preservação de todos os arquivos da extração/PDF na recusa, transcrição visual legítima com/sem BOM, visual vazio/pendente com/sem BOM, página originalmente pendente, substituição explícita e checkpoint inválido.

Complemento após auditoria FV02: a fonte anterior permitia o bypass por TV contendo somente o placeholder em UTF-8 com BOM. A leitura em UTF-8 preservava `U+FEFF`, e `strip()` não o removia. RED exato confirmou retorno zero e perda do texto local. Três outras falhas RED demonstraram o BOM propagado para texto legítimo e a conclusão indevida de página originalmente pendente por placeholder com/sem BOM. A tarefa foi reaberta antes da alteração. O leitor único agora normaliza a codificação e compartilha a mesma validação nas duas fronteiras, sem ocultar a falha apenas na guarda. A fonte anterior foi substituída e não deve ser usada para publicação; a nova fonte foi enviada ao auditor para reauditoria pontual.

Todos os testes usam TEMP, runtime `.venv`, `-B` e `PYTHONDONTWRITEBYTECODE=1`. As execuções finais de OCR usam o Tesseract portátil do projeto, com `CPJ_TESSERACT`, `TESSDATA_PREFIX`, `CPJ_EN01_ENGINE=same` e PATH local. Nenhuma API/modelo externo foi chamado. Resultados finais pelo entrypoint de cada script:

| Suíte | Resultado |
|---|---|
| `teste_extracao_markdown_md01.py` | 12/12; 7,867 s |
| `teste_transcricao_visual_px05.py` | 11/11; 4,391 s |
| `teste_interrupcao_real_un17.py` | 3/3; 8,161 s |
| `teste_limpeza_sz02.py` | 9/9; 0,704 s |
| `teste_extracao_codex.py` | 1/1; 1,425 s |
| `teste_ocr_checkpoint_claude.py` | 22 verificações; TUDO OK, OCR português real |

Nenhum skip nas execuções finais. PX05 emite avisos já existentes do PDFium (`get_text_range`) e de pipes sem fechamento em `comum.py`; não ocultados nem alterados nesta manutenção.

Uma tentativa anterior de UN17 durante a execução de outros scripts TEMP ficou 2/3: a janela para encerrar o servidor não foi observada em `test_morte_do_processo_durante_o_processamento_e_retomada`, asserção `interrompido=False`, após 63,363 s. O reteste isolado, com as mesmas fontes e ambiente completo, passou 3/3 em 8,104 s; não foi demonstrada causa dessa intermitência, nem sua eliminação. Antes disso, UN17 também havia passado 3/3 em 8,082 s. A primeira tentativa de carregar PX05 por nomes de pacote via `unittest` falhou por import relativo ao diretório de testes; usar seu entrypoint executou os onze testes. A primeira invocação de L05 não encontrou `por` sem o PATH portátil e não foi contada como aprovação; a rodada com ambiente completo realizou as 22 verificações. Nenhuma dessas ocorrências motivou alteração fora da reserva.

O gate integral fica com o coordenador; não foi executado full concorrente nesta tarefa.

## Congelamento para integração

Delta MD02 em relação ao índice de integração: 45 linhas adicionadas/duas removidas em `extrair.py`, 110 linhas adicionadas em MD01. AST dos dois arquivos e `git diff --check` aprovados; Git informa apenas a normalização futura de LF para CRLF no teste. Verificação Git feita com `-c safe.directory` por invocação, sem alterar configuração global.

SHA-256 das fontes congeladas:

| Arquivo | SHA-256 |
|---|---|
| `plugin/investigacao-cpj/skills/pdf-autos-policiais/scripts/extrair.py` | `B8EFDE6EA98E739DF6B543EAC2C181C1E53ADFA6DE72907CD2F37AEB1521036A` |
| `plugin/investigacao-cpj/app/testes/teste_extracao_markdown_md01.py` | `58A5CD6DCDBA9C2C6BC06542AA39438B1DCD5B6EBEB344EEA581C4773E85B60E` |
| `plugin/investigacao-cpj/skills/pdf-autos-policiais/scripts/estado_extracao.py` — preservado | `13D237ADE9D8A8EDD1802649E5A366CAC119F431041AC5AB44C546D45AECCCD3` |

Risco residual: divergências detectadas exigem conferência e reconciliação local; texto existente não comprova correção dos dados. A recusa é intencionalmente conservadora e pode interromper a retomada de um documento divergente até essa conferência. Sem publicação, instalação/migração, cleanup ou reprocessamento operacional nesta tarefa.
