# Verificação do projeto pela Oficina de Software — 15/10/2026

Tarefa OF01 · Codex-Oficina-20261015 · Revisão do estado local, sem correção do código.

## Resultado

O projeto possui requisitos, arquitetura documentada, governança de trabalho, procedimentos e testes. A ausência de uso anterior da Oficina de Software não exige refazer essas etapas. A revisão identificou três falhas reproduzíveis: a entrega aceita DOCX divergente ou vazio; o editor pode converter IP local em IPe; e a importação de `.xls` depende de biblioteca ausente dos manifests e do ambiente atual.

## Alinhamento confirmado com o operador

Respostas diretas de 15/10/2026: o resultado principal é **produzir relatórios com menos trabalho manual**. A elaboração deve ser criteriosa e refletir os autos; a dificuldade atual mais relevante é **análise superficial ou conclusões mal sustentadas**. A experiência desejada é **automação até a minuta, com revisão humana ao final, no Word e por conferência com o PDF original**. Quando houver dado essencial ausente, ilegível ou contraditório, o fluxo deve **produzir a minuta com alertas e pendências explícitas**, preservando as regras obrigatórias de fontes e de localização da O.S.

Essas respostas confirmam a prioridade do fluxo existente e orientam sua avaliação. Não autorizam fatos por dedução, fechamento de lacunas com conteúdo inventado ou apresentação de conclusão incerta como comprovada. As paradas já obrigatórias, como ausência da O.S. antes de redigir, permanecem aplicáveis.

Critérios de aceite para a próxima etapa: a minuta responde a cada determinação da O.S.; afirmações e conclusões materiais têm fontes localizáveis e distinguem fato, relato, indício e hipótese; a análise confronta contradições e explicita limites, sem equiparar titularidade de conta a autoria; valores e identificadores são conferidos; dados essenciais não resolvidos aparecem como alerta e ressalva, sem impedir a minuta quando as regras permitirem; a revisão humana final permite conferir o conteúdo que será efetivamente entregue em DOCX. A profundidade deve ser avaliada com cenários fictícios que tenham respostas e limitações esperadas, além dos testes de funcionamento.

## Lacunas em relação ao objetivo alinhado

Os agentes de produto e experiência mapearam o fluxo existente em leitura, e o coordenador conferiu os trechos centrais. Já existe O.S./PDF → extração → análise financeira/documental → consolidação → redação → revisão → ajuste → DOCX. A “Esteira Completa 1-Clique” está na ficha em [index.html:1160](<D:/CPJ - TRABALHO/plugin/investigacao-cpj/app/static/index.html:1160>). Não é necessário inventar outra capacidade de automação para atender à preferência informada.

1. **O contrato estrutural não demonstra profundidade da análise.** [plantao.py:626](<D:/CPJ - TRABALHO/plugin/investigacao-cpj/app/plantao.py:626>) exige saídas existentes, não vazias e modificadas. Os prompts pedem fontes, resposta à O.S. e revisão independente, mas arquivo preenchido não demonstra que uma conclusão esteja bem sustentada. Trata-se de limite de validação confirmado, não de prova de erro em toda minuta. **Aceite:** um ensaio fictício deve reprovar conclusões sem suporte e omissões materiais deliberadamente introduzidas, mesmo quando todos os arquivos existirem.

2. **A revisão independente antecede o último ajuste.** [plantao.py:206](<D:/CPJ - TRABALHO/plugin/investigacao-cpj/app/plantao.py:206>) programa redação, revisão independente e ajuste; o plano termina após o ajuste. O revisor é instruído a não alterar a minuta; o ajuste altera a mesma versão e sua rastreabilidade. Não há etapa independente posterior prevista nesse plano. Isso limita a evidência de revisão do texto efetivamente apresentado ao investigador. **Aceite:** confrontar a versão ajustada com os achados anteriores e as fontes, mantendo visíveis os pontos não resolvidos. A revisão humana final permanece necessária.

