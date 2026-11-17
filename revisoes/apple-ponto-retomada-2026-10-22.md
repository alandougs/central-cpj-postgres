# Ponto de retomada — Central CPJ — 22/10/2026

## Onde parou

**Etapa Apple e mapa único concluída.** Goal AP36–AP39 marcado como completo; quatro tarefas concluídas na fila. Execução registrada em aproximadamente 39 minutos. O operador pediu gravar este ponto; não há implementação pendente dessa etapa.

## Entrega confirmada

- Skill `apple-design` instalada em `C:/Users/alan_/.codex/skills/apple-design`, origem `dickwu/apple-design-skill`, commit `914b6a377c22755597e4405e54911b996de822d7`. Disponível na próxima interação do Codex.
- Visual Apple aplicado ao site e ao painel autônomo: tipografia de sistema, superfícies, espaçamento, temas claro/escuro, foco e preferências de acessibilidade; marca ASTRA/CPJ preservada.
- Uma aba principal **Mapa**, URL `#mapa`. Removidos os acessos duplicados em Pesquisa/Grafo; atalhos contextuais e alias levam à mesma instância, com filtros, zoom e fontes preservados.
- Rótulos do mapa com 12,5 px reais, alvos de 44 px e seleção por Enter/Espaço. Estatísticas acompanha o tema principal.

Arquivos de produto: `plugin/investigacao-cpj/app/static/css/apple-cpj.css`, `static/index.html`, `static/js/inteligencia-mapa.js` e `skills/base-cpj/scripts/gerar_painel.py` (os três últimos caminhos relativos ao mesmo plugin). Harnesses RG26/EX01 ajustados somente para encerrar a árvore do Edge criado pelo próprio teste, preservando asserções.

## Verificação executada

Dez cenários novos aprovados (AP37: 1; AP38: 4; AP39: 5) e nove suítes de regressão afetadas aprovadas. Resultados foram obtidos em rodadas e repetições explicitadas, sem alegar uma rodada completa inteiramente verde: integração inicial 8/9, seguida de EX01 aprovado após corrigir seu encerramento; AP39/03 aprovado após corrigir a espera da requisição no teste. Produto permaneceu com os mesmos hashes. Não há falha de produto conhecida pendente desta entrega.

Capturas e inspeção real no Edge com dados fictícios em TEMP, temas claro/escuro e larguras desktop/compacta. Contraste mínimo de 5,5666:1 em 50 amostras. Não houve auditoria WCAG completa nem repetição de toda a suíte de backend/OCR/DOCX nesta etapa visual.

## Programa e evidências

Última conferência: aplicação já aberta em **http://127.0.0.1:8765/**; HTML, CSS e JavaScript responderam HTTP 200, idênticos aos arquivos finais. Abrir **http://127.0.0.1:8765/#mapa** e usar **Ctrl+F5** para carregar o novo visual. Esta sessão não reiniciou workers durante a alteração visual; não pressupor que o processo continuará aberto depois de desligar o computador.

- Relatório principal: `revisoes/apple-mapa-2026-10-22.md`.
- Revisão independente: `revisoes/apple-revisao-ap39.md`.
- Capturas: `%TEMP%/cpj-apple-ap39-20261022`.
- Logs/JSON: `%TEMP%/cpj-apple-ap36-gate-20261022.*`, `cpj-apple-ap36-ex01-20261022.*` e `cpj-apple-ap36-entrega-20261022.json`. Arquivos TEMP podem ser removidos pelo Windows.
- Histórico anterior preservado: `revisoes/pesquisa-aplicada-cpj-2026-10-22.md` (RP30–RP35) e `revisoes/cinco-falhas-gerais-2026-10-22.md` (RG26–RG29).

## Próxima ação e limites

Na retomada, ler este checkpoint, `PRD.md`, `AGENTS.md` e a fila. A próxima ação concreta é apresentar o sistema atualizado ao operador e tratar eventual ajuste solicitado; não repetir instalação, redesign ou consolidação do mapa já concluídos. Não iniciar nova implementação apenas por ler este arquivo.

Preservar alterações preexistentes, contratos e segurança. Nenhum auto/configuração operacional foi usado nos testes; nenhuma migração, reindexação, publicação, commit ou push foi executado nesta etapa. Novas funcionalidades continuam somente propostas. O plano canônico UN10–UN18 não foi executado nem substituído; eventual retomada dele segue `docs/ESPINHA-DORSAL.md` e seu checkpoint próprio.
