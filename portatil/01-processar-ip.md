# Receber e processar o material do IP (PDF → OCR → Markdown por página)

No workspace, comece pela memória central `MEMORIA.md` e pelas fontes vivas ali indicadas; este portátil é um instantâneo para uso fora dele.

*Arquivo portátil gerado em 2026-10-27 16:08 a partir do plugin `investigacao-cpj`. Autocontido: serve para qualquer agente de IA. Não edite aqui — edite o plugin e rode `ferramentas\exportar-portatil.py`.*

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

17. **A Ordem de Serviço manda no relatório (determinação do usuário, 05/10/2026):** o relatório de investigação deve atender **principalmente** às solicitações da O.S. — geralmente a **última** O.S. do procedimento. O sistema/agente deve (a) identificar a O.S. vigente nos documentos do caso, (b) extrair cada solicitação/determinação do Delegado de Polícia, (c) registrá-las em `02-analise\solicitacoes-os.md` (item, trecho com pág./fls., onde o relatório responde), (d) responder a cada item no relatório, e (e) tratar item não atendido como ressalva objetiva na Conclusão + aviso em CAIXA ALTA (`DADOS FALTANTES — PROVIDENCIAR (OPERADOR)`). Sem a O.S. localizada, parar e avisar o operador antes de redigir. A revisão reprova minuta que não responda a item da O.S. (f) **Cumprir todas as solicitações que for possível** com os documentos do caso e, no mais, fazer as análises de fraude/estelionato pelas regras de sempre (caminho do dinheiro, art. 171, lacunas). (g) **Escrita sempre humanizada** (texto corrido, natural, como o investigador escreveria; sem tom robótico ou de lista). (h) **CNPJ necessário e ausente dos autos:** pesquisar por OSINT de empresa (skill `osint-policial`; `plugin\investigacao-cpj\skills\analise-ip-fraude\references\osint-empresas.md`; só CNPJ/razão social/cidade, duas fontes, citando a fonte) e inserir o dado no relatório no contexto adequado; não achando, `[PESQUISAR: CNPJ]` + aviso em CAIXA ALTA. Detalhe: `plugin\investigacao-cpj\skills\relatorio-ip-fraude\SKILL.md` (item 10) e `skills\analise-ip-fraude\SKILL.md` (passo 0).

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

## Fonte: `plugin/investigacao-cpj/commands/novo-caso.md`

> Cria o caso pela Ordem de Serviço (pasta casos\OS-...), opcionalmente copiando o PDF/MD para 00-originais

> **Antes de executar:** leia `MEMORIA.md` na raiz do workspace — entrada comum de todos os agentes — e as fontes vivas ali indicadas, em especial `AGENTS.md` (regras obrigatórias e sigilo) e `calibracao/licoes-aprendidas.md`. As regras vigentes prevalecem sobre este procedimento.

Crie o caso: [ARGUMENTOS: informe o ID do caso (ex.: OS-123-2026) e observações]

Forma preferida: a **Central CPJ** (`Central CPJ.bat` → aba Entrada) cria o caso e já processa os arquivos. Use este comando quando o usuário pedir pelo Claude.

