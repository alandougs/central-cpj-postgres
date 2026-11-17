# Open Notebook: o que aproveitar para digerir documentos (RP36)

Data: 22/10/2026. Pedido do operador: avaliar o que o projeto [Open Notebook](https://github.com/lfnovo/open-notebook) (licença MIT) tem de útil para a Central CPJ, no sentido de digerir os documentos do caso, e deixar registrado no backlog.

Fontes lidas: o README do repositório e as páginas da documentação sobre Transformations, Sources/Insights/Notes, AI Context & RAG e Content Processing Engines. Os parâmetros citados abaixo vêm dessa leitura e devem ser conferidos de novo na fonte antes de qualquer implementação.

Base de comparação na Central: OCR local, índice FTS5 em `rag/cpj.sqlite`, extração de entidades e cruzamento entre casos. Hoje a indexação corta páginas longas em janelas de 2.500 caracteres com sobreposição de 250 (`plugin/investigacao-cpj/skills/base-cpj/scripts/indexar.py`, `JANELA, SOBREPOE`). A coluna `trechos.embedding` já existe e a busca híbrida está prevista como próxima fase em `rag/README.md`.

## Ideias aproveitáveis

1. **Transformações por documento.** É a peça mais útil. São prompts salvos que rodam sozinhos depois da extração, e cada um gera uma nota presa ao documento (no Open Notebook, "insight"). Para nós: resumo da dinâmica e dos valores, linha do tempo, contas/Pix/titulares, pessoas e papéis, e o que a O.S. pede. A saída iria para `01-extracao/<doc>/` em Markdown, com `(pág. N; fls. X)` e separando fato, relato e indício. Vale a orientação deles de usar um prompt por tarefa, em vez de um prompt que pede tudo.
2. **Playground de prompts.** Tela para testar uma transformação sobre texto colado, sem salvar nada. Casa com a regra de testar só com dados fictícios.
3. **Níveis de contexto por documento.** Cada documento fica "fora", "só resumos" ou "texto integral" no que vai para o modelo, com estimativa de tokens na tela. Em IP com mais de 100 páginas isso reduz custo e reduz o que é exposto ao modelo.
4. **Busca híbrida (FTS5 + embeddings locais).** Já prevista no `rag/README.md`. Do Open Notebook aproveitam-se os parâmetros: trechos de cerca de 400 tokens com 15% de sobreposição, e resumos indexados à parte do texto bruto. Modelo de embeddings local, via Ollama.
5. **Pergunta em três estágios ("Ask").** O modelo planeja até cinco buscas, responde cada uma em separado e junta tudo numa resposta com citações. Aqui a citação apontaria para página e fls., não para o documento inteiro. Seria uma evolução do `/buscar`.
6. **Docling como extrator opcional** para layout e tabelas, sobretudo extratos bancários. Se falhar, a Central volta para pypdf/Tesseract em vez de parar. Roda localmente, mas é pesado (de centenas de MB a alguns GB) e a instalação precisa de internet ou de pacote baixado antes.
7. **Salvar resposta como nota com a origem marcada** ("Humano" ou "Gerado por IA") em `02-analise`. Reforça a regra de que toda saída é minuta.
8. **Aviso de truncamento.** Quando o documento passa do limite de contexto, o modelo é avisado de que o texto foi cortado. Aqui o aviso também deveria chegar ao operador, na linha da correção OCR01 (nada de falha silenciosa).

## O que não aproveitar

- Os extratores de URL (Firecrawl e Jina enviam conteúdo para fora) e a escolha livre de provedores na nuvem: esbarram na regra 6 do `CLAUDE.md`.
- O podcast, a pilha SurrealDB/Next.js e a instalação do sistema inteiro. Por padrão a interface e a API dele ficam abertas em todas as interfaces de rede e sem senha.
- O que se aproveita são ideias, prompts e parâmetros. Pela licença MIT, trechos podem ser copiados com citação da fonte.

## Ordem sugerida, se o operador decidir implementar

Primeiro os itens 1 e 3, depois o 4, e o 6 por último. Cada item vira tarefa própria na fila somente sob pedido expresso e delimitação do operador, conforme a nota de 22/10/2026 sobre funcionalidades novas.

## Limites desta entrega

Somente documentação. Nenhum código, dependência, instalação, teste ou envio de autos a serviço externo.
