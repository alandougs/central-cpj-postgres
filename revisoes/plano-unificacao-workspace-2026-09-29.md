# Registro de Unificação do Workspace Canônico, Base de Dados e Ordens de Serviço

> Data: 29/09/2026  
> Responsável: Arquiteto Backend / Dev Sênior (Gemini / Antigravity)  
> Solicitante: Alan Douglas Silva — Investigador de Polícia (Dono do Produto)

---

## 1. Contexto e Motivação

Historicamente, o sistema apresentava duplicidade entre o disco local `C:\CPJ - TRABALHO` e o SSD externo `E:\CPJ - TRABALHO`, além de uma pasta externa `E:\ORDENS DE SERVIÇO CPJ` contendo as Ordens de Serviço brutas e relatórios finais copiados com nomes heterogêneos (`OS 2534-26`, `OS 2534.26`, `OS -2650-26`, `os 2716.2026`, etc.).

Além disso:
1. O volume `E:` (SSD Externo de 2 TB) apresentou no Windows o estado de integridade **`Warning: Full Repair Needed`**, representando risco de ponto único de falha se mantido como unidade primária ativa.
2. A base de dados SQLite (`rag\cpj.sqlite`) carecia de índices na tabela relacional `pessoas`, gerando varreduras completas (`FULL TABLE SCAN`) a cada pesquisa de investigados, CPFs e mandados.
3. O painel de estatísticas (`/painel`) demorava mais de **31 segundos** para abrir, pois disparava o script `indexar.py` completo (reindexando RAG, FTS5, entidades e pessoas) em vez de apenas computar as métricas de produção.

---

## 2. Decisões Implementadas

### A. Workspace Canônico Único no Disco C:
- **Localização Canônica Única:** `C:\CPJ - TRABALHO`.
- Todos os arquivos mais recentes e casos foram consolidados em `C:\CPJ - TRABALHO`.
- O SSD externo (`E:`) passou a ser a **Unidade de Backup Espelho**, preservando a redundância física sem gerar divergência de código ou de relatórios ("Split-Brain").

### B. Pasta de Ordens de Serviço Centralizada e Padronizada
- Criada a pasta interna: `C:\CPJ - TRABALHO\ordens-de-servico\`.
- Todas as O.S. foram migradas e consolidadas para a nomenclatura canônica `OS-XXXX-2026`:
  - `OS-2534-2026`
  - `OS-2586-2026`
  - `OS-2623-2026`
  - `OS-2650-2026`
  - `OS-2668-2026`
  - `OS-2672-2026`
  - `OS-2702-2026`
  - `OS-2705-2026`
  - `OS-2716-2026`
- O script `ferramentas\fila-os.py` foi atualizado para apontar por padrão para `RAIZ / "ordens-de-servico"` com fallback dinâmico em `CPJ_PASTA_OS`.

### C. Otimização da Base de Dados SQLite (`cpj.sqlite`)
- Adicionados índices de alta performance na tabela `pessoas`:
  - `ix_pessoas_cpf` (em `cpf_d`)
  - `ix_pessoas_nome` (em `nome_n`)
  - `ix_pessoas_no` (em `no_id`)
  - `ix_pessoas_origem` (em `origem`)
  - `ix_pessoas_mandado` (em `tem_mandado`)
  - `ix_pessoas_cautelar` (em `tem_cautelar`)
- A indexação de pessoas, arestas e rótulos no `indexar.py` passou a ser atômica dentro de transação, sem `DROP TABLE` destrutivo que gerava indisponibilidade temporária da API.
- Adicionado `PRAGMA optimize;` no fechamento do banco.

### D. Aceleração Instantânea das Estatísticas e Painel (220x mais rápido)
- Adicionado o argumento `--so-base` ao `indexar.py`:
  - Atualiza apenas `producao\base.json` e `producao\base.csv` a partir dos `caso.json`.
  - Tempo de execução caiu de **31,5 segundos** para **0,14 segundos**!
- Em `plugin\investigacao-cpj\app\rotas\comum.py`, a função `atualizar_painel` foi ajustada para chamar `indexar.py --so-base` seguido de `gerar_painel.py` (tempo total: ~0,4s).
- Em `plugin\investigacao-cpj\app\rotas\sistema.py`, implementado o padrão **Stale-While-Revalidate**: se o arquivo `painel.html` já existe, ele é servido imediatamente para o navegador sem tela branca de espera.

### E. Isolamento de Código Legado / Congelado
- Arquivos de Docker e banco Postgres (`compose.yaml`, `Dockerfile`, `.dockerignore`, `README-DOCKER.md`, `deploy/`, `db.py`) foram movidos para `C:\CPJ - TRABALHO\legado\postgres-docker\`.

### F. Rotina de Backup Espelho
- Criados `ferramentas\backup-para-ssd.ps1` e o atalho `ferramentas\Backup para SSD.bat` para sincronizar o workspace de `C:\CPJ - TRABALHO` para `E:\CPJ - BACKUP` via Robocopy com 1 duplo clique.

---

## 3. Instruções para Outros Agentes (Claude, Codex, Gemini)

1. **Workspace:** Execute sempre em `C:\CPJ - TRABALHO`.
2. **Ordens de Serviço:** Localizam-se em `C:\CPJ - TRABALHO\ordens-de-servico\OS-XXXX-2026`.
3. **Casos Processados:** Localizam-se em `C:\CPJ - TRABALHO\casos\OS-XXXX-2026`.
4. **Fila de O.S.:** `python ferramentas\fila-os.py listar` (lê automaticamente a pasta interna).
5. **Atualização Rápida de Métricas:** `python plugin\investigacao-cpj\skills\base-cpj\scripts\indexar.py --so-base`.
6. **Reindexação Completa do RAG:** `python plugin\investigacao-cpj\skills\base-cpj\scripts\indexar.py --tudo`.
