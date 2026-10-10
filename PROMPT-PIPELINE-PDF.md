# PROMPT — Completar o pipeline de PDF do ASTRA (tarefas PX01–PX07)

> Aprovado pelo investigador em 07/10/2026. Vale para qualquer agente (Codex, Claude, Gemini/Antigravity, Copilot).
> ASTRA é o nome da interface da Central CPJ (`plugin/investigacao-cpj/app/`). Não há outro sistema.

Você vai completar o pipeline de processamento de PDF do ASTRA **implementando somente o que falta**. O pipeline local já existe e funciona: não o reescreva, não o substitua e não mude o formato dos arquivos que ele produz.

## 0. Antes de começar (obrigatório)

1. Leia `AGENTS.md` (seção 1, principalmente regras 2, 3, 5, 6 e 16), `PRD.md` (§3 e §9), as skills `.agents/skills/scope-guard/SKILL.md` e `.agents/skills/no-gold-plating/SKILL.md` e a seção "07/10/2026 — pipeline de PDF" de `TAREFAS-COMPARTILHADAS.md`.
2. Trabalhe em loop pela fila, uma tarefa por vez:
   - `python ferramentas\fila-tarefas.py proxima --prefixo PX` → saída 0 = ID livre; 3 = acabou; 4 = só restam tarefas bloqueadas (aguarde ou encerre).
   - `python ferramentas\fila-tarefas.py assumir <ID> --agente <nome-da-sessao>`. Se recusar, não force.
   - Edite **só** os arquivos reservados na linha da tarefa. Defeito fora do escopo vira uma linha no relato final.
   - Ao terminar: `python ferramentas\fila-tarefas.py concluir <ID> --agente <nome> --resultado "arquivos; comandos; resultado dos testes"`. Se parar: `liberar` com o ponto de retomada.
3. Somente dados fictícios e workspace temporário (`CPJ_WORKSPACE`). Nunca abra `casos\`, `config\` (inclusive `config\chaves_llm.json`), `consulta\` nem `ordens-de-servico\`. **Nenhuma chamada real a provedor de IA nos testes:** simule com monkeypatch de `executores_llm._http_json` ou servidor HTTP fictício em `127.0.0.1`. Não pare nem reinicie a Central real (porta 8765).
4. Validação de cada tarefa: o teste próprio da tarefa isolado + `python ferramentas\testar-tudo.py --rapido`. Só afirme sucesso com a saída do comando à vista. Sem commit e sem push.

## 1. O que JÁ EXISTE — não reimplementar

| Etapa | Onde | O que faz |
|---|---|---|
| Orquestração do botão "Processar PDF" | `app/rotas/comum.py` (função de processamento, ~l. 355–425) | diagnóstico → `extrair.py` → `tabelas.py` (PDF e MD) → `entidades.py` → `dados_json.py` → `caso.py ip` → `registro-tratamento.md` |
| Validação, páginas, digital/escaneado/misto | `skills/pdf-autos-policiais/scripts/diagnostico.py` | SHA-256, contagem, páginas sem texto, erro ao abrir (senha **ou** corrompido, sem distinguir) |
| Texto nativo, OCR seletivo, confiança, método por página | `scripts/extrair.py` | pypdfium2; Tesseract `por` só onde falta texto; `confianca_media`; `--conf-min 75`; página com pouco texto + imagem grande → OCR da imagem + "conferir"; carimbos e-SAJ ignorados na medição; checkpoints v2 por página; reaproveitamento por hash entre casos; PNG em `paginas_visao/` para pendentes/conferir; **`transcricoes_visuais/pNNNN.md` prevalece sobre OCR ao rodar de novo** |
| Tabelas | `scripts/tabelas.py` | pdfplumber com e sem bordas; tabelas Markdown da transcrição; CSV com `pagina_pdf` |
| Entidades e JSON consolidado | `scripts/entidades.py`, `scripts/dados_json.py` | `entidades.csv`; `dados_extraidos.json` (`cpj-dados-extraidos/1`) |
| Saídas | `01-extracao/<doc>/` | `transcricao.md` (`## Página N` + `<!-- método: … -->`), `tabelas/*.csv`, `relatorio_extracao.json`, `diagnostico.json`, `dados_extraidos.json` |
| Provedores, catálogo de modelos, fallback | `app/executores_llm.py`, `app/rotas/sistema.py` | 8 provedores; `provedores_api_configurados()` e `executar_com_fallback()` tentam em ordem; chave ocultada nas mensagens; catálogo consulta só com a chave |

