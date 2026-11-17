---
description: Cria o caso pela Ordem de Serviço (pasta casos\OS-...), opcionalmente levando o PDF/MD para 00-originais
argument-hint: <nº da O.S.> [caminho do PDF/MD] [--bo N] [--ip N] [--processo N]
---

> **Antes de executar:** leia `MEMORIA.md` na raiz do workspace — entrada comum de todos os agentes — e as fontes vivas ali indicadas, em especial `AGENTS.md` (regras obrigatórias e sigilo) e `calibracao/licoes-aprendidas.md`. As regras vigentes prevalecem sobre este procedimento.

Crie o caso: $ARGUMENTS

Forma preferida: a **Central CPJ** (`Central CPJ.bat` → aba Entrada) cria o caso e já processa os arquivos. Use este comando quando o usuário pedir pelo Claude.

1. Sem nº de O.S., pergunte. O ID da pasta é gerado a partir dela (`123/2026` → `OS-123-2026`).
2. `python "plugin\investigacao-cpj\skills\base-cpj\scripts\caso.py" novo --os "<O.S.>" [--bo ...] [--ip ...] [--processo ...] [--natureza ...]`
3. Se foi informado arquivo, copie-o para `casos\<ID>\00-originais\` e confira que o SHA-256 da cópia é igual ao do arquivo de origem. **Pasta única:** se a origem estava na pasta de entrada `ordens-de-servico\`, remova-a de lá depois dessa conferência, para os autos existirem só em `00-originais`; arquivo vindo de outro local do usuário não é removido. Nunca altere o que já está em `00-originais`. Siga com `/processar-ip <ID>`.
4. Responda em até 4 linhas: pasta do caso e próximo passo.
