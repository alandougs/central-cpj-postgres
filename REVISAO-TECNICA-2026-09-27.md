# Revisão técnica da Central CPJ — 27/09/2026

## Parecer

O projeto tem um núcleo funcional e uma arquitetura adequada ao volume previsto: Python, Flask, arquivos por caso, extração local e SQLite FTS5. A prioridade é estabilizar o que existe, completar a interface e eliminar resultados incorretos antes de ampliar as funcionalidades. Ainda não considero a versão atual validada para operação integral com múltiplos usuários.

Esta revisão não alterou o código funcional nem acessou autos reais. Foram inspecionados PRD, instruções, servidor, autenticação, tarefas, interface, scripts de casos, busca, indexação, consulta, extração, DOCX e backup. A interface foi revisada pelo código; não foi feito ensaio visual no navegador.

## Evidência de execução

- A suíte existente `plugin/investigacao-cpj/app/testes/teste_central.py` foi executada em workspace temporário, servidor HTTP em loopback e dados inteiramente fictícios: **52 verificações OK, retorno 0**.
- O provedor de IA foi substituído no teste por um estado desconectado. Portanto, a aprovação da suíte não valida análise/redação por IA, consumo, disponibilidade de conta nem isolamento de rede.
- O PDF desta revisão continha texto nativo. A execução não revalidou o OCR de 230 páginas citado historicamente no PRD.
- Testes adicionais isolados reproduziram as falhas descritas abaixo. A troca obrigatória de senha temporária passou no teste focado: acesso bloqueado com 428, troca com 200 e acesso posterior com 200.
- O PRD registra 54/54 de uma sessão anterior. Esse registro histórico não corresponde à contagem de verificações aprovadas nesta execução e não cobre as falhas adicionais encontradas.

## O que já foi feito

| Área | Situação observada |
|---|---|
| Cadastro de O.S. | Cadastro, upload, prazo, determinação, prioridade, responsável e filtros implementados; fluxo básico passou na suíte. |
| Documentos | Originais separados, hash, extração de texto, OCR, CSV, entidades, progresso, fila e retomada de documentos implementados. Extração de PDF nativo passou; OCR extenso não revalidado. |
| Acesso | Login, perfis, matriz editável, auditoria, bloqueio por tentativas e troca de senha implementados; testes básicos passaram. Existem falhas de autorização e sessão. |
| Central v2 | Interface de login, início, casos, pesquisa, estatísticas e sistema já existe. A instrução antiga de “reescrever toda a interface” no PRD está desatualizada. |
| Relatório | Editor de minuta, versão, geração DOCX, definição de FINAL, baixa e cópia para pasta do cadastrante implementados; fluxo passou na suíte. Qualidade visual do DOCX não foi avaliada nesta revisão. |
| Busca | FTS5, identificadores, pessoas, referências e cruzamentos implementados; busca básica passou. Novos vínculos exigem correção de identidade. |
| Consultas | Excel, CSV, Word e referências testados pela suíte; PDF, TXT, texto colado e novos filtros existem no backend, mas precisam de interface e testes adicionais. |
| Produção | Entregas, metas, prazos e versões estão no código. Indicador de entregas no prazo já está no painel. |
| Transporte de dados | Exportação com manifesto/hash e importação sem sobrescrever casos existentes passaram no fluxo básico; cancelamento, escopo e recuperação da importação precisam de correção. |
| IA automática | Executor Claude, fila, logs, marcos e pós-processamento implementados. Execução real do agente não validada nesta revisão. |
| Codex | Onze skills do projeto e uma entrada pessoal instaladas e descobertas nesta sessão. Os adaptadores preservam os procedimentos originais. |
| Manutenção | Scripts de diagnóstico, backup, publicação e atualização existem. Manifesto do plugin permanece em `0.2.0`. |

## Falhas prioritárias

### 1. Alta — cadastro de O.S. contorna a autorização de edição

**Reproduzido:** um escrivão B recebe HTTP 403 ao editar diretamente uma O.S. criada pelo escrivão A, mas consegue alterar sua determinação com HTTP 200 reenviando o mesmo número para `/api/os`.

**Origem:** `app/servidor.py:534` aplica a regra de autoria/perfil na edição; o ramo de caso existente em `app/servidor.py:563` não aplica a mesma regra.

