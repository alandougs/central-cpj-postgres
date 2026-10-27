# Base RAG local

- Índice: `cpj.sqlite` (SQLite + FTS5, sem dependências, 100% local). Regenerável: `indexar.py --tudo`.
- Tabelas: `docs` (arquivo, caso, tipo, sha), `trechos` (caso, tipo, página, fls., seção, texto, modalidade, natureza, embedding), `trechos_fts` (busca textual sem acento), `entidades` (CPF, CNPJ, telefone, placa, e-mail, chave Pix, conta, titular — normalizados para cruzamento entre casos).
- Tipos de trecho: `transcricao` (1 por página), `analise`, `minuta`, `revisao`, `relatorio` (FINAL aprovado), `calibracao`, `acervo`.
- Consulta: `rag.py buscar | entidade | cruzar | exemplos | stats` (skill `base-cpj`, comando `/buscar`). `buscar` é híbrida quando a maior parte dos trechos tem vetor — veja abaixo.

## Convenções que mantêm a base boa

1. Transcrições sempre com `## Página N` (página do PDF) e fls. quando legíveis.
2. Arquivos de análise e relatório com cabeçalho YAML (`caso`, `versao`, `tipo`).
3. Relatório aprovado sempre salvo como `RELATORIO-<ID>-FINAL.md` (via `/entregar`).
4. `caso.json` completo (modalidade, natureza, datas) — é o filtro de metadados do RAG e da estatística.

## Busca híbrida (textual + semântica)

- **Vetores:** `indexar.py --embeddings` preenche `trechos.embedding` nos trechos que ainda não têm (`--reembeddings` regera tudo, para troca de modelo). Grava e comita por lote, então a geração é retomável.
- **Modelo:** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384 dimensões) rodando em ONNX via `fastembed`, baixado uma única vez para `rag/modelos/`. Depois disso não há rede: nenhum conteúdo de caso sai do computador. Dependência opcional — sem ela a busca textual continua inteira.
- **Granularidade:** um vetor por trecho, igual ao FTS. Como o modelo trunca em 128 tokens e um trecho de transcrição é uma página inteira, o texto é dividido em janelas de 96 palavras e o vetor do trecho é a média normalizada das janelas — a página toda conta, não só o começo dela. **Limite:** o corte é em 24 janelas (cerca de 2.300 palavras); o que passa disso não entra no vetor, e quem cobre o trecho inteiro por palavra é o FTS.
- **Consulta:** `rag.py buscar --modo auto|lexical|semantico|hibrido`. `auto` (padrão) usa a híbrida quando pelo menos 90% dos trechos têm vetor (`COBERTURA_MINIMA`) e cai para a textual abaixo disso — com cobertura parcial, o subconjunto já vetorizado passaria à frente de trechos que contêm os termos; pedir `hibrido`/`semantico` nessa base funciona, com aviso da porcentagem. `--fts` (expressão FTS crua) impõe a busca textual em qualquer `--modo`, avisando que o modo pedido foi ignorado. A parte semântica descarta candidatos com cosseno abaixo de 0,30 (`SIMILARIDADE_MINIMA`; medido: relevantes entre 0,56 e 0,87, irrelevantes entre -0,11 e 0,17). A fusão é por posto recíproco (RRF), então as duas listas pesam sem precisar calibrar escala de nota.
- **Matriz em memória:** os vetores são carregados uma vez por processo e reusados entre consultas, com invalidação por mudança no arquivo do banco — a Pesquisa da Central caiu de 1307 ms para 94 ms por consulta. Consulta semântica **com** filtro de caso/tipo/modalidade continua pelo SQL e não ganha o cache (cerca de 1 s), que é o que garante que o filtro não sai do banco.
- **Leitura do resultado:** quando nenhum trecho contém os termos, o resultado vem por proximidade de sentido e a busca avisa. Trecho achado só por semântica não é prova de nada: confira o texto nos autos antes de usar.
- `rag.py stats` mostra quantos trechos já têm vetor.

## Próximas fases (quando quiser)

- **Interface própria:** a interface de pesquisa pode ler diretamente `cpj.sqlite` (qualquer linguagem com SQLite). Manter local; não expor em rede sem controle de acesso.
