# Correções de segurança — 21/10/2026

> Continuidade em 22/10/2026: o operador autorizou corrigir as cinco reprovações gerais abaixo. Correções e verificação atual em [Cinco falhas gerais](cinco-falhas-gerais-2026-10-22.md), tarefas RG26–RG29. Os resultados de 21/10 neste documento são históricos e não foram reescritos como aprovação retroativa.

## Autorização e limites

O operador solicitou corrigir os sete achados apresentados nesta sessão e executar o trabalho com os papéis Dev sênior, Analista de Sistemas, CEFO e Analista de Segurança sênior. Goal ativo na sessão. Esta é a evidência da rodada corretiva SEC21–SEC24 na fila única, subordinada aos contratos de `docs/ESPINHA-DORSAL.md`; não é outro plano de unificação nem execução das etapas UN10–UN18.

Preservar as alterações locais anteriores, Python/Flask/SQLite, `caso.json`, checkpoints, fontes, consentimentos e orçamento. Nenhum teste usa autos, credenciais, configurações ou bancos operacionais. Nenhuma chamada paga, ativação de provedor, publicação, merge, atualização instalada, alteração da rede real ou migração de dados reais faz parte desta rodada.

## Estado da execução

Código corretivo local implementado, com revisão específica aprovada e regressão geral executada com ressalvas discriminadas abaixo. Não homologado nem ativado no processo operacional. A revisão inicial confirmou com fixtures sintéticas: HTML aceito na importação e servido inline na origem da Central; chave de API persistida em texto claro; exportação ZIP sem criptografia própria. As demais evidências vieram da leitura do código. Não foi verificado o estado efetivo de BitLocker, firewall ou exposição da instalação em uso. Base Git local: `f56653c`, branch `codex/final-sync-20261010`, com alterações anteriores preservadas e correções desta rodada ainda sem commit/publicação.

| Item | Responsável / fila | Critério de conclusão | Estado |
|---|---|---|---|
| Conteúdo ativo / web / TLS / WSGI | Dev sênior / SEC21 | Arquivos ativos isolados ou baixados; acesso local preservado; rede não inicia sem TLS; HTTP/HTTPS sintético | Implementado; 13 testes específicos aprovados |
| Segredos / auditoria / IA | Segurança sênior / SEC22 | Credenciais protegidas e falha fechada; adulterações detectáveis; ferramentas limitadas ao caso/etapa | Implementado; 14 + 6 testes específicos aprovados |
| Exportação / importação / backup | Analista de Sistemas / SEC23 | Pacote autenticado portátil; aceite de legado; snapshots versionados e restauração sintética | Implementado; 15 testes específicos aprovados |
| Restauração legada / PowerShell | Analista de Sistemas / SEC25 | Entrada antiga também exige destino novo, snapshot íntegro e confirmação de mídia | Implementado; 3 testes específicos aprovados |
| Integração e revisão de custos | Coordenação + CEFO / SEC24 | Contratos HTTP e UI compatíveis; testes, dependências e limites documentados | 9 testes integrados aprovados; revisão CEFO concluída; fluxo HTTP completo e workspace aprovados; ressalvas gerais registradas |

## Evidência de testes

Interpretador de testes: `.venv/Scripts/python.exe`, confirmado com Flask e dependências existentes. O Python global não contém Flask; não usá-lo para executar testes da Central.

- Teste integrado SEC24 antes das correções: `python -X utf8 plugin/investigacao-cpj/app/testes/teste_integracao_seguranca_sec24.py`; cinco testes, oito falhas esperadas, retorno 1. Reproduz falta de proteção das chaves, configuração corrompida substituída silenciosamente, exportação sem senha, importação legada sem aceite e ausência de diagnóstico de integridade da auditoria.
- Após estabilização: **60 testes específicos/integrados aprovados, zero skips nessa seleção**. Comando por arquivo: `.venv/Scripts/python.exe -X utf8 -W ignore::ResourceWarning plugin/investigacao-cpj/app/testes/<arquivo>`.

