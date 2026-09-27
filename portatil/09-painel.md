# Produção e painel

*Arquivo portátil gerado em 2026-09-27 09:53 a partir do plugin `investigacao-cpj`. Autocontido: serve para qualquer agente de IA. Não edite aqui — edite o plugin e rode `ferramentas\exportar-portatil.py`.*

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

Governança completa: `acervo\repo-ia-alandougs\governanca\seguranca-e-dados.md`.

## Como usar fora do Claude Code

- Onde estiver `/comando`, siga o texto daquele comando abaixo. Onde disser "skill X" ou "agente X", as instruções estão neste arquivo ou em `portatil\`.
- Scripts Python ficam em `C:\CPJ - TRABALHO\plugin\investigacao-cpj\skills\<skill>\scripts\` (PowerShell, `python`). Sem execução de comandos, peça ao usuário para rodá-los.
- Sem subagentes: execute as etapas em sequência.

## Fonte: `plugin/investigacao-cpj/commands/painel.md`

> Atualiza a base e abre o painel de produção (dia, mês, ano, metas e indicadores)

Atualize e mostre a produção. [ARGUMENTOS: informe o ID do caso (ex.: OS-123-2026) e observações]

1. `python "C:\CPJ - TRABALHO\plugin\investigacao-cpj\skills\base-cpj\scripts\indexar.py"`
2. `python "C:\CPJ - TRABALHO\plugin\investigacao-cpj\skills\base-cpj\scripts\gerar_painel.py"`
3. `Start-Process "C:\CPJ - TRABALHO\producao\painel.html"` (abre no navegador local; não publicar).
4. Resuma em 4–6 linhas a partir de `producao\base.json`: entregues hoje, no mês (× meta de `producao\config.json`), no ano, prazo mediano, casos em aberto por etapa.

## Fonte: `plugin/investigacao-cpj/skills/base-cpj/SKILL.md`

> Base de dados local do workspace CPJ - registro de casos (caso.json), estatística de produção, índice RAG (busca por trecho com página/fls.), cruzamento de CPF/chave Pix/conta/telefone entre IPs e painel de produção. Use quando o usuário pedir "cria o caso", "atualiza o status", "minha produção", "estatística do mês", "painel", "quantos relatórios", "pesquisa na base", "busca nos IPs", "essa chave Pix aparece em outro caso?", "cruza com outros inquéritos", "exemplos de relatórios anteriores", ou ao fim de cada etapa do pipeline.

## Base CPJ — casos, estatística, RAG e painel

Todo o conteúdo de `C:\CPJ - TRABALHO` é a base de dados. **Fonte da verdade:** `casos\<ID>\caso.json` (um por caso) + os arquivos Markdown/CSV do caso. Tudo o mais é derivado e pode ser regenerado a qualquer momento.

Scripts em `scripts\` (ao lado deste SKILL.md). Em PowerShell: `$B = "C:\CPJ - TRABALHO\plugin\investigacao-cpj\skills\<skill>\scripts"`.

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

A **Central CPJ** (`C:\CPJ - TRABALHO\Central CPJ.bat` → http://127.0.0.1:8765) é a interface única, com login e perfis (admin, delegado, investigador, escrivão): Início (pendências e prazos), Nova O.S. (upload e processamento automático), Casos (ficha, botões de IA atendidos pelos agentes de plantão, editor, DOCX/PDF, baixa), Pesquisa (RAG, pesquisa relacional e vínculos), Estatísticas (painel e KPIs) e Sistema (exportar/importar, bases de consulta, referências, agentes, usuários). Código em `C:\CPJ - TRABALHO\plugin\investigacao-cpj\app\`. O painel também pode ser gerado avulso:

#### Painel avulso — `gerar_painel.py`

```powershell
python "$B\indexar.py"; python "$B\gerar_painel.py"; Start-Process "C:\CPJ - TRABALHO\producao\painel.html"
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
