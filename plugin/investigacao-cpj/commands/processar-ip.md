---
description: Processa novos PDFs em Markdown por página, com O.S. em Markdown e checkpoint essencial único; sem derivados CSV/JSON
argument-hint: <ID do caso (OS-...)> [arquivo específico]
---

> **Antes de executar:** leia `MEMORIA.md` na raiz do workspace — entrada comum de todos os agentes — e as fontes vivas ali indicadas, em especial `AGENTS.md` (regras obrigatórias e sigilo) e `calibracao/licoes-aprendidas.md`. As regras vigentes prevalecem sobre este procedimento.

Processe o material do caso: $ARGUMENTS

Leia primeiro a skill `pdf-autos-policiais`. Use os scripts originais em `plugin/investigacao-cpj/skills/pdf-autos-policiais/scripts`; caso em `casos/<ID>/`.

1. Confira `processamento.json`: não reprocessar documento concluído nem concorrer com extração na fila/em andamento. Em erro, leia o log daquele documento e preserve checkpoints e originais.
2. Para novo PDF ainda não processado, rode `extrair.py <pdf> --saida <pasta-da-extracao> --lang por`. Use OCR local disponível; ausência/ilegibilidade é pendência, nunca sucesso presumido. A extração gera `transcricao.md` com páginas, O.S. em Markdown e um checkpoint essencial consolidado. **Não executar tabelas.py, entidades.py nem dados_json.py no fluxo dos novos PDFs.** Não criar arquivo por página apenas para indexar no RAG. Para registrar metadados no caso, use `caso.py ip <ID> <pasta-da-extracao>` (leitor do estado consolidado).
3. Para transcrição visual pendente, consulte o estado pelo leitor `estado_extracao.ler(pasta, 'relatorio_extracao.json')`; preserve a distinção entre transcrição confirmada e dado duvidoso. Observe consentimentos antes de qualquer provedor externo. Complete a transcrição conforme a skill e reprocesse apenas o necessário, sem gerar derivados CSV/JSON.
4. Material MD/CSV fornecido pelo operador continua sendo original e não deve ser descartado; sua importação legada não autoriza recriar CSV/JSON para os novos PDFs.
5. Atualize registro de tratamento e estado do caso, preservando SHA-256 do original; indexe pelos scripts existentes quando a etapa exigir. Resuma páginas/método, pendências e localização do Markdown. Próximo passo: `/analisar-ip <ID>`.
