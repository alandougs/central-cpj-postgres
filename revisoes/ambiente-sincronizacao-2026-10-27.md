# Ambiente local da sincronização — EN01 — 27/10/2026

Escopo: recuperar o ambiente Python transferido e disponibilizar OCR local, sem instalação global, alteração de PATH persistente, registro do Windows, serviços, credenciais ou dados de casos. A descoberta no código foi alterada somente no candidato isolado; o runtime foi recuperado no workspace original conforme autorização do coordenador.

## Python

A reprodução inicial de `.venv/Scripts/python.exe --version` falhou porque `pyvenv.cfg` referenciava o perfil anterior, inexistente neste computador. O interpretador local disponível tem a mesma versão 3.12.14. Antes da correção foram copiados `pyvenv.cfg` e todo o diretório `Scripts` para o backup externo da sincronização, subpasta `ambiente-original`.

Executado `python -m venv --without-pip --upgrade` apontando para a `.venv` existente. Não houve instalação ou atualização de pacotes. As bibliotecas em `Lib/site-packages` foram mantidas. Os onze lançadores de comandos copiados de C:/D: foram corrigidos para a raiz atual F: por substituição da linha shebang, mantendo seu tamanho e o restante dos executáveis. Os scripts de ativação foram regenerados pelo próprio venv.

Verificação direta: Python 3.12.14, prefixo da `.venv` correta, imports Flask, Cheroot, pypdf, QuickJS, Playwright, pypdfium2 e pytesseract aprovados. `pip.exe --version`, `flask.exe --version` e `playwright.exe --version` aprovados; nenhuma shebang remanescente aponta para as raízes antigas.

## OCR portátil

Fonte: [release oficial Tesseract 5.5.3](https://github.com/tesseract-ocr/tesseract/releases/tag/5.5.3). Artefato `tesseract-ocr-w64-setup-5.5.3.20260724.exe`, SHA-256 `bee9e3434bd94fd65387d9be28cd467a41f61b1275383b55b0f59a1331270ae4`, conferido antes da extração. O instalador não foi executado. O [7-Zip oficial 26.05](https://www.7-zip.org/download.html) foi extraído em staging externo e usado apenas como ferramenta portátil.

O runtime em `ferramentas/tesseract/` contém 34 arquivos PE (executável e 33 DLLs) selecionados por fecho recursivo das importações PE, mais `doc/LICENSE`, `doc/AUTHORS` e `doc/README.md`: 48.718.059 bytes. Foram omitidas 22 DLLs sem dependência do comando OCR, utilitários de treinamento, instalador/desinstalador, imagens, JARs e idiomas duplicados. O manifesto de hashes fica no staging externo `ocr-tools/runtime-manifest.json`. Os arquivos já presentes em `ferramentas/tessdata` não foram alterados.

`--version` confirmou `tesseract v5.5.3.20260724`, e `--list-langs` com o tessdata existente listou `eng`, `osd` e `por`, tanto no staging reduzido quanto após a cópia para o projeto. O runtime está excluído do Git pela regra `/ferramentas/tesseract/` no candidato. Os binários permanecem apenas locais.

## Descoberta e evidência

`comum.py` e `extrair.py` preservam a prioridade: `CPJ_TESSERACT` explícito (diretório ou caminho de executável), runtime portátil do workspace ou fonte, instalações existentes e PATH. Uma configuração inexistente permite a procura seguinte. A CLI também encontra o idioma no tessdata local quando não existe `TESSDATA_PREFIX` explícito. Não foram alterados os contratos de extração Markdown/checkpoint da MD01.

TDD: teste novo executado antes da correção mostrou quatro falhas esperadas (runtime local não descoberto, caminho explícito de executável não aceito e CLI sem OCR); o fallback PATH já passava. Após a correção, os cinco testes de `teste_ambiente_en01.py` passaram em 1,920 s, sem skips. A integração usa scan fictício em TEMP, cópia portátil, PATH sem Tesseract e sem prefixo de idioma preparado; conferiu texto extraído e SHA-256 inalterado do PDF.

Uma primeira seleção de regressões invocou um nome de módulo inexistente (`teste_ocr_parcial_ocr01`), gerando erro de seleção; RG27 e desempenho da mesma rodada passaram. A rodada final usa o nome correto `teste_ocr_indisponivel_claude`; os resultados finais são registrados abaixo. O gate completo do candidato é responsabilidade do coordenador.

Verificação final focada: 19/19 unittests aprovados em 5,990 s, sem skips — EN01 5, RG27 3, OCR01 10, desempenho F02 1. L05 executou 22 verificações reais de OCR/checkpoint com resultado `TUDO OK`; por ser script que encerra no import, foi conferido separadamente dos 19 unittests. `git diff --check` dos arquivos alterados passou, e `git check-ignore` confirmou exclusão do executável e da licença do runtime no candidato. O coordenador executa o gate integrado com `CPJ_EN01_ENGINE` apontando ao runtime original para a fixture portátil; isso não cria configuração persistente.

Limites: a recuperação não torna o venv relocável para outra máquina; uma nova transferência requer regenerar lançadores. A instalação operacional do código candidato e o gate geral ficam com o coordenador. Nenhuma API de IA, autos reais, assinatura pessoal, rede operacional, serviço, boot ou reinício foi usado. EN01 congelada após estes resultados.