Fora desta rodada (decisão de 07/10/2026): detecção de layout/ordem de leitura com bibliotecas pesadas (docling, layoutparser etc. — contraria a premissa 9 do PRD) e extração de imagens embutidas (o PNG da página já cobre a necessidade).

## 2. Regras que mandam em todas as tarefas

- **Local first.** IA só para a página que a avaliação local reprovar (ou em todas, no modo IA Completa escolhido pelo operador). Nunca enviar o PDF inteiro; enviar só o PNG da página necessária.
- **Consentimento antes de sair do computador (PX01).** Nenhum conteúdo de caso sai do computador sem o aceite registrado do operador para aquele pedido e aqueles provedores. O servidor bloqueia o envio sem aceite: o aviso na tela, sozinho, não é proteção.
- **Rastreabilidade.** Toda transcrição vinda de IA fica marcada com origem (provedor/modelo, data e hora), entra como "conferir" e mantém `## Página N`. A página nunca perde o texto nativo/OCR já obtido.
- **Dígitos (regra 3).** O prompt de transcrição manda o modelo usar `?` e `[dígito incerto]` em qualquer dígito duvidoso de CPF, conta, chave Pix, placa, telefone ou valor, e nunca completar nada por dedução.
- **Originais (regra 5).** `00-originais` e `transcricao.md` gerado pela extração não são editados por normalização; o que for normalizado vai para arquivo derivado.
- **Compatibilidade.** Não mude o formato de `transcricao.md`, `relatorio_extracao.json`, dos CSV nem a assinatura dos checkpoints do `extrair.py` (mudar a assinatura obrigaria refazer o OCR de todos os casos).

## 3. Tarefas

### PX01 — Aviso de processamento fora do ambiente local (Aceitar / Não aceitar)

**Quando aparece (quando aplicável):** sempre que uma ação da Central for enviar conteúdo de caso a um processamento cuja inferência ocorre fora deste computador:
- pedido de IA (análise, relatório, revisão, financeiro, esteira) executado por provedor de API (modo API em Sistema → Configurações);
- pedido destinado a agente automático cuja inferência roda na nuvem (Claude/Codex/Gemini por CLI);
- transcrição visual por API (PX05) e modo IA Completa (PX06).

Não aparece para: scripts locais (diagnóstico, OCR Tesseract, tabelas, entidades, JSON), modo Rápido, consulta ao catálogo de modelos (só envia a chave) e modo sessão de chat (o operador copia o prompt por conta própria).

**Tela (modal):** título "PROCESSAMENTO FORA DO AMBIENTE LOCAL". Texto informando: o caso (O.S.), o que será enviado (ex.: "arquivos de extração do caso" ou "imagens das páginas 12, 15 e 40 — 3 páginas"), **todos** os destinos possíveis na ordem de fallback (provedor/modelo ou agente), e a frase: "O conteúdo sairá deste computador e será processado pelo serviço indicado. Confirme que o uso atende ao sigilo do inquérito (art. 20 do CPP) e às normas do órgão." Botões **Aceitar** e **Não aceitar**; foco inicial e tecla Esc em "Não aceitar". Sem opção "não perguntar de novo".

**Não aceitar:** nada é enviado. Pedido de IA: não é enfileirado (ou fica restrito a executor local, se houver) e a tela informa. Transcrição visual: as páginas continuam pendentes para transcrição local/manual, como hoje.

