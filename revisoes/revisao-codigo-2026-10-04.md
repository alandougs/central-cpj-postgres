# Revisão de código da Central CPJ — 04/10/2026

Repositório: `alandougs/central-cpj-postgres`. Base revisada: `main`, commit `927c54891e7fc24321f273ab05e5760c9efc2490`. `consolidacao-2026-10-01` aponta ao mesmo commit; `master`, a branch padrão, contém a versão anterior `7e537c4`. As correções usam a consolidação mais recente e serão enviadas em branch própria com PR para `main`.

Código e testes fictícios foram usados em Linux/Python 3.12, com dependências de `requirements-dev.txt`. Nenhum auto real, conta de produção ou chave de API foi utilizado. A revisão aplicou `AGENTS.md`, `PRD.md` e a reserva RV17 na fila compartilhada.

## Falhas reproduzidas e corrigidas

| Prioridade | Gatilho e falha anterior | Correção |
|---|---|---|
| P1 | Vários editores salvavam simultaneamente com a mesma `versao_base`; a checagem ocorria antes da reserva, permitindo aceitar todas as gravações. | Leitura da última versão, validação da base e publicação da nova minuta sob a mesma trava reentrante do caso. Uma gravação aceita, demais retornam 409. |
| P1 | `conferencia-vNN.json` aprovado de uma execução anterior era devolvido quando a execução atual do conferidor falhava. | Remover o resultado JSON anterior sob trava antes de executar; aceitar apenas resultado atual válido e compatível com o retorno do processo. Ausência de resultado, timeout e erro de I/O bloqueiam a entrega. |
| P1 | `FINAL` do DOCX v01 podia usar uma minuta v02 explicitamente enviada, ou a mais recente quando v01 não existia. | A minuta explícita precisa existir e corresponder à versão do DOCX; versão conhecida sem minuta correspondente bloqueia com 409. Entrega com ressalva continua exigindo justificativa e auditoria. |
| P1 | Alias em análise/relatórios apontando aos originais permitia ler ou sobrescrever o original pelas ferramentas de API. A ferramenta DOCX não verificava o destino real. | Validar também o caminho resolvido e suas raízes permitidas. Gerador DOCX recusa redirecionamento da pasta e links no destino. Listagem apresenta somente arquivos legíveis pelo agente. |
| P1 | `caso.caminho('.')` e `caso.caminho('..')` eram aceitos e representavam diretórios acima da pasta do caso. | Recusar esses identificadores; as ferramentas de API também validam ID e contenção do caso no workspace. |
| P2 | Com apenas `minuta-v03.md` no disco, salvar criava `minuta-v01.md`, que não seria considerada a mais recente. | Usar a reserva existente de próxima minuta baseada no maior número de versão e publicação por substituição atômica. |
| P2 | `versao_base` inválida era ignorada ou convertida indevidamente, permitindo escrita sem a proteção esperada. | HTTP 400 para valores inválidos, negativos, booleanos e fracionários, antes da escrita. |
| P2 | Erro de permissão ou disco em `reservar_arquivo_versao` era tratado como arquivo existente e gerava um loop. | Repetir apenas diante de `FileExistsError`; propagar demais erros. |
| P2 | Escrita de ferramenta de API truncava o arquivo existente antes de terminar a gravação. | Gravar em temporário no mesmo diretório e publicar com `os.replace`; falha conserva a versão anterior e limpa o temporário. |
| P2 | Definir um arquivo já chamado `FINAL` novamente causava `SameFileError`. | Evitar copiar o arquivo sobre si mesmo, mantendo conferência, baixa e auditoria. |

## Validação da primeira rodada RV17 (histórico)

- `teste_relatorios_rv17.py`: 11 testes aprovados, incluindo seis requisições concorrentes, recusa de versão errada, falha do conferidor, numeração com lacunas e falha de I/O.
- `teste_executores_rv17.py`: 6 testes aprovados, incluindo leitura/escrita por aliases, gerador DOCX, listagem, preservação do arquivo diante de falha e operações válidas.
- Antes das correções, os testes novos reproduziram as falhas. Depois, todos os 17 passaram.
- Suítes existentes: segurança (11 testes), solo (7), modularização (6) e gate de entrega (5) aprovadas. Sintaxe dos cinco arquivos Python alterados/adicionados e `git diff --check` aprovados.
- Suíte completa executada antes e depois em snapshots descartáveis por `python -u ferramentas/testar-tudo.py`: **30/48 antes (174,21 s)** e **32/50 depois (173,97 s)**. As duas suítes novas passaram; permanecem exatamente as mesmas 18 suítes com falha da versão-base. Nenhuma suíte que passava antes passou a falhar. O runner retornou 1 nas duas execuções, portanto a validação integral continua pendente.