| Arquivo | Testes aprovados | Duração da repetição final |
|---|---:|---:|
| `teste_web_sec21.py` | 13 | 25,503 s |
| `teste_segredos_auditoria_sec22.py` | 14 | 5,085 s |
| `teste_isolamento_ia_sec22.py` | 6 | 1,722 s |
| `teste_backup_exportacao_sec23.py` | 15 | 17,123 s |
| `teste_integracao_seguranca_sec24.py` | 9 | 9,587 s |
| `teste_backup_antigravity.py` | 3 | 18,139 s |

Os tempos acima foram medidos com execução paralela de suítes independentes e não constituem benchmark de desempenho. A rodada inclui Edge, TLS real, exFAT sintético, junctions reais, concorrência entre processos, restauração funcional da cadeia de auditoria e wrappers PowerShell reais. Streaming foi ensaiado com múltiplos MiB; não houve ensaio físico de 2 GiB.

- Regressões dirigidas adicionais aprovadas: importação legada 5/5 + 2/2 (aceite agora explícito, mantendo checksum/traversal/cancelamento); Explorer 9/9 (HTTP remoto recusado e HTTPS autorizado preservado); catálogo/API de modelos 13/13 (fixture já protegida, catálogo não altera seleção/ativação); orçamento 19/19; consentimento seguro 7/7; segurança existente 11/11; solo 7/7 e usuário solo 7/7; visualizador 12/12; ExplorerUI Edge 1/1; produção 7/7.
- Help offline do Claude instalado confirmou presença de todos os flags usados pelo transporte limitado, sem pedido de inferência: `--tools`, `--disallowedTools`, `--strict-mcp-config`, `--mcp-config`, `--disable-slash-commands`, `--setting-sources`, `--settings`, `--safe-mode`, `--restricted`, `--no-session-persistence`, `--chrome`, `--system-prompt`; retorno 0. O contrato de ferramentas virtuais foi testado com subprocesso real sintético; não foi feito piloto de inferência real.
- `pip check`: `No broken requirements found`. Cheroot 11.1.2 instalado na `.venv` usada para verificar.
- Comando geral executado: `.venv/Scripts/python.exe -X utf8 ferramentas/testar-tudo.py`, saída em `%TEMP%/cpj-seguranca-sec24-suite-completa-20261021.log`. São snapshots isolados por suíte. A rodada de descoberta iniciou antes do complemento SEC25 e de encerrar o teste concorrente SEC24; por isso o teste PowerShell legado da primeira passagem precisa ser lido junto da repetição final 3/3 acima. Não apresentar essa passagem como uma revisão única imutável totalmente aprovada.

### Resultado da regressão geral e repetições finais

A passagem geral terminou com **89/96 suítes aprovadas em 463,92 s, retorno 1**. O fluxo `teste_central.py (Central isolada)` foi aprovado. Duas das sete reprovações foram resolvidas durante a revisão:

- `teste_backup_antigravity.py`: contrato antigo esperava backup espelhado/restauração sobre a origem; SEC25 reconciliou wrappers e fixture com snapshots e destino novo. Repetição final: 3/3, sem skips, tabela acima.
- `teste_workspace_v01.py`: o novo WSGI deixou a mensagem de inicialização retida no buffer de stdout. Confirmado no log das duas inicializações sintéticas; corrigido com `flush=True` na própria mensagem, sem alterar teste. Repetição pelo helper `rodar_suíte` do runner, em clone isolado: retorno 0, 9,125 s, todos os checks aprovados.

Após a última alteração de produto, `rodar_central()` do runner repetiu todo o fluxo HTTP, desde cadastro/upload e permissões até DOCX/FINAL/baixa fictícios, exportação cifrada e importação com senha: **retorno 0, 20,906 s, TUDO OK**. Nenhum desses atos corresponde a um caso ou entrega real.

