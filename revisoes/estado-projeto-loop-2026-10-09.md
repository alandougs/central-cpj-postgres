# Projeto CPJ — diagnóstico e loop de conclusão

Pedido do operador em 09/10/2026: conhecer o projeto, verificar sincronização GitHub/PostgreSQL, listar pendências e executá-las com persistência. Diagnóstico sem acesso a autos, contas ou credenciais reais. Este registro documenta a conclusão da fila local autorizada e seus limites; não certifica dados reais, uso oficial ou sincronização remota.

## Estado consolidado em 10/10/2026

Decisão vigente: SQLite na operação local; JSON fonte do caso, índices e fila SQLite. PostgreSQL permanece congelado. GitHub reconfirmado nesta consolidação: core remoto a40a2d81235361e2940d0fddb6f1f3e6ca0d7f36, acervo main b28610c1a619cd6b756f422e2cb30b11788df50a. O acervo local e2c563d tem 31 commits remotos ausentes; origin/main local está desatualizada. Alterações deste loop estão sem commit/push. Não há sincronização completa nem certificação de banco operacional real.

ENV02, ENV03, TS04, TS05 e AI03 concluídas. Verificação independente: seis testes de inicializadores em 27,09 s e pip check; oito testes da descoberta Claude em 0,107 s; 19 testes de identidade bancária em 1,631 s e quatro DOCX em 13,442 s; 12 testes de arquivos ausentes em 1,115 s e oito RV14 em 1,014 s; 13 testes de catálogo em 0,220 s, CF01 e cinco de consentimento. Regressões rápidas finais dos executores aprovadas. Chrome: 12 cenários do catálogo, claro/escuro, escolhas manuais e campo limpo preservados, erros tratados; integrador conferiu imagens e JSON finais. Sem consulta a API real ou chave de produção.

Após as mudanças, a integração HTTP completa retornou zero: **128,66 s de teste, 157,80 s de harness**, com permissões, OCR, minuta/DOCX, FINAL sem forçar, baixa, pesquisa, exportação/importação e auditoria. Evidência: `C:/Users/alan_/AppData/Local/Temp/cpj-http-final-20261010-l0ubkw_0/resultado.json` e `http.log`. Workspace, perfil, APPDATA e configuração Claude fictícios isolados. Esse teste não substitui P01 com inferência; as duas rodadas 71/71 da AG04 pertencem ao snapshot anterior explicitamente documentado.

Plugin final **0.3.3 instalado e habilitado**, CLI e validações oficiais aprovadas. Conferência independente: 76 arquivos do bundle coincidem por SHA-256 com fonte/staging/cache; marketplace completa os 77 arquivos genéricos preparados. CL06 corrigiu a descrição YAML dobrada na exportação portátil, com dois testes vermelhos e quatro verdes; integrador repetiu os quatro em 3,498 s e conferiu descrição real e whitespace. Onze procedimentos regenerados e 12 adaptadores sem alterações; bundle/cache/versionamento permaneceram intactos.

OAuth autorizado expressamente pelo operador em 10/10/2026: página oficial e CLI confirmaram sucesso, `loggedIn: true`, `claude.ai`, Pro. ENV01 encerrada. Primeira tentativa real P01 falhou em 403,85 s: sessão financeira preservou arquivos corretos, mas não atualizados, e o gate bloqueou. Três logs terminais conferidos independentemente somam US$ 2,4557518 equivalentes API, sem comprovar cobrança Pro; zero web search/fetch reportados. Original e tentativa falha preservados.

TS06 concluída: prompt explicita conferir/gravar todas as saídas na execução, sem mudar fatos ou timestamps artificialmente; gate não relaxado. Log/retorno permanecem na etapa erro após reprovação posterior. Três testes independentes em 1,873 s, squad 12/12, rápida 5/5 e plantão sandbox aprovados. CL07 instalou **0.3.2**, conferida por CLI/validação e 76 hashes fonte/staging/cache. Segunda tentativa P01 concluída em novo TEMP, sem copiar produtos/logs/SQLite da anterior: quatro ações, sete sessões, 859,75 s, US$ 5,3127658 equivalentes API e 4.085.381 tokens cumulativos incluindo cache; cobrança Pro não disponível. Auditoria Codex corrigiu duas formulações na v02 e completou três registros obrigatórios ausentes na automação. Treze hashes originais preservados e 48 afirmações v02 sustentadas; DOCX reaberto e fonte preservada. O revisor automático errou a contagem do resumo; limites e intervenções registrados em PILOTO-2026.md. Não houve aprovação humana oficial.

