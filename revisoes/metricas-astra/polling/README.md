# AST15 — coleta de polling

Estado: comparação executada em janela exclusiva, 36/36 amostras auditadas, exit0. Nenhum teste ou Edge concorrente foi executado pelo integrador/equipe durante a coleta. Fonte, método e resultados abaixo; homologação humana pendente.

Instrumento autocontido no snapshot oficial: `plugin/investigacao-cpj/app/testes/astra_polling/measure.cjs`; fontes dos cinco módulos anteriores em `antes-fontes.json.gz` no mesmo diretório. O gzip preserva literalmente os textos UTF-8 anteriores, sem dados de casos. A comparação troca somente esses cinco módulos; HTML, CSS e demais módulos são comuns às duas variantes e seus hashes entram no raw. O bootstrap normal é desativado para isolar o polling; APIs são sintéticas locais e não há servidor operacional/executor.

Comando previsto (passar caminhos absolutos do snapshot):

```powershell
$env:NODE_PATH = "<runtime>/node_modules"
& "<runtime>/bin/node.exe" "<app>/testes/astra_polling/measure.cjs" "<app>" "<app>/testes/astra_polling/antes-fontes.json.gz" "<saida>/raw.json.gz"
```

Foram seis cenários × três repetições × duas variantes: início ocioso, caso ocioso, caso ativo constante, outra aba com caso aberto, erro de tarefas e aba oculta emulada. Ordem pareada alterna por repetição. Edge headless, viewport 1440×1000/DPR1, janela de 5200 ms após o ciclo inicial. Requests incluem o ciclo inicial; mutações separam a primeira pintura das seguintes. O fluxo de OCR e mudanças de tarefa é validado pelos testes HTTP/Edge, não por este benchmark de tarefa constante.

Limites: MutationObserver conta mutações, não repaints de compositor; CDP LayoutCount/RecalcStyleCount/TaskDuration são métricas distintas. Heap é memória JavaScript do renderer, não RAM total do navegador nem CPU do sistema. Oculação é explicitamente emulada, sem alegar throttling nativo. Host compartilhado pode afetar tempos. Sem requisição a origem externa permitida. Dados raw comprimidos sem perda, contagens/latências por pedido, hashes e versão do navegador permitem auditoria.

Focais coletados nesta etapa: 7 testes determinísticos de política/timeout/sessão + 5 testes reais Edge/HTTP; regressões 63 (AST09/10/12/16, Explorer, AR01, UX01, GF02, navegação e F01). Logs do trabalho sob `%TEMP%/cpj-ast15-*.log`. A homologação humana e a suíte global final seguem sob coordenação do integrador; este registro não declara produção homologada.

## Resultado pareado

Coleta UTC: 2026-10-14T19:33:31.757Z → 2026-10-14T19:37:15.063Z. Edge 155.0.4283.45, Windows 10.0.26200, x64. As contagens foram idênticas nas três repetições de cada variante. Requests incluem o ciclo inicial; DOM conta apenas mutações após essa primeira pintura. P50/p95 usa nearest rank; n=3 por cenário/variante, insuficiente para afirmar significância estatística.

| Cenário | GET tarefas antes → depois | GET fila antes → depois | Mutações DOM estável antes → depois | CDP TaskDuration p50/p95 ms antes → depois |
|---|---:|---:|---:|---:|
| Início ocioso | 4 → 1 | 4 → 1 | 9 → 0 | 67.4/88.8 → 61.0/67.2 |
| Caso ocioso | 8 → 1 | 0 → 0 | 3 → 0 | 69.3/86.0 → 67.2/68.5 |
| Caso ativo constante | 8 → 4 | 0 → 0 | 6 → 0 | 82.4/87.4 → 68.2/89.6 |
| Outra aba com caso aberto | 8 → 1 | 0 → 0 | 3 → 0 | 77.7/98.2 → 75.7/78.3 |
| Erro503 de tarefas | 4 → 2 | 0 → 0 | 0 → 0 | 63.1/75.9 → 79.5/79.9 |
| Aba oculta emulada | 8 → 0 | 0 → 0 | 3 → 0 | 67.2/76.6 → 57.9/87.8 |

No caso ocioso, GET tarefas caiu 87,5%; no ativo 50%; Início teve 75% menos GET tarefas/fila. A aba oculta emulada não iniciou leituras, com pausa e retomada verificadas também pelos testes. O erro 503 teve 2 leituras na janela, por backoff; retry permanece GET. Estes percentuais descrevem as janelas e fixtures medidas, não toda utilização da Central.

O cenário de erro teve **aumento** de TaskDuration p50 enquanto passou a renderizar erro recuperável visível; portanto não há ganho universal de tempo. A ausência de alterações DOM estáveis não é prova de ausência de repaints do compositor. As latências são da API sintética deste instrumento, sem extração/SQL reais; com menos pedidos, a proporção de primeira conexão versus conexões aquecidas também muda. Não se atribui a esses números melhoria de latência do backend. Métricas CDP de layout/recalculo e heap, além das latências individuais, constam de summary.json/raw.json.gz. Não se afirma redução de RAM, CPU total ou FPS. A fixture não inclui a imagem institucional ausente no código estático; a requisição 404 comum às variantes não integra os GET de API medidos e não sustenta avaliação visual dessa imagem.

## Auditoria e reprodução

- `raw.json.gz`: dados brutos sem perda, 36 amostras, horários/pedidos/respostas e CDP. SHA256: 034694fab394c385eee57b6cc2d4a2328680529f380cc19689d9b87904e5013c.
- `summary.json`: p50/p95, contagens, limites e oráculos 36/36.
- `snapshot.json`: hashes dos 22 arquivos congelados (código/assets e instrumento), origem e método; a identidade da medição é esse manifesto, pois o trabalho integrado ainda tinha alterações coordenadas não commitadas.
- `source-validation.json`: snapshot intacto e cinco módulos do worktree iguais aos medidos. A auditoria posterior repetiu ambas as comparações.
- Fontes anteriores no gzip de testes preservam o conteúdo textual com finais de linha normalizados para LF na leitura Python; não são alegadas como cópia binária CRLF do Git. As duas variantes usam os mesmos demais recursos, com hashes no raw.
- Utilitário `app/testes/astra_polling/summarize.py` confere conclusão, 36 amostras, métodos GET, status esperados (503 somente no cenário de erro), uma resposta por pedido, contagens, zero mutações estáveis depois, ausência de erro JS/rede externa e hashes. Nenhum oráculo usa dado real ou mascara truncamento.

A coleta não validou extração/OCR real, agente real nem persistência de relatório; as transições foram exercitadas nos testes HTTP/Edge fictícios. Nenhum POST é repetido pelo instrumento ou pelo retry de polling. A suíte geral e a homologação humana seguem sob coordenação do integrador.
