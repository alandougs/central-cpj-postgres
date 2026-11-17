# Auditoria independente — recuperação da reserva de extração

Data: 27/10/2026. Tarefa RS01, responsável Codex-RS01. Candidato autorizado: `F:/CPJ-BACKUPS/sync-github-20261027-023944/candidato`. Produto somente lido; correção pertence ao executor IV01. Fila registrada no workspace original. Aplicadas as instruções AGENTS, PRD, MEMORIA, ESPINHA-DORSAL, plano canônico e skills scope-guard, no-gold-plating, systematic-debugging e verification-before-completion.

## Parecer

**Aprovado no escopo da recuperação antecipada local, incluindo o complemento PX05.** Após a primeira aprovação focada, o gate integrado encontrou uma regressão: a trava mantida por `atexit` continuava aberta após retorno de `runpy`, impedindo limpeza no Windows. A versão corrigida delimita a trava ao corpo da extração, liberando-a em sucesso e exceção. A auditoria repetiu os testes afetados: UN14 **22/22**, UN17 **3/3**, PX05 **11/11**, sem skips. A fixture adicional de seis processos permanece válida para a coordenação, cujo código não mudou neste complemento. O gate integrado final continua com o coordenador.

## Causa e fronteiras verificadas

No código anterior à correção, `_processar_coordenado` reserva a etapa por 12 horas usando `extrator-PID-thread`. `reconciliar_inicializacao` e `registrar_extracao` reconhecem abandono apenas quando falta reserva válida no tempo. Após morte real do servidor, `processamento.json` pode ser reenfileirado, mas `reservar` recusa a etapa SQLite ainda `em_execucao`. A transação `BEGIN IMMEDIATE` protege a aquisição, porém não informa a vida do executor.

A recuperação antecipada deve restringir-se a extração comprovadamente local, na mesma máquina, com identidade do processo que não confunda reutilização de PID. Processo vivo, acesso negado, consulta incerta, host diferente e dono desconhecido/legado não são prova de morte. Ausência de thread em outro processo também não prova término. Cancelamento, IDs históricos, checkpoints e intenções externas devem permanecer preservados.

## Achados comunicados ao executor e coordenador

1. **Extração também pode executar API.** `comum.processar` chama `transcricao_visual` em PDF com modo inteligente/ia_completa e consentimento, criando tarefa separada. Filtrar apenas `origem=processamento` e `etapa=extracao` não impede repetir resultado externo incerto. **Tratamento conferido:** somente `modo=rapido` recebe identidade recuperável antecipadamente. Outros modos não entram no novo mecanismo. A guarda de intenção externa continua levando a `aguardando_operador`, sem nova tentativa.
2. **Morte do servidor não comprova morte do filho escritor.** O filho de `comum.rodar` pode continuar escrevendo depois da morte do pai. A nova reserva SQLite, isoladamente, não bloqueia esse processo antigo. **Tratamento conferido:** `extrair.py` adquire trava exclusiva de um byte antes de ler/reusar/gravar checkpoints e a mantém durante todo o corpo da extração, inclusive quando o pai morre. A saída normal ou excepcional do bloco `with` libera a trava mesmo quando executado por `runpy`, sem depender do encerramento do chamador. O arquivo não é removido; usa `msvcrt` no Windows e `flock` em POSIX. Validação de reparse precede e segue a abertura. O teste real de filho órfão confirmou que outro extrator não escreve enquanto a trava está ocupada e prossegue após liberação.
3. **Retomada pode alterar o checkpoint de outro servidor vivo.** O fluxo anterior chamava `enfileirar`, que substituía o item por `na_fila`. Conferir o estado antes dessa chamada ainda deixava uma corrida entre dois servidores. **Tratamento conferido:** `retomar_pendentes` agora reutiliza item e etapa persistidos em `fila.put`, sem regravar o checkpoint nem criar outra solicitação. A reserva atômica é conferida pelo trabalhador antes de executar. O teste da leitura obsoleta preservou `processando`, progresso 47 e data original, sem segundo despacho.

A leitura final confirmou host/PID/nascimento, classificação conservadora de identidade incerta e recuperação dentro de `BEGIN IMMEDIATE`. Ausência de thread não é usada como prova de morte. PID reutilizado com nascimento diferente identifica o término da instância anterior. Estados terminais/cancelados não entram na seleção de recuperação antecipada.

## Evidência sintética independente inicial

Executado pelo runtime `F:/CPJ - TRABALHO/.venv/Scripts/python.exe -X utf8 -`, via script inline, sem arquivos de teste persistentes. Em diretório `TEMP` exclusivo, um processo pai iniciou um filho escritor com stdout em pipe; só o pai foi encerrado. Após a morte do pai, a quantidade de linhas do arquivo do filho passou de **4 para 12** em 0,4 segundo. O filho encerrou naturalmente após 30 escritas. Resultado do teste: código **0**, `parent_exit=1`, `child_continued=True`. Nenhum serviço existente, configuração, banco operacional, auto ou API foi acessado.

## Validação final independente

