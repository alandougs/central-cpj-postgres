# RI01 — Reindexação de manutenção sem baixa automática

Em 27/10/2026, Codex-RI01 implementou no candidato autorizado a opção `indexar.py --sem-baixa`. Motivo: reconstruir derivados de pesquisa após limpeza sem interpretar a presença de um arquivo FINAL como nova entrega operacional. Nenhuma reindexação do workspace original foi executada nesta tarefa.

A opção ignora exclusivamente o laço de detecção de relatórios FINAL/chamada de `caso.baixa_automatica`. A leitura dos casos, produção derivada e indexação textual/estruturada continuam normalmente. Sem a opção, o comportamento anterior permanece: um FINAL elegível pode dar baixa automática. A opção também pode ser combinada com `--so-base` ou `--tudo`. Não foi alterado `caso.py` nem o contrato de entrega.

## TDD e verificação

No teste `test_manutencao_sem_baixa_preserva_bytes_e_default_continua_baixa`, foi criado um workspace TEMP exclusivo, com um caso sintético em status `analisado`, transcrição Markdown por página e `RELATORIO-FINAL.md` sintético. Antes da implementação, o teste falhou porque `--sem-baixa` não era reconhecido (exit 2). Após a alteração:

- `indexar.py --tudo --sem-baixa` termina com exit 0 e preserva exatamente os bytes, SHA-256 e status do `caso.json`;
- a busca textual encontra o marcador na página 3 e `entidade` encontra o CPF candidato extraído em memória;
- `indexar.py --so-base --sem-baixa` também conserva os bytes do caso;
- `indexar.py --tudo`, na mesma fixture, continua identificando o FINAL e altera o status para `entregue`, origem `automatica-pasta`.

Comandos executados a partir do candidato, usando o runtime reparado original e `PYTHONDONTWRITEBYTECODE=1`:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
& 'F:/CPJ - TRABALHO/.venv/Scripts/python.exe' plugin/investigacao-cpj/app/testes/teste_rag_markdown_rg40.py
& 'F:/CPJ - TRABALHO/.venv/Scripts/python.exe' plugin/investigacao-cpj/app/testes/teste_gravacao_caso_as01.py
& 'F:/CPJ - TRABALHO/.venv/Scripts/python.exe' plugin/investigacao-cpj/app/testes/teste_travas_caso_as02.py
```

Resultados observados: **RG40/RI01 11 testes OK**, exit 0 (4,213 s); **AS01 5 testes OK**, exit 0; **AS02 5 testes OK**, exit 0. `git diff --check` do indexador sem erro. Todos os subprocessos de indexação desta verificação usam `CPJ_WORKSPACE` TEMP, nunca o workspace operacional. Nenhum serviço foi reiniciado; não houve API, rede, alteração de configuração, baixa real ou limpeza de casos reais.

## Congelamento e limite operacional

| Arquivo | SHA-256 |
|---|---|
| `plugin/investigacao-cpj/skills/base-cpj/scripts/indexar.py` | `2b38f9f718bdb9f3bd485dbf2a26d683ebd8a9e118803347fccc0cb24167078d` |
| `plugin/investigacao-cpj/app/testes/teste_rag_markdown_rg40.py` | `5135e73ab54b60c1747622b688ea6c5017a4691fdcb1cfcb456607f655ac0ac4` |

Estes hashes substituem os hashes anteriores desses dois arquivos registrados na revisão RG40. O coordenador fará integração, gate final, backup SQLite consistente e preservação da fonte autoritativa manual antes de eventual reconstrução operacional. Esta tarefa entrega a opção testada; não afirma que o backup ou a reconstrução real já ocorreram. A opção não substitui o backup nem altera outros comportamentos documentados do indexador.
