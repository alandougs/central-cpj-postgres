# AS03 — histórico do processamento por O.S.

Prioridade indicada pelo operador em 18/10/2026, dentro do painel UN15 e do contrato `cpj-fluxos/1`. Nenhuma atualização, instalação, migração ou reinicialização da Central em uso.

## Falhas reproduzidas e correção

O histórico recebia HTTP 200 e etapas válidas, mas a referência a `id` inexistente gerava um erro capturado e um aviso falso. Além disso, uma resposta antiga podia receber a versão da lista mais recente, impedindo a atualização do histórico aberto.

A consulta agora registra a referência da O.S. antes de sair, descarta o resultado se essa referência mudou e revalida o histórico aberto. A revalidação aguarda a aba ficar visível; não se repete automaticamente após uma falha real. Mantidas as guardas de usuário, identidade do detalhe, paginação, permissões, foco e rascunhos do formulário.

## Evidências locais

- Antes da correção: dois testes de navegador falharam. Corrigir apenas o identificador eliminou o aviso falso, mas manteve a falha com resposta atrasada, comprovando os dois defeitos separadamente.
- A primeira revalidação expôs consulta extra com a aba oculta. Regressão formal reproduziu `2 !== 1`; a guarda de visibilidade corrigiu o cenário e a consulta voltou ao retornar à aba.
- Versão final: **7/7 testes de navegador aprovados**, sem skips, em **23,92 s**. Inclui erro HTTP real, resposta atrasada, pausa/retomada, troca de usuário, rede, permissões, foco, texto digitado e ações versionadas. Log local: `%LOCALAPPDATA%\CPJ\test-envs\as03-interface-final.log`.
- Suíte completa estrita anterior ao último ajuste de visibilidade: **121/121**, soma **661,87 s**, total **809,09 s**, saída **0**. Log `as03-suite-completa.log` na mesma pasta. A suíte de navegador nessa rodada continha seis testes; o ajuste final foi validado com os sete acima e ainda exige os checks obrigatórios do head publicado.
- Cinco testes de links simbólicos pulados por privilégio do Windows na rodada completa; nenhum skip crítico por ferramenta ausente. O guard da árvore operacional passou nesta rodada; as interferências de metadados das rodadas AS02 continuam registradas, sem enfraquecer o teste.

Todos os testes usam O.S. fictícias e servidor local temporário. Não foram usados autos, credenciais ou bancos reais nas fixtures. Os resultados do GitHub e a integração devem ser conferidos no PR da branch `codex/fluxos-os-historico`; aprovação local não substitui esses checks.
