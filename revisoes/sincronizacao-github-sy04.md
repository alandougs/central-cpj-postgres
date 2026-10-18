# SY04 — sincronização estrutural do GitHub

Autorização: corrigir pendências e sincronizar a estrutura do sistema no GitHub, sem dados reais dos casos; instalação e migração expressamente excluídas. Continuação do plano canônico UN18 na cópia de desenvolvimento `codex/unificacao-cpj`.

## Correção reproduzida

`teste_identidade_form_codex.py`: oito subfalhas na revisão publicada; os formulários não tinham seleção de cargo, máscara de CPF ou autocomplete de nome. O teste estático de helpers ainda examinava o HTML anterior à modularização. Dois testes Edge acrescentados falharam pela ausência de `selecionarCargo` antes da implementação.

Correção: seletor de cargos com opção personalizada; carregamento e envio dos três formulários preservam o valor personalizado; reset limpa o campo auxiliar; CPF recebe somente formatação visual e limite de 11 dígitos, sem inferir ou completar identificadores. Testes estáticos leem o módulo JS real. Resultado dirigido: 6 testes aprovados, incluindo dois no Edge com dados fictícios.

## Publicação e preservação

- Iniciador genérico `ferramentas/Abrir ASTRA.bat` versionado. Ícones pessoais ficam locais e ignorados; nenhum arquivo local foi apagado.
- As três branches locais de editor, DOCX e progresso passaram individualmente em `verificar-publicacao.py --ref` sem achados proibidos. Os commits serão preservados em branches remotas próprias; suas funcionalidades já estão integradas, com adaptações, à candidata. Não reaplicar patches antigos sobre os módulos atuais.
- A candidata e a branch atual passaram no verificador de publicação; nenhuma pasta de casos reais, banco, configuração operacional, credencial, assinatura ou documento real foi identificada. A auditoria adicional do histórico de branches e PRs remotos (21 referências) examinou 1.083 blobs: somente os três dados genéricos de Tesseract abaixo foram sinalizados. A verificação dos objetos locais também encontrou snapshots internos do Codex com material operacional; essas referências são exclusivamente locais e não foram publicadas. Os pushes nomeiam expressamente as branches aprovadas; não usar push `--mirror` ou envio de referências internas.
- As branches antigas contêm dados genéricos de idioma do Tesseract; não são autos nem dados de casos. Nenhuma história será reescrita ou branch apagada para simular consolidação.
- Pacote genérico preparado e conferido em pasta temporária: 107 arquivos incluídos e 161 excluídos. Esse ensaio não executa o instalador nem atualiza o plugin em uso.
- Portáteis (12 arquivos) e adaptadores Codex conferem com as fontes. O custo de abertura anteriormente medido em UN17 (+170 ms na máquina usada; módulos separados com `no-store`) permanece documentado; esta correção de publicação e identidade não muda o desenho de cache nem mede um novo ganho de desempenho.

## Verificações

- Suíte estrita local em `beef9e6`: **112/119 suítes**, saída 1, 624,79 s. Sete erros `ModuleNotFoundError: quickjs` nas suítes AST16, consentimento de interface, grafo de interface, catálogo de modelos, modos, relatórios de interface e transcrição visual. Cobertura estrita incompleta: sintaxe JS sem QuickJS e E2E F03 sem dependência de navegador Python; links simbólicos sem privilégio também foram declarados. Nenhuma dependência foi instalada para contornar a restrição do operador.
- Identidade: 6/6, incluindo dois testes Edge; suíte HTTP da Central isolada aprovada; workspace preservado, recuperação e interrupção real do OCR aprovados.
- O diff da pasta principal em relação ao início contém somente `.gitignore` e `ferramentas/Abrir ASTRA.bat`. Comparação normalizada de CRLF/LF confirma que `index.html`, `servidor.py` e `plantao.py` operacionais não mudaram.
- PR de integração: [#20](https://github.com/alandougs/central-cpj-postgres/pull/20), integrado em `main` no merge `9471131f271a871a6702a96f3617a38691578b9c`. Os PRs #18/#19 também foram encerrados pela integração. O diff entre a candidata e o merge é vazio.
- [CI da candidata](https://github.com/alandougs/central-cpj-postgres/actions/runs/39090064610), SHA `beef9e675c9d8fda768c924b80870dac447796a9`: **119/119 suítes aprovadas**, 568,95 s, com navegador e OCR; sigilo/distribuição/portáteis aprovados. Não houve cobertura crítica ignorada nesse CI. O job opcional de medição de desempenho não foi disparado, conforme o desenho do workflow.
- A página do GitHub exigiu autenticação `sudo` para salvar proteção de `main`; confirmação pelo GitHub Mobile solicitada ao operador, mas expirou sem conclusão. A branch padrão ainda é `master`, e a proteção de `main` não foi salva. Permanecem pendentes somente essas ações de metadados dentro da sincronização; nenhuma autenticação é presumida pelo tempo decorrido.
- Os commits de fechamento seguintes alteram somente fila/PRD/checkpoint/evidências; o workflow valida também o SHA efetivamente enviado a `main`. Conferir a execução correspondente antes de declarar o CI da revisão final aprovado.

Não foi feita instalação, migração, reinicialização da Central nem alteração de banco operacional. A parte operacional da UN18 permanece pendente por determinação expressa do operador.