**Servidor (obrigatório):** a rota que enfileira devolve `requer_consentimento: true` + `destinos` quando aplicável; o pedido só é criado com `consentimento_externo = {usuario, data_hora, destinos, escopo}` gravado nele. Antes de **qualquer** chamada HTTP com conteúdo de caso, `executores_llm` confere se o provedor está entre os destinos aceitos; se o fallback chegar a um provedor não aceito, ele é pulado e a falha registrada. Aceite e recusa vão para `config\auditoria.log` e para o `registro-tratamento.md` do caso (sem chave de API).

**Teste próprio** `teste_consentimento_externo_px01.py`: (a) pedido em modo API sem aceite → recusado e nenhuma chamada HTTP; (b) com aceite → executa só nos destinos aceitos; (c) fallback para provedor não aceito → pulado; (d) recusa registrada em auditoria; (e) modo agente local/scripts → sem aviso; (f) `index.html` contém o modal com os dois botões e sem URL externa.

### PX02 — Roteador de IA: capacidades, nova tentativa, saúde e prioridade

Estender `executar_com_fallback`/`provedores_api_configurados` (não criar um segundo sistema; manter as assinaturas atuais funcionando). Interface única para o resto do sistema, ex.: `rotear(ws, capacidades={"vision"}, executor=..., destinos_aceitos=...)`.
- **Capacidades** por provedor/modelo: `text`, `vision`, `json`, `structured_output`, `pdf` — tabela local + dados do catálogo quando o provedor informa (ex.: `input_modalities` do OpenRouter). Pedido que exige `vision` só vai a modelo com `vision`; sem nenhum, erro claro ("nenhum provedor com visão configurado").
- **Nova tentativa limitada:** 1 nova tentativa com espera curta em 429, 5xx e timeout; nenhuma em 400/401/403 (vai direto ao próximo).
- **Timeout configurável** (padrão atual 90 s) e **prioridade configurável** (ordem salva em `config\ia.json`, editável em Configurações).
- **Saúde:** verificação usando só a chave (o catálogo de modelos já faz isso), com resultado em cache por alguns minutos; provedor fora do ar vai para o fim da fila naquela rodada.
- Respeita o aceite do PX01 em toda tentativa.

**Teste** `teste_roteador_px02.py`: seleção por capacidade, ordem configurada, nova tentativa só nos códigos certos, timeout, provedor sem saúde pulado, chave nunca aparece em mensagem/log.

### PX03 — Avaliação de qualidade por página (local, sem IA)

Novo `skills/pdf-autos-policiais/scripts/qualidade.py <pasta-extracao> [--pdf arquivo.pdf]` → grava `qualidade.json` e **não altera** `extrair.py` nem os demais arquivos. Por página: `categoria` (`digital` | `escaneada` | `hibrida` | `complexa`), `pontuacao` 0–100, `motivos[]` e `precisa_ia` (bool). Combine sinais, sem regra única: caracteres úteis (sem carimbos — reutilize o mesmo critério do `extrair.py`), confiança do OCR, proporção de caracteres inválidos (`�`, controle, símbolos soltos), fragmentação (média de caracteres por linha, proporção de tokens de 1 caractere), fração da página ocupada por imagem, tabela detectada pelo pdfplumber com colunas inconsistentes, e as listas `pendentes_transcricao_visual`/`conferir_visualmente` já existentes. Limiares em constantes nomeadas no topo do arquivo.

**Teste** `teste_qualidade_px03.py` com PDFs fictícios gerados no teste: página digital limpa → não precisa de IA; página só imagem → precisa; texto com muitos `�`/fragmentado → precisa; página digital com tabela bem lida → não precisa.

### PX04 — Diagnóstico: distinguir PDF protegido de corrompido

