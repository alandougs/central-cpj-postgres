# Sincronização GitHub/local e integridade — 27/10/2026

## Pedido e autorização

O operador pediu atualizar sua pasta com o GitHub e escolheu expressamente combinar as duas versões, preservando correções locais. Ampliou o pedido para extração dos novos PDFs somente em Markdown, limpeza dos derivados desnecessários, memória central e coordenação de agentes, auditor independente e processamento posterior das pendências, uma O.S. por vez. Autorizou executores adicionais conforme capacidade/complexidade, com economia de tokens compatível com acerto.

## Base e preservação

Remoto `alandougs/central-cpj-postgres`, `origin/main` em `2ce862d` (confirmado novamente por fetch). HEAD local inicial `f56653c`, ancestral de main, 59 commits ausentes na pasta. Mudanças locais posteriores à revisão remota foram preservadas em cópias ZIP verificadas e branch `codex/backup-antes-sync-20261027`. Dados de casos, configurações, credenciais, modelos/assinaturas operacionais e temporários privados não integram a seleção de código. Candidato isolado no backup externo ao workspace; não se aplica código não conferido por reset destrutivo.

## Entregas verificadas antes do gate final

SX01 combina módulos/fila/ASTRA remotos com segurança e correções locais. MD01 passa a produzir Markdown e checkpoint essencial consolidado, com leitura legada, páginas, qualidade e O.S. rastreáveis; não gera CSV/JSON analítico novo. RG40 calcula candidatos estruturados em memória a partir do Markdown para o mesmo SQLite/grafo, mantendo consultas e cruzamentos sem recriar intermediários. RI01 fornece `--sem-baixa` para manutenção sem alterar o estado dos casos.

MM01 cria `MEMORIA.md` como entrada comum das fontes canônicas, adapta CLI/API e adaptadores, preserva segregação de casos e aprovação das lições genéricas. Política de coordenação em AGENTS21–23: Astra preferida na coordenação, Sol/Terra/Luna conforme tarefa/custo/capacidade; nenhuma troca automática de provedor/runtime ou autorização de chamada externa. AV01 encontrou e corrigiu ordem absoluta de não perguntar que conflitaria com o bloqueio de redação sem O.S. vigente/extração completa. AU01 complementa o revisor existente com evidências divergentes, explicações alternativas compatíveis, reconciliação financeira, lacunas e parecer claro; nenhum percentual inventado de certeza penal.

EN01 recuperou Python3.12 local após transferência do perfil e disponibilizou OCR portátil verificado dentro do projeto, sem instalação global/rede/registro/serviço. Dependências existentes preservadas. Runtime e idiomas permanecem locais e ignorados no Git.

SZ03 removeu 36.878 derivados reconhecidos, totalizando 981.352.481 bytes, somente após ZIP privado com 36.878 membros e 343.180.955 bytes verificado por tamanho/SHA-256. Os 1.188 PDFs/Markdown/originais protegidos mantiveram hashes; 85 checkpoints consolidados, 89 Markdown faltantes acrescentados sem sobrescrita; 16 documentos bloqueados e 4.705 derivados sem condição segura preservados. O helper foi corrigido para leitura linear e recusa de reparse antes de compactar. Auditoria dos 85 estados constatou zero reparse points. Manifestos/nomes/hashes de caso ficam somente no backup privado, não neste relatório genérico.

## Verificação e correções integradas

Rodada inicial com log no F foi interrompida por erro de E/S do volume; não foi concluída. O Windows informou HealthStatus Warning no F(exFAT); isso não confirma causa e nenhum reparo de disco foi feito. Logs das rodadas completas seguintes ficam no C temporário.

Primeira rodada completa: 138/144 suítes. Corrigidas fixtures antigas de backup/runner, leituras do checkpoint por página, erro claro fora do workspace e entrega de respostas HTTP403 no Windows. IV04 drenagem JSON limitada a 64 KiB em respostas de erro preserva auth/CSRF/TLS e exclui mídia, sucesso e corpos grandes/desconhecidos; TDD, 40 respostas HTTP reais,SEC21 e Central completa aprovados.

