# Memória central — MM01 — 27/10/2026

Pedido do operador: memória compartilhada pelos agentes, com regras consistentes e aprendizado genérico seguro, sem transportar fatos entre casos. Execução reservada a Codex-MM01; candidato isolado `F:/CPJ-BACKUPS/sync-github-20261027-023944/candidato`. Nenhuma alteração operacional, provedor ativado, API real, publicação ou migração.

## Entrega

`MEMORIA.md` é o ponto de entrada lógico comum e remete às fontes autoritativas existentes: AGENTS.md, PRD.md, espinha dorsal, fila compartilhada, lições genéricas revisadas e procedimento da tarefa. Não cria banco ou outro repositório de fatos. CLAUDE.md e GEMINI.md são adaptadores curtos para a mesma entrada; removidas regras copiadas, descrições antigas de derivados e a alegação histórica de reservas L01/L02. Comandos úteis de procedimentos e fila foram preservados.

`plantao.montar_prompt` dirige os modos auto/chat/API à memória central, AGENTS.md e lições vivas. `executores_llm._instrucoes_locais` lê esses três arquivos do workspace antes dos portáteis/agentes/skills, deixando explícita a precedência das regras vigentes sobre snapshots antigos. A leitura acontece a cada nova montagem de instruções, sem cache global. Uma execução já iniciada conserva o prompt com que começou; não há injeção automática de mudanças no meio de uma rodada. O transporte Claude isolado existente já usa `_instrucoes_locais`, preservando ferramentas virtuais e isolamento.

O leitor usa a lista fixa de fontes e procedimentos previstos para a ação. Não percorre links Markdown nem varre pastas do caso/configuração. Links simbólicos e junções nos caminhos dessas fontes são bloqueados. Fonte ausente ou bloqueada aparece como aviso explícito no prompt. O prompt adicional configurado pelo investigador permanece sob o fluxo existente; a alteração não remove ativação, consentimento, orçamento ou restrições de ferramentas.

## Aprendizado e aprovação

As lições globais continuam exclusivamente em `calibracao/licoes-aprendidas.md`, genéricas e revisadas. A memória exige registrar data, origem da determinação, aprovação/responsável e evidência ao modificar regras/lições na fonte apropriada. Descoberta de agente é proposta até aprovação; hipótese de caso não vira regra. Nenhum histórico de autos, identificador, nome, valor, credencial ou conteúdo de caso foi incorporado aos documentos novos. A lição existente não foi reescrita nesta tarefa. A ligação em AGENTS/PRD e a atualização dos portáteis ficam com o coordenador.

## Complemento de coordenação do operador

Na mesma sessão, o operador determinou coordenador sempre presente, executores de igual ou menor hierarquia/capacidade, preferência Astra na orquestração e Sol/Terra/Luna na execução, com escolha do menor custo compatível com eficiência e acerto. A regra foi incorporada na memória e referenciada pelos adaptadores; distribuição/integração/validação, escala de incerteza e revisão independente permanecem sob coordenação. O complemento é documental: não altera o runtime, não ativa provedor, não dispara chamada paga nem cria sistema/skill/auditor concorrente. AGENTS/PRD/espinha recebem o complemento pelo coordenador.

## Evidência TDD e regressões

RED: `teste_memoria_mm01.py` falhou em dois cenários antes do produto: CLI não mencionava MEMORIA.md e API não carregava memória/lições vivas. Os outros dois cenários já preservavam a ausência de varredura; passaram a exercer a leitura nova no GREEN, inclusive junção real para um caso fictício.

GREEN: memória MM01 4/4; isolamento SEC22 6/6; consentimento seguro SE01 7/7; orçamento 19/19. Total 36 unittest aprovados, zero skips nessa seleção. `teste_plantao_claude.py` D01 TUDO OK, com agentes/processos simulados. Testes não chamaram API nem IA real. Fixtures em TEMP; `config_ia` foi substituído por fixture no teste MM01, sem leitura de configuração operacional. AST dos arquivos alterados e `git diff --check` restrito a MM01 aprovados.

Runtime: Python 3.12.14 empacotado do perfil atual, com `PYTHONPATH` temporário apontando às bibliotecas da instalação e `PYTHONDONTWRITEBYTECODE=1`; o executável da .venv original referencia perfil antigo e não foi alterado. Nenhum full executado; gate integrado é responsabilidade do coordenador após congelamento.

