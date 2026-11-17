# Revisão independente AP39 — Central CPJ

Data: 22/10/2026. Responsável: Codex-QA-AP39. Escopo: interface web local em HTML/CSS/JavaScript, princípios de clareza, leitura, alinhamento e acessibilidade da skill pessoal `apple-design`; adaptação visual inspirada em macOS para Windows/Edge. Convenções nativas como menu de aplicativo macOS não são requisitos desta aplicação web.

## Síntese

A composição passa a priorizar os dados e a fonte, com superfícies neutras, hierarquia por tamanho/peso e ações azuis. O mapa pertence a uma tela principal e o inspetor acompanha sua leitura. **Avaliação: bom nos cenários verificados**, após os reparos de teclado, escala dos rótulos e sincronização do tema do painel; nenhum achado crítico ou alto permanece aberto nesta amostra.

## Contexto e método

A interface deve permitir ao investigador localizar a O.S., consultar os elementos e abrir a fonte sem dispersar o trabalho entre mapas duplicados. A identidade é uma ferramenta policial sóbria, com dados como conteúdo principal e azul reservado às ações. Esta revisão só altera o teste AP39 e este registro. Produto, backend, dados e demais testes pertencem às reservas AP37/AP38/AP36.

Referências locais lidas na skill: `accessibility.md`, `layout.md`, `typography.md`, `color.md`, `designing-for-macos.md`, `cross-platform.md`, `sidebars.md`, `buttons.md`, `materials.md`, `dark-mode.md`, `focus-and-selection.md` e `entering-data.md`. Fundamentação aplicada: `layout.md › Visual hierarchy`: “Align elements to make them easier to scan”; `materials.md › Liquid Glass`: “Use Liquid Glass effects sparingly”; `focus-and-selection.md › Best practices`: “Avoid changing focus without people’s interaction”; `accessibility.md › Vision`: “Support larger text sizes”. Os arquivos completos estão em `C:/Users/alan_/.codex/skills/apple-design/references/`.

Edge real em modo headless, servidor Flask/Cheroot em porta automática e workspace temporário, usuário fictício e O.S. `OS-931-2099`/`OS-932-2099`. A API de mapa recebe fixture de pessoas, empresas e polígonos sintéticos. A fonte Markdown é gravada apenas nesse workspace TEMP e aberta pela rota real `/arquivo`. Nenhum auto, configuração operacional, provedor, modelo DOCX ou assinatura pessoal é copiado da operação para a fixture. Não se utiliza `127.0.0.1:8765`.

Evidências persistentes locais: `%TEMP%/cpj-apple-ap39-20261022`. Prefixos `antes-` e `depois-`, tela, largura CSS e tema. Capturas incluem Início, Casos, Nova O.S. e Mapa em 1440/390 px e claro/escuro; login e Estatísticas recebem capturas complementares. São arquivos locais temporários, sem publicação.

## Achados e evolução

Linha de base, antes da inclusão do novo CSS: capturas `antes-mapa-390-light.png` e `antes-mapa-390-dark.png` evidenciam página com 430 px para viewport de 390 px, mapa fora da faixa visível e inspetor alongado. A navegação ainda apresenta Mapa na barra principal e dentro de Pesquisa. Esses problemas são o objeto das mudanças AP37/AP38.

Inspeção independente detectou seletor da malha em `apple-cpj.css` para `path`, enquanto a renderização produz `polygon`. Encaminhado à AP37 e corrigido por ela com `:is(path, polygon)`. Captura `depois-mapa-1440-light.png` aberta e conferida: malha clara e composição alinhada.

**Crítico — acesso por teclado:** teste05 reproduziu o marcador clicável sem `tabindex` (`null`, esperado `0`), em 29,519 s. AP38 adicionou foco, nome/role e Enter/Espaço aos alvos existentes. Repetição independente aprovou marcador com Enter, registro sem localização com Espaço, mesmo inspetor/fonte e anel de foco, em 77,750 s.

**Alto — rótulos do mapa compacto:** medição por `fontSize × getScreenCTM` encontrou **4,0953 px efetivos** na largura de 390 px. AP38 compensou a escala do SVG. O teste05 repetido mediu **12,5000 px**, acima do piso de 11 px verificado; tamanho aparente passou a ser preservado ao redimensionar.

**Médio — tema do painel:** screenshot `depois-estatisticas-390-dark.png` mostrou a tela principal grafite e o iframe claro. Teste04 reproduziu o fundo do painel `rgb(245, 245, 247)` sob tema principal escuro, em 25,646 s. AP38 aplicou sincronização same-origin em carregamento e no comando de tema. A execução final aprovou a medição nos dois temas; as novas capturas de Estatísticas e login foram abertas e conferidas, incluindo o painel grafite em 390 px.

