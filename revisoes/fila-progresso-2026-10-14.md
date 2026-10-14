# FP01 — atividade e previsão da fila

Pedido: esclarecer o que a extração está fazendo e mostrar estimativas por arquivo e para a fila. A tela anterior repetia a última página do OCR durante as tabelas, sem explicar a etapa; a barra usa pesos das fases e não informa duração. O backend já fornece etapa, progresso, início/fim e páginas. A mudança utiliza esses campos, sem alterar o worker ou reiniciar a Central em uso.

Cada arquivo mostra atividade descrita, posição/etapa quando conhecida, tempo decorrido, previsão aproximada e horário de término. Os que aguardam têm posição e previsão acumulada de início/término. O resumo distingue ativos, aguardando, erros e previsão total. A página corrente aparece somente durante extração/OCR; durante CSV a descrição explica a criação das tabelas. Uma etapa desconhecida mantém o texto informado pelo servidor, sem inventar sua posição. Arquivos concluídos mantêm páginas e duração; erros mostram a fase e a mensagem.

## Método e limites

O histórico vem exclusivamente dos trabalhos concluídos já retornados por `/api/fila` (janela atual de12h). Só se comparam mesmo formato e modo. Com páginas conhecidas, usa-se a mediana de duração por página; sem elas, a mediana por arquivo semelhante. Para o ativo, subtrai-se o tempo decorrido. Na ausência de histórico, somente o OCR com avanço e pelo menos15s pode usar extrapolação inicial do progresso publicado; as etapas posteriores aguardam dados medidos.

A faixa exibida é heurística: metade a duas vezes a previsão central, com mínimo positivo e janela superior mínima de30s; não é intervalo estatístico de confiança. Esperas e términos são somados conforme o worker sequencial. Uma duração desconhecida impede fechar a previsão total e os horários posteriores; não é tratada como zero. Duração acima do histórico aparece como recalculando. Falta de mudança observada por60s é descrita como observação, sem afirmar que travou. A observação reinicia ao recarregar a página. Datas inválidas/futuras não geram contagem falsa.

As estimativas podem variar bastante conforme OCR, tabelas, conteúdo e processamento visual. Não medem uma fase interna que o backend ainda não publicou e não abrangem análise/redação de IA após a extração. Horários seguem o relógio local do navegador. O módulo não faz chamadas de rede próprias, não grava dados, não usa armazenamento persistente e não envia conteúdo externo. Falha de atualização mostra aviso e preserva os últimos cartões.

## Aplicação e compatibilidade

Aplicado por dois trechos delimitados do HTML e um módulo novo na Central primária: referência ao script e renderização da fila. O teste de reversão normalizada confirmou preservação de RP01 e dos demais trechos; cópia anterior e hashes em TEMP `cpj-fp01-aplicacao-0jrx_n71`. O servidor ativo não foi reiniciado. HTML e módulo responderam HTTP200. O operador precisa atualizar a página para carregar a interface.

Portado à branch ASTRA sem mudar seu controlador: leitura compartilhada, guarda de sessão, intervalo adaptativo e atualização de HTML preservados. O helper é isolado em IIFE própria, com apenas o novo namespace público `CPJFilaProgresso`; os globais anteriores não foram encapsulados. O carregamento continua clássico e local, agora18 scripts. Isso revê explicitamente a restrição de IIFE da migração16 para este módulo novo; testes de ordem/semântica existentes foram mantidos.

## Validação

TDD: cinco testes iniciais falharam por ausência do módulo; o Edge falhou pela ausência do novo resumo. Depois, um cenário reproduziu a perda de etapa desconhecida antes do ajuste. O novo conjunto tem nove testes: oito de cálculo/contrato e um Edge real com API fictícia, tempos, fila acumulada, falta de base, atualização503, recuperação, texto hostil escapado e preservação da atividade. O primeiro ensaio do harness revelou mock de Popen herdado; foi removido apenas do setup do navegador, conforme o teste UI já existente. Não foi falha do produto nem foi contado como RED de comportamento.

A fixture não contém o brasão oficial ignorado: seus404 são limitação já conhecida; o novo módulo responde200 e a asserção de pageerror é estrita. Capturas somente fictícias em TEMP `cpj-fp01-fila-ficticia-com-previsao.png` e `cpj-fp01-fila-ficticia.png`. O teste15 antigo foi alinhado à etapa real `extração/OCR` e às novas descrições, mantendo verificação de todos os status, página e atualização sem refresh. Resultados finais e comandos ficam no registro FP01 da fila compartilhada.

A rodada geral101/103 e as medições ASTRA anteriores referem-se ao snapshot anterior à FP01. Esta alteração tem testes focais próprios; não se atribui à nova versão uma execução geral nem benchmark que não foi repetido.

Resultado final: FP01 **9/9** na Central primária (4,552s) e na ASTRA;26 testes F01/UX01/consentimento verdes, RP01 **7/7** com Edge, AST16 **4/4**, política15 **7/7**, UI15 **5/5** e E2E17 **1/1** (25,101s). A asserção de status cancelado foi reproduzida antes do ajuste: uma fila apenas cancelada não aparece como concluída. Após esse último ajuste, os9 FP01 foram repetidos nas duas fontes. Logs em TEMP `cpj-fp01-*.log`. Nenhuma estimativa foi validada como promessa de prazo nem houve benchmark de precisão.