Runtime: Python **3.12.14**, `F:/CPJ - TRABALHO/.venv/Scripts/python.exe`. Comandos executados no candidato, com `CPJ_TESSERACT` e `CPJ_EN01_ENGINE` apontando para `F:/CPJ - TRABALHO/ferramentas/tesseract/tesseract.exe` e `TESSDATA_PREFIX` para `F:/CPJ - TRABALHO/ferramentas/tessdata`. Variáveis restritas ao processo de teste.

| Verificação | Evidência desta auditoria |
|---|---|
| `-X utf8 -m unittest discover -s plugin/investigacao-cpj/app/testes -p teste_fluxo_execucao_un14.py` | 22 testes, 4,992 s, código 0, sem skips; repetido após complemento PX05 |
| `-X utf8 -m unittest discover -s plugin/investigacao-cpj/app/testes -p teste_interrupcao_real_un17.py -v` | 3 testes, 9,443 s, código 0, sem skips; repetido após complemento PX05 |
| `-X utf8 -m unittest discover -s plugin/investigacao-cpj/app/testes -p teste_transcricao_visual_px05.py -v` | 11 testes, 5,355 s, código 0, sem skips |
| Fixture inline de concorrência, criada pelo auditor | Seis processos reais liberados pelo mesmo marcador, uma recuperação, uma reserva vencedora, duas tentativas ligadas pelo ID anterior; código 0 |
| `git diff --check` dos arquivos do patch e do complemento | Código 0 |

UN14 cobriu dono vivo, legado, outro host, identidade incerta, PID reutilizado, intenção externa, outra etapa, cancelamento, checkpoint vivo e corrida de retomada. UN17 passou pelo término forçado do servidor depois de checkpoint parcial real, retomada com reaproveitamento, oito páginas com OCR português, original inalterado, ausência de caso duplicado e de execução órfã; também verificou filho órfão com trava e rejeição de junction sem alterar o destino.

No complemento, PX05 confirmou que outro extrator adquire a trava após sucesso e após falha controlada de gravação, enquanto o chamador `runpy` permanece vivo. A fixture UN17 foi ajustada para manter o escritor dentro de `estado.gravar`, durante a extração real; a proteção não depende de manter uma trava depois que a extração já terminou. A leitura confirmou que o bloco engloba a espera pelo `ThreadPoolExecutor`, o fechamento do PDF e a última publicação de estado. PX05 emitiu `UserWarning` do PDFium e `ResourceWarning` dos pipes de `comum.rodar`; os testes terminaram com código 0. Esse último aviso preexistente foi comunicado, sem correção adicional fora do escopo.

Hashes SHA-256 do código/testes revisados (não são hashes de autos):

| Arquivo | SHA-256 |
|---|---|
| `app/fluxo_execucao.py` | `6dc7fbdc9bda5894dc7661b996353a0bb6ff79b5842030d90e67a35b0935094e` |
| `app/rotas/comum.py` | `bf9e81318884b9d09a34a88f2c5df0959de60cd468e44c344037f499630b1adb` |
| `skills/pdf-autos-policiais/scripts/extrair.py` | `a48b71add61f7b4f388decffeef949ee1a398071b0c130b6d1524ac1d0661077` |
| `app/testes/teste_fluxo_execucao_un14.py` | `587c8c35b4897f72583b8ba4c18cc4e73df5b03e57bbdcad0599a6a64b362e66` |
| `app/testes/teste_interrupcao_real_un17.py` | `2862a7ba35a62611125ff686ed19bf72de64be53b8261b8433d8bd19562a79cf` |
| `app/testes/teste_transcricao_visual_px05.py` | `37872bff154a5d5a9acbbb5f847821cb1ca0653a7ae2f448c7e5efed30b568fa` |

Prefixo dos caminhos: `plugin/investigacao-cpj/`.

## Limites e pendências de integração

- A recuperação antecipada nova vale para reservas produzidas pelo modo rápido com identidade verificável. Donos legados, outro host e modos com possível API não recebem essa liberação antecipada. Não se afirma que a correção elimina reservas históricas presas sem identificação.
- A expiração temporal anterior continua sendo uma rota distinta, inclusive em `registrar_extracao`; não foi redesenhada nesta correção e não deve ser descrita como prova de morte de processo vivo.
- A espera padrão da trava é de 30 segundos, configurável entre 0 e 300. Se o escritor não terminar no prazo, a nova execução falha de modo visível sem remover a trava nem sobrescrever checkpoints. Isso preserva dados, mas não promete retomada automática ilimitada.
- A execução de testes foi Windows. O ramo `flock` POSIX recebeu leitura de código, sem execução nesta auditoria.
- Não houve teste de API paga, modificação de conteúdo de caso, banco operacional, configuração ou serviço existente. A aprovação não abrange reexecução de chamadas externas nem autorização de instalação/publicação. Suíte completa final permanece com o coordenador.

Complemento solicitado pelo coordenador: leitura de `web_seguro.drenar_corpo_de_erro` e sua chamada em `after_request` (IV04). O trecho restringe a drenagem a erro HTTP com JSON e tamanho conhecido até 65.536 bytes, sem interpretar o corpo, mudar autorização ou substituir a resposta quando a leitura falha. Não foi encontrado risco concreto adicional ao tempo de leitura HTTP já existente; os testes IV04 não foram executados por este auditor e não integram os 36 testes acima.
