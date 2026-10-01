---
description: Executa o pipeline completo do IP - caso, processamento, análise, relatório e DOCX - com paradas para aprovação
argument-hint: <ID do caso> [caminho do PDF/MD] [observações]
---

Execute o pipeline completo para: $ARGUMENTS

Sequência (pare e peça confirmação nos pontos ⏸):
0. Reserve a O.S.: `python ferramentas\fila-os.py listar` e `python ferramentas\fila-os.py assumir <nº> --agente <nome-da-sessão>`. Se a O.S. estiver `em_andamento` com outro agente ou já tiver relatório (`concluida`/`com_relatorio`), pare e avise; só refaça com pedido expresso (`--forcar`). Em trabalhos longos, `renovar` a cada etapa.
1. `/novo-caso` (se o caso não existir) e cópia do arquivo para `00-originais`.
2. `/processar-ip` → ⏸ mostre o diagnóstico e o custo de transcrição visual, se houver muitas páginas sem OCR.
3. `/analisar-ip` → ⏸ mostre o resumo (modalidade, caminho do dinheiro, lacunas) e pergunte se há diligências próprias (consultas, oitivas) a incluir e os dados do cabeçalho (O.S., delegado).
4. `/relatorio-ip` → entregue a minuta, a revisão e o DOCX.
5. Copie o DOCX para a pasta da O.S. em `E:\ORDENS DE SERVIÇO CPJ` como `Relatorio de Investigacao - OS <nº>-<AAAA>.docx` e rode `fila-os.py concluir <nº> --agente <nome> --docx "<caminho>"` (se parar antes, `liberar ... --motivo`).
6. Lembre: após revisar no Word e entregar, `/entregar <ID>` e `/calibrar <ID>`.

> **Esteira Completa 1-Clique (Central CPJ):** Na ficha do caso na Central, o botão **⚡ Esteira Completa 1-Clique** (ou endpoint `/api/casos/<id>/esteira`) dispara automaticamente as etapas 2 a 5 sequenciadas em background (OCR $\rightarrow$ RAG $\rightarrow$ Analista Documental $\rightarrow$ Analista Financeiro $\rightarrow$ Redação DOCX $\rightarrow$ Revisor Gauntlet) com checkpoints de retomada e barra de progresso.

Um lembrete por conversa: conferir se o uso desta conta é compatível com o sigilo do procedimento (art. 20 do CPP) e com as normas internas.