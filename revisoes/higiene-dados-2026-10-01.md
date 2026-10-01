# Inventário e Proposta de Higiene dos Dados de Produção (RV13)

**Data da elaboração:** 01/10/2026  
**Agente responsável:** Gemini-1  
**Diretriz de governança (Regra 5 e Regra 8 do `AGENTS.md`):** Este documento constitui exclusivamente inventário e proposta técnica para deliberação do Investigador de Polícia Alan Douglas Silva. **Nenhum arquivo ou caso foi apagado, movido ou alterado** durante esta averiguação.

---

## 1. Resumo Executivo

A Central CPJ opera com o princípio de que o diretório `casos/` é a fonte canônica da verdade para o banco de dados analítico (`caso.json`), indexação RAG e painel de metas da unidade policial.

Na varredura realizada em 01/10/2026:
- Foram identificadas **20 pastas** de casos no workspace real (`casos/`), além de `_MODELO-CASO`.
- Destas 20 pastas, **13 são casos policiais legítimos** em tramitação ou entregues.
- **7 pastas são anômalas** (4 resíduos de execução de testes automatizados anteriores, 1 caso de teste/carga de benchmark, e 2 casos duplicados/com nomenclatura fora do padrão).
- No repositório de Ordens de Serviço (`ordens-de-servico/OS-2702-2026/trabalho`), foram identificados **4 perfis temporários de navegador Microsoft Edge** (`edge_qa_*_profile`) totalizando **40,91 MB e 1.004 arquivos** de cache e sessão, gerados durante testes de renderização/QA automatizado.

Essas anomalias distorcem a base consolidada (`producao/base.json`), o índice relacional SQLite e o painel de produção (`producao/painel.html`), inflando a contagem de casos abertos de 13 para 20.

---

## 2. Inventário Detalhado dos Casos em `casos/`

| Pasta do Caso | Status Atual | Processo Judicial / BO | Originais | Relatórios / Minutas | Situação / Diagnóstico |
|---|---|---|:---:|---|---|
| `_MODELO-CASO` | — | — | 0 | 0 | Template limpo canônico (correto). |
| `OS-101-2026` | `recebido` | Nenhum | 0 | 0 | **Resíduo de Teste:** Criado pelo `teste_esteira_completa.py` legado. |
| `OS-102-2026` | `recebido` | Nenhum | 0 | 0 | **Resíduo de Teste:** Criado pelo `teste_esteira_completa.py` legado. |
| `OS-103-2026` | `recebido` | Nenhum | 0 | 0 | **Resíduo de Teste:** Criado pelo `teste_esteira_completa.py` legado. |
| `OS-104-2026` | `recebido` | Nenhum | 0 | 0 | **Resíduo de Teste:** Criado pelo `teste_esteira_completa.py` legado. |
| `OS-2477-2026` | `minuta` | 1500382-94.2026.8.26.0425 | 1 | Minutas v01, v02, v03, DOCX v02 e v03 | Caso real legítimo. |
| `OS-2534-2026` | `minuta` | 1501864-08.2023.8.26.0482 | 1 | Minutas v02, v03, FINAL.md, DOCX v02 e v03 | Caso real legítimo. |
| `OS-2586-2026` | `entregue` | 1506487-24.2025.8.26.0425 | 2 | Minutas v01 a v03, FINAL.md, DOCX v01 a v03 | Caso real legítimo (entregue). |
| `OS-2623-2026` | `minuta` | 1508006-34.2025.8.26.0425 | 1 | Minutas v01 a v04, FINAL.md, DOCX v01 a v04 | Caso real legítimo. |
| `OS-2628-2026` | `minuta` | 1506548-79.2025.8.26.0425 | 1 | Minutas v01 a v03, FINAL.docx, DOCX v02 e v03 | Caso real legítimo. |
| `OS-2650` | `extraido` | 1508144-98.2025.8.26.0425 | 1 | 0 arquivos | **Duplicata fora do padrão:** Importado em 30/09 sem sufixo de ano. |
| `OS-2650-2026` | `entregue` | 1508144-98.2025.8.26.0425 | 3 | Minuta v01, anexo financeiro CSV, QA | Caso real legítimo completo (entregue). |
| `OS-2668-2026` | `entregue` | 1511200-08.2026.8.26.0425 | 2 | Minutas v01, FINAL.docx, FINAL.md, DOCX v01/v02 | Caso real legítimo (entregue). |
| `OS-2672-2026` | `minuta` | 1511795-07.2026.8.26.0425 | 1 | Minutas v01 a v03, FINAL.md, DOCX v01 a v03 | Caso real legítimo canônico. |
| `OS-os-2672-2026` | `devolvido` | 1511795-07.2026.8.26.0425 | 1 | Minuta v01, DOCX v01 | **Duplicata fora do padrão:** Importado em 28/09 com prefixo duplo `OS-os-`. |
| `OS-2699-2026` | `minuta` | 1511987-37.2026.8.26.0425 | 1 | Minutas v01 a v04, FINAL.docx, DOCX v02 a v04 | Caso real legítimo. |
| `OS-2702-2026` | `entregue` | 1512411-80.2026.8.26.0425 | 1 | FINAL.md, DOCX final | Caso real legítimo (entregue). |
| `OS-2705-2026` | `minuta` | 1502519-77.2023.8.26.0482 | 1 | Minutas v01 a v03, FINAL.docx, FINAL.md, DOCX v01 a v03 | Caso real legítimo. |
| `OS-2716-2026` | `minuta` | 1502477-28.2023.8.26.0482 | 2 | Minutas v01 a v05, DOCX v02 a v05 | Caso real legítimo. |
| `OS-2729-2026` | `minuta` | 1502396-79.2023.8.26.0482 | 2 | Minutas v01 a v04, FINAL.docx, FINAL.md, DOCX v01 a v04 | Caso real legítimo. |
| `OS-OS-TESTE` | `extraido` | Desconhecido (PDF de 415 págs) | 1 | 0 arquivos | **Resíduo de Teste:** Criado em 27/09 durante testes de orquestração. |