Em `diagnostico.py`, separar "protegido por senha/criptografia" de "arquivo corrompido ou não é PDF" (códigos de erro do pdfium), mantendo a chave `erro` (a Central já depende dela) e acrescentando `motivo_erro`: `senha` | `corrompido` | `desconhecido`. Mensagem clara para o operador em cada caso. **Teste** `teste_diagnostico_px04.py` com PDF fictício cifrado (pypdf) e arquivo truncado.

### PX05 — Transcrição visual por API (multimodal) das páginas reprovadas

Novo `scripts/transcrever_visual.py <pasta-extracao> --paginas ...` chamado pela Central depois da extração local:
1. Páginas candidatas = `pendentes_transcricao_visual` ∪ `conferir_visualmente` ∪ `precisa_ia` do `qualidade.json`.
2. Pede o aceite do PX01 (mostrando quantas páginas e quais destinos). Recusou → nada é enviado.
3. Envia **só o PNG** de cada página (`paginas_visao/`) pelo roteador com `vision`; prompt de transcrição com as regras da skill `pdf-autos-policiais` (tabelas em Markdown, `?` em dígito incerto, nada inventado, "[ilegível]" quando não der para ler).
4. Grava `transcricoes_visuais/pNNNN.md` com primeira linha `<!-- origem: api <provedor>/<modelo> em <data-hora>; conferir -->`. Não sobrescreve transcrição visual já existente feita por agente/operador.
5. Roda de novo `extrair.py` (os checkpoints evitam novo OCR) e depois `tabelas.py` sobre a transcrição, `entidades.py` e `dados_json.py`, exatamente como a Central já faz.
6. Registra no `registro-tratamento.md`: páginas enviadas, provedor/modelo usado em cada uma, falhas.

Na Central: ao fim do processamento local, se houver páginas candidatas e provedor com visão ativo, mostrar "N página(s) precisam de leitura por IA" com o aviso do PX01. Atualizar `skills/pdf-autos-policiais/SKILL.md` e `portatil/01-processar-ip.md` (passo 3) para mencionar a opção por API sem remover o caminho atual por agente. **Teste** `teste_transcricao_visual_px05.py` com provedor simulado: só as páginas candidatas são enviadas, só PNG, marcação de origem, sem aceite nada sai, transcrição existente preservada, reprocessamento sem novo OCR.

### PX06 — Modos de processamento: Rápido, Inteligente (padrão), IA Completa

Seletor ao lado de "Processar PDF" (padrão vindo de Configurações; padrão de fábrica **Inteligente**):
- **Rápido:** pipeline local atual, sem PX05, nunca pede aceite.
- **Inteligente:** pipeline local + PX03 + PX05 só nas páginas reprovadas.
- **IA Completa:** pipeline local + PX05 em todas as páginas; o aviso do PX01 aparece **antes de começar**, informando o total de páginas.

O modo usado fica em `processamento.json` e em `registro-tratamento.md`. **Teste** `teste_modos_px06.py`: cada modo chama (ou não) a etapa de IA e o aviso, com provedor simulado.

### PX07 — Normalização em arquivo derivado (opcional, por último)

Novo `scripts/normalizar.py <pasta-extracao>` → `transcricao-normalizada.md` + `normalizacao.json` (o que mudou, por página). `transcricao.md` continua sendo a fonte citada. Pode: juntar hifenização de fim de linha; reduzir linhas em branco; remover carimbos e-SAJ repetidos (mesmo critério do `extrair.py`); **na mesma página**, remover do bloco "[OCR da imagem da página]"/"[Transcrição visual complementar]" as linhas idênticas ao texto nativo daquela página. **Proibido:** remover linhas repetidas entre páginas diferentes, linhas de tabela ou lançamento financeiro (dois Pix iguais são dois fatos), alterar qualquer dígito, reordenar texto. **Teste** `teste_normalizacao_px07.py`, incluindo dois lançamentos idênticos que devem permanecer.

## 4. Relato final (até 10 linhas)

Tarefas concluídas (arquivos, testes e resultado), liberadas (com motivo), achados fora do escopo e o que depende do investigador (ex.: ativar provedor com visão em Configurações).