Permanecem cinco suítes gerais reprovadas, fora dos sete achados e dos componentes corretivos desta rodada. Não foram alteradas para esconder as falhas; não há homologação geral:

| Suíte | Falha observada |
|---|---|
| `teste_casos_status_visual_codex.py` | Expectativa de helper de status e CSS de linha concluída ausentes na interface desta base |
| `teste_dados_os_codex.py` | OCR real da fixture não preencheu `ESCRIVAO FICTICIO`; também há indisponibilidade de OCR em outros cenários do ambiente |
| `teste_docx_f04.py` | Duas expectativas não reconciliadas de citações/estilos e quebra antes da assinatura; SEC/SIG01 específicos passaram, sem substituir esta reprovação |
| `teste_identidade_form_codex.py` | Expectativas de seleção de cargos, máscara CPF e autocomplete não implementadas nesta interface |
| `teste_interface_claude.py` | Expectativa estática de um único bloco de script, incompatível com os scripts locais presentes na base |

Testes ignorados na passagem geral, separados de aprovação: `teste_desempenho_f02.py` (1 cenário OCR/Tesseract), `teste_executores_rv17.py` (4 cenários de symlink sem privilégio), `teste_ocr_checkpoint_claude.py` (OCR português indisponível), `teste_segredos_auditoria_sec22.py` (1 cenário exFAT indisponível no clone NTFS do runner). O cenário exFAT SEC22 foi executado sem skip na repetição direta sintética em D; os cenários Windows de junction SEC23 também foram executados. Isso não transforma os quatro cenários de symlink RV17 ignorados em aprovação.

## Decisões e impactos a verificar