TS07 e TS08 concluídas: defeitos das opções DOCX corrigidos com oito testes focados e sete regressões; contrato dos registros obrigatórios corrigido, incluindo retomadas, com oito testes, squad 12/12, TS06 3/3 e plantão simulado. Integrador repetiu oito testes DOCX em 4,736 s e oito de registros em 13,508 s. CL08 consolidou os patches no plugin 0.3.3, validou instalação e 76 hashes, sem nova inferência. A fila local autorizada está concluída, com CL04/SY01 consolidando estas evidências. GitHub permanece divergente e sem publicação; PostgreSQL congelado por decisão do operador. O incidente anterior do atalho Startup permanece documentado, sem restauração automática ou certificação de boot.

As listas e estados abaixo são históricos e devem ser lidos com suas datas; a fila compartilhada registra o estado corrente.

## Mapa do projeto

A Central CPJ é o aplicativo Flask em `plugin/investigacao-cpj/app/`. O fluxo operacional é recebimento de O.S. e PDF, extração local por página, tabelas e entidades, análise, minuta, revisão e DOCX. Os procedimentos vivem em `commands/`, `agents/` e `skills/` do plugin; `portatil/` e os adaptadores `.agents/skills/cpj-*` distribuem esses procedimentos. `ferramentas/` contém a fila compartilhada, manutenção, diagnóstico e testes.

No código da branch atual, `caso.json` continua como fonte dos casos e SQLite como índice de pesquisa regenerável. O acervo `acervo/repo-ia-alandougs` é outro repositório, dedicado a procedimentos genéricos. Documentação e código PostgreSQL existem em outra linha do Git e no legado; não constituem sincronização automática do banco com a Central.

## Sincronização verificada

| Item | Evidência | Situação |
|---|---|---|
| Core | Remoto `alandougs/central-cpj-postgres`, branch `consolidacao-2026-10-01`; HEAD e SHA remoto `a40a2d8` | Os commits coincidem nessa branch, antes das alterações deste loop |
| Core versus `main` | `git rev-list --left-right --count HEAD...origin/main`: 3/3 | RV17/RV18 do PR #2 estão em `main`, mas não integrados à branch atual |
| Core versus `master` | 11/12 commits exclusivos; `origin/master` em `7e537c4` | Outra linha de desenvolvimento, incluindo migração PostgreSQL |
| Acervo | Branch `main`, HEAD `e2c563d`; remoto `b28610c1a619cd6b756f422e2cb30b11788df50a`, 31 commits à frente; 63 arquivos rastreados alterados e 4 novos | Confirmado pelo conector GitHub; clone local não sincronizado |
| PostgreSQL | Sem importação de `Database` no runtime atual; migração manual separada | Não foi comprovado banco ativo ou dados sincronizados |
| Ambiente | `python` do PATH é alias da Store; `.venv` aponta para Python de outro usuário | Testes usam Python 3.12.14 do runtime Codex com bibliotecas da `.venv` via `PYTHONPATH` |

Os arquivos PostgreSQL/Docker na raiz são não rastreados. O Docker Compose usa `./data`, enquanto a operação atual organiza dados por workspace. O entrypoint não executa a migração para PostgreSQL. `docker`, `psql` e `pg_isready` não foram encontrados no PATH; consultas locais não localizaram listeners PostgreSQL/Central. Isso não determina o estado de infraestrutura externa.

## Fila pendente no início do loop

