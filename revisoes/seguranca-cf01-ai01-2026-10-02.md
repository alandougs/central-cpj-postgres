# Revisão CF01/AI01 — evidência recuperada em 09/10/2026

O arquivo desta entrega estava com zero bytes. A AG03 foi reaberta pela fila e este parecer substitui a ausência de evidência; não recupera nem confirma a execução histórica de 02/10. Revisão somente do código, sem leitura de configuração real, chaves, contas ou autos e sem chamadas reais aos provedores. Os números de linha referem-se ao levantamento de 09/10 e podem mudar na integração.

## Achados e propostas

| Severidade | Achado documentado no código | Proposta de tarefa |
|---|---|---|
| Alta | `rotas/sistema.py`, `api_sistema_llm_post`, grava `chaves_llm.json` com `json.dump`, sem cifra; `executores_llm.configuracao` lê a chave diretamente | Proteger credenciais em repouso e gravação atômica, mantendo chave mascarada na API; testes com credenciais fictícias |
| Alta | `plantao._executar_sessao` transforma consentimento ausente em `destinos_aceitos=None`; `executores_llm.rotear` só filtra destinos quando o argumento não é `None` | Bloquear execução externa sem consentimento válido no executor, inclusive pedidos antigos/importados; testar ausência, vazio e destino não aceito |
| Alta | `rotas/sistema.api_ia` verifica consentimento apenas para nomes começando com `api`; não aplica o mesmo gate aos CLIs com inferência em nuvem | Aplicar o contrato PX01 a cada executor externo; manter exceções de scripts locais e sessão de chat |
| Alta | `api_ia` enfileira antes de atualizar a coluna de consentimento; pedido da esteira retorna um ID, mas os demais filhos são criados antes dessa atualização | Persistir consentimento junto com criação/reserva e propagá-lo a todas as etapas, para evitar execução antes do aceite |
| Média | `api_ia` aceita do cliente `usuario`, `data_hora` e `destinos` sem validação estrutural robusta; consentimento de tipo errado pode provocar erro 500 | Gerar identidade/data no servidor e validar tipo, escopo e destinos autorizados |
| Média | Prompt editável é anexado ao system prompt; limites de ferramentas são gerais por caso e não por etapa | Preservar regras mandatórias e limitar efeitos de cada etapa; conferir as correções RV17 do `main` antes de adicionar outro mecanismo |

Estes itens são propostas da revisão AG03, sem correção de código nesta tarefa. A CL02 está reservando `plantao.py`; não se edita o arquivo concorrentemente. O orçamento CX03 não resolve os achados de consentimento.

## Controles observados e limites

Catálogos e endpoints de trabalho usam URLs fixas no código para os provedores conhecidos. Não foi encontrado campo de URL arbitrária neste caminho, portanto não há evidência de SSRF configurável nessa interface. O catálogo transmite a chave em cabeçalho e não incorpora conteúdo do caso. Não foi feito teste de redirecionamento externo.

Rotas de alteração de chaves e configuração usam `@requer("usuarios")`; leitura mascarada usa `@requer("ia")`. A gravação de auditoria da configuração inclui o nome do provedor, sem a chave. `_http_json` não devolve corpo de erro HTTP, e o fallback substitui a chave na mensagem. A revisão não leu logs de produção e não pode afirmar ausência de vazamento histórico.

Os testes de segurança/mode solo executados neste loop tiveram retorno zero no runner isolado. O diagnóstico completo já apontou falha de sintaxe em `teste_consentimento_externo_px01.py`; esse arquivo não comprova o gate. Endpoints e provedores ativos em produção não foram consultados. A revisão de segurança é parcial e não constitui homologação.

## Evidência reproduzível

Comandos usados: `Get-Item revisoes/seguranca-cf01-ai01-2026-10-02.md` (Length=0 antes da recuperação), `rg -n` dos caminhos de configuração/consentimento/HTTP e leitura das funções citadas. Runner: `ferramentas/testar-tudo.py --rapido --incluir teste_importacao_codex.py`, com Python 3.12.14 do runtime Codex e bibliotecas locais via `PYTHONPATH`: 5/5 suítes aprovadas em 87,49 s. A suíte completa permanece em execução e seus resultados serão registrados separadamente.
