---
description: Executa o pipeline completo do IP - caso, processamento, análise, relatório e DOCX - com paradas para aprovação
argument-hint: <ID do caso> [caminho do PDF/MD] [observações]
---

Execute o pipeline completo para: $ARGUMENTS

Sequência (pare e peça confirmação nos pontos ⏸):
1. `/novo-caso` (se o caso não existir) e cópia do arquivo para `00-originais`.
2. `/processar-ip` → ⏸ mostre o diagnóstico e o custo de transcrição visual, se houver muitas páginas sem OCR.
3. `/analisar-ip` → ⏸ mostre o resumo (modalidade, caminho do dinheiro, lacunas) e pergunte se há diligências próprias (consultas, oitivas) a incluir e os dados do cabeçalho (O.S., delegado).
4. `/relatorio-ip` → entregue a minuta, a revisão e o DOCX.
5. Lembre: após revisar no Word e entregar, `/entregar <ID>` e `/calibrar <ID>`.

Um lembrete por conversa: conferir se o uso desta conta é compatível com o sigilo do procedimento (art. 20 do CPP) e com as normas internas.