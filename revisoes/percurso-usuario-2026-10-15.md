# Percurso de uso com caso fictício — 15/10/2026

Tarefa OF02 · Codex-Percurso-20261015 · Análise e revisão documental concluídas; conferência visual no Word pendente. Mudança de autenticação solicitada separadamente: OF03.

## Objetivo e limites

Percorrer o caminho PDF → extração → análise → minuta DOCX → conferência no Word e no PDF original, conforme preferência do operador. Observar redução de trabalho manual, profundidade analítica, sustentação de conclusões e visibilidade das lacunas. O ensaio não substitui revisão ou assinatura humanas nem certifica uso oficial.

Somente dados sintéticos, em workspace descartável. Nenhum caso, modelo com assinatura, usuário ou configuração da produção foi copiado. O código executado é uma cópia do produto. Ajustes no próprio harness são registrados separadamente e não são correções da Central. Não haverá definição de FINAL nem baixa de produção.

## Materiais e isolamento

- Raiz do ensaio: `C:/Users/alan_/AppData/Local/Temp/cpj-percurso-of02-2f7108f7a8d2427fad7e7c185ce09c0b`.
- Central: `http://127.0.0.1:58331`, somente local; workspace `sandbox/`, independente da produção.
- Fonte: `fixture/autos-ficticios-of02-100p.pdf`, 100 páginas/peças sintéticas, 97 nativas e três digitalizadas (15, 35 e 93). As páginas têm comprimentos variados; não se trata de certificação para cem páginas densas de autos reais.
- PDF com 260.293 bytes e SHA-256 `cee0ae35584ef263debee89eb8c1e4f0ed2b9271c1a12cbf92abfb38a447b526` antes do upload e na reconferência do original ao final da análise: íntegro.
- O.S. anterior na página 3; vigente na página 4 com cinco solicitações. Peças materialmente relevantes também entre as páginas 90 e 100. Há comprovantes repetidos, divergências de relato, homônimos, limite de rastreio financeiro e identificador incerto.
- Gabarito e mapa de peças ficam em `fixture/`, fora do workspace da Central; não são fornecidos ao executor. A avaliação independente tem acesso a ambos.
- Modelo DOCX, investigador, dados padrão e material de calibração são fictícios. A apresentação no modelo institucional real não está sendo certificada.

## Percurso observado

| Passo | Ação e resultado efetivamente observado |
|---|---|
| Entrada | Tela de login → configuração inicial; administrador descartável criado pela interface. |
| Cadastro | Seleção do PDF em Nova O.S.; prévia retornou “Nenhum campo novo detectado”, apesar de identificadores e O.S. em texto nativo. Foram preenchidos manualmente O.S., IPe, Processo, requisitante e resumo da determinação a partir do próprio PDF. |
| Extração | Modo padrão Inteligente; sem API de visão ativa, interface informou processamento somente local. Processo concluiu as 100 páginas em 42 s (11:12:49–11:13:31 no registro local), com 97 páginas nativas e três de OCR português. |
| Acompanhamento | Ficha apresentou estado extraído, 100 páginas e método de extração. Metadados adicionais continuaram pendentes; foi necessário atualizar/reabrir a ficha para observar o estado final. |
| Pedido de IA | Esteira Completa acionada pela interface; confirmação e modal de consentimento `claude (CLI)` aceitos para o material fictício. Não foi usado endpoint alternativo sem consentimento. |
| Navegador do ensaio | Uma confirmação JavaScript foi exibida como diálogo nativo da janela Codex, bloqueando CDP; a ferramenta de navegador não a reportou como diálogo. Foi resolvida por teclado no diálogo observado. Fila consultada antes de retomar: zero pedidos, impedindo duplicação. Trata-se de limitação da instrumentação, não defeito comprovado da Central. |
| Worker | Agente `OF02-Claude` registrado na sandbox. O worker embutido foi desabilitado deliberadamente por `CPJ_SEM_AGENTE_EMBUTIDO=1`; helper executa somente o grupo autorizado usando os métodos reais da fila. A ausência inicial de agente é consequência do harness e não achado de UX. |

## Tentativas e falhas preservadas

