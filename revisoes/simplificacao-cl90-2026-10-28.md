# CL90 — simplificação Cline e verificação integrada

## Base, limites e ambiente

Base `7d910cc472862e63980830904936f0afb3e71c66`; branch local `cline/simplificacao-20261028`; worktree `D:/CPJ-DEV/cline-simplificacao-20261028`. Commits locais: `8756508` (contexto) e `a9cc04c` (legado/dependências); a fixture e este registo formam o lote seguinte. Fila canónica `D:/CPJ - TRABALHO/TAREFAS-COMPARTILHADAS.md`, tarefa `CL90`, agente `Cline-CL90`. Windows 11 26200, PowerShell 7.6.9 e Python 3.12.14 da `.venv` existente. Nenhum push, merge, instalação, provedor externo, dado operacional ou configuração real. `CX90/CX91` e `AG90` têm reservas disjuntas; PRD, interface e contratos dessas frentes não foram editados.

## Baseline anterior às alterações

- Pacote: 114 arquivos, 2.077.945 bytes de conteúdo, 162 exclusões já existentes; manifesto em `D:/CPJ-DEV/cl90-artefatos/baseline-manifesto.json`. Essas exclusões não foram contabilizadas como ganho novo.
- Portáteis e adaptadores conferiam com as fontes. MM01 8/8; CI27 6/6 sem comandos reais de disco; dependências aprovadas; LC01 26/26 em 60,600 s, com backend local real `fastembed/numpy` e zero skips nessa execução. UN16 tinha duas falhas pela ausência do brasão sintético no worktree e um skip de privilégio de symlink.
- Composição de instruções (caracteres, não tokens): `analisar` 100.202; `financeiro` 74.158; `relatorio` 149.501; `revisar` 91.634; `completo` 186.826; `esteira` 224.245. Cada portátil repetia as regras centrais e alguns repetiam as lições; agentes/skills também eram acrescentados fora do snapshot.
- A primeira tentativa de suíte integral foi iniciada antes das edições, mas o runner clona cada suíte no momento da execução e a retomada permitiu que o código mudasse durante a rodada. O resultado misto de 135/148 foi descartado como baseline/candidato coerente; não é usado como evidência de aprovação. Falhas focadas anteriores às alterações permanecem registadas acima.

## Inventário e decisões

| item | função | consumidores | ativo/legado/gerado | ação proposta | risco | teste | reversão |
|---|---|---|---|---|---|---|---|
| `legado/postgres-docker/` (7 arquivos) | experiência congelada Docker/PostgreSQL | nenhum inicializador, import, subprocesso, rota ou CI atual; só documentação histórica | legado versionado, sem alterações exclusivas | retirar | reativar referência histórica por engano | pesquisa estática, dependências e regressões | reverter commit CL90 ou recuperar paths de `7d910cc` |
| `legado/app/rotas_*.py` (5) | rotas monolíticas anteriores à A01 | substituídas por `app/rotas/`; sem consumidores atuais | legado versionado | retirar | confundir compatibilidade ativa com legado | modularização e suíte | idem |
| `legado/app/modify_tarefas.py` | patch pontual de desenvolvimento | nenhum | legado versionado | retirar | executar patch antigo se preservado | pesquisa e suíte | idem |
| `legado/app/db.py` | adaptador PostgreSQL | somente o migrador legado | legado versionado | retirar | perder referência de experiência congelada | dependências e suíte | idem |
| `legado/ferramentas/refatorar_servidor.py` | divisão pontual já aplicada | nenhum | legado versionado | retirar | repetição de patch destrutivo se executado | modularização | idem |
| `legado/ferramentas/migrar-json-postgres.py` | migração experimental para PostgreSQL | nenhum fluxo habilitado; caminho de import atual incompatível com a estrutura movida | legado versionado | retirar; não é migração ativa | confundir script histórico com recuperação suportada | dependências e suíte | idem |
| `psycopg[binary]` | driver do adaptador retirado | nenhum após CL-R02 | opcional | retirar de `requirements-opcional.txt` | consumidor externo não versionado | V08 e imports do core | reverter commit; pacote externo deve declarar seu driver |
| PDF/OCR/DOCX (`pdfplumber`, `pypdf`, `pypdfium2`, `pytesseract`, `pillow`, `python-docx`) | extração, renderização, OCR e documentos | imports diretos nos scripts de extração/relatório e testes | ativo | preservar | remoção quebraria fluxos distintos | suíte e smoke DOCX | não aplicável |
| `reportlab`, `playwright`, `quickjs` | fixtures e testes de browser/JS | somente desenvolvimento/CI | desenvolvimento | manter fora da operação | mover para base aumentaria instalação operacional | V08/CI | não aplicável |
| `fastembed` | busca híbrida local | backend RAG opcional | opcional ativo | preservar | perder cobertura semântica | LC01 backend real | não aplicável |
| `pacote-plugin.py` | único empacotador genérico | atualizador e UN16 | ativo | reutilizar sem criar outro | omissão de recurso estático/manifesto | manifesto, hashes, UN16 e smoke | reverter alterações, se houver |
| `executores_llm.py` + `exportar-portatil.py` | composição de IA e portáteis | API/CLI limitado, geradores e distribuição | ativo/gerado | manifesto único; regras uma vez | perda de instrução ou bloqueio | CL90 RED/GREEN, MM01, CF01, UN16 | reverter commit CL-R04 |
| `legado/check_fin.py`, `process_cases.py`, `scratch_extrair*.ps1` | scripts fora dos candidatos | não investigados como alvos de remoção | legado | preservar | escopo insuficiente para exclusão | nenhuma alteração | não aplicável |
| `caso.json`, checkpoints, `plantao.sqlite`, vínculos/notas e RAG | fontes oficiais, coordenação e índice derivado | fluxos existentes | ativo/protegido | preservar; nenhum esquema novo | perda de estado ou memória concorrente | suíte sintética de persistência | não aplicável |

