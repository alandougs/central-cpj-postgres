---
name: analise-ip-fraude
description: Analisa inquérito policial de fraude/estelionato a partir da transcrição Markdown (e CSVs de tabelas) do caso, com rastreabilidade por página - ficha do caso, cronologia, pessoas e vínculos, caminho do dinheiro (vítima → contas de passagem → destinatário), matriz dos elementos do art. 171 do CP, lacunas e diligências possíveis. Use quando o usuário pedir "analisa o IP", "analisa esse inquérito", "monta a cronologia", "segue o dinheiro", "caminho do dinheiro", "quem recebeu o Pix", "cruza os dados", ou entregar transcrição/Markdown/CSV de autos de estelionato, golpe, fraude eletrônica, Pix, boleto, falso parente, falsa central etc.
---

# Análise de IP de fraude e estelionato

Transforma a transcrição dos autos em material analítico rastreável que sustenta o relatório de investigação. **Nada entra na análise sem localizador** (`pág. N do PDF`, e `fls. X` quando legível).

Base de comportamento: skill `analise-documental` (inventário → achados com localizador → contradições → pendências) e o system prompt do agente `analista-documental`. Esta skill especializa esse método para fraude/estelionato.

## Entradas

- `casos\<ID>\01-extracao\<documento>\transcricao.md` (seções `## Página N`; uma pasta por arquivo original — cite o documento quando houver mais de um: `(Doc. <nome>, pág. N)`) — ou o Markdown entregue pelo usuário (copie para `01-extracao\<nome>\transcricao.md` e registre a origem em `registro-tratamento.md`).
- `01-extracao\<documento>\tabelas\*.csv`, `entidades.csv`, `relatorio_extracao.json` (páginas pendentes/⚠), `estrutura.md` quando existirem.
- `caso.json` (ordem de serviço, referência) e, se houver, o texto da **Ordem de Serviço / determinação do delegado** — ela delimita o escopo da análise.
- Leia também `calibracao\licoes-aprendidas.md` antes de começar.

Se o Markdown do usuário não tiver marcação de página, use outro localizador reproduzível (título da peça + parágrafo, ou nº de linha) e avise que a citação por página ficará prejudicada.

## IPs grandes (100–300 páginas)

Não leia a transcrição inteira de uma vez. Divida em blocos de ~75–100 páginas e delegue cada bloco a um agente `analista-documental` (em paralelo), com saída em `02-analise\blocos\bloco-NN.md`. Em seguida consolide os blocos nos arquivos abaixo, eliminando duplicatas e apontando divergências entre blocos. Para localizar algo específico, use `Grep` na transcrição ou `rag.py buscar --caso <ID>` (skill `base-cpj`) em vez de reler tudo.

## Procedimento

