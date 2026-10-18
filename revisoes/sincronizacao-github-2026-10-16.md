# Sincronização GitHub — 16/10/2026 (SY03)

Pedido: conferir arquivos novos, deixar dados sigilosos fora do GitHub e sincronizar o projeto. Repositório: `alandougs/central-cpj-postgres`; branch existente: `codex/os-markdown-relatorio-20261014`. Estado inicial após `git fetch origin`: três commits locais pendentes, nenhum commit remoto pendente e 28 arquivos novos. Nenhum arquivo rastreado tinha alteração de conteúdo antes desta tarefa.

## Triagem dos arquivos novos

Os 28 arquivos permanecem no computador, excluídos pelo `.gitignore`. Não foi necessário incorporar código novo: os arquivos restantes são operacionais, temporários ou duplicatas já arquivadas.

| Grupo | Quantidade | Decisão |
|---|---:|---|
| Scripts operacionais, pilotos, correções avulsas e `scratch/` | 17 | Somente locais; há referências a casos e identificadores em parte desses scripts. Nenhum conteúdo operacional reproduzido neste registro. |
| Configuração local de assinatura em `modelos/assinaturas/` | 1 | Pasta inteira excluída do versionamento, inclusive arquivos auxiliares JSON. |
| Base local `sync.ffs_db` | 1 | Excluídas bases `*.ffs_db`. |
| Marcador de teste de escrita | 1 | Pasta `teste-escrita-temporaria/` excluída. |
| Cópias de Docker/PostgreSQL | 8 | Comparação byte a byte confirmou igualdade com arquivos já rastreados em `legado/`; cópias mantidas locais. |

As oito duplicatas são `.dockerignore`, `Dockerfile`, `README-DOCKER.md`, `compose.yaml`, os dois arquivos de `deploy/`, `ferramentas/migrar-json-postgres.py` e `plugin/investigacao-cpj/app/db.py`. Correspondem a `legado/postgres-docker/`, `legado/ferramentas/migrar-json-postgres.py` e `legado/app/db.py`. Isso não reativa o experimento congelado nem muda a operação SQLite.

Além das exclusões acima, `.env.*` passa a ser ignorado, com exceção de `.env.example`. As exclusões anteriores para casos, configurações, usuários, consultas, referências, exportações, documentos e chaves foram preservadas.

## Histórico pendente

Foram examinadas as 41 revisões de arquivos introduzidas pelos três commits, incluindo versões intermediárias, para evitar que uma remoção posterior escondesse uma credencial em um commit anterior:

- `33c1402`: correlações documentadas, mapa offline e consolidação de entregas locais.
- `2386ac3`: cartografia IBGE e renderização do mapa.
- `3e3a4cc`: alerta e listagem de pendências de OCR indisponível.

Não foram encontrados caminhos proibidos de dados operacionais, chaves privadas, tokens dos provedores/GitHub/AWS, JWTs ou URLs com credencial literal nos padrões examinados. Identificadores pessoais/processuais detectados nas adições foram conferidos no contexto: fixtures sintéticas, exemplos de interface/documentação e reproduções isoladas, sem conteúdo de autos reais. A lista atual de arquivos rastreados também não contém caminhos de casos reais, configurações privadas, usuários, consultas, referências, exportações ou assinaturas.

Esta verificação é uma triagem por caminhos, padrões e contexto; não constitui certificação de todo o histórico antigo do repositório nem garantia absoluta contra qualquer formato de segredo. Não foi usado serviço externo para analisar arquivos locais. Somente os arquivos selecionados e os commits revisados integram o envio ao GitHub.

## Validação executada nesta tarefa

Usado o Python existente em `.venv/Scripts/python.exe`: o comando `python` do PATH aponta ao alias da Microsoft Store e não inicia o interpretador. Os testes abaixo usam dados fictícios e workspaces temporários.

| Verificação | Resultado |
|---|---|
| `teste_ocr_indisponivel_claude.py` | 10 testes aprovados; retorno 0. |
| `teste_correlacoes_mapa_etapa1.py` | 7 testes aprovados; retorno 0. |
| `teste_seguranca_codex.py` | 11 testes aprovados; retorno 0. |
| `git check-ignore --stdin` nos 28 arquivos da triagem | 28 ignorados, todos continuam existentes. |
| `git check-ignore --no-index --stdin` em exemplos sintéticos | 12 caminhos sensíveis protegidos e 6 caminhos de projeto permitidos, incluindo `.env.example`, o modelo fictício de caso e o código arquivado. |
| Histórico de envio | 3 commits, 41 revisões de arquivos, nenhum achado nos padrões de credenciais e caminhos proibidos examinados. |
| `git diff --check` das alterações desta tarefa | Retorno 0; apenas aviso de conversão LF/CRLF do Git para Windows. |

Logs dos testes: `%TEMP%/cpj-sy03-teste_ocr_indisponivel_claude.py.log`, `%TEMP%/cpj-sy03-teste_correlacoes_mapa_etapa1.py.log` e `%TEMP%/cpj-sy03-teste_seguranca_codex.py.log`.

A suíte geral não foi reexecutada. O registro anterior da OCR01 informa falhas fora da seleção acima; esta tarefa não as corrige nem declara o produto inteiro aprovado. Nenhum caso, original, relatório, configuração privada ou assinatura foi modificado. O envio usa a branch existente, sem force push, merge em `main`, implantação ou reinício da Central. A confirmação final exige comparar o hash de `HEAD` com a referência da mesma branch consultada diretamente no GitHub.
