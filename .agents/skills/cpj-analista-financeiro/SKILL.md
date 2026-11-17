---
name: cpj-analista-financeiro
description: "Normalizar extratos e comprovantes de um caso CPJ e reconstruir o caminho do dinheiro, com valores, camadas e fontes."
---

<!-- Gerado por ferramentas/configurar-codex.py; edite o gerador. -->

# CPJ: fluxo financeiro

Leia e execute [o procedimento desta tarefa](../../../portatil/03-analista-financeiro.md). Esse arquivo é a fonte do fluxo; não use apenas este resumo.

## Uso no Codex

- Leia primeiro `MEMORIA.md` na raiz, entrada comum de todos os agentes, e as fontes vivas ali indicadas, especialmente `AGENTS.md`. Regras vigentes prevalecem sobre snapshots dos procedimentos.
- Execução de arquivos no PC não implica inferência local. Siga as autorizações e restrições vigentes de sigilo em `AGENTS.md`; a memória e os adaptadores não autorizam provedor externo, publicação nem troca do runtime.
- Confirme o ID e a etapa solicitada; não selecione um caso por proximidade ou data. Leia a versão viva de `calibracao/licoes-aprendidas.md` antes de analisar ou redigir, em vez de depender do instantâneo portátil.
- Comandos `/...` e `$ARGUMENTS` nos procedimentos significam a tarefa e os argumentos do usuário; não exigem Claude CLI. Skills e agentes citados são instruções no plugin/portátil, não dependências instaladas do Codex. Use os scripts existentes no plugin; não copie scripts nem o modelo DOCX para a skill.
- Execute as instruções de agentes conforme a coordenação, autorização e adaptação de `MEMORIA.md` e `AGENTS.md`. Em IP extenso, trabalhe por blocos e consolide as fontes. Não inicie tarefas automáticas da Central ao atender uma tarefa interativa.
- Resolva caminhos relativos à raiz CPJ. Se aparecer `<base da skill>`, use a pasta original em `plugin/investigacao-cpj/skills/`, nunca esta pasta adaptadora. Scripts usam `python` em PowerShell; confira `--help` quando necessário. Em teste isolado, defina `CPJ_WORKSPACE` para a pasta fictícia.
- Atualize status/campos documentados com `caso.py` e indexe após concluir a etapa. Não registre entrega nem crie arquivo `FINAL` ao apenas produzir minuta: a indexação pode dar baixa automaticamente por esse nome.
- Preserve pontos de aprovação explícitos do procedimento quando não houver autorização prévia. Produza o resultado concreto revisável antes de solicitar aprovação. Calibração só guarda lições genéricas aprovadas; aprovação de uma minuta não autoriza divulgação externa.
