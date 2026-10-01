# Arquivos Legados — Central CPJ

Este diretório contém códigos, scripts e módulos que não fazem mais parte do núcleo ativo da Central CPJ, preservados para histórico e referência técnica (não devem ser executados no fluxo padrão de produção).

## Estrutura do Legado

- `app/`:
  - `rotas_*.py` (`rotas_casos.py`, `rotas_consulta.py`, `rotas_relatorios.py`, `rotas_sistema.py`, `rotas_usuarios.py`): Módulos monolíticos de rotas anteriores à modularização da rodada A01 (o servidor ativo utiliza os blueprints modulares sob `plugin/investigacao-cpj/app/rotas/`).
  - `modify_tarefas.py`: Script pontual de desenvolvimento utilizado para patch do `tarefas.py`.
  - `db.py`: Adaptador PostgreSQL da fase experimental (Postgres congelado e desacoplado do core na RV05).
- `ferramentas/`:
  - `refatorar_servidor.py`: Script pontual de divisão do servidor executado na rodada A01.
  - `migrar-json-postgres.py`: Script de migração experimental SQLite/JSON -> Postgres.
- `postgres-docker/`:
  - Configuração Compose e scripts do contêiner PostgreSQL da fase experimental.
- Scripts avulsos de raiz:
  - `check_fin.py`: Verificação pontual com caminhos legados do drive `E:`.
  - `process_cases.py`: Script de extração manual em lote com caminhos fixos de `E:`.
  - `scratch_extrair.ps1` e `scratch_extrair_2699.ps1`: Scripts temporários de extração de casos específicos.