## Diagnóstico inicial anterior à RV18 (histórico)

A execução inicial do runner retornou **30/48 suítes aprovadas**. Ela não comprova validação integral da aplicação. As falhas abaixo já existiam no commit-base:

| Suíte | Evidência observada / próximo diagnóstico |
|---|---|
| `teste_backup_antigravity` | `powershell.exe` ausente neste Linux; revalidar no Windows. |
| `teste_cabecalho_escrivao_copilot`, `teste_core_e03`, `teste_docx_f04`, `teste_workspace_v01` | Dependem do modelo DOCX oficial, que é ignorado pelo Git e não veio no clone. Revalidar com o modelo local autorizado. |
| `teste_calibrar_contencao_rv06` | Snapshot do runner não copia a pasta `calibracao/`; teste não encontra os documentos esperados. |
| `teste_claude_exe_e01` | Expectativa de executável `claude.exe` via `which` não corresponde à descoberta atual no Linux. |
| `teste_dados_os_codex` | Fonte de imagem do Windows indisponível: `OSError: cannot open resource`. |
| `teste_desempenho_f02` | CLI atual de extração não aceita `--workers`, exigido pelo teste. Reconciliar contrato de paralelismo com o código atual. |
| `teste_extracao_codex`, `teste_revisao_pr1_f12` | Testes exigem `checkpoints_reutilizados` e `checkpoints-extracao.json`, ausentes na extração atual. Reconciliar contrato de retomada. |
| `teste_esteira_completa` | Minuta simulada não contém as três seções obrigatórias; gerador DOCX a recusa. |
| `teste_fulltime`, `teste_plantao_claude` | Encerramento de processos usa `taskkill`, indisponível neste Linux. |
| `teste_importacao_codex` | Teste espera retorno `None` no cancelamento, mas o código lança `ImportacaoCancelada`; texto esperado da rejeição de escopo também diverge. |
| `teste_interface_f01` | Limite histórico de tamanho do HTML foi superado pelas funcionalidades posteriores. |
| `teste_squad_claude` | Teste chama `plantao.plano_etapas`, função ausente na versão atual. |
| `teste_central` | Fluxo HTTP não conclui DOCX/FINAL neste clone; logs registram 400 na definição do FINAL e 404 nos downloads dependentes. |

O E2E de navegador retorna sucesso com `SkipTest` quando Edge não está disponível; isso não é evidência de execução visual. Nenhum provedor de IA real foi chamado. O PostgreSQL é legado/experimento no estado atual do projeto: o adaptador foi inspecionado, mas nenhuma instância PostgreSQL ou stack Docker foi executada. Não houve migração de dados nem alteração do esquema.

As pendências acima registram a primeira rodada; a continuação RV18 abaixo substitui esse estado de validação. Instalação na máquina do investigador e alinhamento da branch padrão são etapas separadas da publicação da branch de correções.

## Continuação RV18: correções e reconciliação

O usuário pediu continuação em loop até concluir a revisão e sincronizar GitHub. A RV18 reservou o restante da revisão e repetiu reproduzir → corrigir → testar, mantendo dados fictícios e sandboxes isoladas.

