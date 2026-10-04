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

## Validação

- `teste_relatorios_rv17.py`: 11 testes aprovados, incluindo seis requisições concorrentes, recusa de versão errada, falha do conferidor, numeração com lacunas e falha de I/O.
- `teste_executores_rv17.py`: 6 testes aprovados, incluindo leitura/escrita por aliases, gerador DOCX, listagem, preservação do arquivo diante de falha e operações válidas.
- Antes das correções, os testes novos reproduziram as falhas. Depois, todos os 17 passaram.
- Suítes existentes: segurança (11 testes), solo (7), modularização (6) e gate de entrega (5) aprovadas. Sintaxe dos cinco arquivos Python alterados/adicionados e `git diff --check` aprovados.
- Suíte completa executada antes e depois em snapshots descartáveis por `python -u ferramentas/testar-tudo.py`: **30/48 antes (174,21 s)** e **32/50 depois (173,97 s)**. As duas suítes novas passaram; permanecem exatamente as mesmas 18 suítes com falha da versão-base. Nenhuma suíte que passava antes passou a falhar. O runner retornou 1 nas duas execuções, portanto a validação integral continua pendente.

## Pendências anteriores à RV17

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

As correções desta revisão devem ser avaliadas com essas limitações; as pendências de validação integral permanecem explícitas no PR. Instalação na máquina do investigador e alinhamento da branch padrão são etapas separadas da publicação da branch de correções.
