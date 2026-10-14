# ASTRA — homologação de outubro de 2026

Este documento distingue a integração automatizada em dados fictícios da aceitação humana. Não declara homologação de autos reais, assinatura válida, qualidade da inferência de IA ou autorização para uso oficial.

## Integração AST170

Comando, a partir da raiz do checkout de desenvolvimento:

```powershell
& 'C:\CPJ - TRABALHO\.venv\Scripts\python.exe' -X utf8 plugin/investigacao-cpj/app/testes/teste_astra_ast17_e2e.py
```

Requer o runtime Node/Playwright já instalado no cache do Codex, Microsoft Edge e dependências Python do projeto. A ausência de Node falha o teste; não aparece como E2E aprovado por `skip`. O teste F03 anterior continua dependente de Python Playwright, ausente no ambiente de referência desta execução.

O novo teste cria um workspace em `%TEMP%\cpj-astra-ast17-e2e-*`, um modelo DOCX geométrico sem assinatura real e um PDF fictício nativo de três páginas, com O.S. também na última página. Sobe o servidor local em porta livre, desativa o agente embutido e o modelo local opcional. Não lê modelos, casos, usuários ou configurações de produção. O conteúdo fictício de análise, o CSV financeiro e o texto da minuta são determinísticos: **nenhum executor de IA foi exercitado**. A extração, indexação, rotas HTTP, páginas Edge, persistência manual, reinício, geração DOCX, conferência de entrega e atualização do painel usam os componentes reais.

O brasão `/static/brasao-pcsp.png` é um asset ignorado ausente neste worktree. A rodada estrita em `%TEMP%\cpj-astra-ast17-e2e-6hgfptw3` falhou com três 404 desse recurso e foi preservada. Com autorização do integrador, **somente essa URL** recebe uma figura geométrica fornecida pelo harness; não se copiou ou publicou brasão/assinatura real. Os demais recursos e erros de console continuam sob asserções estritas. A disponibilidade do brasão oficial não foi validada por esta integração.

| Requisito | Fixture e verificação | Evidência |
|---|---|---|
| Receber e extrair O.S. | Upload no formulário; aguarda processamento concluído, Markdown com página 3, entidades e O.S. transcrita | `upload.log`, `upload.png`, `01-extracao` fictícia |
| Originais preservados | SHA-256 do PDF antes do upload e após FINAL | `resultado.json` |
| Fontes do grafo | CSV fictício com documento/página/fls.; inspetor exibe referência e recurso responde 200; ASTRA contextual retorna relações | `fontes.log`, `fontes.png` |
| Fonte autoritativa manual | Criação, duplicata 409, reindexação e reinício; identidade manual e documental preservadas | `estado.json`, diretório interno fictício |
| Remoção delimitada | Excluir manual por ID/versão; repetição 409; contrato por tupla recusado; sem CSRF 403; documental continua | `relatorio.log` |
| Editor e DOCX separados | Salvar mantém editor, nenhum DOCX implícito; reabrir conserva conteúdo; botão DOCX retorna 200 | `03-relatorios` fictício, `relatorio.log` |
| FINAL por decisão explícita | Minuta com `[PENDENTE]` recebe 409 sem criar FINAL; corrigida recebe 200 por botão com confirmação, sem forçar | `estado.json`, conferência JSON/MD e FINAL fictícios |
| Produção | Caso entregue e painel inclui seu ID | `resultado.json`, `relatorio.png` |
| Falhas do navegador | Exceção de página/HTTP 5xx ou tentativa externa do navegador falham a fase | Logs JSON das fases |

As capturas e logs ficam em TEMP mesmo quando o teste falha; não são publicados. `servidor.log` registra o processo e as requisições. `resultado.json` só é escrito após todas as etapas aprovadas, com ambiente e hashes de fontes no início/fim; os logs das fases registram a versão do Edge. Estado parcial e captura `*-falha.png` permitem distinguir falha de preparação, de seletor e de produto. Os hashes não substituem o snapshot congelado da suíte geral final do integrador.

Execução focal final de 14/10/2026: **1 teste aprovado, 36,283 s**, Windows 11 AMD64, Python 3.12.14, Edge 155.0.4283.45. Evidências em `%TEMP%\cpj-astra-ast17-e2e-c0a929t6`: três fases com zero exceção de página, erro de console, HTTP 5xx e tentativa externa do navegador; bloqueio 409 e aprovação 200 de FINAL registrados em `estado.json`. O F03 adaptado foi invocado separadamente: **0 testes executados, 1 skip** por ausência de Python Playwright. Não é aprovação do cenário OCR do F03. As primeiras rodadas ajustaram esperas/seletor/contexto do próprio harness; a rodada 404 citada acima permanece como limitação do asset, sem correção de produto por esta tarefa.

