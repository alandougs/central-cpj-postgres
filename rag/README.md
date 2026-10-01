# Base RAG local

- Índice: `cpj.sqlite` (SQLite + FTS5, sem dependências, 100% local). Regenerável: `indexar.py --tudo`.
- Tabelas: `docs` (arquivo, caso, tipo, sha), `trechos` (caso, tipo, página, fls., seção, texto, modalidade, natureza, embedding), `trechos_fts` (busca textual sem acento), `entidades` (CPF, CNPJ, telefone, placa, e-mail, chave Pix, conta, titular — normalizados para cruzamento entre casos).
- Tipos de trecho: `transcricao` (1 por página), `analise`, `minuta`, `revisao`, `relatorio` (FINAL aprovado), `calibracao`, `acervo`.
- Consulta: `rag.py buscar | entidade | cruzar | exemplos | stats` (skill `base-cpj`, comando `/buscar`).

## Convenções que mantêm a base boa

1. Transcrições sempre com `## Página N` (página do PDF) e fls. quando legíveis.
2. Arquivos de análise e relatório com cabeçalho YAML (`caso`, `versao`, `tipo`).
3. Relatório aprovado sempre salvo como `RELATORIO-<ID>-FINAL.md` (via `/entregar`).
4. `caso.json` completo (modalidade, natureza, datas) — é o filtro de metadados do RAG e da estatística.

## Próximas fases (quando quiser)

- **Busca semântica local:** gerar embeddings com modelo local (ex.: Ollama + modelo de embeddings multilíngue) na coluna `trechos.embedding` e combinar com o FTS (busca híbrida).
- **Interface própria:** a interface de pesquisa pode ler diretamente `cpj.sqlite` (qualquer linguagem com SQLite). Manter local; não expor em rede sem controle de acesso.
