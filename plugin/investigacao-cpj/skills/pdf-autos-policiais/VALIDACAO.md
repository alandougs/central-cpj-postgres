---
id: skill-pdf-autos-policiais
tipo: skill
estado: rascunho
revisao: 2026-09-25
tags: [pdf, ocr, extracao, rastreabilidade, inquerito]
---

# Histórico de validação — pdf-autos-policiais

## 2026-09-25 — teste técnico com PDF fictício

**Cenário:** PDF gerado por `teste/gerar_pdf_ficticio.py`, com 230 páginas: 1–80 com camada de texto (simulando peça digital) e 81–230 apenas imagem (simulando digitalização). Todo o conteúdo é fictício.

**Ambiente:** Linux, Python 3.11, pypdf, pypdfium2, pytesseract + Tesseract 5 com `por.traineddata` (tessdata_fast).

| Script | Resultado |
|---|---|
| `diagnostico.py` | Identificou 230 págs., 80 com texto, 150 sem texto (faixa 81-230), tipo "misto", 3 partes necessárias |
| `dividir.py` | Gerou 3 partes (1-100, 101-200, 201-230) e `MANIFESTO.json` com SHA-256; cortes personalizados funcionaram; cortes com lacuna foram recusados |
| `extrair.py` (auto) | 80 págs. texto nativo + 150 OCR Tesseract, confiança média ~92%; ~1 s/página no OCR |
| `extrair.py` (sem idioma `por`) | Páginas sem texto renderizadas em PNG e marcadas como pendentes; transcrição visual gravada em `transcricoes_visuais/` foi incorporada na segunda execução |
| `entidades.py` | 850 candidatos (fls., CPF, placa, telefone, data, valor) com página de origem |

**Observação relevante:** o OCR "corrigiu" `FICTICIO` para `FICTÍCIO`, o que ilustra por que dados críticos devem ser conferidos contra a imagem da página.

**Pendente para `testado`:** aplicação em PDF real de procedimento, em ambiente autorizado, com conferência humana de amostra das páginas e dos dados críticos.
