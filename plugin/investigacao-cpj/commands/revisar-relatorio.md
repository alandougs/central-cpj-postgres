---
description: Revisa um relatório (inclusive escrito pelo investigador) contra as fontes do caso e o modelo CPJ
argument-hint: <arquivo do relatório (.md/.docx)> [ID do caso]
---

Revise: $ARGUMENTS

Se for DOCX, extraia o texto com python-docx. Delegue ao agente `revisor-de-relatorio` com as fontes do caso (`02-analise\`, `01-extracao\<documento>\transcricao.md`). Preserve o conteúdo do autor; proponha correções em tabela (trecho atual | problema | fonte | redação sugerida), separando erro de transcrição de inferência indevida; não acrescente enquadramento jurídico ou diligência sem fonte. Liste ao final o que precisa de decisão humana.