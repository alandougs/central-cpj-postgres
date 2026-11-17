# Estilo Apple e mapa único — 22/10/2026

## Escopo autorizado

O operador pediu instalar `https://github.com/dickwu/apple-design-skill`, aplicar os estilos ao sistema web atual e manter o mapa em um único lugar, com agentes. Goal AP36–AP39 na fila compartilhada. Alteração visual e de navegação sobre o projeto existente; não é outro plano de arquitetura/unificação.

Preservar marca CPJ/ASTRA, funções, dados, permissões, consentimentos, fontes, filtros e correções SEC/RG/RP. Testes e capturas exclusivamente fictícios em TEMP, com porta automática; a aplicação operacional em 8765 não é usada para examinar casos ou capturar imagens. Sem reiniciar trabalhadores, reindexar casos, migrar dados ou publicar código.

## Instalação da skill

Instalada com o helper oficial `skill-installer/scripts/install-skill-from-github.py`, usando `--repo dickwu/apple-design-skill --ref 914b6a377c22755597e4405e54911b996de822d7 --path . --name apple-design`. Destino: `C:/Users/alan_/.codex/skills/apple-design`. A instalação foi pedida explicitamente; nenhum script baixado do repositório foi executado. As referências foram lidas localmente. A skill estará disponível automaticamente a partir da próxima interação e foi aplicada manualmente nesta tarefa.

É uma skill de terceiros que reúne referências do Apple HIG, não certificação nem componente de runtime da Apple. Não incorpora ao site o conteúdo da skill, fontes proprietárias, logotipos Apple, CDN ou bibliotecas novas.

## Direção visual e navegação

Aplicação web local de trabalho investigativo: leitura, busca, revisão e acompanhamento por O.S. Visual inspirado em macOS, adaptado a HTML/CSS/JavaScript e ao Windows. Fundamentos aplicáveis: hierarquia, contraste, tipografia de sistema, espaçamento, foco/teclado, adaptação por largura e redução de movimento/transparência. Convenções de AppKit, menu de sistema e controles de janela nativos não se impõem ao navegador.

Manter a escolha de tema existente por compatibilidade. Conteúdo em superfícies opacas legíveis; materiais translúcidos restritos à camada funcional. Identidade institucional preservada. Sem hero promocional, fontes externas ou decoração que ocupe o espaço dos dados.

Mapa canônico: uma aba principal **Mapa**, com um painel e uma instância. Remover o submodo duplicado de Pesquisa e o botão duplicado de Grafo. Atalhos contextuais, como abrir uma correlação no mapa, levam à mesma tela e preservam seu contexto, em vez de criar outra visualização.

| Frente | Responsável | Arquivos |
|---|---|---|
| CSS e tokens Apple | AP37 | `static/css/apple-cpj.css`, teste próprio |
| Mapa único, navegação e carregamento CSS | AP38 | `static/index.html`, `static/js/inteligencia-mapa.js`, teste próprio |
| Verificação visual/teclado/responsividade | AP39 | teste Edge e relatório independente |
| Instalação, integração, PRD e evidência | AP36 | Este documento e PRD |

O escopo visual AP37 inclui o CSS autônomo de `skills/base-cpj/scripts/gerar_painel.py`, pois a aba Estatísticas usa um iframe e o CSS do documento pai não alcança seu conteúdo. Alterações restritas à apresentação; manter geração/exportação autônoma e cálculos existentes.

### Baseline com dados fictícios

Capturas anteriores à integração salvas em `%TEMP%/cpj-apple-ap39-20261022/antes-*.png`. A inspeção manual de `antes-mapa-1440-light.png` confirmou a duplicação do acesso em Pesquisa; `antes-mapa-390-light.png` confirmou largura global de 430 px numa viewport de 390 px e mapa praticamente oculto pelo arranjo lateral. São falhas de disposição diretamente abrangidas pela aplicação do estilo e pela unificação do mapa. Nenhuma captura contém autos reais.

