---
description: Atualiza a base e abre o painel de produção (dia, mês, ano, metas e indicadores)
argument-hint: [ano-mês opcional]
---

Atualize e mostre a produção. $ARGUMENTS

1. `python "plugin\investigacao-cpj\skills\base-cpj\scripts\indexar.py"`
2. `python "plugin\investigacao-cpj\skills\base-cpj\scripts\gerar_painel.py"`
3. `Start-Process "producao\painel.html"` (abre no navegador local; não publicar).
4. Resuma em 4–6 linhas a partir de `producao\base.json`: entregues hoje, no mês (× meta de `producao\config.json`), no ano, prazo mediano, casos em aberto por etapa.