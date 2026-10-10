# Plugin 0.3.0 — instalação local verificada

Em 10/10/2026, após AG04 encerrar duas rodadas de 71/71 suítes com retorno zero, os dois manifestos foram atualizados de 0.2.1 para 0.3.0. O número 0.3.0 em registros anteriores descrevia uma rodada funcional, não a versão então conferida dos manifestos.

A CLI nativa 2.1.287 confirmou `investigacao-cpj@cpj-local`, versão **0.3.0**, `enabled: true`, `scope: user`, instalado em `C:/Users/alan_/.claude/plugins/cache/cpj-local/investigacao-cpj/0.3.0`. O marketplace aponta para `C:/Users/alan_/AppData/Local/CPJ/plugin`. A validação estrita por CLI passou tanto nesse pacote quanto no cache instalado: zero erros e avisos.

O atualizador anterior informou “Pronto” apesar de marketplace e plugin ausentes, reproduzido exclusivamente em configuração fictícia. A correção valida marketplace e pacote, verifica códigos de saída, instala quando ausente e confere a versão antes de informar conclusão. O YAML inválido de `analista-documental.md` foi corrigido apenas delimitando a descrição; texto, instruções, ferramentas, nome e modelo foram preservados.

A CLI recusou tanto pasta quanto manifesto em D: com `failureCode: network_location`. D: foi identificado como disco local exFAT, sem provedor de rede e sem link no diretório; a recusa não comprova que seja uma unidade de rede. Não houve alteração da política de confiança. A alternativa local autorizada copia de D: para C: somente o marketplace e o código genérico do plugin: **77 arquivos**, cada SHA256 conferido. Testes, fixtures, casos, configuração local, originais, caches, chaves e SQLite ficam excluídos. Destino com arquivo inesperado, link ou marketplace apontando a outro local interrompe a atualização; o ensaio de conflito preservou uma sentinela fictícia.

Primeira instalação e atualização pelo staging passaram em TEMP antes da instalação real. Onze procedimentos portáteis foram regenerados; os doze adaptadores CPJ passaram em `configurar-codex.py --verificar`. Todas as skills existentes permaneceram idênticas aos snapshots, inclusive as personalizadas. Verificação de whitespace passou.

O ensaio sem Python no PATH reproduziu falha de exportação no atualizador anterior. A correção seleciona primeiro `.venv/Scripts/python.exe` com `--version` e retorno zero; aceita um Python válido no PATH como alternativa e falha explicitamente, antes de modificar a versão ou instalar, se nenhum existir. Candidata TEMP passou com venv fictícia válida e PATH sem Python; cenário sem venv nem Python foi recusado. ENV02 reparou a venv real para Python 3.12.14; a execução padrão do atualizador passou com PATH sem Python, sem função temporária e sem PYTHONPATH, usando essa venv; confirmou 0.3.0, regenerou onze portáteis e terminou com retorno zero.

Evidências: `C:/Users/alan_/AppData/Local/Temp/cpj-cl03-candidato-r8785fdi`, arquivos `instalacao-real-staging.log`, `plugins-reais.json`, `marketplaces-reais.json`, `validacao-real.json`, `validacao-cache-real.json`, `inventario-staging-sha256.json` e logs Python. Estado anterior preservado em `C:/Users/alan_/AppData/Local/Temp/cpj-cl03-before-20261010`.

A checagem de saúde ocorreu exclusivamente em cópia TEMP, com dados e modelo fictícios, zero casos e endereço 127.0.0.1:1. Usou runtime explícito Python 3.12.14: nove imports, Tesseract/POR e plugin passaram; Git não foi encontrado após o reset do PATH. **A saúde padrão real não foi certificada**. Boot real e CI remota não foram testados. Nenhuma inferência, API, avaliação em nuvem, credencial ou fluxo OAuth foi utilizado nesta tarefa.

A instalação reflete o snapshot atual. Alterações posteriores em TS04/AI03 exigirão nova atualização do staging e cache antes de declarar o código instalado atualizado.