## Verificação

Realizadas reprodução dos problemas, verificação de navegação e inspeção visual em fixtures, medição de contraste e capturas claro/escuro/compacto. Produto congelado antes da regressão afetada; resultados de integração abaixo.

### Encerramento do navegador de teste

Reproduzido timeout de 55 segundos no harness RG26: Edge mantinha o fechamento/WebSocket bloqueado e o `finally` ocultava a conclusão ou falha das asserções. A reserva AP36 foi ampliada para o harness de testes. O navegador agora é criado por `launchServer`, conectado pelo próprio teste, e apenas a árvore do PID retornado é encerrada; erros são registrados antes da limpeza e preservam retorno de falha. Não há fechamento por nome de processo nem ação sobre o Edge do operador. As verificações de recursos, CSP, erros JavaScript e requisições externas foram preservadas. As novas suítes AP37–AP39 receberam limpeza equivalente em seus próprios runners.

Repetição RG26 no clone canônico: 1 teste aprovado em 36,311 s (40,922 s no subprocesso). A primeira execução com timeout não é contada como aprovação.

### Implementação e verificações dirigidas

- CSS local carregado após o estilo legado: fonte de sistema, superfícies opacas, cabeçalho com transparência discreta e fallback opaco, hierarquia e espaçamento consistentes, azul nas ações, temas claro/escuro. Não incorpora novas bibliotecas ou fontes remotas.
- Tabelas preservam rolagem própria e linhas de casos concluídos continuam verdes. Formulários, seleção de tema, permissões e controles ocultos permanecem funcionais.
- A amostra de 50 pares texto/fundo computados no navegador apresentou contraste mínimo de 5,5666:1. Fronteiras geográficas e contagens foram medidas separadamente. Isso não equivale a auditoria WCAG completa.
- O mapa tem seção principal única `#mapa` e URL `#mapa`; acessos legados/contextuais encaminham à mesma instância. Filtros, zoom, origem dos registros e distinção entre localização municipal aproximada e coordenada documentada permanecem.
- Rótulos dos pontos compensam a escala real do SVG (`getScreenCTM`): 12,5 px de texto e alvo de 44 px nas larguras verificadas. Registros já clicáveis receberam foco e ativação por Enter/Espaço, incluindo itens sem localização e leque, sem novo modo de análise.
- AP37: 1 cenário Edge final aprovado em 32,190 s, sem skips; cobre estilos computados, contraste, foco, redução de movimento/transparência, aumento de contraste, zoom/reflow, larguras 360/768/1440 e painel autônomo.
- AP38: rodada final de 4 cenários Edge aprovada em 88,730 s; mapa único, navegação/URL/alias, preservação de estado/contexto, leitura/alvo em 1440/390/1024 e retorno com correlação ativa sem perder zoom. A sincronização do tema do iframe foi confirmada independentemente pela AP39.
- O servidor já aberto em 8765 respondeu HTTP 200 para HTML/CSS/JavaScript; os dois recursos servidos eram idênticos aos arquivos locais. Esta conferência leu somente código estático, sem autenticar, consultar casos ou executar geração operacional.

Inspeção manual da coordenação: novos screenshots de Mapa em 1440/390 claro, Casos em 1440 escuro, Estatísticas em 1440 claro e login em 390 claro; depois dos últimos ajustes, Mapa e Estatísticas em 390 escuro. Confirmadas a identidade institucional, a hierarquia visual, a leitura dos formulários, os rótulos maiores e a correção do mapa oculto/overflow e do iframe claro no tema escuro.

### Revisão independente AP39

Cinco cenários distintos aprovados: rodada final com quatro aprovações e uma falha de sincronização do próprio teste em 127,481 s; cenário 03 repetido e aprovado em 25,656 s após armar a espera da requisição antes do clique e aguardar a resposta. Não houve alteração de produto nessa repetição nem redução das asserções sobre O.S., UF ou fontes. A mesma espera determinística foi aplicada ao teste AP38. Detalhes, REDs anteriores e comandos em `revisoes/apple-revisao-ap39.md`.

