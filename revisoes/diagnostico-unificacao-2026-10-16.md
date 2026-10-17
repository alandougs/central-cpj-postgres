# Diagnóstico para unificação da Central CPJ

Data: 16/10/2026. Tarefa UN01. Base auditada: `d13db2871ac853c4e73c75ba33b505eae74d8eb2`, branch `codex/os-markdown-relatorio-20261014`.

## Conclusão

A branch de trabalho estava sincronizada com o GitHub, mas o projeto ainda não tem uma versão oficial que reúna as melhorias auditadas. Há diferenças entre branches, artefatos gerados e ambiente de testes. O desenho proposto está em `docs/superpowers/specs/2026-10-16-cpj-unificado-design.md`.

## GitHub e coordenação

- Após `fetch`, HEAD e upstream: zero commits à frente/atrás; árvore limpa antes desta documentação.
- `origin/main` é ancestral de HEAD e está oito commits atrás. Padrão remoto confirmado por `ls-remote --symref origin HEAD`: `master`, revisão `7e537c47...` de 28/09/2026.
- Comparação `origin/master...HEAD`: 12 commits exclusivos de master e 27 de HEAD. Comparação `origin/codex/astra-evolucao-20261014...HEAD`: 11 exclusivos de ASTRA e quatro de HEAD. São contagens de história, não quantidades de funcionalidades ausentes.
- [PR #18](https://github.com/alandougs/central-cpj-postgres/pull/18): branch atual para main, rascunho, oito commits e 61 arquivos.
- [PR #19](https://github.com/alandougs/central-cpj-postgres/pull/19): ASTRA para main, rascunho, 15 commits e 157 arquivos. Inclui parte das mudanças do PR18; não são conjuntos independentes.
- Integração simulada com `git merge-tree --write-tree --name-only`, sem alterar checkout: conflitos em `PRD.md`, `TAREFAS-COMPARTILHADAS.md` e `plugin/investigacao-cpj/app/static/index.html`. Mescla textual automática de outros arquivos não certifica compatibilidade funcional.
- Fila local no início da auditoria: 148 registros concluídos, nenhuma reserva ativa. GitHub: 14 issues abertas (#4 a #17). É necessário distinguir tarefa implementada de entrega integrada e homologada.
- Nenhum workflow versionado em `.github/workflows` na base auditada; check-runs e statuses vazios na revisão atual. A listagem de Actions mostrou uma execução antiga do Copilot, sem evidência de CI de testes para esses PRs.
- API de rulesets retornou lista vazia. Consulta de proteção de main/master retornou 403: proteção dessas branches não pôde ser verificada, e não deve ser declarada ausente.

## Integridade de dados — prioridade inicial

Na versão auditada, `rotas/consulta.py` grava vínculos manuais na tabela derivada `arestas`. O indexador executa `DELETE FROM arestas` ao reconstruí-la. Em workspace temporário vazio, foram inseridos nós fictícios e um vínculo manual; executar o indexador real da revisão auditada reduziu o número de vínculos manuais de um para zero, com saída bem-sucedida.

A rota de remoção atual seleciona extremidades e relação sem restringir origem manual nem usar ID imutável. A leitura do código mostra risco de remover correspondências documentais. Não foi executada exclusão em banco operacional.

A ASTRA contém correções candidatas para armazenamento autoritativo e exclusão por ID. Elas devem ser integradas e verificadas conjuntamente, evitando criar uma segunda solução concorrente. Nenhum dado real foi alterado nesta auditoria.

## Acompanhamento de processamento

`app/tarefas.py` mantém parte dos trabalhos em `self.t`, na memória do processo. `listar()` reúne trabalhos recentes dessa estrutura com pedidos convertidos de `Plantao`. `plantao.py` persiste pedidos, agentes, grupos, dependências e etapas em `config/plantao.sqlite`. `/api/tarefas` já oferece a listagem agregada.

Portanto, o ponto de partida é aproveitar essa agregação e tornar explícita e durável a relação entre O.S., execução e etapas. A interface única deve preservar cancelamento, reservas, consentimento, orçamento e limites dos executores existentes. Unificar a apresentação não exige serializar todo o processamento nem misturar tarefas de desenvolvimento com autos.

## Artefatos e ambiente

| Verificação | Resultado observado |
|---|---|
| `configurar-codex.py --verificar` | 12 adaptadores do projeto conferem |
| `configurar-codex.py --instalar-usuario --verificar` | Falha: entrada pessoal `cpj-projeto/SKILL.md` e `agents/openai.yaml` ausentes no caminho esperado |
| `pip check` | Sem dependências instaladas incompatíveis; não comprova que todos os requisitos de desenvolvimento estão instalados |
| Portáteis regenerados em cópia de `git archive HEAD` | 11 procedimentos divergem, mesmo normalizando datas; faltam regras atuais sobre nome/texto do relatório, assinatura e referências somente por fls. |
| Manifesto do plugin na fonte | Versão 0.3.3 |
| Staging/registro local conhecido do plugin Claude | Manifesto ausente no staging padrão e nenhum registro CPJ no arquivo consultado; outras instalações não foram descartadas |
| `ferramentas/atualizar-plugin.ps1` | Lista de extensões não inclui `.js`; omite os recursos versionados `fila-progresso.js` e `inteligencia-mapa.js` |
| Backup/restauração | Scripts existentes inspecionados; restauração operacional não executada nem certificada |

O exportador portátil foi executado apenas em cópia temporária. O atualizador instalado não foi executado, pois modifica instalação e versão. Os arquivos locais excluídos do Git pela SY03 permaneceram locais.

## Suíte completa da revisão versionada

Uma execução de `ferramentas/testar-tudo.py` em snapshot de `git archive HEAD`, usando o Python da `.venv` local: **79/91 suítes aprovadas; saída 1**. Tempo somado das suítes: 360,07 s; tempo de parede: 474,39 s. São grupos de testes, não 91 casos individuais. A Central HTTP isolada passou.

| Falhas da rodada | Evidência e classificação |
|---|---|
| `teste_consentimento_interface_se01.py`, `teste_grafo_interface_gf02.py`, `teste_modelos_api_ai03.py`, `teste_modos_px06.py`, `teste_relatorios_interface_ux01.py`, `teste_transcricao_visual_px05.py` | Seis suítes com `ModuleNotFoundError: quickjs`; requisito de desenvolvimento ausente. Não demonstram, por si, defeito do produto |
| `teste_desempenho_f02.py` | Subprocesso retorna 1 por Tesseract sem idioma `por`; ambiente OCR incompleto |
| `teste_casos_status_visual_codex.py` | Dois asserts esperam helper/classe antigos. Interface usa `caso-entregue` para entregue, compatível com a determinação UX03; provável teste obsoleto, requer conciliação com o requisito |
| `teste_interface_claude.py` | Espera um único bloco de script; a interface agora carrega JavaScript local externo. Demais verificações passaram; provável contrato de teste antigo |
| `teste_docx_f04.py` | Duas falhas em cinco testes: referência antiga com página PDF contraria a regra atual de somente fls.; expectativa de quebra antes da assinatura requer conciliação de fixture/layout. Não comprova defeito visual do DOCX |
| `teste_identidade_form_codex.py` | Quatro testes, oito subfalhas: espera seleção de cargo e formatação de CPF não encontradas no HTML auditado. Contrato estático não atendido; confirmar requisito e história antes de classificar como regressão |
| `teste_workspace_v01.py` | Falhou somente na comparação global de mtimes enquanto o agente principal escrevia a documentação UN01. Com as gravações suspensas, repetição exclusiva pelo mesmo runner passou em 12,17 s, saída 0 |

O placar original permanece 79/91; o reteste de workspace é evidência separada. Não foi reexecutada a suíte geral nem corrigido produto para fazer o diagnóstico passar.

Limitações declaradas pelo runner: um teste E2E ignorado, quatro testes de links simbólicos ignorados por falta de permissão, um teste de sintaxe JavaScript ignorado por ausência de QuickJS e verificação OCR não executada por indisponibilidade de Tesseract com português. Playwright também não está instalado no ambiente de desenvolvimento auditado. Nenhum desses casos deve ser contado como funcionalidade comprovada.

O runner descobre `app/testes/teste_*.py` e executa a Central HTTP separadamente. Isso não certifica automaticamente todos os testes de navegador existentes em subdiretórios. A homologação ponta a ponta permanece necessária.

Logs locais desta rodada estão no diretório temporário `cpj-auditoria-d13db28-u7_27bin`: `testar-tudo.log` e `workspace-v01-reteste.log`. O registro acima preserva os resultados relevantes sem publicar logs operacionais.

## Método e limites

Consultas estruturais usaram codebase-memory com checagem de cobertura; código fora do índice e arquivos estáticos foram consultados diretamente. Os testes usam cópia dos arquivos rastreados, sem casos, bases, credenciais, assinatura ou modelo de produção. Isso verifica a reprodutibilidade da revisão versionada, não a saúde de todos os componentes instalados nem a homologação visual com o operador.

O diagnóstico não efetua merge, não reinicia a Central, não instala dependências e não ativa provedores. A documentação desta UN01 é posterior à revisão usada na medição.
