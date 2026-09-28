# Gemini / Antigravity

Siga integralmente as instruções de `AGENTS.md` (mesma pasta). Para cada tarefa, leia o arquivo correspondente em `portatil\`.

Para desenvolver o sistema, leia também `PRD.md` e `TAREFAS-COMPARTILHADAS.md`. A fila é comum a Gemini, Codex, Claude e outros agentes.

**Fase atual (28/09/2026):** trabalhe só nas tarefas `E` da seção "Rodada enxuta". Em loop: `python ferramentas\fila-tarefas.py proxima`. Código de saída 0 = assuma o ID impresso; 3 = rodada concluída, pare; 4 = aguarde. Depois, `python ferramentas\fila-tarefas.py assumir <ID> --agente Gemini-1`. Só comece se a reserva for confirmada; não edite arquivos de tarefas em andamento de outro agente. Diretrizes só valem depois de implementadas e testadas: não registre como pronto o que ficou apenas no documento.

Ao terminar, rode `python ferramentas\fila-tarefas.py concluir <ID> --agente Gemini-1 --resultado "arquivos e testes realizados"`. Se precisar devolver a tarefa, use `liberar` com o ponto de retomada em `--resultado`. Teste somente com dados fictícios e workspace isolado.
