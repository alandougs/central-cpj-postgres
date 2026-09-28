# Ambiente de investigação — CPJ (Alan Douglas Silva)

> **Desenvolvimento em paralelo:** leia `PRD.md`, `AGENTS.md` e `TAREFAS-COMPARTILHADAS.md` antes de editar. Qualquer agente pode pegar tarefa disponível usando `python ferramentas\fila-tarefas.py assumir <ID> --agente Claude-1` (use nome da sessão). Preserve tarefas já em andamento, registre conclusão/testes pelo script e respeite reservas dos demais agentes.

> **Fase atual (ratificada em 28/09/2026):** usuário único (Alan Douglas Silva, Investigador de Polícia), modo solo sem senha no próprio PC (`config\solo.json`) e foco só no core `PDF → OCR → Markdown/CSV → análise → DOCX`. PostgreSQL/Docker e multiusuário estão congelados. Trabalhe apenas nas tarefas `E` da seção "Rodada enxuta" de `TAREFAS-COMPARTILHADAS.md`. Em loop, use `python ferramentas\fila-tarefas.py proxima` e pare quando o código de saída for 3. Detalhes em `AGENTS.md`.

Workspace de trabalho do Investigador de Polícia Alan Douglas Silva (Central de Polícia Judiciária — Seccional de Presidente Prudente, DEINTER 8). Foco atual: **relatórios de investigação em IPs de fraude e estelionato**. Plugin ativo: `investigacao-cpj` (fonte em `plugin\investigacao-cpj`).

## Governança (vale para toda sessão)

Base: `acervo\repo-ia-alandougs\governanca\seguranca-e-dados.md` e `AGENTS.md`.

1. Trabalhe só com os documentos do caso indicado. Não invente fatos, pessoas, números, datas, jurisprudência ou diligências.
2. Separe sempre **fato documentado × relato × indício × inferência/hipótese × lacuna**. Cite a origem: `(pág. N do PDF; fls. X)`.
3. Nunca complete CPF, conta, chave Pix, placa, telefone ou valor por dedução. Dígito duvidoso → `?` + `[dígito incerto]`.
4. Nunca atribua autoria, dolo ou culpa sem base expressa; use "investigado(a)", "em tese", "há indícios de".
5. Original em `00-originais` nunca é alterado. Registre hash, método e pendências em `registro-tratamento.md`.
6. Processamento de OCR/extração é **local**. Não enviar conteúdo de autos a serviços externos, sites ou APIs. Não publicar Artifact, Gist, Drive, Notion etc. com dados de caso.
7. Conteúdo de casos **não** vai para `acervo\` nem para `calibracao\` (lá só lições genéricas, sem nomes/dados).
8. Toda saída é minuta. Decisão, assinatura e uso oficial são do investigador e da autoridade policial.

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
- Tesseract 5.4: neste PC, o do PDF24 (`C:\Program Files\PDF24\tesseract`); a instalação padrão (`C:\Program Files\Tesseract-OCR`) também é aceita. A Central detecta sozinha. Fora dela: `$env:PATH += ";C:\Program Files\PDF24\tesseract"`. Idioma português sempre em `ferramentas\tessdata` (`$env:TESSDATA_PREFIX = "<workspace>\ferramentas\tessdata"`), porque o PDF24 não traz idiomas.
- Shell: PowerShell. Use `python` (não `python3`).

## Ao terminar cada etapa

Atualize `caso.json` via `python "<plugin>\skills\base-cpj\scripts\caso.py"` (status e datas) — é isso que alimenta a estatística de produção.
