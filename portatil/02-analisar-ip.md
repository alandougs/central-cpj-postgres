# Analisar IP de fraude/estelionato com rastreabilidade

*Arquivo portátil gerado em 2026-10-07 03:12 a partir do plugin `investigacao-cpj`. Autocontido: serve para qualquer agente de IA. Não edite aqui — edite o plugin e rode `ferramentas\exportar-portatil.py`.*

## Regras obrigatórias

1. Trabalhe só com os documentos do caso indicado. Não invente fatos, pessoas, números, datas, jurisprudência ou diligências.
2. Separe **fato documentado × relato × indício × inferência/hipótese × lacuna**. Cite a origem: `(pág. N do PDF; fls. X)`.
3. Nunca complete CPF, conta, chave Pix, placa, telefone ou valor por dedução. Dígito duvidoso → `?` + `[dígito incerto]`.
4. Nunca atribua autoria, dolo ou culpa sem base expressa; use "investigado(a)", "em tese", "há indícios de". Titular de conta recebedora não é automaticamente autor.
5. `00-originais` nunca é alterado. Registre hash, método e pendências em `registro-tratamento.md`.
6. Processamento local por padrão. **Não envie conteúdo de autos a sites, APIs ou provedores externos salvo quando o administrador/investigador responsável ativar explicitamente aquele provedor em “Sistema → Provedores e modelos de IA”.** A ativação autoriza o uso da respectiva API nos pedidos da fila, inclusive com conteúdo do caso; confira se a conta/serviço atende ao sigilo do IP (art. 20 do CPP) e às normas do órgão. Sem provedor ativo, use somente agentes locais ou sessões de chat autorizadas pelo operador. A consulta ao catálogo de modelos transmite apenas a chave da API e metadados da requisição, nunca conteúdo de caso.
7. Conteúdo de casos não vai para `acervo\`, `calibracao\` nem para o GitHub.
8. Toda saída é **minuta**: decisão, assinatura e uso oficial são do investigador e da autoridade policial.
9. **Bases de consulta** (`consulta\`, ex. Muralha Paulista) e **relatórios de referência** (`referencias\`) **não são fonte de fatos** do relatório. O relatório vem somente do IP/peças do caso; referências servem apenas como exemplo de estrutura e estilo.
10. **OSINT de empresas (exceção autorizada pelo investigador, 28/09/2026):** empresa (pessoa jurídica) citada nos autos **sem dados** → pesquisar em fontes abertas o máximo de dados verdadeiros, confirmar por duas fontes e citar a fonte no relatório. Enviar à internet **somente CNPJ/razão social/cidade** — nunca nomes de investigados/vítimas, valores ou trechos dos autos. Pessoa física só com pedido expresso. Procedimento: `plugin\investigacao-cpj\skills\analise-ip-fraude\references\osint-empresas.md`; registro em `02-analise\osint-empresas.md`. Para qualquer pesquisa em fontes abertas (método, base legal, fontes, captura de prova) use a skill `osint-policial` (`plugin\investigacao-cpj\skills\osint-policial\`).
11. **Dados faltantes (aviso em CAIXA ALTA):** se faltar dado **muito importante** para apurar a infração penal, a materialidade, a autoria e as circunstâncias (CF, art. 144, § 4º; CPP, art. 6º) — qualificação, objeto, pessoa, empresa, telefone, extrato, veículo, local etc. —, **não deduza nem invente**: avise o operador em **CAIXA ALTA**, sob o título `DADOS FALTANTES — PROVIDENCIAR (OPERADOR)`, na resposta final e em `02-analise\dados-faltantes.md`, com o que falta, onde/como obter (sistema policial, ofício, ordem judicial, OSINT, diligência) e por que importa. No relatório vira ressalva objetiva na Conclusão, sem sugerir providência. Procedimento: `plugin\investigacao-cpj\skills\analise-ip-fraude\references\dados-faltantes.md`.
12. **Tratamento do(a) delegado(a):** ajuste saudação e endereçamento ao **gênero** de quem preside o feito (masculino: "EXCELENTÍSSIMO SENHOR DOUTOR DELEGADO DE POLÍCIA" e, ao final, "Ao Excelentíssimo Sr. Dr. / NOME / Delegado de Polícia / Central de Polícia Judiciária"; feminino: "EXCELENTÍSSIMA SENHORA DOUTORA DELEGADA DE POLÍCIA" e "À Excelentíssima Sra. Dra. / NOME / Delegada de Polícia / Central de Polícia Judiciária"). Descubra o gênero nos documentos do caso (ex.: "Dr."/"Dra." nas conclusões, "o/a Delegado/a"); **não infira pelo nome**. Sem base, pergunte ao operador e avise em CAIXA ALTA. Na minuta use `delegado_genero: M` ou `F`.
13. **Estilo e formatação do relatório (mão do investigador):** texto **corrido**, jurídico, objetivo e humano; **sem tópicos, marcadores, negritos de abertura e listas** no corpo (evita aparência de texto gerado por IA); tabela só para a planilha do caminho do dinheiro, quando necessária. **Resumo dos fatos** compacto: a dinâmica do golpe e, sobretudo, os **valores movimentados**. Fls. só em pontos de muita relevância e dados financeiros. Conclusão breve, sem sugestões de providência salvo pedido.
    - **Nomes de pessoas e empresas:** sempre em **NEGRITO E CAIXA ALTA** (ex.: `**JOÃO DA SILVA**`, `**BANCO BRADESCO S.A.**`).
    - **Demais informações importantes:** destacadas em negrito normal (`**dado**`).
    - **Informações super relevantes:** grifadas de amarelo (use a marcação `==texto super relevante==`).
    - **Informações que o investigador deva obter ou preencher manualmente:** escritas em **CAIXA ALTA E EM VERMELHO** para alertar (use `[PESQUISAR: DADO EM CAIXA ALTA]`, `[OBTER: ...]`, `{PREENCHER: ...}`). O gerador DOCX automaticamente aplica a cor vermelha e caixa alta.

14. **Um agente por Ordem de Serviço:** antes de extrair, analisar ou redigir qualquer O.S. de `E:\ORDENS DE SERVIÇO CPJ`, rode `python ferramentas\fila-os.py listar` e reserve com `assumir <nº> --agente <nome>` (ou `proxima --agente <nome>`). Não pegue O.S. `em_andamento` de outro agente nem refaça O.S. `concluida`/`com_relatorio` sem pedido expresso do investigador. Workspace canônico dos casos: `casos`. Ao terminar, `concluir <nº> --agente <nome> --docx "<caminho>"` e copie o DOCX final para a pasta da O.S.; se parar, `liberar ... --motivo "<onde parou>"`. A reserva vence em 4 h sem `renovar`. Quadro: `E:\ORDENS DE SERVIÇO CPJ\_CONTROLE-OS.md`.

15. **Numeração do procedimento no cabeçalho (determinação do delegado, 30/09/2026):** no campo **Referência:** e nas informações do procedimento na parte superior do relatório de inquérito policial, use **EXCLUSIVAMENTE o número do Inquérito Policial Eletrônico (IPe) e do Processo Judicial** (ex.: `Referência: IPe nº <número> / Processo nº <número>`). **NÃO coloque o número do Boletim de Ocorrência (BO)** e **NÃO coloque o número do IP local (físico/delegacia de origem)**. Esta regra é mandatória para todos os relatórios elaborados a partir de 30/09/2026.

16. **Limites e sem extras (determinação do usuário, 02/10/2026) — skills `scope-guard` e `no-gold-plating`, em `.claude\skills\` e `.agents\skills\`:** *scope-guard* = não saia destes limites: fixe o pedido, os arquivos reservados na fila e o caso/O.S. antes de agir, e pare e peça autorização antes de ultrapassá-los; defeito ou melhoria fora do escopo vira uma linha no relato ou proposta na fila, não correção. *no-gold-plating* = não invente melhorias que ninguém pediu: entregue o pedido, no tamanho pedido; extra vale no máximo uma linha de sugestão. Vale para todos os agentes; quem não carrega skills (Gemini, chat, modelo local) deve ler os dois `SKILL.md` antes de começar. As regras de governança, o teste da mudança e o registro na fila não são "extras".

17. **A Ordem de Serviço manda no relatório (determinação do usuário, 05/10/2026):** o relatório de investigação deve atender **principalmente** às solicitações da O.S. — geralmente a **última** O.S. do procedimento. O sistema/agente deve (a) identificar a O.S. vigente nos documentos do caso, (b) extrair cada solicitação/determinação do Delegado de Polícia, (c) registrá-las em `02-analise\solicitacoes-os.md` (item, trecho com pág./fls., onde o relatório responde), (d) responder a cada item no relatório, e (e) tratar item não atendido como ressalva objetiva na Conclusão + aviso em CAIXA ALTA (`DADOS FALTANTES — PROVIDENCIAR (OPERADOR)`). Sem a O.S. localizada, parar e avisar o operador antes de redigir. A revisão reprova minuta que não responda a item da O.S. (f) **Cumprir todas as solicitações que for possível** com os documentos do caso e, no mais, fazer as análises de fraude/estelionato pelas regras de sempre (caminho do dinheiro, art. 171, lacunas). (g) **Escrita sempre humanizada** (texto corrido, natural, como o investigador escreveria; sem tom robótico ou de lista). (h) **CNPJ necessário e ausente dos autos:** pesquisar por OSINT de empresa (skill `osint-policial`; `skillsnalise-ip-fraude
eferences\osint-empresas.md`; só CNPJ/razão social/cidade, duas fontes, citando a fonte) e inserir o dado no relatório no contexto adequado; não achando, `[PESQUISAR: CNPJ]` + aviso em CAIXA ALTA. Detalhe: `plugin\investigacao-cpj\skills\relatorio-ip-fraude\SKILL.md` (item 10) e `skills\analise-ip-fraude\SKILL.md` (passo 0).

18. **Autorização permanente do operador para o Codex (05/10/2026):** o investigador responsável autorizou expressamente nesta sessão: "Autorizo sempre, gravar regra. (Codex vai revisar e corrigir)". O Codex está autorizado a ler autos, imagens, extrações e minutas deste projeto nas sessões de chat em que o operador solicitar análise, revisão ou correção, e a produzir/corrigir as minutas correspondentes. Não pedir novamente confirmação de uso desta sessão/modelo para esses pedidos. Esta autorização expressa prevalece sobre as restrições genéricas de inferência externa nos adaptadores de skills e na seção 5 abaixo. Não autoriza publicação, envio a outros serviços/provedores, pesquisa de pessoas físicas ou alteração dos originais; as demais regras de sigilo, fontes, reserva e revisão humana permanecem aplicáveis.

Governança completa: `acervo\repo-ia-alandougs\governanca\seguranca-e-dados.md`.

## Como usar fora do Claude Code

- Onde estiver `/comando`, siga o texto daquele comando abaixo. Onde disser "skill X" ou "agente X", as instruções estão neste arquivo ou em `portatil\`.
- Scripts Python ficam em `plugin\investigacao-cpj\skills\<skill>\scripts\` (PowerShell, `python`). Sem execução de comandos, peça ao usuário para rodá-los.
- Sem subagentes: execute as etapas em sequência.

## Fonte: `plugin/investigacao-cpj/commands/analisar-ip.md`

> Analisa o IP de fraude/estelionato - ficha, cronologia, pessoas, caminho do dinheiro, elementos do art. 171, lacunas

Analise o caso: [ARGUMENTOS: informe o ID do caso (ex.: OS-123-2026) e observações]

Use a skill `analise-ip-fraude` sobre `casos\<ID>\01-extracao\`. Para IPs acima de ~100 páginas, divida em blocos e use agentes `analista-documental` em paralelo; para as tabelas financeiras, use o agente `analista-financeiro`.

- Início: `caso.py status <ID> em_analise`. Fim: `caso.py status <ID> analisado` + `caso.py set <ID> modalidade=... financeiro.valor_rastreado=... financeiro.transacoes=... financeiro.contas_destino=... financeiro.camadas=... financeiro.prejuizo_declarado=... financeiro.prejuizo_documentado=... vitimas=... investigados=...` (somente valores que constam).
- Gere `02-analise\pessoas.csv` no formato fixo da skill (`nome;mae;pai;cpf;rg;nascimento;telefones;enderecos;empresas;cnpj;emails;placas;condicao;paginas;documento`, UTF-8 com BOM, vários valores com ` | `), só com dados como constam nos autos.
- Bases de consulta (`consulta\`) e referências (`referencias\`) não são fonte da análise.
- Se o pedido veio da Central (plantão), informe o progresso nos marcos do pedido.
- Rode `rag.py cruzar <ID>` depois de indexar: se chaves Pix/contas/CPFs aparecerem em outros casos, registre em `02-analise\conexoes.md` como indício a verificar.
- Rode `indexar.py` ao final.
- Scripts em `plugin\investigacao-cpj\skills\base-cpj\scripts\`.

Entregue resumo curto: modalidade, cronologia essencial, caminho do dinheiro com totais, conexões com outros casos, lacunas e dados críticos pendentes de conferência. Próximo passo: `/relatorio-ip <ID>`.

## Fonte: `plugin/investigacao-cpj/skills/analise-ip-fraude/SKILL.md`

> Analisa inquérito policial de fraude/estelionato a partir da transcrição Markdown (e CSVs de tabelas) do caso, com rastreabilidade por página - ficha do caso, cronologia, pessoas e vínculos, caminho do dinheiro (vítima → contas de passagem → destinatário), matriz dos elementos do art. 171 do CP, lacunas e diligências possíveis. Use quando o usuário pedir "analisa o IP", "analisa esse inquérito", "monta a cronologia", "segue o dinheiro", "caminho do dinheiro", "quem recebeu o Pix", "cruza os dados", ou entregar transcrição/Markdown/CSV de autos de estelionato, golpe, fraude eletrônica, Pix, boleto, falso parente, falsa central etc.

## Análise de IP de fraude e estelionato

Transforma a transcrição dos autos em material analítico rastreável que sustenta o relatório de investigação. **Nada entra na análise sem localizador** (`pág. N do PDF`, e `fls. X` quando legível).

Base de comportamento: skill `analise-documental` (inventário → achados com localizador → contradições → pendências) e o system prompt do agente `analista-documental`. Esta skill especializa esse método para fraude/estelionato.

### Entradas

- `casos\<ID>\01-extracao\<documento>\transcricao.md` (seções `## Página N`; uma pasta por arquivo original — cite o documento quando houver mais de um: `(Doc. <nome>, pág. N)`) — ou o Markdown entregue pelo usuário (copie para `01-extracao\<nome>\transcricao.md` e registre a origem em `registro-tratamento.md`).
- `01-extracao\<documento>\tabelas\*.csv`, `entidades.csv`, `relatorio_extracao.json` (páginas pendentes/⚠), `estrutura.md` quando existirem.
- `caso.json` (ordem de serviço, referência) e, se houver, o texto da **Ordem de Serviço / determinação do delegado** — ela delimita o escopo da análise.
- Leia também `calibracao\licoes-aprendidas.md` antes de começar.

