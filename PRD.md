# PRD — Central CPJ e plugin `investigacao-cpj`

> Documento de continuidade. Qualquer agente (Claude Code, Codex, Gemini, modelo local) deve ler **este arquivo + `AGENTS.md`** antes de alterar o sistema. Atualize a seção **9 (Estado atual)** e o **Registro de mudanças** a cada entrega.
> Dono do produto: Alan Douglas Silva — Investigador de Polícia, Central de Polícia Judiciária (CPJ), Seccional de Presidente Prudente, DEINTER 8, PCSP.
> Última atualização: 2026-09-28 (Revisão de Foco no Core e Operação Solo).

---

## 1. Visão

> **FASE ATUAL, ratificada pelo investigador em 28/09/2026: operação solo e foco no core.** Usuário único: Alan Douglas Silva, Investigador de Polícia, no próprio computador. Core: **PDF dos autos → OCR local → Markdown por página + CSV → análise investigativa (caminho do dinheiro/Pix, art. 171) → relatório DOCX CPJ 2026**. Meta: uso real em 29/09/2026, 09:00 (tarefas `E` em `TAREFAS-COMPARTILHADAS.md`).
> Modo solo implementado (`config\solo.json`), sem senha no próprio PC. **Congelados**, com o código mantido e sem melhorias: perfis delegado/escrivão, rede local, PostgreSQL/Docker (PG01) e novos papéis de IA. O texto abaixo sobre perfis e fluxo delegado/escrivão descreve a capacidade existente, não a prioridade.

