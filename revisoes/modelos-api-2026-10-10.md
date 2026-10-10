# AI03 — catálogos e seleção de modelos

Implementados nove cartões: oito APIs e Copilot CLI, incluindo xAI. Cada campo permite escolher no catálogo ou digitar manualmente. “Consultar modelos” chama o backend existente, enviando somente chave e metadados ao provedor; não salva, ativa, altera executor, tarifa, orçamento ou consentimento. A consulta não inclui prompt ou autos.

Sem modelo preenchido nem edição manual, a resposta dinâmica pode sugerir o identificador equilibrado exato presente no catálogo textual. Erro, catálogo vazio/incompleto, modelo desconhecido ou metadados explicitamente incompatíveis não geram sugestão. Modelo salvo, digitado ou apagado manualmente — inclusive enquanto a consulta está pendente — permanece intacto. A escolha só é persistida pelo botão Salvar.

Os candidatos abaixo foram conferidos em fontes primárias em 10/10/2026. São uma seleção editorial para equilíbrio, condicionada ao catálogo retornado e à compatibilidade explícita; não uma comprovação de acesso ou inferência na conta do usuário.

| Provedor | Candidato exato | Fonte primária |
|---|---|---|
| OpenAI | `gpt-6.1-sol` | [OpenAI Docs](https://developers.openai.com/api/docs/models/gpt-6.1-sol) |
| Anthropic | `claude-sonnet-5-5` | [Claude Sonnet 5.5](https://platform.claude.com/docs/en/models/sonnet-5-5/overview) |
| Gemini | `gemini-3.8-flash` | [Gemini 3.8 Flash](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash) |
| DeepSeek | `deepseek-flash` | [Modelos DeepSeek](https://api-docs.deepseek.com/quick_start/pricing/) |
| xAI | `grok-4.7` | [Grok 4.7](https://docs.x.ai/developers/models/grok-4.7) |
| Groq | `openai/gpt-oss-120b` | [Groq GPT OSS 120B](https://console.groq.com/docs/model/openai/gpt-oss-120b) |
| NVIDIA NIM | `nvidia/llama-3.3-nemotron-super-49b-v1.5` | [NVIDIA API](https://docs.api.nvidia.com/nim/reference/nvidia-llama-3_3-nemotron-super-49b-v1_5-infer) |
| OpenRouter | `openai/gpt-6.1-sol`, depois `anthropic/claude-sonnet-5.5`, somente se retornados e compatíveis | [OpenRouter](https://openrouter.ai/compare/anthropic/claude-sonnet-5.5/openai/gpt-6.1-sol) |
| Copilot CLI | sem sugestão automática; `claude-sonnet-5.5` é o padrão documentado, GPT-6.1 Sol exige seleção explícita | [Referência Copilot CLI](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference) |

Metadados `active: false`, ciclo deprecated/retired, saída sem texto, OpenRouter sem `tools` nos parâmetros publicados e negativa explícita de tool/function calling impedem a sugestão, mesmo para identificador conhecido. Não se deduz capacidade de visão a partir do nome. A lista do Copilot é documental e avisa que o acesso da conta deve ser confirmado no CLI; não executa o CLI nem seleciona automaticamente GPT.

Paginação Anthropic e Gemini segue [after_id/has_more](https://platform.claude.com/docs/en/api/models/list) e [pageToken/nextPageToken](https://ai.google.dev/api/models), com cursor codificado, limite de dez páginas e recusa de cursor ausente/repetido ou limite atingido. Um catálogo incompleto não é usado como sucesso parcial.

TDD reproduziu dezessete falhas/subfalhas iniciais, quatro de incompatibilidade explícita, uma do prefixo Gemini no veto e uma da limpeza manual em consulta pendente. Após correções, treze testes passaram em 0,255 s, incluindo rota Flask com chave fictícia/configuração byte a byte preservada, mocks de paginação e QuickJS executando o comportamento do formulário e compilando todos os scripts HTML. A revisão independente do integrador também verificou CF01 e a interface de consentimento. A regressão rápida final, em snapshot estável após a última correção, passou: cinco de cinco suítes em 93,42 s, incluindo treze testes AI03 em 2,58 s. Uma rodada intermediária capturou o teste Gemini novo antes do patch correspondente (4/5 em 102,52 s); não foi usada como homologação.

Chrome headless em clone de código genérico e workspace/APPDATA fictícios: doze cenários aprovados, nove cartões, sete sugestões API, modelo legado preservado, digitação/limpeza manual preservadas e Copilot sem seleção automática. Configuração permaneceu byte a byte igual; só ocorreram POSTs locais ao endpoint de catálogo. Chamadas HTTP externas foram bloqueadas; zero erros de console/página. Imagens claro/escuro foram inspecionadas. Browser e servidor próprios foram encerrados em finally.

Evidências: `C:/Users/alan_/AppData/Local/Temp/cpj-ai03-before-20261010` (snapshots, logs TDD e `rapida-estavel.log`); `C:/Users/alan_/AppData/Local/Temp/cpj-ai03-visual-7ryqohd6` (`resultados.json`, `dom.json`, `server.log`, `catalogos-dark.png`, `catalogos-light.png`). Nenhuma chave real, configuração real, caso real ou API de inferência foi usada. A disponibilidade real por conta, tarifas, inferência, visão e CI remota não foram testadas. O cache do plugin 0.3.0 antecede AI03 e precisa de atualização posterior pelo integrador.
