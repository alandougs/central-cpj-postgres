# Fila de processamento: remover, cancelar, reprocessar e OCR alternativo (AZ01, NO01, OC01)

Data: 30/10/2026. Pedido expresso do operador: botão de excluir na fila; opção de forçar outro método de OCR e disponibilizar esse método. AZ01/NO01 transferidas por decisão do operador (Codex-AZ01 → Claude-NO01 → Claude-OC01). Testes somente com dados fictícios em TEMP.

## Entrega

- **Backend (Claude-NO01, preservado):** `POST /api/casos/<id>/processamento/cancelar` (na fila → cancelado; em execução → encerra o processo local, checkpoints preservados) e `/processamento/dispensar` (falha ou cancelamento encerrado sai da fila; registro e arquivos preservados, auditoria antes da gravação, idempotente). `/api/fila` oculta dispensados. Causa legível do erro (`motivo_falha`) e gravação de estado tolerante a bloqueio transitório do Windows.
- **Interface (`fila-progresso.js`, `recebimento.js`):** por item, conforme a situação — "Cancelar processamento" (na fila/em processamento), "Reprocessar" e "Remover da fila" (erro/cancelado); concluídos sem ação. Confirmação antes de cancelar/remover; `aria-label` com o nome do arquivo; botões só para quem tem permissão `trabalho`. Resumo conta cancelados.
- **OCR alternativo:** `extrair.py --ocr rapidocr` usa RapidOCR 3.10 (PaddleOCR em ONNX, reconhecimento latino PP-OCRv5, local). Método `ocr-rapidocr` com confiança média na transcrição; relatório registra o motor. Troca de motor invalida os checkpoints (assinatura já inclui `ocr`); mesmo motor retoma. Sem o pacote: encerra com "RapidOCR indisponível…" sem gravar transcrição. Na fila, PDFs com erro/cancelados têm seletor "OCR padrão (Tesseract)" / "OCR alternativo (RapidOCR)" ao lado de "Reprocessar"; `comum.enfileirar(..., ocr=)` valida e persiste o motor (também na retomada) e `processar` passa `--ocr` ao extrator; a rota de reprocessar aceita `ocr` e recusa motor inválido (400). Pacote instalado na `.venv` e listado em `requirements-opcional.txt`.
- `rodar()` força `PYTHONIOENCODING=utf-8` no filho (mensagem com acento legível).

## Verificação

`.venv\Scripts\python.exe -B -X utf8`: OC01 5/5 (RED antes da implementação no extrator), NO01 11/11, AZ01 5/5, OCR01 10/10 (ajuste do duplo `rodar_falso` à assinatura `chave=`), PX06 10/10, dados_os 18/18, FP01 9/9, UN15 16/16, UN15 UI 7/7, UN17 3/3, UN14 22/22, RG26 1/1, AP39 5/5, AP37 1/1, MV01 1/1, MD01 12/12, PX05 11/11, RG27 3/3, EN01 5/5, extração Codex 1/1, L05 TUDO OK.

## Limites e pendências

- Sem teste de clique em navegador real nos novos botões (contrato verificado por renderização em Node); a Central em execução precisa ser reiniciada para carregar as mudanças.
- `rotas/casos.py` está reservado também por AS50: a alteração de OC01 (3 linhas em `api_reprocessar` e import de `MOTORES_OCR`) foi autorizada pelo operador e deve ser preservada na integração do AS50.
- Leitor de O.S. vigente (NO01) conferido só por leitura e de forma agregada nas transcrições reais: 68 com cabeçalho de O.S., 107 O.S. lidas, 32 vigentes com data e determinação, 30 com prazo, 0 exceções. As 36 sem data merecem conferência (falso positivo de menção ou lacuna do parser).
- PRD não atualizado (reservado por AS50). Revisão independente pendente.
