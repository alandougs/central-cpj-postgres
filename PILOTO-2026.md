# Piloto Controlado da Central CPJ — 2026

**Estado:** planejado; aguardando confirmação do investigador antes da primeira chamada de IA.

## Objetivo

Executar uma vez o fluxo com um IP inteiramente fictício, em workspace temporário isolado, para medir o funcionamento da análise, revisão e geração do DOCX. O piloto não define FINAL nem registra baixa de produção.

## Roteiro proposto

1. Criar um workspace descartável com `TemporaryDirectory` e configurar `CPJ_WORKSPACE` exclusivamente para esse diretório.
2. Gerar o PDF sintético usando `plugin/investigacao-cpj/app/testes/e2e/pdf_aux.py` (`gerar_pdf_sintetico_e2e`, três páginas textuais e uma página digitalizada). Não copiar nem consultar pastas reais em `casos/` ou ordens de serviço.
3. Processar o PDF localmente, incluindo OCR da página digitalizada, e conferir que a transcrição e os artefatos do caso ficaram dentro do workspace temporário.
4. Após confirmação do investigador, executar pelo fluxo automático do Claude Code as etapas de análise documental, análise financeira, redação da minuta e revisão independente, nessa ordem.
5. Gerar o DOCX no modelo oficial dentro do workspace temporário e verificar que o arquivo abre e corresponde à minuta. Não gerar FINAL, baixa ou dados para `producao/`.
6. Registrar resultados agregados nesta ficha; ao encerrar, limpar o temporário e confirmar que nenhum arquivo foi criado/alterado nas pastas reais de casos ou produção.

## Ambiente observado antes da execução

- Binário: resolvido por `plantao.claude_exe()`; Claude Code `2.1.286`.
- Autenticação: `loggedIn: true`, `claude.ai`, plano Pro (verificado em 2026-10-01; nenhum segredo ou identificador de conta registrado).
- Plugin habilitado no CLI: `investigacao-cpj@cpj-local`, versão instalada `0.2.0`.
- Fixture: gerador sintético E2E local, quatro páginas; nenhum dado de caso real.
- Primeira chamada de IA: **ainda não realizada**.

## Métricas a registrar

| Métrica | Método |
|---|---|
| Tempo | Horário de início/fim e duração de cada etapa (extração, análise documental, análise financeira, redação, revisão e DOCX), além do tempo total. |
| Custo/uso | Registrar tokens e custo em USD se o CLI os reportar. Se o plano Pro não expuser custo por chamada, registrar isso como indisponível e anotar apenas a métrica de uso realmente exibida; não estimar valores. |
| Retrabalho | Quantidade de novas tentativas, versões da minuta, alterações após a revisão e intervenções manuais necessárias para concluir cada etapa. |
| Achados do revisor | Contagem por categoria e gravidade, indicando quantos foram confirmados na fonte fictícia, quantos eram falsos positivos e quantos ficaram sem resolução. |
| Saída | Etapas concluídas/falhas, arquivos gerados, rastreabilidade das afirmações e validação de abertura do DOCX. |

Recomendações de mudança de papéis serão limitadas ao que essas observações sustentarem. Um único caso sintético curto não permite inferir desempenho em autos extensos; se a amostra não for suficiente, o resultado será “evidência insuficiente”.

## Segurança e limites

- Conteúdo inteiramente inventado; nenhum documento, resultado ou identificador de caso real será usado.
- Extração e preparação locais. A inferência do piloto será enviada ao Claude Pro autenticado, conforme este piloto solicitado e somente após confirmação do investigador.
- O agente deve trabalhar com `cwd` no workspace temporário, sem WebFetch, WebSearch ou conectores MCP.
- Se uma etapa tentar acessar um caminho de caso real, usar dado não sintético ou gravar fora do temporário, interromper o piloto.
- Toda saída é minuta de teste; nenhum relatório será usado oficialmente.

## Aprovação do roteiro

- Confirmação do investigador: **pendente**.
- Data/hora da confirmação: —

## Resultados

A preencher após a confirmação e execução. Nenhuma chamada de IA foi feita até o momento.