Foram retirados exatamente 16 arquivos, 48.075 bytes de conteúdo versionado. `legado/README.md` foi atualizado. Referências históricas em PRD/revisões/fila não foram reescritas. Nenhum dado, banco, modelo, assinatura ou configuração foi removido.


## CL-R04 — composição implementada

`PACOTES` continua sendo a fonte literal do exportador. Este gera `plugin/investigacao-cpj/procedimentos.json` e o verifica com `--verificar`. O executor API/CLI limitado lê memória, AGENTS e lições uma vez; expande somente as fontes da ação, evita duplicatas e mantém os suplementos dos mapas existentes. O prompt adicional é preservado. Não há truncamento, resumo de evidências, leitura de casos/configuração ou alteração de consentimento, orçamento, cancelamento e escrita.

RED: 3 testes resultaram em 6 falhas de duplicação e 2 erros por manifesto ausente. GREEN: 3/3. MM01 exigia marcador do snapshot duplicado; sua expectativa foi migrada para o contrato vigente de ordenação/releitura usando procedimento fictício, e passou 8/8. CF01 passou; os 12 portáteis regenerados ficam normalizados idênticos ao HEAD (só muda o carimbo).

| ação | antes (caracteres) | depois | redução de caracteres |
|---|---:|---:|---:|
| analisar | 100.202 | 68.669 | 31,47% |
| financeiro | 74.158 | 54.873 | 26,01% |
| relatorio | 149.501 | 89.975 | 39,82% |
| revisar | 91.634 | 61.210 | 33,20% |
| completo | 186.826 | 92.858 | 50,30% |
| esteira | 224.245 | 99.853 | 55,47% |

Medição no mesmo host/Python, com as mesmas fontes genéricas e prompt adicional vazio. Não houve medição compatível de tokens, custo ou qualidade semântica de resposta.

## CL-R06 — fixture de verificação

O runner gerava modelo DOCX sintético, mas não o `static/brasao-pcsp.png` exigido pela interface/UN16; o CI já gerava esse recurso. RED: UN16 2 falhas no runner. `clonar_codigo()` agora cria apenas uma imagem geométrica RGBA sintética na sandbox. GREEN: regressão rápida + UN16 5/5 suítes, com um skip de symlink por privilégio; publicação/CI 20/20. Nenhuma asserção ou cobertura foi removida. CI27 permanece 6/6, sem ensaio físico local.

## Distribuição e medições atuais

Pacote candidato em `D:/CPJ-DEV/cl90-artefatos/pacote-candidato`; manifesto ao lado, 115 arquivos e 2.082.660 bytes. A diferença de +4.715 bytes é o manifesto de procedimentos; a retirada do legado não reduz o pacote porque ele já não era incluído. `procedimentos.json` está presente; nenhum caminho de casos/config/modelos/assinatura entrou. Preparação conferiu hashes.

Smoke sintético do próprio pacote: Central HTTP 200 em 1,344 s (uma abertura, não benchmark) e DOCX com modelo geométrico fictício gerado e relido com o texto esperado (`package-smoke.json`). Não houve instalação operacional. Abertura, RAM, busca e extração não foram apresentadas como mais rápidas: não há benchmark antes/depois pertinente concluído; o tempo das suítes não é benchmark do produto.

## Estado dos requisitos e próximos passos

- CL-R01: inventário/baseline produzidos; revisão final pendente.
- CL-R02/CL-R03: implementados; suíte integral e pacote final no SHA commitado pendentes.
- CL-R04: implementado e verificado nos testes focados; revisão independente pendente.
- CL-R05: preservado por não alteração dos mecanismos; verificações integrais pendentes.
- CL-R06: defeito de fixture implementado/verificado; demais falhas da rodada integral coerente por investigar.
- CL-R07: backend híbrido real executado no baseline; repetição no candidato e skips finais pendentes.
- CL-R08: contexto, tamanho de legado/pacote e smoke medidos; demais limitações declaradas.