1. Sem nº de O.S., pergunte. O ID da pasta é gerado a partir dela (`123/2026` → `OS-123-2026`).
2. `python "plugin\investigacao-cpj\skills\base-cpj\scripts\caso.py" novo --os "<O.S.>" [--bo ...] [--ip ...] [--processo ...] [--natureza ...]`
3. Se foi informado arquivo, **copie** (nunca mova) para `casos\<ID>\00-originais\` e siga com `/processar-ip <ID>`.
4. Responda em até 4 linhas: pasta do caso e próximo passo.

## Fonte: `plugin/investigacao-cpj/commands/processar-ip.md`

> Processa novos PDFs em Markdown por página, com O.S. em Markdown e checkpoint essencial único; sem derivados CSV/JSON

> **Antes de executar:** leia `MEMORIA.md` na raiz do workspace — entrada comum de todos os agentes — e as fontes vivas ali indicadas, em especial `AGENTS.md` (regras obrigatórias e sigilo) e `calibracao/licoes-aprendidas.md`. As regras vigentes prevalecem sobre este procedimento.

Processe o material do caso: [ARGUMENTOS: informe o ID do caso (ex.: OS-123-2026) e observações]

Leia primeiro a skill `pdf-autos-policiais`. Use os scripts originais em `plugin/investigacao-cpj/skills/pdf-autos-policiais/scripts`; caso em `casos/<ID>/`.

1. Confira `processamento.json`: não reprocessar documento concluído nem concorrer com extração na fila/em andamento. Em erro, leia o log daquele documento e preserve checkpoints e originais.
2. Para novo PDF ainda não processado, rode `extrair.py <pdf> --saida <pasta-da-extracao> --lang por`. Use OCR local disponível; ausência/ilegibilidade é pendência, nunca sucesso presumido. A extração gera `transcricao.md` com páginas, O.S. em Markdown e um checkpoint essencial consolidado. **Não executar tabelas.py, entidades.py nem dados_json.py no fluxo dos novos PDFs.** Não criar arquivo por página apenas para indexar no RAG. Para registrar metadados no caso, use `caso.py ip <ID> <pasta-da-extracao>` (leitor do estado consolidado).
3. Para transcrição visual pendente, consulte o estado pelo leitor `estado_extracao.ler(pasta, 'relatorio_extracao.json')`; preserve a distinção entre transcrição confirmada e dado duvidoso. Observe consentimentos antes de qualquer provedor externo. Complete a transcrição conforme a skill e reprocesse apenas o necessário, sem gerar derivados CSV/JSON.
4. Material MD/CSV fornecido pelo operador continua sendo original e não deve ser descartado; sua importação legada não autoriza recriar CSV/JSON para os novos PDFs.
5. Atualize registro de tratamento e estado do caso, preservando SHA-256 do original; indexe pelos scripts existentes quando a etapa exigir. Resuma páginas/método, pendências e localização do Markdown. Próximo passo: `/analisar-ip <ID>`.

## Fonte: `plugin/investigacao-cpj/skills/pdf-autos-policiais/SKILL.md`

> Prepara PDFs de inquéritos, processos e procedimentos policiais para análise por IA com segurança e rastreabilidade. Diagnostica o arquivo (páginas, camada de texto, hash), extrai transcrição Markdown página a página (texto nativo, OCR Tesseract em português ou transcrição visual), tabelas em Markdown e dados críticos conferíveis; ou divide em partes de até 100 páginas. Use sempre que o usuário enviar ou mencionar PDF de IP, autos, processo, BO, RDO, TCO, laudo, extrato ou peça digitalizada, ou disser "processa esse IP", "faz OCR", "extrai o texto", "extrai as tabelas", "transforma em markdown", "divide o PDF", "PDF muito grande", "o Claude não leu o PDF inteiro".

## PDF de Autos Policiais: diagnóstico, extração estruturada ou divisão

> **Antes de executar:** leia `MEMORIA.md` na raiz do workspace — entrada comum de todos os agentes — e as fontes vivas ali indicadas, em especial `AGENTS.md` (regras obrigatórias e sigilo) e `calibracao/licoes-aprendidas.md`. As regras vigentes prevalecem sobre este procedimento.

> Origem: `repo-ia-alandougs/skills/pdf-autos-policiais` (estado: rascunho). Adaptada para Claude Code no Windows (PowerShell, `python`), com extração somente em Markdown e integração ao workspace CPJ.

Prepara PDFs volumosos de inquéritos, processos e procedimentos para que a análise por IA seja completa, auditável e citável por página. Quando o modelo lê e interpreta ao mesmo tempo, um erro de leitura (um dígito de CPF, conta ou valor) entra na conclusão sem deixar registro conferível. Por isso, aqui a regra é: **primeiro transcrever com método registrado, depois analisar sobre a transcrição**.

Dois caminhos:

- **B — Extração estruturada (padrão neste ambiente):** transcrição página a página com método registrado, tabelas em Markdown, dados críticos candidatos e índice de peças em Markdown.
- **A — Dividir** em partes de até 100 páginas, preservando a leitura visual (útil para envio ao Claude.ai/Projetos ou para peças predominantemente visuais).

---

### Quando usar

- O usuário coloca/menciona PDF de IP, processo, procedimento, BO/RDO, TCO, laudo, extrato bancário, relatório de quebra, peça digitalizada.
- O usuário pede para analisar, resumir, montar cronologia, extrair qualificação, cruzar dados ou redigir relatório com base em autos em PDF.
- O usuário diz: "faz OCR", "extrai o texto", "extrai as tabelas", "transforma em markdown", "divide o PDF".

**Não use** quando o usuário já entregar a transcrição em Markdown (e/ou CSV): nesse caso, pule direto para a skill `analise-ip-fraude` — preserve tabelas no próprio Markdown, sem criar derivados CSV/JSON.

---

### Onde ficam as coisas

- **Scripts:** `$S = "plugin\investigacao-cpj\skills\pdf-autos-policiais\scripts"`.
- **Caso:** `casos\<ID>\`, onde `<ID>` deriva da **Ordem de Serviço** (O.S. `123/2026` → `OS-123-2026`).
  - `00-originais\` — arquivos originais (somente leitura), **nunca modificados**.
  - `01-extracao\<documento>\` — uma pasta por arquivo original (nome do arquivo sem extensão): `transcricao.md`, `ordens-de-servico\*.md` e um único `.checkpoint\estado.json` essencial à retomada/OCR/qualidade; o log operacional permanece quando gerado pela Central.
  - `ordens-de-servico\`, dentro da pasta de extração de cada documento — transcrições Markdown das O.S. localizadas e `indice.md` com páginas, fonte e SHA-256. `extrair.py` gera/atualiza esses arquivos Markdown. A busca começa pelas páginas finais; a posição não determina vigência. Confira integralidade, continuações e datas no PDF antes de escolher a ordem principal.
  - `02-analise\`, `03-relatorios\` — etapas seguintes.
  - `caso.json`, `processamento.json`, `registro-tratamento.md`.
- **Central CPJ** (`http://127.0.0.1:8765`, atalho `Central CPJ.bat`): o usuário normalmente envia os PDFs por ela, e ela já executa diagnóstico, extração/OCR em Markdown e indexação. **Antes de processar, verifique `processamento.json`**: se o documento já está `concluido`, não refaça — vá direto à transcrição visual das páginas pendentes/⚠ (se houver) e à análise.