| ID | Entrega | Condição de execução |
|---|---|---|
| CL02 | Restaurar ou reconciliar etapas da squad com a esteira | Disponível; assumida pelo subagente deste loop |
| CX02 | Contrato e cancelamento da importação | Disponível; assumida pelo integrador deste loop |
| CX03 | Orçamento por pedido: tempo, tokens e custo | Depende de CL02; AG03 está administrativamente concluída, mas seu relatório tem zero bytes |
| AG04 | Duas execuções completas e registro de falhas | Depende de CL02, CX01 e CX02 |
| CL03 | Versão e instalação do plugin | Depende das correções e suíte verde; instalação demanda autorização aplicável |
| CL04 | PRD consolidado | Depende de CL03/AG04; PRD também reservado por DJ01 |
| PX05 | Transcrição visual de páginas reprovadas | Depende de CX01/DJ01 |
| PX06 | Modos Rápido, Inteligente e IA Completa | Depende de PX05 |
| PX07 | Normalização derivada sem alterar dígitos/fontes | Depende de PX05 |
| AI03 | Catálogo e seleção de modelos | Depende de CL04 |
| GC01 | Correções legais e autonomia no PR #17 do acervo | Repositório remoto; autenticação necessária e manter draft |
| GC02 | Sincronização Claude, dependências e hook | Acervo; reconciliar mudanças locais e remoto antes de editar |
| GC03 | Cópias canônicas e validação dos estados | Acervo; mesma condição |
| GC04 | Regressão fictícia de fraude e CI | Acervo; mesma condição |
| GC05 | Validação estrita e detector de sensíveis | Depende dos merges humanos dos PRs #17/#14/#15 |
| P01 | Piloto fictício com IA automática | Reservada por Copilot-1 |
| CX01 | Recuperar workers/checkpoints de OCR | Reservada por Codex-1 |
| DJ01 | Consolidado JSON da extração | Reservada por Codex-DJ01 |

Há **15** tarefas disponíveis/aguardando dependências e **3** reservas anteriores no levantamento inicial. A tarefa SY01 registra este diagnóstico, além da fila preexistente. Reservas e conclusões administrativas não demonstram aprovação dos testes.

## Execução e decisões

CX02: reproduzidas uma falha por mensagem de contrato obsoleta e uma exceção de cancelamento. Um teste assíncrono adicional comprovou que o cancelamento era convertido em `erro` pelo executor. A correção trata `ImportacaoCancelada` na importação, mantém o status cancelado e a limpeza, sem esconder erros de integridade ou indexação. Runner isolado rápido com importação: 5/5 suítes aprovadas em 87,49 s; diagnóstico completo em execução.

GitHub: o conector permitiu leitura do acervo privado, sem autenticar o terminal ou acessar credenciais. PRs #14/#15/#17 estão fechados sem merge, desde 01/10; as condições GC01/GC05 do quadro precisam ser reconciliadas, sem reabrir ou mesclar PR automaticamente. CI de `main` em `b28610c1` aprovado ([run 37989791416](https://github.com/alandougs/repo-ia-alandougs/actions/runs/37989791416)); cobre validação e núcleo financeiro, não o fluxo PDF/DOCX GC04.

AG03 reaberta porque o relatório estava vazio; evidência recuperada por leitura do código. Identificados armazenamento de chaves em claro e gates de consentimento incompletos. Nenhuma configuração real lida ou alterada.

CL02: subagente verifica a esteira e as correções já existentes em `origin/main` antes de implementar a recuperação. Nenhuma API real usada nos testes.

CL02 concluída na fila: restauradas etapas internas com blocos de até 90 páginas, sessões paralelas, consolidação, financeiro, redação, revisão independente e ajuste; checkpoints SQLite e verificação das saídas. Evidência do executor: 11 testes focados aprovados, regressão rápida 5/5 e esteira 6/6. A conferência independente completa está em curso. Colisão de logs API reproduzida foi transferida à CX03; o teste está temporariamente marcado como expectedFailure, explicitamente sem alegar cobertura desse defeito.

TS01: compilação dos 64 arquivos de teste identificou três erros de sintaxe (RV06, Central HTTP e PX01) e um arquivo vazio (`teste_fila_os_padrao_antigravity.py`). Erros de sintaxe corrigidos; a nova compilação não apresentou erros. O teste PX01 também tinha fixture com caminhos, autenticação e tipos de agente incorretos; foi isolado antes de importar o servidor e sua consulta externa de saúde foi simulada. Runner rápido com PX01: 5/5 suítes aprovadas em 98,02 s. RV06 em sandbox: retorno zero e cinco verificações aprovadas. O teste HTTP será avaliado pelo diagnóstico completo. Arquivo vazio continua como lacuna de evidência, sem ser tratado como cobertura.

GC02 e CX03 estão em execução por subagentes, com reserva oficial. GC02 usa testes em acervo fictício e preserva as alterações locais existentes. CX03 integra consumo, limites e logs à orquestração, sem chamar API real.

## Atualização após as decisões do operador

