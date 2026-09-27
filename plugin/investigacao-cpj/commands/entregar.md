---
description: Registra a entrega do relatório (versão final), atualiza produção, índice RAG e painel
argument-hint: <ID do caso> [data AAAA-MM-DD] [arquivo DOCX final]
---

Registre a entrega do caso: $ARGUMENTS

A baixa também acontece sem este comando: arquivo com `FINAL` no nome em `03-relatorios\` (automática no `indexar.py`) ou botão *Dar baixa* na Central. Se `caso.json` já tiver `baixa`, não duplique: apenas confira e siga para o passo 4.

1. Identifique a versão final: o DOCX indicado ou o `RELATORIO-<ID>-vNN.docx` mais recente em `casos\<ID>\03-relatorios\` (o investigador pode tê-lo editado no Word).
2. Extraia o texto do DOCX final com python-docx para `03-relatorios\RELATORIO-<ID>-FINAL.md` (com o cabeçalho YAML da minuta: caso, versao, modalidade, data). Esse arquivo é o exemplo aprovado usado pelo RAG e pela calibração.
3. `caso.py relatorio <ID> --arquivo RELATORIO-<ID>-FINAL.md --versoes <nº de minutas> [--data ...]`, `caso.py status <ID> entregue --origem agente --arquivo RELATORIO-<ID>-FINAL.md [--data ...]` e, se ainda não preenchido, `caso.py set <ID> resultado.autoria=identificada|indicios|nao_identificada resultado.sugestoes_providencias=true|false`.
4. `indexar.py` e `gerar_painel.py` (scripts em `C:\CPJ - TRABALHO\plugin\investigacao-cpj\skills\base-cpj\scripts\`).
5. Responda: produção do dia e do mês × meta (de `producao\base.json`) e sugira `/calibrar <ID>` se o DOCX final difere da minuta.