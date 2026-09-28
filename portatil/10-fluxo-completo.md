# Pipeline completo do IP com pontos de aprovação

*Arquivo portátil gerado em 2026-09-28 02:53 a partir do plugin `investigacao-cpj`. Autocontido: serve para qualquer agente de IA. Não edite aqui — edite o plugin e rode `ferramentas\exportar-portatil.py`.*

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

## Fonte: `plugin/investigacao-cpj/commands/fluxo-ip.md`

> Executa o pipeline completo do IP - caso, processamento, análise, relatório e DOCX - com paradas para aprovação

Execute o pipeline completo para: [ARGUMENTOS: informe o ID do caso (ex.: OS-123-2026) e observações]

Sequência (pare e peça confirmação nos pontos ⏸):
1. `/novo-caso` (se o caso não existir) e cópia do arquivo para `00-originais`.
2. `/processar-ip` → ⏸ mostre o diagnóstico e o custo de transcrição visual, se houver muitas páginas sem OCR.
3. `/analisar-ip` → ⏸ mostre o resumo (modalidade, caminho do dinheiro, lacunas) e pergunte se há diligências próprias (consultas, oitivas) a incluir e os dados do cabeçalho (O.S., delegado).
4. `/relatorio-ip` → entregue a minuta, a revisão e o DOCX.
5. Lembre: após revisar no Word e entregar, `/entregar <ID>` e `/calibrar <ID>`.

Um lembrete por conversa: conferir se o uso desta conta é compatível com o sigilo do procedimento (art. 20 do CPP) e com as normas internas.

## Fonte: `plugin/investigacao-cpj/commands/processar-ip.md`

> Processa os arquivos do caso (PDF → diagnóstico, OCR, Markdown por página, CSV, entidades; ou MD/CSV prontos) e completa a transcrição visual das páginas pendentes

Processe o material do caso: [ARGUMENTOS: informe o ID do caso (ex.: OS-123-2026) e observações]

Use a skill `pdf-autos-policiais`. Caminhos: `$S = "C:\CPJ - TRABALHO\plugin\investigacao-cpj\skills\pdf-autos-policiais\scripts"`, `$B = "C:\CPJ - TRABALHO\plugin\investigacao-cpj\skills\base-cpj\scripts"`, caso em `C:\CPJ - TRABALHO\casos\<ID>\`.

1. **Verifique `processamento.json`** do caso. Documentos já `concluido` pela Central CPJ **não** devem ser reprocessados. Documentos em `na_fila`/`processando`: aguarde (a Central está trabalhando). Em `erro`: leia `01-extracao\<doc>\processamento.log`, explique e corrija.
2. Para cada arquivo de `00-originais\` ainda sem pasta em `01-extracao\` (quando o usuário não usou a Central), com `$E = "...\01-extracao\<nome do arquivo sem extensão>"`:
   - **PDF:** `$env:PATH += ";C:\Program Files\Tesseract-OCR"`; se existir `C:\CPJ - TRABALHO\ferramentas\tessdata\por.traineddata`, `$env:TESSDATA_PREFIX = "C:\CPJ - TRABALHO\ferramentas\tessdata"`. Rode `diagnostico.py` → `extrair.py <pdf> --saida $E --lang por` (use `eng` só se `por` não existir, e avise) → `tabelas.py <pdf> --saida $E` → `tabelas.py $E\transcricao.md --saida $E` → `entidades.py $E\transcricao.md` → `caso.py ip <ID> $E\relatorio_extracao.json`.
   - **MD:** copie para `$E\transcricao.md` → `tabelas.py` → `entidades.py`. **CSV:** copie para `$E\tabelas\`.
3. **Complete o que a máquina não resolve:** para páginas em `pendentes_transcricao_visual` ou `conferir_visualmente` (`relatorio_extracao.json`), leia os PNGs de `$E\paginas_visao\` em lotes de ~20, grave `$E\transcricoes_visuais\pNNNN.md` pelas regras de transcrição da skill (tabelas em Markdown) e rode `extrair.py` de novo + `tabelas.py`/`entidades.py` sobre a transcrição. Se forem muitas páginas, informe o volume antes e pergunte se deve priorizar só as páginas críticas (extratos, comprovantes, qualificações).
4. Atualize `registro-tratamento.md`, rode `python "$B\indexar.py"` e resuma: páginas por método, pendências, tabelas CSV, entidades. Próximo passo: `/analisar-ip <ID>`.

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
- Scripts em `C:\CPJ - TRABALHO\plugin\investigacao-cpj\skills\base-cpj\scripts\`.

Entregue resumo curto: modalidade, cronologia essencial, caminho do dinheiro com totais, conexões com outros casos, lacunas e dados críticos pendentes de conferência. Próximo passo: `/relatorio-ip <ID>`.

## Fonte: `plugin/investigacao-cpj/commands/relatorio-ip.md`

> Redige a minuta do Relatório de Investigação no modelo CPJ, revisa contra as fontes e gera o DOCX com timbre e assinatura

Elabore o relatório do caso: [ARGUMENTOS: informe o ID do caso (ex.: OS-123-2026) e observações]

Use a skill `relatorio-ip-fraude`.

1. Leia `calibracao\licoes-aprendidas.md`, `modelos\dados-padrao.json`, a análise do caso (`02-analise\`) e exemplos da mesma modalidade por autor e peso (`rag.py exemplos <modalidade> --autor "<investigador>" -n 3` — FINAL do sistema + referências importadas; só estilo/estrutura, nunca fatos). Fatos: somente os documentos do caso; bases de consulta não são fonte.
2. Se o investigador informou diligências próprias (consultas a sistemas, oitivas, campana), inclua **somente** o que ele informou. Se faltar dado do cabeçalho (O.S., delegado destinatário), use `{...}` e liste.
3. Grave `03-relatorios\minuta-vNN.md` e `rastreabilidade-vNN.md`; `caso.py status <ID> minuta`.
4. execute as instruções do agente `revisor-de-relatorio` (seção neste arquivo ou em portatil\) → `revisao-vNN.md`. Corrija erros objetivos na minuta (mesma versão) e liste o que depende de decisão.
5. Gere o DOCX (rascunho): `python "C:\CPJ - TRABALHO\plugin\investigacao-cpj\skills\relatorio-ip-fraude\scripts\gerar_docx.py" "<minuta>" --saida "casos\<ID>\03-relatorios\RELATORIO-<ID>-vNN.docx"`.
6. Apresente: caminho do DOCX, resumo da revisão, campos pendentes, dados críticos não conferidos. Diga que, após revisar/editar no Word e entregar, basta rodar `/entregar <ID>`.
