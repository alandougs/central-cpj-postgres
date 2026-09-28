# Rodada de melhorias F — prompts por agente (28/09/2026)

Cole cada bloco em uma sessão nova do agente indicado, aberta em `D:\CPJ - TRABALHO`. As tarefas estão em `TAREFAS-COMPARTILHADAS.md`, seção "Rodada de melhorias F". Os arquivos de cada uma são disjuntos, então os quatro podem rodar juntos.

## Claude — F01 · Visual e usabilidade da Central

```text
Você é Claude-1 no workspace D:\CPJ - TRABALHO. Leia AGENTS.md (seções 1 e 6), PRD.md e a seção "Rodada de melhorias F" de TAREFAS-COMPARTILHADAS.md.

1. Assuma: python ferramentas\fila-tarefas.py assumir F01 --agente Claude-1. Se recusar, pare e me diga o motivo.
2. Suba uma Central de teste com workspace temporário e dados fictícios (flags em .agents\skills\cpj-desenvolver\SKILL.md: --workspace, --porta 8766, --somente-local, --sem-navegador). Nunca abra a Central real nem leia casos\, config\ ou consulta\.
3. Diagnóstico: rode /web-design-guidelines em plugin\investigacao-cpj\app\static\index.html e tire screenshots das telas principais em 1366x768 e 1920x1080 pelo MCP playwright.
4. Com /frontend-design e /theme-factory, proponha 2 direções visuais curtas (paleta, tipografia só com fontes do sistema, densidade, componentes). O visual deve ser sóbrio e institucional (Polícia Civil, uso diário por investigador). Mostre as direções e ESPERE minha escolha.
5. Implemente em etapas pequenas, com HTML/CSS/JS puros. Sem CDN, sem fonte externa e sem framework. Preserve IDs, chamadas de API e o modo solo da E02. Inclua tema claro/escuro, estados de carregamento/erro/vazio, foco visível, contraste AA e rótulos. O index.html não pode crescer mais de 15%.
6. Crie app\testes\teste_interface_f01.py cobrindo: nenhuma URL externa no HTML, elementos-chave presentes, rótulos de acessibilidade. teste_interface_solo_e02 e teste_interface_claude têm de continuar verdes.
7. Antes de concluir: skill verification-before-completion, regressão mínima da fila, screenshots antes/depois para eu comparar. Depois: python ferramentas\fila-tarefas.py concluir F01 --agente Claude-1 --resultado "arquivos; testes; resultado".
Só edite index.html e o seu teste. Bug em outro arquivo vira linha F1x. Sem commit.
```

## Codex — F02 · Velocidade do OCR e da extração

```text
Você é Codex-1 no workspace D:\CPJ - TRABALHO. Leia AGENTS.md (seções 1, 5 e 6), PRD.md e a seção "Rodada de melhorias F" de TAREFAS-COMPARTILHADAS.md.

1. Assuma: python ferramentas\fila-tarefas.py assumir F02 --agente Codex-1. Se recusar, pare e me diga o motivo.
2. Linha de base: gere o PDF fictício (plugin\investigacao-cpj\skills\pdf-autos-policiais\teste\gerar_pdf_ficticio.py) e meça o tempo por etapa em workspace temporário, comparando com revisoes\ensaio-core-2026-09-28.md. Guarde a saída (transcricao.md por página, CSV, entidades) como referência.
3. Use $systematic-debugging como método: perfile com cProfile e identifique os 3 maiores gargalos com números, antes de mudar qualquer coisa.
4. Otimize só em extrair.py, diagnostico.py e dividir.py. Ideias a validar: páginas em paralelo com limite de CPU, não rasterizar a mesma página duas vezes, pular OCR quando a camada de texto é boa, DPI adequado. Não toque em tabelas.py (E04), tarefas.py (S01) nem nas regras de OCR português (ferramentas\tessdata).
5. A saída tem de ser idêntica à referência, ou a diferença precisa ser justificada página a página. Qualidade do OCR vale mais que velocidade.
6. Crie app\testes\teste_desempenho_f02.py (equivalência de saída e limite de paralelismo). Registre antes/depois em revisoes\desempenho-f02.md. teste_desempenho_codex, teste_extracao_codex e teste_core_e03 têm de continuar verdes.
7. Antes de concluir: $verification-before-completion e regressão mínima da fila. Depois: python ferramentas\fila-tarefas.py concluir F02 --agente Codex-1 --resultado "gargalos; ganho medido; testes".
Bug em outro arquivo vira linha F1x. Sem commit.
```