---

## 3. Análise Detalhada dos Casos Anômalos

### 3.1. Casos de Teste de Esteira: `OS-101-2026` a `OS-104-2026`
- **Causa-raiz:** O teste unitário `plugin/investigacao-cpj/app/testes/teste_esteira_completa.py` possuía caminhos absolutos fixos (`C:\CPJ - TRABALHO`) e criava 4 casos no workspace de produção durante sua execução. Na tarefa RV16, o teste foi corrigido para operar exclusivamente em `tempfile.TemporaryDirectory()`.
- **Conteúdo atual:** As pastas contêm apenas o arquivo `caso.json` com status `"recebido"`. Não há arquivos originais (`00-originais/` vazio), nem extrações (`01-extracao/` vazio), nem relatórios.
- **Impacto:** Entram na contagem de casos abertos no painel e na indexação geral como pendências fictícias.

### 3.2. Duplicata `OS-2650` × `OS-2650-2026`
- **Processo Judicial Comum:** `1508144-98.2025.8.26.0425`.
- **Histórico documental:**
  - `OS-2650-2026` foi criado em 28/09/2026 18:31. Possui o PDF principal `arquivo  OS 2650-26 - Moacyr.pdf` (243 págs, sha256 `7825...`), 15 relatórios de análise profunda (cronologia, fluxo financeiro, dados faltantes, empresas OSINT), anexo financeiro e status `entregue`.
  - `OS-2650` foi criado em 30/09/2026 13:58 através da Central (sem o ano no formulário). Contém o arquivo `1508144-98.2025.8.26.0425 _8.pdf` (237 págs, sha256 `3754...`), que foi extraído (`status=extraido`), mas não possui nenhuma análise nem relatório.
- **Diagnóstico:** Trata-se de uma segunda versão do mesmo processo, nomeada sem o ano (`-2026`). O arquivo `_8.pdf` representa a mesma peça processual com numeração de download ligeiramente diferente. A pasta `OS-2650` é redundante e distorce a produção como um caso não concluído.

### 3.3. Duplicata `OS-os-2672-2026` × `OS-2672-2026`
- **Processo Judicial Comum:** `1511795-07.2026.8.26.0425`.
- **Boletim de Ocorrência:** `LF6589-1/2026`.
- **Arquivo PDF original idêntico:** Ambos possuem o mesmo arquivo de 83 páginas com o mesmo hash SHA-256 (`9293603cd0b26ce10bdcab2cff2f2c2d013cde8f7f3f4d5db2c464ef33b339c3`).
- **Histórico documental:**
  - `OS-os-2672-2026` foi criado em 28/09/2026 15:17 com o prefixo repetido e em minúsculas (`OS-os-`). Parou na versão 01 e recebeu status `devolvido`.
  - `OS-2672-2026` foi criado em 29/09/2026 00:47 com a nomenclatura canônica correta (`OS-2672-2026`). Tramitou normalmente, recebeu as minutas v01, v02, v03 e possui o relatório `RELATORIO-OS-2672-2026-FINAL.md`.
- **Diagnóstico:** A pasta `OS-os-2672-2026` é uma pasta obsoleta de uma tentativa preliminar. A pasta `OS-2672-2026` é a oficial completa.

### 3.4. Resíduo de Teste `OS-OS-TESTE`
- **Criação:** 27/09/2026 08:21:47 (durante a primeira calibração do squad multi-agente).
- **Conteúdo:** Contém o arquivo `1501864-08.2023.8.26.0482.pdf` (415 páginas, sha256 `8121...`), extraído por texto nativo.
- **Observação relevante:** O processo `1501864-08.2023.8.26.0482` é o mesmo processo do caso legítimo `OS-2534-2026` (cuja O.S. é 2534/2026).
- **Diagnóstico:** Foi criado como teste de extração em lote para medir o tempo de processamento de um PDF extenso (415 págs). Permaneceu esquecido em `casos/` com o nome `OS-OS-TESTE`.

