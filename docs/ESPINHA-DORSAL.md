# Espinha dorsal da Central CPJ

Determinação do operador em 16/10/2026, aplicável a Codex, Claude, Gemini e qualquer outro executor. Este documento fixa os contratos de desenvolvimento; `AGENTS.md` continua regendo segurança e operação dos casos. Uma instrução posterior explícita do operador pode alterar o escopo; registre a alteração antes de implementar.

## Direção única

Um projeto, um repositório, uma Central e uma versão oficial em `main` após integração validada. Python, Flask e SQLite; execução local por padrão. Arquivos internos podem ter responsabilidades distintas, mas não criar versões concorrentes, serviços novos ou outra infraestrutura sem necessidade aprovada.

Uma fila de desenvolvimento: `TAREFAS-COMPARTILHADAS.md`, com reservas pelo script e IDs relacionados às issues/PRs. Uma experiência operacional: acompanhamento por O.S., com documentos, etapas, tentativas e pendências dentro do mesmo fluxo. Dados de casos nunca são copiados para a fila pública de desenvolvimento.

## Contratos que o código deve preservar

| Área | Regra obrigatória |
|---|---|
| Caso | `caso.json` é a fonte do estado oficial e dos dados do caso |
| Extração | Preservar os checkpoints de `processamento.json`, arquivos extraídos, hashes e rastreabilidade; integrar sua leitura e recuperação ao fluxo comum |
| Execução | Aproveitar `config/plantao.sqlite` para coordenação durável, com IDs estáveis, dependências, reservas atômicas, cancelamento e histórico |
| Índice | RAG é derivado e regenerável. Vínculos manuais precisam de fonte autoritativa preservada; nunca depender somente do índice |
| Originais | `00-originais` é imutável; reprocessar cria/atualiza derivados conforme as regras existentes |
| Relatório | Atender à O.S., preservar fontes, versões e revisão. Sucesso técnico não registra entrega nem gera `FINAL` automaticamente |
| IA | Preservar ativação, consentimento, orçamento e permissões. Não ativar provedor nem repetir automaticamente uma chamada de resultado incerto |
| Interface | Uma linha principal por O.S.; etapas e documentos acessíveis como detalhes; atividade e erros reais, sem progresso inventado |
| Compatibilidade | Migrar contratos de API e consumidores em conjunto; nenhuma alteração silenciosa de estado, permissão ou formato |
| Sigilo | Casos, bases, credenciais, assinaturas, configurações e bancos operacionais ficam locais. Repositório, CI, logs publicados e fixtures somente com dados genéricos/sintéticos |
| Distribuição | Fonte, recursos estáticos, portáteis, adaptadores e pacote devem corresponder à mesma revisão |
| Evidência | Teste ignorado não é teste aprovado. Não enfraquecer testes para esconder falhas; confrontar expectativa antiga com o requisito vigente |
| Retorno | Backup consistente e restauração verificada antes de migração operacional. Nunca restaurar cegamente sobre dados criados depois do backup |

## Documentos canônicos da unificação

1. Desenho aprovado: [2026-10-16-cpj-unificado-design.md](superpowers/specs/2026-10-16-cpj-unificado-design.md).
2. Plano de execução: [2026-10-16-cpj-unificado.md](superpowers/plans/2026-10-16-cpj-unificado.md).
3. Prompt de passagem: [2026-10-16-cpj-unificado-prompt.md](superpowers/plans/2026-10-16-cpj-unificado-prompt.md).
4. Evidência inicial: [diagnóstico](../revisoes/diagnostico-unificacao-2026-10-16.md).

Não criar plano paralelo ou recomeçar o projeto. Antes de cada etapa, conferir a versão atual desses documentos, a fila e os commits remotos; retomar o primeiro item incompleto. Divergência factual exige atualizar a evidência e adaptar os detalhes sem abandonar os contratos acima.

## Estado e autorização

O desenho foi aprovado pelo operador. O pedido desta sessão é **registrar e publicar o plano e o prompt, sem executar a implementação**. A existência destes documentos ou de tarefas disponíveis não dispara execução. O agente seguinte começa quando receber do operador o prompt de execução ou autorização equivalente.

Essa execução abrange implementação, testes sintéticos e sincronização da branch de integração. Merge definitivo em `main`, troca da branch padrão e instalação/migração operacional têm uma liberação final específica, após apresentação da revisão testada, backup/restauração e riscos residuais. Se essa liberação já tiver sido dada explicitamente na sessão de execução, não pedir novamente.

Os documentos orientam os agentes; a conformidade real será comprovada pelos testes e pelas verificações do plano. Não declarar o projeto unificado, protegido ou sem perda de dados apenas porque a regra foi registrada.

## Atualização expressa — 27/10/2026

Novos PDFs passam a gerar somente Markdown como extração documental, sem derivados CSV/JSON. Preservar estado e checkpoints essenciais consolidados, originais, rastreabilidade e compatibilidade de leitura legada. Reduzir arquivos técnicos descartáveis dentro do projeto; não apagar dados antigos por extensão. Esta determinação posterior altera o escopo de geração de derivados, preservando os demais contratos.

Memória compartilhada: entrada em `../MEMORIA.md`; determinações de extração enxuta, memória e coordenação em `../AGENTS.md`, regras 21–23. Mantidos um projeto/plano canônico e os consentimentos existentes; preferência de modelos não troca executor ou provedor automaticamente.