A rodada também demonstrou lease órfã de extração: retomada podia aguardar 12 horas após morte do servidor. IV01/RS01 corrigem recuperação antecipada somente do extrator local rápido com host/PID/nascimento verificáveis, preservando vivos/incertos/legados/modos externos. Trava de arquivo mantida pelo filho impede dois escritores mesmo com pai morto; retomada não sobrescreve checkpoint antes da aquisição. Auditoria Astra independente: 25 testes e disputa entre 6 processos com única recuperação/reserva. Expiração antiga/outros modos permanecem conservadores, sem acelerar retry externo incerto.

Segunda rodada completa: 144/145 suítes em 674,25 s. Única falha: lock preso após retorno de runpy. A aquisição foi convertida em contexto léxico até o fim da extração, liberando no sucesso e exceção sem remover o arquivo de lock persistente. Sol e Astra confirmaram PX05 11/11,UN17 3/3,UN14 22/22; sem skips nesses cenários. A rodada integral seguinte confirmou 145/145 suítes, com os skips ambientais discriminados.

## Checkpoint de execução do coordenador

Candidato: `F:/CPJ-BACKUPS/sync-github-20261027-023944/candidato`.

Gate3 concluído: 145/145 suítes em 686,80s, retorno zero; sete cenários de symlink e um cenário físico exFAT ignorados por ambiente, com junctions nativas executadas. As341fontes conservaram hashes; log `C:/Users/Usuario/AppData/Local/Temp/cpj-full-gate3-20261027.log`. Manifesto genérico das 341 fontes congeladas: `fontes-gate-final.json` no backup. Não alterar produto durante a rodada. Confirmar código de saída e skips explícitos. Fontes anteriores desta rodada não devem ser confundidas com os snapshots anteriores que reprovaram.

Após aprovação: atualizar fila combinando estados locais com histórico remoto por ID; executar plano privado `aplicar-codigo-revisado.py` (guardas de HEAD/index/fontes/alterações inesperadas/dados protegidos), criar branch local `codex/sincronizacao-enxuta-20261027`, guardar alterações locais via stash seletivo, fast-forward main e copiar somente fontes públicas revistas. Não aplicar stash antigo sobre o código combinado nem tocar dados privados por reset/clean. Conferir os 341 hashes aplicados. A solicitação tem foco em receber o GitHub na pasta local; não fazer merge/default branch/restart/migração da fila ou publicar dados.

RI02: backup consistente `rag-antes-indexacao.sqlite` já passou PRAGMA integrity_check; backup do ledger manual foi verificado, sem arquivos preexistentes nesse ledger. Manifesto privado registra 74 arquivos caso.json (inclui modelo) para conferir bytes/SHA após manutenção. Só depois do código validado rodar indexar `--tudo --sem-baixa` no workspace real, preservando fonte manual/estados e mantendo todos os originais. Não enviar banco ou backup para serviços externos. Conferir integridade do índice e arquivos de estado, registrar resultado genérico.

Fechar SY05/RI02 e atualização PRD/revisões, com scanner apenas na seleção explícita de código se houver commit local. Preservar não rastreados privados, como histórico duplicado de calibração e temporário de upload não comprovado dispensável. Scanner de sigilo LP01 não identificou bloqueio na árvore de código; seleção staged final ainda deve ser conferida, se usada. Brasão institucional local não é assinatura pessoal, mas continua sob exclusão geral de mídia no Git.

## Continuidade operacional autorizada