---

## 4. Inventário do Diretório `ordens-de-servico/OS-2702-2026/trabalho`

O diretório `ordens-de-servico/OS-2702-2026/trabalho` possui atualmente **108,43 MB** distribuídos em **1.458 arquivos**.

Deste total, **40,91 MB e 1.004 arquivos** pertencem exclusivamente a perfis de sessão automatizada do navegador Microsoft Edge:
- `edge_qa_profile`: 11,91 MB (263 arquivos)
- `edge_qa_revisao_profile`: 11,40 MB (252 arquivos)
- `edge_qa_final_profile`: 11,11 MB (242 arquivos)
- `edge_qa_entrega_profile`: 6,49 MB (247 arquivos)

**Natureza dos arquivos:** Cache temporário do Chromium (`GPUCache`, `Code Cache`, `Network Persistent State`, `Local State`, `Cookies`). Foram criados quando um script de QA visual abriu instâncias headless/automáticas do Edge para inspecionar a interface da Central e a visualização do relatório Word/PDF.

Estes perfis não contêm peças investigativas, relatórios ou informações processuais originais que não existam no próprio caso entregue (`casos/OS-2702-2026`).

---

## 5. Propostas de Ação para Deliberação do Investigador

Para cada item, apresentamos a proposta técnica recomendada, a justificativa e os comandos equivalentes para execução caso o usuário aprove:

### Proposta 1: Limpeza dos Casos Fantasmas de Teste (`OS-101-2026` a `OS-104-2026`)
- **Ação:** Mover as 4 pastas para `legado/testes-antigos/` (ou exclusão direta, visto que não contêm dados).
- **Benefício:** Elimina imediatamente 4 casos fantasmas da contagem de produção e das consultas da Central.

### Proposta 2: Arquivamento da Pasta Duplicada `OS-os-2672-2026`
- **Ação:** Mover `casos/OS-os-2672-2026` para `legado/casos-duplicados/OS-os-2672-2026`.
- **Benefício:** O processo `1511795-07.2026.8.26.0425` passa a constar exclusivamente sob o caso oficial `OS-2672-2026`, eliminando a duplicidade e a confusão no cruzamento de dados.

### Proposta 3: Unificação de `OS-2650` em `OS-2650-2026`
- **Ação:**
  1. Copiar o arquivo `1508144-98.2025.8.26.0425 _8.pdf` de `OS-2650/00-originais/` para `casos/OS-2650-2026/00-originais/` (garantindo que nenhum original seja descartado).
  2. Mover `casos/OS-2650` para `legado/casos-duplicados/OS-2650`.
- **Benefício:** Todos os originais do processo `1508144-98.2025.8.26.0425` ficam reunidos no caso canônico `OS-2650-2026`, mantendo a integridade histórica e zerando a pendência no painel.

### Proposta 4: Destinação de `OS-OS-TESTE`
- **Opção A (Recomendada):** Mover `casos/OS-OS-TESTE` para `legado/testes-antigos/OS-OS-TESTE`, uma vez que os autos originais (`1501864-08.2023.8.26.0482.pdf`) já estão preservados no caso canônico `OS-2534-2026`.
- **Opção B:** Preservar a extração em pasta de benchmark se o operador desejar utilizá-la para testes futuros de desempenho de OCR.

### Proposta 5: Purga dos Perfis de QA do Edge em `OS-2702-2026/trabalho`
- **Ação:** Apagar os 4 diretórios `edge_qa_*_profile` dentro de `ordens-de-servico/OS-2702-2026/trabalho`.
- **Benefício:** Liberação de ~41 MB de espaço e redução de mais de 1.000 arquivos temporários inócuos no backup e no sistema de arquivos, sem nenhum impacto sobre os relatórios oficiais gerados.

### Proposta 6: Reindexação Geral da Base
- **Ação:** Após a execução das decisões pelo usuário, rodar:
  ```powershell
  python plugin/investigacao-cpj/skills/base-cpj/scripts/indexar.py
  python plugin/investigacao-cpj/skills/base-cpj/scripts/gerar_painel.py
  ```
- **Benefício:** Atualização atômica do SQLite, do RAG e do painel, refletindo o volume real e verídico de 13 inquéritos policiais em tramitação/entregues.

---

## 6. Procedimento de Aplicação (Aguardando Decisão do Usuário)

Quando o operador deliberar sobre as propostas acima, basta indicar quais itens devem ser aplicados (ex.: "Aprovo propostas 1 a 6" ou selecionar pontualmente). Nenhuma alteração foi realizada até a presente data.