## Complementos da issue 17

O E2E acima é um cenário integrado, não substitui as suítes de isolamento, concorrência, pacote/backup e entradas hostis. A execução geral rápida/completa e sua contagem final pertencem ao registro do integrador. Uma suíte interrompida com continuação em snapshot deve ser descrita como tal, sem alegar uma única execução homogênea.

| Risco | Testes focais existentes |
|---|---|
| Append-only, CAS, migração, backup/exportação/importação e tombstones | `teste_astra_ast06_store.py`, `teste_astra_ast11_api.py` |
| Remover anotação sem remover fonte documental; autorização | `teste_astra_ast07_api.py`, `teste_astra_ast07_ui.py` |
| Todas as referências, caminhos confinados e ausência de fonte | `teste_astra_ast08_api.py`, `teste_astra_ast08_ui.py` |
| Homônimos, contas/Pix e perguntas locais delimitadas | `teste_astra_ast10.py` |
| Conferência humana, candidato, histórico e fonte ausente | `teste_astra_ast11_api.py`, `teste_astra_ast11_ui.py` |
| Rascunho, conflitos e geração explícita | `teste_astra_ast12.py` |
| Paginação, totais, concorrência e ausência de índice | `teste_astra_ast14_api.py`, `teste_astra_ast14_ui.py` |
| Polling, recuperação e interrupção | `teste_astra_ast15_ui.py` |

As métricas rastreáveis estão em [SQL/API](metricas-astra/sql/README.md), [grafo](metricas-astra/grafo/README.md) e [polling](metricas-astra/polling/README.md). Cada experimento descreve método, amostras, fontes e limites próprios; não se devem combinar p95 de workloads diferentes. Na medição SQL de 1.000 casos densos, a busca global completa teve p50 de cerca de **13,3 s**, contra uma consulta antiga que cortava resultados. A redução de instruções/conexões não elimina esse custo de contagem exata. O E2E funcional não mede FPS, RAM ou latência p50/p95 e não deve ser apresentado como benchmark.

## Roteiro humano — execução separada

1. Em workspace de homologação, receber a O.S. fictícia e conferir a O.S. transcrita contra todas as páginas, especialmente o final e continuações. Conferir qual O.S. vigora pelo conteúdo/data, não pela posição.
2. Abrir o caso no ASTRA; conferir contagens e avisos de materiais. Selecionar entidade identificada por documento/CPF/conta, sem unir homônimos pelo nome. Abrir cada fonte e comparar página/fls., trecho e recurso original ou derivado.
3. Criar uma hipótese manual com evidência; conferir que continua hipótese. Reindexar e reiniciar; verificar que permanece. Remover apenas essa anotação e confirmar que a fonte documental continua disponível.
4. Pedir as consultas locais suportadas sobre conta recebedora, chave Pix, candidatos e documentos do fluxo. Verificar contexto do caso e a indicação de escopo global quando aplicável. Conferir lacunas/contradições no documento; a resposta não comprova autoria.
5. No inspetor, distinguir conferir original de conferir extração; registrar observação/candidato e abrir histórico. Conferir usuário/data e recuperar após conflito sem perder texto. Repetir leitura com perfil sem permissão de escrita.
6. Redigir a minuta atendendo cada solicitação da O.S.; salvar, sair e voltar. Confirmar que salvar não criou DOCX. Gerar DOCX explicitamente e conferir visualmente metadados, texto, referências, formatação e bloco de assinatura no Word.
7. Tentar finalizar uma minuta com pendência: o gate deve bloquear. Corrigir com base na fonte, regenerar e revisar. Só então definir FINAL, confirmar a decisão humana e conferir baixa/estatísticas. Nunca usar força para fazer a homologação parecer aprovada.
8. Em cópia descartável, simular índice ausente, desconexão e erro temporário; confirmar aviso, texto preservado, cancelamento e retomada. Exportar/restaurar somente a fixture, comparar anotações e históricos e conferir que nenhum original mudou.

## Limites de aceitação

O novo fluxo usa PDF nativo, sem executar OCR de página escaneada. F03 mantém o cenário OCR separado, sujeito às dependências declaradas. Não valida fidelidade de OCR difícil, resposta de provedor/modelo, inferência investigativa, assinatura manuscrita ou renderização final no Word. Os arquivos gerados são fictícios, e a aprovação do gate automatizado não substitui revisão e decisão do investigador. Roteiro humano ainda depende de execução e registro do operador; não está marcado como concluído por este documento.
