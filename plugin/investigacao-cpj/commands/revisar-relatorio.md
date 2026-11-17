---
description: Revisa um relatório (inclusive escrito pelo investigador) contra as fontes do caso e o modelo CPJ
argument-hint: <arquivo do relatório (.md/.docx)> [ID do caso]
---

> **Antes de executar:** leia `MEMORIA.md` na raiz do workspace — entrada comum de todos os agentes — e as fontes vivas ali indicadas, em especial `AGENTS.md` (regras obrigatórias e sigilo) e `calibracao/licoes-aprendidas.md`. As regras vigentes prevalecem sobre este procedimento.

Revise: $ARGUMENTS

Se for DOCX, extraia o texto com python-docx. Delegue ao agente `revisor-de-relatorio` com as fontes do caso (`02-analise\`, `01-extracao\<documento>\transcricao.md`). Preserve o conteúdo do autor; proponha correções em tabela (trecho atual | problema | fonte | redação sugerida), separando erro de transcrição de inferência indevida; não acrescente enquadramento jurídico ou diligência sem fonte. Liste ao final o que precisa de decisão humana.
O revisor também audita explicações alternativas sustentadas nos autos, evidências divergentes, reconciliação dos valores e lacunas documentais/OCR. Exija o parecer definido em `agents/revisor-de-relatorio.md`, mantendo a linha de contagem por sustentação e a decisão humana. Não converter essas contagens em probabilidade de autoria/culpa.
Gate de entrega: confira se existe `03-relatorios\conferencia-vNN.json` da versão atual, gerado em `--modo entrega`; se não existir, rode `python "plugin\investigacao-cpj\skills\relatorio-ip-fraude\scripts\conferir_minuta.py" <ID> --modo entrega`. Minuta com `BLOQUEIA` pendente é reprovada; não corrija nem apague dado para passar no gate. Inclua os itens `REVISAR` no parecer, em "Itens para decisão humana".
