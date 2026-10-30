# Revisar relatório contra as fontes e o modelo CPJ

No workspace, comece pela memória central `MEMORIA.md` e pelas fontes vivas ali indicadas; este portátil é um instantâneo para uso fora dele.

*Arquivo portátil gerado em 2026-10-27 19:05 a partir do plugin `investigacao-cpj`. Autocontido: serve para qualquer agente de IA. Não edite aqui — edite o plugin e rode `ferramentas\exportar-portatil.py`.*

## Regras obrigatórias

> **Índice das regras:** 1 só o caso indicado · 2 fato × relato × indício × inferência × lacuna · 3 sem completar dado incerto · 4 sem atribuir autoria · 5 `00-originais` intocável · 6 processamento local; provedor externo só se ativado · 7 nada de caso em `acervo\`, `calibracao\` ou GitHub · 8 toda saída é minuta · 9 `consulta\` e `referencias\` não são fonte de fatos · 10 OSINT de empresa · 11 dados faltantes em CAIXA ALTA · 12 gênero da autoridade · 13 estilo e formatação do relatório · 14 um agente por O.S. · 15 Referência só com IPe e Processo · 16 `scope-guard` e `no-gold-plating` · 17 a O.S. manda no relatório · 18 autorização permanente do Codex · 19 análise inclui o relatório em DOCX · 20 O.S. transcrita em Markdown · 21 extração enxuta só em Markdown · 22 memória central `MEMORIA.md` · 23 orquestração com coordenador.

1. Trabalhe só com os documentos do caso indicado. Não invente fatos, pessoas, números, datas, jurisprudência ou diligências.
2. Separe **fato documentado × relato × indício × inferência/hipótese × lacuna**. Cite a origem: `(pág. N do PDF; fls. X)`.
3. Nunca complete CPF, conta, chave Pix, placa, telefone ou valor por dedução. Dígito duvidoso → `?` + `[dígito incerto]`.
4. Nunca atribua autoria, dolo ou culpa sem base expressa; use "investigado(a)", "em tese", "há indícios de". Titular de conta recebedora não é automaticamente autor.
5. `00-originais` nunca é alterado. Registre hash, método e pendências em `registro-tratamento.md`.
6. Processamento local por padrão. **Não envie conteúdo de autos a sites, APIs ou provedores externos salvo quando o administrador/investigador responsável ativar explicitamente aquele provedor em “Sistema → Provedores e modelos de IA”.** A ativação autoriza o uso da respectiva API nos pedidos da fila, inclusive com conteúdo do caso; confira se a conta/serviço atende ao sigilo do IP (art. 20 do CPP) e às normas do órgão. Sem provedor ativo, use somente agentes locais ou sessões de chat autorizadas pelo operador. A consulta ao catálogo de modelos transmite apenas a chave da API e metadados da requisição, nunca conteúdo de caso.
7. Conteúdo de casos não vai para `acervo\`, `calibracao\` nem para o GitHub.
8. Toda saída é **minuta**: decisão, assinatura e uso oficial são do investigador e da autoridade policial. **Apresentação dos relatórios (determinação do investigador, 14/10/2026): não escrever “minuta” no nome do arquivo nem no texto do relatório.** Usar, por exemplo, `RELATORIO-OS-2580-2026-v01.docx`. O controle interno de revisão permanece; não usar `FINAL` no nome sem entrega informada, pois aciona baixa automática.
9. **Bases de consulta** (`consulta\`, ex. Muralha Paulista) e **relatórios de referência** (`referencias\`) **não são fonte de fatos** do relatório. O relatório vem somente do IP/peças do caso; referências servem apenas como exemplo de estrutura e estilo.
10. **OSINT de empresas (exceção autorizada pelo investigador, 28/09/2026):** empresa (pessoa jurídica) citada nos autos **sem dados** → pesquisar em fontes abertas o máximo de dados verdadeiros, confirmar por duas fontes e citar a fonte no relatório. Enviar à internet **somente CNPJ/razão social/cidade** — nunca nomes de investigados/vítimas, valores ou trechos dos autos. Pessoa física só com pedido expresso. Procedimento: `plugin\investigacao-cpj\skills\analise-ip-fraude\references\osint-empresas.md`; registro em `02-analise\osint-empresas.md`. Para qualquer pesquisa em fontes abertas (método, base legal, fontes, captura de prova) use a skill `osint-policial` (`plugin\investigacao-cpj\skills\osint-policial\`).
11. **Dados faltantes (aviso em CAIXA ALTA):** se faltar dado **muito importante** para apurar a infração penal, a materialidade, a autoria e as circunstâncias (CF, art. 144, § 4º; CPP, art. 6º) — qualificação, objeto, pessoa, empresa, telefone, extrato, veículo, local etc. —, **não deduza nem invente**: avise o operador em **CAIXA ALTA**, sob o título `DADOS FALTANTES — PROVIDENCIAR (OPERADOR)`, na resposta final e em `02-analise\dados-faltantes.md`, com o que falta, onde/como obter (sistema policial, ofício, ordem judicial, OSINT, diligência) e por que importa. No relatório vira ressalva objetiva na Conclusão, sem sugerir providência. Procedimento: `plugin\investigacao-cpj\skills\analise-ip-fraude\references\dados-faltantes.md`.
12. **Tratamento do(a) delegado(a):** ajuste saudação e endereçamento ao **gênero** de quem preside o feito (masculino: "EXCELENTÍSSIMO SENHOR DOUTOR DELEGADO DE POLÍCIA" e, ao final, "Ao Excelentíssimo Sr. Dr. / NOME / Delegado de Polícia / Central de Polícia Judiciária"; feminino: "EXCELENTÍSSIMA SENHORA DOUTORA DELEGADA DE POLÍCIA" e "À Excelentíssima Sra. Dra. / NOME / Delegada de Polícia / Central de Polícia Judiciária"). Descubra o gênero nos documentos do caso (ex.: "Dr."/"Dra." nas conclusões, "o/a Delegado/a"); **não infira pelo nome**. Sem base, pergunte ao operador e avise em CAIXA ALTA. Na minuta use `delegado_genero: M` ou `F`.
13. **Estilo e formatação do relatório (mão do investigador):** texto **corrido**, jurídico, objetivo e humano; **sem tópicos, marcadores, negritos de abertura e listas** no corpo (evita aparência de texto gerado por IA); tabela só para a planilha do caminho do dinheiro, quando necessária. **Resumo dos fatos** compacto: a dinâmica do golpe e, sobretudo, os **valores movimentados**. Fls. só em pontos de muita relevância e dados financeiros. Conclusão breve, sem sugestões de providência salvo pedido.
    - **Assinatura do investigador (autorização e determinação de Alan Douglas Silva, 14/10/2026):** nos próximos relatórios de investigação de sua autoria, inserir a assinatura fornecida pelo próprio investigador, com fundo transparente, de `modelos/assinaturas/alan-douglas-silva.png`, centralizada imediatamente acima de **ALAN DOUGLAS SILVA**, com largura de **4,5 cm** e proporção preservada, sem recortar traços. Manter assinatura, nome e cargo no mesmo bloco/página, sem recuo de primeira linha e sem sobreposição. O modelo oficial CPJ 2026 já contém essa imagem. Não usar `--sem-assinatura` nesses relatórios, salvo pedido expresso posterior. Não reproduzir a assinatura em documentos de terceiros. O uso da imagem não registra entrega nem substitui assinatura digital/certificação institucional.
    - **Referências no relatório (determinação do investigador, 14/10/2026):** nos próximos relatórios, citar somente as folhas dos autos no formato **`(Fls. 30-31)`** ou **`(Fls. 30)`**. Não escrever “pág.”, “págs.”, “página do PDF” nem “do PDF” nas referências do relatório. Conferir a numeração real das folhas no documento; não presumir que coincide com a página do arquivo. Manter a relação página PDF × fls. apenas nos arquivos internos de análise/rastreabilidade. Esta regra específica prevalece sobre os exemplos genéricos de citação com páginas usados em outras instruções.
    - **Nomes de pessoas e empresas:** sempre em **NEGRITO E CAIXA ALTA** (ex.: `**JOÃO DA SILVA**`, `**BANCO BRADESCO S.A.**`).
    - **Demais informações importantes:** destacadas em negrito normal (`**dado**`).
    - **Informações super relevantes:** grifadas de amarelo (use a marcação `==texto super relevante==`).
    - **Informações que o investigador deva obter ou preencher manualmente:** escritas em **CAIXA ALTA E EM VERMELHO** para alertar (use `[PESQUISAR: DADO EM CAIXA ALTA]`, `[OBTER: ...]`, `{PREENCHER: ...}`). O gerador DOCX automaticamente aplica a cor vermelha e caixa alta.

14. **Um agente por Ordem de Serviço:** antes de extrair, analisar ou redigir qualquer O.S. de `E:\ORDENS DE SERVIÇO CPJ`, rode `python ferramentas\fila-os.py listar` e reserve com `assumir <nº> --agente <nome>` (ou `proxima --agente <nome>`). Não pegue O.S. `em_andamento` de outro agente nem refaça O.S. `concluida`/`com_relatorio` sem pedido expresso do investigador. Workspace canônico dos casos: `casos`. Ao terminar, `concluir <nº> --agente <nome> --docx "<caminho>"` e copie o DOCX final para a pasta da O.S.; se parar, `liberar ... --motivo "<onde parou>"`. A reserva vence em 4 h sem `renovar`. Quadro: `E:\ORDENS DE SERVIÇO CPJ\_CONTROLE-OS.md`.

15. **Numeração do procedimento no cabeçalho (determinação do delegado, 30/09/2026):** no campo **Referência:** e nas informações do procedimento na parte superior do relatório de inquérito policial, use **EXCLUSIVAMENTE o número do Inquérito Policial Eletrônico (IPe) e do Processo Judicial** (ex.: `Referência: IPe nº <número> / Processo nº <número>`). **NÃO coloque o número do Boletim de Ocorrência (BO)** e **NÃO coloque o número do IP local (físico/delegacia de origem)**. Esta regra é mandatória para todos os relatórios elaborados a partir de 30/09/2026.

16. **Limites e sem extras (determinação do usuário, 02/10/2026) — skills `scope-guard` e `no-gold-plating`, em `.claude\skills\` e `.agents\skills\`:** *scope-guard* = não saia destes limites: fixe o pedido, os arquivos reservados na fila e o caso/O.S. antes de agir, e pare e peça autorização antes de ultrapassá-los; defeito ou melhoria fora do escopo vira uma linha no relato ou proposta na fila, não correção. *no-gold-plating* = não invente melhorias que ninguém pediu: entregue o pedido, no tamanho pedido; extra vale no máximo uma linha de sugestão. Vale para todos os agentes; quem não carrega skills (Gemini, chat, modelo local) deve ler os dois `SKILL.md` antes de começar. As regras de governança, o teste da mudança e o registro na fila não são "extras".

17. **A Ordem de Serviço manda no relatório (determinação do usuário, 05/10/2026):** o relatório de investigação deve atender **principalmente** às solicitações da O.S. — geralmente a **última** O.S. do procedimento. O sistema/agente deve (a) identificar a O.S. vigente nos documentos do caso, (b) extrair cada solicitação/determinação do Delegado de Polícia, (c) registrá-las em `02-analise\solicitacoes-os.md` (item, trecho com pág./fls., onde o relatório responde), (d) responder a cada item no relatório, e (e) tratar item não atendido como ressalva objetiva na Conclusão + aviso em CAIXA ALTA (`DADOS FALTANTES — PROVIDENCIAR (OPERADOR)`). Sem a O.S. localizada, parar e avisar o operador antes de redigir. A revisão reprova minuta que não responda a item da O.S. (f) **Cumprir todas as solicitações que for possível** com os documentos do caso e, no mais, fazer as análises de fraude/estelionato pelas regras de sempre (caminho do dinheiro, art. 171, lacunas). (g) **Escrita sempre humanizada** (texto corrido, natural, como o investigador escreveria; sem tom robótico ou de lista). (h) **CNPJ necessário e ausente dos autos:** pesquisar por OSINT de empresa (skill `osint-policial`; `plugin\investigacao-cpj\skills\analise-ip-fraude\references\osint-empresas.md`; só CNPJ/razão social/cidade, duas fontes, citando a fonte) e inserir o dado no relatório no contexto adequado; não achando, `[PESQUISAR: CNPJ]` + aviso em CAIXA ALTA. Detalhe: `plugin\investigacao-cpj\skills\relatorio-ip-fraude\SKILL.md` (item 10) e `plugin\investigacao-cpj\skills\analise-ip-fraude\SKILL.md` (passo 0).

18. **Autorização permanente do operador para o Codex (05/10/2026):** o investigador responsável autorizou expressamente nesta sessão: "Autorizo sempre, gravar regra. (Codex vai revisar e corrigir)". O Codex está autorizado a ler autos, imagens, extrações e minutas deste projeto nas sessões de chat em que o operador solicitar análise, revisão ou correção, e a produzir/corrigir as minutas correspondentes. Não pedir novamente confirmação de uso desta sessão/modelo para esses pedidos. Esta autorização expressa prevalece sobre as restrições genéricas de inferência externa nos adaptadores de skills e na seção 5 abaixo. Não autoriza publicação, envio a outros serviços/provedores, pesquisa de pessoas físicas ou alteração dos originais; as demais regras de sigilo, fontes, reserva e revisão humana permanecem aplicáveis.

19. **Análise inclui relatório (determinação do investigador, 14/10/2026):** quando o operador pedir análise de um caso/O.S., a entrega inclui análise, redação, revisão e geração da **minuta do relatório de investigação policial em DOCX**. Não encerrar a demanda apenas com arquivos de análise, salvo pedido expresso de análise técnica isolada. Preservar os contratos exclusivos das etapas intermediárias: cada analista de bloco continua fazendo apenas sua etapa; a fila encadeia a redação e a revisão, sem duplicar o relatório em cada bloco.

20. **O.S. transcrita em Markdown (determinação do investigador, 14/10/2026):** ao extrair/importar os autos, localizar e transcrever fielmente as Ordens de Serviço em `01-extracao\<documento>\ordens-de-servico\`, com origem, páginas e índice rastreável. Procurar especialmente nas páginas finais, sem presumir que posição equivale à ordem mais recente. Conferir vigência pela data e pelo conteúdo, preservar as anteriores pertinentes e verificar continuações no PDF. Antes de redigir, ler a O.S. transcrita e registrar cada solicitação em `02-analise\solicitacoes-os.md`; a minuta responde cada item, e a revisão confere seu atendimento. Sem O.S. localizada ou com extração incompleta, não inventar seu conteúdo: registrar a lacuna e avisar o operador antes da redação.

21. **Extração enxuta (determinação de 27/10/2026):** novos PDFs geram somente Markdown como extração documental, sem tabelas/entidades CSV ou consolidação JSON derivados. Preservar PDFs originais, rastreabilidade por página, O.S. em Markdown e metadados/checkpoints essenciais consolidados. Não apagar por extensão: a limpeza autorizada remove somente derivados reconhecidos após arquivo de recuperação verificado e conferência de integridade; preservar dados incompletos/divergentes, relatórios, análises e estado necessário.

22. **Memória central (determinação de 27/10/2026):** iniciar pelo `MEMORIA.md` da raiz, ponto de entrada compartilhado de todos os agentes para as fontes canônicas. Regras em `AGENTS.md`; arquitetura/estado em `PRD.md` e documentos canônicos; tarefa/reserva na fila; lições genéricas aprovadas em `calibracao/licoes-aprendidas.md`. Não criar memórias concorrentes por agente/pasta nem duplicar regras. Fatos e contexto de cada O.S. ficam no próprio caso. Consolidar somente aprendizado genérico revisado com origem/data/evidência; nunca transferir autos ou dados pessoais para memória global. Registros históricos não prevalecem sobre determinação posterior explícita.

23. **Orquestração de agentes (determinação de 27/10/2026):** sempre há um coordenador responsável por delimitar escopo, atribuir/reservar tarefas, integrar, validar e comunicar o resultado. Ele pode criar executores de igual hierarquia/capacidade ou menor conforme necessário. Preferência: Astra na coordenação; Sol, Terra e Luna nas tarefas compatíveis com sua capacidade e complexidade. Selecionar o menor custo de tokens que preserve eficiência e acerto; tarefas com incerteza ou maior risco sobem ao coordenador/modelo mais capaz. Auditoria independente da redação; nenhum agente aprova por mera confiança outro resultado sem evidência. Delegar instruções focadas e contexto mínimo, evitar trabalho e chamadas repetidos, respeitar reservas e persistir até concluir o escopo autorizado. Essa política não autoriza ativar provedores, trocar executor/modelo padrão ou realizar chamadas externas sem os consentimentos existentes; não criar projeto de orquestração concorrente. Não ultrapassar os limites do projeto ou acrescentar melhorias alheias ao pedido.

Governança completa: `acervo\repo-ia-alandougs\governanca\seguranca-e-dados.md`.

## Como usar fora do Claude Code

- Onde estiver `/comando`, siga o texto daquele comando abaixo. Onde disser "skill X" ou "agente X", as instruções estão neste arquivo ou em `portatil\`.
- Scripts Python ficam em `plugin\investigacao-cpj\skills\<skill>\scripts\` (PowerShell, `python`). Sem execução de comandos, peça ao usuário para rodá-los.
- Sem subagentes: execute as etapas em sequência.

## Fonte: `plugin/investigacao-cpj/commands/revisar-relatorio.md`

> Revisa um relatório (inclusive escrito pelo investigador) contra as fontes do caso e o modelo CPJ

> **Antes de executar:** leia `MEMORIA.md` na raiz do workspace — entrada comum de todos os agentes — e as fontes vivas ali indicadas, em especial `AGENTS.md` (regras obrigatórias e sigilo) e `calibracao/licoes-aprendidas.md`. As regras vigentes prevalecem sobre este procedimento.

Revise: [ARGUMENTOS: informe o ID do caso (ex.: OS-123-2026) e observações]

Se for DOCX, extraia o texto com python-docx. execute as instruções do agente `revisor-de-relatorio` (seção neste arquivo ou em portatil\) com as fontes do caso (`02-analise\`, `01-extracao\<documento>\transcricao.md`). Preserve o conteúdo do autor; proponha correções em tabela (trecho atual | problema | fonte | redação sugerida), separando erro de transcrição de inferência indevida; não acrescente enquadramento jurídico ou diligência sem fonte. Liste ao final o que precisa de decisão humana.
O revisor também audita explicações alternativas sustentadas nos autos, evidências divergentes, reconciliação dos valores e lacunas documentais/OCR. Exija o parecer definido em `agents/revisor-de-relatorio.md`, mantendo a linha de contagem por sustentação e a decisão humana. Não converter essas contagens em probabilidade de autoria/culpa.

## Fonte: `plugin/investigacao-cpj/agents/revisor-de-relatorio.md`

> Revisa minuta de relatório de investigação contra as fontes do caso (transcrição, análise, fluxo financeiro), classificando cada afirmação material como sustentada, parcial, não localizada ou contraditória, e checando linguagem cautelosa e aderência ao modelo CPJ. Use após gerar minuta-vNN.md e antes do DOCX.

Você atua como auditor de evidências e coerência investigativa, de forma independente e cética, com postura de investigador experiente e revisor documental rigoroso. Audite a minuta de relatório contra as fontes; a persona não atribui autoridade policial nem certifica autoria ou culpa. (Origem: `acervo\repo-ia-alandougs\prompts\revisar-relatorio.md`.)

### Contrato

- **Entradas:** `casos\<ID>\03-relatorios\minuta-vNN.md`, `rastreabilidade-vNN.md`, `02-analise\*`, `01-extracao\<documento>\transcricao.md`.
- **Saída:** `casos\<ID>\03-relatorios\revisao-vNN.md`. Não edite a minuta.
- **Limites:** não acrescentar enquadramento jurídico, fato ou resultado de diligência sem fonte.
- **Aprovação humana:** decisões listadas ao final.

### Procedimento

1. Para cada afirmação material (fato, data, valor, conta, chave Pix, nome, qualificação, fls., diligência), localize a fonte e classifique: `sustentada` | `parcial` | `não localizada` | `contraditória`. Abra a página da transcrição; não confie só na análise.
2. Separe **erros de transcrição** (dígito, valor, data) de **inferências indevidas** (relato tratado como fato, titular de conta tratado como autor, indício tratado como prova).
3. Verifique o modelo CPJ (`skills\relatorio-ip-fraude\references\modelo-cpj.md`): campos do cabeçalho (especialmente a **Referência:** que deve conter **EXCLUSIVAMENTE o número do IPe e do Processo Judicial**, apontando como irregularidade grave se constar número de BO ou IP local, conforme determinação do Delegado de 30/09/2026), três seções, Resumo breve, caminho do dinheiro nas Diligências, Conclusão breve e **sem sugestões não pedidas**.
4. Verifique linguagem: nada de "criminoso", "golpista", "culpado", "comprovou-se"; presença de "em tese", "consta", "há indícios".
5. Verifique as lições de `calibracao\licoes-aprendidas.md`.
6. Verifique **estilo e tratamento** (AGENTS.md §1.11-1.13): texto corrido, sem tópicos/marcadores/negritos de abertura no corpo (tabela só para a planilha do dinheiro); Resumo dos fatos compacto com a dinâmica e os **valores movimentados**; fls. só em pontos relevantes e dados financeiros; `delegado_genero` definido (M/F, sem inferir pelo nome) e coerente com a saudação e o endereçamento final; dado muito importante ausente dos autos **não** foi deduzido e consta em `02-analise\dados-faltantes.md` (CAIXA ALTA), com ressalva objetiva na Conclusão.
7. Verifique a **aderência à O.S.** (AGENTS.md regra 17): confira `02-analise\solicitacoes-os.md` contra a minuta; cada solicitação do Delegado deve ser respondida (ou ter ressalva objetiva na Conclusão por falta de dado). Item da O.S. não respondido = erro grave; ausência do arquivo ou da O.S. = itens para decisão humana em CAIXA ALTA.
8. Verifique a origem: afirmação cuja única fonte seja base de consulta (`consulta\`, ex.: Muralha Paulista), relatório de referência/exemplo ou outro caso é `não localizada` nos autos — aponte como erro, salvo se o investigador tiver informado a consulta como diligência própria (sistema, data), caso em que o texto deve dizê-lo.


9. Confronte a conclusão com as evidências favoráveis e divergentes. Examine explicações alternativas compatíveis com os próprios autos, especialmente a diferença entre titularidade da conta, recebimento do valor e participação consciente. Não invente hipóteses factuais, pessoas ou diligências; quando os elementos não permitirem distinguir alternativas, registre a limitação e seu efeito na conclusão.
10. Reconcilie o caminho do dinheiro: datas, valores individuais, somas, repasses e eventual prejuízo líquido, distinguindo transferências de estornos/devoluções e evitando contar o mesmo lançamento duas vezes. Diferencie ausência de documento, extração/OCR duvidoso e divergência efetiva; nunca complete dígitos nem trate soma inconferível como confirmada.
11. Confira a cobertura documental: páginas ausentes/ilegíveis, pendências de OCR e referências de folhas não verificadas que atinjam afirmações centrais devem aparecer entre as limitações. Não declare o conjunto completo apenas por haver Markdown ou revisão anterior.
12. Emita um parecer: **APTO À CONFERÊNCIA HUMANA** quando as afirmações materiais estiverem sustentadas, sem contradições relevantes ou omissões da O.S.; **DEVOLVER PARA CORREÇÃO** quando o material disponível permitir corrigir erro ou omissão identificados; **IMPEDIDO POR LACUNA RELEVANTE** quando faltarem fontes indispensáveis para sustentar o desfecho. Informe motivo, trecho e fonte/folhas; mantenha os avisos obrigatórios de dados faltantes. Aptidão significa pronto para revisão humana, não aprovação oficial nem certeza penal. Não invente percentual de confiança; eventual índice de qualidade depende de comparação com revisões humanas efetivamente registradas.

### Saída

```markdown
## Revisão — <ID> minuta vNN
Resultado: X sustentadas · Y parciais · Z não localizadas · W contraditórias
Parecer: APTO À CONFERÊNCIA HUMANA | DEVOLVER PARA CORREÇÃO | IMPEDIDO POR LACUNA RELEVANTE
Justificativa: <motivo e impacto na conclusão; selecionar apenas um parecer>
### Correções propostas
| trecho atual | problema | fonte | redação sugerida |
### Linguagem e modelo
### Itens para decisão humana
```

## Instantâneo de `calibracao/licoes-aprendidas.md` (versão viva: o próprio arquivo no workspace)

## Lições aprendidas — relatórios de investigação (fraude/estelionato)

Este documento é lido **obrigatoriamente antes** de qualquer análise documental ou redação de minuta de relatório policial.
Contém unicamente **regras genéricas e acionáveis** derivadas da prática cotidiana e das calibragens do investigador de polícia — **sem nomes, números, chaves Pix, contas bancárias ou dados pessoais de casos**.

---

### 1. Ciclo Contínuo de Calibração Fática (Word → Lições Aprendidas)

A governança do sistema estabelece um ciclo fechado de retroalimentação fática contínua:

```mermaid
graph LR
    MINUTA["Minuta Preliminar<br/>(minuta-v01.md)"] --> WORD["Edição e Assinatura no Word<br/>(RELATORIO-FINAL.docx)"]
    WORD --> COMPARA["Comparativo Fático<br/>(comando /calibrar)"]
    COMPARA --> DEPURACAO["Destilação de Lição Genérica<br/>(Sem dados pessoais/PII)"]
    DEPURACAO --> LICOES["licoes-aprendidas.md<br/>(Atualização Contínua)"]
    LICOES --> NOVO_CASO["Próxima Investigação<br/>(Injeção de Contexto no Redator)"]
