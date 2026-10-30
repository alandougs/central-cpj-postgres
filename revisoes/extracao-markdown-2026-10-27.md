# Extração somente Markdown — MD01 — 27/10/2026

Implementação no candidato isolado, sem implantação, reinício ou exclusão no workspace operacional. Reserva `Codex-MD01`. Determinação do operador: novos PDFs geram transcrição e Ordens de Serviço em Markdown, sem CSVs nem consolidações JSON analíticas. `caso.json`, `processamento.json`, originais e rastreabilidade permanecem.

## Contrato entregue

`extrair.py` gera `transcricao.md`, transcrições das O.S. e `ordens-de-servico/indice.md`. Um único `.checkpoint/estado.json` contém assinatura/hash/parâmetros, registros de página, metadados, pendências e qualidade necessários à retomada. Não gera `relatorio_extracao.json`, `diagnostico.json`, `qualidade.json`, `dados_extraidos.json`, entidades ou tabelas CSV no novo fluxo PDF. Os PNGs de conferência continuam disponíveis e podem ser regenerados do PDF original, preservando o DPI.

A Central usa esse contrato na extração e no replay visual. Consentimento, orçamento, fallback, limites OCR, bloqueio por alteração do original/checkpoint e cancelamento permanecem. Importações explícitas de MD/CSV e utilitários legados mantêm seu comportamento anterior. Nenhum arquivo legado é apagado por esta alteração.

`estado_extracao.ler(pasta, nome)` e `transcrever_visual.ler_json(pasta, nome)` resolvem os nomes lógicos antigos dentro do checkpoint consolidado e leem o legado quando não existe estado novo. Metadados para o caso são importados em memória: `C.importar_ip(id, relatorio=dict, pasta=documento)`. A assinatura antiga por caminho continua aceita, inclusive para `.checkpoint/estado.json`, permitindo `caso.py ip <ID> <checkpoint>` sem arquivo temporário.

Os consumidores de pendências OCR, proveniência na indexação e conferência do relatório usam o leitor comum. Dados de página continuam em Markdown com método e referência ao PDF; O.S. continua com fonte, hash, páginas e verificação de integralidade/vigência.

Em um PDF de 300 páginas, a extração direta anterior produzia pelo menos 303 arquivos JSON (300 checkpoints, assinatura, relatório e índice das O.S.); o novo formato produz um checkpoint essencial. A contagem exclui Markdown e imagens de conferência.

## Consolidação conservadora do legado

`estado_extracao.compactar_legado(pasta)` não apaga arquivos. Exige metadados versão 2, SHA-256 coerente com o relatório e checkpoints de todas as páginas. Retorna `compactado`, `cobertos` (caminhos relativos com conteúdo JSON semanticamente igual ao estado relido) e, em caso de recusa, `motivo`. Estado consolidado já existente tem precedência; divergências não entram na lista de equivalentes. Checkpoint versão 1 sem hash permanece intocado e não é declarado coberto. A função não autoriza exclusão nem substitui o backup/verificação do limpador SZ02.

Inventário operacional somente leitura: 101 documentos com relatório legado; 85 estruturalmente elegíveis e 16 incompletos/divergentes. Duas cópias privadas temporárias foram consolidadas e tiveram os seis arquivos legados cobertos comparados semanticamente; hashes dos arquivos de origem permaneceram iguais nos dois documentos. As cópias foram descartadas. Nenhum conteúdo identificável foi impresso; nenhum original ou derivado operacional foi escrito ou removido. A consolidação massiva não foi executada por MD01.

## Evidências e limites

TDD observado: o teste real de PDF falhou porque havia relatório JSON; o teste real da Central falhou no contrato antigo; o teste de importação CLI do checkpoint falhou por interpretar o envelope como relatório. Após as mudanças, os quatro testes MD01 passaram, incluindo original intacto, ausência de CSV/JSON analítico, pendência visual, qualidade, retomada e compactação sem alteração do legado.

Runtime utilizado: `C:/Users/Usuario/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`; `PYTHONPATH=F:/CPJ - TRABALHO/.venv/Lib/site-packages` e `PYTHONDONTWRITEBYTECODE=1` somente no ambiente dos comandos. Nenhum pacote instalado ou ambiente ativo alterado. Comando base: `<runtime> -X utf8 -W ignore::ResourceWarning plugin/investigacao-cpj/app/testes/<teste>.py`.

Resultados direcionados: MD01 4 testes; OCR indisponível 10; transcrição visual PX05 9; O.S. Markdown AR01 9; extração Codex 1; qualidade PX03 todas as verificações — aprovados. Fontes RP33: 8 aprovados e 2 skips explícitos por privilégio Windows de symlink de arquivo; junctions reais exercitadas.

Limites do host: Tesseract ausente nos caminhos Tesseract-OCR e PDF24. RG27 teve uma falha explícita por ausência do engine; dados O.S. teve 17/18 aprovados, falhando o teste que exige OCR português real. F02 teve um skip e OCR checkpoint informou que não executou o OCR. Esses resultados não contam como validação positiva do engine. O core E03 alcançou extração de 120 páginas e falhou ao gerar DOCX por ausência do modelo sintético na execução direta; validação completa desse cenário fica no runner com fixture.

A suíte `ferramentas/testar-tudo.py` foi iniciada antes do congelamento e interrompida, a pedido do coordenador, para evitar validar fontes ainda em edição. Foram observadas falhas em `teste_apple_ui_ap39.py` e `teste_astra_ast06_store.py`, sem afirmação de resultado global. O coordenador executará a suíte completa sobre o candidato congelado.

Os testes antigos do contrato de extração foram adaptados para ler/mutar o checkpoint consolidado, preservando asserts de páginas, texto, retomada, original, limites, consentimento e cancelamento. Expectativas de entidades/JSON analítico foram substituídas pela ausência exigida pelo novo requisito.