Depois da manutenção validada, seguir o objetivo ativo da conversa: inventariar a fila oficial, reservar uma O.S. livre sem relatório, completar PDFs pendentes/OCR/Markdown, conferir a O.S. vigente e suas solicitações, analisar fatos e lacunas, redigir, revisar independentemente e gerar DOCX no modelo oficial. Um caso por vez, sem refazer relatório existente automaticamente, sem inventar dados e sem entregar oficialmente/gerar FINAL. Autorização de leitura/análise nesta sessão já existe em AGENTS18 e no pedido expresso do operador; não pedir novamente confirmação do modelo desta sessão. Não estende a APIs/provedores/OSINT de pessoa física. Usar fila-os e procedimentos vivos, fontes somente do caso e assinatura autorizada do investigador. Objetivo só estará completo após tratar as pendências operacionais autorizadas ou registrar bloqueios reais conforme a governança.

Inventário preliminar contou apenas metadados; antes de selecionar trabalho, cruzar status/relatórios na pasta da O.S. e no caso para evitar duplicação. Fatos/identificadores dos casos não pertencem à memória central nem à fila pública de desenvolvimento.

## Aplicação concluída

Código aplicado à pasta original, branch local `codex/sincronizacao-enxuta-20261027` sobre2ce862d, stash de preservação mantido. Índice reconstruído com `--sem-baixa`, banco íntegro e arquivos de estado/originais/Markdown conferidos sem alterações. Correção RG41 de releitura do checkpoint validada por61testes dirigidos, aplicada após conferir hashes;341fontes finais iguais ao conjunto validado. Ver `revisoes/reindexacao-aplicada-2026-10-27.md`, incluindo o crescimento do SQLite e a distinção entre volume removido e economia líquida. Próxima fase: fila operacional autorizada, uma O.S. por vez, sem refazer relatórios existentes nem dar baixa oficial.

## Retomada após pausa do operador

O operador determinou continuar até concluir o escopo em 27/10/2026. A manutenção já aplicada foi preservada; não se repetiu a limpeza nem a reconstrução do índice. A conferência independente final FV01 foi retomada para atualizar as pendências históricas deste registro. As instruções antigas que ainda mencionavam CSV na tabela operacional de AGENTS.md e na premissa de PRD.md foram alinhadas à regra vigente de extração somente Markdown; portáteis regenerados e conferidos (12 arquivos), adaptadores Codex conferidos sem alteração. Scanner da seleção previamente staged: 170 arquivos e zero achados proibidos. Sem commit/push ou publicação nesta retomada; alterações locais continuam disponíveis para revisão.

A fila operacional foi consultada novamente com CPJ_WORKSPACES limitado ao workspace F:. A seleção exige distinguir relatório de outros documentos Word, excluir casos já concluídos/com relatório e respeitar reservas. Inventários operacionais e identificação de pendências ficam somente em registros privados ou nos próprios casos.

Fechamento da manutenção nesta retomada: FV01 concluída com 341/341 hashes e 12 testes focais independentes novamente aprovados. SY05 concluída pelo script da fila. A fase operacional continua separadamente, sem inserir dados de casos neste registro.

## Complemento de autorização na retomada

Em 27/10/2026, o operador determinou sincronizar com GitHub ao final e lançar as entregas no próprio sistema CPJ para refletir no dashboard. Publicação restrita a código e documentação genérica revisados; dados operacionais, autos, bancos, configurações e assinaturas permanecem locais. A interrupção transitória de disponibilidade do volume F: foi constatada por leitura e cessou após retorno da unidade. Retomada exige conferência de integridade antes das gravações. Nenhum reparo de disco ou cópia de casos para outro volume/serviço foi realizado.

## Limpeza complementar verificada

