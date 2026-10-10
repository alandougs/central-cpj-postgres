# AG04 — verificação da suíte completa

Registro retomado pelo loop de 09/10/2026. **Duas execuções completas aprovadas em 10/10/2026.** Resultados focados não as substituem; mudanças posteriores exigem validação do comportamento afetado.

## Diagnóstico inicial

`ferramentas/testar-tudo.py`, executado com Python 3.12.14 do runtime Codex, dependências locais via `PYTHONPATH` e UTF-8, terminou em **54/64 suítes aprovadas, 555,20 s**, durante alterações concorrentes. Isso é diagnóstico, não execução final estável.

As falhas foram: RV06 e PX01 (sintaxe/fixtures, TS01), desempenho F02/extração/F12 (CX01), GF02 e UX01 (QuickJS ausente), fallback/qualidade/cancelamento C03 (TS02). Verificações focadas posteriores passaram; CX03 também removeu a falha esperada de colisão de logs da squad. AG05 recuperou teste antes vazio, que não era evidência de cobertura.

**Isolamento:** depois desse diagnóstico, foi descoberto que `teste_fulltime.py` instalava e removia o atalho Startup pelo APPDATA real. O runner não isolava essa variável. O operador foi informado; estado anterior do atalho é desconhecido. AG02 foi reaberta para corrigir o teste e provar preservação de sentinela herdada fictícia. Não executar novamente FullTime antes dessa correção. Este diagnóstico não pode ser descrito como inteiramente sem alteração externa aos temporários.

## Ambiente das verificações seguintes

- Python: `C:\Users\alan_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`.
- `PYTHONPATH`: dependências de teste em `C:\Users\alan_\AppData\Local\Temp\cpj-loop-test-deps-20261009` e bibliotecas da `.venv` do projeto. `PYTHONUTF8=1`.
- Casos fictícios e código clonado pelo runner, portas temporárias. Nenhuma API de IA real.
- Playwright preparado no diretório temporário de dependências para conferência visual; usar Chrome headless com perfil temporário, sem perfil do operador.

## Verificações de integração anteriores ao fechamento

| Verificação | Resultado | Limite |
|---|---|---|
| SE01 segurança e interface | 7 + 5 testes aprovados, conferência independente | Aceite positivo ausente foi detectado depois; correção incluída na PX05 e deve integrar a execução final. |
| Central HTTP após SE01 | Retorno 0, 93,30 s | Processamento, permissões, DOCX/FINAL, exportar/importar e perfis fictícios; não é piloto IA. |
| AG05 | Cinco testes próprios e suíte de reservas/reaproveitamento aprovados | Somente O.S. e documentos fictícios. |

## Execuções finais

| Rodada | Estado | Suítes | Tempo | Falhas/intermitências |
|---|---|---|---|---|
| 1 | aprovada | 71/71 | 560,67 s de testes; 833,09 s incluindo cópias/limpeza | Nenhuma falha |
| 2 | aprovada | 71/71 | 841,92 s de testes; 1.305,95 s incluindo cópias/limpeza | Nenhuma falha; mais lenta, sem repetição ou ajuste de timeout |

AG02, PX05/PX06/PX07 e demais mudanças autorizadas devem estar liberadas antes das execuções finais. Uma falha exige registro e tarefa responsável; AG04 não corrige código silenciosamente.

Primeira tentativa final interrompida pelo integrador após 13 suítes aprovadas: a conferência independente no Chrome encontrou o corpo do aviso externo quase branco sobre branco no tema escuro. PX06 reaberta para ajuste mínimo e regressão; esta tentativa **não conta como rodada final**. Log preservado em `C:\Users\alan_\AppData\Local\Temp\cpj-ag04-duas-20261009\diagnostico-interrompido-contraste.log`. Processo do harness e sua árvore foram encerrados após identificação pelo caminho exato. As duas rodadas serão reiniciadas depois da nova liberação e prova visual. APPDATA adicional fictício será mantido no harness.

Após correção mínima das cores do aviso, o Chrome headless repetiu sete cenários de cadastro/ficha, modos, aceite e recusa: todos aprovados, sem erros de console nem HTTP externo. Contraste computado: **14,69:1 escuro e 17,06:1 claro**, ambos acima de 4,5:1; integrador conferiu captura e JSON. Evidências TEMP: `cpj-px06-visual-iwo86_bs/evidencias.json`, `aviso-dark.png` e `aviso-light.png`. Isso verifica a interface/enfileiramento fictício; não comprova inferência ou processamento externo. Browser e servidor próprios encerrados.

Rodada posterior terminou em **70/71 suítes, 544,52 s** de testes (**803,73 s** de execução do harness com cópias/limpeza). Única falha F03: fixture omitia campos obrigatórios e recebeu HTTP409 com sete bloqueios do gate FINAL. TS03 corrigiu somente fonte fictícia complementar e teste/observação, sem alterar nem forçar gate. Conferência independente do integrador: F03 retorno zero em **26,78 s**, fluxo real Edge **19,24 s**, OCR/minuta/DOCX/FINAL/baixa/painel aprovados. Log vermelho preservado em TEMP `diagnostico-f03-red.log/json`. As duas rodadas finais foram reiniciadas sobre o core estabilizado após TS03; trabalho do acervo ocorre em diretório separado, não clonado pelo runner.
