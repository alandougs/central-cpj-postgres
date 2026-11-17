# Implementação e Verificação da Interface CPJ Astra — AG90

Data: 28/10/2026.
Agente responsável: Antigravity-AG90 (Engenharia de Frontend e Experiência de Uso).
Base de desenvolvimento: `codex/sincronizacao-enxuta-20261027`, commit `7d910cc`.
Diretriz do operador: Frente visual do site mantida sob responsabilidade do GPT Astra (VU01); a frente Antigravity (AG90) implementou e verificou integralmente a esteira operacional, navegação, conferência lado a lado, mapa único com descarte de race conditions, grafo funcional com diferenciação de fontes, filtros financeiros e notas analíticas, com validação de ponta a ponta por Edge headless.

---

## 1. Escopo e Fronteiras

- **Frente Antigravity:** interface web local (`index.html`, `central.css`, `apple-cpj.css`), componentes JavaScript (`casos.js`, `inteligencia-mapa.js`, `fluxograma.js`, `core.js`), e suíte de testes de interface Playwright/Edge `teste_interface_astra_ag90.py`.
- **Frente GPT Astra / Codex:** acabamento visual do site (VU01), contratos de backend, rotas e persistência durável (`afirmacoes_fontes.py`, `tarefas.py`, `plantao.sqlite`).
- **Frente Cline:** simplificação e empacotamento.
- **Proteções ativas:** sem push, sem merge, sem alteração de banco/casos operacionais, sem envio de dados reais a serviços externos; testes conduzidos exclusivamente com fixtures sintéticas e instâncias isoladas em portas temporárias.

---

## 2. Matriz de Requisitos e Critérios de Aceitação

| ID | Requisito | Status | Implementação Realizada | Evidência / Validação |
|---|---|---|---|---|
| **AG-R01** | Preservar e completar o visual existente; identidade ASTRA/CPJ; temas claro/escuro; foco e densidade. | Aprovado | Tokens de cor preservados, anéis de foco consistentes (`:focus-visible` >= 2px), remoção de botões duplicados no HTML (`#b-gr-correlacoes`). | `test_01_visual_temas_foco_contraste`: capturas Edge para Desktop (1440px), Tablet (720px) e Mobile (390px) nos dois temas em `%TEMP%/cpj-astra-ag90-20261028/`. |
| **AG-R02** | Simplificar fluxo operacional: O.S. -> Documentos -> Extração -> Solicitações -> Análise -> Relatório -> Revisão -> DOCX -> Finalização humana. | Aprovado | Esteira Operacional em 5 etapas no detalhe do caso (`casos.js`), com badges de estado explícitos (concluída, ativa, pendente, bloqueada), links diretos para as fontes e botões de ação integrados. | `test_02_esteira_fluxo_5_etapas`: validação da esteira com 5 etapas e transição de status no Edge. |
| **AG-R03** | Mapa único e utilizável; atalhos canônicos; prevenção de race conditions; identificação de precisão aproximada. | Aprovado | Instância canônica única (`#mapa`), controle sequencial de requisição (`seqRequisicaoMapa`) com descarte de respostas obsoletas/fora de ordem, indicador `#mapa-carregando`, badge `.badge-aproximada` para centróides municipais e seção acessível de registros não localizados. | `test_03_mapa_unico_race_condition`: simulação de requisição com atraso de 500ms descartada em favor de resposta mais recente; sem sobreposição de estado. |
| **AG-R04** | Grafo funcional e fontes corretas; direção de setas; vínculo manual vs documental; sanitização de texto e apóstrofos. | Aprovado | Remoção restrita a vínculos manuais via `{id, caso, versao}`, preservando vínculos documentais sem botão de exclusão; escape seguro contra XSS e quebra de atributos em nomes com apóstrofo (`D'Ávila`) via `esc()` aprimorada. | `test_04_grafo_fontes_manual_vs_documental`: validação de escape e ausência de execução de script. |
| **AG-R05** | Navegar da afirmação ou valor até a fonte; original, transcrição, derivado e referência. | Aprovado | Links diretos no detalhe do caso apontando para folhas e páginas (`#page=N`), mantendo o contexto do caso e permitindo abertura direta do arquivo. | `test_05_navegacao_afirmacao_ate_fonte`: validação de âncoras para `01-extracao` com referências a folhas. |
| **AG-R06** | Revisão guiada da O.S.; status atendida/parcial/pendente; aviso de reconferência após edição da minuta. | Aprovado | Painel de Solicitações da O.S. (`#painel-solicitacoes-os`), listando determinações da autoridade e solicitações mapeadas; exibição de `.aviso-reconferencia` quando há mais de uma minuta gerada (`j.relatorios.length > 1`). | `test_06_revisao_solicitacoes_os`: detecção e exibição do alerta de nova versão da minuta. |
| **AG-R07** | Conferência documental: PDF e extração lado a lado; página PDF vs folha dos autos. | Aprovado | Modal `#modal-conferencia-documental` com visualizador duplo: iframe do PDF original à esquerda e transcrição Markdown da página à direita; seletor de páginas sincronizado e distinção entre página do PDF e folha dos autos. | `test_07_conferencia_lado_a_lado`: abertura do modal, sincronização de página, renderização do Markdown e fechamento limpo. |
| **AG-R08** | Eventos, transações financeiras e filtros estruturados; crédito vs débito vs saldo; precisão temporal. | Aprovado | Visão em tabela estruturada (`#fx-visao-tabela`) alternável via `#b-fx-toggle-visao`; colunas de camada, sentido (Transferência), data/hora, precisão temporal (`.badge-precisao`), origem, destino, valor em R$ e fonte documental; filtros interativos de data, valor mínimo/máximo e termo. | `test_08_eventos_transacoes_filtros`: renderização de transações com apóstrofo preservado, formatação R$, precisão e filtragem por valor mínimo. |
| **AG-R09** | Consultas salvas e notas analíticas com etiqueta de hipótese; persistência sem duplicação. | Aprovado | Painel `#painel-notas-caso` integrado ao detalhe do caso com persistência em `localStorage` (`cpj_notas_<id>`); inserção obrigatória da etiqueta `[HIPÓTESE / NOTA DO INVESTIGADOR — NÃO CONSTITUI FATO DOCUMENTADO]`; suporte a salvar consulta atual e exclusão individual. | `test_09_notas_analiticas_e_consultas_salvas`: inserção de nota com etiqueta de hipótese e remoção funcional. |
| **AG-R10** | Coerência com extração Markdown; remoção de referências legadas a CSV no cadastro e em `casos.js`. | Aprovado | Texto de cadastro atualizado em `index.html` ("Markdown por página e indexação"); painel de disponibilidade em `casos.js` reconhece extrações modernas em Markdown puro sem reportar erro ou falta de `entidades.csv`. | `test_10_coerencia_markdown_enxuto`: teste com caso sintético contendo apenas Markdown, exibindo status saudável `consultar na transcrição (Markdown)`. |