Os dois primeiros comandos de captura salvaram os PNGs e excederam o timeout no fechamento do Edge pelo harness RG26. Isso é falha da execução do teste, não resultado aprovado. O novo teste tem BrowserServer próprio e encerra exclusivamente a árvore do PID que criou, preservando o navegador do operador e permitindo que a asserção original seja exibida.

## Validação final

Primeira rodada: teste01 (capturas), teste02 (contraste/foco/layout) e teste03 (mapa/filtros/fonte/recursos) aprovados. Teste04 falhou por seletor incorreto do próprio teste (`.kpi`, gerador usa `.card`), corrigido sem mudar produto; repetição aprovou em 31,750 s antes da asserção adicional de sincronização de tema. Esses resultados não ocultam os REDs de produto descritos acima.

Contraste computado em **25 amostras por tema**, mínimo **5,5666:1** em ambos, acima de 4,5:1 para texto comum e 3:1 para texto grande. A amostra inclui navegação, botões, rótulos e indicadores do mapa. Foram conferidos tipografia de sistema, foco visível e ordem Tab, ausência de overflow global nas telas Início/Casos/Nova O.S./Mapa a 1440/390/720 px, movimento reduzido e transparência/contraste por CDP. Reflow de 200% foi simulado com viewport CSS 720 px e DPR 2, produzindo 1440 px físicos; isso não é ensaio do comando de zoom na barra nativa do Edge.

Execução após congelamento do produto:

```powershell
$env:CPJ_AP39_SO_MAPA='1'
.venv\Scripts\python.exe plugin\investigacao-cpj\app\testes\teste_apple_ui_ap39.py
```

Resultado: **4 aprovados / 1 falha, 127,481 s**. A falha03 foi de sincronização do próprio teste: `networkidle` podia retornar antes do fetch do clique. A espera foi substituída por `waitForRequest` armada antes do clique, validação dos mesmos parâmetros `caso`/`uf` e conclusão da resposta. Nenhum produto foi alterado para esse ajuste. Repetição final:

```powershell
.venv\Scripts\python.exe plugin\investigacao-cpj\app\testes\teste_apple_ui_ap39.py AppleUIAP39.test_03_mapa_unico_atalhos_filtro_fonte_tema_recursos
```

Resultado: **1 aprovado / 0 falhas, 25,656 s**. Assim, os **cinco testes distintos estão aprovados no candidato congelado**; não se apresenta a primeira execução como uma rodada integralmente verde. O teste03 também confirmou o atalho contextual Radar → Mapa com O.S. diferente e UF preservada, mesma instância DOM, vínculo com a fonte sintética, recursos locais HTTP 200 e ausência de chamadas externas/erros JS/CSP. Os scripts realmente carregam e executam no Edge.

As quatro capturas de Mapa foram regravadas após a correção dos rótulos, as quatro de Estatísticas após carregar `#kpis .card` e as duas de login nos temas explícitos de inspeção. Há também `depois-mapa-inspetor-1440-light.png` e `depois-reflow-200.png`. As demais telas já tinham sido capturadas com os mesmos estilos. Diretório: `C:/Users/alan_/AppData/Local/Temp/cpj-apple-ap39-20261022/`. `py_compile` aprovado; o diff não apresentou erros e, como os dois arquivos são novos/não rastreados, seu conteúdo foi conferido diretamente quanto a espaços finais e marcadores de conflito. A regressão integrada é coordenada pela AP36.

## O que preservar e limites

Preservar as superfícies sóbrias, a tipografia de sistema, a ação azul identificável e a explicação da precisão municipal; PF/PJ possuem forma, legenda e texto, além da cor. A navegação compacta tem rolagem própria e mantém a aba ativa; tabelas podem rolar dentro do seu contêiner. O vidro fica restrito à camada funcional e dispõe de alternativa opaca.

Não se declara conformidade WCAG completa. Os checks medem amostra explícita de texto/controles, navegação/foco com teclado, reflow, preferências, mapa e recursos locais; não substituem leitor de tela, Switch Control, hardware móvel ou homologação humana. A seleção de tema do aplicativo foi preservada conforme determinação do operador. O login recebeu temas por atributo para inspeção visual; não se alega um comando de troca de tema na tela de login. Regressões de XSS, fontes divergentes e demais contratos de backend pertencem ao gate integrado AP36, não são certificadas por esta revisão visual isolada.
