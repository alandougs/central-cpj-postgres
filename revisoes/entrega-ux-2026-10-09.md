# Central CPJ / ASTRA — entrega de interface e sincronização

Data: 09/10/2026. Demandas expressas do operador: ordenação numérica das O.S., acesso à pasta dos relatórios, visualização leve de DOCX/PDF e sincronização do código com o GitHub.

## Comportamento entregue

- Casos ordena a lista pelo número da O.S. em ordem crescente, inclusive quando o número está no ID do caso. A busca e os filtros permanecem disponíveis; os alertas de prazo continuam no Início.
- A ficha oferece o atalho **📁 Relatórios**, que abre `03-relatorios` do caso no computador da Central, com a permissão de trabalho existente. Também oferece navegação para a seção Relatórios.
- **Visualizar** abre uma janela interna somente ao clicar. Ao fechar, o documento é descarregado.
- PDF usa o leitor nativo do navegador, conferido no Chrome. Navegadores sem esse leitor podem usar **Abrir original**.
- DOCX usa uma prévia HTML local de texto e tabelas, preservando a sequência dos blocos e negrito/itálico simples. Não exige nova biblioteca, Word ou conversão para PDF. A formatação completa, imagens e cabeçalhos continuam no arquivo original.
- A prévia respeita permissões, restrição de caminhos e limites de tamanho. Não envia documentos a serviços externos. A abertura local de arquivos também passou a validar caminhos com `realpath/commonpath`.

## Validação realizada

- `teste_relatorios_interface_ux01.py`: 6 verificações aprovadas (ordem numérica real na renderização, filtros, ID sem número, carregamento sob demanda, fechamento, DOCX e sintaxe JS).
- `teste_visualizador_relatorios_ux02.py`: 12 verificações aprovadas (conteúdo, escape HTML, ordem dos blocos, Word/PDF, permissões, limites e pasta simulada).
- Regressões de navegação, interface, segurança e modo solo: 6 + 15 + 11 + 7 verificações aprovadas.
- Ensaio visual em workspace fictício: O.S. 9, 10 e 100/2099; DOCX com texto e tabela; PDF no Chrome. Nenhum caso real usado no ensaio.
- Auditoria geral anterior à integração destas demandas: 46/60 suítes com retorno zero, 14 falhas, 397,54 s. Uma suíte aprovada estava vazia, portanto o retorno zero não comprova cobertura. Não houve homologação geral nesta entrega.

## Pendências observadas na auditoria geral

Testes inválidos por sintaxe; regressões de desempenho e checkpoints de extração; divergência entre a esteira e o squad anunciado; contrato de importação; execução/progresso de IA e fallback; teste de qualidade com caminho relativo incorreto; E2E com timeout. O teste global de workspace observou mudanças concorrentes e não prova, isoladamente, escrita indevida.

Há registros de conclusão cujo teste ou relatório técnico está vazio. O percentual da fila é administrativo e não deve ser tratado como certificação do produto. A fila operacional de O.S. e a baixa da produção também precisam de reconciliação humana: conclusão do trabalho, existência de DOCX e entrega oficial são estados diferentes.

## Documentação e publicação

`PRD.md` permanece reservado à DJ01 ativa. A atualização do estado atual e do registro de mudanças desta entrega deve ser incorporada pela CL04 após a liberação dessa reserva; este arquivo e as conclusões UX01/UX02 mantêm o registro imediato.

A sincronização utiliza o remoto já configurado `alandougs/central-cpj-postgres`, na branch de trabalho `consolidacao-2026-10-01`. Somente código e procedimentos genéricos auditados entram na publicação. Exemplos operacionais identificáveis foram generalizados; autos, arquivos de produção, credenciais e relatórios reais não compõem a entrega. A sincronização da branch não certifica a suíte geral nem altera a branch padrão.