**Correção proposta:** centralizar a autorização de modificar uma O.S. e usá-la tanto no cadastro repetido quanto na edição e no acréscimo de documentos. Testar a mesma operação por todas as rotas.

### 2. Alta — grafo mistura homônimos e identificadores financeiros

**Reproduzido:** dois registros fictícios de mesmo nome e CPFs diferentes produziram um único nó PESSOA conectado aos dois CPFs.

**Origem:** `skills/base-cpj/scripts/indexar.py:302` define a identidade da pessoa pelo nome normalizado. A busca de vínculos em `rag.py:163` percorre esse nó já fundido.

**Também observado no código:** contas são normalizadas apenas por dígitos, sem banco; no fluxo financeiro, uma chave Pix usada como alternativa à conta ainda recebe o tipo CONTA (`indexar.py:341`). Isso pode unir contas de bancos diferentes ou perder vínculos entre tipos.

**Correção proposta:** cada pessoa deve ter identidade de registro e fonte; CPF confirmado pode apoiar a vinculação, mas nome sozinho deve gerar candidato a conferir. Conta precisa de banco, agência e conta; chave Pix conserva seu próprio tipo. Preservar documento e página em cada vínculo. O grafo visual deve vir depois dessa correção.

### 3. Alta — negações viram presença de mandado ou cautelar

**Reproduzido:** um registro com “Sem mandado de prisão” e “Sem medida cautelar” foi retornado pelos dois filtros positivos.

**Origem:** `consulta.py:72` identifica palavras sem interpretar negação; `indexar.py:301` marca presença apenas por campo não vazio. Uma planilha com uma coluna preenchida como “Não” também exige tratamento explícito.

**Correção proposta:** separar trecho original de estado interpretado: confirmado, negado, histórico e indeterminado. Manter data/fonte e exigir revisão antes de tratar menção como situação atual. Não inferir vigência de um mandado a partir da existência de texto.

### 4. Alta — importação tem cancelamento e escopo incompletos

**Reproduzido:** uma tarefa marcada como cancelada continuou importando um arquivo. O mesmo ensaio mostrou que o importador aceita um caminho interno ao workspace fora das pastas de dados exportadas.

**Origem:** `app/tarefas.py:131` verifica hash e contenção na raiz, mas não limita os diretórios ao formato esperado. O laço de cópia não observa cancelamento. `cancelar()` muda o estado, mas só interrompe processos externos registrados.

**Risco adicional observado:** erro ou interrupção no meio da cópia pode deixar um caso parcial; a importação seguinte pula a pasta por ela já existir.

**Correção proposta:** permitir somente raízes e tipos definidos pelo esquema; validar todo o manifesto antes da escrita; extrair em área temporária; confirmar o caso completo de forma atômica; conferir cancelamento entre blocos. Adicionar limites de quantidade e tamanho descompactado. O hash verifica consistência, não a procedência ou segurança do pacote.

### 5. Alta — falha de indexação pode aparecer como sucesso

**Reproduzido com falha simulada:** o subprocesso do indexador retornou código 1 e `Tarefas.indexar()` retornou normalmente.

**Origem:** `app/tarefas.py:76` descarta o código de saída. Algumas rotas também disparam indexação em threads ou subprocessos sem propagar seu resultado.

**Correção proposta:** verificar retorno, registrar erro e exibir claramente “arquivo importado; indexação pendente/falhou”. Usar uma fila única de escrita no índice, combinar pedidos redundantes e possibilitar nova tentativa.

### 6. Média — redefinir senha não revoga sessões existentes

**Reproduzido:** após redefinir a senha pelo administrador, o cookie da sessão anterior continuou acessando `/api/casos` com HTTP 200.

**Origem:** `servidor.py:105` consulta apenas o login da sessão; `auth.py` não mantém uma versão de sessão/senha comparada a cada acesso.

**Correção proposta:** incrementar uma versão de autenticação ao redefinir senha e invalidar os cookies anteriores. Testar redefinição, desativação, reativação e remoção de conta.

### 7. Alta antes de uso simultâneo — gravações não protegem a operação completa

**Constatação por leitura, sem teste de carga:** `caso.py:65` usa um único nome temporário por caso e não trava a sequência de leitura, alteração e gravação entre processos. O servidor usa threads; OCR, indexador e IA também podem alterar o mesmo caso. A criação de versão da minuta em `servidor.py:703` calcula a próxima versão antes de gravar, sem reserva exclusiva.