| Problema verificado | Resultado da RV18 |
|---|---|
| OCR sem opção de paralelismo | `--workers 1|2` recuperado, máximo dois bitmaps em voo; somente a thread principal acessa PDFium; imagens, páginas, textpages e documento fechados. Uma passada Tesseract por página; ordem final preservada. |
| Correção visual não tinha checkpoint | Checkpoint visual com SHA-256 da transcrição; reaproveitar somente se intacta; edição ou remoção invalida a versão anterior. Mantidos os dois nomes de contador no relatório para compatibilidade. |
| Reaproveitamento ignorava workspace explícito | Busca entre casos respeita `CPJ_WORKSPACE` quando não há `CPJ_WORKSPACES`. |
| Cancelamento dependia de `taskkill` | Grupos de processo POSIX com `start_new_session`/`killpg`, árvore Windows com `taskkill`, seguido de `wait`. Perda de reserva encerra CLI silencioso; disputa temporária SQLite não desliga o vigia. |
| Supervisor tratava zumbi como vivo | Estado `Z` no `/proc` não é considerado supervisor ativo; ciclo de início/parada e watchdog testados no Linux. |
| Cancelamento ou transferência durante conclusão | UPDATE condicionado a agente, estado em execução e ausência de cancelamento; falha também não sobrescreve reserva alheia nem pedido encerrado. |
| Sucesso sem entrega, arquivo antigo ou indexação falha | Verificar arquivos não vazios exigidos pela etapa e atualização dos metadados frente ao snapshot anterior; exigir minuta para relatório e revisão correspondente; erro de indexação propagado. CLI com retorno não zero é erro mesmo emitindo `success`. |
| Logs podiam colidir no mesmo segundo | Nome inclui microssegundos e ID do pedido, com um log por sessão. |
| Prompt do redator dizia “revisão concluída” | Removida a alegação de autorrevisão; pedido revisor separado segue sem alterar a minuta. |
| Modelo oficial ausente no clone | Fixture DOCX sintética gerada somente nas sandboxes do runner, com cabeçalho, rodapé, campos e imagem geométrica. Sem fallback sintético no gerador de produção; teste F04 verifica preservação do modelo recebido. |
| Calibração ausente no snapshot | Runner inclui os documentos versionados de calibração. |
| Fontes e descoberta de executável dependiam de Windows | Fixtures usam Arial no Windows e DejaVuSans no Linux; executável fictício recebe permissão de execução antes de `which`. |
| Testes de importação divergiam do contrato | Cancelamento deve lançar `ImportacaoCancelada` e conservar estado/ausência de arquivos; rejeição de escopo continua verificada antes de qualquer escrita. |
| Esteira/HTTP enviavam minutas inválidas | Fixtures com as três seções e cabeçalho completos; teste HTTP usa somente afirmações apoiadas na página fictícia. Gate continua ativo, sem forçar entrega. |
| F12 editava formato de checkpoint extinto | Edita `.checkpoint/p0001.json`; continua verificando precedência da correção visual sobre OCR duvidoso. |
| Limite de HTML de versão antiga | Orçamento explícito de 150 KiB para a interface atual; verificações funcionais preservadas. |
| Teste S01 usava APIs ausentes | Substituído por testes dos quatro pedidos encadeados implementados, entrega/DOCX, sessões e logs separados, prompts independentes, falha/cascata, retomada, cancelamento, reserva transferida e propagação de indexação. Não comprova análise por blocos paralelos nem ajuste automático. |
| Runner ocultava testes pulados | Resume skips de ambiente. Integração PowerShell/robocopy e Startup exigem Windows; Edge exige navegador instalado. |

### Evidências da continuação

- Rodada integral intermediária: **48/50 suítes sem falhas, 92,35 s**. Duas falhas restantes: fixture L05 com fonte pequena/inadequada e cabeçalho HTTP incompleto rejeitado pelo gate; corrigidas e reexecutadas isoladamente com sucesso.
- OCR real em português testado com tessdata do histórico do próprio repositório, materializado em pasta de dependências fora do checkout (`/workspace/scratch/tessdata`). Nenhum traineddata ou DOCX binário foi adicionado ao commit.
- Rodada integral final: `TESSDATA_PREFIX=/workspace/scratch/tessdata python -u ferramentas/testar-tudo.py` → **50/50 suítes com retorno zero, 92,93 s**, incluindo OCR real, reconstrução de texto em uma passada, invalidação/retomada de checkpoints, 120 páginas do ensaio core, workflow HTTP DOCX/FINAL/baixa/download, concorrência, segurança e isolamento API. Os três skips divulgados pelo runner são backup PowerShell/robocopy, E2E Edge e Startup Windows. Duas suítes ficam inteiramente puladas; a full-time executa os testes portáveis e pula somente o Startup.
- `teste_squad_claude.py`: 10 testes aprovados; sem uso de API real. Os 17 testes RV17 continuam passando dentro da rodada final.
- AST dos 20 arquivos Python alterados/adicionados e `git diff --check` aprovados. Nenhum dado do workspace temporário, credencial de teste, PDF ou modelo binário faz parte do commit.
- Correções reunidas na branch `codex/revisao-bugs-2026-10-04`, PR [#2](https://github.com/alandougs/central-cpj-postgres/pull/2) para `main`. A rodada final remove a pendência de falhas do core que motivava o rascunho inicial; permanecem somente os limites de ambiente abaixo.

### Limites da validação

Modelo DOCX oficial do operador, APIs reais e a stack PostgreSQL legada não foram executados. O modelo sintético comprova o contrato de transformação/preservação, não a fidelidade visual do timbre oficial. PowerShell/robocopy, Startup do Windows e E2E Edge são explicitamente pulados no Linux sem Edge; não contam como execuções funcionais aprovadas. Não houve autos reais, migração, alteração de rede ou instalação em produção. A publicação usa a branch `codex/revisao-bugs-2026-10-04` e PR #2 para `main`; a configuração da branch padrão e a integração desse PR são decisões separadas.
