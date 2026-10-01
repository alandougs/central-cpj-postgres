# Plano: navegação, escrivão e calibração de relatórios

Data: 2026-09-30
Solicitante: Alan Douglas Silva

## Estado verificado

- O formulário Nova O.S. já coleta `escrivao`; a API persiste e exibe o campo na ficha do caso.
- H01 agora inclui `escrivao` nos metadados iniciais da minuta e o gera no DOCX, inserindo uma linha após Data dos Fatos sem editar o modelo original.
- O editor visual ainda não inclui `escrivao` na lista de campos `META`; enquanto U01 não for feita, salvar uma minuta pelo editor pode descartar esse metadado.
- A abertura da ficha chama `scrollIntoView`, mas o comportamento pedido precisa ser coberto por teste de interação ao selecionar uma O.S. na aba CASOS.
- Existe ação “calibrar estilo” por relatório e endpoint `/api/casos/<id>/calibrar`. O endpoint atual usa heurísticas sobre um Markdown, pode escolher uma minuta sem FINAL e grava lições globais automaticamente, sem comparação nem aprovação. Deve ser substituído antes de uso operacional.
- Já existe upload de relatórios em **Sistema → Relatórios de referência**, para DOCX/PDF/MD, com autor/peso e uso declarado apenas como estrutura e estilo. Não duplicar esse acervo nem usar fatos das referências em outros casos.

## Sequência compartilhada

### H01 — Escrivão no DOCX

Passar `escrivao` do caso aos metadados da minuta e renderizá-lo no cabeçalho do DOCX oficial, após Data dos Fatos. Se o modelo legado não tiver o parágrafo, inseri-lo preservando o estilo adjacente. Campo ausente permanece pendente; nunca inferir o nome.

Critério: teste fictício confirma propagação caso → minuta → DOCX e compatibilidade quando o valor está ausente.

### K01 — Comparação FINAL/minuta (após EC01)

Comparar somente a minuta identificada do caso com o FINAL explicitamente enviado pelo investigador (PDF, DOCX ou MD), em processamento local. PDF sem camada textual deve usar OCR local disponível ou retornar pendência clara. Produzir proposta de diferenças genéricas, sem promover fatos, nomes, valores, números ou dados pessoais a `calibracao/`.

Exibir a proposta para aprovação humana. Só lições aprovadas podem ser gravadas em `calibracao/licoes-aprendidas.md`, de forma genérica; rejeições e contagens ficam no histórico sem conteúdo identificável. O FINAL enviado permanece na pasta do caso com origem/hash registrados. Não alterar originais nem acervo global.

Critério: fixtures cobrem DOCX/PDF textual/MD, FINAL ausente, extração inválida, aprovação e rejeição; nenhuma gravação global ocorre antes da aprovação.

### U01 — Navegação e ação em CASOS (após K01 e EC01)

Ao selecionar uma linha de O.S. na lista, abrir a ficha correspondente e rolar até ela, com foco visível no painel de Inteligência Artificial, sem depender da posição anterior da página. Incluir `escrivao` nos campos do editor visual da minuta para preservar o dado ao salvar. Na ficha, fornecer seleção explícita do FINAL a comparar, botão de calibração, progresso/resultado e aprovação/rejeição da proposta.

Critério: teste de navegador confirma que clicar numa O.S. seleciona a O.S. certa, rola até a ficha, mostra as ações IA e não inicia processamento sem confirmação do operador.

## Validação já executada

- H01: `teste_cabecalho_escrivao_copilot.py` — 3/3 verificações aprovadas em workspace/DOCX fictícios.
- Regressão `teste_docx_f04.py` — 2/5 passaram; 3 falharam em checagens de quebra de página da assinatura e formatação/alinhamento da tabela. Investigar separadamente antes da integração final; não corrigidas por H01.
- `teste_seguranca_codex.py` não apresentou resumo final nesta sessão; status não confirmado.

## Uso já disponível

Para adicionar relatório finalizado como exemplo de estilo, usar **Sistema → Relatórios de referência**. O cadastro aceita `.docx`, `.pdf` e `.md`, com autor e peso. Isso não substitui a comparação por caso nem autoriza reutilizar fatos da referência em outro inquérito.

## Restrições de segurança

- Todo conteúdo de caso permanece local e dentro da pasta do caso; não enviar autos ou relatórios a serviços externos.
- Não gravar conteúdo de casos em `calibracao/`, `acervo/` ou Git; somente lições genéricas aprovadas.
- Não escolher automaticamente um FINAL ou minuta ambíguos; exigir seleção/associação inequívoca.
- Preservar aprovação humana e registrar hash, origem, método e pendências do FINAL recebido.
