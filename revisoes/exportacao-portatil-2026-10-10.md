# CL06 — descrição completa no portátil

O exportador lia apenas a linha `description: >-` e gerava `> >-`, perdendo o descritivo do analista documental. A correção mínima lê as linhas recuadas da descrição dobrada ou literal, encerra no próximo campo YAML e mantém a descrição inline existente. Usa somente a biblioteca padrão; não altera frontmatter, corpo ou fonte do plugin.

TDD: dois testes vermelhos reproduziram descrição dobrada e literal incompletas; inline e ausência de descrição já passavam. Após a correção, **quatro testes aprovados em 4,958 s**. Cada teste copia o exportador para uma pasta temporária com fontes fictícias e executa um subprocesso; a AST é apenas lida para preparar as peças. O módulo com efeitos no topo nunca é importado no workspace real. Os testes conferem descrição completa, dois-pontos, linhas literais, inline, corpo, bytes da fonte e doze saídas não vazias. O integrador repetiu os quatro testes, aprovados em 3,498 s.

Onze portáteis e seu README foram regenerados. A descrição real em `02-analisar-ip.md` corresponde exatamente ao texto da fonte. Descontado o horário de geração, somente a substituição do marcador vazio pela descrição completa mudou: todos os outros conteúdos e corpos permaneceram iguais ao snapshot. Os doze adaptadores CPJ passaram em `configurar-codex.py --verificar`, sem alteração de skills. Whitespace passou.

O plugin permanece **0.3.1**: os 77 arquivos genéricos da fonte e os 76 do cache conservaram os SHA256 registrados em CL05. Não houve nova atualização CLI, edição de agent YAML, versão, staging ou cache. Nenhum caso real, configuração, credencial, OAuth, inferência ou Git remoto foi utilizado.

Evidências e snapshot: `C:/Users/alan_/AppData/Local/Temp/cpj-cl06-before-20261010`, com `red.log`, `green.log`, `conferencia-gerados.json`, `exportador-incremental.diff`, exportador anterior e portáteis anteriores. Comando focado: `.venv/Scripts/python.exe ferramentas/teste_exportar_portatil_cl06.py`.
