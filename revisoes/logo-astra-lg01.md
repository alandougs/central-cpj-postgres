# LG01 — logo própria ASTRA

Pedido expresso de 30/10/2026: substituir o brasão no sistema web por identidade ASTRA, moderna e com movimento, usando as cores do tema. A proposta anterior com nome Alan Douglas foi descartada pelo operador.

Marca vetorial local: A geométrico verde, órbita e estrela. Animação suave da órbita por dois ciclos, desligada com prefers-reduced-motion. Sem bibliotecas, chamadas externas ou dependências novas.

Arquivos: static/astra-logo.svg e static/css/astra-brand.css. Integração planejada no favicon, cabeçalho e três telas de acesso de static/index.html, mantendo textos institucionais.

Reserva inicial recusada: PRD.md pertence a AS50 e index.html pertence a IA91. Esses arquivos não foram alterados por LG01 enquanto reservados. Coordenação de liberação/integracão solicitada ao operador. Registro para futura atualização da seção 9 e histórico do PRD após liberação.

Validação: Edge headless com Playwright, sem APIs ou dados de casos: SVG carregado, animação astra-orbit ativa, prefers-reduced-motion desliga a animação, capturas claro/escuro conferidas e viewport 390px sem overflow. Script de conferência temporário: %TEMP%/astra-lg01-preview.cjs; capturas astra-lg01-dark.png e astra-lg01-light.png.

Integração exata pendente em index.html: favicon /static/astra-logo.svg com type=image/svg+xml; carregar /static/css/astra-brand.css?v=lg01 após apple-cpj.css; substituir as quatro imagens de brasao-pcsp.png por astra-logo.svg, alt="Logo ASTRA" e classes brasao-hd/brasao-lg por astra-mark. Manter textos institucionais e demais alterações.

Operador autorizou mensagem de coordenação à IA91. A ferramenta send_message_to_thread recusou o envio ao chat identificado como provável coordenador (Executar o programa): "already has an active writer". Mensagem não entregue; não presumir liberação nem integração.

30/10/2026 — autorização posterior expressa do operador: "Autorizo alterar somente o trecho da logo no index.html, preservando o trabalho da IA91. Insira a logo no ASTRA e confira se ficou funcionando." Exceção restrita à reserva de index.html; IA91 mantém sua reserva e seu trabalho. LG01 reassumida pelo script. PRD segue reservado por AS50 e não foi editado.

Aplicadas seis substituições pontuais no HTML lido imediatamente antes da edição: favicon, quatro imagens e inclusão do CSS da marca. Bytes do restante do documento preservados, com conferência de concorrência antes da gravação e cópia anterior em %TEMP%/astra-lg01-index-before.html.

Integração validada em 30/10/2026: servidor ativo 127.0.0.1:8765 entrega HTML e assets idênticos aos locais (HTTP 200). Edge carregou o HTML servido com APIs/scripts operacionais bloqueados e somente recursos estáticos locais; quatro imagens decodificadas, favicon SVG correto, marca de 104px nas três telas de acesso e 52px no cabeçalho. Mobile claro 390px: logo 44px e cabeçalho sem overflow. Captura do cabeçalho conferida em %TEMP%/astra-lg01-integrado.png. Reversão das seis substituições reproduziu integralmente o HTML anterior, comprovando preservação dos outros trechos da IA91. Teste de animação e movimento reduzido repetido e aprovado. Scripts: %TEMP%/astra-lg01-integration.cjs e astra-lg01-preview.cjs. Sem acesso a casos, reinício, migração ou publicação.

Estado: logo integrada e servida pelo ASTRA; basta atualizar a página aberta. Registro no PRD permanece pendente exclusivamente pela reserva AS50, com evidência completa neste documento.
