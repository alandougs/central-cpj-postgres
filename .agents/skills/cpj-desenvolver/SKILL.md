---
name: cpj-desenvolver
description: "Desenvolver ou manter a Central CPJ, o plugin investigacao-cpj e seus scripts locais conforme PRD, com validação em dados fictícios."
---

<!-- Gerado por ferramentas/configurar-codex.py; edite o gerador. -->

# Manutenção da Central CPJ

Leia [PRD.md](../../../PRD.md) e [AGENTS.md](../../../AGENTS.md) na raiz antes de alterar o sistema. O PRD descreve a arquitetura, o estado e os próximos passos; consulte os arquivos atuais para confirmar o que está implementado.

- Trabalhe apenas no escopo solicitado. Central: `plugin/investigacao-cpj/app/`; procedimentos: `commands/`, `skills/`, `agents/`; manutenção: `ferramentas/`.
- Preserve `caso.json` como fonte da verdade, índice SQLite regenerável, permissões por perfil, auditoria, cabeçalho `X-CPJ: 1` em POST e acesso local por padrão. Alterações de integração do Codex não autorizam trocar o executor Claude em `tarefas.py`.
- Não leia autos, bases de consulta, relatórios reais, credenciais ou arquivos de `config/` para desenvolver. Teste com dados fictícios em workspace isolado, com `CPJ_WORKSPACE` nos scripts e `--workspace`/`--porta 8766 --somente-local --sem-navegador` no servidor.
- Procedimentos operacionais continuam no plugin. Após editá-los, gere `portatil/` com `python ferramentas/exportar-portatil.py`. Os adaptadores Codex apontam para esses arquivos vivos.
- Após editar este gerador, rode `python ferramentas/configurar-codex.py`; para conferir os adaptadores sem escrever, use `--verificar`.
- Valide o comportamento afetado; atualize a seção 9 e o Registro de mudanças do PRD a cada entrega. Publicação, alterações de rede, instalação do plugin Claude ou envio externo dependem do pedido correspondente; não fazem parte de uma manutenção local automaticamente.