O operador autorizou a transferência das reservas antigas CX01, DJ01 e P01, confirmando o encerramento dos agentes anteriores. Depois da comparação das arquiteturas, decidiu expressamente **seguir com SQLite na operação local atual**. A escolha anterior de retomar PostgreSQL foi substituída. A Central mantém `caso.json` como fonte e SQLite como índice; não há migração PostgreSQL autorizada em execução.

O diagnóstico completo inicial terminou em **54/64 suítes**, durante alterações concorrentes. Não é homologação final. As dez falhas foram distribuídas entre CX01, TS01, TS02 e dependências QuickJS de GF02/UX01; verificações focadas posteriores passaram. AG04 ainda exige duas execuções completas sobre uma entrega estabilizada.

| Entrega registrada no loop | Evidência e limite |
|---|---|
| CL02 e CX03 | 12 testes da squad sem expectedFailure; 19 testes de orçamento. Limites persistidos por grupo/pedido; uma chamada já enviada pode exceder o teto antes da medição da resposta. Não houve API real. |
| CX01 | Workers e checkpoints restaurados, cache visual invalidado por hash; regressão rápida 4/4 e testes OCR/extração/F12. Benchmark fictício de quatro páginas: 3,544 s com um worker, 3,167 s com dois; texto igual. |
| CX02 e DJ01 | Cancelamento assíncrono preservado; consolidado JSON existente verificado em sandbox. |
| TS01 e TS02 | Sintaxe de três testes corrigida, fixtures isoladas e método PDF inexistente substituído por `get_pos`; verificações focadas e rápidas aprovadas. Central HTTP isolada terminou com retorno zero em 105,25 s. |
| AG03 e AG05 | Relatórios/testes vazios recuperados; AG05 tem cinco testes CLI fictícios, duas falhas reproduzidas antes e cinco aprovadas depois; rápida 4/4 em 44,02 s. |
| GC02 e GI01 | Sincronização com manifesto e preservação de conflitos, ferramentas por autonomia, dependências e hook versionados; erro DOCX corrigido e índices gerados. Verificação independente do acervo: 31 testes aprovados e validação de 170 itens sem erros/avisos. Nenhuma sincronização dos agentes reais. |

SE01 concluída na fila; conferência independente aprovou sete testes de consentimento e cinco da interface (QuickJS). O servidor identifica o usuário/data do aceite e persiste os destinos nas quatro etapas EC01; pedidos históricos sem aceite válido são bloqueados antes de prompt, HTTP ou CLI. PX05 está em execução, incluindo adaptador PNG e endpoint com escopo de consentimento próprio.

A integração HTTP da Central foi repetida depois de SE01: retorno zero em **93,30 s**, com workspace fictício, incluindo processamento, permissões, pesquisa, minuta/DOCX, FINAL/baixa, exportação/importação e gestão de responsáveis. A nova conferência independente de AG05 aprovou cinco testes de nomes da O.S. e a suíte preexistente de reservas e reaproveitamento. Estas verificações não substituem as duas execuções completas AG04 após todas as alterações.

**Falha de isolamento encontrada após o diagnóstico inicial:** `teste_fulltime.py` isolava o workspace, mas herdava APPDATA real ao executar instalar/remover o atalho de boot; o runner também não sobrescrevia APPDATA. Esse teste participou do diagnóstico inicial. Portanto a alegação geral de que nada fora dos temporários foi alterado nos testes **não vale para esse atalho**: o teste podia substituir e apagar `Central-CPJ-24-7.lnk` da Startup do usuário. O caminho específico foi consultado depois e não existe; não há evidência do conteúdo ou presença anterior, nem base para restauração automática. O operador foi informado. AG02 reaberta, relatório antes vazio, para isolar APPDATA e provar preservação de uma sentinela herdada fictícia; novas execuções FullTime suspensas até a correção. Não instalar boot real. Casos, originais e credenciais não foram usados nesse teste.

Revisão de PX05 também identificou que os endpoints podiam considerar destinos informados como aceite, sem booleano positivo. O executor recebeu escopo para exigir `aceito is True` nos dois endpoints e atualizar regressões; SE01 não deve ser considerada cobertura desse caso antes da correção.