Após nova determinação de limpeza do operador, foram removidos 37 caches regeneráveis (27 bytecodes com fonte correspondente e 10 arquivos de cache de testes), totalizando 391.606 bytes. ZIP privado com 37 membros únicos, CRC, tamanhos e SHA-256 conferidos antes/depois; fonte dos 27 módulos preservada por hash. Coordenador repetiu a conferência do arquivo de recuperação, dos alvos ausentes e dos fontes. Nenhuma pasta, ambiente Python, Git, Tesseract, caso, análise, relatório, lock, imagem crítica, log ou derivado incompleto/divergente foi excluído nesta passada. A limpeza documental anterior de 36.878 derivados permanece separada; não se soma esta conferência como nova remoção daqueles mesmos arquivos.

## Correção localizada de paginação DOCX

A conferência do documento no Word revelou títulos de seção isolados no fim da página. O gerador agora define keepNext e keepLines somente nos três títulos canônicos, preservando conteúdo e demais propriedades do modelo. O novo teste F04 falhou nos três títulos antes da correção; depois, F04 6/6, SIG01 12/12 e RG28 5/5 passaram, zero skips, usando somente fixtures sintéticas. Delta de dois arquivos registrado por hashes no manifesto privado; sem repetir a suíte integral. A rodada integral de 145/145 permanece evidência do snapshot anterior, complementada pelos deltas dirigidos de cache e paginação.

## Arquivamento técnico complementar

Quatro perfis de navegador comprovadamente criados em QA antigo, sem uso observado nos processos relevantes, foram arquivados em ZIP privado verificado antes da remoção: 1.004 arquivos, 42.899.083 bytes e 497 diretórios. O arquivo preserva também 178 diretórios vazios; 1.182 membros únicos, CRC e hashes conferidos. Os 1.304 arquivos fora dos alvos na árvore operacional mantiveram tamanho/hash. O coordenador reconferiu ZIP/manifesto/membros e ausência dos alvos. Nenhum dado foi enviado para outro serviço e nenhuma restauração real foi alegada. O ambiente Python antigo permanece por dispensabilidade não comprovada. Uma cópia de histórico com conteúdo byte a byte idêntico ao canônico (386 bytes) também foi arquivada e removida após verificação, mantendo o original intacto.

## Limite final de limpeza de diretórios

Um marcador técnico de escrita de dois bytes foi arquivado em ZIP privado verificado e removido. A remoção dos diretórios vazios foi interrompida após Acesso negado em um cache com atributo somente leitura; nenhum atributo/permissão foi alterado. Os 17 diretórios vazios permaneceram. Scripts operacionais locais, PDF avulso sem classificação e temporários de origem não demonstrada foram preservados. Não se declara remoção integral de material desconhecido nem liberação de espaço a partir de diretórios vazios.

## Deltas finais de integridade e paginação

O teste de paginação passou a reproduzir também o espaçador vazio do modelo; keepNext é propagado apenas pelos separadores vazios seguros, mantendo o título com o texto sem alterar conteúdo/espaçamento. F04 7/7, SIG01 12/12 e RG28 5/5 passaram (24 testes). MD02 reproduziu perda de transcrição preenchida em retomada por checkpoint obsoleto; a proteção conservadora recusa antes da primeira gravação, sem declarar qualidade ou alterar imagens. Validação dirigida: 34 testes e 22 verificações OCR. Intermitência UN17 numa tentativa ficou registrada; reteste isolado passou sem alteração. Manifesto das 341 fontes atualizado por hashes; revisão independente dos deltas e nova execução integral seguem pendentes antes da publicação. Nenhum caso real foi usado nas fixtures ou modificado pela correção.

## Reauditoria MD02 — BOM

FV02 reproduziu um bloqueante: arquivo de transcrição visual vazio/placeholder com BOM podia contornar a guarda inicial. MD02 unificou leitura e validação em UTF-8-sig, preservando suporte ao texto legítimo. TDD e regressões finais: 36 testes dirigidos e 22 verificações OCR, sem skips. FV02 repetiu independentemente MD01 12/12 e as quatro reproduções consolidado/legado × vazio/placeholder BOM; todas recusam antes da gravação com bytes preservados. Achado encerrado na revisão focal, DOCX também aprovado focalmente. Manifesto das341fontes incorpora os dois hashes finais; nova rodada integral permanece pendente e será executada após cessarem operações de casos.