---

### Processo

#### Etapa 0 — Preparar o ambiente

```powershell
python -c "import pypdf, pypdfium2, pdfplumber, PIL; print('ok')"
## se faltar:
python -m pip install pypdf pypdfium2 pdfplumber pytesseract pillow
```

OCR em português exige o **Tesseract** instalado no Windows com o idioma `por`:

```powershell
python -c "import pytesseract; print(pytesseract.get_languages(config=''))"
```

Se der erro de executável não encontrado, verifique `C:\Program Files\Tesseract-OCR\tesseract.exe` e, se existir, defina antes de rodar: `$env:PATH += ";C:\Program Files\Tesseract-OCR"`. Se o idioma `por` não aparecer, baixe `por.traineddata` (tessdata_fast, ~2 MB — confira o tamanho; poucos bytes = mensagem de erro) para uma pasta `tessdata` e aponte `$env:TESSDATA_PREFIX` para ela. **Pergunte ao usuário antes de instalar ou baixar qualquer coisa.** Sem Tesseract, o script cai para transcrição visual (PNG → leitura pelo Claude).

Trabalhe **sempre sobre cópia**. Nunca modifique o arquivo em `00-originais`.

#### Etapa 1 — Preservar e diagnosticar

```powershell
python "$S\diagnostico.py" "casos\<ID>\00-originais\arquivo.pdf"
```

