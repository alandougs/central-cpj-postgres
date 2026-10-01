# Instruções para agentes de IA — Ambiente de investigação CPJ

> **Para desenvolver/continuar o sistema** (Central CPJ, plugin, scripts): leia primeiro **`PRD.md`** — requisitos, arquitetura, estado atual e próximos passos. Este `AGENTS.md` cobre o **uso** operacional (casos, análise, relatório).

> **Desenvolvimento em paralelo:** antes de editar, leia `TAREFAS-COMPARTILHADAS.md`. A fila está aberta a Codex, Claude, Gemini e outros agentes. Assuma uma tarefa disponível com `python ferramentas\fila-tarefas.py assumir <ID> --agente <nome-da-sessao>`; respeite as reservas das tarefas em andamento e registre testes/conclusão pelo mesmo script. Não edite arquivo reservado ao outro agente.

Vale para **qualquer agente** (Claude Code, Codex, Gemini/Antigravity, Copilot, modelos locais). Workspace do Investigador de Polícia Alan Douglas Silva (Central de Polícia Judiciária — Seccional de Presidente Prudente, DEINTER 8). Foco: **relatórios de investigação em IPs de fraude e estelionato**.

Tudo aqui é Markdown + scripts Python locais: nada depende do Claude. No Claude Code, os mesmos procedimentos aparecem como plugin `investigacao-cpj` (comandos `/…`).

## 1. Regras (obrigatórias)

