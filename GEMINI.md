> **FILA DE O.S. — UM AGENTE POR ORDEM DE SERVIÇO (obrigatório, 29/09/2026).** Antes de extrair/analisar/redigir qualquer O.S. de `ordens-de-servico`, consulte e reserve: `python ferramentas\fila-os.py listar` e depois `... assumir <nº> --agente <seu-nome>` (ou `... proxima --agente <seu-nome>`). O quadro legível fica em `ordens-de-servico\_CONTROLE-OS.md` e em `_STATUS-OS.txt` dentro de cada pasta. Não pegue O.S. `em_andamento` de outro agente nem refaça O.S. `concluida`/`com_relatorio` sem pedido expresso do investigador. Workspace canônico dos casos: `C:\CPJ - TRABALHO\casos`. Ao terminar: `... concluir <nº> --agente <seu-nome> --docx "<caminho>"`; se parar no meio: `... liberar <nº> --agente <seu-nome> --motivo "<onde parou>"`. Reserva vence em 4 h sem `renovar`.

# Gemini / Antigravity

Siga integralmente as instruções de `AGENTS.md` (mesma pasta). Para cada tarefa, leia o arquivo correspondente em `portatil\`. Atenção especial à **Regra 15 do `AGENTS.md`** (determinação do delegado, 30/09/2026): no campo **Referência:** e nas informações do procedimento na parte superior do relatório, use **EXCLUSIVAMENTE o número do IPe e do Processo Judicial**; nunca coloque número de BO nem IP local.

Para desenvolver o sistema, leia também `PRD.md` e `TAREFAS-COMPARTILHADAS.md`. A fila é comum a Gemini, Codex, Claude e outros agentes: qualquer tarefa disponível pode ser assumida.

Antes de editar, execute `python ferramentas\fila-tarefas.py assumir <ID> --agente Gemini-1` (use um nome identificável da sessão). Só comece se o comando confirmar a reserva; não edite arquivos de tarefas em andamento de outro agente. L04 (backup), L05 (OCR) e L03 (interface) são exemplos de frentes possíveis, não reservas fixas.

Ao terminar, rode `python ferramentas\fila-tarefas.py concluir <ID> --agente Gemini-1 --resultado "arquivos e testes realizados"`. Se precisar devolver a tarefa, use `liberar` com o ponto de retomada em `--resultado`. Teste somente com dados fictícios e workspace isolado; registre dependências no quadro.
