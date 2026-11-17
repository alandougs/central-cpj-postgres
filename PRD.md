# PRD — Central CPJ e plugin `investigacao-cpj`

> Documento de continuidade. Qualquer agente (Claude Code, Codex, Gemini, modelo local) deve ler **este arquivo + `AGENTS.md`** antes de alterar o sistema. Atualize a seção **9 (Estado atual)** e o **Registro de mudanças** a cada entrega.
> Dono do produto: Alan Douglas Silva — Investigador de Polícia, Central de Polícia Judiciária (CPJ), Seccional de Presidente Prudente, DEINTER 8, PCSP.
> Última atualização: 2026-11-16 (reorganização MQ04: registros históricos e Registro de mudanças movidos para `docs/historico/PRD-historico-2026.md`; estado vigente da seção 9 mantido).

---

## 1. Visão

> **FASE ATUAL, ratificada pelo investigador em 28/09/2026: operação solo e foco no core.** Usuário único: Alan Douglas Silva, Investigador de Polícia, no próprio computador. Core: **PDF dos autos → OCR local → Markdown por página + checkpoint essencial consolidado → análise investigativa (caminho do dinheiro/Pix, art. 171) → relatório DOCX CPJ 2026**. Meta: uso real em 29/09/2026, 09:00 (tarefas `E` em `TAREFAS-COMPARTILHADAS.md`).
> Modo solo implementado (`config\solo.json`), sem senha no próprio PC. **Congelados**, com o código mantido e sem melhorias: perfis delegado/escrivão, rede local, PostgreSQL/Docker (PG01) e novos papéis de IA. O texto abaixo sobre perfis e fluxo delegado/escrivão descreve a capacidade existente, não a prioridade.

Sistema local, simples e seguro para a **produção de relatórios de investigação em inquéritos de fraude e estelionato**: a O.S. chega (cadastrada pelo delegado/escrivão ou pelo investigador) com o PDF do IP → o sistema extrai **Markdown por página** (OCR em português quando necessário) → **agentes de IA** analisam somente o material do caso e redigem a **minuta no modelo oficial** (DOCX com timbre e assinatura) → o investigador revisa/edita, define a versão FINAL e a **produção** é contabilizada (dia/mês/ano, prazos, KPIs). Tudo vira base pesquisável (RAG local), com calibração contínua a partir das correções do investigador e de relatórios de referência.

Volume de referência: **30–50 relatórios/mês**, IPs de **100–300 páginas**.

## 2. Usuários e perfis

| Perfil | Pode |
|---|---|
| **Admin** | Tudo, inclusive usuários, auditoria e rede |
| **Investigador** | O.S., casos (completo), processamento, IA, minuta/DOCX/PDF/FINAL, baixa, pesquisa, estatísticas, exportar/importar, bases de consulta, referências |
| **Delegado** | Cadastrar O.S. (com prazo, determinação), enviar arquivos, ver lista/status/prazos de todas as O.S., baixar relatório FINAL e originais, pesquisa, estatísticas |
| **Escrivão** | Cadastrar O.S., enviar arquivos, ver lista/status/prazos, baixar relatório FINAL e originais |

Permissões codificadas em `plugin/investigacao-cpj/app/auth.py` (`PERMISSOES`): `os, casos, trabalho, ia, pesquisa, estatisticas, dados, relatorio_final, usuarios, rede`.

**Uso atual:** uma conta, `alandougs` (admin, Alan Douglas Silva). **Modo solo:** `config\solo.json` com `{"ativo": true}` faz a Central, acessada em `127.0.0.1`/`localhost`, entrar direto como o único admin ativo (`auth.usuario_solo()`, `rotas/comum.usuario()`). Deixa de valer, e o login volta, quando o acesso vem da rede, com outro Host ou com mais de um admin ativo. O anti-CSRF (`X-CPJ: 1`) continua. Com `ativo: false` ou sem o arquivo, o login volta. Teste: `app/testes/teste_solo_claude.py`.

## 3. Premissas e regras inegociáveis