## Conferência complementar de higiene

O operador reiterou a limpeza dentro do projeto. Auditoria independente somente por metadados não encontrou caches regenerados; os 37 arquivos de cache e os 1.004 arquivos de perfis QA anteriormente removidos continuam ausentes. Permanecem os 4.705 derivados protegidos por pendências de integridade, totalizando 1.014.246.768 bytes, sem evidência adicional que autorize sua exclusão. O ambiente de teste antigo, temporários de transferência, scripts locais e PDF avulso de origem incerta foram preservados. Os 17 diretórios vazios com bloqueio anterior continuam sem tentativa de contorno.

Dois outros diretórios temporários foram reconferidos vazios, dentro da raiz resolvida, sem atributos de somente leitura ou reparse. Foram removidos sem recursão e a ausência foi verificada; nenhum arquivo ou byte documental removido nessa etapa. A premissa antiga Markdown + CSV do PRD foi alinhada à determinação vigente de extração somente Markdown.

A primeira tentativa de nova suíte integral foi interrompida: EN01 recebeu um valor de ambiente incorreto para o caminho do runtime. Corrigido o ambiente para o diretório real do Tesseract, foi iniciada nova execução integral em sandbox, sem mudanças no código para contornar a falha. O resultado dessa execução ainda precisa ser conferido; não se declara aprovação com base na tentativa interrompida. Durante o gate, os agentes apenas leem fontes e escrevem suas análises reservadas; sem alterações em código, reindexação ou estado operacional concorrentes.

## Resultado integral atual e ambiente antigo

A execução completa seguinte terminou com exit 0: **145/145 suítes aprovadas em 662,51 s**, incluindo MD02 e os demais deltas finais. Log local `C:/Users/Usuario/AppData/Local/Temp/cpj-full-gate5-20261027.log`. Há oito cenários não executados: sete dependentes de criação de links simbólicos sem privilégio e um cenário ambiental SEC22. Não foram contados como cobertura executada. Junctions e as demais verificações nativas foram efetivamente executadas. Uma execução aprovada não demonstra eliminação da intermitência anteriormente observada em UN17. Os hashes das 341 fontes foram reconferidos sem divergências antes desta rodada.

A auditoria de um ambiente Python antigo encontrou 2.354 arquivos padrão de dependências, totalizando 180.171.957 bytes: 2.318 hashes conferiram com RECORD, outros 29 arquivos eram os próprios RECORD e sete eram componentes normais do venv. Nenhuma referência funcional ao ambiente foi encontrada; a Central usa `.venv`. As três diferenças de versões de pacotes foram preservadas no arquivo recuperável, sem tratar os ambientes como idênticos. A consulta de processos tinha linhas indisponíveis, portanto não foi apresentada como prova absoluta de ausência de consumidores.

Após o gate, esse ambiente foi arquivado em ZIP privado novo de 70.617.455 bytes, com todos os membros, CRC, tamanho e SHA-256 verificados antes da exclusão. Os 2.354 arquivos foram removidos somente da subpasta exata autorizada e sua ausência foi conferida. Nenhum atributo ou permissão foi alterado. O executável de `.venv` conservou o hash registrado. O manifesto privado guarda os caminhos, hashes e resultado da operação. A reauditoria independente confirmou 2.354 arquivos e 271 diretórios, todos os hashes, tamanhos, CRC e caminhos, sem membros extras/duplicados/links, correspondência exata dos removidos, ausência do alvo e preservação do executável atual. O runtime atual iniciou e importou Flask, python-docx, pypdfium2 e PIL após a limpeza. Não se alega teste de restauração real nem liberação líquida de 180 MB no volume que também guarda o ZIP.

