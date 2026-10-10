# Registros obrigatórios das etapas — TS08 — 10/10/2026

P01 comprovou que a consolidação entregava ficha e pessoas, mas não os registros obrigatórios de solicitações da O.S. e dados faltantes; a redação entregava minuta sem rastreabilidade. Os revisores perceberam a ausência, porém remetê-la ao operador não cumpria AGENTS.md regras 11/17 e o procedimento de relatório. O sucesso técnico do contrato antigo não certificava conformidade integral.

O contrato da consolidação agora exige `solicitacoes-os.md` e `dados-faltantes.md`, além da ficha/pessoas. O prompt orienta O.S. vigente, item, trecho, página/fls., resposta/limite e identificação das lacunas com fonte, meio de obtenção e importância. Sem lacunas relevantes, deve registrar a conferência expressamente; não inventar dados ou diligências. A redação exige `rastreabilidade-vNN.md` da mesma versão da minuta, com afirmação material, fonte documental e distinção entre fato, relato, inferência e lacuna. Ajuste atualiza o mapa da mesma versão; o revisor continua em sessão independente, confrontando minuta/mapa com os autos, não usando o mapa como fonte.

Relatório não pula análise se os quatro produtos de consolidação estiverem ausentes/vazios. Retomadas também incorporam o contrato aos checkpoints antigos e recompõem a análise quando o plano salvo não tinha consolidação e seus registros faltam, sem incrementar a versão de redação já reservada. Produto concluído e disponível continua reutilizável pela regra normal de checkpoint; ausência/vazio refaz a etapa. Revisão limpa continua dispensando ajuste.

O guard existente (arquivo não vazio e metadata diferente antes/depois da sessão), captura de log antes do gate, cancelamento, cadeia EC01 e revisão independente não foram flexibilizados. Não se adicionou papel, provedor, opção ou validador semântico novo: a geração do conteúdo é instruída pelos procedimentos e a entrega de arquivos é exigida pela orquestração.

## Verificação

TDD com SQLite/orquestrador e subprocesso Python real simulando CLI, inteiramente fictício e sem HTTP/IA real. Antes do patch: cinco testes executados, onze falhas de assertions em 9,922 s (nove cenários de ausência/vazio/antigo e contratos de salto/prompt), um controle completo aprovado; teste do ajuste com mapa antigo também reproduziu falha em 1,285 s. Depois de corrigir o contrato, um teste adicional reproduziu bypass de retomada de plano salvo (ausência do registro não recompunha consolidação) em 0,832 s; correção mínima incluída.

Rodada final de `teste_registros_obrigatorios_ts08.py`: **oito testes aprovados em 12,779 s**, com nove subcenários de gates, ajuste sem mapa atualizado, sucesso completo com versão03, revisão independente/dispensa, prompt sem lacunas inventadas e duas retomadas sem versão04 indevida. Sessões consumidas permanecem com log em etapa erro. Os produtos do simulador são definidos independentemente do plano em teste para não validar apenas um espelho da implementação.

`teste_squad_claude.py`: **12 aprovados** na rodada anterior em 12,724 s; a rodada final após o último reparo de retomada também passou, conforme registro na fila. Apenas a fixture da análise já concluída foi adaptada para produzir os novos registros obrigatórios; demais simuladores usam as saídas dinâmicas reais. `teste_squad_contrato_ts06.py`: **3 aprovados em 1,941 s** (freshness, retorno/log preservado e regeneração válida). `teste_plantao_claude.py`: retorno zero, todos os checks incluindo CLI, fila, posse, cancelamento e botões; seus casos/configuração são temporários fictícios. Nenhuma suíte inteira nova é alegada por esta tarefa.

Python: `D:/CPJ - TRABALHO/.venv/Scripts/python.exe`, 3.12.14. Comando focado:

```powershell
& 'D:/CPJ - TRABALHO/.venv/Scripts/python.exe' 'D:/CPJ - TRABALHO/plugin/investigacao-cpj/app/testes/teste_registros_obrigatorios_ts08.py'
```

Diff dos trechos conferido e `git diff --check` retornou zero. Sem nova inferência, API real, alterações em P01/fontes/modelos/configurações reais, manifestos, PRD ou cache. O piloto permanece evidência da versão0.3.2, incluindo as intervenções Codex registradas; o integrador consolidará TS07/TS08 na atualização oficial CL08.
