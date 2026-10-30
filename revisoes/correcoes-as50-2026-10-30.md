# AS50 — correções da auditoria e conferência do RAG

Pedido do operador em 30/10/2026: corrigir os achados da revisão e conferir o RAG; autorização de executores paralelos. O operador esclareceu que não observou um defeito específico no RAG. Coordenador: Codex-AS50. Sem publicação, ativação de provedores ou acesso a autos/configurações operacionais.

## Candidato e fronteiras

O candidato de validação do projeto existente está em `desenvolvimento-correcoes-as50/codigo`, produzido pelo clonador sintético do runner oficial. Modelo DOCX e assinatura são exclusivamente fictícios. `desenvolvimento-correcoes-as50/baseline-sha256.json` contém hashes de código na captura inicial. Não é outra versão operacional do produto.

Os arquivos físicos da raiz com reservas anteriores foram preservados durante a implementação: `executores_llm.py` (IC91), `rotas/casos.py` (AZ01), `tarefas.py` (CX99), `rotas/relatorios.py` (CX93). A integração exige coordenação explícita dessas reservas e comparação com a fonte atual. As reservas de NO01/MP91 e suas mudanças não pertencem a AS50.

Liberação posterior expressa do operador nesta sessão: **“Sim, integre preservando as outras frentes”**. A integração de AS50 aplica somente seus trechos e fixtures de contrato; não muda responsáveis/estado das reservas anteriores. A base atual de código foi preservada em `desenvolvimento-correcoes-as50/base-integracao/`; mudanças concorrentes de NO01/MP91 foram incorporadas ao candidato sem reverter sua autoria, com mescla de três vias de `rotas/casos.py`.

## Causas e correções integradas

- AS51: escape de status no HTML; limites de tamanho, taxa e retenção no login; cache da auditoria condicionado a identidade e marca confiável de alteração, sem dispensar validação integral quando necessário.
- AS52: ficha usa revisão e atualização atômica; metadados importados validados e escapados; vínculo autenticado entre hashes de minuta/DOCX e publicação do snapshot conferido; PDF gerado em área temporária e substituído somente após sucesso.
- AS53: primeira página de Markdown com BOM preservada; falha do encoder opcional não derruba FTS; filtro de O.S. aplicado também às entidades. Ranking e modelo não foram alterados.
- AS54: transporte externo de resultado incerto não abre retry/fallback; erro após rodada já iniciada não reinicia sessão; cancelamento entre resposta e ferramenta impede escrita; pedido cancelado cujo agente morreu é encerrado, mantendo tratamento separado de intenção externa incerta.

## Evidências

AS54: RED reproduziu cancelado→pendente preso, fallback após HTTP503/transporte/JSON inválido e reinício após rodada com ferramenta. Casos adicionais reproduziram reset de conexão/resposta incompleta e escrita após cancelamento durante HTTP. GREEN: 7 testes, mais 22 UN14, 19 de orçamento, 14 verificações de provedores e 10 de roteador existentes aprovados.

AS53: RED com seis falhas nos quatro testes originais. GREEN ampliado: AS53 7/7; RG40 12/12; UI01 13/13; seleção LC01 sem modelo 11/11; consultas legadas 52 verificações. Sem skips nos cenários executados. Semântica exercitada com encoder/vetores determinísticos, sem download nem modelo real. Reindexação sintética preservou os arquivos de caso.

AS51 final: 16/16; AS52 final: 26/26 + 2/2 JavaScript; AS53 final: 8/8; AS54 final: 10/10; V05 real: 5/5. Os **67 testes focados foram repetidos e aprovados na raiz integrada**, em processos separados com fixtures temporárias; SIG01 acrescenta **12/12** e RV17 **11/11**, totalizando **90 testes de regressão**. Logs `verificacao-raiz-final.log` e `relatorios-rv17-raiz-final.log`. AR01 real de navegador e encadeamento também foi repetida ao final: **2/2**, em `analise-relatorio-ar01-final.log`. LC01 completa com modelo público copiado do cache existente, `HF_HUB_OFFLINE=1`: **26/26**, sem download. Isso valida os cenários da suíte, sem medir exaustivamente a qualidade semântica de autos reais.

O vínculo DOCX recebe HMAC com subchave própria derivada do segredo local existente. A assinatura cobre esquema, caso, nomes, dois hashes e data de emissão. RED comprovou que hashes fabricados num pacote importado podiam satisfazer o vínculo não autenticado; GREEN exige emissão local válida. Revisão independente adicional conferiu adulteração de cada campo, assinatura ausente/alterada, outra chave e outro caso, sem achar falha remanescente nesses caminhos. DOCX legado, edição manual ou documento de outra instalação exige regeneração local ou aceite humano explícito do hash específico, com justificativa; `forcar` genérico não basta. Os arquivos importados são preservados. Isso não protege contra comprometimento do segredo local.