Uma conferência independente posterior comparou as fontes imutáveis com o baseline privado anterior à limpeza: **504/504 arquivos, 1.441.042.959 bytes**, iguais por tamanho e SHA-256, sem ausências ou erros de leitura. São 112 arquivos de todas as extensões em `00-originais` e 392 PDF/Markdown de `01-extracao`. O baseline completo tem 1.188 entradas; as 684 restantes incluem análises, relatórios e registros legitimamente atualizados durante o trabalho operacional posterior e não foram usadas para alegar imutabilidade global. Esta verificação não certifica a qualidade semântica do OCR.

## Checkpoint de pausa expressa — 27/10/2026

Operador pediu guardar o ponto e pausar. Agentes interromperam o trabalho e registraram seus checkpoints; nenhuma publicação ou nova etapa deve começar antes de retomada expressa. Estado técnico: branch `codex/sincronizacao-enxuta-20261027`, HEAD e `origin/main` em `2ce862d6f96b1cc4731be3223f868de5c79de406` na última consulta; alterações integradas continuam locais, sem commit/push/PR desta entrega. Há 173 arquivos previamente selecionados/revisados no índice e documentos posteriores ainda não selecionados; refazer conferência de sigilo e staging explícito antes de publicar.

O gate 145/145 acima é a evidência do snapshot anterior ao início de CI27. Foram confirmados dois bloqueios no clone limpo do CI: runtime EN01 ausente sem `CPJ_EN01_ENGINE` e skip SEC22 de volume físico não aceito no modo estrito. CI27 está incompleta e reservada. Apenas o novo teste `teste_ci_volume_ci27.py` e `revisoes/ci-final-ci27-2026-10-27.md` foram criados; o primeiro ciclo teve 3 falhas e 1 skip em 4 testes, sem correção aplicada. Não alegar que o estado atual passa integralmente. Antes de executar esse teste novamente, corrigir seu isolamento: dois ensaios negativos alcançaram o SEC22 antigo e criaram temporários fictícios na raiz do volume, fora do projeto; foram removidos automaticamente. Não houve formatação, montagem ou alteração de ACL. Checkpoint CI27 contém a ocorrência e o próximo passo seguro. Não dispensar cobertura nem executar provisionamento de disco no computador do operador.

O progresso operacional permanece nas filas e nos próprios casos, sem dados de autos neste registro público. A entrega mais recente ainda requer complemento de conferência visual independente e atualização final de base/painel; não repetir o registro do relatório já existente. A reindexação RAG incremental final e a sincronização remota permanecem pendentes. Detalhes de retomada, caminhos e hashes operacionais estão no checkpoint privado `RETOMADA-20261027.md`, dentro do diretório de recuperação já autorizado `F:/CPJ-BACKUPS/sync-github-20261027-023944`.

Uma tentativa de exclusão de temporários de QA fora do projeto foi rejeitada pela revisão automática com “blocked by policy”. O alvo foi preservado, sem contorno. Diretórios vazios anteriormente bloqueados e arquivos de utilidade incerta também permanecem. Não confundir pausa com conclusão integral da limpeza, do lote operacional ou da publicação.

## Resolução das 7 falhas do PR #25 com esquadrão de 10 agentes — 28/10/2026

Por determinação expressa do operador em 28/10/2026 ("resolve o problema... faça com 10 agentes"), a coordenação central (**Astra**) assumiu `CI27`, `UI01` e `SY05` e orquestrou 10 subagentes em paralelo com escopos disjuntos (7 executores `Sol`/`Terra` e 3 auditores independentes `Luna`):

