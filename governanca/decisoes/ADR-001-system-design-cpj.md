# ADR-001 — Arquitetura e governança da Central CPJ

- **Status:** Aceito
- **Data:** 2026-09-30
- **Contexto de aprovação:** diretrizes de foco no core e operação solo ratificadas em 2026-09-28; formação da squad aprovada em 2026-09-27.
- **Escopo:** Central CPJ, plugin `investigacao-cpj` e scripts locais deste workspace.

## Contexto

A Central atende a produção local de relatórios de investigação: receber documentos, extrair texto e tabelas, apoiar a análise e gerar uma minuta DOCX para revisão humana. O ambiente prioriza uso solo em Windows, simplicidade operacional, rastreabilidade por fonte e proteção dos dados dos inquéritos. O sistema não substitui a análise, decisão ou assinatura do investigador e da autoridade policial.

## Decisões

1. **Foco no core local.** O caminho prioritário é PDF → extração local → Markdown/CSV → análise → minuta DOCX CPJ. Arquivos e scripts locais são a base operacional; banco servidor, Docker, rede multiusuário e novos papéis ficam congelados enquanto não houver decisão expressa de prioridade.
2. **Dados do caso permanecem locais e segregados.** Originais não são alterados. A fonte factual de cada relatório são as peças do próprio caso. Dados identificáveis de casos não entram em repositórios, calibração global ou serviços externos. Testes usam fixtures fictícias em workspace isolado.
3. **Caso como fonte da verdade operacional.** `caso.json` guarda o estado de gestão e produção do caso; índices e painéis são derivados e regeneráveis. O `caso.json` do acervo analítico é distinto e não deve ser unificado com o do core nesta fase.
4. **Extração determinística antes da interpretação.** OCR, transcrição paginada, tabelas CSV e entidades são produzidos por scripts locais sempre que possível. A análise deve distinguir fato, relato, indício, inferência e lacuna e apontar a página de origem.
5. **Minuta com decisão humana.** A automação pode preparar análise e DOCX, mas toda saída é minuta. O investigador revisa e decide a versão final; a autoridade policial decide e assina conforme sua competência.
6. **Separação de responsabilidades e módulos.** A Central orquestra etapas por código. Trabalho de engenharia é dividido por módulo; alterações concorrentes no mesmo módulo são sequenciadas. Integração e mudanças compartilhadas seguem a fila de tarefas.
7. **Revisão independente no fluxo de relatório.** Quando a esteira automatizada estiver habilitada, a revisão probatória deve ser executada por sessão/papel distinto de quem redigiu, confrontando afirmações com as fontes extraídas.
8. **Calibração só produz regra genérica aprovada.** Comparações entre minuta e versão final podem sugerir lições; a gravação em material global depende de aprovação humana e remoção de fatos e dados identificáveis. Documento final de um caso não vira fonte factual de outro.
9. **Validação segura.** Mudanças são verificadas com dados fictícios, workspace temporário e sem conexão com provedores externos quando o teste não exigir integração autorizada. Suítes e testes de segurança aplicáveis devem ser executados antes de declarar entrega.

## Consequências

- A arquitetura favorece scripts locais, arquivos legíveis e índices regeneráveis, com menos dependências operacionais.
- O fluxo deve preservar localizadores de página e trilha de tratamento para permitir conferência humana.
- Recursos multiusuário, infraestrutura pesada ou novos agentes exigem reavaliação explícita, evidência de necessidade e decisão do responsável pelo produto.
- A automação não autoriza envio de autos ou dados identificáveis a serviços externos.

## Revisão

Revisar este ADR se houver mudança aprovada no foco do produto, no modelo de execução local, no tratamento de dados ou na divisão de responsabilidades humanas e automatizadas.