1. **Fonte do relatório = somente o IP/peças do próprio caso.** Bases de consulta (Muralha Paulista etc., pasta `consulta\`) e relatórios de referência (pasta `referencias\`) **nunca** são fonte de fatos; referências servem apenas como exemplo de estrutura/estilo.
2. PDF ≤ 100 págs. pode ser lido diretamente por IA em consulta pontual; novos PDFs geram **somente Markdown como extração documental**, com rastreabilidade por página e checkpoint essencial consolidado. Não gerar CSV/JSON documentais derivados; preservar arquivos legados necessários conforme a regra 21 de `AGENTS.md`.
3. Separar fato documentado × relato × indício × inferência × lacuna; citar `(pág. N; fls. X)`; nunca completar CPF/conta/chave Pix/valor por dedução; nunca atribuir autoria sem base.
4. **Sigilo:** processamento local por padrão; dados de casos nunca vão ao GitHub. Uso de API exige ativação explícita do provedor pelo responsável e aceite positivo do pedido, com usuário, data e destinos persistidos; pedidos antigos sem esse contrato ficam bloqueados antes do envio. Agentes CLI automáticos não recebem ferramentas WebFetch/WebSearch nem conectores MCP. A autorização de sessões Codex para revisão não autoriza outros serviços. Prevalecem as regras 6 e 18 de `AGENTS.md`.
5. Originais (`00-originais`) somente leitura; hash SHA-256 registrado.
6. Toda saída de IA é **minuta**: decisão e assinatura são humanas.
7. Relatório segue o **modelo DOCX CPJ 2026** (`modelos\`), com cabeçalho (O.S., Referência, Natureza, Investigado(s), Vítima(s), Local, Data dos Fatos) e seções RESUMO DOS FATOS / DILIGÊNCIAS REALIZADAS / CONCLUSÃO; conclusão preferencialmente **sem sugestões de providências** (discricionariedade do delegado).
8. Simplicidade: Windows + Python + arquivos; sem banco de dados servidor; tudo regenerável a partir de `caso.json` + arquivos.
9. **Modo solo e foco no core (28/09/2026):** uso diário do investigador no próprio computador. Não adicionar Docker, banco servidor, framework de frontend nem tela que não sirva ao core. A premissa 8 prevalece sobre a PG01: PostgreSQL/Docker ficam como experimento congelado, fora do caminho de execução (`db.py` só é usado por `ferramentas\migrar-json-postgres.py`; `psycopg` é opcional para a Central). Diretriz só conta como entregue depois de implementada e testada.

## 4. Requisitos funcionais (Central CPJ — `http://127.0.0.1:8765`)

| # | Requisito | Estado |
|---|---|---|
| RF01 | Login com senha (PBKDF2), sessão 12 h, bloqueio após 5 falhas, configuração inicial do admin só no próprio PC; **modo solo** sem senha no próprio PC (`config\solo.json`) | implementado; interface do modo solo na E02 |
| RF02 | Perfis admin/investigador/delegado/escrivão com permissões por rota | implementado (backend) |
| RF03 | Auditoria de ações em `config\auditoria.log`, cadeia HMAC, âncora protegida por conta e trava interprocesso; diagnóstico de integridade | implementado na fonte e testado com dados fictícios (SEC22/SEC24); legado permanece identificado |
| RF04 | **Nova O.S.**: nº O.S., BO, IP, processo, natureza, requisitante, prazo, prioridade, determinação + upload PDF/MD/CSV (progresso real de envio) | implementado (backend) |
| RF05 | Fila de processamento: texto/OCR (progresso por página) → Markdown e O.S. → checkpoint essencial único → indexação | implementado |
| RF06 | **Início**: O.S. novas não vistas, prazos vencidos/hoje/≤3 dias, sem prazo, andamento por etapa, minhas O.S., produção do dia/mês | implementado (backend) |
| RF07 | **Casos**: lista ordenada por urgência de prazo; busca por O.S./BO/IP/processo/partes/modalidade; ficha com edição, documentos, processamento, arquivos, conexões | implementado |
| RF08 | **Botões de IA** na ficha: Analisar, Gerar relatório, Análise+relatório, Revisar — fila persistente com agente selecionável, CLI ou API configurada, progresso e cancelamento | implementado e testado com executores simulados; Claude continua executor padrão e requer login; piloto CLI real P01 concluído, com correção e complementação Codex medidas |
| RF09 | **Editor leve da minuta** (campos do cabeçalho + 3 seções) → nova versão + DOCX no modelo; PDF (LibreOffice, se instalado); Abrir no Word (só no PC da Central); **Definir FINAL** (gera FINAL.md e dá baixa) | implementado (backend) |
| RF10 | **Baixa na produção** por 3 vias com origem registrada: arquivo `*FINAL*` na pasta (automática), botão, agente | implementado |
| RF11 | **Pesquisa relacional** de pessoas: nome, mãe, pai, CPF, RG, telefone, CNPJ/empresa, endereço (combináveis, sem acento, por palavras) em qualificações extraídas dos autos (`02-analise\pessoas.csv`) e bases de consulta; + ocorrências nos autos | implementado (backend) |
| RF12 | **Pesquisa textual (RAG)** em transcrições, análises, relatórios, referências, acervo; cruzamento de CPF/Pix/conta/telefone entre casos | implementado |
| RF13 | **Bases de consulta** (Muralha Paulista e similares): importar .xlsx/.xls/.csv/.docx com mapeamento automático de colunas; listar/remover | implementado (backend) |
| RF14 | **Relatórios de referência** por autor, modalidade e peso (1–5) para calibração/exemplos; importar DOCX/PDF/MD; editar peso; remover | implementado (backend) |
| RF15 | **Exportar dados**: pacote `.cpjenc` com senha obrigatória, Scrypt e AES-256-GCM por blocos; ZIP interno com manifesto SHA-256; modo completo ou só dados, opcional modelo DOCX; planilha CSV separada | implementado na fonte e testado (SEC23/SEC24); ZIPs antigos são identificados como sem criptografia |
| RF16 | **Importar pacote**: autentica `.cpjenc`, valida manifesto/escopo/junções, acrescenta casos novos e nunca sobrescreve; ZIP legado exige aceite explícito | implementado na fonte e testado (SEC23/SEC24) |
| RF17 | **Estatísticas/KPIs**: entregues dia/mês/ano × meta, páginas, prazo mediano, em aberto por etapa, modalidades, autoria indicada, valor rastreado; relatório de O.S. cumpridas por intervalo | implementado, inclusive relatório completo por data de cumprimento, O.S., data do relatório, natureza, policial responsável, total e resumo por natureza; impressão/PDF e CSV |
| RF18 | **Rede local**: compartilhamento somente com HTTPS; WSGI Cheroot com TLS direto, Host/Origin conferidos, certificado autoassinado; padrão local | implementado na fonte e testado com HTTP/HTTPS/Edge sintéticos (SEC21); não muda rede/firewall em uso |
| RF19 | Usuários (admin): criar/editar/desativar/remover, trocar a própria senha, ver auditoria | implementado (backend) |
| RF20 | Interface única, responsiva, claro/escuro, progresso em upload, OCR, exportação, importação e IA | implementada; integração HTTP e Edge F03 aprovados; AI03 verificada em 12 cenários Chrome, nos dois temas |
| RF21 | **Operação Full-Time 24/7**: supervisor local, reinício em falha e utilitários de controle | testes com Startup fictícia aprovados (RV01/AG02); instalação e boot reais não certificados |
| RF22 | **Esteira Completa**: extração, derivados, análise documental/financeira, redação, revisão e DOCX, com fila, checkpoints e progresso | implementada (EC01/CL02), 12 testes da squad e 19 de orçamento aprovados; análise por blocos e tarefas paralelas internas; piloto IA real P01 pendente |
| RF23 | **Fluxograma do dinheiro**: PNG local e inserção no DOCX; identidade de nós e indicação de posição calculada | RV02/RV17 e TS04 testadas; banco participa da identidade, contas ambíguas permanecem separadas |
| RF24 | **Governança e calibração**: papéis de engenharia/operação, ADRs e registro das correções | SD01/K01/RV06 implementadas; lições globais dependem de autorização/revisão, sem aprendizagem automática irrestrita |

## 5. Arquitetura

```
<workspace CPJ>\            atual: D:\CPJ - TRABALHO\
├─ PRD.md · AGENTS.md · CLAUDE.md · GEMINI.md · LEIA-ME.md · Central CPJ.bat
├─ casos\OS-<nº>-<ano>\        00-originais · 01-extracao\<doc>\ · 02-analise · 03-relatorios · caso.json · processamento.json
│                               · registro-tratamento.md · ia-progresso.json · ia-logs\
├─ consulta\<base>\             original · registros.jsonl · base.json      (somente pesquisa)
├─ referencias\<ref>\           original · texto.md · meta.json             (estilo/calibração)
├─ calibracao\                  licoes-aprendidas.md · historico-calibracao.md
├─ modelos\                     MODELO RELATORIO DE INVESTIGACAO - CPJ 2026.docx · dados-padrao.json
├─ producao\                    base.json · base.csv · painel.html · config.json (meta)
├─ rag\cpj.sqlite               trechos(+FTS5) · entidades · pessoas · docs     (derivado; regenerável)
├─ config\                      usuarios.json · segredo.key · auditoria.log · rede.json · central.crt/key  (NUNCA versionar)
├─ exportacoes\                 pacotes ZIP exportados · _recebidos\
├─ portatil\                    procedimentos autocontidos para qualquer IA (gerado)
├─ ferramentas\                 scripts .ps1/.bat/.py de manutenção · tessdata\por.traineddata
├─ acervo\repo-ia-alandougs\    clone Git do GitHub alandougs/repo-ia-alandougs
└─ plugin\                      marketplace local "cpj-local"
   └─ investigacao-cpj\
      ├─ .claude-plugin\plugin.json          versão 0.3.2 instalada e confirmada em 10/10/2026
      ├─ app\servidor.py · auth.py · tarefas.py · static\index.html      (Central CPJ, Flask)
      ├─ commands\*.md (10)  agents\*.md (3)
      └─ skills\ pdf-autos-policiais (diagnostico/extrair/tabelas/entidades/dividir.py)
                analise-documental · analise-ip-fraude (references: normativas, tipologia)
                relatorio-ip-fraude (gerar_docx.py, references/modelo-cpj.md)
                base-cpj (caso.py, indexar.py, rag.py, consulta.py, referencias.py, progresso.py, gerar_painel.py)
```

- **Stack:** Python 3.12, Flask 3.1, Cheroot 11.1.2+ (WSGI/TLS), SQLite FTS5, pypdf, pypdfium2, pdfplumber, pytesseract + Tesseract 5.4 (`por` tessdata_best), python-docx, openpyxl, xlrd, cryptography. Sem Node em produção. PowerShell 5.1 (scripts `.ps1` ASCII).
- **IA automática:** fila SQLite do plantão com agentes aprovados, reserva atômica, expediente, cancelamento e quatro pedidos da esteira. Claude é o padrão; há adaptadores Codex/Gemini/Copilot e oito APIs. O executor recebe procedimentos e ferramentas do caso, sem navegação/conectores. Após a execução, o servidor gera DOCX e reindexa. Ativação de API e consentimento são distintos; catálogo transmite chave/metadados, sem autos. **Claude requer `claude auth login`**; login concluído após autorização OAuth específica do operador em 10/10/2026. AI03 implementa consulta explícita ao catálogo e sugestão equilibrada compatível, preservando escolha manual; salvar continua uma ação do operador.
- **Segurança web:** cookie HttpOnly/SameSite=Strict (Secure com HTTPS), cabeçalho `X-CPJ: 1` obrigatório em POST (anti-CSRF), permissões por rota, bind 127.0.0.1 por padrão, `abrir` arquivos só no PC da Central.
- **Segurança SEC21–SEC25 (fonte local):** arquivos ativos/desconhecidos baixados com CSP sandbox; Host/Origin e HTTPS obrigatórios no compartilhamento. Chaves API protegidas por DPAPI, com migração atômica do legado e falha fechada. Em exFAT a âncora da auditoria fica no perfil NTFS da conta. Claude automático usa transporte JSON sem ferramentas nativas, com capacidades de arquivo conferidas pelo servidor; exige CLI 2.1.304+ da série 2.1.x. Codex/Gemini/Copilot automáticos ficam bloqueados até controle equivalente; sessões de chat autorizadas não são alteradas. Não é sandbox de SO nem proteção contra controle integral da conta/máquina.

## 6. Modelo de dados

`caso.json` (schema `cpj-caso/1`): `id, ordem_servico, bo, inquerito, processo, referencia, natureza, modalidade, status, datas{recebido, extraido, em_analise, analisado, minuta, entregue}, prazo, requisitante, prioridade, determinacao, criado_por, responsavel, visto, documentos[], ip{paginas, sha256, metodos, pendentes, conferir}, vitimas[], investigados[], financeiro{prejuizo_declarado, prejuizo_documentado, valor_rastreado, transacoes, contas_destino, camadas}, resultado{autoria, sugestoes_providencias}, relatorios[], baixa{data, origem, arquivo}, baixa_ignorar, horas_trabalho, observacoes`.

Status: `recebido → extraido → em_analise → analisado → minuta → entregue` (+ `devolvido`, `arquivado`). Modalidades: `skills/analise-ip-fraude/references/tipologia-golpes.md`.

Arquivos de análise: `ficha-caso.md, cronologia.md, pessoas-vinculos.md, pessoas.csv (nome;mae;pai;cpf;rg;nascimento;telefones;enderecos;empresas;cnpj;emails;placas;condicao;paginas;documento), fluxo-financeiro.csv/.md, elementos-tipo.md, matriz-achados.md, lacunas-diligencias.md, conexoes.md`. Relatório: `minuta-vNN.md` (frontmatter lido por `gerar_docx.py`), `rastreabilidade-vNN.md`, `revisao-vNN.md`, `RELATORIO-<ID>-vNN.docx`, `RELATORIO-<ID>-FINAL.docx/.md`.

Pacote de exportação: `.cpjenc` autenticado (Scrypt + AES-256-GCM por blocos), com ZIP interno contendo `manifest.json` (`schema: cpj-export/1`, `modo`, `casos`, `arquivos[{caminho, tamanho, sha256}]`) e `dados/<caminho relativo ao workspace>`. A senha não é recuperável pela Central; não integra tarefa/log. Isso não substitui backup completo do estado operacional.

## 7. Requisitos não funcionais

- Tempo: OCR ~1–3 s/página (300 págs. ≈ 5–15 min), sem travar a interface; exportação/importação com progresso por bytes.
- Robustez: tarefas interrompidas retomam na reinicialização (processamento); escrita atômica de JSON; índice regenerável (`indexar.py --tudo`).
- Portabilidade: tudo funciona sem Claude (scripts + Central); procedimentos em `portatil\` para outros agentes.
- Privacidade: painel/planilha não exibem nomes além do necessário; `config\`, casos, bases e referências nunca vão ao Git (`ferramentas\publicar-github.ps1` faz varredura e bloqueia).

## 8. Como executar e manter

- Abrir: `Central CPJ.bat` (ou atalho na Área de Trabalho). Primeiro acesso: criar o admin (no próprio PC). Depois, Sistema → Usuários.
- Saúde: `ferramentas\Verificar ambiente.bat`. Backup completo: `ferramentas\Backup.bat`, que exige confirmar escritores parados e mídia autorizada/protegida. Snapshots são versionados, incluem cópia consistente SQLite e âncora cifrada da auditoria; não apagam versões antigas. `restaurar.ps1 -Origem <snapshot> -Destino <pasta-nova> -MidiaProtegida` restaura somente em pasta NOVA. Confirmações não verificam BitLocker nem param processos. Sistema → Exportar gera pacote de transferência, não backup completo. DPAPI depende da conta/perfil Windows; outra conta exige migração explícita.
- Após editar o plugin: `ferramentas\Atualizar plugin.bat` (sobe versão, valida pacote/marketplace, confere instalação e regera `portatil\`). O staging local `C:\Users\alan_\AppData\Local\CPJ\plugin` contém apenas código genérico; a CLI recusou registro direto da origem D: exFAT. Não alterar confiança para contornar a recusa. Atualizador prioriza Python válido da `.venv`.
- Publicação exige pedido expresso. **Não executar o publicador legado para diagnóstico:** ele pode alterar o acervo mesmo sem envio. GitHub não recebeu as alterações deste loop.
- Teste isolado: `python plugin\investigacao-cpj\app\servidor.py --workspace <pasta-teste> --porta 8766 --somente-local --sem-navegador` (use `CPJ_WORKSPACE` nos scripts). PDF fictício: `skills\pdf-autos-policiais\teste\gerar_pdf_ficticio.py`.

## 9. Estado atual e próximos passos (atualizar sempre)

**16/11/2026 — meta de entrega (MQ01–MQ04).** A confiabilidade passa a ser medida: percentual da primeira e da última minuta mantido no relatório entregue (PDF do relatório = versão entregue), por `skills/relatorio-ip-fraude/scripts/medir_entrega.py`. Linha de base manual: 10 relatórios completos, primeira minuta mantida em 80 % ou mais em 5 e a última em 9. Enquanto esse número não estabilizar, não se acrescenta funcionalidade fora do core (mapa, grafo, perfis delegado/escrivão, rede, novos provedores de IA, operação 24/7); o código existente permanece. Plano e andamento: `revisoes/confiabilidade-mq-2026-11-16.md`.

**Histórico movido em 16/11/2026 (MQ04):** as entradas datadas da seção 9 de 27/09 a 28/10/2026 (rodadas E/V/RV, ASTRA/AST, unificação UN, AS01–AS04, SY, SEC21–SEC25, RG26–RG29, RP30–RP35, AP36–AP40, VU01, MD02 e demais), a subseção "Registros históricos" e o "Registro de mudanças" completo estão em [docs/historico/PRD-historico-2026.md](docs/historico/PRD-historico-2026.md). Esse arquivo é registro histórico, não autoritativo; o estado vigente é o desta seção.

**30/10/2026 — FP02, controles da fila:** cartões concluídos, inclusive com pendência, oferecem reprocessamento com seleção de OCR e abertura da O.S.; cancelamento e remoção permanecem nos estados aceitos pela API. Atualização manual e contagem de pendências no resumo. Barra acessível em todos os estados, com percentual real, conclusão explicitamente local, amarelo para pendência e indicação indeterminada quando não há medida. Controles evitam pedidos repetidos e recuperam falhas sem perder a seleção. FP02 4/4 (Edge e mobile), FP01 9/9, OS01 2/2, OC01 5/5 e AZ01 5/5 aprovados: 25 testes. Recursos atualizados conferidos por hash na Central, sem reiniciar ou processar casos reais. Evidências em `revisoes/controles-fila-fp02-2026-10-30.md`.

**30/10/2026 — OS01, pendências visíveis na fila da O.S.:** o cartão de extração local concluída com transcrição visual pendente ou OCR indisponível deixou de usar o selo verde de conclusão integral. A fila agora mostra “Processamento local concluído · transcrição pendente”, selo amarelo “pendências” e resumo com pendências; conclusões sem limitação permanecem inalteradas. Não houve mudança de estado persistido, extração, consentimento ou provedor. Regressão sintética `teste_fila_pendencias_os01.py` 2/2 (incluindo dois cenários de limitação) e FP01 9/9, incluindo navegador Edge.


**30/10/2026 — AS50, correções da auditoria e conferência do RAG:** integração local expressamente liberada pelo operador, preservando as frentes concorrentes. Corrigidos XSS em metadados/status/datas, limites de login e custo da auditoria onde há marca confiável de alteração, CAS da ficha, vínculo autenticado por HMAC e snapshot de minuta/DOCX, PDF obsoleto, repetição de IA após resultado incerto e cancelamento após queda. RAG preserva primeira página com BOM, repara índices legados afetados na indexação incremental, informa falha semântica sem derrubar FTS e filtra entidades por O.S. Novos contratos interativos e fixtures registrados na AS50. Na raiz integrada: 90 testes de regressão aprovados, AR01 real 2/2 e fluxo HTTP completo aprovado; LC01 com modelo público já em cache, rede desativada, 26/26; revisão independente dos achados e do HMAC, além de ensaio Edge de XSS, aprovados. Central reiniciada ociosa com os últimos ajustes: HTTP 200, estáticos conferidos por hash e login malformado JSON 400. Primeira rodada ampla: 150/161 suítes; quatro falhas foram resolvidas e aprovadas em retestes; sete suítes de outras frentes têm pendências discriminadas na revisão. Não se declara homologação geral nem publicação. Evidências e limites em `revisoes/correcoes-as50-2026-10-30.md`.

**30/10/2026 — MV01, movimento no visual futurista:** pedido expresso do operador, que apontou a ausência de movimento no VU01 (registrado como "sem animação contínua"). Somente CSS em `apple-cpj.css`: aba ativa entra deslizando, modal surge, reflexo percorre a faixa verde do header de vidro, KPIs e etapas elevam com brilho verde no hover, cartões acendem a borda, botão principal brilha, etapa ativa e contador de pendências pulsam e a barra de progresso tem reflexo. Grafo e mapa permanecem parados (GF10). Movimento reduzido, contraste alto, transparência reduzida e cores forçadas desligam a decoração. Teste novo `teste_movimento_mv01.py` 1/1; AP37 1/1, AP39 5/5, RG26 1/1, GF10 e FX91 aprovados. AP39 passou a aguardar só animações finitas (as contínuas nunca terminam). Central serve o CSS novo sem reinício.

**27/10/2026 — memória e coordenação:** `MEMORIA.md` é a entrada comum dos agentes; fontes canônicas existentes mantidas, sem regras concorrentes por pasta. Preferência Astra coordenador e Sol/Terra/Luna por complexidade e custo compatível com acerto, com revisão independente e limites/consentimentos preservados. Auditor existente complementado em AU01, sem percentual fictício de certeza.

**27/10/2026 — determinação vigente:** novos PDFs devem produzir somente Markdown como extração documental; sem tabelas/entidades CSV ou JSON consolidado derivados. Metadados/checkpoints essenciais permanecem; arquivos antigos não são apagados por extensão. Integração SY05/SX01, mudança MD01 e diagnóstico/limpeza SZ01 autorizados pelo operador com coordenação e subagentes. Integração validada em candidato isolado e aplicada localmente; testes/resultados registrados em `revisoes/sincronizacao-github-2026-10-27.md`.

### Estado consolidado em 10/10/2026

**Arquitetura escolhida pelo operador:** SQLite para a operação solo. `caso.json` permanece fonte do caso, `rag/cpj.sqlite` é índice regenerável e o plantão mantém sua fila SQLite. PostgreSQL/Docker continuam fora do caminho de execução; não foi comprovada sincronização de um PostgreSQL externo. Esta revisão usa código e fixtures fictícias, sem certificar dados reais da produção.

**Verificação:** AG04 concluiu duas rodadas completas estabilizadas: **71/71 suítes em ambas**, retorno zero, **560,67 s e 841,92 s** de testes; tempos do harness **833,09 s e 1.305,95 s**. Não houve repetição para esconder falha. F03 Edge inclui OCR, minuta, DOCX, gate FINAL sem forçar, baixa e painel. Alterações posteriores têm validação própria e não devem ser atribuídas àquele snapshot. Acervo: **61 testes + 33 subtestes**, validação estrita **170 itens, 35 planejados, zero erros/avisos**; CLI GC04 verifica seis páginas digitalizadas, 105 referências, cinco cálculos e mutações que falham. CI remota não executada. Na sincronização SY02, o acervo atualizado com 31 commits remotos passou na validação estrita (184 itens, 35 planejados, zero erros/avisos) e no detector de sensíveis (zero achados); 60 testes e 33 subtestes passaram, e uma falha de teste de OCR permaneceu por falta do executável Tesseract. O smoke test do núcleo de fraude passou. Na Central, o ciclo completo aprovou 77/78 no primeiro teste; a única asserção incompatível com o contrato de cancelamento foi corrigida no teste e validada em 5/5 no runner integrado (`--rapido --incluir teste_importacao_codex.py`).

**Ambiente/plugin:** Claude Code oficial **2.1.287**, plugin **0.3.3** instalado/habilitado, conferidos independentemente pelo CLI; os 76 arquivos do bundle instalado coincidem por SHA-256 com fonte e staging (mais o manifesto do marketplace, 77 arquivos genéricos preparados). Onze portáteis e doze adaptadores CPJ regenerados/conferidos. CL03 corrigiu YAML inválido e atualizador que anunciava sucesso após falha. Python do PATH é alias Store ausente; ENV02 reparou `.venv` para **3.12.14**, com imports principais, pip e cinco inicializadores verificados. ENV03 encontra o Claude nativo sem depender do PATH antigo. Não houve instalação global de Python. Login Claude concluído após autorização OAuth específica do operador em 10/10/2026; CLI confirma `loggedIn: true`, `claude.ai`, plano Pro. P01 concluída e auditada com fonte fictícia de quatro páginas e plugin 0.3.2; as correções posteriores TS07/TS08 foram testadas e incorporadas ao plugin 0.3.3, sem nova inferência.

| Frente | Estado e evidência atual |
|---|---|
| CF01/AI01/AI02/AI03 | Configurações, prompt de sistema, executor e consulta explícita aos catálogos implementados. Nove cartões, oito APIs e Copilot; sugestão equilibrada depende de resposta compatível e preserva escolhas manuais, inclusive campo limpo. Consulta não salva nem ativa provedor. Treze testes e 12 cenários Chrome aprovados; disponibilidade real da conta e inferência não certificadas. |
| D01–D03/CL02/CX03 | Plantão persistente, aprovação/sinal de vida, painel, expediente configurável, squad por blocos e orçamento por grupo/pedido. Custo/tokens exigem uso medido e tarifas explícitas; CLI admite limite de tempo, sem teto financeiro inferido. Uma chamada enviada pode exceder o teto antes de sua medição. |
| CX01/CX02/DJ01/PX05–PX07/SE01 | OCR local com workers/checkpoints por hash, cancelamento, Markdown/CSV/JSON, modos Rápido/Inteligente/IA Completa, PNG por API com aceite positivo e normalização somente de derivados. Sem autorização/provedor compatível, limitação explícita; originais preservados. |
| GH01/GH02 | Integração SY02 reconciliou `origin/main` nos branches de preservação `codex/final-sync-20261010` (Central) e `codex/sync-20261010` (acervo), mantendo as mudanças locais e os 31 commits remotos do acervo. Catálogo/ROUTER/llms.txt foram regenerados: 184 itens. PRs para `main` estão publicados e mergeáveis: [Central #3](https://github.com/alandougs/central-cpj-postgres/pull/3) e [acervo #23](https://github.com/alandougs/repo-ia-alandougs/pull/23), aguardando revisão humana; sem merge direto. Experimentos PostgreSQL/Docker e scripts de depuração permaneceram locais, fora da publicação, conforme a decisão SQLite. |
| GH03–GH07/GC01–GC06/GI01 | Revisões/propostas históricas não são merge. PR14/15/17 fechados sem merge; operador autorizou GC05 local. Modo entrega, detector de sensíveis, esquemas e cópias canônicas implementados/testados. GC06 registrou aprovação humana somente de autoria; não promoveu todo o acervo a revisado. GH07 continua proposta de estados patrimoniais, não integração concluída. |
| SK01 | scope-guard/no-gold-plating instaladas nas pastas de skills, cópias equivalentes; reservas, testes e governança permanecem obrigatórios. |
| RV17–RV20/TS04/TS05 | Gate exige conferência nova da minuta atual (hash/modo); escrita API atômica e arquivos vazios bloqueados. TS04 inclui banco na identidade financeira: 19 testes e conferência independente de dois nós de 100 em vez de um de 200. TS05 impede conclusão com arquivo reservado ausente, salvo justificativa explícita registrada: 12 testes e oito RV14 aprovados. |

**Fila local autorizada concluída:** as tarefas do loop foram executadas e verificadas, incluindo P01, TS07, TS08 e CL08. TS07 corrige CSV explícito e imagens de conteúdo com `--sem-assinatura`; oito testes focados e sete regressões aprovados, oito repetidos pelo integrador em 4,736 s. TS08 exige solicitações da O.S., dados faltantes e rastreabilidade versionada, inclusive em retomadas antigas; oito testes independentes em 13,508 s, squad 12/12, TS06 3/3 e plantão simulado aprovados. CL08 instalou 0.3.3 e conferiu todos os hashes. Funcionalidades congeladas e propostas históricas não foram implementadas por esse fechamento. Em 10/10/2026 o operador autorizou commit, sincronização e publicação por PR; SY02 publicou os PRs Central #3 e acervo #23 para `main`, ambos mergeáveis e aguardando revisão humana.

**Verificação posterior ao snapshot AG04:** ambiente virtual e cinco inicializadores verificados em sandbox; seis testes independentes, rápida 5/5 e `pip check` aprovados. ENV03 encontra a instalação nativa mesmo com PATH antigo: oito testes, rápida 5/5 e plantão simulado aprovados. AI03 passou em rápida 5/5; TS04 em rápida 5/5 e quatro testes DOCX. Integração HTTP final, após essas mudanças, retornou zero em **128,66 s** (harness 157,80 s): permissões, OCR, minuta/DOCX, FINAL, baixa, exportação/importação e pesquisa com dados fictícios. Nenhum desses resultados comprova o piloto real com IA ou boot operacional.

**Piloto P01 concluído:** segunda tentativa real com plugin 0.3.2: quatro pedidos, sete sessões Claude, **859,75 s**, **US$ 5,3127658 equivalentes API** e 4.085.381 tokens cumulativos incluindo cache; cobrança Pro não disponível. Primeira tentativa falha preservada. Auditoria corrigiu duas formulações em v02 e completou explicitamente três registros obrigatórios ausentes na automação; 13 hashes anteriores intactos, 48 afirmações v02 sustentadas na auditoria Codex, DOCX reaberto com imagem, feminino e valores corretos. Resumo do revisor automático errou a contagem (44+2, tabela 46+2); não se presume revisão humana ou conformidade automática integral. Relato e métricas em `PILOTO-2026.md`. Um caso fictício curto não certifica qualidade em autos extensos nem uso oficial. Os dois bugs das opções DOCX foram corrigidos em TS07 e o contrato dos registros em TS08; revisão/correção humanas das minutas continuam necessárias.

**Incidente de teste conhecido:** o diagnóstico inicial herdou APPDATA real ao testar Startup e pode ter substituído/apagado `Central-CPJ-24-7.lnk`. O caminho estava ausente na conferência posterior; presença/conteúdo anteriores são desconhecidos. O operador foi informado. AG02 corrigiu isolamento e comprovou preservação de sentinela fictícia; rodadas seguintes usaram APPDATA adicional fictício. SY02 instalou e verificou `Central-CPJ-24-7.lnk` na pasta Startup, apontando a `wscript.exe` e ao inicializador VBS do workspace; o daemon foi iniciado e `status --json` confirmou processo vivo e HTTP saudável em `127.0.0.1:8765`. A execução após reinício do Windows ainda depende do próximo login.

Relatos completos: `revisoes/estado-projeto-loop-2026-10-09.md`, `revisoes/suite-completa-2026-10-02.md`, `revisoes/plugin-0.3.3-2026-10-10.md`, `revisoes/exportacao-portatil-2026-10-10.md` e quadro `TAREFAS-COMPARTILHADAS.md`. Os registros abaixo são **históricos**; suas listas de pendências e alegações de instalação não substituem este estado consolidado.

### Registros históricos

Registros históricos movidos literalmente para [docs/historico/PRD-historico-2026.md](docs/historico/PRD-historico-2026.md) (seção "Registros históricos").

## Registro de mudanças

Registro de mudanças até 16/11/2026 movido literalmente para [docs/historico/PRD-historico-2026.md](docs/historico/PRD-historico-2026.md) (seção "Registro de mudanças"). Novas entregas continuam sendo registradas aqui, uma linha por entrega, com a mais recente no topo.

- 2026-11-17 — MQ06: `ferramentas/fila-os.py` deixa de contar pedido de dilação de prazo como autos ou relatório da O.S.; teste `teste_fila_os_pedido_mq06.py`. Evidência em `revisoes/confiabilidade-mq-2026-11-16.md`.
- 2026-11-17 — MQ05: pasta única por O.S.; a fila de O.S. enxerga o PDF e o relatório do próprio caso; teste `teste_fila_os_caso_mq05.py`. Evidência no mesmo arquivo.
