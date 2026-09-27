---
description: Cria o caso pela Ordem de Serviço (pasta casos\OS-...), opcionalmente copiando o PDF/MD para 00-originais
argument-hint: <nº da O.S.> [caminho do PDF/MD] [--bo N] [--ip N] [--processo N]
---

Crie o caso: $ARGUMENTS

Forma preferida: a **Central CPJ** (`C:\CPJ - TRABALHO\Central CPJ.bat` → aba Entrada) cria o caso e já processa os arquivos. Use este comando quando o usuário pedir pelo Claude.

1. Sem nº de O.S., pergunte. O ID da pasta é gerado a partir dela (`123/2026` → `OS-123-2026`).
2. `python "C:\CPJ - TRABALHO\plugin\investigacao-cpj\skills\base-cpj\scripts\caso.py" novo --os "<O.S.>" [--bo ...] [--ip ...] [--processo ...] [--natureza ...]`
3. Se foi informado arquivo, **copie** (nunca mova) para `casos\<ID>\00-originais\` e siga com `/processar-ip <ID>`.
4. Responda em até 4 linhas: pasta do caso e próximo passo.
