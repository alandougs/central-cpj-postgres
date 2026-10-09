---
name: no-gold-plating
description: Não invente melhorias que ninguém pediu. Use ao escrever ou alterar código, documentos, relatórios e análises do projeto CPJ, e sempre que sentir vontade de acrescentar recurso, opção, refatoração, seção, tabela, sugestão ou providência extra além do pedido. Entregue exatamente o pedido, no tamanho pedido.
---

# no-gold-plating — não invente melhorias que ninguém pediu

Entregue o que foi pedido, com qualidade, e pare. Acrescentar o que ninguém pediu aumenta o que o usuário tem de ler, revisar, testar e manter, e cada extra é uma chance de erro.

## O teste

Para cada coisa que você está prestes a acrescentar, pergunte: **alguém pediu isto, ou o pedido não funciona sem isto?** Se não, não faça. Se vale a pena, diga em **uma linha** no fim ("sugestão, não feita: …") e deixe o usuário decidir.

## O que conta como extra

- **Código:** recurso novo, parâmetro, flag, configuração, camada de abstração, generalização "para o futuro", tratamento de caso impossível, refatoração ou renomeação do que está ao redor, reformatação de linhas que você não precisou mudar, comentários e documentação que ninguém pediu.
- **Correção de defeito:** corrija a causa do defeito indicado, na menor mudança que o resolve, com teste que o reproduza. Não reescreva a vizinhança.
- **Tarefas e telas:** botão, aba, relatório, painel ou modo que não está no pedido.
- **Relatório e análise de caso (`AGENTS.md`, regra 13):** texto corrido, objetivo, sem tópicos nem seções acrescentadas. Nada de diligência, providência ou sugestão que o investigador não pediu; a Conclusão é breve. Não amplie a análise além do que os autos documentam e do que foi solicitado.
- **Resposta ao usuário:** sem resumo do que ele já sabe, sem lista de opções que você não vai seguir, sem recomendações em cascata. Dê a resposta e, se necessário, uma recomendação.

## O que NÃO é gold plating

Estas coisas fazem parte do pedido, mesmo sem estarem escritas nele:

- as regras do projeto: governança, sigilo, rastreabilidade por página, separação entre fato e inferência, aviso de dados faltantes (`AGENTS.md`);
- teste da mudança que você fez, com dados fictícios, e a conferência de que nada quebrou;
- registro na fila (`fila-tarefas.py`) e no PRD quando o projeto o exige;
- tratamento de erro e validação nas fronteiras onde o dado vem de fora.

## Em caso de dúvida

Escolha a opção mais simples que atenda ao pedido. Se houver mais de uma leitura razoável do pedido, pergunte; não entregue as duas.