Apresente ao usuário um quadro curto e registre em `registro-tratamento.md`:

| Item | Resultado |
|---|---|
| Páginas | N |
| Tamanho | X MB |
| Tipo | digital / escaneado / misto (faixas sem texto) |
| SHA-256 do original | hash |

O hash registra a integridade do original e permite comprovar depois que a análise partiu daquele arquivo.

#### Etapa 2 — Decidir o caminho

**Neste ambiente (Claude Code local), o padrão é B**, porque a leitura direta de PDF pelo Claude é limitada a lotes pequenos de páginas por chamada e não deixa registro intermediário conferível. Só pergunte se houver motivo para A:

| | **A — Dividir em partes de até 100 páginas** | **B — Extração estruturada** |
|---|---|---|
| Como funciona | O PDF é fatiado; cada parte é lida com texto + imagem de cada página (ex.: Claude.ai) | Cada página vira texto (camada nativa, OCR ou transcrição visual do Claude), com página e método registrados; tabelas permanecem em Markdown, com índice de peças e dados críticos |
| Vantagens | Mantém leitura de manuscritos, carimbos, assinaturas, fotos, croquis e tabelas tortas; rápido; não altera o conteúdo | Texto conferível e pesquisável; cita página em cada afirmação; ocupa muito menos contexto, então o IP inteiro pode ser cruzado de uma vez; busca exata de CPF, placa, telefone, conta, Pix; tabelas de extratos em Markdown; material reaproveitável em relatório e na base RAG |
| Desvantagens | Partes se somam no contexto e detalhes se perdem; cruzar informação entre partes exige consolidação; erro de leitura não deixa registro | Mais demorado em PDF escaneado; OCR erra manuscrito e carimbo e pode "corrigir" palavras; tabelas escaneadas precisam de transcrição visual; exige conferência dos dados críticos |
| Indicado para | Peças com muito manuscrito, fotos ou croquis; consulta pontual | Relatório de investigação, análise de fraude/estelionato, cronologia de transferências, cruzamento de vínculos, qualquer produto que vá aos autos |

Muitos casos pedem **B com conferência visual** das páginas críticas (extratos, comprovantes Pix, qualificações): ofereça como variante de B.

#### Etapa 3A — Dividir

```powershell
python "$S\dividir.py" "arquivo.pdf" --saida "casos\<ID>\01-extracao\partes"
python "$S\dividir.py" "arquivo.pdf" --cortes "1-92,93-180,181-260" --saida "casos\<ID>\01-extracao\partes"
```

Entregue as partes e o `MANIFESTO.json`. Oriente: uma parte por conversa, ao final gerar **Ficha da Parte** e fazer a análise final a partir das fichas. Página da parte é relativa: some o início da faixa (parte 02, faixa 101-200 → pág. 5 da parte = pág. 105 do original).

**Ficha da Parte (modelo):**

```markdown
## Ficha — Parte 02 de 03 (págs. 101–200 do original)
### Peças contidas
| Peça | Data | Págs. (original) | fls. | Síntese objetiva |
### Pessoas citadas
| Nome | Qualificação como consta | Condição no procedimento | Págs. |
### Dados críticos
| Tipo | Valor como consta | Pág. | Legibilidade (legível/duvidoso) |
### Fatos relevantes (com página)
### Lacunas e pontos a conferir
```

#### Etapa 3B — Extração estruturada

Seja `$E = "casos\<ID>\01-extracao\<documento>"` (uma pasta por arquivo original).

1. **Extrair texto página a página:**