3. **Qualidade em volume representativo ainda precisa ser demonstrada.** O piloto registrado usa fonte fictícia curta e requereu correções, enquanto o volume de referência do PRD é 100–300 páginas. **Aceite:** avaliar caso fictício representativo com solicitações, valores, contradições e limites conhecidos; medir cobertura dos itens materiais e sustentação das conclusões. A revisão atual não executou inferência nem esse novo ensaio.

Na experiência, o editor da Central usa campos de texto ([index.html:1332](<D:/CPJ - TRABALHO/plugin/investigacao-cpj/app/static/index.html:1332>)) e o caminho de FINAL apresenta achados por código/linha ([index.html:1239](<D:/CPJ - TRABALHO/plugin/investigacao-cpj/app/static/index.html:1239>)). Os agentes levantaram a navegação manual para conferir fontes como possível atrito; seu impacto não foi medido. Como o operador confirmou preferência por **Word + PDF original**, esta revisão não transforma uma nova interface de revisão na Central em requisito. A prioridade é a qualidade e rastreabilidade da minuta e a consistência do DOCX final, inclusive após edição no Word.

## Achados confirmados, por impacto

### 1. P1 — O FINAL pode divergir da minuta conferida ou estar vazio

**Condição:** existe uma minuta aprovada e um arquivo com extensão `.docx` da mesma versão, mas o conteúdo do Word foi alterado ou o arquivo ficou vazio.

**Evidência:** [relatorios.py:367](<D:/CPJ - TRABALHO/plugin/investigacao-cpj/app/rotas/relatorios.py:367>) verifica extensão e existência. A conferência chamada na linha 414 recebe a minuta Markdown; na linha 430 o DOCX é copiado para FINAL. A falha de leitura do Word é ignorada nas linhas 432–439, e a linha 440 registra a entrega. O hash conferido identifica o Markdown, sem estabelecer correspondência com o conteúdo entregue em Word.

**Reprodução isolada:** reutilizados `GateCentralV05`, `LIMPA`, transcrição e relatório de extração fictícios de [teste_gate_central_v05.py](<D:/CPJ - TRABALHO/plugin/investigacao-cpj/app/testes/teste_gate_central_v05.py>). O conferidor real foi executado; somente a indexação posterior foi substituída por função sem efeito. Na primeira execução o DOCX foi substituído por documento válido com valor fictício `R$ 9.999,99`, ausente da transcrição. Resultado: HTTP 200, estado `entregue`, baixa registrada e FINAL com 36.633 bytes. Na segunda, o DOCX foi substituído por zero bytes: HTTP 200, estado `entregue`, baixa registrada, FINAL com zero bytes e ausência do FINAL.md. A reprodução final terminou sem erro.

**Consequência:** o gate pode aprovar a entrega de conteúdo que não examinou; um relatório ilegível também entra na produção como entregue. O RF09 não é cumprido no cenário vazio, pois o FINAL.md não é gerado.

**Correção indicada, não executada:** validar o DOCX antes da cópia e da baixa, propagar falha de leitura e conferir a correspondência do artefato entregue com o conteúdo revisado. Edições manuais no Word precisam ser contempladas nesse vínculo. Regressões devem cobrir DOCX vazio, inválido e divergente.

### 2. P1 — O cabeçalho pode apresentar IP local como IPe

**Condição:** o cadastro contém `inquerito` com número identificado como IP, ou contém simultaneamente `inquerito` e `ipe` diferentes.

**Evidência:** [relatorios.py:101](<D:/CPJ - TRABALHO/plugin/investigacao-cpj/app/rotas/relatorios.py:101>) prioriza `inquerito` sobre `ipe`; o tratamento seguinte remove rótulos como `IP` e `Inquérito Policial` e monta a referência com o rótulo `IPe`. O cadastro apresenta o campo genérico “Inquérito Policial” em [index.html:277](<D:/CPJ - TRABALHO/plugin/investigacao-cpj/app/static/index.html:277>).

