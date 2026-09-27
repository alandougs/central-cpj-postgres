# Guia: consulta do acervo por LLM

## Seleção

Use `catalogo.json` para localizar ID, tema, estado e caminho. Carregue primeiro os arquivos diretamente relacionados à pergunta, inclusive a política de dados. Não entregue o repositório inteiro ao contexto por padrão.

## Resposta verificável

Peça ao agente: `Responda com base apenas nos arquivos lidos. Para cada orientação específica, cite caminho, seção e commit ou data de revisão. Indique o que é inferência e o que precisa de confirmação atual.`

## Busca semântica opcional

Um índice local pode dividir Markdown por títulos, guardar `path`, `heading`, `id`, `estado`, `revisao` e hash/commit e recuperar trechos. Sempre releia o arquivo fonte antes de aplicar uma instrução; trate o índice como mecanismo de busca, não como autoridade. Exclua arquivos locais de casos, segredos e dados pessoais do processo de indexação.