```powershell
python "$S\extrair.py" "casos\<ID>\00-originais\arquivo.pdf" --saida $E              # auto: texto nativo > Tesseract > visual
python "$S\extrair.py" "casos\<ID>\00-originais\arquivo.pdf" --saida $E --ocr visao  # força transcrição visual pelo Claude
```

Gera `$E\transcricao.md` (seção `## Página N` por página, método em comentário) e um único `$E\.checkpoint\estado.json` para retomada e controle de qualidade, sem relatório JSON separado. Páginas sem texto e sem OCR, ou com OCR de confiança < 75%, são renderizadas em `$E\paginas_visao\pNNNN.png`.

2. **Transcrição visual das páginas pendentes ou a conferir:** leia os PNGs em lotes (até ~20 por rodada) e grave cada transcrição em `$E\transcricoes_visuais\pNNNN.md`, seguindo as **regras de transcrição** abaixo — **tabelas sempre em Markdown** (`| col | col |`), sem conversão em CSV. Depois rode `extrair.py` de novo com os mesmos parâmetros: ele incorpora as transcrições (método `transcricao-visual-llm`). Se houver centenas de páginas pendentes, avise o tempo/consumo antes e sugira instalar o Tesseract.

   **Pela Central CPJ:** na ficha do caso, use **Transcrever páginas a conferir**. O servidor seleciona a união de `pendentes_transcricao_visual`, `conferir_visualmente` e páginas com `precisa_ia` no checkpoint essencial (leitura lógica `qualidade.json` pelo leitor compatível). O aviso lista os destinos possíveis; Aceitar autoriza somente o escopo `transcricao_visual`, e Recusar/Esc não cria pedido. Somente o PNG de cada página selecionada e uma instrução fixa são enviados, pelo roteador com capacidade `vision`; o modelo configurado também deve aceitar imagens. Não são enviados o PDF inteiro, nomes de arquivos nem textos das outras páginas. DeepSeek/Groq sem visão não participam dessa rota.

   `scripts/transcrever_visual.py` grava arquivos novos com origem (provedor/modelo, página, hash do PNG) e aviso **CONFERIR**; nunca sobrescreve transcrição existente, inclusive gravação concorrente. Dígitos duvidosos devem ser `? [dígito incerto]`; a conferência humana continua obrigatória. O pedido compartilha o orçamento entre páginas, retries e fallback. A chamada enviada pode ultrapassar um teto antes da medição; a próxima é bloqueada, sem prometer limite rígido de faturamento.

   A Central valida o hash do original, os checkpoints e a disponibilidade de Tesseract antes do envio. Com os mesmos parâmetros, incorpora as transcrições sem novo OCR e atualiza a transcrição Markdown, o índice das O.S. em Markdown e a qualidade no checkpoint essencial. Se original/checkpoint/ambiente mudou, interrompe com aviso para executar processamento local primeiro. Retomar preserva arquivos já transcritos e incorpora também resultados de um pedido interrompido.

3. **Tabelas e dados críticos:** mantenha as tabelas no próprio Markdown, com página de origem e marcações de legibilidade. Não execute `tabelas.py`, `entidades.py` nem `dados_json.py` no fluxo de novos PDFs. Esses utilitários continuam disponíveis para compatibilidade com trabalho anterior, sem conversão ou exclusão indiscriminada do legado.

4. **Encaminhar a transcrição para análise:** índices, cronologia e dados críticos necessários à análise permanecem em Markdown no caso. Não gere consolidações JSON ou CSV da extração. O checkpoint essencial mantém a assinatura dos parâmetros, o SHA-256, registros por página, pendências OCR/visuais e qualidade em um único arquivo. `estado_extracao.ler()` e `transcrever_visual.ler_json()` leem também os formatos legados; não alteram nem apagam esses arquivos.

#### Regras de transcrição visual

