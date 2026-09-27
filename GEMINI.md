# Gemini / Antigravity

Siga integralmente as instruções de `AGENTS.md` (mesma pasta). Para cada tarefa, leia o arquivo correspondente em `portatil\`.

Para desenvolver o sistema, leia também `PRD.md` e `TAREFAS-COMPARTILHADAS.md`. A fila é comum a Gemini, Codex, Claude e outros agentes: qualquer tarefa disponível pode ser assumida.

Antes de editar, execute `python ferramentas\fila-tarefas.py assumir <ID> --agente Gemini-1` (use um nome identificável da sessão). Só comece se o comando confirmar a reserva; não edite arquivos de tarefas em andamento de outro agente. L04 (backup), L05 (OCR) e L03 (interface) são exemplos de frentes possíveis, não reservas fixas.

Ao terminar, rode `python ferramentas\fila-tarefas.py concluir <ID> --agente Gemini-1 --resultado "arquivos e testes realizados"`. Se precisar devolver a tarefa, use `liberar` com o ponto de retomada em `--resultado`. Teste somente com dados fictícios e workspace isolado; registre dependências no quadro.