Primeiro grupo: `fluxo-f0500667ee`, com quatro pedidos dependentes (`analisar`, `financeiro`, `relatorio`, `revisar`), preferido `OF02-Claude` e consentimento `cli:claude` registrado pela interface. O primeiro pedido `ia-92c4aa075a` falhou em autenticação e os três dependentes foram cancelados normalmente. Não houve análise ou minuta concluída nessa tentativa.

O préflight inicial herdou APPDATA normal e indicou login ativo; o worker redirecionava APPDATA para uma pasta fictícia e, nesse ambiente efetivo, o préflight retornou sem autenticação. A preparação foi inadequada para conferir a autenticação do executor. O helper foi corrigido para manter o ambiente normal do CLI, sem ler/copiar credenciais e preservando CPJ_WORKSPACE na sandbox. Uma consulta posterior no ambiente normal também retornou sem autenticação. Portanto, não se estabeleceu uma causa única para a falha: o teste não prova expiração da sessão normal nem que somente o isolamento a causou. O grupo não foi reexecutado; não houve login, ativação de outro provedor ou nova tentativa de inferência automática.

Métricas da tentativa falha: duas chamadas registradas; tokens e custo indisponíveis, medição incompleta. Não representam cobrança comprovada. Evidências em `infra/fluxo-f0500667ee-execucao.json`, logs do pedido e préflights.

## Observações de confiabilidade já verificadas

Na página 35, a imagem original mantém `9?00-0000 [dígito incerto]`. Uma ocorrência da transcrição ficou `9700-0000 [dígito incerto]`, enquanto outra preserva o `?`. A revisão independente identificou corrupção de dígito pelo OCR apesar de confiança reportada de 93,6%. O relatório de extração não marcou páginas pendentes nem para conferência visual; a avaliação de qualidade marcou a página híbrida com `precisa_ia: true`. O redator conferiu a imagem e manteve a incerteza nos apoios, na minuta e no DOCX. A sequência incorreta não foi propagada ao relatório. Esse erro pertence à transcrição; a compensação manual foi necessária para obter o resultado correto.

## Análise e revisão concluídas nesta sessão

Após a falha do executor, um agente desta sessão leu as cem páginas da transcrição em quatro blocos e conferiu imagens das peças materiais, inclusive anexos finais. Produziu análise, cronologia, individualização, matriz de achados, atendimento dos cinco itens da O.S., fluxo financeiro, lacunas e minuta. Não recebeu o gabarito. Outro agente realizou avaliação independente, com acesso ao gabarito e ao PDF, sem redigir ou editar a minuta. Isso é complementação interativa assistida, não êxito da esteira automática do produto.

Os sete eventos financeiros únicos confirmam R$ 24.000,00 pagos, R$ 18.000,00 repassados, R$ 2.000,00 restituídos e prejuízo líquido financeiro de R$ 22.000,00. A parcela aritmética de R$ 4.000,00 não foi confundida com o saldo bancário total de R$ 4.770,00. Comprovantes repetidos não foram somados novamente; homônimos permaneceram distintos; titularidade não foi convertida em autoria; rastreio parou em L2, sem destino posterior inventado. Peças relevantes das páginas 90–100 foram consideradas.

Na revisão da v01, **24 grupos identificados de afirmações materiais foram sustentados, zero parcialmente sustentados e zero sem suporte**, consideradas as ressalvas expressas. Os cinco itens da O.S. receberam resposta, inclusive limites do que as peças permitem. Esse recorte não certifica todos os fatos possíveis nem dispensa revisão humana. O laudo enumera afirmações, fontes e limites em `avaliacao/revisao-independente-v01.md`.

O DOCX v01 foi gerado pelo endpoint real `POST /api/casos/OS-002-2026/docx`, HTTP 200, com minuta explícita `minuta-v01.md`. A inspeção do XML confirmou os 17 parágrafos do corpo, telefone incerto preservado, referência apenas IPe/Processo, realces amarelos e alertas vermelhos. O gerador informou o campo de escrivão ausente; o dado não foi inventado para eliminar o alerta. Não houve FINAL nem baixa; o caso permanece em minuta. A geração foi feita por API após instabilidade da instrumentação do navegador, sem alegar verificação do clique na interface.

