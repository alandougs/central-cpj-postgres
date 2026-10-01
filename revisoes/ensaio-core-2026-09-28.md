# Relatório de Ensaio Ponta a Ponta do Core Operacional — 28/09/2026

Ensaio automatizado executado pelo agente `Gemini-1` (Tarefa E03) validando o fluxo completo sem IA externa, com dados 100% fictícios e workspace isolado.

## 1. Escopo e Volume do Teste
- **Documento testado:** PDF fictício de **120 páginas** (`ip_120_paginas.pdf`).
- **Composição das páginas:**
  - 105 páginas textuais (qualificação de partes, despachos, depoimentos e extrato bancário).
  - 15 páginas escaneadas (imagens geradas com texto, processadas pelo OCR Tesseract em português).
- **Extratos e Tabelas:** Extrato bancário de conta corrente com lançamentos Pix positivos e negativos.
- **Ambiente:** Windows, Python 3.12, Flask, Tesseract local em português (`por.traineddata`), python-docx, modo solo ativado.

## 2. Tempos Medidos por Etapa
| Etapa | Operação | Tempo | Resultado |
|---|---|---|---|
| **1. Ingestão / O.S.** | `POST /api/os` com upload do PDF (120 págs.) | 0.11 s | O.S. `RECEBIDO-303a5ab2c36a416058aaf08b` criada em `00-originais` |
| **2. Processamento Core** | Diagnóstico + OCR `por` + Markdown + CSV + Entidades + RAG | 22.16 s | `transcricao.md` (120 págs.), tabelas CSV e `entidades.csv` |
| **3. Minuta** | `POST /api/casos/RECEBIDO-303a5ab2c36a416058aaf08b/minuta` | 0.73 s | `minuta-v01.md` gerada e validada |
| **4. DOCX Oficial** | `POST /api/casos/RECEBIDO-303a5ab2c36a416058aaf08b/docx` no modelo CPJ 2026 | 0.70 s | `RELATORIO-RECEBIDO-303a5ab2c36a416058aaf08b-v01.docx` (3,519,781 bytes) |
| **5. Relatório FINAL & Baixa** | `POST /api/casos/RECEBIDO-303a5ab2c36a416058aaf08b/final` | 0.42 s | `RELATORIO-RECEBIDO-303a5ab2c36a416058aaf08b-FINAL.docx` e status `entregue` |
| **6. Painel & Estatísticas** | Consulta e compilação do `/painel` | 0.00 s | Métricas de produção atualizadas |
| **TOTAL DO FLUXO** | Do PDF bruto ao relatório oficial entregue | **24.12 s** | **Fluxo 100% aprovado sem erros** |

- **Taxa média de processamento:** 5.4 páginas/segundo (para PDF misto com 15 páginas em OCR puro).

## 3. Evidências dos Artefatos Gerados
- `00-originais/ip_120_paginas.pdf`: original intacto com hash SHA-256 verificado.
- `01-extracao/.../transcricao.md`: 120 seções com marcação `## Página N`.
- `01-extracao/.../tabelas/`: extração de tabelas financeiras em formato CSV com delimitador `;`.
- `01-extracao/.../entidades.csv`: CPFs, telefones e placas identificados.
- `03-relatorios/RELATORIO-RECEBIDO-303a5ab2c36a416058aaf08b-v01.docx`: DOCX compilado com brasão, cabeçalho e assinatura do Investigador.
- `03-relatorios/RELATORIO-RECEBIDO-303a5ab2c36a416058aaf08b-FINAL.md`: texto integral indexado para busca e calibração.
- `caso.json`: status transicionado de `recebido` -> `extraido` -> `minuta` -> `entregue`.

## 4. Conclusão
O Core Operacional funciona perfeitamente de ponta a ponta no ambiente local (SSD), atendendo integralmente à definição de pronto da tarefa E03 sem bloqueios.