Sistema local, simples e seguro para a **produção de relatórios de investigação em inquéritos de fraude e estelionato**: a O.S. chega (cadastrada pelo delegado/escrivão ou pelo investigador) com o PDF do IP → o sistema extrai **Markdown por página + tabelas em CSV** (OCR em português quando necessário) → **agentes de IA** analisam somente o material do caso e redigem a **minuta no modelo oficial** (DOCX com timbre e assinatura) → o investigador revisa/edita, define a versão FINAL e a **produção** é contabilizada (dia/mês/ano, prazos, KPIs). Tudo vira base pesquisável (RAG local), com calibração contínua a partir das correções do investigador e de relatórios de referência.

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
2. PDF ≤ 100 págs. pode ser lido diretamente por IA em consulta pontual, mas **o correto é extrair Markdown + CSV** e analisar sobre a extração (rastreabilidade por página).
3. Separar fato documentado × relato × indício × inferência × lacuna; citar `(pág. N; fls. X)`; nunca completar CPF/conta/chave Pix/valor por dedução; nunca atribuir autoria sem base.
4. **Sigilo (art. 20 CPP):** processamento local; nada de conteúdo de caso para serviços externos; agentes automáticos rodam **sem internet e sem conectores (MCP)**; dados de casos nunca vão ao GitHub.
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
| RF03 | Auditoria de ações (login, O.S., uploads, downloads, IA, exportações, pesquisas) em `config\auditoria.log` | implementado |
| RF04 | **Nova O.S.**: nº O.S., BO, IP, processo, natureza, requisitante, prazo, prioridade, determinação + upload PDF/MD/CSV (progresso real de envio) | implementado (backend) |
| RF05 | Fila de processamento: diagnóstico → texto/OCR (progresso por página) → tabelas CSV → dados críticos → indexação | implementado |
| RF06 | **Início**: O.S. novas não vistas, prazos vencidos/hoje/≤3 dias, sem prazo, andamento por etapa, minhas O.S., produção do dia/mês | implementado (backend) |
| RF07 | **Casos**: lista ordenada por urgência de prazo; busca por O.S./BO/IP/processo/partes/modalidade; ficha com edição, documentos, processamento, arquivos, conexões | implementado |
| RF08 | **Botões de IA** na ficha: Analisar, Gerar relatório, Análise+relatório, Revisar — executa Claude Code em modo automático com progresso por marcos + atividade ao vivo, fila única, cancelar | implementado (backend); requer login do Claude CLI |
| RF09 | **Editor leve da minuta** (campos do cabeçalho + 3 seções) → nova versão + DOCX no modelo; PDF (LibreOffice, se instalado); Abrir no Word (só no PC da Central); **Definir FINAL** (gera FINAL.md e dá baixa) | implementado (backend) |
| RF10 | **Baixa na produção** por 3 vias com origem registrada: arquivo `*FINAL*` na pasta (automática), botão, agente | implementado |
| RF11 | **Pesquisa relacional** de pessoas: nome, mãe, pai, CPF, RG, telefone, CNPJ/empresa, endereço (combináveis, sem acento, por palavras) em qualificações extraídas dos autos (`02-analise\pessoas.csv`) e bases de consulta; + ocorrências nos autos | implementado (backend) |
| RF12 | **Pesquisa textual (RAG)** em transcrições, análises, relatórios, referências, acervo; cruzamento de CPF/Pix/conta/telefone entre casos | implementado |
| RF13 | **Bases de consulta** (Muralha Paulista e similares): importar .xlsx/.xls/.csv/.docx com mapeamento automático de colunas; listar/remover | implementado (backend) |
| RF14 | **Relatórios de referência** por autor, modalidade e peso (1–5) para calibração/exemplos; importar DOCX/PDF/MD; editar peso; remover | implementado (backend) |
| RF15 | **Exportar banco de dados**: pacote ZIP (`manifest.json` com SHA-256 por arquivo), modo completo (com PDFs) ou só dados, opcional modelo DOCX; baixar planilha CSV | implementado (backend) |
| RF16 | **Importar pacote** em outro PC: verifica integridade, acrescenta casos novos, nunca sobrescreve | implementado (backend) |
| RF17 | **Estatísticas/KPIs**: entregues dia/mês/ano × meta, páginas, prazo mediano, em aberto por etapa, modalidades, autoria indicada, valor rastreado | implementado; **pendente**: KPIs de prazo (% no prazo, vencidos) e retrabalho no painel |
| RF18 | **Rede local**: admin habilita acesso de outros PCs com HTTPS (certificado autoassinado); padrão desligado | implementado (backend); exige autorização do firewall pelo usuário e aval da TI |
| RF19 | Usuários (admin): criar/editar/desativar/remover, trocar a própria senha, ver auditoria | implementado (backend) |
| RF20 | Interface única, limpa, responsiva, claro/escuro, barras de progresso reais em upload, OCR, exportação, importação e IA | **em construção** (`app/static/index.html` precisa ser reescrito para as APIs novas) |
| RF21 | **Operação Full-Time 24/7**: execução contínua em segundo plano na porta estática `8765`, inicialização com o Windows, reinício automático em falha e utilitários de controle | implementado e testado (tarefa FT01) |
| RF22 | **Esteira Completa 1-Clique**: botão e orquestrador assíncrono para processar o IP de ponta a ponta (OCR $\rightarrow$ CSVs $\rightarrow$ RAG $\rightarrow$ Analista Financeiro $\rightarrow$ Minuta $\rightarrow$ Revisor Gauntlet $\rightarrow$ DOCX) com checkpoints de retomada e barra de progresso | planejado (tarefa EC01) |
| RF23 | **Fluxograma Visual do Caminho do Dinheiro**: compilação gráfica das camadas de repasse do `fluxo-financeiro.csv` em imagem PNG (300 DPI) e injeção automática no relatório oficial DOCX | planejado (tarefa FD01) |
| RF22 | **Esteira Completa 1-Clique**: botão e orquestrador assíncrono para processar o IP de ponta a ponta (OCR $\rightarrow$ CSVs $\rightarrow$ RAG $\rightarrow$ Analista Financeiro $\rightarrow$ Minuta $\rightarrow$ Revisor Gauntlet $\rightarrow$ DOCX) com checkpoints de retomada e barra de progresso | implementado e testado (tarefa EC01) |
| RF23 | **Fluxograma Visual do Caminho do Dinheiro**: compilação gráfica das camadas de repasse do `fluxo-financeiro.csv` em imagem PNG (300 DPI) e injeção automática no relatório oficial DOCX | implementado e testado (tarefa FD01) |
| RF24 | **Governança de System Design & Calibração Contínua**: formalização dos papéis de engenharia vs operação, ADRs e retroalimentação automática de lições aprendidas a partir das edições no Word | implementado e documentado (tarefa SD01) |

## 5. Arquitetura

```
C:\CPJ - TRABALHO\
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
      ├─ .claude-plugin\plugin.json          versão atual 0.2.0 (→ 0.3.0 nesta entrega)
      ├─ app\servidor.py · auth.py · tarefas.py · static\index.html      (Central CPJ, Flask)
      ├─ commands\*.md (10)  agents\*.md (3)
      └─ skills\ pdf-autos-policiais (diagnostico/extrair/tabelas/entidades/dividir.py)
                analise-documental · analise-ip-fraude (references: normativas, tipologia)
                relatorio-ip-fraude (gerar_docx.py, references/modelo-cpj.md)
                base-cpj (caso.py, indexar.py, rag.py, consulta.py, referencias.py, progresso.py, gerar_painel.py)
```