**Consequência possível:** perda de alterações por gravação de estado antigo, colisão de `.tmp` ou duas minutas com o mesmo número. Escrita atômica de um arquivo não resolve atualização concorrente.

**Correção proposta:** transação por caso com trava entre processos, arquivo temporário exclusivo e revisão esperada no salvamento. Rejeitar edição sobre versão antiga com mensagem útil. Preservar `caso.json` como fonte da verdade conforme o PRD.

### 8. Decisão arquitetural pendente — IA automática e regra de processamento local

O executor em `tarefas.py:283` usa Claude CLI e proíbe WebFetch/WebSearch e MCP. O código não apresenta um provedor de inferência local nem isolamento de rede do processo Python autorizado. Portanto, essas flags não demonstram cumprimento da premissa de que conteúdo de autos não é enviado a serviço externo.

**Encaminhamento:** definir e documentar o ambiente permitido antes de validar o fluxo com material real. Se processamento estritamente local for requisito, implementar um provedor local e restrições técnicas coerentes. O teste desta revisão manteve a IA externa desligada.

## O que falta concluir

1. Completar os campos de usuários: CPF, e-mail, cargo e senha temporária; edição dos dados da própria conta.
2. Liberar PDF/TXT e texto colado na tela de bases de consulta. O backend já aceita; `index.html:161` ainda limita a seleção aos formatos antigos.
3. Acrescentar filtros de processo/BO/placa e apresentação de antecedentes com estado/fonte. Integrar vínculos após corrigir a identidade dos nós.
4. Validar os novos recursos de autenticação, consultas e vínculos com casos negativos, não apenas exemplos bem formados.
5. Validar a execução real de análise → revisão → DOCX com caso fictício, no provedor aprovado, incluindo interrupção e retomada.
6. Atualizar as skills originais para gerar `pessoas.csv` de forma consistente em execução interativa e automática; sincronizar os procedimentos portáteis.
7. Consolidar o PRD: atualizar a tabela RF, remover pendências já concluídas, separar histórico de estado atual e vincular cada requisito ao teste correspondente.
8. Preparar a versão de entrega do plugin após estabilização. Publicação no GitHub não é requisito para funcionamento local.
9. Completar a recuperação do sistema: o backup de `ferramentas/backup.ps1` cobre apenas casos, calibração, produção e modelos. Faltam consultas, referências, configuração de usuários/perfis e pastas pessoais, conforme o objetivo de restauração. Configuração sensível deve permanecer em backup local protegido e fora do Git.
10. Corrigir a portabilidade do DOCX: `gerar_docx.py:40` usa modelo absoluto em `C:\CPJ - TRABALHO`; `tarefas.gerar_docx()` não passa `--modelo` do workspace recebido.

## Melhorias para ficar rápido

| Mudança | Evidência atual | Benefício esperado |
|---|---|---|
| Guardar em cache o diagnóstico do OCR | `/api/fila`, linha 647, chama Tesseract; a interface atualiza em ciclo de 1,6 s. | Eliminar criação recorrente de processo durante navegação. |
| Servir o painel pronto e atualizar após alterações | `/painel`, linha 978, executa indexador e gerador antes de responder. | Abrir estatísticas sem aguardar reconstrução de dados. |
| Indexar somente fontes alteradas | Texto tem hash, mas entidades são refeitas e pessoas/arestas são descartadas e reconstruídas em cada execução. | Reduzir trabalho proporcional ao acervo inteiro e competição entre escritores. |
| Gravar checkpoints do OCR por página | `extrair.py` mantém páginas em memória e escreve a transcrição no final. Retomar documento repete páginas. | Recuperar queda sem refazer o documento inteiro. |
| Evitar duas execuções OCR equivalentes por página | `extrair.py:53` usa `image_to_data` e depois `image_to_string`. | Reduzir trabalho do Tesseract; preservar ordenação e validar qualidade antes de substituir. |
| Atualização adaptativa da interface | Ciclo fixo de tarefas e nova consulta de tarefas no painel de IA. | Reutilizar a resposta, pausar aba oculta e diminuir frequência sem trabalho ativo. |
| Paginar e filtrar no servidor | Lista de casos e fila percorrem os casos e arquivos repetidamente. | Manter resposta previsível conforme o acervo cresce. |
| Reutilizar hashes conhecidos dos originais | Upload recalcula hash de cada original para cada novo arquivo. | Evitar reler PDFs antigos em cada lote. |