## Gemini — F03 · Testes ponta a ponta no navegador

```text
Você é Gemini-1 no workspace D:\CPJ - TRABALHO. Leia AGENTS.md (seções 1 e 6), PRD.md e a seção "Rodada de melhorias F" de TAREFAS-COMPARTILHADAS.md.

1. Assuma: python ferramentas\fila-tarefas.py assumir F03 --agente Gemini-1. Se recusar, pare e me diga o motivo.
2. Use a skill webapp-testing (.agents\skills\webapp-testing). Instale o pacote Python playwright (pip) SEM baixar navegador: use channel="msedge" (Edge já instalado). Se precisar de algo além disso, me pergunte antes.
3. Suba uma Central de teste isolada (workspace temporário, porta 8766, --somente-local, --sem-navegador, modo solo) com dados fictícios. Nunca use a Central real nem leia casos\, config\ ou consulta\.
4. Escreva app\testes\teste_e2e_f03.py (auxiliares em app\testes\e2e\), headless, em menos de 5 minutos, pulando com aviso claro se o playwright não estiver instalado. Fluxos: abrir a Central em modo solo; Nova O.S. com o PDF fictício (gerar_pdf_ficticio.py); acompanhar o progresso do OCR até concluir; abrir o caso e ver a transcrição e o CSV; minuta fictícia; gerar DOCX; definir FINAL; conferir o painel. Em todos: zero erro de console e zero resposta HTTP 5xx.
5. Use seletores por papel/rótulo/ID estável. O Claude-1 está redesenhando a interface (F01) ao mesmo tempo: não edite index.html. Se algo quebrar por causa da F01, registre uma linha F1x com os passos. Rode tudo de novo depois que a F01 for concluída.
6. Não corrija código de produto. Cada bug vira uma linha F1x disponível no fim da tabela F, com passos para reproduzir. Resumo em revisoes\e2e-f03.md.
7. Antes de concluir: skill verification-before-completion e regressão mínima da fila. Depois: python ferramentas\fila-tarefas.py concluir F03 --agente Gemini-1 --resultado "fluxos cobertos; bugs F1x; tempo da suíte".
Sem commit.
```

## Copilot — F04 · DOCX do relatório fiel e bonito

```text
Você é Copilot-1 no workspace D:\CPJ - TRABALHO. Leia AGENTS.md (seções 1 e 6), PRD.md e a seção "Rodada de melhorias F" de TAREFAS-COMPARTILHADAS.md.

0. Se você for a mesma sessão que está com a E04 (Copilot-2), termine e conclua a E04 primeiro e use o mesmo nome abaixo.
1. Assuma: python ferramentas\fila-tarefas.py assumir F04 --agente Copilot-1. Se recusar, pare e me diga o motivo.
2. Leia plugin\investigacao-cpj\skills\relatorio-ip-fraude\scripts\gerar_docx.py e o modelo DOCX oficial em modelos\ (somente leitura; nunca altere o modelo nem modelos\dados-padrao.json).
3. Monte uma minuta fictícia completa no formato de portatil\04-relatorio-ip.md: títulos, parágrafos longos, tabela de transações Pix com R$, citações "(pág. N do PDF; fls. X)", lista de diligências e assinatura. Nada de dados reais.
4. Gere o DOCX e compare com o modelo usando python-docx: margens, cabeçalho/timbre, rodapé, numeração de páginas, estilos e fontes, espaçamento, tabelas (cabeçalho repetido, largura, alinhamento de valores à direita), quebra de página antes da assinatura, bloco de assinatura. Liste as divergências antes de corrigir.
5. Corrija só em gerar_docx.py, com as skills systematic-debugging e test-driven-development (em .claude\skills ou .agents\skills): primeiro o teste que falha, depois a correção.
6. Crie app\testes\teste_docx_f04.py com as verificações do item 4. Os testes que já geram DOCX (teste_core_e03, teste_central) têm de continuar verdes.
7. Deixe o DOCX fictício final em uma pasta temporária e me diga o caminho, para eu abrir no Word e aprovar o visual.
8. Antes de concluir: verification-before-completion e regressão mínima da fila. Depois: python ferramentas\fila-tarefas.py concluir F04 --agente Copilot-1 --resultado "divergências corrigidas; testes".
Bug em outro arquivo vira linha F1x. Sem commit.
```
