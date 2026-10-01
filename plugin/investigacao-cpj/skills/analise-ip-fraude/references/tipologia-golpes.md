# Tipologia de modalidades (campo `modalidade` do caso.json)

Lista controlada para classificar casos, alimentar a estatística e o RAG. Classifique pelo que **consta nos autos**; se não se encaixar, use `outro` e descreva em `observacoes`. Revise a lista pela calibração.

| Código | Modalidade | Indicadores típicos nos autos |
|---|---|---|
| `falso-parente` | Falso parente / WhatsApp com foto de familiar | Mensagem de número novo alegando troca de celular; pedido de Pix |
| `whatsapp-clonado` | Conta de mensageria clonada/sequestrada | Código de verificação solicitado; contatos da vítima abordados |
| `falsa-central` | Falsa central / falso funcionário de banco | Ligação alegando compra suspeita; orientação para transferir/instalar app |
| `boleto-falso` | Boleto adulterado ou falso | Código de barras/beneficiário divergente |
| `falso-vendedor` | Venda falsa em marketplace/rede social | Anúncio, pagamento antecipado, produto não entregue |
| `falso-intermediario` | Intermediação falsa (golpe da OLX/triangulação) | Comprador e vendedor reais enganados por terceiro |
| `falso-investimento` | Falso investimento / pirâmide / cripto | Promessa de rendimento; plataforma; depósitos sucessivos |
| `falso-emprego` | Falso emprego / tarefas remuneradas | Pequenos ganhos iniciais, depois "taxas" |
| `emprestimo-falso` | Empréstimo/consignado falso | Cobrança antecipada de taxa para liberar crédito |
| `golpe-afetivo` | Golpe afetivo ("do amor") | Relacionamento virtual, pedidos de dinheiro |
| `falso-sequestro` | Falso sequestro / extorsão por telefone | Ameaça e pedido urgente de transferência |
| `maquininha` | Maquininha adulterada / cartão trocado | Valor digitado divergente, troca de cartão |
| `fraude-cartao` | Uso indevido de cartão/dados | Compras não reconhecidas |
| `fraude-documental` | Abertura de conta/crédito com documento falso | Cadastro com dados da vítima |
| `outro` | Outra | Descrever |
