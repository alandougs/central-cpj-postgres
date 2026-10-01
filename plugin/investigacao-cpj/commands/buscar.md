---
description: Pesquisa na base RAG local (transcrições, análises, relatórios, acervo) ou cruza CPF/chave Pix/conta/telefone entre casos
argument-hint: <texto ou valor> [--caso ID] [--tipo relatorio|transcricao|analise]
---

Pesquise na base: $ARGUMENTS

Scripts: `plugin\investigacao-cpj\skills\base-cpj\scripts\`.
- Se o argumento parecer identificador (CPF, CNPJ, telefone, placa, chave Pix, conta) → `rag.py entidade "<valor>"`.
- Se for um ID de caso precedido de "cruzar" → `rag.py cruzar <ID>`.
- Se for pessoa (nome, mãe, pai, CPF, RG, telefone, CNPJ/empresa, endereço) → `rag.py pessoas --nome "..." [--mae ...] [--cpf ...]` (qualificações de `02-analise\pessoas.csv` dos casos + bases de consulta importadas). Na Central: *Pesquisa* (também BO, processo, placa, mandado e cautelar, e *vínculos*).
- Caso contrário → `rag.py buscar "<texto>" [filtros] -n 10`.

Resultado vindo de **base de consulta** (`consulta\`, ex.: Muralha Paulista) é apoio à pesquisa do investigador: informe a base de origem e a situação como consta (ex.: mandado "confirmado", "histórico", "negado"), mas nunca o use como fonte de relatório. Vínculo por nome é candidato (homônimos possíveis); por CPF/telefone/conta, indício a conferir.

Abra os trechos mais relevantes no arquivo de origem para confirmar antes de responder. Responda citando caso, arquivo e página/fls. Conexões entre casos são indícios a verificar, não conclusões.