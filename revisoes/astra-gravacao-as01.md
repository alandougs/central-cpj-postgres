# AS01 — gravação atômica de casos com bloqueio transitório Windows

Pedido do operador em 18/10/2026: corrigir a intermitência da ASTRA, repetir a suíte completa e sincronizar no GitHub, iniciando as melhorias em ciclos. A Central em uso continua fora de atualização/migração.

## Causa e reprodução

Na TL01, a AST17 recebeu HTTP 500 porque `caso.salvar()` executava `os.replace` uma única vez e o Windows recusou a substituição de `caso.json` com `WinError 5`. A repetição isolada passou, sem comprovar correção. O log histórico não identifica o processo que mantinha o arquivo ocupado.

O teste novo reproduziu o mesmo `WinError 5` com um leitor real do Windows aberto no destino, sem simular `os.replace`. Também reproduziu a recusa transitória controlada, a recusa persistente e um erro de disco distinto. Antes da correção, cinco testes resultaram em um aprovado, duas falhas e dois erros esperados dos defeitos reproduzidos. Além da recusa transitória, a gravação malsucedida avançava a revisão do objeto em memória e deixava o temporário.

## Alteração

`caso.salvar()` preserva a trava exclusiva e a conferência da revisão. Escreve uma cópia do registro no temporário exclusivo, tenta a substituição atômica até três vezes para erros de permissão/bloqueio Windows (pausas de 20 e 40 ms) e confirma revisão/data no objeto somente depois do sucesso. Faz a limpeza do temporário sem mascarar o erro original caso a remoção também falhe.

Erros de disco distintos não são retentados. Uma recusa persistente continua sendo erro após o limite; não há promessa de corrigir falta permanente de permissão ou qualquer bloqueio de duração arbitrária. Não há repetição de chamadas de IA nem alteração da política de rede.

## Verificação local

- `teste_gravacao_caso_as01.py`: **5/5 aprovados**, incluindo bloqueio nativo Windows, preservação do arquivo anterior até a troca, falha persistente sem revisão fantasma/temporário, nova tentativa após liberação da trava e conflito de revisão sem substituição.
- Ambiente de teste separado da TL01: Python 3.12.14, QuickJS 1.19.4, Playwright Python 1.64.0; Edge e Tesseract existentes. Sem instalação de dependências no ambiente operacional.
- `ferramentas/testar-tudo.py --estrito`: **120/120 suítes aprovadas**, saída **0**, soma **653,11 s**, duração total **799,09 s** com preparação dos workspaces. AST17 E2E **23,88 s**, nova suíte AS01 **0,36 s**, Central HTTP isolada **16,73 s**.
- Log integral local: `%LOCALAPPDATA%\CPJ\test-envs\as01-suite-completa.log`. Nenhum skip crítico de ferramenta ausente. Os únicos skips foram cinco testes de links simbólicos por falta de privilégio deste Windows (UN16: um; RV17: quatro), tolerados pelo runner após a sonda de capacidade do host.
- Todos os testes usaram dados fictícios e workspaces temporários. O código ficou congelado durante a suíte; os registros desta entrega foram escritos depois.

## Publicação e limites

Candidata na branch `codex/astra-gravacao-windows`, derivada de `main` em `ddee698`. Esta publicação inclui o relatório histórico TL01, antes somente local. A validação remota e a integração serão conferidas no PR da candidata, sem tratar o resultado local como resultado do CI.

Nenhuma atualização, migração, reinício ou troca de branch da Central operacional. A cópia principal permanece em `codex/os-markdown-relatorio-20261014`, `66ea935`; banco, configuração, credenciais, assinaturas e casos reais não integram esta alteração.
