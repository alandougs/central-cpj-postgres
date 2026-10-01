# F02 — desempenho do OCR e da extração

## Corpus e linha de base

- Corpus fictício gerado pelo helper da E03: 120 páginas, sendo 105 com camada de texto e 15 escaneadas.
- SHA-256 do PDF usado na comparação: `ed101367c00b77759543988eec61c4c1e16d0e9aa96e70cc06a3ac4cd67a7a90`.
- OCR local: Tesseract do PDF24, idioma `por`, `TESSDATA_PREFIX` apontado para `ferramentas/tessdata`.
- O perfil foi feito com `cProfile` em extração isolada, saída nova e checkpoint vazio, antes e depois da alteração.

| Medição | Antes | Depois | Variação |
|---|---:|---:|---:|
| Extração completa (120 páginas) | 149,734 s | 65,637 s | −56,2% |
| Chamadas OCR Tesseract (15 páginas) | 130,023 s acumulados | 51,578 s acumulados | −60,3% |
| Ritmo total observado | 0,80 pág./s | 1,83 pág./s | 2,28× |

Antes, cada uma das 15 chamadas `image_to_data` aguardava o subprocesso Tesseract em série (8,67 s por chamada, em média). O perfil também mostra `communicate`/`run_tesseract` e esperas de thread dentro dessa mesma cadeia; esses tempos se sobrepõem e não devem ser somados como gargalos independentes. O custo dominante identificado foi a espera serial dos OCRs.

As duas otimizações candidatas restantes já são feitas pelo código atual: as 105 páginas com pelo menos 50 caracteres usam texto nativo e não passam por OCR; cada página escaneada é rasterizada uma vez e a mesma imagem alimenta o OCR e, se necessário, a imagem de conferência. Não as alterei para evitar mudar os critérios de qualidade ou duplicar trabalho.

## Alteração

`extrair.py` aceita `--workers 1|2` (padrão: até 2, limitado ao número de processadores reportado pelo Python). As imagens são renderizadas pela thread principal; somente os subprocessos Tesseract rodam em paralelo. `OMP_THREAD_LIMIT=1` limita cada Tesseract a uma thread. Checkpoints continuam atômicos e são gravados quando cada página termina; as páginas são recompostas na ordem original antes de escrever `transcricao.md`. O relatório de extração registra quantos workers foram usados.

## Verificação

- Teste diferencial F02: `--workers 1` e `--workers 2` geram o mesmo texto por página, confiança OCR e contagem de métodos em quatro páginas fictícias escaneadas; passa. O CLI limita a concorrência a no máximo dois workers.
- Ensaio E03: OCR e extração das 120 páginas concluídos; o teste parou na etapa DOCX com HTTP 400 porque o modelo não foi localizado no workspace temporário (`modelos/MODELO RELATORIO DE INVESTIGACAO - CPJ 2026.docx`). A cópia do modelo e a rota DOCX estão fora dos arquivos F02; não foram alteradas.
- `teste_desempenho_codex.py`: 7 testes OK.
- `teste_extracao_codex.py`: 1 teste OK.
- Regressão mínima: `teste_solo_claude.py` (7), `teste_seguranca_codex.py` (11), `teste_modularizacao_gemini.py` (6) e `teste_dados_os_codex.py` (18) OK. O teste de dados da O.S. incluiu OCR real.

O ensaio anterior da E03 registrou 30,34 s para a etapa completa; as medições deste relatório usam `cProfile`, extração isolada e o mesmo PDF/hash antes e depois, portanto a comparação de 149,734 s para 65,637 s é a medida controlada desta mudança. O tempo do ensaio anterior não é diretamente comparável a esse perfil.
