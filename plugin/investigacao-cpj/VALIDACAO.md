---
id: plugin-investigacao-cpj
tipo: skill
estado: rascunho
revisao: 2026-09-27
tags: [plugin, claude-code, ocr, relatorio, estelionato, rag, producao]
---

# Histórico de validação — plugin investigacao-cpj

## 2026-09-27 — testes técnicos com dados fictícios (Windows 10, Python 3.12, Tesseract 5.4)

| Componente | Resultado |
|---|---|
| `diagnostico.py` | PDF fictício de 230 págs. (80 digitais + 150 imagem): tipo "misto", faixas sem texto corretas |
| `extrair.py` | 230 págs. em ~133 s (80 texto nativo + 150 OCR); progresso por página emitido para a Central |
| OCR `por` (tessdata_best) × `eng` | Página de teste com acentos, CPF e valores: `por` sem erros; `eng` errou "fls." → "fis." e acentuação |
| `tabelas.py` | Tabela Markdown de transcrição → CSV com coluna `pagina_pdf`; PDF sem tabelas digitais informa corretamente |
| `entidades.py` | 715 candidatos com página de origem |
| `gerar_docx.py` | Minuta fictícia → DOCX no modelo CPJ: timbre, cabeçalho, 3 seções, tabela, assinatura e data do rodapé preservados; campo vazio mantém texto-guia |
| `caso.py` / baixa | Baixa automática por arquivo `*FINAL*` (ignora `~$` do Word), por agente e desfazer sem reaplicação |
| `indexar.py` / `rag.py` | Indexação incremental; busca sem acento; fallback OR; entidade e cruzamento detectaram a mesma chave Pix em 2 casos |
| `gerar_painel.py` | Painel com indicadores e gráficos; claro/escuro |
| Central CPJ (`app/`) | Upload PDF+MD → caso pela O.S. → fila concluída; busca por nome/IP; edição; baixa; produção |
| Manifestos | `claude plugin validate` aprovado; instalado como `investigacao-cpj@cpj-local` |

**Pendente para `testado`:** aplicação em IP real, em ambiente autorizado, com conferência humana de amostra das páginas, dos dados críticos e do relatório final.