AG02: reprodução feita pelo executor com APPDATA herdado **inteiramente fictício** confirmou remoção de uma sentinela válida pelo teste antigo. Dois testes falharam antes da correção e passaram depois (8,704 s): APPDATA agora aponta para Startup sob o próprio temporário, e APPDATA/CPJ_WORKSPACE são restaurados na saída. Snapshot anterior do teste salvo em TEMP; daemon do produto não alterado. Ensaio completo ainda em execução no momento deste registro; isso não comprova boot real instalado.

Atualização AG02: tarefa encerrada após rápida + FullTime **5/5 suítes em 94,58 s**, incluindo ciclo, watchdog e Startup fictícia. O integrador revisou o diff e repetiu a nova regressão de isolamento: dois testes aprovados em sandbox (4,53 s). Relatório recuperado em `revisoes/fulltime-verificacao-2026-10-02.md`; boot operacional não certificado.

PX05 e PX07 encerradas na fila. Conferência independente aprovou nove testes visuais em 13,44 s e quatro de normalização em 1,38 s. PX05 exige aceite booleano positivo, envia somente PNG com instrução estática, preserva transcrição humana existente e consolida derivados por replay; PX07 escreve somente arquivos derivados, mantendo bytes/hash da fonte e registrando alterações por página/linha. PX06 ainda está em execução. Uma checagem de integração HTTP após seu novo backend, antes da UI final, passou em **90,53 s**; Inteligente sem API/permissão IA manteve processamento local com limitação explícita.

A revisão intermediária também reproduziu diferença entre o ambiente OCR do subprocesso e o pai na validação visual; PX06 está corrigindo a consulta para usar o ambiente efetivo do replay, sem alterar PATH global nem rodar OCR para a checagem. Essa entrega deve integrar a homologação final.

GC03 foi implementada e liberada para decisão humana: oito testes próprios e 39 da suíte do acervo aprovados. O validador agora detecta **um erro documental real**: `governanca/autoria.md` declara `revisado`, sem registro `VALIDACAO.md`. O operador foi consultado para confirmar a revisão ou corrigir o estado; nenhum parecer foi inventado. GC04 prepara regressão PDF/JSON/DOCX e CI, mas a parte `--modo entrega` depende de GC05. Foi solicitada reconciliação da condição de GC05 porque os três PRs previstos estão fechados sem merge.

GC04 preparada nos quatro arquivos reservados: quatro testes locais aprovados em **85,03 s**. A fixture produziu 31 páginas Markdown, incluindo OCR português nas seis páginas digitalizadas; outras páginas nativas curtas também recebem OCR pelo critério existente, sem reduzir limiares para fabricar contagem. Totais de 5.500/700/4.800 e mutação financeira foram verificados; DOCX reaberto com três títulos e três totais. Workflow contém Actions fixadas por SHA e oito dependências diretas fixas. O CLI completo retorna **1**, explicitamente porque `--modo entrega` ainda não existe; não usa diagnóstico como substituto. CI remoto não disparado. Cache de bytecode isolado no TEMP para evitar `bad marshal` das bibliotecas antigas, sem alterar vendor.

GC01 preparada localmente: reserva jurisdicional inserida na recuperação de ativos, conferência oficial da cessão de conta e das vigências do MED/Pix datada em 09/10/2026, ferramentas de inteligência limitadas a Read/Glob/Grep sem alterar sua autonomia N2. Dois testes próprios e 12 da sincronização aprovados; índices regenerados pelos scripts. Foi liberada, sem concluir: a validação geral permanece com o erro de autoria acima; CI remoto não foi executado neste loop.

P01 preparada e liberada: PDF fictício de quatro páginas extraído no temporário, com três páginas nativas e uma por OCR, sem pendências, retorno zero em 5,34 s. Claude CLI não localizado; inferência, DOCX, custo, tokens e retrabalho não medidos. O operador foi consultado sobre o caminho do executável. Detalhes em `PILOTO-2026.md`.

A lista inicial acima é histórica; os estados atuais ficam em `TAREFAS-COMPARTILHADAS.md`. A fila ainda contém PX06, GC01/GC03–GC05, AG04, CL03/CL04, AI03 e P01; tarefas parcialmente preparadas continuam abertas até satisfazerem suas condições.

O acervo trabalha agora na branch local `codex/loop-gc02-20261009`, preservando as alterações anteriores. O remoto continua separado por 31 commits no diagnóstico; não houve pull, reset, commit ou push neste loop. O executável Claude não foi encontrado no PATH nem nos locais previstos pelo atualizador; instalação do plugin e piloto automático real ainda dependem de ambiente disponível. Originais, casos reais, credenciais, contas e publicação permanecem intocados. A exceção de alteração pelo teste antigo de Startup está registrada acima.

