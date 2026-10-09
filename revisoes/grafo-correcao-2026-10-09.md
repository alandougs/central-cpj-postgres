# ASTRA — correção do grafo de vínculos

Entrega GF01/GF02, em 09/10/2026, a pedido do operador.

## Defeitos confirmados

O seletor usava as OS encontradas nas arestas do índice e deixava de fora OS cadastradas sem vínculos. A busca só consultava nomes completos; o fallback por CPF/conta/Pix não funcionava porque a rotina de vínculos sempre incluía um nó inicial, mesmo sem conexões. A interface não explicava resultados vazios.

O ensaio visual também confirmou um erro no cálculo de atração: os dois extremos da conexão recebiam força no mesmo sentido, fazendo os nós se afastarem até sair da tela. A força do extremo de destino foi corrigida para o sentido oposto.

## Comportamento entregue

- O seletor recebe as OS do cadastro, em ordem numérica, inclusive sem índice ou sem arestas. A seleção é preservada e a lista atualiza a cada consulta.
- Busca parcial por nome e identificadores, com filtro de OS combinado. Os registros homônimos continuam separados; nomes são candidatos e não comprovação de identidade.
- Mensagens de carregamento, busca sem resultado, OS sem vínculos, filtros que ocultam todos os nós, índice ausente e erro de carregamento.
- Respostas antigas não substituem consultas mais recentes. Falhas removem o desenho anterior para não exibir resultados desatualizados.
- A contagem de conexões respeita os nós visíveis. O desenho estabiliza e centraliza ao final do posicionamento; movimentação e zoom manuais interrompem esse ajuste automático.
- O inspetor continua exibindo relações e fontes/localizadores existentes. A consulta não cria vínculos nem reindexa dados operacionais.

## Verificação

- 11 testes fictícios da API GF01, incluindo metadados de OS sem índice/arestas, busca parcial, homônimos, identificadores, filtro combinado e autorização.
- 10 testes fictícios da interface GF02, incluindo carga assíncrona, seleção, ordem numérica, desenho de nós/arestas, fontes no inspetor, filtros, erros e estabilidade/enquadramento após 250 passos do cálculo.
- Regressões aprovadas: 6 testes de modularização, 6 da interface UX01, 11 de segurança e a suíte de consultas relacionais L01/L02.
- Ensaio Chrome em workspace isolado: OS 9, 10 e 100/2099; busca parcial de pessoa fictícia com seis nós/cinco conexões; seleção de OS sem vínculos e inspeção de fontes. Nenhum caso real utilizado como fixture.
- Servidor em uso atualizado pelo inicializador oficial 24/7, após confirmação de ausência de tarefas em andamento. Conferência de API feita apenas com contagens/metadados; os resultados confirmaram que a lista do grafo coincide com a lista de casos e que a busca parcial retorna vínculos.

## Limites e documentação

A visão geral e a busca mantêm limite de 400 conexões; a busca resolve até 30 nós iniciais. Se uma OS não tiver vínculos no índice, aparece uma mensagem e permanece disponível no seletor. Esta entrega não certifica a suíte geral do produto nem reconcilia estados operacionais de OS.

O PRD permanece reservado pela tarefa DJ01. Este registro e a conclusão GF01/GF02 devem ser incorporados pela CL04 ao estado atual e ao registro de mudanças quando a reserva for liberada.

A sincronização usa a branch de trabalho existente `consolidacao-2026-10-01`. Somente os arquivos desta correção e seu registro genérico entram na entrega; índice SQLite, autos, relatórios reais, credenciais e configuração operacional não são publicados.