Próxima ação: revisar diff, commitar lotes coesos, executar suíte integral num snapshot estável, investigar apenas falhas reproduzíveis, preparar candidato final e encaminhar autoria CL90 a outro agente. A revisão independente do candidato Codex/Antigravity e as cinco funcionalidades ainda não foram executadas; nenhuma homologação operacional é declarada.

## Verificação final do candidato CL90 — 0537ab8

SHA completo `0537ab87b81a6e09e23f8d5530335b36d5d261a8`, worktree limpo. Runner existente executado sem edições durante a rodada: **149/149 suítes aprovadas em 656,94 s**, incluindo `teste_central.py` isolado. Log: `D:/CPJ-DEV/cl90-artefatos/candidate-0537ab8-full.log`. O tempo é da suíte, não benchmark do produto.

Aprovados, entre outros: importação/extração Markdown e OCR; busca híbrida e fontes/páginas; DOCX; gates de finalização; recuperação/retomada/cancelamento e histórico; consentimento, orçamento e ausência de repetição externa incerta; preservação de vínculos/conferências em reindexação; isolamento entre casos; portáteis/adaptadores; distribuição e regressões de legado/dependências. LC01 repetiu no candidato sem skips.

**Não executados (8 testes, não aprovações):** 1 de link simbólico em UN16; 4 de links/alias em RV17; 2 de symlink em RP33; 1 ensaio físico SEC22 sem fixture de volume. Motivos: privilégio/recurso de SO. Nenhum comando de disco real ou contorno de permissão. CI27 focal permaneceu 6/6 com dublês.

Pacote final: `D:/CPJ-DEV/cl90-artefatos/pacote-final-0537ab8`; manifesto homónimo `.manifesto.json`. Revisão/árvore limpa no manifesto, 115 arquivos, 2.082.660 bytes e `procedimentos.json` presente. Scanner `--ref HEAD`: 565 arquivos, 0 achados proibidos. Smoke final (`final-package-smoke.json`): Central HTTP 200 em 1,312 s (uma abertura, não benchmark) e DOCX sintético válido. Não instalado.

## Revisão independente parcial de AG90 — não é candidato integrado

Revisão identificada: `58826f3814f7e2486edee7db9a2754c4502ebe75`, código de outro agente. Reexecutei `teste_interface_astra_ag90.py`: **10/10 em 28,311 s**, log `ag90-58826f3.log`. Abri as capturas novas de desktop/mobile, claro/escuro. Os cenários de mapa com resposta obsoleta, grafo/fonte, navegação, conferência lado a lado, eventos/filtros e notas foram reexecutados, não apenas lidos no relatório AG90.

Limite do parecer: o candidato Codex ainda tem CX90–CX99 ativos e não foi entregue integrado com AG90/CL90. Assim, as cinco funcionalidades aprovadas e o visual/mapa/grafo **não foram verificados no candidato integrado**. Em AG90 isolado, o teste de notas cobre acrescentar/excluir no DOM, mas não recarregar/reiniciar nem isolamento entre casos; persistência integrada continua por provar pelos testes do backend Codex. Capturas antigas não foram usadas como prova do candidato novo.

## Bloqueios, revisão da autoria e retomada

`CL91` foi registada na fila comum para outro agente revisar CL90 em `0537ab8`, reexecutar testes e gravar `revisoes/revisao-independente-cl91-2026-10-28.md`. Continua disponível; não há Codex/Claude CLI no PATH. Minha autoinspeção e os testes acima **não são revisão independente da minha autoria**.

Estado final: CL-R01–R08 implementados/produzidos e verificados no escopo CL90, com skips declarados. **Entrega parcial da missão total:** revisão independente de CL91 e revisão do candidato consolidado Codex/Antigravity bloqueadas por artefacto/agente ainda não disponível. Nenhuma homologação operacional.

Próxima ação copiável: `Assumir CL91 e revisar 7d910cc..0537ab8 no worktree D:/CPJ-DEV/cline-simplificacao-20261028; depois, quando Codex estabilizar o candidato integrado, identificar seu SHA e reexecutar as cinco funcionalidades, persistência/isolamento, mapa/grafo, suíte e pacote sem reutilizar este check como prova do novo SHA.`

Reversão local dos lotes, somente numa branch de desenvolvimento e após revisão: `git revert 0537ab8 a9cc04c 8756508`. Não executar sobre dados nem usar reset/limpeza. Eventual atualização operacional exige integração, CL91 aprovada, revisão independente do candidato final, backup/restauração e liberação final expressa; nada nesta entrega autoriza instalação, merge ou publicação.