1. **`Sol-1-EN01` (`teste_ambiente_en01.py`)**: isolou `os.path.isfile` ao workspace temporário no teste unitário de precedência de `PATH` (evitando que `C:\Program Files\Tesseract-OCR\tesseract.exe` pré-instalado no runner interceptasse o mock) e adicionou fallback para `self.c._achar_tesseract()` no teste de clone limpo quando `CPJ_EN01_ENGINE` e `ROOT/ferramentas/tesseract` estão ausentes. Resultado: **5/5 OK**.
2. **`Sol-2-CI27` (`CI27` / `SEC22` / `validacao.yml`)**: concluiu `ferramentas/ci-volume-exfat.ps1` (restrito ao runner Windows hospedado do GitHub Actions com `CPJ_CI_EXFAT_ENABLE=1`), atualizou `teste_segredos_auditoria_sec22.py` para exigir/validar a fixture explícita `CPJ_SEC22_VOLUME_SEM_ACL_DIR` sem usar `Path(__file__).anchor`, isolou os testes negativos em `teste_ci_volume_ci27.py` e configurou os passos de mount/dismount e `CPJ_EN01_ENGINE` em `.github/workflows/validacao.yml`. Resultado: `teste_ci_volume_ci27.py` **6/6 OK**, `teste_segredos_auditoria_sec22.py` **14/14 OK**, `teste_publicacao_un17.py` **20/20 OK**.
3. **`Terra-3-AST11` (`teste_astra_ast11_api.py`)**: normalizou `snapshot.resolve().is_relative_to(backup.resolve())` em `test_backup_restauracao_preserva_conferencias_sem_indice`, resolvendo a divergência entre o caminho curto 8.3 (`RUNNER~1`) de `$env:TEMP` no runner Windows e o caminho longo (`runneradmin`) emitido por `backup_consistente.py`. Resultado: **15/15 OK**.
4. **`Terra-4-SEC23` (`teste_backup_exportacao_sec23.py`)**: normalizou `self.ws.resolve()` e `restaurado.resolve()` no mock `suporta(path)` de `test_restauracao_preserva_auditoria_ancorada_fora_do_workspace`, que falhava quando `$env:TEMP` usava caminho 8.3 (`RUNNER~1`). Resultado: **16/16 OK**.
5. **`Terra-5-UN17` (`teste_interrupcao_real_un17.py`)**: adicionou leitura tolerante a locks transitórios do Windows (`PermissionError`/`OSError`/`JSONDecodeError`) durante `os.replace` concorrente no polling de `processamento.json` e `.checkpoint/estado.json`. Resultado: **3/3 OK**.
6. **`Sol-6-LC01` (`teste_lacunas_lc01.py`, `rag.py` e `ferramentas/testar-tudo.py`)**: incluiu os 8 documentos antigos da raiz em `clonar_codigo()` de `testar-tudo.py`, antecipou a verificação de ausência de vetores (`sem_vetores` -> `indexar.py --embeddings`) em `rag.py` antes da checagem de `fastembed`, propagou `CPJ_EMBEDDINGS_CACHE` e UTF-8 nos subprocessos e reconheceu `PADROES_OPCIONAIS` no modo estrito quando `fastembed` não está instalado no host. Resultado: **26/26 OK** com `fastembed` e **OK (0 skips críticos)** sem `fastembed`.
7. **`Sol-7-AP38` (`inteligencia-mapa.js` / `teste_mapa_unico_ap38.py`)**: removeu o re-enquadramento incondicional em todo retorno à aba `#mapa` quando `f.correlacao_id` estava preenchido e cancelou o auto-enquadramento pendente caso o usuário ajuste o zoom manualmente durante uma carga assíncrona. Resultado: **4/4 OK**.
8. **`Luna-8-Auditor-UI01`**: executou a revisão independente obrigatória de `UI01` (`APROVADO`, registrada em `revisoes/marcacao-busca-ui01-2026-10-27.md`).
9. **`Luna-9-Auditor-CI-OCR-RAG`** e **`Luna-10-Auditor-Backup-UN17-Mapa`**: auditaram independentemente todas as 7 frentes, os invariantes de `teste_publicacao_un17.py` e o scanner de sigilo (`verificar-publicacao.py`), com parecer `APROVADO`.