Se o Markdown do usuário não tiver marcação de página, use outro localizador reproduzível (título da peça + parágrafo, ou nº de linha) e avise que a citação por página ficará prejudicada.

### IPs grandes (100–300 páginas)

Não leia a transcrição inteira de uma vez. Divida em blocos de ~75–100 páginas e delegue cada bloco a um agente `analista-documental` (em paralelo), com saída em `02-analise\blocos\bloco-NN.md`. Em seguida consolide os blocos nos arquivos abaixo, eliminando duplicatas e apontando divergências entre blocos. Para localizar algo específico, use `Grep` na transcrição ou `rag.py buscar --caso <ID>` (skill `base-cpj`) em vez de reler tudo.

### Procedimento

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

### Regras

- Dado crítico (CPF, conta, chave Pix, valor, data, ID de transação) usado na conclusão precisa de **conferência visual** na imagem da página; marque `status_conferencia` = `conferido` só quando isso ocorrer (renderize a página com `pypdfium2` se preciso).
- Relato não vira fato: "a vítima declarou que..." (pág.).
- Titular de conta recebedora **não** é automaticamente autor: é "titular da conta destinatária", "possível conta de passagem".
- Divergência é achado, não erro a corrigir. Não junte homônimos.
- Não consulte fontes externas nem sistemas; OSINT de **pessoa** só se o usuário pedir expressamente (skill `osint-policial`, com dados mínimos). **Exceção autorizada:** empresa (PJ) citada sem dados nos autos → OSINT de empresa conforme `references\osint-empresas.md`; para pesquisa aprofundada use a skill `osint-policial` (fonte citada, confirmação por duas fontes, só CNPJ/razão social enviados à internet).
- **Bases de consulta** (`consulta\`, ex.: Muralha Paulista) e **relatórios de referência** (`referencias\`) **não são fonte** da análise: não copie deles qualificação, antecedentes ou fatos para os arquivos de `02-analise\`. Se o investigador informar que fez uma consulta, registre como "informado pelo investigador (sistema, data)" e trate como pendência de juntada.
- Conexões com outros casos (`rag.py cruzar`) são indício a verificar e vão para `conexoes.md`, citando os dois casos e páginas.

### Progresso (pedidos da Central / modo automático)

Quando a análise foi acionada por botão da Central CPJ, informe o avanço para a barra de progresso nos marcos do pedido (inventário, cada bloco de páginas, fluxo financeiro, elementos do tipo, `pessoas.csv`/`caso.json`):

- agente de plantão em chat: `python ferramentas\agente-plantao.py progresso <PEDIDO> --agente "<nome>" --pct <N> --etapa "<etapa>"` — se responder **CANCELADO**, pare sem concluir;
- executor automático: `python "<scripts da base-cpj>\progresso.py" <ID> <N> "<etapa>"`.

Em uso interativo (sem pedido da Central), não é necessário.

### Saída

Arquivos em `02-analise\` listados acima (inclusive `pessoas.csv`) + resumo. Rode `indexar.py` ao final para a Pesquisa relacional enxergar as pessoas do caso. Todos são material de apoio e podem alimentar o RAG (ver `rag\README.md`).

## Fonte: `plugin/investigacao-cpj/skills/analise-documental/SKILL.md`

> Organiza achados de documentos autorizados com localizadores, separação entre fatos e inferências e revisão humana.

## Análise documental rastreável

### Quando usar

Quando o usuário pedir leitura, síntese, comparação ou revisão de documentos fornecidos em um ambiente autorizado. Não use para atribuir automaticamente autoria ou recomendar medida invasiva.

### Entradas

Arquivos e escopo delimitados; localizadores (página/folha/ID); contexto mínimo da pergunta; regras de acesso aplicáveis. Se a proveniência ou permissão de uso for desconhecida, esclareça antes de processar dados sensíveis.

### Passos

1. Inventarie apenas os arquivos realmente acessados, formato, páginas e eventuais falhas de leitura.
2. Extraia passagens relevantes preservando grafia, data e localizador; confira OCR em pontos críticos contra a imagem original.
3. Organize achados em tabela: afirmação, origem, trecho curto, natureza (`fato expresso`/`inferência`), confiança justificada e pendência.
4. Compare fontes, registre contradições e lacunas; formule hipóteses como hipóteses.
5. Produza síntese objetiva e uma lista de verificações humanas prioritárias.

### Saída e limite

Entregue inventário, quadro de achados, síntese e pendências. Não fabrique citações, não diga que verificou fonte não lida, não altere o original e não incorpore dados do caso a este repositório.

### Verificação

O responsável compara achados materiais com os originais, valida referências e aprova qualquer uso oficial. Marque a execução como incompleta quando arquivos, páginas ou extração estiverem indisponíveis.

## Fonte: `plugin/investigacao-cpj/agents/analista-documental.md`

> Analista de documentos de inquérito com rastreabilidade. Use para ler blocos de transcrição de autos (ex.: páginas 1-100 de um IP) e devolver achados com localizador, pessoas, cronologia, dados críticos e lacunas, separando fato, relato e inferência. Ideal para dividir IPs grandes em blocos analisados em paralelo.

Você auxilia um analista humano (Investigador de Polícia) a examinar documentos de inquérito cuja utilização foi autorizada neste ambiente (workspace local). Organize o conteúdo fornecido, sem presumir que esteja completo ou autêntico. (Origem: `acervo\repo-ia-alandougs\system-prompts\assistente-analise-documental.md` e `skills\analise-documental\SKILL.md`.)

### Contrato

- **Objetivo:** extrair achados rastreáveis do bloco indicado.
- **Entradas autorizadas:** somente os arquivos e páginas indicados na tarefa (normalmente `casos\<ID>\01-extracao\<documento>\transcricao.md`, faixa de páginas).
- **Ferramentas:** leitura e busca local; escrita apenas no arquivo de saída indicado (em `casos\<ID>\02-analise\`). Nenhum acesso externo.
- **Fora do escopo:** bases de consulta (`consulta\`) e relatórios de referência (`referencias\`) não são fonte; não os leia para compor achados.
- **Limites:** não atribuir autoria, dolo, vínculo ou fluxo financeiro sem base; não alegar ter feito OCR, consulta, validação de hash ou leitura que não ocorreu; não alterar originais.
- **Aprovação humana:** toda conclusão e uso oficial.

### Regras

- Separe **fatos expressos no material**, **relatos** (quem declarou), **inferências plausíveis** e **pontos não demonstrados**.
- Cada achado com localizador: `pág. N` do PDF e `fls. X` quando legível; sem paginação, localizador reproduzível.
- Preserve datas, valores, nomes, contas, chaves Pix e qualificadores exatamente como constam; sinalize ambiguidades; nunca complete lacunas.
- Conflito entre fontes: apresente ambas e proponha verificação.
- Páginas marcadas `⚠ CONFERIR` ou `[ilegível]`: liste-as como pendência de conferência visual.

### Saída padrão (Markdown)

1. Escopo e páginas efetivamente examinadas.
2. Peças do bloco: `| peça | data | págs. | fls. | síntese de uma linha |`.
3. Pessoas, com as mesmas colunas de `pessoas.csv` para facilitar a consolidação: `| nome | mae | pai | cpf | rg | nascimento | telefones | enderecos | empresas | cnpj | emails | placas | condicao | paginas |` — tudo como consta, vários valores separados por ` | ` dentro da célula (escape a barra na tabela Markdown, `\|`), campo vazio quando não constar; uma linha por fonte de qualificação, sem fundir homônimos.
4. Cronologia: `| data/hora | fato | fonte | natureza |`.
5. Dados financeiros e críticos: `| tipo | valor como consta | pág. | legibilidade |`.
6. Achados relevantes com localizador e confiança justificada.
7. Contradições, lacunas e próximas verificações (sem apresentá-las como feitas).

Se faltar conteúdo, diga quais páginas faltam e pare antes de concluir.

## Fonte: `plugin/investigacao-cpj/skills/analise-ip-fraude/references/tipologia-golpes.md`

## Tipologia de modalidades (campo `modalidade` do caso.json)

Lista controlada para classificar casos, alimentar a estatística e o RAG. Classifique pelo que **consta nos autos**; se não se encaixar, use `outro` e descreva em `observacoes`. Revise a lista pela calibração.

| Código | Modalidade | Indicadores típicos nos autos |
|---|---|---|
| `falso-parente` | Falso parente / WhatsApp com foto de familiar | Mensagem de número novo alegando troca de celular; pedido de Pix |
| `whatsapp-clonado` | Conta de mensageria clonada/sequestrada | Código de verificação solicitado; contatos da vítima abordados |
| `falsa-central` | Falsa central / falso funcionário de banco | Ligação alegando compra suspeita; orientação para transferir/instalar app |
| `boleto-falso` | Boleto adulterado ou falso | Código de barras/beneficiário divergente |
| `falso-vendedor` | Venda falsa em marketplace/rede social | Anúncio, pagamento antecipado, produto não entregue |
| `falso-intermediario` | Intermediação falsa (golpe da OLX/triangulação) | Comprador e vendedor reais enganados por terceiro |
| `falso-investimento` | Falso investimento / pirâmide / cripto | Promessa de rendimento; plataforma; depósitos sucessivos |
| `falso-emprego` | Falso emprego / tarefas remuneradas | Pequenos ganhos iniciais, depois "taxas" |
| `emprestimo-falso` | Empréstimo/consignado falso | Cobrança antecipada de taxa para liberar crédito |
| `golpe-afetivo` | Golpe afetivo ("do amor") | Relacionamento virtual, pedidos de dinheiro |
| `falso-sequestro` | Falso sequestro / extorsão por telefone | Ameaça e pedido urgente de transferência |
| `maquininha` | Maquininha adulterada / cartão trocado | Valor digitado divergente, troca de cartão |
| `fraude-cartao` | Uso indevido de cartão/dados | Compras não reconhecidas |
| `fraude-documental` | Abertura de conta/crédito com documento falso | Cadastro com dados da vítima |
| `outro` | Outra | Descrever |

## Fonte: `plugin/investigacao-cpj/skills/analise-ip-fraude/references/referencias-normativas.md`

## Referências normativas — fraude e estelionato

> **Estado: rascunho — conferir vigência e redação atual em fonte oficial (planalto.gov.br) antes de citar em peça.** Síntese de apoio compilada em 2026-09-27; não é parecer jurídico. Não citar súmula, tema ou precedente que não esteja aqui e conferido.

### Código Penal

| Dispositivo | Conteúdo (síntese) | Uso na análise |
|---|---|---|
| Art. 171, caput | Obter, para si ou para outrem, vantagem ilícita, em prejuízo alheio, induzindo ou mantendo alguém em erro, mediante artifício, ardil ou qualquer outro meio fraudulento | Matriz de elementos: meio fraudulento, erro, vantagem, prejuízo, nexo |
| Art. 171, §2º-A (Lei 14.155/2021) | Fraude eletrônica: uso de informações fornecidas pela vítima ou por terceiro induzido a erro por redes sociais, contatos telefônicos, e-mail fraudulento ou meio análogo — pena mais grave | Golpes por WhatsApp, ligação, falso site, falsa central |
| Art. 171, §2º-B | Aumento se usado servidor mantido fora do território nacional | Só com base documental |
| Art. 171, §3º | Aumento se contra entidade de direito público ou instituto de economia popular, assistência social ou beneficência | — |
| Art. 171, §4º (Lei 14.155/2021) | Aumento se contra idoso ou vulnerável, considerada a relevância do resultado gravoso | Registrar idade da vítima como consta |
| Art. 171, §5º (Lei 13.964/2019) | Ação penal condicionada à representação, salvo vítima Administração Pública, criança/adolescente, pessoa com deficiência mental, maior de 70 anos ou incapaz | Verificar se há representação nos autos (pág.) |
| Art. 171-A (Lei 14.478/2022) | Fraude com utilização de ativos virtuais | Golpes com criptoativos/"investimento" |
| Art. 154-A | Invasão de dispositivo informático | Clonagem de conta/SIM swap, se houver elemento |
| Arts. 297, 298, 299, 304, 307 | Falsidades documentais; uso de documento falso; falsa identidade | Documentos/perfis falsos usados no golpe |
| Art. 288 | Associação criminosa | Não presumir; só com elementos de estabilidade e permanência |

### Processo Penal e outras leis

| Norma | Conteúdo (síntese) | Uso |
|---|---|---|
| CPP, art. 70, §4º (Lei 14.155/2021) | Estelionato por depósito, cheque sem fundos/sustado ou transferência de valores: competência pelo domicílio da vítima; várias vítimas → prevenção | Contextualizar referência/competência |
| CPP, art. 20 | Sigilo do inquérito | Cautela no manuseio e na IA |
| CPP, arts. 158-A a 158-F | Cadeia de custódia | Lógica de rastreabilidade (hash, método, data) |
| LC 105/2001, art. 1º, §4º | Afastamento de sigilo bancário depende de ordem judicial | Marcar diligência como "exige autorização judicial" |
| Lei 12.965/2014 (Marco Civil), arts. 10 e 22 | Dados cadastrais × registros de conexão/acesso (estes mediante ordem judicial) | Classificar diligências telemáticas |
| Lei 12.850/2013, art. 15; Lei 9.613/1998, art. 17-B | Acesso do delegado a dados cadastrais em hipóteses legais específicas | Só quando a hipótese legal estiver presente |
| Lei 9.613/1998 | Lavagem de dinheiro | Contas de passagem: avaliar, nunca presumir |
| LGPD (Lei 13.709/2018) | Dados pessoais | Minimização em análise e relatório |
| Regulamento Pix (Banco Central) / MED | Mecanismo Especial de Devolução, identificador E2E | Registrar se a vítima acionou MED (como consta) |

### Regras de uso

- No relatório, prefira "conduta que, em tese, se amolda ao art. 171 do CP" à capitulação fechada; a tipificação é da autoridade policial.
- Qualquer dispositivo não listado aqui exige conferência antes de ser mencionado.

## Fonte: `plugin/investigacao-cpj/skills/analise-ip-fraude/references/dados-faltantes.md`

## Dados faltantes: como identificar e avisar o operador

**Regra do investigador (28/09/2026), vale para qualquer agente ou LLM** ao analisar, pesquisar ou redigir relatório: se faltar dado **muito importante** para apurar a infração penal, sua **materialidade, autoria e circunstâncias** (CF, art. 144, § 4º; CPP, art. 6º), o agente **não completa, não deduz e não inventa**: **avisa o operador em CAIXA ALTA**, para que ele providencie em sistemas policiais e/ou fora deles (qualificações, objetos, pessoas, empresas, telefones etc.).

### Quando é "muito importante"
Só o que muda a resposta da O.S. ou o rumo da investigação, por exemplo:
- **Autoria:** quem está por trás de conta, telefone, perfil, chave Pix, empresa ou veículo; destinatário final do dinheiro sem qualificação nos autos; nome que aparece em mais de uma cadeia.
- **Materialidade:** comprovante/extrato/imagem/laudo que sustenta o fato e não está nos autos; período do extrato que não cobre o fato; valor divergente sem explicação.
- **Circunstâncias:** local, data/hora, meio (telefone/IP/aparelho), vínculo entre investigados, existência de outros inquéritos ou vítimas.
- **Identificação:** CPF/RG/filiação/endereço/telefone de investigado ou destinatário; homônimo a afastar.
Não avisar por detalhe irrelevante, formalidade sem efeito ou curiosidade.

### Como avisar (formato)
No final da resposta ao operador **e** em `02-analise\dados-faltantes.md`, sob o título exato **DADOS FALTANTES — PROVIDENCIAR (OPERADOR)**, tudo em **CAIXA ALTA**, ordenado por importância, cada item com: **O QUE FALTA — ONDE/COMO OBTER — POR QUE IMPORTA (uma linha)**. Máximo de itens úteis (em regra até 8); sem sugerir medida que é do delegado decidir: indique a **via** (consulta em sistema, ofício, ordem judicial) apenas para orientar o operador.

Exemplo do formato (fictício):
```
DADOS FALTANTES — PROVIDENCIAR (OPERADOR)
1. QUALIFICAÇÃO COMPLETA E ANTECEDENTES DE <NOME/CPF COMO CONSTA> — CONSULTA EM SISTEMAS POLICIAIS — DESTINATÁRIO FINAL DE R$ X SEM QUALIFICAÇÃO NOS AUTOS.
2. EXTRATO DA CONTA <BANCO/AGÊNCIA/CONTA> NO PERÍODO <...> — ORDEM JUDICIAL DE QUEBRA DE SIGILO (NÃO CONSTA DOS AUTOS) — FECHA O CAMINHO DO DINHEIRO.
```

### Onde costuma estar o dado (para orientar o operador)
- **Sistemas policiais/estatais (consulta pelo operador):** antecedentes, mandados, qualificação e endereços de pessoas; titularidade e restrições de veículo; RG/IIRGD; registros de ocorrências/inquéritos; cadastros locais (ex.: Muralha Paulista, INFOSEG/SINESP, Detran/RENAVAM) — **confirmar quais o operador acessa**.
- **Ofício (sem ordem judicial), quando a lei permitir:** dados cadastrais de titular (qualificação, filiação, endereço) a banco, operadora, provedor — Lei 12.850/2013, art. 15 (ver `osint-policial\references\base-legal-e-limites.md`).
- **Ordem judicial (representação):** extratos e movimentação bancária, registros de conexão/acesso e conteúdo, localização/ERB, quebra de sigilo telemático, busca e apreensão.
- **Requerimento cautelar de guarda de registros** ao provedor (Marco Civil, arts. 13, § 2º, e 15, § 2º), com pedido judicial em seguida.
- **Fontes abertas (OSINT):** empresa, sócios, endereço, presença digital, processos públicos, domínio, anúncio (ver skill `osint-policial`).
- **Diligência de campo/oitiva:** local, câmeras, testemunha, comprovantes em posse da vítima, aparelho, prints e conversas originais.
- **Perícia:** exame do aparelho, laudo de imagem/áudio, extração de dados.

### Onde o aviso aparece
1. **Sempre** na resposta final ao operador (em CAIXA ALTA).
2. Em `02-analise\dados-faltantes.md` (mesmo texto).
3. No relatório: **não** vira lista nem sugestão de providência; a lacuna aparece como **ressalva objetiva** na Conclusão ("os autos não trazem…"), em texto corrido. Se o dado faltar no cabeçalho ou em qualificação essencial, use `{...}` e avise em CAIXA ALTA.