Capturas finais em `%TEMP%/cpj-apple-ap39-20261022`: Início/Casos/Nova O.S./Mapa em 1440/390 e claro/escuro; mapas recapturados após correção da escala; Estatísticas e login em ambos os temas; inspetor e reflow complementares. As capturas são temporárias e podem ser removidas pelo Windows.

Não se declara certificação WCAG nem validação por leitor de tela, Switch Control ou dispositivo móvel físico. A medição cobre as amostras, tamanhos, preferências emuladas e fluxos descritos. O reflow AP39 usa viewport CSS de 720 px com DPR 2; AP37 também verificou zoom CSS de 200%. Não é ensaio do comando de zoom na barra nativa do Edge. Não se repetiu a suíte completa de backend/OCR/DOCX, pois esta mudança é visual e de navegação; a regressão dirigida verifica os consumidores afetados.

## Regressão integrada AP36 e entrega

Snapshot único criado com `clonar_codigo` do runner canônico, que gera modelo DOCX geométrico e não copia modelos/assinaturas do operador. Cada suíte executada em processo Python separado, workspace TEMP próprio, porta automática e agentes desativados. Hashes do produto e dos testes selecionados idênticos antes/depois da primeira rodada (412,594 s totais).

| Suíte afetada | Resultado final | Tempo do subprocesso |
|---|---|---|
| Relatórios UX01 | aprovado | 2,156 s |
| Consentimento SE01 | aprovado | 4,484 s |
| Explorer EX01 | aprovado na repetição descrita abaixo | 16,985 s |
| Grafo GF02 | aprovado | 1,828 s |
| Scripts/recursos RG26 | aprovado | 18,235 s |
| Status concluídos | aprovado | 22,844 s |
| Identidade/formulários | aprovado | 91,265 s |
| Grafo/XSS/escopo RP35 | aprovado | 67,391 s |
| Fontes do mapa RP31 | aprovado | 88,422 s |

A primeira rodada teve **8/9 suítes com retorno zero**. EX01 excedeu 90 s no seu harness próprio de encerramento do Edge, ainda com o padrão antigo `browser.close`. Com a reserva AP36 ampliada, após a rodada congelada esse arquivo recebeu a mesma limpeza por PID próprio usada no RG26. Todas as asserções de DOCX, arquivos, cliques e acesso remoto foram preservadas. A repetição EX01 no clone canônico aprovou seu cenário em 14,588 s (16,985 s no subprocesso), retorno zero e hashes estáveis. Nenhuma alteração no produto entre as duas rodadas; a primeira execução não é apresentada como nove aprovações. Ao final, **as nove suítes dirigidas e os dez cenários novos têm verificação aprovada**, com as repetições explicitadas.

Evidências locais da integração: `%TEMP%/cpj-apple-ap36-gate-20261022.{log,json}` e `%TEMP%/cpj-apple-ap36-ex01-20261022.{log,json}`. A revisão independente está em `revisoes/apple-revisao-ap39.md`. Verificações de sintaxe Python/JavaScript e `git diff --check` dos arquivos alterados aprovadas; aviso de normalização LF/CRLF não representa falha.

Conferência final de entrega em `%TEMP%/cpj-apple-ap36-entrega-20261022.json`: os quatro arquivos de produto mantêm os hashes do snapshot; HTML, CSS e JavaScript respondem HTTP 200 e seu conteúdo servido é idêntico à fonte final. Skill instalada presente. Nenhum conteúdo de caso foi acessado nessa conferência.

O programa permanece aberto no endereço local informado. Atualizar com **Ctrl+F5** carrega o CSS e o JavaScript novos; o mapa está em `http://127.0.0.1:8765/#mapa`. Skill instalada disponível automaticamente na próxima interação do Codex. Sem publicação, mudança de banco/arquitetura, custo obrigatório novo ou operação em autos.
