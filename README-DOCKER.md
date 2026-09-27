# Central CPJ em Docker

## Subir localmente

1. Copie `.env.example` para `.env` e troque `POSTGRES_PASSWORD`.
2. Execute `docker compose up --build`.
3. Abra <http://127.0.0.1:8765>.

Se a porta estiver ocupada, defina `CPJ_HOST_PORT=8766` no `.env` e abra <http://127.0.0.1:8766>.

O PostgreSQL usa o volume Docker `cpj-postgres`. Os documentos e arquivos operacionais ficam em `data/`, montado no container da aplicação; eles não entram na imagem nem no Git.

## Migrar casos existentes

Depois que a stack estiver ativa, sincronize os `caso.json` do workspace com o PostgreSQL:

```powershell
docker exec cpj-trabalho-app-1 python /app/ferramentas/migrar-json-postgres.py --workspace /workspace
```

O comando é idempotente, não apaga os arquivos locais e atualiza as tabelas `cases` e `documents` (Markdown de extração, análise e relatórios). Use `--dry-run` para listar os casos sem conectar ou gravar.

## Operação

```powershell
docker compose ps
docker compose logs -f app
docker compose down
```

Para remover também o banco local, use `docker compose down -v`. Isso apaga o volume PostgreSQL.
