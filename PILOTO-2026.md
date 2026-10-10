# Piloto Controlado da Central CPJ — 2026

**Estado em 10/10/2026:** piloto executado e auditado. Tentativa 1 falhou explicitamente em 403,85 s; tentativa 2 concluiu as quatro ações em 859,75 s com plugin 0.3.2, preservando as evidências anteriores. A minuta automática precisou de correção Codex v02 e de três registros obrigatórios ausentes. P01 conclui a medição e auditoria do piloto fictício, sem certificar conformidade integral automática ou uso oficial. A execução fictícia foi autorizada em 09/10/2026; OAuth foi especificamente autorizado e confirmado pelo integrador antes da inferência.

## Objetivo

Executar uma vez o fluxo com um IP inteiramente fictício, em workspace temporário isolado, para medir o funcionamento da análise, revisão e geração do DOCX. O piloto não define FINAL nem registra baixa de produção.

## Roteiro proposto

1. Criar um novo workspace com `mkdtemp`, mantido para retomada até a conferência do piloto, e configurar `CPJ_WORKSPACE` exclusivamente para esse diretório; remover `CPJ_WORKSPACES` do ambiente dos processos.
2. Gerar quatro páginas sintéticas (três nativas e uma digitalizada), com IPe, Processo, O.S. vigente, gênero documentado e movimentos coerentes definidos no gerador **antes** do recebimento/hash. Usar nomes declarados fictícios, CPF zero e contatos/contas mascarados. Não copiar nem consultar pastas reais em `casos/` ou ordens de serviço.
3. Processar o PDF localmente, incluindo OCR da página digitalizada, e conferir que a transcrição e os artefatos do caso ficaram dentro do workspace temporário.
4. Após concluir a conexão OAuth autorizada, executar pelo fluxo automático do Claude Code as etapas de análise documental, análise financeira, redação da minuta e revisão independente, nessa ordem, conforme o piloto fictício já autorizado.
5. Usar a geração real de DOCX com um modelo estrutural CPJ 2026 inteiramente fictício no temporário; verificar abertura, seções, referências e tratamento documentado. O preparo não usa a assinatura ou o timbre institucional real. Não gerar FINAL nem baixa; a reindexação do produto poderá gerar derivados de produção somente no TEMP.
6. Registrar resultados agregados nesta ficha e manter os artefatos temporários para conferência. Limpar somente após concluir a revisão do piloto e confirmar que nenhum arquivo foi criado/alterado nas pastas reais de casos ou produção.

## Ambiente histórico observado em 01/10/2026

- Binário: resolvido por `plantao.claude_exe()`; Claude Code `2.1.286`.
- Autenticação: `loggedIn: true`, `claude.ai`, plano Pro (verificado em 2026-10-01; nenhum segredo ou identificador de conta registrado).
- Plugin habilitado no CLI: `investigacao-cpj@cpj-local`, versão instalada `0.2.0`.
- Fixture: gerador sintético E2E local, quatro páginas; nenhum dado de caso real.
- Primeira chamada de IA: **ainda não realizada**.

## Preparação verificada no loop de 09/10/2026

O executável Claude não foi encontrado no PATH nem nos três locais previstos pelo atualizador (Claude Desktop, instalação npm e extensão VS Code). A autenticação e a versão instalada registradas acima são históricas, não foram confirmadas neste PC.

Foi criado um workspace exclusivamente fictício em `C:\Users\alan_\AppData\Local\Temp\cpj-piloto-p01-2wmtk6lz`, com o PDF de quatro páginas do gerador E2E existente. A primeira extração, sem caminho do Tesseract no ambiente do subprocesso, deixou a página 4 pendente; isso foi registrado, sem atribuir sucesso de OCR. Repetida com o Tesseract do PDF24 e o idioma português do projeto, a extração retornou zero em **5,34 s**, com três páginas de texto nativo e uma de OCR, sem páginas pendentes ou marcadas para conferência. `CPJ_WORKSPACE` apontou somente para o temporário e `--sem-reaproveitar` impediu busca em outros casos. O PDF original sintético foi preservado.

Comando da extração: `extrair.py <pdf-ficticio> --saida <temporario>/01-extracao/piloto-ficticio --workers 2 --sem-reaproveitar`. Python 3.12.14 do runtime Codex, bibliotecas locais via `PYTHONPATH`, UTF-8 e Tesseract configurados apenas para o processo de teste. A preparação e suas métricas estão em `preparacao.json` no temporário; não são produtos oficiais.

