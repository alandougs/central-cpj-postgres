# Pesquisar na base RAG e cruzar identificadores entre casos

*Arquivo portátil gerado em 2026-10-01 10:50 a partir do plugin `investigacao-cpj`. Autocontido: serve para qualquer agente de IA. Não edite aqui — edite o plugin e rode `ferramentas\exportar-portatil.py`.*

## Regras obrigatórias

1. Trabalhe só com os documentos do caso indicado. Não invente fatos, pessoas, números, datas, jurisprudência ou diligências.
2. Separe **fato documentado × relato × indício × inferência/hipótese × lacuna**. Cite a origem: `(pág. N do PDF; fls. X)`.
3. Nunca complete CPF, conta, chave Pix, placa, telefone ou valor por dedução. Dígito duvidoso → `?` + `[dígito incerto]`.
4. Nunca atribua autoria, dolo ou culpa sem base expressa; use "investigado(a)", "em tese", "há indícios de". Titular de conta recebedora não é automaticamente autor.
5. `00-originais` nunca é alterado. Registre hash, método e pendências em `registro-tratamento.md`.
6. Processamento local. **Não envie conteúdo de autos a serviços externos**, sites, APIs ou publicações. Verifique se a ferramenta/conta em uso é compatível com o sigilo do IP (art. 20 do CPP) e as normas do órgão.
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

Governança completa: `acervo\repo-ia-alandougs\governanca\seguranca-e-dados.md`.

## Como usar fora do Claude Code

