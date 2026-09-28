# Ambiente de Investigação CPJ — guia rápido

## Guia de uso de amanhã (29/09/2026)

1. Duplo clique em `Central CPJ.bat` — abre `http://127.0.0.1:8765` direto na Central (sem senha, modo solo).
2. **Nova O.S.** → preencha O.S./BO/IP/processo (o que faltar é detectado no PDF) → arraste o PDF do IP → *Processar PDF*. Acompanhe o OCR em *Tarefas* e na ficha do caso.
3. Caso pronto (extraído): na ficha do caso, clique no botão de IA (*Analisar*, *Gerar relatório* ou *Análise + relatório*) — ou, no Claude Code, `/fluxo-ip OS-<número>`.
4. Edite a minuta gerada (*Casos* → abra o caso → *Editar minuta*) e gere o DOCX no modelo CPJ 2026 (timbre e assinatura).
5. Confira o DOCX e clique em **Definir FINAL** — isso registra a entrega (baixa) e atualiza o painel de *Estatísticas*.

**Modo solo:** ativo quando existe `config\solo.json` com `{"ativo": true}` — a Central abre direto como o único administrador, sem tela de login, só em `127.0.0.1`/`localhost`. Para desligar, apague o arquivo ou troque `ativo` para `false` e reabra a Central.

