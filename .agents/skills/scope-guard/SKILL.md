---
name: scope-guard
description: Não saia destes limites. Use no início de qualquer tarefa que leia, altere, crie ou apague arquivos, rode comandos ou mexa em casos e O.S. do projeto CPJ, e sempre que surgir a tentação de "aproveitar e mexer também" em algo fora do que foi pedido. Fixa os limites da tarefa antes de agir e manda parar e perguntar antes de ultrapassá-los.
---

# scope-guard — não saia destes limites

O trabalho vale só dentro do que foi pedido. O que está fora, mesmo quando está errado, não é seu para mexer sem autorização.

## 1. Antes de agir: fixe os limites

Escreva, para si, em poucas linhas:

- **Pedido:** o que o usuário pediu, nas palavras dele. Não amplie por interpretação.
- **Pode tocar:** arquivos, pastas, caso/O.S. e comandos necessários para esse pedido.
- **Não pode tocar:** todo o resto.

Pedido ambíguo que mude muito o tamanho do trabalho: pergunte uma vez, objetivamente, antes de começar.

## 2. Limites fixos do projeto CPJ

- **Tarefa e arquivos reservados.** Desenvolvimento só com a tarefa assumida em `python ferramentas\fila-tarefas.py assumir <ID> --agente <sessão>`. Não edite arquivo reservado por tarefa em andamento de outro agente, nem para uma correção pequena: registre a dependência e aguarde.
- **Caso e O.S.** Trabalhe só com os documentos do caso indicado (`AGENTS.md`, regra 1). Uma O.S. por agente, reservada com `ferramentas\fila-os.py`. Não selecione caso por proximidade nem refaça O.S. concluída sem pedido.
- **Intocáveis.** `00-originais` (somente leitura), `config\`, `usuarios\`, credenciais e chaves de API, e o conteúdo de casos fora do caso em curso.
- **Sem dados de caso fora do caso.** Nada de caso em `acervo\`, `calibracao\`, GitHub, Artifact, Gist, Drive ou Notion (regras 6 e 7).
- **Só com pedido expresso do usuário:** commit e push, publicação, instalação ou atualização do plugin, mudança de rede, uso de provedor externo de IA, apagar ou mover dado de produção.
- **Dados fictícios e workspace temporário** em todo teste. Nunca escreva em `casos\` real para testar.

## 3. Durante o trabalho

- Achou um defeito, uma melhoria ou um arquivo estranho fora do escopo? **Não corrija.** Anote em uma linha no relato final ou, se for do sistema, proponha tarefa na fila. O usuário decide.
- Precisa sair do limite para concluir (outro arquivo, outro caso, comando destrutivo)? **Pare e peça autorização**, dizendo o que, onde e por quê. Autorização para uma coisa não vale para a seguinte.
- Antes de apagar, sobrescrever ou mover, olhe o alvo. Ação difícil de desfazer só com confirmação.
- Não contorne bloqueio de permissão, trava ou reserva. Se algo o impede, esse é o limite.

## 4. Ao terminar

Confira o que mudou (por exemplo `git status`) e confirme que **todo arquivo tocado** estava no escopo. Se algo ficou fora, diga qual e por quê. Informe também o que você viu e deliberadamente não mexeu.