V02 criada após a revisão: exatamente cinco linhas alteradas (versão, aspas exteriores do metadado escrivão, duas citações próximas e crases do domínio). Não houve alteração dos fatos, valores ou limites. O avaliador reconferiu as citações no PDF e aprovou esse diff restrito. O DOCX v02 também foi gerado pelo endpoint real, HTTP 200; mantém o alerta legítimo de escrivão ausente. V01 e seu laudo foram preservados. Minuta v02 SHA-256: `4682d32197ec107d3abc7a52148d4e4e7fcd2d8ee193d60a41416b6a46eff550`.

Revisão posterior à exportação v02: os 17/17 parágrafos do corpo correspondem ao Markdown, as duas referências estão presentes, crases e aspas exteriores desapareceram, `?` foi preservado e `9700-0000` permanece ausente. Placeholders do cabeçalho e do corpo estão em vermelho `FF0000`. DOCX com 232.627 bytes. Hash do original foi reconferido novamente, sem alteração. Esses resultados são documentais/estruturais; a avaliação visual continua pendente.

Indexador copiado executado com `CPJ_WORKSPACE` explicitamente fixado na sandbox: uma ficha na base fictícia, 14 arquivos, 143 trechos, 28 entidades e 13 registros de pessoas no índice derivado. Não houve indexação no workspace de produção. OF02 foi devolvida à fila como disponível, com o ponto exato de continuidade, sem registrar conclusão integral enquanto falta a conferência visual.

## Conferência no Word e limitação do ambiente

A sessão foi interrompida fisicamente por Escape e retomada após pedido expresso do operador. O Word instalado foi localizado e houve tentativa de abertura pelos métodos nativos. Uma janela intitulada “Word (Produto Não Licenciado)” foi observada transitoriamente, mas não permaneceu disponível; as chamadas de abertura retornaram `launch_app timed out`. A recuperação não produziu janela estável para abrir e conferir o relatório. Isso não comprova a causa do encerramento e não foi atribuído à Central.

O renderizador canônico foi tentado com o runtime Python fornecido pelo Codex: falhou por `LibreOffice soffice.exe was not found on PATH`. A tentativa anterior com a `.venv` do produto não tinha `pdf2image`; usar o runtime correto resolveu essa dependência, mas não a ausência do conversor. Não foi instalado software nem alterada ativação do Office. Inspeção XML não substitui avaliação visual de paginação, recortes e espaçamento. **A revisão visual no Word continua pendente**; foi solicitado ao usuário abrir o Word manualmente enquanto o restante do trabalho prossegue. Não há certificação visual do DOCX ou do modelo institucional real.

## Ajustes prioritários

| Prioridade | Evidência e impacto | Ajuste e critério de aceite propostos |
|---|---|---|
| P1 — incerteza do OCR | Página 35 contém `?` na imagem e `7` em uma ocorrência transcrita, sem pendência visual no extrator. Exigiu intervenção do redator. | Exibir e manter pendência por página/campo quando houver identificador incerto ou ocorrências contraditórias; a revisão deve mostrar a imagem original e preservar `?` até conferência. Repetir este cenário sem propagação do dígito incorreto. |
| P1 — prontidão do executor | A esteira foi aceita; o primeiro pedido falhou por autenticação e cancelou três dependentes. Préflight inicial não representava o ambiente efetivo. | Verificar autenticação no mesmo ambiente do worker antes de iniciar o grupo; mostrar executor, etapa, causa legível e dependentes cancelados. Após autenticação feita pelo operador, permitir retomada explícita sem duplicar pedidos concluídos. Não confundir login da Central com login do CLI. |
| P1 — integridade da entrega final | Achado anterior OF01: endpoint aceita DOCX vazio/divergente da minuta aprovada e registra entrega. Não foi repetido com este caso e não foi corrigido aqui. | Vincular a conferência à versão e ao DOCX realmente entregue; recusar arquivo vazio ou divergente antes da baixa. É condição anterior a confiar no fluxo Word → FINAL. |
| P2 — rastreio durante a leitura no Word | V01 tinha dois parágrafos densos de comunicações sem fls. próximas; fontes estavam em apoio separado. DOCX sem hiperlinks para o PDF. | Incluir referências próximas às afirmações materiais e permitir localizar a página da fonte com pouco esforço. V02 corrige as referências no exemplo; facilidade de navegação continua proposta de produto. |
| P2 — cadastro e origem dos identificadores | Prévia do PDF nativo não detectou campos e exigiu cadastro manual; OF01 também demonstrou IP local rotulado como IPe. | Validar detecção deste PDF e distinguir origem/tipo de cada número; não preencher IPe com IP local. Exibir pendência explícita para o que não foi detectado. |
| P3 — acabamento da exportação | V01 preservou aspas no placeholder de escrivão e crases em domínio demonstrativo. | Normalizar representação de metadados e código inline sem remover alertas. Correção aplicada apenas à minuta fictícia v02; parser/exportador do produto permanece sem alteração. |