**Reprodução isolada:** reutilizados os helpers de [teste_minuta_campos_rv07.py](<D:/CPJ - TRABALHO/plugin/investigacao-cpj/app/testes/teste_minuta_campos_rv07.py>). Cadastro `inquerito = "IP nº 123/2099"` e processo fictício produziu `IPe nº 123/2099 / Processo nº 0001234-56.2099.8.26.0000`. Acrescentar `ipe = "999999/2099"` manteve a mesma referência errada. Execução encerrada sem erro.

**Consequência:** o cabeçalho pode violar a regra 15 de AGENTS.md. Trocar o rótulo não demonstra que o identificador seja de um inquérito eletrônico.

**Correção indicada, não executada:** distinguir a origem e o tipo do identificador; usar o IPe confirmado e deixar pendência quando só houver IP local. Preservar a compatibilidade com cadastros existentes sem reclassificar números por dedução. Regressões devem incluir IP local, IPe explícito e ambos diferentes.

### 3. P2 — Importação de `.xls` anunciada sem dependência necessária

**Condição:** o operador envia planilha Excel no formato antigo `.xls`.

**Evidência:** RF13 anuncia esse formato; a interface o aceita em [index.html:500](<D:/CPJ - TRABALHO/plugin/investigacao-cpj/app/static/index.html:500>). [consulta.py:198](<D:/CPJ - TRABALHO/plugin/investigacao-cpj/skills/base-cpj/scripts/consulta.py:198>) importa `xlrd`, usado pelo ramo `.xls` na linha 305. A biblioteca não consta em `requirements.txt`, `requirements-dev.txt` ou `requirements-opcional.txt` e não está instalada na `.venv` atual.

**Reprodução isolada:** executar o gerador `consulta.tabelas_xls()` em workspace temporário produz `ModuleNotFoundError: No module named 'xlrd'`, antes mesmo da abertura do arquivo. A pesquisa dos testes existentes encontrou o ensaio de importação HTTP com `.xlsx`, sem exercício funcional de `.xls`.

**Consequência:** o formato oferecido falha neste ambiente e não é assegurado pela instalação declarada. `pip check` passa porque verifica dependências declaradas dos pacotes instalados, não todos os imports do código do projeto.

**Correção indicada, não executada:** declarar a dependência do formato mantido no RF13 e verificar uma importação real de `.xls` fictício, além de instalar a dependência no ambiente operacional na etapa de correção.

## Conferência das etapas da Oficina

| Etapa | Evidência e avaliação |
|---|---|
| Necessidade e requisitos | PRD §§1–4 define usuário, volume e RF01–RF24. O foco atual é operação solo e o fluxo PDF → extração → análise → DOCX. Não foi identificada necessidade de reabrir essas decisões. |
| Arquitetura | PRD §§5–7 e ADR-001 documentam arquivos, Python/Flask e SQLite. `caso.json` é fonte do caso; os índices são derivados. Não foi encontrado import do módulo PostgreSQL nos pontos de entrada e rotas examinados. Experimentos locais não comprovam migração do sistema. |
| Dados e rastreabilidade | O modelo está documentado no PRD §6; procedimentos e gates existem. Os achados 1 e 2 mostram limites concretos que a existência da documentação não elimina. Não foram examinados dados reais. |
| Interface | Há interface e testes automatizados; a integração HTTP isolada passou, mas o E2E visual F03 foi pulado na preparação do navegador. Esta rodada não certifica o fluxo visual completo nem acessibilidade ou uso real. |
| Implementação e manutenção | A análise sintática de 130 arquivos Python em `app`, `skills` e `ferramentas` não encontrou erro de sintaxe nem arquivo vazio. Isso não certifica os scripts experimentais da raiz nem todo comportamento em execução. |
| Testes e entrega | Runner retornou 1: 78/79 suítes aprovadas segundo seu resumo, com uma falha de comparação de tempo e cinco verificações internas puladas. As reproduções adicionais demonstram lacunas específicas que as aprovações existentes não cobrem. |
| Continuidade | Fila, PRD, ADR e revisão estão presentes. Mudanças locais anteriores à revisão foram preservadas. Commit, push, instalação e publicação não foram executados. |

## Verificações e limitações