1. Trabalhe só com os documentos do caso indicado. Não invente fatos, pessoas, números, datas, jurisprudência ou diligências.
2. Separe **fato documentado × relato × indício × inferência/hipótese × lacuna**. Cite a origem: `(pág. N do PDF; fls. X)`.
3. Nunca complete CPF, conta, chave Pix, placa, telefone ou valor por dedução. Dígito duvidoso → `?` + `[dígito incerto]`.
4. Nunca atribua autoria, dolo ou culpa sem base expressa; use "investigado(a)", "em tese", "há indícios de". Titular de conta recebedora não é automaticamente autor.
5. `00-originais` nunca é alterado. Registre hash, método e pendências em `registro-tratamento.md`.
6. Processamento local por padrão. **Não envie conteúdo de autos a sites, APIs ou provedores externos salvo quando o administrador/investigador responsável ativar explicitamente aquele provedor em “Sistema → Provedores e modelos de IA”.** A ativação autoriza o uso da respectiva API nos pedidos da fila, inclusive com conteúdo do caso; confira se a conta/serviço atende ao sigilo do IP (art. 20 do CPP) e às normas do órgão. Sem provedor ativo, use somente agentes locais ou sessões de chat autorizadas pelo operador. A consulta ao catálogo de modelos transmite apenas a chave da API e metadados da requisição, nunca conteúdo de caso.
7. Conteúdo de casos não vai para `acervo\`, `calibracao\` nem para o GitHub.
8. Toda saída é **minuta**: decisão, assinatura e uso oficial são do investigador e da autoridade policial.
9. **Bases de consulta** (`consulta\`, ex. Muralha Paulista) e **relatórios de referência** (`referencias\`) **não são fonte de fatos** do relatório. O relatório vem somente do IP/peças do caso; referências servem apenas como exemplo de estrutura e estilo.
10. **OSINT de empresas (exceção autorizada pelo investigador, 28/09/2026):** empresa (pessoa jurídica) citada nos autos **sem dados** → pesquisar em fontes abertas o máximo de dados verdadeiros, confirmar por duas fontes e citar a fonte no relatório. Enviar à internet **somente CNPJ/razão social/cidade** — nunca nomes de investigados/vítimas, valores ou trechos dos autos. Pessoa física só com pedido expresso. Procedimento: `plugin\investigacao-cpj\skills\analise-ip-fraude\references\osint-empresas.md`; registro em `02-analise\osint-empresas.md`. Para qualquer pesquisa em fontes abertas (método, base legal, fontes, captura de prova) use a skill `osint-policial` (`plugin\investigacao-cpj\skills\osint-policial\`).
11. **Dados faltantes (aviso em CAIXA ALTA):** se faltar dado **muito importante** para apurar a infração penal, a materialidade, a autoria e as circunstâncias (CF, art. 144, § 4º; CPP, art. 6º) — qualificação, objeto, pessoa, empresa, telefone, extrato, veículo, local etc. —, **não deduza nem invente**: avise o operador em **CAIXA ALTA**, sob o título `DADOS FALTANTES — PROVIDENCIAR (OPERADOR)`, na resposta final e em `02-analise\dados-faltantes.md`, com o que falta, onde/como obter (sistema policial, ofício, ordem judicial, OSINT, diligência) e por que importa. No relatório vira ressalva objetiva na Conclusão, sem sugerir providência. Procedimento: `plugin\investigacao-cpj\skills\analise-ip-fraude\references\dados-faltantes.md`.
12. **Tratamento do(a) delegado(a):** ajuste saudação e endereçamento ao **gênero** de quem preside o feito (masculino: "EXCELENTÍSSIMO SENHOR DOUTOR DELEGADO DE POLÍCIA" e, ao final, "Ao Excelentíssimo Sr. Dr. / NOME / Delegado de Polícia / Central de Polícia Judiciária"; feminino: "EXCELENTÍSSIMA SENHORA DOUTORA DELEGADA DE POLÍCIA" e "À Excelentíssima Sra. Dra. / NOME / Delegada de Polícia / Central de Polícia Judiciária"). Descubra o gênero nos documentos do caso (ex.: "Dr."/"Dra." nas conclusões, "o/a Delegado/a"); **não infira pelo nome**. Sem base, pergunte ao operador e avise em CAIXA ALTA. Na minuta use `delegado_genero: M` ou `F`.
13. **Estilo e formatação do relatório (mão do investigador):** texto **corrido**, jurídico, objetivo e humano; **sem tópicos, marcadores, negritos de abertura e listas** no corpo (evita aparência de texto gerado por IA); tabela só para a planilha do caminho do dinheiro, quando necessária. **Resumo dos fatos** compacto: a dinâmica do golpe e, sobretudo, os **valores movimentados**. Fls. só em pontos de muita relevância e dados financeiros. Conclusão breve, sem sugestões de providência salvo pedido.
    - **Nomes de pessoas e empresas:** sempre em **NEGRITO E CAIXA ALTA** (ex.: `**JOÃO DA SILVA**`, `**BANCO BRADESCO S.A.**`).
    - **Demais informações importantes:** destacadas em negrito normal (`**dado**`).
    - **Informações super relevantes:** grifadas de amarelo (use a marcação `==texto super relevante==`).
    - **Informações que o investigador deva obter ou preencher manualmente:** escritas em **CAIXA ALTA E EM VERMELHO** para alertar (use `[PESQUISAR: DADO EM CAIXA ALTA]`, `[OBTER: ...]`, `{PREENCHER: ...}`). O gerador DOCX automaticamente aplica a cor vermelha e caixa alta.

14. **Um agente por Ordem de Serviço:** antes de extrair, analisar ou redigir qualquer O.S. de `E:\ORDENS DE SERVIÇO CPJ`, rode `python ferramentas\fila-os.py listar` e reserve com `assumir <nº> --agente <nome>` (ou `proxima --agente <nome>`). Não pegue O.S. `em_andamento` de outro agente nem refaça O.S. `concluida`/`com_relatorio` sem pedido expresso do investigador. Workspace canônico dos casos: `C:\CPJ - TRABALHO\casos`. Ao terminar, `concluir <nº> --agente <nome> --docx "<caminho>"` e copie o DOCX final para a pasta da O.S.; se parar, `liberar ... --motivo "<onde parou>"`. A reserva vence em 4 h sem `renovar`. Quadro: `E:\ORDENS DE SERVIÇO CPJ\_CONTROLE-OS.md`.

15. **Numeração do procedimento no cabeçalho (determinação do delegado, 30/09/2026):** no campo **Referência:** e nas informações do procedimento na parte superior do relatório de inquérito policial, use **EXCLUSIVAMENTE o número do Inquérito Policial Eletrônico (IPe) e do Processo Judicial** (ex.: `Referência: IPe nº <número> / Processo nº <número>`). **NÃO coloque o número do Boletim de Ocorrência (BO)** e **NÃO coloque o número do IP local (físico/delegacia de origem)**. Esta regra é mandatória para todos os relatórios elaborados a partir de 30/09/2026.

Governança completa: `acervo\repo-ia-alandougs\governanca\seguranca-e-dados.md`.

## 2. Estrutura

| Pasta | Conteúdo |
|---|---|
| `casos\OS-<nº>-<ano>\` | Um caso por Ordem de Serviço: `00-originais` (somente leitura), `01-extracao\<documento>\` (`transcricao.md` com `## Página N`, `tabelas\*.csv`, `entidades.csv`, `relatorio_extracao.json`), `02-analise\`, `03-relatorios\`, `caso.json` (fonte da verdade), `processamento.json`, `registro-tratamento.md` |
| `modelos\` | Modelo DOCX oficial (timbre + assinatura) e `dados-padrao.json` |
| `calibracao\licoes-aprendidas.md` | **Ler antes de analisar ou redigir** |
| `producao\`, `rag\` | Base consolidada, painel e índice de busca (derivados; regeneráveis) |
| `plugin\investigacao-cpj\` | Fonte dos procedimentos: `commands\`, `skills\`, `agents\`, `app\` (Central CPJ) |
| `portatil\` | Os mesmos procedimentos em **um arquivo por tarefa** (gerado por `ferramentas\exportar-portatil.py`) |
| `ferramentas\` | Scripts de manutenção (verificar, atualizar, publicar, backup, exportar) |

## 3. Tarefa → o que ler → o que rodar

Leia o arquivo de `portatil\` da tarefa (autocontido). Scripts: `P = C:\CPJ - TRABALHO\plugin\investigacao-cpj\skills`.

| Tarefa | Instrução | Scripts |
|---|---|---|
| Receber PDF e extrair (OCR, MD, CSV) | `portatil\01-processar-ip.md` — ou a Central CPJ (`Central CPJ.bat`), que faz sozinha | `P\pdf-autos-policiais\scripts\diagnostico.py, extrair.py, tabelas.py, entidades.py` |
| Analisar o IP (cronologia, pessoas, caminho do dinheiro, art. 171) | `portatil\02-analisar-ip.md` | `P\base-cpj\scripts\rag.py cruzar <ID>` |
| Normalizar extratos / fluxo financeiro | `portatil\03-analista-financeiro.md` | — |
| Redigir relatório (minuta + DOCX no modelo CPJ) | `portatil\04-relatorio-ip.md` | `P\relatorio-ip-fraude\scripts\gerar_docx.py` |
| Revisar relatório contra as fontes | `portatil\05-revisar-relatorio.md` | — |
| Dar baixa / registrar entrega | `portatil\06-entregar.md` | `P\base-cpj\scripts\caso.py status <ID> entregue --origem agente` |
| Calibrar (aprender com a versão final) | `portatil\07-calibrar.md` | — |
| Pesquisar na base / cruzar CPF, Pix, conta | `portatil\08-buscar.md` | `P\base-cpj\scripts\rag.py buscar|entidade|cruzar` |
| Pesquisa OSINT (fontes abertas, lícita, com captura de prova) | `portatil\11-osint-policial.md` | — |
| Produção e painel | `portatil\09-painel.md` | `P\base-cpj\scripts\indexar.py`, `gerar_painel.py` |

Sempre que concluir uma etapa, atualize o caso com `caso.py` (status e campos) e rode `indexar.py` — isso alimenta estatística, RAG e painel.

## 4. Adaptação a outros agentes

- **Sem subagentes:** onde a instrução mandar "delegar ao agente X", execute você mesmo as instruções daquele agente (estão no arquivo portátil), em sequência.
- **Sem execução de comandos:** peça ao usuário para rodar os scripts indicados (PowerShell, `python`) e colar a saída; ou use a Central CPJ para a extração.
- **IA de chat sem acesso a arquivos:** cole o arquivo portátil da tarefa como instrução e anexe apenas os trechos necessários da transcrição (minimize dados pessoais). A minuta produzida deve seguir o formato Markdown descrito em `04-relatorio-ip.md` para depois virar DOCX com `gerar_docx.py`.
- **Modelo local (Ollama etc.):** preferível para dados sigilosos; use os mesmos arquivos portáteis.
- Ambiente: Windows, PowerShell, `python` (não `python3`). Tesseract em `C:\Program Files\Tesseract-OCR`; idioma português em `ferramentas\tessdata` (`$env:TESSDATA_PREFIX`).

## 5. Codex — skills e instruções deste projeto

- `AGENTS.md` contém as regras do workspace; para desenvolvimento, leia também `PRD.md`.
- As skills descobertas pelo Codex ficam em `.agents\skills\cpj-*\SKILL.md`: `cpj-processar-ip`, `cpj-analisar-ip`, `cpj-analista-financeiro`, `cpj-relatorio-ip`, `cpj-revisar-relatorio`, `cpj-entregar`, `cpj-calibrar`, `cpj-buscar`, `cpj-painel`, `cpj-fluxo-completo` e `cpj-desenvolver`. Cada skill aponta para a versão viva do procedimento em `portatil\`; scripts, referências e modelo continuam nas pastas originais.
- Pode invocar por `$cpj-analisar-ip OS-123-2026`, por exemplo, ou pedir a tarefa em linguagem natural. A skill pessoal `cpj-projeto`, instalada em `%USERPROFILE%\.agents\skills\`, localiza as instruções quando a tarefa começou fora desta pasta.
- Regerar adaptadores: `python ferramentas\configurar-codex.py`. Instalar também a entrada pessoal: acrescente `--instalar-usuario` ou use `ferramentas\Configurar Codex.bat`. Conferir sem alterar: `python ferramentas\configurar-codex.py --instalar-usuario --verificar`.
- Não se instala um conector nem se troca o executor automático da Central. Os procedimentos continuam compatíveis com os outros agentes.
- **Sigilo no Codex:** scripts locais não tornam a inferência do modelo local. A instalação destas skills não comprova compatibilidade da conta com a regra 6. Não carregue autos reais, imagens, transcrições ou resultados identificáveis no contexto de um modelo externo; use o fluxo local autorizado pelo órgão. Para manutenção, use código, procedimentos e dados fictícios.