GC03 e GC01 concluídas localmente: a marcação de autoria sem registro foi corrigida para `rascunho`, reversivelmente, sem declarar aprovação humana. Índices regenerados pelos scripts oficiais. Suíte geral do acervo: **45 testes e 11 subtestes aprovados em 52,41 s**, com OCR português local; validador **170 itens, 35 planejados, zero erros e avisos**, cópias `--check` e whitespace aprovados. Uma execução anterior sem PATH/TESSDATA encontrou zero páginas OCR; repetir com o ambiente correto resolveu. Outra validação sem `safe.directory` caiu na varredura de bibliotecas `.venv` e reportou 127 ocorrências de vendor; a execução com Git seguro validou o conjunto versionado sem erros. Nenhuma dependência vendor foi alterada para ocultar essas ocorrências. GC04 continua parcial até GC05; não confundir seus testes auxiliares verdes com a CLI de entrega completa.

PX06 concluída e arquivos liberados após rápida **5/5 em 66,99 s**, com 18 testes do formulário e nove dos modos. Rápido/Inteligente/IA Completa presentes no cadastro e reprocessamento; worker fictício comprova 0/1/2 chamadas, metadados e hashes. Nove testes PX05 atualizados aprovados em 12,52 s cobrem ambiente OCR efetivo e alteração dos checkpoints durante a resposta. AG04 iniciou as duas rodadas completas com APPDATA adicional fictício no harness TEMP, mesmo após a correção específica AG02; código do produto estabilizado. Conferência visual independente em andamento.

SHAs remotos reconfirmados pelo conector durante a verificação final: acervo `main` permanece `b28610c1a619cd6b756f422e2cb30b11788df50a`; core `consolidacao-2026-10-01` permanece `a40a2d81235361e2940d0fddb6f1f3e6ca0d7f36`. Entregas locais deste loop continuam sem commit/push, portanto não estão sincronizadas com GitHub.

Novas decisões expressas do operador: aprovou a revisão humana de autoria, autorizou GC05 LOCAL substituindo os merges dos três PRs fechados e autorizou instalar Claude Code. GC06 registrou a aprovação em `governanca/VALIDACAO.md`, versão 1.0.0, restaurou `revisado` e gerou índices; validação 170 itens sem erros/avisos. Claude Code oficial stable 2.1.287 instalado sob `.local/bin`, versão comprovada; login iniciado no navegador. A conta está logada na página oficial, mas falta a autorização de acesso ao CLI; solicitado aceite específico, sem ler ou solicitar senha/token. ENV01/CL03/P01 ainda não são conclusão do piloto.

A rodada de integração terminou em **70/71 suítes, 544,52 s** de execução dos testes (803,73 s com overhead), única falha F03. Reprodução isolada confirmou HTTP409 do gate por sete campos ausentes na fixture. TS03 ajustou somente fonte fictícia complementar e teste, preservando produto/gate. Conferência independente: F03 **retorno zero, 26,78 s**, oito etapas reais Edge incluindo FINAL/baixa/painel, conferência sem forçar. Logs vermelhos e evidências fictícias preservados em TEMP. As duas rodadas finais AG04 foram reiniciadas após essa estabilização. GC04/GC05 prosseguem no acervo, que não integra o clone do runner core.

GC04 e GC05 encerradas: suíte final do acervo **61 testes e 33 subtestes aprovados em 130,64 s**; modo padrão e estrito aprovados. Integrador repetiu `validar.py --estrito`: **170 itens, 35 planejados, zero erros e avisos**. Repetiu também a CLI completa GC04, retorno zero: 31 páginas extraídas, seis digitalizadas verificadas, 13 páginas com OCR, desembolso 5.500/devolução 700/líquido 4.800, cinco cálculos demonstrados, 105 referências confirmadas, mutações de valor e folha com retorno 1 e DOCX reaberto. PDF e caso JSON do gabarito intactos; citações, demonstrações de cálculo e conferência corrigidas com as fontes fictícias existentes. Detector protege texto e propriedades DOCX/PDF, inclusive XMP; exceção técnica de dois padrões do gerador fictício vinculada a arquivo/hash/categorias exatos, não aprovação humana inventada. PDFs só imagem exigem OCR prévio; não se declara prova de anonimização. Gitleaks/Actions preparados no CI com SHA fixo, sem comentários/artefatos contendo valores, CI remoto não executado.

