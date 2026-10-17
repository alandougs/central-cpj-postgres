# Prompt de execução — copiar para o agente responsável

O texto abaixo só inicia trabalho quando o operador o enviar ao agente executor. Sua gravação neste repositório não é ordem de execução para a sessão que está preparando o plano.

```text
Execute a unificação da Central CPJ conforme o plano canônico já registrado no projeto. Quero um único projeto oficial, uma fila de desenvolvimento e acompanhamento contínuo por O.S., leve, rápido, fácil e sem perda de dados. Aprovo a execução do plano abaixo em sequência por um agente responsável; não crie outro projeto, outra arquitetura ou um plano concorrente.

Workspace operacional: C:\CPJ - TRABALHO.
Repositório: https://github.com/alandougs/central-cpj-postgres.
Os documentos foram publicados na branch codex/os-markdown-relatorio-20261014. Faça fetch e confirme que seu checkout contém as versões mais recentes antes de agir; não substitua mudanças locais nem suponha que o conteúdo já esteja em main.

Leia, nesta ordem:
1. AGENTS.md e docs/ESPINHA-DORSAL.md.
2. PRD.md e TAREFAS-COMPARTILHADAS.md.
3. docs/superpowers/specs/2026-10-16-cpj-unificado-design.md.
4. docs/superpowers/plans/2026-10-16-cpj-unificado.md.
5. revisoes/diagnostico-unificacao-2026-10-16.md.
6. revisoes/unificacao-execucao.md, se já existir, para retomar do ponto correto.

Execute UN10 a UN18 na ordem e com seus gates. Use superpowers:executing-plans se disponível; sem a skill, siga os mesmos passos diretamente. Reserve cada tarefa pelo script ferramentas/fila-tarefas.py antes de editar e respeite reservas alheias. Use branch/check-out isolado codex/unificacao-cpj, retomando-o se já existir e for desta execução. Subagentes somente para testes ou logs extensos, conforme AGENTS.md.

Preserve Python, Flask e SQLite; caso.json como fonte oficial; checkpoints de processamento.json; coordenação em config/plantao.sqlite; originais imutáveis; fontes e vínculos manuais; histórico, consentimentos, orçamento, permissões e revisão. Não ativar IA nem usar autos reais em testes. Não criar FINAL nem registrar entrega automaticamente. Não fazer reset destrutivo, force-push, limpeza indiscriminada ou sobrescrever trabalho posterior com backup antigo.

Primeiro ensaie recuperação com dados fictícios. Depois integre as mudanças úteis dos PRs #18 e #19 e verifique os commits exclusivos de master. Resolva conflitos sem perder funcionalidades ou documentos de governança. Corrija as falhas pela causa e pelo requisito atual: não remova nem enfraqueça testes para obter aprovação. Unifique acompanhamento, persistência, recuperação, interface e distribuição conforme os contratos do plano; reaproveite as soluções existentes.

Faça testes sintéticos proporcionais a cada etapa, suíte completa na revisão congelada, navegador, OCR, concorrência, reinício, cancelamento, migração, restauração, segurança e desempenho. Registre falhas e skips separadamente; não considere cobertura crítica ignorada como aprovação. Nunca execute o publicador legado para diagnóstico. Antes de cada push, confira caminhos e conteúdo para não publicar casos, bases, credenciais, configurações, assinaturas ou bancos operacionais.

Está autorizada a implementação em isolamento, preparação do ambiente de teste, commits, push da branch de integração e criação/atualização do PR. Mantenha PRD, fila e revisoes/unificacao-execucao.md atualizados com SHA, testes, limitações e próximo passo. Não me peça confirmação para decisões rotineiras dentro do plano.

Antes de merge definitivo em main, troca da branch padrão ou instalação/migração operacional, apresente a revisão testada e a evidência de recuperação e solicite a liberação final que ainda não tiver sido dada. Se eu já a tiver concedido expressamente nesta sessão, use essa autorização sem repetir a pergunta. Faça backup operacional consistente e restauração verificada antes de migrar; preserve dados criados depois do backup. Não apague branches antigas.

Ao final, informe: revisão local/remota/instalada, o que foi integrado, testes realmente executados, skips e riscos, evidência de preservação/restauração, métricas de desempenho e eventuais pendências. Só declare unificação concluída quando todos os critérios do desenho estiverem comprovados; se faltar liberação operacional, entregue candidato testado e sincronizado, identificando essa pendência. Se interromper, deixe checkpoint preciso e libere a reserva para o próximo agente continuar sem recomeçar.
```
