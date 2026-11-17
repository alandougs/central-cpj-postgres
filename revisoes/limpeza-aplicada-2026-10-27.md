# Limpeza operacional aplicada — SZ03 — 27/10/2026

Executada mediante autorização expressa do operador para excluir arquivos desnecessários, preservando PDFs originais e todos os Markdown. Processamento exclusivamente local, sem envio a APIs, inferência sobre conteúdo ou exposição de identificadores neste registro.

| Verificação | Resultado |
|---|---:|
| Documentos com relatório legado examinados | 101 |
| Documentos consolidados em checkpoint essencial único | 85 |
| Documentos incompletos/divergentes preservados | 16 |
| Markdown faltantes acrescentados, sem sobrescrita | 89 |
| Derivados reconhecidos removidos | 36.878 arquivos |
| Volume removido da pasta operacional | 981.352.481 bytes |
| Itens do ZIP privado verificados | 36.878 arquivos |
| Tamanho do ZIP privado | 343.180.955 bytes |
| Arquivos protegidos conferidos antes e depois | 1.188 |
| Derivados reconhecidos restantes, preservados | 4.705 arquivos |
| Volume desses derivados restantes | 1.014.246.768 bytes |

O ZIP recuperável e o manifesto detalhado ficam exclusivamente no backup privado externo ao workspace, com nomes genéricos. Nenhum nome de caso, texto, identificador ou hash de documento integra este relatório público. O ZIP foi verificado antes da exclusão e novamente após a operação; conteúdo, quantidade, tamanho e SHA-256 de cada membro conferem com o manifesto privado.

Os 1.188 arquivos protegidos do inventário anterior mantiveram tamanho e SHA-256. Todos os originais e Markdown preexistentes foram preservados. Novas transcrições/índices de O.S. foram gerados em cópia privada e somente arquivos Markdown faltantes foram copiados com criação exclusiva, sem substituir arquivos existentes. Não houve reindexação operacional, migração de banco, reinício ou alteração em configurações, credenciais, ambientes, Git e diretórios de originais.

Foram removidos somente derivados reconhecidos pelo limpador em documentos com checkpoint coerente, SHA do PDF original confirmado e todas as páginas presentes no Markdown. JSONs de checkpoint/relatório/qualidade somente foram elegíveis quando semanticamente iguais ao consolidado. Permaneceram arquivos de documentos incompletos/divergentes, PNGs ainda pendentes ou a conferir, arquivos sem equivalência comprovada, índices JSON de O.S., dados desconhecidos e CSVs de análise. Os 85 checkpoints essenciais consolidados foram mantidos. Nenhum diretório foi removido.

Durante a preparação, uma execução foi interrompida antes do arquivamento/exclusão por custo quadrático na leitura de checkpoints grandes. O ajuste mínimo autorizado passou a reler o estado consolidado uma única vez por documento e comparar cada legado em memória, usando o mesmo resolvedor de nomes. A regressão instrumentada falhou com quatro leituras onde exigia uma e passou após o ajuste. A retomada reutilizou os estados já existentes, sem duplicá-los.

A revisão FV01 posterior reproduziu em diretório temporário a aceitação indevida de uma junction interna pelo compactador. O helper foi corrigido para recusar qualquer reparse point na ancestralidade, da raiz ao arquivo, antes de enumerar, ler ou gravar checkpoints. Auditoria operacional dos 85 checkpoints consolidados e seus ancestrais constatou zero reparse points. O limpador já recusava links/junções antes de selecionar e remover derivados. A última rodada aprovou cinco testes MD01, incluindo a junction interna nativa Windows, e nove testes SZ02.

Os arquivos privados de operação permitem auditoria e restauração individual; não devem ser enviados ao GitHub. A preservação de derivados bloqueados é deliberada: sua exclusão exigiria primeiro completar a rastreabilidade/equivalência, mantendo PDFs e Markdown.
