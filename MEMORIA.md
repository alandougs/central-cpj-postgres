# Memória central do workspace CPJ

A pausa de 27/10/2026 foi retomada por pedido expresso do operador na mesma data, no escopo da tarefa LC01 (fechamento das lacunas dos três requisitos — ver `revisoes/lacunas-2026-10-27.md`). Fora desse escopo o checkpoint ao final de `revisoes/sincronizacao-github-2026-10-27.md` continua valendo: a sincronização remota de SY05, a CI27 e a nova rodada integral da suíte seguem pendentes e exigem pedido expresso. Não tratar tarefa incompleta como concluída; confira o estado atual na fila, não em conversa anterior.

Atualizada em 27/10/2026. Entrada comum para Codex, Claude, Gemini, agentes locais e executores CLI/API. A memória é uma organização das fontes existentes, sem banco, serviço ou cópia por agente. Leia este arquivo ao iniciar e releia as fontes pertinentes antes de executar cada tarefa; uma conversa anterior não substitui o estado atual dos arquivos.

## Fontes canônicas

| Informação | Fonte viva | Quando ler |
|---|---|---|
| Regras operacionais, sigilo e determinações do investigador | [AGENTS.md](AGENTS.md) | Sempre, antes da tarefa |
| Requisitos e estado do sistema | [PRD.md](PRD.md) | Desenvolvimento/manutenção |
| Contratos e plano único de unificação | [docs/ESPINHA-DORSAL.md](docs/ESPINHA-DORSAL.md) | Desenvolvimento/manutenção |
| Reservas, andamento e evidências de entregas | [TAREFAS-COMPARTILHADAS.md](TAREFAS-COMPARTILHADAS.md) | Antes de editar e ao registrar resultados |
| Lições genéricas revisadas pelo investigador | [calibracao/licoes-aprendidas.md](calibracao/licoes-aprendidas.md) | Antes de analisar, redigir ou revisar |
| Procedimento da tarefa | Arquivo correspondente em `portatil/` ou skill viva do plugin | Após as regras vigentes |

Estas fontes continuam sendo autoritativas em suas responsabilidades. Não replique suas regras neste arquivo nem em adaptadores de cada agente. Em divergência, aplique a determinação explícita vigente do operador; regras específicas posteriores de AGENTS.md prevalecem sobre exemplos genéricos e snapshots antigos de procedimentos. Se persistir conflito material sem determinação que o resolva, registre o ponto e solicite orientação antes da ação dependente. A existência de plano, memória ou sugestão não autoriza implementar, instalar, publicar ou ativar provedor.

## Separação entre memória e caso

A memória compartilhada contém somente orientação genérica aprovada. Fatos, nomes, identificadores, valores, documentos, hipóteses e pendências de investigação continuam exclusivamente no caso/O.S. indicado. Não copiar autos, trechos de transcrição, credenciais, configurações privadas ou conteúdo de outros casos para esta memória, adaptadores, lições globais, fila pública ou GitHub. Uma lição não pode transportar uma hipótese de um caso para outro nem substituir a conferência dos autos e da O.S.

CLI: ler os arquivos vivos no workspace autorizado. API: carregar somente MEMORIA.md, AGENTS.md e lições genéricas antes dos procedimentos previstos para a ação. Não percorrer links Markdown automaticamente, varrer casos/configurações ou resolver fontes de memória por links/junções. A memória não ativa provedores nem altera o consentimento, orçamento, isolamento e ferramentas permitidas. O prompt adicional configurado pelo investigador continua sob os controles existentes.

## Coordenação e escolha de executores

Determinação do operador em 27/10/2026: todo trabalho tem um agente coordenador responsável por delimitar escopos, distribuir tarefas quando houver delegação autorizada, integrar resultados e validar a entrega. Executores podem ter a mesma hierarquia/capacidade do coordenador ou menor. A preferência é Astra na orquestração; Sol, Terra e Luna executam conforme capacidade e complexidade. Escolher o menor custo compatível com eficiência e acerto, economizando tokens sem retirar verificações necessárias; escalar incerteza ou insuficiência de capacidade. A auditoria/revisão independente existente permanece separada da autoria da entrega.

Esta regra orienta a organização e a seleção quando disponíveis e autorizadas. Não troca o modelo padrão do runtime, não ativa provedor, não concede chamada paga nem exige construir novo sistema, auditor ou skill. Os contratos e detalhes de governança continuam em AGENTS.md, PRD.md e docs/ESPINHA-DORSAL.md; reservas e fronteiras de escrita continuam na fila comum.

## Atualização com aprovação e evidência

Uma descoberta do agente é proposta, não aprendizado automático. Antes de incorporar regra ou lição global, remover todo dado de caso, verificar sua generalidade e obter a aprovação prevista na governança do investigador. Atualizar a fonte canônica apropriada, evitando versões concorrentes. Registrar no histórico dessa fonte: data, mudança genérica, origem da determinação, responsável/aprovação e evidência de verificação. Se ainda não aprovada, identificar como proposta pendente; não apresentá-la como regra vigente. Progresso e testes de desenvolvimento pertencem à fila e à revisão correspondente, não a um cadastro de fatos nesta memória.

## Registro desta organização

27/10/2026 — LC01: os 10 comandos e as 6 skills do plugin passaram a apontar para esta entrada (antes só 1 de 16), e os 8 documentos antigos da raiz foram marcados como não autoritativos, de modo que o roteamento até aqui passou a ser verificado por teste. A memória de sessão do Claude recebeu somente um ponteiro para este arquivo, sem cópia de regra, conforme a regra 22 de AGENTS.md. Origem/aprovação: pedido expresso do operador; evidência em [revisoes/lacunas-2026-10-27.md](revisoes/lacunas-2026-10-27.md).

27/10/2026 — Origem/aprovação: pedido explícito do operador, transmitido ao executor pelo coordenador Codex-Sync, para memória central compartilhada e regras consistentes entre agentes. Implementação MM01: entrada única e adaptadores sem duplicação de normas; prompts CLI/API consultam fontes vivas. Evidência e limites: [revisoes/memoria-central-2026-10-27.md](revisoes/memoria-central-2026-10-27.md). Complemento expresso do operador na mesma data: coordenação sempre presente e preferência Astra/Sol/Terra/Luna conforme tarefa e custo compatível com acerto, com revisão independente. Nenhuma autorização de novos provedores, troca do runtime, chamada paga, publicação de dados ou aprendizado automático foi criada.