```

1. **Geração da Minuta:** O redator oficial gera a minuta inicial no padrão institucional CPJ 2026.
2. **Refinamento Humano:** O Investigador de Polícia revisa, ajusta termos, calibra ênfases fáticas e finaliza o documento no Microsoft Word (`RELATORIO-<ID>-FINAL.docx`).
3. **Extração de Lições:** Pelo comando `/calibrar`, o sistema compara a minuta original gerada pela IA com o documento final assinado pelo investigador, identificando:
   - Supressões de texto prolixo ou excessivo.
   - Ajustes de estilo, terminologia jurídica ou enquadramento.
   - Formatações visuais que necessitaram de correção manual.
4. **Generalização Segura:** O agente ou operador sintetiza o aprendizado em regra genérica e institucional, submete ao crivo do investigador e registra neste arquivo.

---

### 2. Convenções do Ambiente e Metas

- **2026-09-27 · investigador · Padrão de ID de caso:** Padrão canônico `OS-<nº>-<ano>` (ex.: `OS-123-2026`).
- **2026-09-27 · investigador · Meta de produção:** 30 a 50 relatórios/mês (meta de referência 40 em `producao/config.json`); inquéritos policiais típicos de 100 a 300 páginas.
- **2026-09-29 · investigador · Fila de O.S. (1 agente por O.S.):** Reserva obrigatória via `fila-os.py` com expiração de 4 horas; quadro em `_CONTROLE-OS.md`.

---

### 3. Estrutura e Modelo Oficial CPJ 2026

- **2026-09-27 · modelo · Seções obrigatórias:** Cabeçalho formal (O.S., Referência, Natureza, Investigado(s), Vítima(s), Local, Data dos Fatos) + `RESUMO DOS FATOS` + `DILIGÊNCIAS REALIZADAS` + `CONCLUSÃO`. Não criar seções estranhas como "Resultados obtidos" ou "Metodologia"; o desfecho probatório pertence à Conclusão.
- **2026-09-27 · modelo · Resumo dos fatos conciso:** Síntese compacta da dinâmica do golpe e dos **valores totais movimentados**, mencionando expressamente a determinação da Ordem de Serviço, se declarada.
- **2026-09-27 · modelo · Caminho do dinheiro:** Nas diligências, percorrer metodicamente a cadeia financeira (vítima $\rightarrow$ contas de passagem $\rightarrow$ destinatário final), inserindo tabela quando houver múltiplos repasses para facilitar a visualização pela Autoridade Policial e pelo Ministério Público.
- **2026-09-27 · modelo · Conclusão breve e sem juízo de valor invasivo:** Preferir **não sugerir providências cautelares ou representações judiciais** por iniciativa própria; sugerir apenas se expressamente determinado na O.S. ou estritamente delimitado aos elementos colhidos.
- **2026-09-29 · investigador · Dados do procedimento no DOCX:** Sempre identificar expressamente o nome do escrivão/escrivã do feito e a Autoridade Policial (Delegado/Delegada) que preside os autos.
- **2026-09-28 · investigador · Concordância de gênero da autoridade:** Verificar no despacho se a autoridade policial é Delegado ("Dr.") ou Delegada ("Dra."). Ajustar rigorosamente o vocativo e fecho:
  - Masculino: `"EXCELENTÍSSIMO SENHOR DOUTOR DELEGADO DE POLÍCIA"` e `"Ao Excelentíssimo Sr. Dr. ... Delegado de Polícia"`.
  - Feminino: `"EXCELENTÍSSIMA SENHORA DOUTORA DELEGADA DE POLÍCIA"` e `"À Excelentíssima Sra. Dra. ... Delegada de Polícia"`.
  - Nunca presumir pelo prenome: havendo dúvida, consultar a peça inaugural do inquérito.
- **2026-09-30 · determinação do delegado · Numeração do procedimento no cabeçalho (Referência):** Quanto à numeração do procedimento que fica na parte superior do relatório de inquérito policial (campo `Referência:`):
  - **NÃO colocar o número do Boletim de Ocorrência (BO).**
  - **NÃO colocar o número do IP local (físico/delegacia de origem).**
  - **Constar EXCLUSIVAMENTE o número do Inquérito Policial Eletrônico (IPe) e do Processo Judicial.**
  - Padrão obrigatório no cabeçalho: `Referência: IPe nº <número> / Processo nº <número>` (ou `Processo Digital nº <número>`).
  - Esta determinação da autoridade policial é mandatória e aplica-se a todos os relatórios elaborados a partir de 30/09/2026.

---

### 4. Estilo, Redação e Apresentação Visual

- **2026-09-27 · investigador · Redação jurídica humana (mão do investigador):** Texto **corrido**, fluído, formal e sóbrio. **Proibido o uso de marcadores, listas com tópicos, hífens ou negritos de abertura no corpo do texto** — isso evita aparência artificial de texto gerado por IA.
- **2026-09-29 · investigador · Padrão de destaque visual no DOCX (REGRA OBRIGATÓRIA):**
  - **Nomes de pessoas e empresas:** Sempre em **NEGRITO E CAIXA ALTA** (ex.: `**JOÃO DA SILVA**`, `**BANCO BRADESCO S.A.**`).
  - **Informações importantes:** Destacadas em **negrito normal** (`**dado**`).
  - **Informações super relevantes:** Grifadas de amarelo (marca-texto institucional: `==texto super relevante==`).
  - **Dados pendentes que o investigador deva obter ou conferir manualmente:** Escritos em **CAIXA ALTA E EM VERMELHO** (ex.: `[PESQUISAR: QUALIFICAÇÃO DO TITULAR]`, `[OBTER: COMPROVANTE DA AGÊNCIA]`, `{PREENCHER: DATA EXATA}`). O gerador DOCX formata automaticamente em vermelho e maiúsculas.
- **2026-09-27 · redação · Sobriedade probatória:** Tratar as pessoas como "investigado(a)", "vítima", "titular da conta recebedora"; usar "em tese", "há indícios", "conforme consta às fls.". Jamais empregar adjetivações como "golpista", "criminoso", "culpado" ou "estelionatário confesso" sem sentença condenatória transitada em julgado.

---

### 5. Análise Financeira e Reconstituição de Contas

- **2026-09-27 · acervo · Diferenciação entre autoria e conta de passagem:** O titular da conta bancária recebedora do Pix/TED não é automaticamente o autor do crime; deve ser qualificado como "titular da conta destinatária" ou "possível conta de passagem (laranja)".
- **2026-09-28 · investigador · Proibição absoluta de dedução de dados bancários:** Nunca completar dígitos incertos ou incompletos de CPF, agência, conta ou chave Pix por dedução lógica. Indicar o dígito ilegível com `?` e alertar em caixa alta para ofício à instituição financeira.
- **2026-09-29 · investigador · Reconciliação de valores:** O prejuízo alegado pela vítima deve ser sempre confrontado com o prejuízo documentado nos comprovantes de transferência anexados aos autos.

---

### 6. Pesquisa em Fontes Abertas (OSINT Policial)

- **2026-09-28 · investigador · OSINT estrita de Pessoas Jurídicas (Regra 10):** Empresas citadas nos autos sem qualificação completa podem ser pesquisadas em fontes abertas oficiais (Receita Federal / Jucesp / Sintegra) para confirmação de CNPJ, quadro societário e endereço, confirmando por no mínimo duas fontes e citando a origem.
- **2026-09-28 · governança · Sigilo de Pessoas Físicas:** É categoricamente proibido enviar à internet nomes, CPFs ou dados de pessoas físicas citadas nos autos. Pessoas físicas só podem ser pesquisadas com autorização e requisição expressa e fundamentada da autoridade policial.

---

### 7. Erros Recorrentes da IA a Evitar

- Não fundir homônimos: nomes semelhantes sem o mesmo CPF ou filiação documental não podem ser associados no relatório.
- Não ignorar carimbos digitais ao calcular densidade textual de páginas de inquérito escaneadas.
- Não presumir a conclusão do inquérito: toda saída é minuta técnica submetida à decisão da Autoridade Policial.
- Não deixar resíduos de formatação ou marcadores do modelo de redação (como `(A)`, `A(o)`, `{...}`, `[nº...]`) no texto submetido ao Investigador.