## Revisão de segurança e limites

Conferidos sigilo, separação memória/caso, fonte única, precedência, autorização e aprovação de lições nos três documentos. A memória não concede acesso extra ao modelo nem certifica que qualquer conta/provedor atende ao sigilo institucional. A classificação do conteúdo nos arquivos de governança continua sob responsabilidade dos mantenedores: não existe detector automático capaz de garantir ausência de dados pessoais se alguém os inserir indevidamente nas fontes canônicas. A validação de links/junções cobre o estado observado na leitura; não é sandbox contra usuário que controla a mesma conta e troca caminhos concorrentemente. Nenhum novo auditor, indicador percentual ou mecanismo de aprendizagem automática foi criado.

## Complemento de distribuição MM01

A revisão complementar encontrou três lacunas reproduzidas antes do patch: `testar-tudo.py` não levava MEMORIA.md para a raiz da sandbox; o pacote genérico não a listava; os adaptadores gerados do Codex não dirigiam à entrada comum. Foram incluídos três testes reais de clonagem em árvore sintética, preparo/cópia e manifesto do pacote, e geração dos adaptadores do projeto/usuário em TEMP. RED: 2 falhas e 1 erro por ausência da memória; GREEN: MM01 7/7, sem skips. Regressão de higiene SZ01 1/1 aprovada. A geração preserva a autorização vigente de AGENTS.md, removendo proibições genéricas antigas do adaptador que divergiam da autorização expressa do operador.

O pacote contém MEMORIA.md na raiz como snapshot de distribuição com hash, nunca dentro de cada skill/agente. Esse snapshot não substitui a fonte autoritativa no workspace: executores continuam lendo ws/MEMORIA.md, ws/AGENTS.md e as lições vivas; o pacote de plugin não instala nem migra o workspace operacional ou suas lições. Pacotes de workspaces legados que não possuam MEMORIA.md continuam possíveis; a ausência não é ocultada pelo runtime, que inclui aviso ao montar as instruções.

Foi lida somente a revisão `revisoes/auditor-relatorio-2026-10-27.md` de AU01: os critérios adicionados preservam revisão independente e a linha Resultado, sem percentual fictício de certeza, novo auditor, nova chamada de IA ou diligência automática. Nenhuma divergência documental com a memória central foi identificada nessa leitura; eficácia não foi medida.

Adaptadores `.agents/skills/cpj-*/SKILL.md` regenerados somente no candidato: 12 arquivos atualizados pelo gerador, sem instalação pessoal. Rodada UN16 completa de 18 cenários: 15 aprovados, um skip ambiental por privilégio de link simbólico, duas falhas em portáteis que o coordenador ainda estava regenerando (conteúdo desatualizado e regras vigentes não propagadas). As verificações de pacote e dos adaptadores passaram; essa rodada não declara o gate geral aprovado. Repetição após regeneração de portáteis fica com o coordenador.

## Resolução posterior do achado AV01 — MM01 — 27/10/2026

O achado histórico acima foi preservado. Por determinação do coordenador, `plantao.montar_prompt` passou a limitar a autonomia sem perguntas às decisões rotineiras e a declarar que os bloqueios de AGENTS.md prevalecem. Sem O.S. vigente localizada ou com extração incompleta, o prompt manda não redigir o relatório, registrar a lacuna e avisar o operador antes da redação; placeholders não contornam bloqueios. A mudança não acrescenta um novo gate nem altera a classificação de fato/inferência. TDD: novo cenário falhou no prompt anterior; GREEN MM01 8/8 e consentimento seguro SE01 7/7 aprovados, sem skips. O cenário cobre quatro ações e três modos de prompt, com dados fictícios, sem IA real. A validação é do contrato de instruções, não demonstra cumprimento semântico por uma chamada de IA real.

Na mesma revisão, a descrição gerada de `cpj-processar-ip` deixou de anunciar tabelas/entidades para novos PDFs: passou a descrever Markdown por página/O.S. e checkpoint essencial, preservando MD/CSV legados. O teste do gerador reproduziu o texto antigo em RED e passou após a atualização. Adaptador regenerado no candidato, sem instalação pessoal.
