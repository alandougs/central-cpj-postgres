# Pipeline completo do IP com pontos de aprovação

*Arquivo portátil gerado em 2026-10-10 05:58 a partir do plugin `investigacao-cpj`. Autocontido: serve para qualquer agente de IA. Não edite aqui — edite o plugin e rode `ferramentas\exportar-portatil.py`.*

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

## Fonte: `plugin/investigacao-cpj/commands/fluxo-ip.md`

> Executa o pipeline completo do IP - caso, processamento, análise, relatório e DOCX - com paradas para aprovação

Execute o pipeline completo para: [ARGUMENTOS: informe o ID do caso (ex.: OS-123-2026) e observações]

Sequência (pare e peça confirmação nos pontos ⏸):
0. Reserve a O.S.: `python ferramentas\fila-os.py listar` e `python ferramentas\fila-os.py assumir <nº> --agente <nome-da-sessão>`. Se a O.S. estiver `em_andamento` com outro agente ou já tiver relatório (`concluida`/`com_relatorio`), pare e avise; só refaça com pedido expresso (`--forcar`). Em trabalhos longos, `renovar` a cada etapa.
1. `/novo-caso` (se o caso não existir) e cópia do arquivo para `00-originais`.
2. `/processar-ip` → ⏸ mostre o diagnóstico e o custo de transcrição visual, se houver muitas páginas sem OCR.
3. `/analisar-ip` → ⏸ mostre o resumo (modalidade, caminho do dinheiro, lacunas) e pergunte se há diligências próprias (consultas, oitivas) a incluir e os dados do cabeçalho (O.S., delegado).
4. `/relatorio-ip` → entregue a minuta, a revisão e o DOCX.
5. Copie o DOCX para a pasta da O.S. em `E:\ORDENS DE SERVIÇO CPJ` como `Relatorio de Investigacao - OS <nº>-<AAAA>.docx` e rode `fila-os.py concluir <nº> --agente <nome> --docx "<caminho>"` (se parar antes, `liberar ... --motivo`).
6. Lembre: após revisar no Word e entregar, `/entregar <ID>` e `/calibrar <ID>`.

> **Esteira Completa 1-Clique (Central CPJ):** Na ficha do caso na Central, o botão **⚡ Esteira Completa 1-Clique** (ou endpoint `/api/casos/<id>/esteira`) dispara automaticamente as etapas 2 a 5 sequenciadas em background (OCR $\rightarrow$ RAG $\rightarrow$ Analista Documental $\rightarrow$ Analista Financeiro $\rightarrow$ Redação DOCX $\rightarrow$ Revisor Gauntlet) com checkpoints de retomada e barra de progresso.

Um lembrete por conversa: conferir se o uso desta conta é compatível com o sigilo do procedimento (art. 20 do CPP) e com as normas internas.

## Fonte: `plugin/investigacao-cpj/commands/processar-ip.md`

> Processa os arquivos do caso (PDF → diagnóstico, OCR, Markdown por página, CSV, entidades e JSON; ou MD/CSV prontos) e completa a transcrição visual das páginas pendentes

Processe o material do caso: [ARGUMENTOS: informe o ID do caso (ex.: OS-123-2026) e observações]

