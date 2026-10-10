# Opções DOCX — TS07 — 10/10/2026

Dois defeitos foram comprovados na correção local do piloto fictício P01, sem alterar sua execução automática nem seus originais. A reserva TS07 cobre somente o gerador, o teste novo e este registro.

Com `--fluxo-csv` explícito, `pasta_caso` era definida apenas na descoberta automática; o uso posterior provocava `NameError`, capturado como aviso, e produzia DOCX sem o fluxograma. Agora as pastas da minuta/caso são definidas antes da escolha do CSV, preservando a descoberta automática e o nome do diagrama.

Com `--sem-assinatura`, o laço final removia qualquer parágrafo sem texto contendo imagem, incluindo fluxograma e conteúdo inseridos da minuta. Agora captura os elementos desses parágrafos preexistentes do modelo antes da inserção e restringe a remoção a eles. Conserva o tratamento original dessas imagens como assinatura; não introduz classificação por aparência, nome ou conteúdo. Imagens inseridas permanecem mesmo quando seus bytes/rId coincidem com os do modelo. Imagens em outros locais mantêm o comportamento anterior.

## Evidência

TDD em modelo, assinatura, PNG e CSV inteiramente fictícios gerados no TEMP. O primeiro desenho do teste foi ajustado antes do patch para usar os prefixos reais do contrato do modelo e verificar imagens efetivamente referenciadas no corpo do DOCX, não apenas blobs ZIP órfãos. Reprodução correta: cinco falhas e dois controles aprovados em 3,089 s, incluindo o aviso explícito `pasta_caso` indefinida e ausência real das imagens inseridas. Após o patch: sete aprovados em 3,368 s. Caso adicional de bytes idênticos protege a distinção por origem do parágrafo: rodada final **oito aprovados em 3,553 s**.

`teste_docx_opcoes_ts07.py` executa o gerador real em subprocesso, reabre o DOCX e compara imagens realmente usadas e hashes de seis insumos (modelo, minuta, CSV, assinatura e dois PNGs). Cobre CSV explícito, descoberta automática, opções combinadas, PNG explícito, imagem Markdown, assinatura padrão, desativação de fluxograma e conteúdo com bytes iguais aos da assinatura.

Regressões existentes executadas por `C:/Users/alan_/AppData/Local/Temp/ts07-regressao-ficticia.py`: quatro testes de `teste_diagrama_docx.py` e três de `teste_docx_f04.py` (tabela, alinhamento monetário e citações/estilos), **sete aprovados em 1,443 s**. O harness aponta os módulos para um novo TEMP com scripts genéricos e modelo criado pelo teste TS07; não lê nem copia modelo institucional real. Os testes existentes que exigem margens/timbre/assinatura reais não foram executados nesta tarefa; essa comparação não é necessária para comprovar estes dois defeitos e não é alegada.

Python utilizado: `D:/CPJ - TRABALHO/.venv/Scripts/python.exe`, 3.12.14. Comando focado:

```powershell
& 'D:/CPJ - TRABALHO/.venv/Scripts/python.exe' 'D:/CPJ - TRABALHO/plugin/investigacao-cpj/app/testes/teste_docx_opcoes_ts07.py'
```

Diff mínimo conferido; `git diff --check` retornou zero. Nenhuma inferência, API, assinatura real, caso real, mudança de configuração ou alteração de insumos. P01 v01/v02 e métricas automáticas permanecem como evidência do plugin 0.3.2; não foram regenerados com o patch TS07. Atualização oficial CL08 pertence ao integrador.