As três constatações documentais da revisão independente são OCR, esforço de rastreio e resíduos de exportação. A falha do executor e o cadastro foram observados no percurso; os dois achados de OF01 estão identificados como antecedentes. Não se misturam hipóteses com defeitos reproduzidos. Prioridade de confiabilidade vem antes de redesenho amplo da interface.

## Acesso local sem senha — OF03

Pedido adicional do operador implementado separadamente. O modo solo já estava ativo, mas havia dois administradores ativos; a regra anterior exigia um único. Agora `config/solo.json` escolhe explicitamente `alandougs`, exigindo administrador ativo, loopback e Host local. Contas e senhas preservadas; login externo e autenticação Claude não foram alterados. Para voltar a exigir senha local, definir `ativo: false`.

Sete testes focados aprovados novamente pelo coordenador. O agente implementador registrou regressão rápida oficial 5/5 suítes e interface solo E02 4/4; sem nova suíte integral. Serviço reiniciado pelo supervisor oficial após conferir zero pedidos/trabalhos ativos. HTTP real sem cookie: `127.0.0.1` e `localhost` retornaram `solo: true`/`alandougs`; Host externo retornou `solo: false`/usuário nulo; POST sem `X-CPJ` retornou 403. Essa mudança é do produto, autorizada no pedido de retomada; não altera a separação dos dados do ensaio.

## Dados faltantes do cenário

**DADOS FALTANTES — PROVIDENCIAR (OPERADOR): EXTRATO L2 E DESTINO POSTERIOR; IDENTIDADE CIVIL DO INTERLOCUTOR E VÍNCULO COM OS TITULARES; CONTATO LEGÍVEL E DADOS TÉCNICOS; QUALIFICAÇÃO COMPLETA; EXISTÊNCIA/CNPJ DA ANUNCIANTE; DOCUMENTAÇÃO DO EQUIPAMENTO; IDENTIFICAÇÃO DO ESCRIVÃO OU ESCRIVÃ.** São lacunas deliberadas da simulação, registradas em `02-analise/dados-faltantes.md` e ressalvadas na minuta. Não pesquisar pessoas/empresas fictícias nem completar os campos por dedução.

## Materiais para continuidade

Raiz absoluta do ensaio: `C:/Users/alan_/AppData/Local/Temp/cpj-percurso-of02-2f7108f7a8d2427fad7e7c185ce09c0b/`. Originais em `sandbox/casos/OS-002-2026/00-originais/`, análise em `02-analise/`, minuta e DOCX em `03-relatorios/`, laudo independente em `avaliacao/`. Preservar v01 e evidências da tentativa automática falha. Nenhum conteúdo do caso foi colocado no GitHub, acervo ou calibração da produção. A raiz é temporária e deve ser preservada até a conferência visual pendente.

- [Minuta fictícia v02 em DOCX](C:/Users/alan_/AppData/Local/Temp/cpj-percurso-of02-2f7108f7a8d2427fad7e7c185ce09c0b/sandbox/casos/OS-002-2026/03-relatorios/RELATORIO-OS-002-2026-v02.docx)
- [PDF original fictício](C:/Users/alan_/AppData/Local/Temp/cpj-percurso-of02-2f7108f7a8d2427fad7e7c185ce09c0b/sandbox/casos/OS-002-2026/00-originais/autos-ficticios-of02-100p.pdf)
- [Laudo independente e addendo v02](C:/Users/alan_/AppData/Local/Temp/cpj-percurso-of02-2f7108f7a8d2427fad7e7c185ce09c0b/avaliacao/revisao-independente-v01.md)