- **Stack:** Python 3.12, Flask 3.1, SQLite FTS5, pypdf, pypdfium2, pdfplumber, pytesseract + Tesseract 5.4 (`por` tessdata_best), python-docx, openpyxl, xlrd, cryptography. Sem Node. PowerShell 5.1 (scripts `.ps1` ASCII).
- **IA automática:** `tarefas.py` executa `claude.exe -p <prompt> --output-format stream-json --permission-mode acceptEdits --allowedTools Read Write Edit Glob Grep Skill Task TodoWrite "Bash(python *)" "PowerShell(python *)" --disallowedTools WebFetch WebSearch --strict-mcp-config` com `cwd` = workspace. O agente registra marcos com `progresso.py <ID> <pct> "<etapa>"`. Após o agente, o servidor garante o DOCX da minuta mais recente e reindexa. **Requer `claude auth login` no CLI** (Sistema → Entrar no Claude).
- **Segurança web:** cookie HttpOnly/SameSite=Strict (Secure com HTTPS), cabeçalho `X-CPJ: 1` obrigatório em POST (anti-CSRF), permissões por rota, bind 127.0.0.1 por padrão, `abrir` arquivos só no PC da Central.

## 6. Modelo de dados

`caso.json` (schema `cpj-caso/1`): `id, ordem_servico, bo, inquerito, processo, referencia, natureza, modalidade, status, datas{recebido, extraido, em_analise, analisado, minuta, entregue}, prazo, requisitante, prioridade, determinacao, criado_por, responsavel, visto, documentos[], ip{paginas, sha256, metodos, pendentes, conferir}, vitimas[], investigados[], financeiro{prejuizo_declarado, prejuizo_documentado, valor_rastreado, transacoes, contas_destino, camadas}, resultado{autoria, sugestoes_providencias}, relatorios[], baixa{data, origem, arquivo}, baixa_ignorar, horas_trabalho, observacoes`.

Status: `recebido → extraido → em_analise → analisado → minuta → entregue` (+ `devolvido`, `arquivado`). Modalidades: `skills/analise-ip-fraude/references/tipologia-golpes.md`.

Arquivos de análise: `ficha-caso.md, cronologia.md, pessoas-vinculos.md, pessoas.csv (nome;mae;pai;cpf;rg;nascimento;telefones;enderecos;empresas;cnpj;emails;placas;condicao;paginas;documento), fluxo-financeiro.csv/.md, elementos-tipo.md, matriz-achados.md, lacunas-diligencias.md, conexoes.md`. Relatório: `minuta-vNN.md` (frontmatter lido por `gerar_docx.py`), `rastreabilidade-vNN.md`, `revisao-vNN.md`, `RELATORIO-<ID>-vNN.docx`, `RELATORIO-<ID>-FINAL.docx/.md`.

Pacote de exportação: ZIP com `manifest.json` (`schema: cpj-export/1`, `modo`, `casos`, `arquivos[{caminho, tamanho, sha256}]`) e `dados/<caminho relativo ao workspace>`.

## 7. Requisitos não funcionais