Não foi feito benchmark de desempenho. Esses ganhos são hipóteses fundamentadas no código. Medir antes/depois com 100, 500 e 1.000 casos fictícios, documentos de 100–300 páginas e múltiplos usuários. Metas iniciais propostas: buscas/listas comuns com p95 abaixo de 1 s na máquina-alvo; abertura do painel sem indexação; retomada sem repetir páginas concluídas. Tempos de OCR dependem da máquina e da qualidade dos documentos.

## Melhorias para ficar fácil e eficiente

- Na ficha, mostrar uma próxima ação principal conforme a etapa: conferir extração → analisar → revisar minuta → finalizar. Erro e pendência devem indicar o que fazer para resolver.
- Colocar documento-fonte e minuta lado a lado, abrindo a página citada. Priorizar a fila de dados críticos não conferidos.
- Salvar rascunho no servidor, indicar “salvo às…” e avisar antes de sair com alterações. A interface atual não tem tratamento de saída com texto não salvo. Evitar guardar autos em armazenamento do navegador por padrão.
- Separar “salvar rascunho”, “gerar DOCX” e “definir FINAL”; tornar o estado e a versão inequívocos. Manter a confirmação humana da entrega.
- Exibir qualidade da importação: registros reconhecidos, campos não mapeados, páginas sem leitura e candidatos a duplicidade, com correção antes de indexar.
- Apresentar a origem como autos, base de consulta ou referência em todo resultado, inclusive vínculos. Manter o clique para conferir a fonte.
- Oferecer diagnóstico inicial simples de Python, OCR português, modelo DOCX e provedor de IA; permitir repetir uma etapa que falhou sem refazer as concluídas.
- Tratar PDF automático e grafo visual como melhorias posteriores; o fluxo principal precisa funcionar bem sem eles.

## Melhorias de manutenção

- Separar as rotas Flask por área e retirar CSS/JavaScript do HTML monolítico, mantendo a stack simples. Não há necessidade demonstrada de reescrever em outro framework.
- Criar um inicializador de aplicação para testes sem efeitos de importação e um comando que gere fixtures, inicie o servidor isolado e execute a suíte. Hoje esses pré-requisitos são manuais.
- Registrar dependências e versões reproduzíveis; o levantamento do plugin não encontrou `requirements` ou `pyproject.toml`.
- Acrescentar testes de permissões equivalentes entre rotas, negações, homônimos, arquivos corrompidos, cancelamento, reinicialização, concorrência e restauração.
- Persistir tarefas e checkpoints; `Tarefas.t` fica apenas em memória. Retomada dos PDFs existe, mas o mesmo não está implementado para a fila de IA/importação/exportação.
- Padronizar erros e não ocultar exceções importantes. Exemplos: falha de indexação e extração do texto FINAL em `servidor.py:752`.
- Antes de uso por vários computadores, validar a execução contínua do servidor, HTTPS, restauração e volume simultâneo. O início atual usa `app.run(..., threaded=True)`.

## Ordem recomendada

1. **Confiabilidade:** corrigir permissão de O.S., identidade dos vínculos, negações, importação/cancelamento, erros de indexação e concorrência. Resolver o ambiente de IA permitido.
2. **Concluir o fluxo:** terminar campos/telas restantes, salvar rascunho com proteção contra perda, atualizar procedimentos e testar ponta a ponta.
3. **Velocidade:** cache de OCR, painel sem reconstrução síncrona, indexação incremental e checkpoints; medir em acervo fictício representativo.
4. **Entrega:** backup/restauração completo, instalação reproduzível, versão, PRD consolidado e piloto controlado.
5. **Evolução:** grafo visual, PDF opcional, busca semântica local e integrações adicionais somente quando houver necessidade demonstrada.

Critério de pronto: requisitos essenciais ligados a testes reproduzíveis, fluxo completo validado com dados fictícios, recuperação de falhas e backup ensaiados, resultados de pesquisa sem fusão indevida e provedor compatível com as regras do projeto. Quantidade de funcionalidades implementadas não substitui esses critérios.