**Onde ficam os arquivos:** cada O.S. vira `casos\OS-<número>\` — `00-originais` (PDF enviado, nunca alterado), `01-extracao\` (transcrição em Markdown por página e tabelas em CSV), `02-analise\` (cronologia, pessoas, financeiro), `03-relatorios\` (minutas, DOCX e o FINAL). O relatório FINAL também chega na sua pasta pessoal (Central → Sistema → *Minha pasta*).

**Se o OCR falhar ou travar:** reabra a ficha do caso e use *reprocessar* no documento com erro (em *Casos* → detalhe → Processamento); confira em `Sistema → Tarefas` a mensagem de erro. Persistindo, rode `ferramentas\Verificar ambiente.bat` para checar se o Tesseract e o idioma português estão instalados.

**Se o botão de IA não sair do lugar:** confira em Sistema → *Inteligência artificial* se há algum agente **ocioso e aprovado**; fora do expediente (seg-sex 9h-18h) o pedido só fica na fila — peça pelo chat do Claude Code para atender na hora, ou aguarde o próximo expediente.

## Dia a dia

1. **Abra a Central CPJ:** duplo clique em `Central CPJ.bat` (abre `http://127.0.0.1:8765` no navegador) e entre com seu usuário (login, CPF, nome completo ou e-mail). Senha temporária exige troca no primeiro acesso.
2. **Nova O.S.:** informe a O.S. (e BO, IP, processo), arraste o PDF do IP (ou MD/CSV) e clique em *Enviar e processar*. A Central cria `casos\OS-<número>\` e faz sozinha: diagnóstico, OCR, Markdown por página, tabelas em CSV, dados críticos e indexação. Acompanhe a barra de progresso em *Tarefas*.
3. **Pela Central, com IA:** na ficha do caso, os botões *Analisar*, *Gerar relatório*, *Análise + relatório* e *Revisar* criam um pedido na fila do **plantão**. O agente ocioso e aprovado pega o pedido, informa o progresso e deixa a minuta e o DOCX no caso (veja *Agentes de plantão* abaixo).
4. **Ou no Claude Code** (análise e relatório):
   - `/processar-ip OS-123-2026` — só se houver páginas pendentes de transcrição visual (a Central avisa).
   - `/analisar-ip OS-123-2026` — cronologia, pessoas, caminho do dinheiro, conexões com outros IPs.
   - `/relatorio-ip OS-123-2026 [suas diligências/observações]` — minuta revisada + DOCX no modelo CPJ (timbre e assinatura).
   - `/entregar OS-123-2026` — registra a produção (depois de revisar/entregar o DOCX).
   - `/calibrar OS-123-2026` — o sistema aprende com as suas correções (com sua aprovação).
5. **Consultas:** Central → *Casos* (O.S., BO, IP, processo, partes), *Pesquisa* (texto; CPF, chave Pix, conta; pesquisa relacional por nome, mãe, pai, telefone, CNPJ, endereço, BO, processo, placa, mandado e cautelar; *vínculos* entre pessoas, contas e casos), *Estatísticas* (dia/mês/ano × meta e KPIs), *Início* (pendências e prazos).

Atalho: `/fluxo-ip OS-123-2026` faz análise → relatório com paradas para aprovação. Outros: `/buscar`, `/painel`, `/revisar-relatorio`.

## O que é fonte e o que é apoio

- **Fonte dos fatos do relatório:** somente os documentos do próprio caso (IP e peças enviadas).
- **Bases de consulta** (Central → Sistema → *Bases de consulta*: Muralha Paulista, fichas de sistemas, em Excel, CSV, Word, PDF, TXT ou texto colado): servem **só para pesquisa**. Mandados e cautelares aparecem com a situação (confirmado, indeterminado, histórico, negado) e o trecho original, para você conferir.
- **Relatórios de referência** (Central → Sistema → *Relatórios de referência*): relatórios anteriores seus ou de colegas, com autor e peso (5 = exemplar). A IA usa só como exemplo de estilo e estrutura, priorizando o seu estilo e os pesos altos.
- **Pessoas dos autos:** a análise grava `02-analise\pessoas.csv`; é isso que alimenta a Pesquisa relacional com as pessoas dos seus casos.

## Agentes de plantão

Um ou mais agentes ficam de alerta e atendem os botões de IA da Central, um pedido por vez, sem dois pegarem o mesmo.

- **Agente embutido:** a Central inicia o seu próprio agente (Claude) quando o Claude Code está com login feito (`claude auth login`).
- **Agente adicional:** duplo clique em `ferramentas\Agente de plantao.bat` (escolha Codex ou Claude), ou cole `PROMPT-AGENTE-PLANTAO.md` numa sessão de chat do agente.
- Agente novo entra como *aguardando aprovação*: aprove ou revogue em Central → Sistema → *Agentes de plantão*. Ao acionar a IA no caso, você pode escolher um agente específico ou deixar para o primeiro ocioso.
- Pedido de agente que parou de responder volta para a fila (até 2 tentativas); *Cancelar* na Central é respeitado pelo agente.
- **Expediente (economia):** os agentes só pegam pedidos de **segunda a sexta, das 9h às 18h**. Fora disso o botão continua criando o pedido, mas ele fica na fila (a barra mostra quando os agentes voltam) e nenhum token é gasto. Precisa agora? Acione pelo chat: peça ao agente para atender o pedido (ele usa `aguardar --forcar`) ou peça a análise/relatório diretamente. Um pedido já em execução às 18h termina normalmente.
- Para mudar o horário ou incluir feriados, edite `config\plantao.json` (`expediente`: `dias` 0=seg … 6=dom, `inicio`, `fim`, `feriados` no formato AAAA-MM-DD; `ativo: false` desliga o controle). Conferir: `python ferramentas\agente-plantao.py expediente`.

## Pastas

- `casos\OS-...\` — `00-originais` (somente leitura), `01-extracao\<documento>\`, `02-analise`, `03-relatorios`, `caso.json`, `processamento.json`, `registro-tratamento.md`.
- `modelos\` — modelo DOCX e `dados-padrao.json` (preencha `delegado_padrao`).
- `producao\` — `painel.html`, `base.csv` (Excel), `config.json` (meta mensal).
- `rag\` — índice de busca local. `calibracao\` — lições aprendidas. `acervo\` — base de conhecimento. `plugin\` — plugin e Central.

## Ferramentas (pasta `ferramentas\` — dê duplo clique no `.bat`)

| Atalho | Para quê |
|---|---|
| `Verificar ambiente.bat` | Checa Python, bibliotecas, OCR português, modelo DOCX, delegado padrão, plugin, Git e Central |
| `Backup.bat` | Cópia de segurança (casos, calibração, produção, modelos) para a pasta que você indicar; nunca apaga no destino |
| `Atualizar plugin.bat` | Depois de editar o plugin: sobe versão, valida, reinstala e regera `portatil\` |
| `Publicar no GitHub.bat` | Mostra o que mudou, faz varredura de segurança (bloqueia dados de caso) e só envia se você confirmar |
| `exportar-portatil.py` | Regera `portatil\` (procedimentos para outros agentes) |

## Sem Claude? Outros agentes

`AGENTS.md` (Codex, Antigravity etc.) e `GEMINI.md` trazem as regras e o mapa das tarefas. Em `portatil\` há um arquivo autocontido por tarefa, que também serve para colar em qualquer IA de chat. A Central CPJ e os scripts funcionam sem nenhuma IA.

## Usar no Codex

Abra este projeto (`C:\CPJ - TRABALHO`) no Codex. Há onze skills locais em `.agents\skills\`, com descoberta automática e invocação explícita:

| Pedido | Skill |
|---|---|
| Receber/extrair material | `$cpj-processar-ip` |
| Analisar IP | `$cpj-analisar-ip` |
| Caminho do dinheiro | `$cpj-analista-financeiro` |
| Minuta e DOCX CPJ | `$cpj-relatorio-ip` |
| Revisar relatório | `$cpj-revisar-relatorio` |
| Registrar entrega informada | `$cpj-entregar` |
| Aprender com correções | `$cpj-calibrar` |
| Pesquisar/cruzar na base | `$cpj-buscar` |
| Produção e painel | `$cpj-painel` |
| Fluxo do recebimento ao DOCX | `$cpj-fluxo-completo` |
| Manter Central/plugin/scripts | `$cpj-desenvolver` |

Exemplo de manutenção: `Use $cpj-desenvolver para verificar o próximo passo do PRD e testar com dados fictícios.` Nos pedidos operacionais, informe o ID do caso e use somente ambiente compatível com o sigilo.

Duplo clique em `ferramentas\Configurar Codex.bat` recria os adaptadores e instala a skill pessoal `$cpj-projeto` em `%USERPROFILE%\.agents\skills\`. Ela aponta para as instruções deste workspace, sem copiar autos. Se as skills não aparecerem, reinicie o Codex. Conferência local: `python ferramentas\configurar-codex.py --instalar-usuario --verificar`.

Os adaptadores leem os procedimentos vivos de `portatil\`. Ao editar procedimentos no plugin, rode `python ferramentas\exportar-portatil.py`. Ao editar a integração Codex, altere `ferramentas\configurar-codex.py` e execute novamente; não edite os arquivos gerados.

**Sigilo:** executar Python neste PC não torna o modelo do Codex local. Skills são instruções, não uma garantia de conta autorizada ou de processamento sem transmissão. Preserve a regra 6 de `AGENTS.md`: conteúdo de autos reais fica no fluxo local autorizado; manutenção no Codex usa procedimentos, código e dados fictícios.

Formato e descoberta seguem a [documentação oficial de skills do Codex](https://learn.chatgpt.com/docs/build-skills); instruções do workspace seguem [AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md).

## Regras de ouro

Tudo é minuta: você confere e assina. Dado crítico só vai à conclusão depois de conferido na imagem da página. A Central roda só neste computador; nada de conteúdo de caso sai daqui por iniciativa da IA.
