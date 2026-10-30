# Integração de vínculos — IV02 — 27/10/2026

Escopo autorizado: rota de consulta, store autoritativo de vínculos, teste RP32 e esta evidência, exclusivamente no candidato isolado. Não alterados indexar.py (reservado RI01), tarefas, interface, autos, configurações ou índices operacionais. Fila IV02 reservada por Codex-IV02.

## Diagnóstico e correção

RED RP32 original: 12 testes, duas falhas. A criação manual por API de CPF com `?`/`[dígito incerto]` retornava 200; a exclusão por payload legado retornava 400 enquanto o teste esperava 200. O coordenador já havia reproduzido ambas também na revisão anterior a RG40; esta rodada confirmou no candidato atual.

O primeiro achado era defeito real: a rota chamava `R.chave_no` antes da validação bruta de `vinculos_manuais._dados`, removendo o marcador de incerteza e oferecendo ao store um identificador diferente do recebido. A recusa já existente no store foi extraída para `recusar_identificador_incerto`, reutilizada pela rota antes de normalizar e pelo store antes de formar a chave. Mesma classificação de tipos e mesmo detector de incerteza existentes; nenhum dígito foi completado ou inferido. O teste ampliado exercita 10 tipos, dois marcadores e ambos os lados da relação (40 combinações), exigindo recusa direta no store e HTTP 400, sem publicação de eventos autoritativos. A rodada RED ampliada também demonstrou que o vazamento produzia eventos e contaminava uma asserção de grafo posterior; após a correção os 12 testes passam em processo limpo.

O segundo achado era expectativa legada: a API atual exige exclusivamente `id`, `caso` e `versao`, evitando exclusões ambíguas e preservando CAS. O produto não foi rebaixado ao payload antigo. O teste passou a criar relações idênticas em duas O.S., preservar uma aresta documental idêntica, recusar o payload legado (400), o caso divergente (404) e a versão divergente (409), excluir somente a fonte manual identificada e conferir a durabilidade após reindexação sintética. A direção origem/destino da relação restante é conferida. A existência da anotação manual não remove a evidência documental.

## Verificações

GREEN em processos isolados e dados fictícios: RP32 12/12; grafo API GF01 11/11; AST06 store 27/27; interface RP35 no Edge 4/4. Total 54 unittest aprovados, zero skips nessa seleção, além das 40 combinações de incerteza dentro do cenário RP32. Store cobre eventos/CAS, concorrência, migração de legados, reindexação derivada, pacotes autenticados, backup/restauração e preservação de fonte; RP35 cobre rótulos com HTML/apóstrofos, direção da remoção, fonte/O.S. e isolamento por ID. AST dos três Python alterados e diffcheck restrito IV02 aprovados.

A mudança é anterior à normalização e não altera proteções de caminho/junção, regras de projeção, estrutura de eventos ou a coordenação da fila. Nenhuma reindexação operacional nem chamadas a IA/APIs reais foram feitas; apenas os testes reindexam workspaces TEMP. Não limpa retroativamente registros que já tenham sido cadastrados por versões anteriores. Se existirem em operação, a investigação documental e decisão de revisão continuam humanas; não há base para identificá-los nesta manutenção sem ler os casos, fora do escopo. Full integrado fica com o coordenador após congelamento.