- Tempo: OCR ~1–3 s/página (300 págs. ≈ 5–15 min), sem travar a interface; exportação/importação com progresso por bytes.
- Robustez: tarefas interrompidas retomam na reinicialização (processamento); escrita atômica de JSON; índice regenerável (`indexar.py --tudo`).
- Portabilidade: tudo funciona sem Claude (scripts + Central); procedimentos em `portatil\` para outros agentes.
- Privacidade: painel/planilha não exibem nomes além do necessário; `config\`, casos, bases e referências nunca vão ao Git (`ferramentas\publicar-github.ps1` faz varredura e bloqueia).

## 8. Como executar e manter

- Abrir: `Central CPJ.bat` (ou atalho na Área de Trabalho). Primeiro acesso: criar o admin (no próprio PC). Depois, Sistema → Usuários.
- Saúde: `ferramentas\Verificar ambiente.bat`. Backup: `ferramentas\Backup.bat` ou Sistema → Exportar.
- Após editar o plugin: `ferramentas\Atualizar plugin.bat` (sobe versão, valida, reinstala, regera `portatil\`).
- Publicar melhorias genéricas: `ferramentas\Publicar no GitHub.bat`.
- Teste isolado: `python plugin\investigacao-cpj\app\servidor.py --workspace <pasta-teste> --porta 8766 --somente-local --sem-navegador` (use `CPJ_WORKSPACE` nos scripts). PDF fictício: `skills\pdf-autos-policiais\teste\gerar_pdf_ficticio.py`.

## 9. Estado atual e próximos passos (atualizar sempre)

**Fila aberta a todos os agentes — 2026-09-27:** `TAREFAS-COMPARTILHADAS.md` permite assumir tarefas livres por Codex, Claude, Gemini ou outro agente. L01/L02 já em andamento permanecem com Claude; as demais frentes não iniciadas ficam sem responsável até reserva. O script `ferramentas/fila-tarefas.py` lista, reserva, conclui e libera tarefas com trava exclusiva, gravação atômica, conferência de responsável, sobreposição de arquivos e dependências da integração. Ensaios em fila fictícia aprovaram reserva/devolução/conclusão, recusa de conflito e responsável incorreto, bloqueio de dependências e disputa simultânea com exatamente um vencedor. `AGENTS.md`, `CLAUDE.md` e `GEMINI.md` apontam para o mesmo procedimento.

**Melhorias coordenadas Codex/Claude — 2026-09-27:** o quadro `TAREFAS-COMPARTILHADAS.md` registra responsáveis, reservas de arquivos e contratos para evitar edições simultâneas. **C01/C02 concluídas pelo Codex:** mesma autorização na edição e no cadastro repetido de O.S. (incluindo uploads), revogação de sessões após redefinição de senha/desativação/reativação/recriação, preservação da sessão atual na troca própria e proteção do último administrador ativo. Validação: **11 testes de segurança novos aprovados + 52 verificações da suíte API existente aprovadas**, somente com workspace temporário e dados fictícios; IA externa desligada. Cookies da versão anterior exigem novo login. Nenhuma conta real foi alterada. C03–C05 e as frentes disponíveis para Claude permanecem pendentes no quadro; a integração de melhorias ao sistema completo ainda não está concluída.

**Revisão técnica do fluxo funcional — 2026-09-27:** ver `REVISAO-TECNICA-2026-09-27.md`. A suíte atual de API passou com **52 verificações** em workspace fictício, com IA externa desativada. Testes adicionais reproduziram contorno de permissão pela rota de cadastro de O.S., fusão de homônimos, filtros positivos para negações de mandado/cautelar, importação após cancelamento e fora das raízes de dados esperadas, sessões anteriores válidas após redefinição de senha e erro de indexação ignorado. O relatório prioriza correções, interfaces restantes, desempenho e recuperação. Esta revisão não corrigiu o código funcional e não valida IA real, carga, OCR extenso ou interface visual. As listas históricas abaixo precisam de consolidação; prevalecem as evidências datadas e o código atual.

**Pronto e testado (dados fictícios):** extração (230 págs.), OCR `por`, tabelas CSV, entidades, DOCX no modelo, baixa (3 vias), RAG/cruzamento, painel, Central v1 (upload, casos, busca, produção), plugin 0.2.0 instalado, `portatil\`, scripts de manutenção.

**Integração Codex (2026-09-27):** onze skills locais em `.agents/skills/` para as dez tarefas portáteis e manutenção do sistema; entrada pessoal `cpj-projeto` em `~/.agents/skills/`. Gerador/instalador local `ferramentas/configurar-codex.py` e atalho `Configurar Codex.bat`, com modo de conferência sem escrita. Adaptadores apontam para procedimentos vivos e não duplicam scripts, modelo ou dados de casos. Regras de sigilo explicitam a diferença entre scripts locais e inferência externa. Esta integração não altera o executor Claude da Central nem conclui as RF pendentes.

**Validação da integração:** as doze skills passaram em `quick_validate.py`; metadados YAML e links locais conferidos. Reinstalação sem alterações e modo `--verificar` aprovados. Workspace fictício confirmou bloqueio de arquivo não gerenciado antes de qualquer escrita e detecção de procedimento ausente. Descoberta visual no seletor do aplicativo ainda não verificada; se não aparecer, reinicie o Codex.

**Implementado nesta entrega, falta testar/integrar:** `app/auth.py`, `app/tarefas.py`, `app/servidor.py` v2 (todas as rotas das RF01–RF19), `consulta.py`, `referencias.py`, `progresso.py`, pessoas/referências no `indexar.py`, `rag.pesquisa_relacional`/`exemplos` com peso/autor.

**Atualização 2026-09-27 (fim da sessão, limite de uso atingido):**
- Central v2 (`app/servidor.py`, `auth.py`, `tarefas.py`, `static/index.html`) implementada e **54/54 testes OK** em `app/testes/teste_central.py` (rodar com servidor de teste: `servidor.py --workspace <pasta-teste> --porta 8767 --somente-local`; a pasta de teste precisa de `config\credenciais-teste.json`, `ip_ficticio.pdf`, `muralha_ficticio.xlsx`, `referencia_ficticia.docx` — ver o cabeçalho do teste). Perfis editáveis (matriz), pasta pessoal `usuarios\<login>\`, responsável por caso, KPIs de prazo e retrabalho feitos.
- **Feito após os testes, falta testar:** (a) `auth.py` com login por usuário, CPF, nome completo ou e-mail, `cargo`/`cpf`/`email` no usuário, **senha temporária com troca obrigatória** (HTTP 428 até trocar) e rede bloqueada enquanto houver senha temporária; (b) `consulta.py` com ingestão de PDF (OCR se necessário), TXT e **texto colado** (`/api/consulta/colar`), extraindo antecedentes: processos/IP/TC/CNJ, BOs, **mandados de prisão**, **medidas cautelares**, placas e veículos; (c) `indexar.py` com colunas novas em `pessoas` e a tabela **`arestas`** (grafo de vínculos: pessoa, CPF, telefone, placa, endereço, empresa, CNPJ, processo, BO, conta, chave Pix, caso); (d) `rag.vinculos()` + `/api/vinculos` e filtros `processo`, `bo`, `placa`, `mandado`, `cautelar` em `/api/pesquisa/pessoas`.
- **Interface pendente para (a)–(d):** a tela de troca de senha e os campos da configuração inicial já estão no `index.html`. Faltam: no formulário de usuários, os campos CPF, e-mail, cargo e a caixa "senha temporária" (enviar `cpf`, `email`, `cargo`, `temporaria` em `/api/usuarios`); em Minha conta, editar e-mail e cargo (`/api/minha-conta`); nas bases de consulta, aceitar .pdf/.txt e um `<textarea>` "colar texto" → `/api/consulta/colar`; na pesquisa, os campos Processo/IP/TC, BO, Placa e as caixas "com mandado de prisão" e "com medida cautelar", uma coluna Antecedentes nos resultados, um botão **vínculos** por pessoa (`/api/vinculos?tipo=PESSOA&valor=<nome>`) exibido em lista e "ver ficha" (campo `texto`).
- **Usuário real a criar** (pedido do investigador): login `admin`, nome Alan Douglas Silva, cargo Investigador de Polícia, perfil admin, CPF informado por ele no chat, e a senha que ele informou como **temporária** (`temporaria=True`, troca obrigatória no 1º acesso). Criar via `Auth(WS).salvar_usuario(...)` no workspace real **somente após testar (a)**. A senha não deve ser registrada em arquivos.
- Depois: acrescentar ao `teste_central.py` os casos de (a)–(d), rodar tudo, `ferramentas\Atualizar plugin.bat` (→ 0.3.0), atualizar skills (`analise-ip-fraude` gerar `pessoas.csv`; regra das bases de consulta; `relatorio-ip-fraude` usar `rag.py exemplos --autor`), `LEIA-ME.md`, e publicar quando o usuário fizer o login no GitHub.
- Visual do grafo (próxima etapa): biblioteca JS **local** (sem CDN, ex. cytoscape.js copiado para `app/static/`) consumindo `/api/vinculos`.

**Rodada enxuta — 2026-09-28 (ratificada pelo investigador; meta 29/09 09:00):**
Revisão da proposta feita com o Gemini: o foco no core e a operação solo foram mantidos. O "auto-login" constava só nos documentos e foi implementado e testado nesta revisão (modo solo, seção 2). Também foram corrigidos dois bloqueios de uso neste PC:
- **OCR:** o Tesseract não está em `C:\Program Files\Tesseract-OCR`, só no PDF24 (5.4.1, sem idiomas). A Central detecta `CPJ_TESSERACT`, a instalação padrão, o PDF24 e o PATH, e usa o `por.traineddata` de `ferramentas\tessdata`. O teste de OCR real (`teste_dados_os_codex`) passou pela primeira vez neste PC.
- **Fila:** `fila-tarefas.py proxima` (códigos 0/3/4) para agentes em loop; saída UTF-8 no console do Windows.

Pendente (tarefas E01–E06): Claude CLI instalado via npm não é encontrado pela Central (E01); interface do modo solo (E02); ensaio ponta a ponta com PDF fictício de ~120 págs. (E03); extratos/Pix → CSV (E04); guia de uso (E05); fechamento, suítes, plugin e esta seção (E06). Busca RAG e estatísticas já existem e não entram nesta rodada.

**Fechamento da rodada enxuta — E06 (2026-09-28, Claude-1):** E01–E05, E07 e a rodada de melhorias F (F01–F04, F10, F03) concluídas. Suíte completa validada em workspace temporário, dados fictícios: as 26 suítes de `app\testes\` (exceto `teste_central.py`) passaram — 0 falhas; `teste_central.py` rodado de ponta a ponta com servidor real na porta 8768, workspace temporário e fixtures fictícias (`credenciais-teste.json`, PDF/xlsx/docx fictícios) — **TUDO OK, retorno 0** (52 verificações: configuração inicial, permissões por perfil, processamento OCR, base de consulta/Muralha fictícia, pesquisa relacional, referência, minuta → DOCX → FINAL → baixa, exportar/importar, IA sem login do Claude, auditoria, pasta pessoal, responsáveis). `ferramentas\verificar-ambiente.ps1`: Python, bibliotecas, Tesseract, OCR português e modelo DOCX OK; duas pendências sem bloquear o core — "Delegado padrão" em `modelos\dados-padrao.json` (preenchimento é do investigador) e o item **Plugin** com caminho desatualizado para o Claude CLI (registrado como `E12`, em andamento por Codex-1). Falha intermitente antes observada em `teste_core_e03.py` sob carga (registrada como `E11`) não se repetiu após a correção da E07; suíte agora estável. `ferramentas\atualizar-plugin.ps1` foi executado (`-SemVersao`) e falhou antes de tocar qualquer arquivo: usa o mesmo caminho fixo desatualizado da E12 para localizar `claude.exe` (`$env:APPDATA\Claude\claude-code\*\claude.exe`, inexistente neste PC — o Claude Code está instalado via npm). Registrado como `E13` (não é arquivo reservado da E06). Plugin e `portatil\` seguem na versão já instalada; nenhuma regressão. Checklist de pronto: itens 1–4 e 6 confirmados por teste; item 5 com três pendências não bloqueantes ao uso do core (E12, E13 e o "Delegado padrão" pendente de preenchimento pelo investigador).

**Rodada V1 — aberta em 28/09/2026 (revisão técnica + auditoria externa do acervo):** plano em `revisoes/plano-v1-2026-09-28.md`, tarefas V (core) e R (acervo) em `TAREFAS-COMPARTILHADAS.md`. A conferência de hoje contradiz o fechamento da E06 em três pontos, todos P0 para o uso real:
- Os scripts e a Central usam `C:\CPJ - TRABALHO` como workspace padrão, mas o projeto está em `D:`: 10 scripts, o `Central CPJ.bat` sem `CPJ_WORKSPACE` e 106 ocorrências nos procedimentos. A Central aberta hoje gravou em `C:\CPJ - TRABALHO\config\`. Os testes não pegaram porque sempre usam `--workspace`. Correções: V01 e V02.
- O plugin `investigacao-cpj` não está instalado no Claude Code (V03, com decisão D2).
- `config\solo.json` ausente (D1, ação do investigador).

Também entra o **gate de entrega** do core: hoje "Definir FINAL" não confere pendências nem citações (V04/V05/V06). A auditoria do GPT sobre o acervo foi conferida no commit `6622fc8`: quase todos os pontos se confirmam (tabela A do plano). Divergências: duplicações resolvidas por manifesto de cópias canônicas, sem reestruturar; nenhum agente novo por enquanto. **Terminologia:** existem dois `caso.json`. O do core (`cpj-caso/1`) é gestão e produção; o do acervo é o estado analítico (nós, operações, fontes). Não unificar nesta fase.

**Consolidação da Central CPJ, Modularização e Operação Full-Time 24/7 (A01 / I01 / FT01 — 2026-09-30, Antigravity / Gemini-1):**
- Modularização completa de `servidor.py` em blueprints no pacote `plugin/investigacao-cpj/app/rotas/` (`casos.py`, `comum.py`, `consulta.py`, `relatorios.py`, `sistema.py`, `usuarios.py`). Preservação integral de retrocompatibilidade de símbolos e propriedades dinâmicas do módulo.
- Implementação rigorosa dos contratos de concorrência C05 em `caso.py` (`ConflitoRevisao`, `CasoOcupado`, `transacao`, `trava` reentrante, `reservar_arquivo_versao`) e nos manipuladores HTTP 409/503.
- Resiliência e robustez na esteira de importação e processamento em `tarefas.py` e rotas de processamento (tratamento robusto de `ip` default em `caso.py`, cancelamento real de importação e validação de caminhos).
- Suíte completa de integração `teste_central.py` (52 verificações ponta a ponta) e todas as suítes especializadas 100% aprovadas em workspace isolado com dados fictícios.
- Operação Full-Time 24/7 (FT01): supervisor de segundo plano `central-daemon.py`, inicializador silencioso VBScript sem janela preta (`iniciar-central-24-7.vbs`), utilitários batch (`Central Full-Time.bat`, `Status Central.bat`, `Parar Central.bat`), reinício automático em caso de crash (watchdog) e instalação de inicialização no boot do Windows (`Startup\Central-CPJ-24-7.lnk`). Validado por suíte própria `teste_fulltime.py` (5/5 testes OK).
- Governança de System Design e Calibração Fática (SD01): formalização do ADR-001 (`governanca/decisoes/ADR-001-system-design-cpj.md`), matriz RACI e papéis de agentes de engenharia vs. produção policial (`governanca/papeis-de-agentes.md`) e fechamento do ciclo contínuo de calibração fática Word $\rightarrow$ `calibracao/licoes-aprendidas.md`.
- Esteira Completa 1-Clique (EC01): implementação da ação e endpoint `POST /api/casos/<id>/esteira` para disparar a esteira integrada (OCR $\rightarrow$ análise documental $\rightarrow$ caminho do dinheiro $\rightarrow$ minuta no modelo oficial $\rightarrow$ revisão independente Gauntlet $\rightarrow$ DOCX), botão visual de destaque na Central CPJ (`index.html`) e orquestração encadeada no plantão (`plantao.py`). Validado por suíte dedicada `teste_esteira_completa.py` (6/6 testes OK).
- Fluxograma Visual do Caminho do Dinheiro (FD01): compilação gráfica forense em alta resolução (PNG 300 DPI) das camadas bancárias (vítima $\rightarrow$ 1ª camada de passagem $\rightarrow$ 2ª camada de repasse $\rightarrow$ destino) via `gerar_diagrama_financeiro.py`, suporte a imagens Markdown (`![legenda](caminho)`) e injeção automática no DOCX oficial CPJ via `gerar_docx.py`. Validado por suíte própria `teste_diagrama_docx.py` (5/5 testes OK).

**Atualização RV03 — 2026-10-01:** os documentos de governança vazios foram reconstruídos a partir das decisões já registradas neste PRD, de `TAREFAS-COMPARTILHADAS.md` e das regras vigentes em `AGENTS.md`: `governanca/decisoes/ADR-001-system-design-cpj.md` registra arquitetura local, foco no core, segregação de dados, decisão humana e validação segura; `governanca/papeis-de-agentes.md` distingue engenharia, etapas de produção do relatório e responsabilidades humanas. São documentos normativos de governança, não evidência de que cada funcionalidade citada no histórico esteja atualmente implementada ou testada. A situação técnica das entregas SD01 permanece sujeita às tarefas de recuperação e validação registradas na fila.

## Registro de mudanças

| Data | Versão | Mudança |
|---|---|---|
| 2026-09-27 | 0.1.0 | Plugin inicial (skills, agentes, comandos), workspace, OCR `por`, DOCX no modelo, RAG, painel |
| 2026-09-27 | 0.2.0 | Central CPJ v1, pasta por O.S., baixa automática/agente/central, scripts de manutenção, `portatil\`, publicação GitHub |
| 2026-09-27 | 0.3.0 (em construção) | Login/perfis/auditoria, O.S. com prazos e pendências, IA por botão, editor de minuta, exportar/importar, bases de consulta (Muralha Paulista), pesquisa relacional, relatórios de referência por autor/peso, rede local HTTPS |
| 2026-09-27 | Integração Codex | Onze skills do projeto, entrada pessoal CPJ, gerador/instalador verificável, instruções e guia de uso; preservados procedimentos e executor existentes |
| 2026-09-27 | Revisão técnica | Inventário do que existe e falta; suíte API com 52 verificações aprovadas em dados fictícios, reproduções de falhas e prioridades de confiabilidade, desempenho e usabilidade; sem alteração do código funcional |
| 2026-09-27 | Melhorias C01/C02 | Quadro Codex/Claude e reservas de arquivos; autorização uniforme de O.S., revogação de sessões e proteção do último admin ativo; 11 testes novos e 52 verificações existentes aprovados em dados fictícios |
| 2026-09-27 | Fila multiagente | Tarefas livres para qualquer agente, preservando as já em andamento; CLI de reserva/conclusão/liberação com trava e verificações de conflitos, responsável e dependências; instruções Gemini atualizadas |
| 2026-09-28 | Revisão Estratégica (Investigador) | Diretriz soberana de foco no Core: PDF -> OCR -> Markdown/CSV -> Análise Investigativa -> DOCX Oficial. Modo solo/direto (sem atrito de login local); postergação de complexidades multiusuário e infraestrutura pesada (Docker/Postgres) em prol de simplicidade e uso operacional diário imediato. |
| 2026-09-28 | Ratificação + rodada enxuta | Diretriz do Gemini revisada: modo solo implementado (opt-in, só loopback, único admin; 7 testes), Tesseract do PDF24 detectado + tessdata do projeto (OCR real verde neste PC), `fila-tarefas.py proxima`; PostgreSQL/Docker e multiusuário congelados; tarefas E01–E06 para uso em 29/09 09:00 |
| 2026-09-28 | Fechamento E06 | E01–E05, E07, F01–F04/F03/F10 concluídas; 26 suítes de `app\testes\` + `teste_central.py` (52 verificações) verdes em workspace temporário; `verificar-ambiente.ps1` sem pendência crítica (2 avisos não bloqueantes, um deles já em atendimento na E12); `atualizar-plugin.ps1` adiado até a E12 concluir |
| 2026-09-28 | Abertura Rodada V1 | Revisão técnica + auditoria GPT conferida no código: bloqueios P0 (workspace fixo em C:, plugin não instalado, solo.json), gate de entrega no core, trilha R do acervo (modo estrito, regressão no CI, cópias canônicas, estados impostos); plano em `revisoes/plano-v1-2026-09-28.md` |
| 2026-09-29 | Demandas Arquiteturais | Inclusão de RF21–RF24 e tarefas FT01 (Full-Time 24/7 porta 8765), EC01 (Esteira Completa 1-Clique), FD01 (Fluxograma no DOCX) e SD01 (System Design & Governança) no quadro compartilhado e planejamento do produto |
| 2026-09-30 | 0.3.0 (consolidada) | Modularização de `servidor.py` em `rotas/` (A01), contratos de concorrência C05 (`ConflitoRevisao`/`CasoOcupado`), resiliência em `tarefas.py` e aprovação integral da suíte `teste_central.py` (52 checks) (I01). |
| 2026-09-30 | 0.3.1 (Full-Time 24/7) | Operação contínua Full-Time 24/7 da Central CPJ na porta estática 8765: supervisor/vigia com auto-restart em falha (`central-daemon.py`), inicializador VBS sem janela (`iniciar-central-24-7.vbs`), scripts batch de controle e inicialização no boot do Windows (`teste_fulltime.py` aprovado com 5/5 testes) (FT01). |
| 2026-09-30 | 0.3.2 (System Design & Governança) | ADR-001 formalizado (`governanca/decisoes/ADR-001-system-design-cpj.md`), matriz RACI e governança de agentes (`governanca/papeis-de-agentes.md`), consolidação do ciclo contínuo de calibração fática Word $\rightarrow$ `calibracao/licoes-aprendidas.md` (SD01). |
| 2026-09-30 | 0.3.3 (Esteira Completa 1-Clique) | Implementação da Esteira Completa 1-Clique (`/api/casos/<id>/esteira` e botão UI), encadeamento automático no plantão e pós-processamento com geração garantida de DOCX e reindexação RAG (`teste_esteira_completa.py` 6/6 OK) (EC01). |
| 2026-09-30 | 0.3.4 (Fluxograma Financeiro no DOCX) | Compilação gráfica do caminho do dinheiro em PNG 300 DPI (`gerar_diagrama_financeiro.py`), suporte a imagens Markdown e injeção automática no relatório oficial DOCX CPJ 2026 (`teste_diagrama_docx.py` 5/5 OK) (FD01). |
| 2026-10-01 | Governança (RV03) | Recriados ADR-001 e matriz de papéis com base em decisões documentadas; esclarecido que o registro histórico não comprova, por si, implementação/teste atual das funcionalidades. |
