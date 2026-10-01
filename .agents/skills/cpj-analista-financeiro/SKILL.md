---
name: cpj-analista-financeiro
description: "Normalizar extratos e comprovantes de um caso CPJ e reconstruir o caminho do dinheiro, com valores, camadas e fontes."
---

<!-- Gerado por ferramentas/configurar-codex.py; edite o gerador. -->

# CPJ: fluxo financeiro

Leia e execute [o procedimento desta tarefa](../../../portatil/03-analista-financeiro.md). Esse arquivo é a fonte do fluxo; não use apenas este resumo.

## Uso no Codex

- Leia `AGENTS.md` na raiz antes de acessar material do caso. Siga as regras de fonte, sigilo, originais imutáveis e saída como minuta.
- Execução de arquivos no PC não implica inferência local: não carregue autos reais, imagens, extrações, consultas ou resultados identificáveis no contexto de um modelo externo. Sem ambiente/conta compatível com a regra 6 de `AGENTS.md`, limite-se a procedimentos, código e dados fictícios; processamento de autos permanece no fluxo local autorizado.
- Confirme o ID e a etapa solicitada; não selecione um caso por proximidade ou data. Leia a versão viva de `calibracao/licoes-aprendidas.md` antes de analisar ou redigir, em vez de depender do instantâneo portátil.
- Comandos `/...` e `$ARGUMENTS` nos procedimentos significam a tarefa e os argumentos do usuário; não exigem Claude CLI. Skills e agentes citados são instruções no plugin/portátil, não dependências instaladas do Codex. Use os scripts existentes no plugin; não copie scripts nem o modelo DOCX para a skill.
- Execute as instruções de agentes em sequência, conforme a adaptação do `AGENTS.md`. Em IP extenso, trabalhe por blocos e consolide as fontes. Não inicie tarefas automáticas da Central ao atender uma tarefa interativa.
- Resolva caminhos relativos à raiz CPJ. Se aparecer `<base da skill>`, use a pasta original em `plugin/investigacao-cpj/skills/`, nunca esta pasta adaptadora. Scripts usam `python` em PowerShell; confira `--help` quando necessário. Em teste isolado, defina `CPJ_WORKSPACE` para a pasta fictícia.
- Atualize status/campos documentados com `caso.py` e indexe após concluir a etapa. Não registre entrega nem crie arquivo `FINAL` ao apenas produzir minuta: a indexação pode dar baixa automaticamente por esse nome.
- Preserve pontos de aprovação explícitos do procedimento quando não houver autorização prévia. Produza o resultado concreto revisável antes de solicitar aprovação. Calibração só guarda lições genéricas aprovadas; aprovação de uma minuta não autoriza divulgação externa.
