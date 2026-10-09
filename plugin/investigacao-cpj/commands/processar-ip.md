---
description: Processa os arquivos do caso (PDF → diagnóstico, OCR, Markdown por página, CSV, entidades e JSON; ou MD/CSV prontos) e completa a transcrição visual das páginas pendentes
argument-hint: <ID do caso (OS-...)> [arquivo específico]
---

Processe o material do caso: $ARGUMENTS

Use a skill `pdf-autos-policiais`. Caminhos: `$S = "plugin\investigacao-cpj\skills\pdf-autos-policiais\scripts"`, `$B = "plugin\investigacao-cpj\skills\base-cpj\scripts"`, caso em `casos\<ID>\`.

1. **Verifique `processamento.json`** do caso. Documentos já `concluido` pela Central CPJ **não** devem ser reprocessados. Documentos em `na_fila`/`processando`: aguarde (a Central está trabalhando). Em `erro`: leia `01-extracao\<doc>\processamento.log`, explique e corrija.
2. Para cada arquivo de `00-originais\` ainda sem pasta em `01-extracao\` (quando o usuário não usou a Central), com `$E = "...\01-extracao\<nome do arquivo sem extensão>"`:
   - **PDF:** `$env:PATH += ";C:\Program Files\Tesseract-OCR"`; se existir `ferramentas\tessdata\por.traineddata`, `$env:TESSDATA_PREFIX = "$PWD\ferramentas\tessdata"`. Rode `diagnostico.py` → `extrair.py <pdf> --saida $E --lang por` (use `eng` só se `por` não existir, e avise) → `tabelas.py <pdf> --saida $E` → `tabelas.py $E\transcricao.md --saida $E` → `entidades.py $E\transcricao.md` → `dados_json.py $E` → `caso.py ip <ID> $E\relatorio_extracao.json`.
   - **MD:** copie para `$E\transcricao.md` → `tabelas.py` → `entidades.py` → `dados_json.py $E`. **CSV:** copie para `$E\tabelas\` → `dados_json.py $E`.
3. **Complete o que a máquina não resolve:** para páginas em `pendentes_transcricao_visual` ou `conferir_visualmente` (`relatorio_extracao.json`), leia os PNGs de `$E\paginas_visao\` em lotes de ~20, grave `$E\transcricoes_visuais\pNNNN.md` pelas regras de transcrição da skill (tabelas em Markdown) e rode `extrair.py` de novo + `tabelas.py`/`entidades.py`/`dados_json.py` sobre a transcrição. Se forem muitas páginas, informe o volume antes e pergunte se deve priorizar só as páginas críticas (extratos, comprovantes, qualificações).
4. Atualize `registro-tratamento.md`, rode `python "$B\indexar.py"` e resuma: páginas por método, pendências, tabelas CSV, entidades e JSON consolidado. Próximo passo: `/analisar-ip <ID>`.