AG04: primeira rodada final estabilizada **71/71 suítes aprovadas, 560,67 s de testes e 833,09 s de harness**, nenhuma falha. Segunda rodada em execução. CL03 prepara candidato somente em TEMP até as duas rodadas verdes; P01 prepara novo caso fictício/harness até OAuth e instalação do plugin. Claude Code foi registrado no PATH do usuário como parte da instalação autorizada, com entradas anteriores preservadas e snapshot TEMP para reversão; nenhuma mudança no Python global ou nos provedores da Central.

AG04 concluída em 10/10: segunda rodada **71/71, retorno zero, 841,92 s de testes e 1.305,95 s de harness**, sem falhas ou repetição para obter sucesso. Fontes estabilizadas durante ambas; mudanças posteriores terão verificações próprias. CL03 liberada para aplicação e instalação autorizadas. Diagnóstico adicional de entrada confirmou `python` como alias Store sem interpretador e `.venv/Scripts/python.exe` apontando para Python ausente de outro usuário; ENV02 aberta para reparar ambiente virtual e inicializadores locais, sem instalação global nem boot real. Auditoria CL04 reproduziu em fixture contas iguais de bancos distintos colapsando no fluxograma (TS04) e conclusão da fila apenas avisando arquivo reservado ausente (TS05); registradas para correção mínima e testes antes de declarar projeto concluído. O publicador legado não foi executado, pois pode alterar o acervo mesmo sem envio.

Conferência independente 10/10: `claude plugin list --json` confirmou `investigacao-cpj@cpj-local`, versão **0.3.0**, habilitado, escopo de usuário, cache local sob `.claude/plugins/cache`; validação estrita do pacote retornou sucesso sem erros/avisos. A CLI recusou o marketplace da unidade D: com `network_location`, embora a unidade seja local/exFAT; alternativa aceita foi staging somente de código genérico em `C:/Users/alan_/AppData/Local/CPJ/plugin`, sem alterar confiança nem copiar fixtures/casos/configurações/chaves. CL03 continua reservada para provar o atualizador usando o ambiente Python reparado. O cache instalado é esse snapshot; alterações posteriores do plugin exigirão atualização confirmada. GitHub reconfirmado por compare remoto: e2c563d → b28610c1, **31 commits adiante, zero no sentido inverso**. `origin/main` local ainda aponta e2c563d e não prova sincronização.

CL03 e CL04 encerradas: atualizador padrão comprovado pelo executor com venv válida e PATH sem Python, sem função temporária/PYTHONPATH; PRD consolidado com evidências e pendências atuais. ENV02: integrador confirmou Python local 3.12.14, cinco imports e **cinco testes de inicializadores em 17,62 s**, sem caso/boot real. TS05 encerrada: revisão independente do diff e **12 testes RV20 + oito RV14 aprovados**. A primeira chamada RV14 sem `PYTHONUTF8=1` apresentou erro de decodificação na fixture CLI; repetida com o ambiente UTF-8 requerido pelo runner, passou em 1,01 s, sem mudar o teste para ocultar a falha. Ausentes agora impedem conclusão antes de alterar o quadro; exceção precisa motivo explícito de 15+ caracteres e registra todas as lacunas. AI03 está liberada após CL04; P01 permanece aguardando OAuth específico.

ENV02 encerrada após ampliar a prova para comandos filhos de processo não Python: os cinco inicializadores passam `.venv/Scripts` no PATH somente do processo, sem alterar PATH global. Integrador repetiu a versão final: **seis testes aprovados em 27,09 s**, `pip check` sem dependências quebradas e pip 25.0.1 confirmado. Executor repetiu rápida final **5/5 em 125,83 s**, preservou por SHA256 os 1.575 arquivos não-pip e registrou snapshot; pip inconsistente foi reconstruído offline pelo wheel embutido. Integrador também reproduziu TS04 antes do patch com duas transações fictícias: bancos diferentes e mesma agência/conta resultaram em um nó de 200; o correto são dois nós de 100. TS04 está assumida para corrigir tanto colunas quanto encadeamento global. CL05 registra a necessidade de atualizar o cache após TS04/AI03; versão 0.3.0 instalada não será confundida com código posterior.
