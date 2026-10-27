# RG40 — RAG e candidatos estruturados a partir do Markdown

Em 27/10/2026, Codex-RG40 verificou o candidato `F:/CPJ-BACKUPS/sync-github-20261027-023944/candidato`. A tarefa inicial verificou a busca FTS sem CSV/JSON documental. Ao comprovar a perda de entidades estruturadas, o coordenador reabriu e ampliou formalmente a RG40 para `indexar.py` e `entidades.py`, visando preservar as consultas existentes sem arquivos intermediários novos. A reserva e a conclusão são registradas na fila original `F:/CPJ - TRABALHO`.

## Alteração

`entidades.py` expõe `iter_candidatos(texto)`, função geradora sem leitura/escrita de arquivos, reutilizando `PADROES`. O comando legado continua gerando o CSV com o mesmo cabeçalho quando chamado explicitamente; sua execução ficou sob `main`/`__main__`. Importar o módulo não gera arquivos. Candidatos têm página, linha física da transcrição e status `pendente de conferência`. Comentários HTML não são fontes; marcadores explícitos `?`, caractere de substituição e anotações de incerteza posteriores ao token impedem aproveitar fragmentos como identificadores completos. Correspondência telefônica sobreposta a CPF/CNPJ não fabrica outro tipo pela mesma sequência. Os padrões são heurísticos, não validam identidade, autoria ou dígito verificador.

`indexar.py` mantém a leitura de `entidades.csv` existente. Por documento sem esse legado, lê `transcricao.md`, consome os candidatos em memória e insere no mesmo SQLite `entidades`/grafo já utilizado. Não chama a CLI geradora de CSV nem grava CSV/JSON de extração. A origem do grafo usa o contrato existente `astra-evidencia/1`, com arquivo Markdown, documento, página, linha, trecho, hash derivado, tipo `extracao_candidata` e status pendente. A reconstrução recupera os candidatos do Markdown; vínculos manuais continuam usando sua fonte autoritativa. Contas/fluxo financeiro legados e normalizadores existentes foram preservados. Não foi criada interpretação automática de contas, nomes ou movimentações no texto.

## Evidência executada

Todos os testes usam dados sintéticos em TEMP. `CPJ_WORKSPACE` dos subprocessos aponta para o workspace temporário, com `PYTHONDONTWRITEBYTECODE=1`. Sem API, rede, servidor ativo ou índice operacional. As fixtures Markdown representam extrações: não geram PDF nem executam OCR. A CLI CSV legada é exercitada somente em outro TEMP explícito para comprovar compatibilidade.

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
& 'F:/CPJ - TRABALHO/.venv/Scripts/python.exe' plugin/investigacao-cpj/app/testes/teste_rag_markdown_rg40.py
```

TDD observado: com os testes novos e antes do fallback, **2 falhas esperadas** por ausência de candidato no grafo e de CPF na tabela de entidades. Após implementação e ampliação dos testes: **10 testes OK, exit 0**, 3,377 s.

| Verificação RG40 | Evidência |
|---|---|
| UTF-8 e origem textual | Texto acentuado, caso, caminho do documento, página 1/folha 41; outro documento na mesma página 1 mantém caminho distinto. |
| Página e folha | Página 2 corresponde à folha 58; remissão no corpo a Fls. 777 não inventa folha física. |
| Identificadores | Dígitos completos compartilhados são acháveis nos dois casos; dígito alterado não; número com `?` não é completado. E-mail e CPF pontuado são localizáveis. |
| Separação | Busca geral rotula referência e casos; `--caso` e `--tipo transcricao` excluem outras fontes. |
| Estruturado sem CSV | `entidade` retorna duas ocorrências de CPF, com documentos/páginas; `cruzar` localiza o segundo caso. Grafo preserva MD/página/linha e status candidato. CPF pontuado é consultável por dígitos limpos em `entidade`. |
| Compatibilidade | CSV presente prevalece só no próprio documento; outros documentos continuam pelo Markdown. CLI antiga conserva cabeçalho e candidatos. |
| Regeneração | Remover apenas o SQLite sintético e reindexar conserva entidades; execução incremental mantém referências FTS. |
| Ausência de intermediários | Após o fluxo principal, casos sintéticos têm somente `caso.json` como JSON; não há CSV/tabelas/`dados_extraidos.json`. |

Regressões dirigidas, cada arquivo em processo isolado:

| Suíte | Resultado observado |
|---|---|
| `teste_grafo_api_gf01.py` | 11 OK, exit 0 |
| `teste_correlacoes_mapa_etapa1.py` | 7 OK, exit 0 |
| `teste_fluxograma_identidade_rv17.py` | 19 OK, exit 0 |
| `teste_integridade_vinculos_rp32.py` | 12 executados, 10 OK e 2 falhas, exit 1 |

As duas falhas RP32 também ocorreram no controle em TEMP sem o fallback/import RG40, com os mesmos 12 testes/2 falhas/0 erros. O controle copiou somente scripts genéricos e removeu apenas o bloco novo de indexação Markdown, mantendo o mesmo código de API do candidato. São: `test_cadastro_manual_rejeita_identificador_incerto_sem_normalizar` (API retorna 200, esperado 400) e `test_exclusao_manual_e_duravel_e_preserva_documental_identica` (payload antigo de remoção retorna 400, esperado 200). Não foram atribuídas à RG40 nem corrigidas fora do escopo; coordenador avisado. Os demais testes RP32 confirmam separação de tipos, contas sem banco, preservação/reconstrução de manuais e rejeição de identificadores incertos no grafo documental.

## Limites

A extração em Markdown por página alimenta a busca textual SQLite FTS5 e agora também recompõe os candidatos estruturados já suportados pelos padrões. Isso não mede qualidade global, OCR, embeddings ou busca semântica. O texto precisa conservar `## Página N`; origem e qualidade da transcrição condicionam os resultados.

A busca textual não normaliza automaticamente CPF pontuado para dígitos limpos: na fixture `[CPF SINTÉTICO]` é encontrado por FTS, `[CPF SINTÉTICO]` não. Isso é distinto de `entidade`, que normaliza o candidato estruturado e o encontra pelos dígitos limpos. Consultas FTS com vários termos podem retornar parte deles com aviso explícito; o teste exige esse aviso. Busca geral reúne tipos rotulados e depende de filtro para restringir casos e referências.

Identificadores são candidatos pendentes de conferência na fonte. Não foram criadas novas entidades por inferência, nomes/pessoas por dedução ou conexões financeiras automáticas. A ausência de correspondência não prova ausência do dado no documento. A indexação continua gerando seus próprios derivados locais de produção/SQLite essenciais: a ausência de CSV/JSON documental não significa ausência de todo arquivo técnico.

## Fontes congeladas para integração final

| Arquivo | SHA-256 |
|---|---|
| `teste_rag_markdown_rg40.py` | `c63389344f2c413a6e47ba8047286fe95d8069055e04b1812d1125ebee65afcd` |
| `indexar.py` | `1f3769fdb1466c3d53c10e11d8e82d30d99149504d08120780d85d199b7d729e` |
| `entidades.py` | `d6ed13602d1a9eb6d5b58150fab5331c1bdd11cd6de3af5e6e916f0a56665d27` |

`rag.py` não foi alterado por esta tarefa. Nenhuma suíte completa concorrente, reindexação operacional ou instalação foi executada. O coordenador integra/revisa e executa a verificação final aplicável.