Revisão independente reproduziu e exigiu correções adicionais no mesmo escopo: falha de auditoria/SQLite após HTTP não podia abrir fallback; parse JSON muito aninhado precisava resposta 400; `dt()` não podia devolver markup; DOCX precisava fonte snapshot para impedir troca A→B→A; resposta CAS precisava corresponder à revisão efetivamente gravada; índice legado BOM precisava reparo incremental. Cada reprodução teve RED e GREEN. Nenhum achado remanescente nos caminhos revisados. Um teste real de navegador descobriu uso incorreto de `.map` em NodeList, corrigido com `Array.from` e repetição AR01 2/2; o harness passou a reproduzir a falta de `.map`. O uso de `Object.hasOwn`, ausente no QuickJS do workspace, foi trocado pelo precedente compatível `Object.prototype.hasOwnProperty.call`, com regressão específica.

## Integração e serviço

Integração de **23 arquivos** aplicada em 30/10, com comparação de três vias quando a fonte mudou e conferência de hash antes/depois. Versões anteriores de código em `desenvolvimento-correcoes-as50/antes-integracao/`, `antes-mac/` e `antes-fixture-http/`; lista exata em `arquivos-integracao.json`, hashes em `integracao-aplicada-sha256.json`. Alterações NO01/MP91 preservadas. Nenhum commit, push ou atualização de plugin instalado foi feito.

Conferência final: 22 arquivos mantiveram o hash aplicado; `rotas/casos.py` recebeu posteriormente o seletor OCR da frente OC01, preservado. A comparação estrutural confirmou que só o import de `MOTORES_OCR` e a função de reprocessamento diferem do candidato, mantendo os trechos AS50; AS52 repetida na raiz após essa mudança: 26/26. Sintaxe dos 21 arquivos Python da lista e `git diff --check` aprovados. Hashes posteriores e resultados em `conferencia-entrega-final.json`.

A Central foi reiniciada após duas consultas locais que imprimiram apenas contagens: tarefas ativas 0 e extrações ativas 0. Somente o processo confirmado do launcher da Central foi encerrado; não se atingiram os navegadores do operador ou servidores de teste. Serviço voltou com HTTP 200; hashes de `casos.js`/`core.js` servidos conferiram com a fonte e POST de login com tipos inválidos retornou JSON 400. O teste de XSS no Edge isolado exibiu o payload como texto, sem nó de imagem nem execução de script (`browser-xss.log`).

Após a inclusão final do HMAC, a revisão automática de permissões recusou o comando que encerrava a árvore inteira do launcher (`blocked by policy`), sem motivo específico; esse comando não foi executado. Uma alternativa mais restrita foi permitida: após nova consulta com **tarefas ativas 0 / extrações ativas 0**, conferiram-se PID, comando e processo proprietário da porta 8765, encerrando **somente o servidor dessa porta** por `Stop-Process`. O launcher foi iniciado novamente, oculto. A Central voltou com HTTP 200, hashes dos dois JavaScripts corretos e login malformado retornando JSON 400. Portanto, não permanece pendência de reinício para o HMAC.

## Rodada ampla e diferenças concorrentes

Runner oficial `ferramentas/testar-tudo.py`, no candidato sintético, com Python 3.12 da `.venv`, OCR portátil, modelo público em cache e downloads desativados. Log: `desenvolvimento-correcoes-as50/suite-completa.log`. **Primeira rodada ampla encerrada: 150/161 suítes aprovadas, saída 1, em 1.413,49 s.** O runner clona o código a cada suíte; essa rodada começou antes dos ajustes finais de compatibilidade. Não apresentar seu resultado como uma execução completa da versão final nem como homologação geral.

Das 11 falhas iniciais, AR01 foi corrigida com `Array.from` sobre NodeList e repetida 2/2; SIG01 recebeu caso sintético válido e passou 12/12; RV17 recebeu DOCX real, vínculo local e hash de conferência, passando 11/11 sem perder a asserção de bytes intactos de arquivo FINAL; a fixture HTTP foi adaptada ao status específico 429 do novo limitador. Nenhum controle de produção foi afrouxado para esses testes. As sete outras suítes estão discriminadas abaixo.

