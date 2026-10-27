# Integração de backup e runner — IV03 — 27/10/2026

Escopo: reconciliar os testes UN10 e RP30 no candidato isolado da sincronização. Foram preservados `ferramentas/backup_consistente.py`, os wrappers PowerShell, o runner e as proteções SEC23/SEC25. Nenhum dado operacional, configuração, credencial, serviço, API de IA ou instalação foi usado.

## Causa e contrato vigente

A execução inicial reproduziu seis erros: os cinco testes UN10 chamavam `criar_backup`, `verificar_backup` e `restaurar`, APIs antigas ausentes; RP30 construía uma origem fictícia sem `plugin/.claude-plugin`, hoje copiado pelo runner. Não se tratava de falha na captura WAL demonstrada.

A busca nos consumidores reais mostrou que `backup.ps1`, `restaurar.ps1` e SEC23 usam `criar_snapshot`, `verificar_snapshot` e `restaurar_snapshot`, com confirmação explícita de escritores parados/mídia protegida. O manifesto aponta para arquivos sob `dados/`. A restauração vigente exige uma pasta nova, protegendo o workspace vivo contra sobreposição e mescla de versões. Não foi restaurada a API antiga nem removida qualquer proteção para satisfazer os testes.

## Correção dos testes e cobertura preservada

UN10 passou a executar a API vigente com `offline=True` e `midia_protegida=True`. Todos os arquivos e o banco principal da origem são conferidos; a cópia restaurada preserva os hashes dos originais, Markdown, metadados, vínculos manuais e relatório fictícios. Um registro de auditoria protegido foi acrescentado à fixture, com perfil TEMP e chave fictícia; somente a primitiva DPAPI é simulada no Windows. O código real de exportação/verificação da âncora, vínculo ao log e restauração continua em execução. Este teste não certifica a criptografia DPAPI; SEC23 também foi executado com sua integração real vigente.

O teste WAL mantém a conexão da fonte aberta, confirma WAL não vazio, recupera as 100 linhas confirmadas e garante ausência de WAL/SHM cru no snapshot. O teste de trabalho posterior cria relatório novo, altera outro, remove um arquivo e insere a linha 101: a restauração no workspace vivo é recusada sem escrever, e a recuperação do estado anterior é demonstrada em outra pasta. Arquivos posteriores e as 101 linhas da origem permanecem intactos. A adulteração agora mantém o tamanho do arquivo, exigindo detecção por SHA-256; verificação e restauração recusam o snapshot sem publicar destino. Os snapshots sequenciais continuam distintos e preservados.

RP30 cria marketplace e MEMORIA somente com conteúdo sintético, confirmando sua cópia para a sandbox. As sentinelas de modelo, assinatura e dados do operador seguem excluídas; o modelo geométrico utilizável continua sendo gerado pela fixture. O runner de produto não foi alterado.

## Verificação

RED: seis erros reproduzidos antes da adaptação, com causas identificadas acima. GREEN focado: UN10 5/5 e RP30 1/1 em 2,713 s. Rodada final: 25/25 testes em 30,939 s, zero skips, zero falhas — UN10 5, RP30 1, SEC23 16 e wrappers PowerShell SEC25/L04 3. A rodada incluiu navegador real de interface SEC23, envelopes/consentimentos de exportação e importação, proteção da auditoria e execução dos wrappers reais exclusivamente sobre dados fictícios em TEMP.

AST dos dois testes e `git diff --check` aprovados. Alterados somente `teste_recuperacao_un10.py`, `teste_runner_isolamento_rp30.py` e este relatório. Nenhum full concorrente foi executado. Fontes congeladas para o próximo gate integrado do coordenador.
