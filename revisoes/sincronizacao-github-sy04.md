# SY04 — sincronização estrutural do GitHub

Autorização: corrigir pendências e sincronizar a estrutura do sistema no GitHub, sem dados reais dos casos; instalação e migração expressamente excluídas. Continuação do plano canônico UN18 na cópia de desenvolvimento `codex/unificacao-cpj`.

## Correção reproduzida

`teste_identidade_form_codex.py`: oito subfalhas na revisão publicada; os formulários não tinham seleção de cargo, máscara de CPF ou autocomplete de nome. O teste estático de helpers ainda examinava o HTML anterior à modularização. Dois testes Edge acrescentados falharam pela ausência de `selecionarCargo` antes da implementação.

Correção: seletor de cargos com opção personalizada; carregamento e envio dos três formulários preservam o valor personalizado; reset limpa o campo auxiliar; CPF recebe somente formatação visual e limite de 11 dígitos, sem inferir ou completar identificadores. Testes estáticos leem o módulo JS real. Resultado dirigido: 6 testes aprovados, incluindo dois no Edge com dados fictícios.

## Publicação e preservação

- Iniciador genérico `ferramentas/Abrir ASTRA.bat` versionado. Ícones pessoais ficam locais e ignorados; nenhum arquivo local foi apagado.
- As três branches locais de editor, DOCX e progresso passaram individualmente em `verificar-publicacao.py --ref` sem achados proibidos. Os commits serão preservados em branches remotas próprias; suas funcionalidades já estão integradas, com adaptações, à candidata. Não reaplicar patches antigos sobre os módulos atuais.
- A candidata e a branch atual passaram no verificador de publicação; nenhuma pasta de casos reais, banco, configuração operacional, credencial, assinatura ou documento real foi identificada. A busca de caminhos históricos remotos não encontrou arquivos desses tipos; isso não constitui auditoria manual integral de cada conteúdo histórico.
- As branches antigas contêm dados genéricos de idioma do Tesseract; não são autos nem dados de casos. Nenhuma história será reescrita ou branch apagada para simular consolidação.

## Verificação em andamento

Suíte estrita completa em execução, seguida de CI no SHA efetivamente publicado. Não declarar CI verde ou sincronização concluída antes de conferir os resultados. Não foi feita instalação, migração, reinicialização da Central nem alteração de banco operacional.