**Reteste HTTP final aprovado, saída 0, em 15,125 s (`central-http-final.log`):** configuração/usuários/permissões, cadastro e processamento local do PDF fictício, busca de identificadores, referência, minuta → DOCX → FINAL → baixa, exportação criptografada/importação sem sobrescrita, bloqueio de login e pasta pessoal. O teste AS51 foi ampliado para exigir 429 da conta bloqueada, ausência de novo evento anônimo de auditoria e expiração do bloqueio; repetição 16/16 em `seguranca-as51-http-final.log`. Não houve outra alteração de produção após o último reinício.

Skips do ambiente: quatro cenários de symlink em executores RV17, dois em fontes RP33 e um de volume exFAT em SEC22. Não se declara validação dessas capacidades indisponíveis no host.

AP39: o teste ainda exige o SVG offline visível; MP91 passou a iniciar no mapa real e oculta esse SVG. Controle independente congelou dois clones com mapa/CSS/HTML/CSP idênticos e restaurou somente os 13 arquivos anteriores de AS50 num deles: `AppleUIAP39.test_03_mapa_unico_atalhos_filtro_fonte_tema_recursos` falhou igualmente nos dois, esperando `#svg-mapa-offline .mapa-ponto` (37,267 s / 36,784 s). Não corrigir silenciosamente a tarefa MP91 reservada.

AST14UI: comparação equivalente de `PaginasUI.test_carrega_proxima_pagina_fontes_e_vista_sem_salto` falhou igualmente com/sem AS50 (7,833 s / 7,374 s): recebeu “Carregando relações…” em vez de 400/405. GF10 marca o grafo pronto antes de concluir o layout; enquanto calcula, o desenho retorna antes da atualização da paginação. As fontes do grafo eram idênticas. Falha concorrente fora do escopo, sem alteração de suas asserções ou da produção GF10.

Confirmação diferencial da AST14UI completa: atual 28,391 s / controle 28,407 s, **2 aprovados e as mesmas 2 falhas em ambos**. O segundo cenário, `versao_alterada`, recebe o mesmo estado de carregamento ao esperar 400/406. Logs e hashes em `ast14ui-*-diferencial.log` e `ast14ui-diferencial-resumo.json`.

F01: 14/15 testes aprovados; a asserção restante exige interface agregada de até 350.000 bytes. A expansão atual tem 396.134 bytes; substituir somente `core.js` e `casos.js` por seus bytes anteriores de AS50, mantendo os demais recursos idênticos, resulta em 395.125 bytes e também excede o teto. O teste e o teto não foram alterados.

UN16 distribuição: o pacote omite o novo `static/vendor/leaflet/LICENSE` sem extensão, introduzido pela frente de mapa; o filtro genérico do empacotador não contempla esse arquivo. O módulo Python novo de AS50 é incluído. Registrar a pendência para a frente de distribuição/mapa; não publicar esse pacote como homologado.

AG90: execução diferencial completa com fontes atuais/controle sem AS50: **8 aprovados e as mesmas 2 falhas em ambos** (193,953 s / 194,375 s). O cenário visual aguarda a promessa de término de `mv-varrer`, cuja iteração é infinita em `HEADER::after`; o cenário de mapa aguarda o SVG offline oculto no modo real. Logs `ag90-atual-diferencial.log`, `ag90-sem-as50-diferencial.log`, prova de animação em `ag90-animacoes-diagnostico.log` e hashes em `ag90-diferencial-resumo.json`. Nenhum teste ou CSS foi alterado para passar.

OCR indisponível: prova curta atual/controle sem AS50 produz exatamente `rodar_falso() got an unexpected keyword argument 'chave'`. A mudança de cancelamento NO01 acrescentou `chave` à chamada; o stub antigo de OCR não aceita esse argumento e interrompe o processamento fictício. Fontes de `rotas/comum.py` e do teste OCR idênticas nos clones; não se trata de falha real do motor OCR nessa reprodução. Evidência em `ocr-indisponivel-diferencial-curto.log`; não alterar silenciosamente a frente NO01/OC01.

NO01: 10/11 no snapshot da rodada ampla. O caso de botões falha no harness Node com `Cannot find module '-'`, a pendência já registrada pela outra frente na fila. Não houve ajuste de código/teste NO01 por AS50.

## Limites preservados

Nenhum teste deve usar a Central operacional em 8765. Testes HTTP/navegador usam loopback em workspace fictício e portas próprias. Não reindexar dados operacionais nem fazer migração apenas para testar. Em volumes sem marca confiável de alteração, a auditoria mantém a verificação integral; não se promete custo constante em todo filesystem. A qualidade de recuperação semântica com o modelo real não é medida por fixtures determinísticas.