Não foram executadas análise automática, redação, revisão ou geração de DOCX do piloto. Custo, tokens, retrabalho e achados do revisor permanecem **não medidos**. P01 não pode ser encerrada como concluída até o executor automático estar disponível e o fluxo real fictício ser verificado.

## Novo preparo isolado em 10/10/2026

Workspace: `C:\Users\alan_\AppData\Local\Temp\cpj-piloto-p01-20261010-bv315iwl`. O preparo anterior foi apenas consultado; seus arquivos não foram alterados. A nova fixture está declarada em `preparar_piloto.py`, com quatro páginas, O.S. vigente, IPe e Processo fictícios, vítima, investigado mencionado em relato, recebedora e destinatário de repasse distintos. A fonte documenta a Delegada como Dra./gênero feminino. CPF zero, telefones, contas e chave Pix mascarados; nenhuma identidade é inferida. Os valores permitem conferir desembolso, devolução, prejuízo, repasse e saldo sem dupla contagem.

O original foi criado uma vez, registrado e tornado somente leitura. SHA-256: `236e24a49ecebba537cc4102acc7accceb35c3bf38eb01b367481c8c0a635f40`. Não houve edição posterior do PDF nem das fontes extraídas para melhorar resultados. A extração real retornou zero em **8,09 s**, com três páginas nativas e uma com OCR português, confiança **94,7%** na página digitalizada, sem pendentes de transcrição visual ou páginas de conferência no relatório da extração. Tabelas, entidades, consolidação JSON e qualidade executaram localmente e retornaram zero.

**Limitação observada:** `qualidade.json` classifica a página 4 como híbrida, pontuação 90, `precisa_ia: true`, pelo motivo “Imagem grande”, embora o OCR tenha produzido texto. Essa sinalização não foi removida e não autoriza uma chamada externa adicional. O piloto deverá registrar como a análise/revisão trata a imagem e o texto, sem atribuir qualidade final apenas ao retorno da extração.

`piloto_harness.py` prepara o contrato sem inferência por padrão. A execução futura usa os métodos reais `Plantao.enfileirar("esteira")`, `executar_pedido`, `pos_processar` e `concluir`, mantendo a cadeia de quatro pedidos e os checkpoints do produto. Antes de chamar o CLI, registra o horário do consentimento criado pelo harness de teste para a ação já autorizada, confere OAuth e CL03 e aplica o limite operacional de tempo. Esse registro não representa clique do operador na interface nem inventa horário da mensagem de autorização. O consentimento canônico usa o usuário fictício, destino `cli:claude` e escopo `api_ia`. Não ativa provedor API nem troca o executor. Configuração, identidade de teste, modelo DOCX e dados padrão existem somente no TEMP.

Cinco verificações locais passaram na rodada final em **3,50 s**: quatro páginas e hash preservado; ausência de liberação bloqueando antes do subprocesso; consentimento e cancelamento nos gates reais; coleta apenas do evento terminal de uso/custo, mantendo campos ausentes como indisponíveis; gerador DOCX real com modelo fictício, arquivo reaberto e tratamento feminino. Esse DOCX é teste de contrato descartável, **não** produto de um fluxo de análise por IA concluído.

