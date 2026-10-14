# Módulos estáticos ASTRA — AST16

Extração literal de `b97b445`, sem alterações funcionais, de nomes globais, IDs, endpoints ou permissões. O único CSS inline passou para `static/css/central.css`. O script único passou para os arquivos abaixo, na mesma ordem do programa original, com carregamento clássico bloqueante no rodapé. Não adicionar `type=module`, `async`, `defer`, IIFE ou inicialização antecipada sem revisar seus contratos e testes.

| Ordem | Arquivo em static/js | Responsabilidade e dependências |
|---|---|---|
| 1 | core.js | API, estado/permissões, seletores, formatadores, upload e feedback. API referencia sessão somente quando chamada. |
| 2 | sessao.js | Login, setup, conta inicial, montagem e navegação. Callbacks usam os domínios carregados depois. |
| 3 | polling.js | `tc`, `nCiclo`, `ciclo`; consome tarefas/agentes, fila, pendências e IA do caso. |
| 4 | inicio.js | Painel e atalhos para casos; usa core e navegação. |
| 5 | recebimento.js | Upload e detecção, consentimento de PDF, cadastro, fila; usa core e consentimento de casos. |
| 6 | casos.js | Listas/ficha, comparador, `tq`, `casoAberto`, arquivos, visualizador, FINAL, consentimento e IA. Usa editor e sistema. |
| 7 | editor.js | Estado da minuta, autosave, controle de revisão/conflitos, DOCX explícito e guardas de saída. Usa API, caso e navegação. |
| 8 | pesquisa.js | Pessoas, textos e vínculos de consulta; usa core/casos. |
| 9 | grafo.js | Estado `gr*`, canvas, física, desenho, filtros e inspetor; usa comparador de casos e callbacks de vínculos manuais. |
| 10 | estatisticas.js | Atalho de exportação; usa navegação e DOM de sistema. |
| 11 | sistema.js | Tarefas/agentes, dados/bases/referências, perfis/usuários/conta/rede; usa `tq` de casos e configuração IA/LLM. |
| 12 | ia-config.js | Preferências da via de IA; usa core e DOM. |
| 13 | llm.js | Provedores e catálogos; usa core e DOM. |
| 14 | fluxograma.js | Fluxo financeiro/canvas; usa core e caso atual. |
| 15 | vinculos.js | Modal de relações manuais e exclusão por ID/caso/revisão; usa grafo/core/caso. |
| 16 | bootstrap.js | Única chamada inicial `iniciar();`, depois de todos os domínios. |

As funções continuam públicas no ambiente global clássico. Os `let`/`const` compartilham o mesmo ambiente léxico global; não convertê-los em propriedades `window`. As dependências cíclicas anteriores continuam explícitas: callbacks só executam após o bootstrap. O ciclo da física do grafo é distinto do polling HTTP.

Na migração, concatenar os 16 arquivos na ordem do HTML reproduziu exatamente o JavaScript anterior do worktree; o CSS também permaneceu idêntico. SHA-256 dos bytes extraídos no Windows: JS `1edadfe40a6b520cd9a294c1808fd5d98e29ffcac1c83ee785246117374ca505`, CSS `84b1e2ff309d4a0a0b3558583370b4e79ec8e829bf92d2a21b4e87df28b6aae0`. A comparação com o conteúdo versionado no Git normaliza CRLF para LF, pois a configuração de checkout pode alterar apenas as quebras de linha; não há mudança de instruções ou da cascata. Esses hashes documentam esta migração; não são uma proibição de evolução posterior.

Os testes de fonte usam `app/testes/fonte_interface.py`: recursos locais são expandidos na ordem do HTML; ausências, recursos externos e mudança para carregamento assíncrono não são ignorados. Trechos que atravessam fronteiras de arquivos usam o JavaScript concatenado. Verificações de sintaxe compilam o programa inteiro, preservando a detecção de declarações léxicas duplicadas. As duas suítes HTTP buscam JS/CSS no mesmo servidor e exigem status 200 e MIME correto. O teto de 300 kB aplica-se à interface agregada, e as verificações sem CDN continuam cobrindo HTML bruto e recursos. Os testes de navegador carregam os arquivos reais.

Antes de editar, assumir tarefa e reservar caminhos exatos no quadro canônico. Para execução paralela, o layout/física do grafo da issue 13 pode reservar `js/grafo.js` e seu teste, enquanto polling da issue 15 reserva `js/polling.js` e seu teste. CSS é `css/central.css`; HTML e contratos compartilhados ficam sob coordenação. Se a issue 15 precisar controlar respostas iniciadas por outros domínios, declarar também as reservas específicas de core/casos/sistema antes de editar. Não reservar `static/` inteiro para um domínio e não alterar outro módulo sob pretexto de pequena correção.

Validação é realizada exclusivamente em workspaces fictícios. Para permitir outras tarefas após o congelamento, uma cópia global do código é produzida em TEMP; a suíte completa roda a partir dessa cópia, e seu runner continua criando sandboxes por teste. Assim nenhuma suíte posterior lê uma versão concorrente do checkout ativo.
