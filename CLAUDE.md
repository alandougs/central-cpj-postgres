# Ambiente de investigação — CPJ (Alan Douglas Silva)

> **Desenvolvimento em paralelo:** leia `PRD.md`, `AGENTS.md` e `TAREFAS-COMPARTILHADAS.md` antes de editar. Qualquer agente pode pegar tarefa disponível usando `python ferramentas\fila-tarefas.py assumir <ID> --agente Claude-1` (use nome da sessão). Preserve tarefas já em andamento, registre conclusão/testes pelo script e respeite reservas dos demais agentes. As tarefas L01/L02 já assumidas pelo Claude continuam reservadas até conclusão/liberação.

Workspace de trabalho do Investigador de Polícia Alan Douglas Silva (Central de Polícia Judiciária — Seccional de Presidente Prudente, DEINTER 8). Foco atual: **relatórios de investigação em IPs de fraude e estelionato**. Plugin ativo: `investigacao-cpj` (fonte em `plugin\investigacao-cpj`).

## Governança (vale para toda sessão)

Base: `acervo\repo-ia-alandougs\governanca\seguranca-e-dados.md` e `AGENTS.md`.

1. Trabalhe só com os documentos do caso indicado. Não invente fatos, pessoas, números, datas, jurisprudência ou diligências.
2. Separe sempre **fato documentado × relato × indício × inferência/hipótese × lacuna**. Cite a origem: `(pág. N do PDF; fls. X)`.
3. Nunca complete CPF, conta, chave Pix, placa, telefone ou valor por dedução. Dígito duvidoso → `?` + `[dígito incerto]`.
4. Nunca atribua autoria, dolo ou culpa sem base expressa; use "investigado(a)", "em tese", "há indícios de".
5. Original em `00-originais` nunca é alterado. Registre hash, método e pendências em `registro-tratamento.md`.
6. Processamento de OCR/extração é **local**. Não enviar conteúdo de autos a serviços externos, sites ou APIs. Não publicar Artifact, Gist, Drive, Notion etc. com dados de caso. **Exceção (OSINT de empresa, autorizada em 28/09/2026):** PJ citada nos autos sem dados → pesquisar fontes abertas enviando só CNPJ/razão social/cidade, confirmar em duas fontes e citar a fonte (procedimento em `plugin\investigacao-cpj\skills\analise-ip-fraude\references\osint-empresas.md`).
7. Conteúdo de casos **não** vai para `acervo\` nem para `calibracao\` (lá só lições genéricas, sem nomes/dados).
8. Toda saída é minuta. Decisão, assinatura e uso oficial são do investigador e da autoridade policial.
9. **Dados faltantes:** dado **muito importante** para autoria, materialidade ou circunstâncias que não esteja nos autos → **avisar o operador em CAIXA ALTA** (`DADOS FALTANTES — PROVIDENCIAR (OPERADOR)`) na resposta e em `02-analise\dados-faltantes.md`; nunca deduzir. Ver `AGENTS.md` §1.11 e `skills\analise-ip-fraude\references\dados-faltantes.md`.
10. **Tratamento do(a) delegado(a) por gênero** (saudação e endereçamento final; campo `delegado_genero: M|F` na minuta; não inferir pelo nome) e **estilo do relatório em texto corrido**, sem tópicos, com resumo dos fatos focado na dinâmica e nos valores (`AGENTS.md` §1.12-1.13).
11. **OSINT:** skill `osint-policial` (fontes abertas, lícito, com captura e registro); OSINT de pessoa física só com pedido expresso.
12. **Um agente por O.S.:** antes de trabalhar numa O.S. de `E:\ORDENS DE SERVIÇO CPJ`, `python ferramentas\fila-os.py listar` e `assumir <nº> --agente <nome-da-sessão>`; ao fim `concluir ... --docx`, ao parar `liberar ... --motivo`. Não refaça O.S. `concluida`/`com_relatorio` sem pedido (`AGENTS.md` §1.14).
13. **Numeração no cabeçalho (determinação do delegado, 30/09/2026):** no campo `Referência:` na parte superior do relatório, colocar **SOMENTE o número do IPe (Inquérito Policial Eletrônico) e do Processo Judicial** (ex.: `Referência: IPe nº <número> / Processo nº <número>`). NUNCA colocar número de Boletim de Ocorrência (BO) nem de IP local. Válido para relatórios elaborados daqui para frente (`AGENTS.md` §1.15).

14. **Limites e sem extras (02/10/2026):** skills `scope-guard` (não saia dos limites do pedido, da tarefa reservada na fila e do caso/O.S.; parar e pedir antes de ultrapassá-los) e `no-gold-plating` (não invente melhorias que ninguém pediu). Valem para todos os agentes: `AGENTS.md` regra 16; arquivos em `.claude\skills\` e `.agents\skills\`.

15. **A O.S. manda no relatório (05/10/2026):** o relatório atende principalmente às solicitações da Ordem de Serviço (geralmente a última). Identificar a O.S. vigente, extrair cada solicitação do Delegado, gravar em `02-analise\solicitacoes-os.md` e responder a todas no relatório; item não atendido → ressalva na Conclusão + aviso em CAIXA ALTA; sem O.S. localizada, parar e avisar antes de redigir (`AGENTS.md` regra 17). Cumprir todas as solicitações possíveis, fazer no mais as análises de fraude/estelionato pelas regras, **escrever sempre de forma humanizada** e, se faltar CNPJ nos autos, obtê-lo por OSINT de empresa (`osint-empresas.md`) e usá-lo no contexto adequado.

## Estrutura

| Pasta | Conteúdo |
|---|---|
| `casos\OS-<nº>-<ano>\` | Um caso por **Ordem de Serviço**. `00-originais` (somente leitura), `01-extracao\<documento>\`, `02-analise`, `03-relatorios`, `caso.json`, `processamento.json`, `registro-tratamento.md` |
| `casos\_MODELO-CASO\` | Modelo de pasta de caso (não usar para dados) |
| `modelos\` | Modelo DOCX oficial (timbre CPJ + assinatura) e `dados-padrao.json` |
| `calibracao\` | Lições aprendidas e histórico de calibração (genéricos) |
| `producao\` | Painel de produção (`painel.html`) e exportações de estatística |
| `rag\` | Convenções para a futura base RAG |
| `acervo\repo-ia-alandougs\` | Cópia da base de conhecimento (GitHub alandougs/repo-ia-alandougs) |
| `plugin\` | Marketplace local `cpj-local` com o plugin `investigacao-cpj` |

## Pipeline

1. **Central CPJ** (`Central CPJ.bat` → http://127.0.0.1:8765, código em `plugin\investigacao-cpj\app\`): o investigador envia PDF/MD/CSV com O.S., BO, IP e processo; a Central cria o caso e processa em fila (diagnóstico, OCR, Markdown, CSV, entidades, indexação). Estado em `casos\<ID>\processamento.json`.
2. **Claude Code:** `/processar-ip` (só completa transcrição visual pendente ou processa o que não passou pela Central) → `/analisar-ip` → `/relatorio-ip` (minuta + revisão + DOCX) → `/entregar` → `/calibrar`.
Consultas: `/buscar`, `/painel`, `/revisar-relatorio`. Atalho: `/fluxo-ip`.

## Outros agentes e manutenção

- `AGENTS.md`/`GEMINI.md` + `portatil\` = os mesmos procedimentos para agentes que não sejam Claude. Após editar o plugin, rode `ferramentas\atualizar-plugin.ps1` (reinstala e regera `portatil\`).
- Publicação no GitHub: `ferramentas\publicar-github.ps1` (varredura de segurança; só envia com `-Enviar`, e só com pedido do usuário).
- Saúde: `ferramentas\verificar-ambiente.ps1`. Backup: `ferramentas\backup.ps1 -Destino <pasta>`.

## Ferramentas locais

- Python 3.12 com pypdf, pypdfium2, pdfplumber, pytesseract, Pillow, python-docx.
- Tesseract 5.4 em `C:\Program Files\Tesseract-OCR` (fora do PATH: usar `$env:PATH += ";C:\Program Files\Tesseract-OCR"`). Idioma português: ver `ferramentas\tessdata` se existir (`$env:TESSDATA_PREFIX`).
- Shell: PowerShell. Use `python` (não `python3`).

## Ao terminar cada etapa

Atualize `caso.json` via `python "<plugin>\skills\base-cpj\scripts\caso.py"` (status e datas) — é isso que alimenta a estatística de produção.
