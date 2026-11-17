# Claude — adaptador do workspace CPJ

Leia primeiro [MEMORIA.md](MEMORIA.md), entrada comum a todos os agentes, e siga as fontes vivas ali indicadas. As regras operacionais estão em [AGENTS.md](AGENTS.md); desenvolvimento também exige PRD.md, docs/ESPINHA-DORSAL.md e a reserva atual na fila. Este adaptador não replica regras, datas, fatos de casos ou reservas de conversas anteriores.

Use os procedimentos vivos do plugin `investigacao-cpj` ou os equivalentes de `portatil/`: `/processar-ip`, `/analisar-ip`, `/relatorio-ip`, `/revisar-relatorio`, `/entregar`, `/calibrar`, `/buscar`, `/painel` e `/fluxo-ip`. Não interpretar a lista de comandos como autorização de executar tarefas fora do pedido. Antes de analisar ou redigir, leia também `calibracao/licoes-aprendidas.md` conforme a memória central.

Para reservar desenvolvimento: `python ferramentas/fila-tarefas.py assumir <ID> --agente <nome-da-sessao>`. Confira a reserva pelo resultado do comando; registre testes e conclusão/liberação na mesma fila. Para O.S., siga a reserva e o fluxo definidos em AGENTS.md. Use PowerShell e `python` no Windows; comandos de backup, publicação ou instalação seguem seus contratos e a autorização do operador.

Coordenação: aplique a regra comum de MEMORIA.md; há sempre um coordenador, com preferência Astra na orquestração e Sol/Terra/Luna na execução conforme capacidade, custo e acerto. A revisão independente permanece exigida. Esta preferência não autoriza trocar o runtime, ativar provedor ou fazer chamada paga.