---

## 3. Resultados dos Testes Automatizados

### 3.1. Suíte Principal: `teste_interface_astra_ag90.py`

Comando executado:
```powershell
.venv\Scripts\python.exe -B plugin/investigacao-cpj/app/testes/teste_interface_astra_ag90.py
```

Resultado:
```text
test_01_visual_temas_foco_contraste (__main__.InterfaceAstraAG90.test_01_visual_temas_foco_contraste)
AG-R01: Verifica temas claro/escuro, cores Astra (#31D96D), foco visível e capturas. ... ok
test_02_esteira_fluxo_5_etapas (__main__.InterfaceAstraAG90.test_02_esteira_fluxo_5_etapas)
AG-R02: Verifica a Esteira Operacional com as 5 etapas, status, links e botões de ação. ... ok
test_03_mapa_unico_race_condition (__main__.InterfaceAstraAG90.test_03_mapa_unico_race_condition)
AG-R03: Verifica mapa único, badge aproximada e descarte de respostas obsoletas. ... ok
test_04_grafo_fontes_manual_vs_documental (__main__.InterfaceAstraAG90.test_04_grafo_fontes_manual_vs_documental)
AG-R04: Verifica grafo com fontes, diferenciação manual/documental e escape de apóstrofo. ... ok
test_05_navegacao_afirmacao_ate_fonte (__main__.InterfaceAstraAG90.test_05_navegacao_afirmacao_ate_fonte)
AG-R05: Verifica links diretos da afirmação/valor até as folhas e páginas. ... ok
test_06_revisao_solicitacoes_os (__main__.InterfaceAstraAG90.test_06_revisao_solicitacoes_os)
AG-R06: Verifica painel de revisão de solicitações e alerta de nova versão. ... ok
test_07_conferencia_lado_a_lado (__main__.InterfaceAstraAG90.test_07_conferencia_lado_a_lado)
AG-R07: Verifica o modal de conferência documental lado a lado (PDF x Markdown). ... ok
test_08_eventos_transacoes_filtros (__main__.InterfaceAstraAG90.test_08_eventos_transacoes_filtros)
AG-R08: Verifica visão em tabela estruturada de eventos financeiros e filtros. ... ok
test_09_notas_analiticas_e_consultas_salvas (__main__.InterfaceAstraAG90.test_09_notas_analiticas_e_consultas_salvas)
AG-R09: Verifica persistência de notas analíticas com alerta de hipótese. ... ok
test_10_coerencia_markdown_enxuto (__main__.InterfaceAstraAG90.test_10_coerencia_markdown_enxuto)
AG-R10: Verifica coerência com extração moderna Markdown (sem entidades.csv). ... ok

----------------------------------------------------------------------
Ran 10 tests in 28.767s

OK
```

### 3.2. Suítes de Regressão Executadas

1. `teste_apple_ui_ap39.py`: 5 testes executados em 26.637s — **OK** (100% aprovado).
2. `teste_grafo_interface_rp35.py`: 4 testes executados em 10.840s — **OK** (100% aprovado).
3. `teste_interface_rg26.py`: 1 teste executado em 2.882s — **OK** (100% aprovado).

### 3.3. Evidências Visuais e Capturas Sintéticas

Capturas salvas em `C:\Users\Usuario\AppData\Local\Temp\cpj-astra-ag90-20261028`:
- `astra-desktop-dark.png` (1440x900, tema escuro)
- `astra-desktop-light.png` (1440x900, tema claro)
- `astra-tablet-dark.png` (720x900, tema escuro)
- `astra-tablet-light.png` (720x900, tema claro)
- `astra-mobile-dark.png` (390x844, tema escuro)
- `astra-mobile-light.png` (390x844, tema claro)

---

## 4. Conclusão da Frente AG90

A implementação funcional e a verificação operacional da interface do CPJ Astra foram concluídas com êxito. Conforme orientação do operador, o trabalho visual/estético fica sob responsabilidade do GPT Astra (VU01), enquanto a infraestrutura de componentes, fluxo investigativo, conferência, navegação de fontes, proteção contra race condition no mapa e integridade no grafo foram plenamente implementados e validados por suíte automatizada.
