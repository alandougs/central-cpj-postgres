# Pesquisa aplicada RP31 — documentos e rastreabilidade

Data: 22/10/2026. Responsável: Codex-Dev-RP31. Escopo autorizado: pesquisar referências, corrigir defeitos existentes reproduzidos e propor funções novas. Esta entrega preserva UN10–UN18; não cria implementação concorrente. Leitura restrita a código, instruções e documentação pública; testes em TEMP com `CPJ_WORKSPACE` e `CPJ_SEM_AGENTE_EMBUTIDO=1`. Sem autos, configuração, usuários, assinatura ou modelo operacional.

## Referências primárias e aplicação

O Paperless-ngx registra alterações documentais e oferece histórico. Suas versões mantêm arquivo e texto extraído associados; selecionar uma versão troca prévia e download. A revisão sugerida usa uma caixa de entrada cujo marcador só é removido após conferir metadados. A busca considera conteúdo e campos. São padrões úteis para vincular revisão, resultado e arquivo específico. Sua edição de PDF pode alterar o original e invalidar assinatura: essa operação não deve ser transplantada à CPJ. Fonte: [uso, versões, histórico e fluxo recomendado](https://github.com/paperless-ngx/paperless-ngx/blob/dev/docs/usage.md#document-file-versions). Consulta em 22/10; ramo `dev` é mutável, e esta pesquisa não certifica uma versão instalada.

A API do Paperless separa pesquisa textual de acesso documental e inclui identificação do resultado e realces. Isso ajuda a distinguir o trecho encontrado do documento a conferir. Fonte: [API, pesquisa](https://github.com/paperless-ngx/paperless-ngx/blob/dev/docs/api.md#searching-for-documents). O OCR possui modos distintos e pode evitar OCR quando já existe texto suficiente. A lição aplicável é declarar método e condição de processamento. Fonte: [configuração de OCR](https://github.com/paperless-ngx/paperless-ngx/blob/dev/docs/configuration.md#PAPERLESS_OCR_MODE). O site de documentação retornou 403 em parte das consultas; foi utilizado o repositório oficial, sem contornar o acesso.

O IPED apresenta visualizadores de texto, metadados, hexadecimal e formatos nativos, além de indexação e marcadores. Isso não exige reproduzir todos os visualizadores na Central. Fonte: [recursos oficiais](https://github.com/sepinf-inc/IPED/blob/master/README.md#features). O manual distingue retomada do último ponto persistido (`--continue`) de reinício do processamento incompleto (`--restart`), explica hashes e permite compor relatórios por marcadores selecionados. A existência de um marcador organiza o exame; não demonstra autoria ou veracidade. Fonte: [manual, retomada](https://github.com/sepinf-inc/IPED/wiki/User-Manual#--continue-and---restart), [hashes](https://github.com/sepinf-inc/IPED/wiki/User-Manual#hashes), [relatório](https://github.com/sepinf-inc/IPED/wiki/User-Manual#report-creation). Há seções de interface apenas esboçadas no manual; não se atribuiu a elas comportamento não documentado.

Na API do IPED, documento é endereçado por `sourceID` e `id`; conteúdo original, texto e miniatura têm operações próprias. Os marcadores recebem pares de origem e item. É uma referência concreta para não perder o caso ao construir um link. Fonte: [Web API, documentos e formatos](https://github.com/sepinf-inc/IPED/wiki/Web-API#documents).

## Comparação com a Central atual

Custos abaixo são estimativas qualitativas de engenharia para o uso solo, sem orçamento comercial. Não se propõe instalar Paperless/IPED, copiar código, adicionar servidor ou substituir a arquitetura.

| Capacidade existente CPJ | Lacuna real ou limite observado | Ideia adaptada e prioridade | Custo / risco | Evidência |
|---|---|---|---|---|
| Ficha única por O.S., documentos e arquivos | O link do mapa descartava o identificador do caso presente no caminho | P0: preservar vínculo caso + caminho e recusar contradição, corrigido nesta tarefa | Baixo; fonte inconsistente passa a não oferecer abertura direta | `inteligencia-mapa.js:133`, teste RP31; par origem/item da API IPED |
| Link PDF com página | Aceitava página negativa e booleano como número | P0: âncora apenas para inteiro positivo seguro; folhas permanecem independentes, corrigido | Baixo; página inválida abre documento sem âncora | Teste RP31 em Edge |
| Prévia DOCX de texto/tabelas, PDF inline e download do original | Prévia não reproduz toda a diagramação; aviso explícito já existe | Manter esse contrato; não anunciar visualização fiel do Word | Sem novo custo; revisão visual integral exige original | `rotas/casos.py:519–612`, UX02 12/12 |
| Relatórios versionados, controle de concorrência e conferência por versão/hash | Não foi demonstrada nesta tarefa perda de versão ou aceite de conferência antiga | Preservar contratos já existentes; associar qualquer futura tela de comparação à versão selecionada (P1, proposta) | Médio; UI e evidência precisam acompanhar a mesma versão | `rotas/relatorios.py:175–217,285–351`; padrão de versões Paperless |
| Pendências OCR e métodos por documento | Estado técnico concluído não comprova revisão humana de todo o texto | P1, proposta: facilitar acesso ao documento, método e pendência na revisão existente | Baixo/médio se houver demanda; evitar nova marca de aprovação automática | `index.html:1163–1165`, `casos.py:pendencias-ocr`; fluxo de caixa de entrada Paperless |
| Extração com hash e checkpoint por página | Nenhuma falha nova de retomada foi reproduzida | Preservar hash/parâmetros e retomada; integrar pela ordem canônica UN10–UN18 | Sem mudança nesta tarefa; invalidar checkpoint incorreto custa reprocessamento | `extrair.py:9–13,84–86,207–258`; manual IPED |
| Busca FTS com caso, arquivo, página, fls., seção e trecho | Fonte de busca é transcrição/derivado; abrir esse arquivo não equivale a conferir PDF original | P1, proposta: explicitar a natureza da fonte e eventual ligação ao original quando já houver relação documentada | Médio; não inferir correspondência entre nomes de PDF/derivado | `rag.py:48–71`, `index.html:1517`; pesquisa/API Paperless |
| Índice armazena `pagina` e `fls` separadamente | Remissão textual pode virar numeração de folha do trecho, reproduzido | P0: encaminhado ao responsável por `indexar.py`; só aceitar numeração documentada, sem dedução | Médio; compatibilidade de derivados deve ser ensaiada | Sonda TEMP abaixo; `indexar.py:151–161` |

## Defeitos e correção RP31

O inspetor de mapa recebe uma ocorrência com caso A e fonte `casos/B/00-originais/autos.pdf`. O código anterior retirava `casos/B/` e montava `/arquivo/A/00-originais/autos.pdf`. Dois arquivos homônimos sintéticos em A e B comprovaram HTTP 200 contendo o marcador de A; a fonte declarada pertencia a B. Não é necessário atravessar o diretório no backend para produzir essa troca de evidência na interface.

Antes de editar produto, a regressão executou no Edge real: dois testes, um FAIL e controle válido PASS em 31,812 s. O erro foi o link incorreto `/arquivo/OS-931-2099/00-originais/autos.pdf#page=2`, em vez de ausência de link diante da contradição. Mais dois REDs demonstraram `fonte.caso` divergente e página `-1`; ambos falharam em 21,786 s. A coordenação ampliou a reserva para `app/static/js/inteligencia-mapa.js` antes da alteração.

A correção limita-se à construção do endereço: recusa identificador/caminho contraditório, raiz absoluta, unidade Windows, controles e segmentos vazios/parentais. Caminhos relativos e caminhos `casos/<mesmo-id>/...` continuam aceitos. Não troca o caso declarado por outro caso. A página só gera `#page=N` para PDF com inteiro positivo seguro; texto de folhas, booleanos e valores inválidos não criam âncora. Nenhuma rota, esquema ou permissão foi alterada.

## Achado encaminhado: folhas derivadas de remissão

Uma sonda executou `indexar.py` real em workspace TEMP contendo somente um caso fictício e esta transcrição:

```markdown
## Página 1
O despacho determina consultar as fls. 30 dos autos.

## Página 2
Folha sem numeracao fisica e sem remissao.
```

Retorno do indexador: zero. Consulta `SELECT pagina, fls, texto FROM trechos ORDER BY pagina`: página 1 recebeu `fls='30'`; página 2 recebeu `fls=NULL`. O texto apenas remete a folhas e não documenta a numeração física da própria página. O esperado conservador é página 1, folha desconhecida, mantendo a remissão no conteúdo. A primeira sonda comprovou a saída, mas falhou ao limpar TEMP por conexão SQLite aberta pelo próprio diagnóstico. O diagnóstico seguinte fechou explicitamente a conexão e limpou TEMP; já observou `fls=NULL` nas duas páginas, após alteração concorrente do arquivo pelo responsável RP32. Sua asserção que caracterizava o comportamento antigo falhou por esse motivo. Esses detalhes de diagnóstico não são falhas do produto.

Encaminhado ao coordenador e RP32, responsável pela reserva de `indexar.py`; esse arquivo não foi alterado por RP31. Um mapa manual PDF × fls. constitui função nova e permanece somente proposta, não solução presumida para dados ausentes.

## Verificação e limites

Comandos usando `.venv/Scripts/python.exe`, cada arquivo em processo próprio:

| Comando (prefixo `plugin/investigacao-cpj/app/testes/`) | Resultado |
|---|---|
| `teste_rastreabilidade_rp31.py` | 4/4, 19,382 s, Edge real e HTTP real |
| `teste_correlacoes_mapa_etapa1.py` | 7/7, 8,154 s |
| `teste_visualizador_relatorios_ux02.py` | 12/12, 1,591 s |

Os testes RP31 cobrem arquivo homônimo errado, caso declarado divergente, caminhos absolutos/parentais, página inválida, distinção de fls., Unicode/espaços/caracteres especiais, caminho Windows/relativo e bytes originais preservados. O harness compartilhado verifica ausência de pedidos externos e erros de página/CSP. Nenhum cenário ignorado nessa seleção. A suíte completa congelada é responsabilidade do coordenador; estes resultados não representam o gate geral nem certificação operacional. PRD e síntese serão atualizados pela tarefa RP30 reservada ao coordenador.

## Segunda revisão corretiva RP35 — consumidor do grafo

A coordenação reservou `static/index.html`, o novo `teste_grafo_interface_rp35.py` e este documento; depois ampliou a reserva para adaptar o DOM fictício de `teste_grafo_interface_gf02.py`. Foram reproduzidos quatro cenários em Edge real, sessão Flask real e workspace TEMP, antes de editar produto: 4/4 falharam em 17,799 s.

O primeiro defeito era execução de JavaScript persistido: o inspetor inseria valores escapados para HTML dentro de atributos `onclick` que continham código JavaScript. O navegador decodificava as entidades antes de interpretar o evento. Uma relação fictícia `x');window.rp35=1;//` cadastrada pela API executou a atribuição ao clicar em remover. O escape impedia criar um elemento HTML, mas não impedia interpretar a string como programa nesse contexto. O teste também verificou que texto com `<img ...>` permanecia texto. Um nome legítimo `P:D'Ávila` quebrava o mesmo mecanismo ao abrir o formulário de criação de vínculo.

O segundo defeito perdia os dados de origem: o formulário enviava `caso_id` e `fonte`, enquanto a API esperava `caso` e `obs`. A API respondia sucesso, mas a anotação acabava associada ao escopo global e sem a observação digitada. O terceiro defeito reconstruía a aresta a partir do nó inspecionado, invertendo origem e destino quando o operador selecionava o nó de chegada. Também omitia a O.S., gerando ambiguidade entre vínculos de casos diferentes.

A correção substitui os eventos com valores interpolados por funções que recebem os valores originais em memória. Os textos continuam escapados para HTML. O inspetor retém a aresta real; a remoção envia seus extremos na direção original, a relação integral e o caso registrado em sua fonte, independentemente do nó inspecionado. O formulário passa a enviar `caso` e `obs`. Essa observação continua sendo anotação manual, sem conversão automática em documento comprovado. Nenhum backend, permissão, CSP, rota ou esquema foi alterado na RP35.

O teste final exige que o rótulo malicioso não execute código, a remoção retorne HTTP 200 e a relação integral realmente desapareça. Confere a persistência da O.S. e observação no histórico autoritativo e verifica que remover uma aresta pelo nó de destino preserva a aresta equivalente da outra O.S. Confere ainda nomes legítimos com apóstrofos. Uma repetição intermediária encontrou colisão entre dois identificadores da própria fixture: o primeiro botão correspondia ao vínculo criado por outro teste. A fixture foi corrigida para usar identificadores distintos; as asserções de status e persistência foram mantidas.

Regressão GF02 inicialmente passou 9/10: o DOM simulado não possuía `querySelector`/`querySelectorAll`, necessários para ligar eventos com segurança. A correção ficou no harness reservado, que agora representa os elementos e seus eventos; todas as asserções anteriores foram preservadas. Não foram adicionados desvios de teste ao produto.

| Verificação final RP35, `.venv/Scripts/python.exe` | Resultado |
|---|---|
| `app/testes/teste_grafo_interface_rp35.py` | 4/4, 35,902 s; Edge, sessão e HTTP reais; zero erros de página/CSP/pedidos externos |
| `app/testes/teste_grafo_interface_gf02.py` | 10/10, 0,609 s; sintaxe e regressões do grafo |
| `app/testes/teste_grafo_api_gf01.py` | 11/11, 2,700 s; backend real em TEMP |

Sem cenários ignorados nessa seleção. Arquivos congelados para o gate único do coordenador. Novas funções permanecem apenas propostas; nenhuma instalação, publicação, migração, serviço pago, inferência por API ou execução com conteúdo operacional.