0. **Escopo.** Identifique a O.S. vigente (geralmente a última) e extraia **cada solicitação do Delegado de Polícia**, gravando em `02-analise\solicitacoes-os.md` (item, trecho com pág./fls.). O relatório será feito principalmente para atendê-las (`AGENTS.md` regra 17). Se não localizar a O.S., avise o operador em CAIXA ALTA e pergunte; só assuma "análise geral para relatório de investigação" se o operador confirmar, e declare.
1. **Inventário.** Arquivos lidos, páginas cobertas, páginas pendentes/ilegíveis (de `relatorio_extracao.json`), tabelas disponíveis. Não afirme ter lido o que não leu.
2. **Ficha do caso** → `02-analise\ficha-caso.md`: referência (BO/IP/processo), natureza como consta, **modalidade** do golpe (ver tipologia em `references\tipologia-golpes.md`), vítima(s) e investigado(s) **como constam**, período dos fatos, prejuízo declarado × prejuízo documentado, meio (Pix, TED, boleto, cartão, cripto).
3. **Cronologia** → `02-analise\cronologia.md`: `| data/hora | fato | fonte (peça, pág., fls.) | natureza |` (fato documentado / relato da vítima / informação de terceiro / dado bancário).
4. **Pessoas e vínculos** → `02-analise\pessoas-vinculos.md`: nome como consta, qualificação como consta (CPF/RG só se estiver nos autos), condição (vítima, comunicante, testemunha, investigado, titular de conta destinatária, representante de empresa), páginas. Vínculos só com base documental (mesma conta, mesmo telefone, mesmo endereço, mesmo IP de acesso, sócio de empresa). Homônimos ficam separados.
   - **Obrigatório:** a mesma qualificação em forma estruturada → `02-analise\pessoas.csv` (alimenta a Pesquisa relacional e o grafo de vínculos da Central). Formato fixo:
     - separador `;`, codificação UTF-8 com BOM, cabeçalho exatamente `nome;mae;pai;cpf;rg;nascimento;telefones;enderecos;empresas;cnpj;emails;placas;condicao;paginas;documento`;
     - colunas opcionais, ao final, quando constarem nos autos: `processos;bos;veiculos` (outros IPs/TCs/processos e BOs citados para a pessoa; veículos por descrição);
     - uma linha por pessoa **por fonte de qualificação** (mesma pessoa qualificada em duas peças com dados diferentes = duas linhas; não funda registros nem homônimos);
     - vários valores no mesmo campo separados por ` | ` (espaço, barra vertical, espaço) — nunca por `;`;
     - `condicao`: vítima, comunicante, testemunha, investigado, titular de conta destinatária, representante de empresa etc., como a análise sustenta;
     - `paginas`: páginas do PDF onde a qualificação consta (ex.: `12 | 45`); `documento`: pasta do documento em `01-extracao\` quando houver mais de um;
     - **somente dados como constam nos autos**, sem completar, corrigir ou deduzir dígitos; campo sem dado fica vazio (dígito ilegível: `?`).
5. **Caminho do dinheiro** → `02-analise\fluxo-financeiro.csv` (`;`, UTF-8 BOM) e `fluxo-financeiro.md`:
   - Colunas: `seq;data;hora;valor;meio;id_transacao(E2E/NSU/autenticação);origem_titular;origem_banco;origem_ag_conta;origem_chave;destino_titular;destino_banco;destino_ag_conta;destino_chave;camada(1=vítima→1º recebedor, 2=repasse...);fonte_pag;fls;status_conferencia`.
   - Parta das tabelas CSV e dos comprovantes; normalize com o agente `analista-financeiro`. Some valores por camada e por destinatário; aponte saques, repasses, dispersão, retorno a contas da própria vítima, estornos/MED quando constarem.
   - No `.md`: diagrama textual do caminho (vítima → conta de passagem → destinatário final), totais, e o que **não** foi possível rastrear e por quê (dados ausentes, extrato não juntado, conta de destino sem qualificação).
6. **Elementos do tipo** → `02-analise\elementos-tipo.md`: matriz `| elemento | evidência (com pág.) | status: sustentado/parcial/ausente | observação |` para: artifício/ardil/meio fraudulento; indução ou manutenção da vítima em erro; vantagem ilícita obtida; prejuízo alheio; nexo entre fraude e disposição patrimonial; circunstâncias do §2º-A (fraude eletrônica), §4º (idoso/vulnerável) e §5º (representação) — consulte `references\referencias-normativas.md` e **não cite dispositivo sem conferir vigência**. Indique autoria apenas como "elementos indicativos de vinculação de X à conta/telefone Y (pág.)", nunca como conclusão.
7. **Matriz de achados, contradições e lacunas** → `02-analise\matriz-achados.md`: `| afirmação | fonte | trecho curto | natureza | confiança justificada | pendência |`, seguida de contradições entre depoimentos/documentos e lacunas (peça citada mas ausente, extrato não juntado, fls. com salto, dado ilegível).
8a. **Dados faltantes (aviso ao operador)** → `02-analise\dados-faltantes.md` e, na resposta final, **em CAIXA ALTA**, sob o título `DADOS FALTANTES — PROVIDENCIAR (OPERADOR)`: dado **muito importante** para autoria, materialidade ou circunstâncias (CF, art. 144, § 4º; CPP, art. 6º) que não consta dos autos — qualificação, objeto, pessoa, empresa, telefone, extrato, veículo, local etc. — com **onde/como obter** e **por que importa**. Procedimento e exemplos: `references\dados-faltantes.md`. Nunca complete por dedução.
8. **Diligências possíveis (uso interno)** → `02-analise\lacunas-diligencias.md`: o que falta para esclarecer; para cada item, se depende de **autorização judicial** (ex.: afastamento de sigilo bancário/fiscal, registros de conexão) ou pode ser requisitado. Este arquivo é apoio ao investigador; o relatório, por padrão, **não** sugere medidas (ver skill `relatorio-ip-fraude`).
9. **Resumo ao usuário:** 5–10 linhas com o que foi apurado, totais do fluxo financeiro, principais lacunas e dados críticos pendentes de conferência visual. Atualize o caso: `caso.py status <ID> em_analise` no início e `caso.py status <ID> analisado` ao final (skill `base-cpj`), registrando `modalidade` e `prejuizo_documentado` no `caso.json`.

## Regras

- Dado crítico (CPF, conta, chave Pix, valor, data, ID de transação) usado na conclusão precisa de **conferência visual** na imagem da página; marque `status_conferencia` = `conferido` só quando isso ocorrer (renderize a página com `pypdfium2` se preciso).
- Relato não vira fato: "a vítima declarou que..." (pág.).
- Titular de conta recebedora **não** é automaticamente autor: é "titular da conta destinatária", "possível conta de passagem".
- Divergência é achado, não erro a corrigir. Não junte homônimos.
- Não consulte fontes externas nem sistemas; OSINT de **pessoa** só se o usuário pedir expressamente (skill `osint-policial`, com dados mínimos). **Exceção autorizada:** empresa (PJ) citada sem dados nos autos → OSINT de empresa conforme `references\osint-empresas.md`; para pesquisa aprofundada use a skill `osint-policial` (fonte citada, confirmação por duas fontes, só CNPJ/razão social enviados à internet).
- **Bases de consulta** (`consulta\`, ex.: Muralha Paulista) e **relatórios de referência** (`referencias\`) **não são fonte** da análise: não copie deles qualificação, antecedentes ou fatos para os arquivos de `02-analise\`. Se o investigador informar que fez uma consulta, registre como "informado pelo investigador (sistema, data)" e trate como pendência de juntada.
- Conexões com outros casos (`rag.py cruzar`) são indício a verificar e vão para `conexoes.md`, citando os dois casos e páginas.

## Progresso (pedidos da Central / modo automático)

Quando a análise foi acionada por botão da Central CPJ, informe o avanço para a barra de progresso nos marcos do pedido (inventário, cada bloco de páginas, fluxo financeiro, elementos do tipo, `pessoas.csv`/`caso.json`):

- agente de plantão em chat: `python ferramentas\agente-plantao.py progresso <PEDIDO> --agente "<nome>" --pct <N> --etapa "<etapa>"` — se responder **CANCELADO**, pare sem concluir;
- executor automático: `python "<scripts da base-cpj>\progresso.py" <ID> <N> "<etapa>"`.

Em uso interativo (sem pedido da Central), não é necessário.

## Saída

Arquivos em `02-analise\` listados acima (inclusive `pessoas.csv`) + resumo. Rode `indexar.py` ao final para a Pesquisa relacional enxergar as pessoas do caso. Todos são material de apoio e podem alimentar o RAG (ver `rag\README.md`).