- Novas exportações exigem senha e formato `.cpjenc`; a senha não integra o registro persistente da tarefa. Pacotes antigos continuam importáveis somente com aceite explícito de seu formato sem criptografia.
- Cheroot foi escolhido para WSGI no Windows com TLS direto, reutilizando os certificados existentes e evitando um proxy adicional. Dependência proposta: `cheroot>=11.1.2,<12`; instalação apenas no ambiente de verificação desta rodada.
- Proteger segredos com o usuário Windows implica recuperação/transferência própria: restaurar um arquivo protegido em outra conta não garante conseguir decifrá-lo. A compatibilidade e o procedimento devem ser explicitados.
- Claude automático preservado como transporte JSON sem ferramentas nativas, MCP, skills ou hooks não gerenciados; cwd temporário, ambiente reduzido sem API keys, chamadas virtuais validadas pelo servidor e escritas somente nas saídas da etapa/ação. Exige CLI 2.1.304+ da série 2.1.x. Codex/Gemini/Copilot automáticos ficam bloqueados explicitamente até capacidade equivalente. Não houve troca silenciosa para API. Binário vendor e políticas gerenciadas do computador continuam confiáveis; não é sandbox de SO. [Contrato oficial do CLI](https://code.claude.com/docs/en/cli-reference).
- Uma cadeia de integridade local não protege contra quem controla simultaneamente a conta, o código, a chave e todas as cópias. O objetivo é detectar adulteração dentro do limite de confiança declarado.

## Revisão CEFO

Revisão independente executada pelo agente CEFO (modelo menor autorizado pelo operador), somente com código genérico e fontes oficiais. Cheroot é a única dependência Python nova; Scrypt/AES-GCM reutilizam `cryptography`. Não foi acrescentado serviço hospedado, banco servidor ou provedor pago obrigatório. [Cheroot upstream](https://github.com/cherrypy/cheroot) e [licença BSD-3-Clause](https://github.com/cherrypy/cheroot/blob/main/LICENSE.md). Nenhuma estimativa fictícia de preço, armazenamento ou ganho de desempenho.

Os snapshots são cópias integrais versionadas, sem deduplicação ou expurgo automático: o espaço necessário cresce com a soma das cópias. A instituição deve definir retenção e manter mídia externa autorizada/protegida. As opções `--offline` e `--midia-protegida` são declarações do operador, não comprovação de parada dos escritores nem de BitLocker ativo. A rotina detecta mudanças de conteúdo e não publica um snapshot confirmado se a origem variar.

DPAPI vincula proteção à conta Windows; transferência para outra conta/máquina pode não decifrar segredos. Não confundir cópia do JSON cifrado com recuperação do perfil Windows. O pacote `.cpjenc` é portátil com sua senha; sem essa senha não há chave de recuperação guardada pela Central. A [documentação DPAPI da Microsoft](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata) descreve os limites de conta/máquina.

Nenhum pedido externo real foi executado nesta rodada. O Claude continua um serviço externo sob a conta/plano do operador, mesmo sem ferramentas nativas; consentimento `cli:claude` e orçamento continuam obrigatórios. Ativar API continua sendo ato explícito do operador; a correção não ativa provedor nem troca o padrão por API para contornar o bloqueio de outro CLI. Limites estimados de custo não são garantia de teto de faturamento do fornecedor.

O volume D foi consultado somente por metadados: é exFAT, sem suporte a ACL. Isso exige proteção real do volume/mídia para confidencialidade dos documentos e do staging. Não foi verificada sua criptografia. A âncora de auditoria usa armazenamento protegido por usuário quando o workspace não oferece ACL; a integração com backup/restauração dessa âncora está sendo validada antes do gate final.

## Revisão independente de código

O Dev sênior, após concluir SEC21, reproduziu três defeitos adicionais nos mesmos componentes corrigidos, exclusivamente em diretórios temporários: exportação seguia junction ancestral para fora do workspace; importação de extras gravava por junction preexistente fora do workspace; dois processos de auditoria podiam apendar a mesma sequência por falta de trava interprocesso. SEC23 e SEC22 corrigiram esses casos; a repetição final cobre junctions Windows reais e dois processos com 25 registros cada, preservando 50 registros íntegros.

A coordenação também reproduziu perda de configuração por dois POSTs concorrentes (modelo de um dos provedores era perdido) e serializou leitura/alteração/gravação no endpoint. O teste final conserva as duas alterações. A entrada legada `restaurar.ps1` foi reconciliada em SEC25 com o mesmo mecanismo de snapshots: destino obrigatório novo, sem sobrepor dados posteriores.

## Limites operacionais e recuperação

Proteção de mídia/offline são declarações e precisam ser verdadeiras. exFAT não fornece ACL nem confidencialidade dos documentos por si só. DPAPI protege credenciais e âncora, não todos os autos. Perder a senha de `.cpjenc` impede recuperar o pacote; perder o perfil DPAPI pode impedir abrir credenciais/âncora, exigindo migração explícita. Restauração usa somente pasta nova e preserva o workspace atual.

O staging de importação contém arquivos em claro durante preparação; não há ZIP temporário em claro. Após queda podem restar diretórios de preparação, limpos no próximo início quando identificados como órfãos. Não há promessa de apagamento físico. Não há proteção contra atacante com controle integral da conta/máquina nem contra troca de junction exatamente durante a operação por esse atacante. A auditoria verifica o log inteiro por escrita (custo O(n)); corrupção/queda entre append e atualização da âncora falha fechada e exige conferência, sem reiniciar cadeia silenciosamente.

`git diff --check` dos arquivos da rodada não apontou erros. No diff geral há uma linha vazia adicional ao fim de `rotas/consulta.py`, que já estava alterado antes da rodada e não foi editado por esta correção; não foi feita limpeza fora da reserva.

## Próximo passo

SEC21–SEC25 encerram a correção de código autorizada, com os resultados e limites acima. Não foi reiniciado o processo operacional, migrado dado real, instalado o plugin, feito commit/push/merge ou alterado firewall/rede. A ativação controlada e a homologação geral permanecem etapas distintas: dependem de backup operacional consistente, proteção efetiva da mídia/perfil, tratamento das cinco reprovações e liberação final aplicável prevista em `AGENTS.md`/plano canônico. Não usar esta entrega como certificação de segurança integral do computador.
