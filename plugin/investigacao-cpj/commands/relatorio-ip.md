---
description: Redige a minuta do Relatório de Investigação no modelo CPJ, revisa contra as fontes e gera o DOCX com timbre e assinatura
argument-hint: <ID do caso> [observações do investigador: diligências feitas, consultas, foco]
---

Elabore o relatório do caso: $ARGUMENTS

Use a skill `relatorio-ip-fraude`.

1. Leia `calibracao\licoes-aprendidas.md`, `modelos\dados-padrao.json`, a análise do caso (`02-analise\`) e exemplos da mesma modalidade por autor e peso (`rag.py exemplos <modalidade> --autor "<investigador>" -n 3` — FINAL do sistema + referências importadas; só estilo/estrutura, nunca fatos). Fatos: somente os documentos do caso; bases de consulta não são fonte.
2. Se o investigador informou diligências próprias (consultas a sistemas, oitivas, campana), inclua **somente** o que ele informou. Se faltar dado do cabeçalho (O.S., delegado destinatário), use `{...}` e liste. No cabeçalho (campo `referencia` / dados do procedimento), siga a **determinação do Delegado (30/09/2026)**: use **SOMENTE o número do IPe (Inquérito Policial Eletrônico) e do Processo Judicial** (ex.: `IPe nº ... / Processo nº ...`); **NUNCA coloque número de BO nem IP local**. Defina `delegado_genero: M|F` pelos documentos do caso (Dr./Dra., "o/a Delegado/a"); não infira pelo nome; sem base, pergunte. Redija em **texto corrido**, sem tópicos; Resumo dos fatos compacto, com a dinâmica e os valores movimentados (AGENTS.md §1.12-1.13, §1.15).
2a. **Dados faltantes:** se faltar dado muito importante para autoria, materialidade ou circunstâncias, grave `02-analise\dados-faltantes.md` e avise o operador **em CAIXA ALTA** na resposta final (`DADOS FALTANTES — PROVIDENCIAR (OPERADOR)`), conforme `skills\analise-ip-fraude\references\dados-faltantes.md`. Não deduza; no relatório, só ressalva objetiva na Conclusão.
3. Grave `03-relatorios\minuta-vNN.md` e `rastreabilidade-vNN.md`; `caso.py status <ID> minuta`.
4. Delegue a revisão ao agente `revisor-de-relatorio` → `revisao-vNN.md`. Corrija erros objetivos na minuta (mesma versão) e liste o que depende de decisão.
5. Gere o DOCX (rascunho): `python "C:\CPJ - TRABALHO\plugin\investigacao-cpj\skills\relatorio-ip-fraude\scripts\gerar_docx.py" "<minuta>" --saida "casos\<ID>\03-relatorios\RELATORIO-<ID>-vNN.docx"`.
6. Apresente: caminho do DOCX, resumo da revisão, campos pendentes, dados críticos não conferidos e, **em CAIXA ALTA, os DADOS FALTANTES para o operador providenciar**. Diga que, após revisar/editar no Word e entregar, basta rodar `/entregar <ID>`.