- `.\.venv\Scripts\python.exe -m pip check`: retorno zero, sem dependências declaradas quebradas.
- `.\.venv\Scripts\python.exe ferramentas\configurar-codex.py --verificar`: retorno zero; 12 skills CPJ, sem divergências dos arquivos gerados. A mensagem “arquivos conferidos: 0” é fixa no modo de verificação; o código compara os 24 arquivos esperados.
- Análise com `ast.parse` dos 130 arquivos Python listados por `rg --files` nas três pastas de código: zero erros de sintaxe e zero arquivos vazios.
- Reproduções dos achados 1 e 2: fixtures fictícias, processos locais e temporários; conferidor real no achado 1. Nenhuma inferência de IA ou chamada a provedor.
- Duas execuções preparatórias do harness do achado 1 falharam no preparo/encerramento do mock e na ordem do import; esses erros do harness foram resolvidos antes da reprodução final sem erro. Não foram tratados como falhas do sistema.
- Suíte completa: `.\.venv\Scripts\python.exe -X utf8 ferramentas/testar-tudo.py`, com APPDATA/LOCALAPPDATA, perfis e temporários fictícios, `CPJ_SEM_AGENTE_EMBUTIDO=1` e `PYTHONDONTWRITEBYTECODE=1`. **Retorno 1; 78/79 suítes aprovadas no resumo do runner; soma 732,33 s; duração real 1.001,65 s.** Não houve repetição para substituir esse resultado.
- Falha em [teste_ocr_checkpoint_claude.py:96](<D:/CPJ - TRABALHO/plugin/investigacao-cpj/app/testes/teste_ocr_checkpoint_claude.py:96>): a retomada levou 2,6 s e a primeira execução 2,5 s, contrariando `t_rep < t_cheio`. Reaproveitamento das quatro páginas, igualdade da transcrição/CSV, recuperação de interrupção, invalidação e prioridade da transcrição visual passaram. O resultado observado é uma falha na comparação de desempenho; a causa da diferença de tempo não foi estabelecida nesta revisão.
- Cinco skips internos em duas suítes: `teste_e2e_f03.py` pulou a preparação da classe, impedindo seu fluxo visual; o runner preservou somente `OK (skipped=1)`, sem motivo exato. Quatro testes de `teste_executores_rv17.py` foram pulados por ausência de permissão para links simbólicos (aliases de leitura/escrita, geração DOCX por link e listagem de arquivos permitidos). Essas verificações não estão certificadas.
- A integração HTTP `teste_central.py` passou em 46,78 s. Relatos parciais de aprovação do OCR e do E2E foram corrigidos após a conferência do fechamento completo.
- [Log completo da suíte](<C:/Users/alan_/AppData/Local/Temp/cpj-review-6da2a9125e534f9da4095a37573df550/suite.log>) preservado em pasta temporária; o resultado consolidado está neste relatório.
- Não foram lidos autos, bases operacionais, credenciais ou configurações reais; produção não foi iniciada. Acervo externo e GitHub não foram auditados nesta rodada.
- Piloto de IA com volume representativo de 100–300 páginas e início após login/reinício do Windows permanecem sem certificação nesta revisão. O piloto curto registrado no PRD não supre essas verificações.
- Foram encontradas e reconciliadas no PRD duas divergências documentais: RF22 dizia “P01 pendente”, embora §9 registrasse conclusão; a árvore de arquitetura mencionava plugin 0.3.2, enquanto o manifesto fonte é 0.3.3. Isso não comprova defeito adicional de execução nem certifica a versão instalada atual.

## Prioridade para a etapa de correção

Corrigir a validação do artefato FINAL e a origem do IPe, que afetam a confiabilidade da entrega. Na prioridade confirmada pelo operador, conferir a versão após os ajustes e avaliar profundidade/sustentação com os critérios e cenários acima, preservando a revisão em Word + PDF. Completar a dependência e o teste de `.xls`; investigar a falha de tempo sem descartar as verificações funcionais aprovadas e recuperar o E2E visual em sandbox. As correções do sistema não foram executadas nesta revisão.