O harness coleta tempos das etapas e do pós-processamento, tentativas, ajustes, versões, resultados do revisor e `usage`/`modelUsage` do último evento `result` de cada sessão. O custo reportado será registrado como **equivalente API estimado pelo CLI**, separado de cobrança do plano Pro, que permanece indisponível. Eventos intermediários não são somados novamente. Campos ausentes não viram zero. Essa distinção segue a [documentação oficial de custos do Claude Code](https://code.claude.com/docs/en/costs), conferida em 10/10/2026. O harness adotou **900 s para o grupo completo como escolha operacional local de teste**, ajustada pelo integrador para comportar as quatro ações e a revisão, sem alterar orçamento ou tarifas do produto nem atribuir ao usuário uma autorização financeira específica. O core atual não oferece limite de tokens/custo para CLI, e nenhuma tarifa foi inventada. Falha, cancelamento ou produto fora do contrato deve ficar registrado como piloto não concluído; sucesso de uma etapa não certifica o fluxo inteiro.

Comando local já verificado, sem inferência:

```powershell
& 'C:\Users\alan_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' 'C:\Users\alan_\AppData\Local\Temp\cpj-piloto-p01-20261010-bv315iwl\piloto_harness.py'
```

O comando de execução liberada e os parâmetros obrigatórios estão no `README-piloto.md` do TEMP. Não foi executado. Custo real reportado, tokens reais, retrabalho e achados de revisão permanecem não medidos. Um único caso curto não sustenta recomendações de novos papéis.

## Métricas a registrar

| Métrica | Método |
|---|---|
| Tempo | Horário de início/fim e duração de cada etapa (extração, análise documental, análise financeira, redação, revisão e DOCX), além do tempo total. |
| Custo/uso | Registrar tokens e custo em USD se o CLI os reportar. Se o plano Pro não expuser custo por chamada, registrar isso como indisponível e anotar apenas a métrica de uso realmente exibida; não estimar valores. |
| Retrabalho | Quantidade de novas tentativas, versões da minuta, alterações após a revisão e intervenções manuais necessárias para concluir cada etapa. |
| Achados do revisor | Contagem por categoria e gravidade, indicando quantos foram confirmados na fonte fictícia, quantos eram falsos positivos e quantos ficaram sem resolução. |
| Saída | Etapas concluídas/falhas, arquivos gerados, rastreabilidade das afirmações e validação de abertura do DOCX. |

Recomendações de mudança de papéis serão limitadas ao que essas observações sustentarem. Um único caso sintético curto não permite inferir desempenho em autos extensos; se a amostra não for suficiente, o resultado será “evidência insuficiente”.

## Segurança e limites

- Conteúdo inteiramente inventado; nenhum documento, resultado ou identificador de caso real será usado.
- Extração e preparação locais. A inferência fictícia foi autorizada pelo operador; a conexão OAuth foi especificamente autorizada e concluída antes da primeira execução. Nenhum conteúdo real foi usado.
- O agente deve trabalhar com `cwd` no workspace temporário, sem WebFetch, WebSearch ou conectores MCP.
- Se uma etapa tentar acessar um caminho de caso real, usar dado não sintético ou gravar fora do temporário, interromper o piloto.
- Toda saída é minuta de teste; nenhum relatório será usado oficialmente.

## Aprovação do roteiro

- Execução fictícia P01: **autorizada**, conforme pedido e respostas do operador em 09/10/2026; horário exato da mensagem não registrado.
- Conexão OAuth da conta: **autorizada especificamente e concluída**, conforme confirmação do integrador antes da primeira execução. Não houve acesso aos arquivos de credenciais.

## Resultados

Primeira tentativa real: workspace `C:/Users/alan_/AppData/Local/Temp/cpj-piloto-p01-20261010-bv315iwl`, hash original preservado. A esteira real concluiu `analisar` (financeiro interno e consolidação), mas o pedido financeiro seguinte declarou que as saídas anteriores estavam corretas e as manteve intactas. O controle de atualização rejeitou `fluxo-financeiro.md`; os pedidos de relatório e revisão foram cancelados. O piloto não está concluído e não produziu DOCX de IA.

Tempo total observado: **403,85 s**, dentro do limite operacional original de 900 s, que não foi alterado posteriormente. Sessões CLI: **118,399 s**, **197,742 s** e **72,769 s**, todas com retorno terminal `success`, modelo runtime **claude-opus-5-5**. A terceira sessão foi corretamente reprovada pela Central após o retorno. Não houve intervenção humana ou alteração Codex nos produtos durante essa execução.

Custo equivalente API reportado pelos três terminais: **US$ 2,4557518**; cobrança da assinatura Pro permanece indisponível. Tokens reportados, incluindo cache cumulativo das sessões: 88  de entrada, 32.702  de saída, 2.438.319  de leitura de cache e 164.212  de criação de cache (**2.635.321** no total dessas categorias; não são páginas ou tokens únicos de conteúdo). Os três terminais registram zero buscas/coletas web, e os logs observados não contêm ferramentas Web/MCP.

`metricas-piloto.json` original permanece intacto. Sua coleta por checkpoint omitiu a terceira sessão, pois o retorno/log era gravado somente após validar os produtos. A auditoria independente de todos os três logs foi registrada em `auditoria-uso-tentativa01.json`, com hashes e métricas completas, sem somar eventos intermediários. Isso motivou a preservação do retorno/log antes do gate em TS06, junto da comunicação explícita no prompt de que todas as saídas devem ser conferidas e novamente gravadas nesta execução, mesmo existentes. O guard, os fatos, as fontes e os timestamps não foram flexibilizados ou manipulados.

Auditoria Codex parcial efetivamente realizada: a imagem da página 4 foi conferida contra o OCR, sustentando PX-02  de 1.200, saldo de 1.200 e ressalva sobre autoria. O fluxo e a consolidação preservam desembolso 2.500, devolução 500, prejuízo 2.000, repasse 1.200 e saldo 800, sem somar saldo a transferência. Sem minuta/revisão produzidas, seus achados ainda não podem ser classificados. Esta auditoria não é revisão humana nem autorização de uso oficial.

Retrabalho observado: uma sessão financeira redundante de **72,769 s / US$ 0,487062 equivalentes API**, seguida de interrupção do fluxo; correção de contrato TS06 e instalação subsequente são intervenções técnicas reais, a contabilizar com a nova tentativa. A nova execução será preparada em outro workspace, com **1.800 s de limite operacional de teste**, escolhidos pelo integrador para comportar as sete sessões previstas. Isso não muda a execução encerrada nem atribui orçamento financeiro ao operador. Não se recomenda acrescentar papéis com esta amostra; primeiro medir a repetição e completar o fluxo corrigido.


## Tentativa 2 encerrada e auditoria efetiva — 10/10/2026

Novo workspace independente: `C:/Users/alan_/AppData/Local/Temp/cpj-piloto-p01-20261010-tentativa02-zuyq9iil`. PDF gerado antes do recebimento a partir da mesma fonte sintética, mesmo SHA-256 registrado acima; nenhum produto ou log da tentativa anterior foi reutilizado. Extração local 5,15 s, quatro páginas (3 nativas/1 OCR,94,7%). Cinco contratos fictícios aprovados4,274 s antes da inferência. Executado `piloto_harness.py --executar --aceite-em <timestamp-do-harness> --oauth-confirmado --plugin-confirmado --segundos 1800`, Python 3.12.14 da `.venv` reparada, `CPJ_WORKSPACE` exclusivo e `CPJ_WORKSPACES` removido. O aceite registra a ação fictícia já autorizada; não simula clique humano. Handle 87464 terminou exit0; OAuth e cache 0.3.2 foram previamente confirmados pelo integrador. Nenhuma nova API foi ativada.

Quatro pedidos concluídos, sete sessões CLI do modelo runtime `claude-opus-5-5`. Métricas automáticas originais preservadas: `metricas-piloto.json`, sucesso técnico=true, falha=null,859,75 s. Limite operacional1800 s escolhido antes da chamada, sem alterar orçamento/tarifas do produto. Tempos abaixo são terminais CLI, distintos do tempo do grupo e da preparação:

| Sessão | CLI (s) | Equivalente API reportado (USD) |
|---|---:|---:|
| Financeiro dentro de analisar |111,715|0,6343982|
| Consolidação |163,918|0,9795504|
| Financeiro separado (repetição) |92,333|0,6277552|
| Redação |111,383|0,7603212|
| Revisão inicial |150,894|0,8816358|
| Ajuste automático |55,436|0,4712772|
| Revisão final |142,734|0,9578278|

Total tentativa2 **US$ 5,3127658 equivalentes API**. Tokens dos sete últimos eventos terminais: entrada 138, saída 78.565, leitura de cache 3.629.809, criação de cache 376.869, total cumulativo **4.085.381 incluindo cache**. Não representa tokens únicos, preço de assinatura ou comprovante de cobrança Pro. `auditoria-uso-tentativa02.json` guarda uso/modelUsage e hashes de todos os terminais; pequenas caudas decimais binárias dos campos float foram preservadas no JSON, apresentação arredondada a7 casas. As duas tentativas somam **US$ 7,7685176 equivalentes API** e6.720.702 tokens incluindo cache;403,85+859,75=1263,60 s de execuções, sem incluir instalação, diagnóstico e correção.

Auditoria de ferramentas da tentativa2:46 PowerShell,42 Read,11 Write,1 Edit,2 Glob,3 Grep;58 alvos de caminho explícito conferidos, nenhum fora do TEMP para escrita ou fora dos procedimentos aprovados para leitura. Comandos PowerShell examinados: dados fictícios relativos ao TEMP e scripts locais do plugin. Zero WebFetch/WebSearch/MCP nos logs; terminais reportam zero buscas/coletas web. Trata-se de auditoria das ferramentas registradas, não prova de confinamento físico da máquina. Não foram carregados autos reais, configurações reais nem arquivos de credenciais.

### Achados, versões e intervenção

Revisão inicial do Claude:37 sustentadas/5 parciais/0 não-localizadas/0 contraditórias. Recuperada do conteúdo Write no log em `auditoria-codex/revisao-inicial-recuperada.md`, pois a revisão final sobrescreveu o mesmo nome. Cinco apontamentos procedentes: natureza extra; prejuízo como cálculo e citação; falta de determinação externa versus proibição; máscara integral versus parcial; vínculo limitado aos autos. Quatro resolvidos no ajuste automático, natureza parcialmente resolvida; três sugestões adicionais de frase, cautela verbal e renderização de asteriscos aplicadas. A revisão inicial considerou sustentada a presidência do IPe sem fonte expressa: falso negativo, corretamente identificado pelo revisor final. As duas fases de conteúdo da minuta v01 foram preservadas nos logs, com redação inicial recuperada separadamente.

Revisão final automática resume44 sustentadas/2 parciais, mas sua tabela tem **48 afirmações:46 sustentadas/2 parciais**. Essa inconsistência de contagem foi detectada pelo Codex; resumo original não alterado. As duas parciais reais eram atribuição de presidência à Delegada signatária da O.S. e inclusão de enquadramento não expresso em Natureza. V02 corrige ambas diretamente pela pág. 1/fls.1. Auditoria Codex v02: **48 sustentadas/0 parciais/0 não-localizadas/0 contraditórias**, com matriz completa em `rastreabilidade-v02.md` e explicação em `revisao-v02.md`. Isso não elimina lacunas documentais nem representa revisão humana.

Outros avisos efetivamente examinados: local dos fatos ausente mantido como marcador; local/data de emissão são configuração fictícia; CPF zero não identifica interlocutor e sua omissão é adequada; OCR pág. 4 foi conferido na imagem pelo Codex e pelo integrador, sem divergência. A suposta citação1|3 no fluxograma era falso positivo de resolução reduzida do integrador: original e CSV contêm2|3, preservados sem correção. Os valores permanecem2500  de desembolso,500  de devolução efetiva,2000  de prejuízo calculado,1200  de repasse,800/1200  de saldos finais; não somar saldos a transferências. Titularidade continua distinta de autoria e nome narrado de identidade confirmada. A flag local `precisa_ia` da página 4 não foi removida.

**Deficiência automática confirmada:** `solicitacoes-os.md`, `dados-faltantes.md` e `rastreabilidade-v01.md` não foram produzidos, embora obrigatórios. O revisor os remeteu ao operador; esse encaminhamento não substitui a obrigação no piloto autorizado. Foram criados explicitamente pelo Codex após encerramento, com fonte e limites, incluindo rastreabilidade posterior da v01 e nova v02. Todas as solicitações da O.S. estão atendidas no limite da fonte; nenhuma diligência real executada ou inventada. Não se declara conformidade integral sem intervenção.

Uma rodada de correção Codex após a automação:2 formulações corrigidas,3 registros obrigatórios completados,2 rastreabilidades versionadas e1 revisão Codex; zero intervenções humanas nos produtos e zero alterações Codex durante as sete sessões. V01, revisão original, métricas, sete logs, PDF e transcrição tiveram13 hashes preservados em `preservacao-antes-v02.json`. DOCXv02 gerado pelo script real, reaberto, três seções, referência IPe/Processo, tratamento/fecho femininos, valores e uma imagem idêntica à v01; sem assinatura real, sem FINAL, sem baixa. Chamada válida0,453 s; caso/index atualizados somente no TEMP, status=minuta.

Na regeneração local houve3 chamadas,2rejeitadas pela validação da imagem. Limitações do gerador detectadas, **core não alterado**: `--fluxo-csv` explícito encontra `pasta_caso` indefinida e omite imagem via aviso; `--sem-assinatura` remove também fluxograma por tratar todo parágrafo só com imagem como assinatura. A chamada válida usou `--fluxograma` com PNG já existente e modelo de teste já sem assinatura. Evidência/comando e validação estão em `auditoria-codex/validacao-v02.json`. Essas duas falhas precisam de reserva própria antes de corrigir o produto.

Retrabalho total do piloto: tentativa1 falha preservada;1 patch TS06 do contrato/log e1 instalação oficial CL07  de0.3.2 antes da segunda preparação;2 workspaces/2 execuções reais;1 ajuste automático na segunda;1 rodada Codex de correção/complementação e3 tentativas locais de gerar DOCXv02. Repetição financeira separada nas duas tentativas consumiu165,102 s/US$ 1,1148172 equivalentes API. Recomenda-se remover repetição somente se o fluxo desejado for definido e testado em tarefa própria; este piloto não refatorou a esteira. Necessário contrato de saídas que exija os três registros obrigatórios; este achado é mensurado, não corrigido silenciosamente no core. **Evidência insuficiente para acrescentar novos papéis ou extrapolar desempenho para autos extensos.**

P01 conclui execução, medição e auditoria de um caso inteiramente fictício. A amostra não certifica ausência de erros em casos reais; decisão humana de uso oficial é inaplicável ao piloto. Fontes e originais permanecem preservados; nenhum envio a GitHub ou publicação.