Use a skill `pdf-autos-policiais`. Caminhos: `$S = "plugin\investigacao-cpj\skills\pdf-autos-policiais\scripts"`, `$B = "plugin\investigacao-cpj\skills\base-cpj\scripts"`, caso em `casos\<ID>\`.

1. **Verifique `processamento.json`** do caso. Documentos já `concluido` pela Central CPJ **não** devem ser reprocessados. Documentos em `na_fila`/`processando`: aguarde (a Central está trabalhando). Em `erro`: leia `01-extracao\<doc>\processamento.log`, explique e corrija.
2. Para cada arquivo de `00-originais\` ainda sem pasta em `01-extracao\` (quando o usuário não usou a Central), com `$E = "...\01-extracao\<nome do arquivo sem extensão>"`:
   - **PDF:** `$env:PATH += ";C:\Program Files\Tesseract-OCR"`; se existir `ferramentas\tessdata\por.traineddata`, `$env:TESSDATA_PREFIX = "$PWD\ferramentas\tessdata"`. Rode `diagnostico.py` → `extrair.py <pdf> --saida $E --lang por` (use `eng` só se `por` não existir, e avise) → `tabelas.py <pdf> --saida $E` → `tabelas.py $E\transcricao.md --saida $E` → `entidades.py $E\transcricao.md` → `dados_json.py $E` → `caso.py ip <ID> $E\relatorio_extracao.json`.
   - **MD:** copie para `$E\transcricao.md` → `tabelas.py` → `entidades.py` → `dados_json.py $E`. **CSV:** copie para `$E\tabelas\` → `dados_json.py $E`.
3. **Complete o que a máquina não resolve:** para páginas em `pendentes_transcricao_visual` ou `conferir_visualmente` (`relatorio_extracao.json`), leia os PNGs de `$E\paginas_visao\` em lotes de ~20, grave `$E\transcricoes_visuais\pNNNN.md` pelas regras de transcrição da skill (tabelas em Markdown) e rode `extrair.py` de novo + `tabelas.py`/`entidades.py`/`dados_json.py` sobre a transcrição. Se forem muitas páginas, informe o volume antes e pergunte se deve priorizar só as páginas críticas (extratos, comprovantes, qualificações).
4. Atualize `registro-tratamento.md`, rode `python "$B\indexar.py"` e resuma: páginas por método, pendências, tabelas CSV, entidades e JSON consolidado. Próximo passo: `/analisar-ip <ID>`.

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

## Fonte: `plugin/investigacao-cpj/commands/relatorio-ip.md`

> Redige a minuta do Relatório de Investigação no modelo CPJ, revisa contra as fontes e gera o DOCX com timbre e assinatura

Elabore o relatório do caso: [ARGUMENTOS: informe o ID do caso (ex.: OS-123-2026) e observações]

Use a skill `relatorio-ip-fraude`.

1. Leia `calibracao\licoes-aprendidas.md`, `modelos\dados-padrao.json`, a análise do caso (`02-analise\`) e exemplos da mesma modalidade por autor e peso (`rag.py exemplos <modalidade> --autor "<investigador>" -n 3` — FINAL do sistema + referências importadas; só estilo/estrutura, nunca fatos). Fatos: somente os documentos do caso; bases de consulta não são fonte.
2. Se o investigador informou diligências próprias (consultas a sistemas, oitivas, campana), inclua **somente** o que ele informou. Se faltar dado do cabeçalho (O.S., delegado destinatário), use `{...}` e liste. No cabeçalho (campo `referencia` / dados do procedimento), siga a **determinação do Delegado (30/09/2026)**: use **SOMENTE o número do IPe (Inquérito Policial Eletrônico) e do Processo Judicial** (ex.: `IPe nº ... / Processo nº ...`); **NUNCA coloque número de BO nem IP local**. Defina `delegado_genero: M|F` pelos documentos do caso (Dr./Dra., "o/a Delegado/a"); não infira pelo nome; sem base, pergunte. Redija em **texto corrido**, sem tópicos; Resumo dos fatos compacto, com a dinâmica e os valores movimentados (AGENTS.md §1.12-1.13, §1.15).
2b. **A O.S. manda (AGENTS.md regra 17):** antes de redigir, identifique a O.S. vigente (geralmente a última) nos documentos do caso, extraia cada solicitação do Delegado para `02-analise\solicitacoes-os.md` e faça a minuta responder a todas. Sem O.S. localizada: pare e avise o operador em CAIXA ALTA. Cumpra todas as solicitações possíveis, escreva sempre de forma humanizada (texto corrido) e, se faltar CNPJ nos autos, obtenha-o por OSINT de empresa (`osint-empresas.md`) e use-o no contexto adequado.
2a. **Dados faltantes:** se faltar dado muito importante para autoria, materialidade ou circunstâncias, grave `02-analise\dados-faltantes.md` e avise o operador **em CAIXA ALTA** na resposta final (`DADOS FALTANTES — PROVIDENCIAR (OPERADOR)`), conforme `skills\analise-ip-fraude\references\dados-faltantes.md`. Não deduza; no relatório, só ressalva objetiva na Conclusão.
3. Grave `03-relatorios\minuta-vNN.md` e `rastreabilidade-vNN.md`; `caso.py status <ID> minuta`.
4. execute as instruções do agente `revisor-de-relatorio` (seção neste arquivo ou em portatil\) → `revisao-vNN.md`. Corrija erros objetivos na minuta (mesma versão) e liste o que depende de decisão.
5. Gere o DOCX (rascunho): `python "plugin\investigacao-cpj\skills\relatorio-ip-fraude\scripts\gerar_docx.py" "<minuta>" --saida "casos\<ID>\03-relatorios\RELATORIO-<ID>-vNN.docx"`.
6. Apresente: caminho do DOCX, resumo da revisão, campos pendentes, dados críticos não conferidos e, **em CAIXA ALTA, os DADOS FALTANTES para o operador providenciar**. Diga que, após revisar/editar no Word e entregar, basta rodar `/entregar <ID>`.