- Transcreva literalmente. Não corrija ortografia, não complete abreviações, não resuma.
- Marque o que não é texto corrido: `[manuscrito: ...]`, `[carimbo: ...]`, `[assinatura ilegível]`, `[rubrica]`, `[foto: descrição objetiva do que se vê]`, `[croqui]`, `[tabela]` seguido da tabela em Markdown.
- Trecho que não dá para ler: `[ilegível]`. Dígito duvidoso: `?` no lugar e `[dígito incerto]` ao lado (ex.: `123.45?.789-00 [dígito incerto]`). **Nunca complete CPF, conta, chave Pix, placa, telefone ou valor por dedução.**
- Registre a numeração de folhas (fls.) quando estiver carimbada ou impressa na página.

#### Etapa 4 — Encaminhar para análise

A análise e o relatório seguem nas skills `analise-ip-fraude` e `relatorio-ip-fraude` (comandos `/analisar-ip` e `/relatorio-ip`). Cite sempre `(pág. 137 do PDF; fls. 142)`; página do PDF e fls. dos autos costumam ser diferentes.

---

### Output

- **B:** `transcricao.md` e `ordens-de-servico\*.md` (incluindo `indice.md`); checkpoint essencial único em `.checkpoint\estado.json`, metadados do caso/processamento e rastreabilidade preservados.
- **A:** partes `NOME_parteXXdeYY_pagsINICIO-FIM.pdf` + `MANIFESTO.json` + modelo de Ficha da Parte.

Atualize `registro-tratamento.md` do caso e feche com o quadro:

| Campo | Conteúdo |
|---|---|
| Original | nome, páginas, SHA-256 |
| Caminho adotado | A ou B (e por quê) |
| Métodos | ex.: 80 págs. texto nativo, 140 OCR, 10 transcrição visual |
| Tabelas | páginas de origem das tabelas no Markdown |
| Pendências | páginas ilegíveis ou com baixa confiança; dados críticos não conferidos |
| Data e ferramentas | data/hora e bibliotecas usadas |

---

### Restrições e cautelas

- **Sigilo:** não envie conteúdo dos autos a serviços externos de OCR ou conversão. Todo o processamento de extração é local. Lembre o usuário, uma vez por conversa, de verificar se a conta usada é compatível com o sigilo do procedimento (art. 20 do CPP) e com as normas internas do órgão; ofereça anonimizar dados de vítimas quando não forem necessários.
- **Integridade:** o original não é alterado. Transcrição, CSVs, partes e fichas são material de apoio analítico e não substituem os autos. Os arts. 158-A a 158-F do CPP tratam da cadeia de custódia de vestígios; a cópia de autos em PDF em regra não é vestígio, mas adote a mesma lógica de rastreabilidade (hash, método, data, responsável).
- **Fidelidade:** não invente conteúdo de página ilegível, não "arrume" dados divergentes, não junte homônimos sem base documental. Divergência é achado a relatar, não erro a corrigir.
- **Limites:** não afirme que leu o PDF inteiro se houver páginas pendentes. Diga quais páginas ficaram de fora.
- Não use esta skill para contornar sigilo, abrir PDF protegido por senha sem autorização do usuário, nem remover assinaturas, carimbos ou marcas de autenticação.

---

### Exemplos

**1.** IP escaneado de 312 páginas; relatório de estelionato com transferências Pix → diagnóstico; B com OCR em português; transcrição visual das páginas de baixa confiança e dos comprovantes; tabelas e dados críticos na transcrição Markdown; segue para `/analisar-ip`.

**2.** Processo de 180 páginas, digital, com laudo com fotos e croqui; usuário quer a dinâmica do local → recomendar A com cortes nas fronteiras das peças.

**3.** Usuário entrega `IP-123.md` já transcrito com tabelas → não usar esta skill; preservar as tabelas no `.md` e seguir para `analise-ip-fraude`.

---

Validação técnica: ver `VALIDACAO.md`. Os scripts estão em `scripts/` (o apêndice com o código-fonte foi removido desta versão por já estarem instalados; o original permanece em `acervo\repo-ia-alandougs`).