- Onde estiver `/comando`, siga o texto daquele comando abaixo. Onde disser "skill X" ou "agente X", as instruções estão neste arquivo ou em `portatil\`.
- Scripts Python ficam em `plugin\investigacao-cpj\skills\<skill>\scripts\` (PowerShell, `python`). Sem execução de comandos, peça ao usuário para rodá-los.
- Sem subagentes: execute as etapas em sequência.

## Fonte: `plugin/investigacao-cpj/commands/buscar.md`

> Pesquisa na base RAG local (transcrições, análises, relatórios, acervo) ou cruza CPF/chave Pix/conta/telefone entre casos

Pesquise na base: [ARGUMENTOS: informe o ID do caso (ex.: OS-123-2026) e observações]

Scripts: `plugin\investigacao-cpj\skills\base-cpj\scripts\`.
- Se o argumento parecer identificador (CPF, CNPJ, telefone, placa, chave Pix, conta) → `rag.py entidade "<valor>"`.
- Se for um ID de caso precedido de "cruzar" → `rag.py cruzar <ID>`.
- Se for pessoa (nome, mãe, pai, CPF, RG, telefone, CNPJ/empresa, endereço) → `rag.py pessoas --nome "..." [--mae ...] [--cpf ...]` (qualificações de `02-analise\pessoas.csv` dos casos + bases de consulta importadas). Na Central: *Pesquisa* (também BO, processo, placa, mandado e cautelar, e *vínculos*).
- Caso contrário → `rag.py buscar "<texto>" [filtros] -n 10`.

Resultado vindo de **base de consulta** (`consulta\`, ex.: Muralha Paulista) é apoio à pesquisa do investigador: informe a base de origem e a situação como consta (ex.: mandado "confirmado", "histórico", "negado"), mas nunca o use como fonte de relatório. Vínculo por nome é candidato (homônimos possíveis); por CPF/telefone/conta, indício a conferir.

Abra os trechos mais relevantes no arquivo de origem para confirmar antes de responder. Responda citando caso, arquivo e página/fls. Conexões entre casos são indícios a verificar, não conclusões.

## Fonte: `plugin/investigacao-cpj/skills/base-cpj/SKILL.md`

> Base de dados local do workspace CPJ - registro de casos (caso.json), estatística de produção, índice RAG (busca por trecho com página/fls.), cruzamento de CPF/chave Pix/conta/telefone entre IPs e painel de produção. Use quando o usuário pedir "cria o caso", "atualiza o status", "minha produção", "estatística do mês", "painel", "quantos relatórios", "pesquisa na base", "busca nos IPs", "essa chave Pix aparece em outro caso?", "cruza com outros inquéritos", "exemplos de relatórios anteriores", ou ao fim de cada etapa do pipeline.

## Base CPJ — casos, estatística, RAG e painel

Todo o conteúdo do workspace é a base de dados. **Fonte da verdade:** `casos\<ID>\caso.json` (um por caso) + os arquivos Markdown/CSV do caso. Tudo o mais é derivado e pode ser regenerado a qualquer momento.

Scripts em `scripts\` (ao lado deste SKILL.md). Em PowerShell: `$B = "plugin\investigacao-cpj\skills\<skill>\scripts"`.

### 1. Registro de casos — `caso.py`

```powershell
python "$B\caso.py" novo --os "142/2026" --bo "AB1234/2026" --ip "1234/2026" --processo "1500123-45.2026.8.26.0482"   # -> casos\OS-142-2026
python "$B\caso.py" status OS-142-2026 em_analise            # grava a data de hoje na etapa
python "$B\caso.py" ip OS-142-2026 "casos\OS-142-2026\01-extracao\<documento>\relatorio_extracao.json"
python "$B\caso.py" set OS-142-2026 modalidade=falso-parente financeiro.valor_rastreado=15800.50 resultado.autoria=indicios
python "$B\caso.py" relatorio OS-142-2026 --arquivo RELATORIO-OS-142-2026-FINAL.md --versoes 2 --paginas 6
python "$B\caso.py" listar --status minuta
```

- **Baixa na produção** (= status `entregue`, com `caso.json["baixa"]` = data + origem): (1) **automática** quando existir arquivo com `FINAL` no nome em `03-relatorios\` (docx/pdf/md) — aplicada pelo `indexar.py`, com a data do arquivo; (2) **Central CPJ** → botão "Dar baixa"; (3) **agente** → `/entregar` (`--origem agente`). Desfazer a baixa volta o caso para `minuta` e ignora aquele arquivo FINAL até surgir outro.
- **Status (nessa ordem):** `recebido → extraido → em_analise → analisado → minuta → entregue` (+ `devolvido`, `arquivado`). Cada troca grava a data — é o que mede prazo e produção diária.
- **ID do caso = Ordem de Serviço** (`142/2026` → `OS-142-2026`). BO, IP e processo ficam em campos próprios e são pesquisáveis (Central CPJ → Casos).
- `modalidade`: códigos de `analise-ip-fraude\references\tipologia-golpes.md`.
- `resultado.autoria`: `identificada` | `indicios` | `nao_identificada`.
- `vitimas`/`investigados`: nomes como constam (listas separadas por vírgula no `set`). Não aparecem no painel.
- `horas_trabalho`: opcional, se o usuário quiser medir esforço.

### 2. Indexar — `indexar.py` (base + RAG)

```powershell
python "$B\indexar.py"          # incremental; --tudo para reconstruir
```

Gera `producao\base.json`/`base.csv` (uma linha por caso, abre no Excel) e atualiza `rag\cpj.sqlite` (trechos com caso, tipo, página, fls., modalidade; entidades para cruzamento). Rode após cada etapa concluída.

### 3. Buscar (RAG) — `rag.py`

```powershell
python "$B\rag.py" buscar "falsa central transferência" --tipo relatorio -n 5
python "$B\rag.py" buscar "chave aleatória" --caso OS-142-2026
python "$B\rag.py" entidade "123.456.789-00"
python "$B\rag.py" cruzar OS-142-2026          # conexões com outros IPs
python "$B\rag.py" exemplos falso-parente --autor "Alan Douglas Silva" -n 3   # FINAL + referências, por modalidade/autor/peso
python "$B\rag.py" pessoas --nome "maria souza" --mae "ana"   # pesquisa relacional (pessoas.csv dos casos + bases de consulta)
```

#### Pessoas, bases de consulta e referências

- **Pessoas dos autos:** `casos\<ID>\02-analise\pessoas.csv` (gerado pela análise; formato fixo na skill `analise-ip-fraude`) → tabela `pessoas` e grafo de vínculos no `indexar.py`.
- **Bases de consulta** (Muralha Paulista, fichas de sistemas — Excel, CSV, Word, PDF, TXT ou texto colado): `consulta.py importar <arquivo> --nome "<base>"`, `consulta.py listar`, `consulta.py remover <id>` (ou Central → Sistema). Antecedentes ficam com a situação classificada (`confirmado`, `indeterminado`, `historico`, `negado`) e o trecho original. **Somente pesquisa** — nunca fonte de análise ou relatório.
- **Relatórios de referência** (anteriores, do investigador ou de colegas): `referencias.py importar <arquivo> --autor "<Nome>" --modalidade <código> --peso 1-5`, `listar [--autor]`, `atualizar <REF_ID> --peso N`, `remover <REF_ID>`. Entram em `rag.py exemplos` e na calibração como **estilo/estrutura**, nunca como fatos.

#### Progresso de tarefas de IA

`python "$B\progresso.py" <ID> <0-100> "<etapa>"` grava `casos\<ID>\ia-progresso.json` (barra de progresso do executor automático). Agentes de plantão em chat usam `ferramentas\agente-plantao.py progresso <PEDIDO> ...` (ver `PROMPT-AGENTE-PLANTAO.md`).

Regras de uso do RAG:
- Resultado de busca é **ponteiro**, não fonte: abra o arquivo/página indicado e confira antes de afirmar qualquer coisa.
- Conexão entre casos (mesma chave Pix, conta, CPF, telefone) é **indício de vinculação a verificar**, nunca conclusão; cite os dois casos e páginas.
- Relatórios de outros casos servem de exemplo de **estilo/estrutura**; nunca transporte fatos de um caso para outro.
- Busca semântica (embeddings) está prevista na coluna `trechos.embedding`; ativar depois com modelo local (ex.: Ollama), sem mudar o resto.

### 4. Central CPJ e painel

A **Central CPJ** (`Central CPJ.bat` → http://127.0.0.1:8765) é a interface única, com login e perfis (admin, delegado, investigador, escrivão): Início (pendências e prazos), Nova O.S. (upload e processamento automático), Casos (ficha, botões de IA atendidos pelos agentes de plantão, editor, DOCX/PDF, baixa), Pesquisa (RAG, pesquisa relacional e vínculos), Estatísticas (painel e KPIs) e Sistema (exportar/importar, bases de consulta, referências, agentes, usuários). Código em `plugin\investigacao-cpj\app\`. O painel também pode ser gerado avulso:

#### Painel avulso — `gerar_painel.py`

```powershell
python "$B\indexar.py"; python "$B\gerar_painel.py"; Start-Process "producao\painel.html"
```

Painel local (HTML único, sem internet): entregues no mês × meta (`producao\config.json`, padrão 40), entregues no ano, páginas analisadas, prazo mediano, casos em aberto por etapa, modalidades, % de autoria indicada, valor rastreado, entregas por dia e por mês, últimas entregas. **Não publicar** (deriva de dados de casos); é para abrir no navegador local.

### Indicadores — definições

| Indicador | Cálculo |
|---|---|
| Entregues (dia/mês/ano) | casos com `datas.entregue` no período |
| Prazo | dias entre `datas.recebido` e `datas.entregue` (mediana) |
| Páginas analisadas | soma de `ip.paginas` dos entregues |
| Em aberto | status ≠ entregue/arquivado, por etapa |
| Autoria indicada | `resultado.autoria` ∈ {identificada, indicios} ÷ entregues |
| Retrabalho | `versoes` do relatório final (média) |

#### Qualidade do fluxo — `metricas.py` (seção própria no painel; sem nomes de pessoas)

| Indicador | Cálculo |
|---|---|
| Versões até o FINAL | `versoes` registradas no `caso.json` ou, na falta, nº de `minuta-vNN.md` (mediana; % com 1 versão e com 3+) |
| Achados da 1ª revisão | linha `Resultado:` da primeira `revisao-vNN.md` legível de cada caso: sustentadas, parciais, não localizadas, contraditórias |
| Tempo por etapa | dias entre as datas de status do `caso.json` (etapa pulada mede desde a anterior registrada); mediana |
| Tarefas de IA | `config\plantao.sqlite`: espera na fila e execução (min), concluídas × erros, por ação |

`python "$B\metricas.py"` grava `producao\metricas.json` e mostra o resumo; o `gerar_painel.py` calcula as mesmas métricas ao gerar o painel.
