# Cinco falhas gerais — 22/10/2026

> Retificação na rodada RP30, também em 22/10: o runner usado neste gate copiava `modelos/` antes de chamar a fixture, e `criar_modelo()` mantinha um DOCX já existente. Portanto a afirmação abaixo de uso exclusivamente sintético dos modelos no gate geral não é sustentada para todas as suítes. O resultado histórico 99/99 continua sendo o retorno observado, mas não comprova isolamento de modelos/assinaturas. RP30 removeu a cópia e reproduziu RED/GREEN com sentinelas fictícias, sem acessar ativos reais nesse teste. Nova passagem completamente isolada e limites em [Pesquisa aplicada](pesquisa-aplicada-cpj-2026-10-22.md). Os testes dirigidos que criaram seu próprio template fictício permanecem identificados como tal.

## Escopo e execução

Correção explicitamente autorizada pelo operador das cinco suítes reprovadas registradas em `revisoes/correcoes-seguranca-2026-10-21.md`. Trabalho na fila única RG26–RG29, preservando SEC21–SEC25 e os contratos da espinha dorsal. Não executa UN10–UN18. Somente código genérico e fixtures fictícias temporárias; sem chamadas de IA, casos reais, publicação ou ativação operacional.

| Falha original | Responsável | Diagnóstico e correção |
|---|---|---|
| Status visual | Dev sênior / RG26 | Corrigido destaque de entregue/concluído nas células, nos dois temas e hover; outros estados e escape de conteúdo preservados. Edge 2/2. |
| Identidade dos formulários | Dev sênior / RG26 | Corrigidos autocomplete, seleção de cargo/outro, edição/reset e máscara CPF sem completar dígitos. Edge 4/4. CPF da própria conta mantém contrato somente mascarado; sem ampliar backend. |
| Contrato de scripts da interface | Dev sênior / RG26 | Substituída expectativa artificial de um script por recursos efetivamente carregados/executados no Edge, sem CDN, erros de CSP ou submissão duplicada. RG26 1/1; L03 TUDO OK. |
| OCR / escrivão | Analista de Sistemas / RG27 | Motor ausente nesta sessão; pacote português já disponível. Corrigida divergência de prioridade entre descoberta e subprocesso. OCR português efetivamente executado: RG27 3/3, DadosOS 18/18, sem skips. |
| DOCX F04 | Segurança sênior / RG28 | Expectativas antigas de página PDF/quebra forçada conflitavam com regras atuais. Também reproduzidas falhas de normalização da assinatura e das citações; corrigidas e cobertas por regressões. |

CEFO: revisão independente de custo e impacto operacional concluída, somente leitura. Coordenação RG29: integração, suíte completa congelada, documentação e encerramento.

## Evidências dirigidas

DOCX: RED inicial F04 com duas reprovações; regressões adicionais demonstraram largura de 4 cm, nome/bloco e referências incompatíveis. Após correção: F04 5/5, RG28 5/5 e SIG01 12/12, sem skips. Testes preservam bytes da imagem fictícia e fontes por hash, proporção/largura de 4,5 cm, caixa alta/negrito, bloco sem quebra forçada, margens/timbre/rodapé/paginação/tabelas. Somente referência a página PDF gera `[OBTER: FOLHAS DOS AUTOS]` em vermelho no DOCX, sem inventar folhas nem alterar o Markdown. A renderização visual não foi realizada: `pdf2image` e LibreOffice indisponíveis; inspeção estrutural por OOXML/python-docx.

Interface: RED reproduzido em status (duas falhas) e identidade (oito subfalhas). Validação dirigida final do Dev: status 2 + identidade 4 + scripts 1 + relatórios UX01 6 + consentimento interface 5 + InterfaceF01 15 + web SEC21 13 = **46 testes**, mais L03 HTTP/browser TUDO OK; zero skips. Browser real verifica cores de todas as células, hover, escape de HTML, nomes/cargos/CPF, payloads, edição/reset e ausência de gravação duplicada. Os POSTs de observação de payload usam interceptação somente nos endpoints fictícios de teste; servidor, sessão e leitura/edição da conta usam workspace temporário.

OCR: RED reproduzido no fluxo DadosOS (17/18) e seleção de executável rival no PATH. Após correção e disponibilização explícita do motor temporário: RG27 3/3, DadosOS 18/18, OCR indisponível 10/10, desempenho/cache 7/7, extração 1/1 e checkpoint 22 verificações, todos executados sem skips. O teste exige relatório `tesseract (por)`, método OCR, escrivão/OS extraídos com origem na página 1 e SHA-256 do PDF preservado. Checkpoint cobre quatro páginas OCR, igualdade de métodos, reutilização, queda/retomada, DPI, refazer/outro PDF e transcrição visual. Não houve alteração no parser `dados_os.py` nem no extrator `extrair.py` sem defeito demonstrado.

## Revisão CEFO

Nenhum serviço hospedado/pago ou dependência operacional nova introduzido por RG26–RG28; nenhuma chamada de IA/API. Tesseract e idioma são locais, `reportlab` já consta das dependências de desenvolvimento e não foi acrescentado às de operação. O relatório não estima preços, ganhos de desempenho ou consumo sem medição.

CEFO confirmou cobertura sem skips silenciosos e ressaltou: motor em TEMP não certifica instalação após reinício; DOCX sintético/OOXML não homologa renderização do modelo oficial nem fluxograma; suítes da interface exigem processos separados. O runner canônico mantém um subprocesso/workspace por suíte. Ausência de OCR deve continuar visível como pendência, sem declarar uma página sem texto como extraída; regressão OCR01 cobre esse contrato.

## Ambiente OCR de verificação

Nenhum Tesseract encontrado no PATH nem nos diretórios de instalação conhecidos nesta sessão. `ferramentas/tessdata` já contém `por`, `eng` e `osd`. Extraído Tesseract `5.5.3.20260724` para `%TEMP%/cpj-ocr-tools-20261022/tesseract`, sem executar instalador, alterar PATH persistente ou configurações da Central. `--version` e `--list-langs --tessdata-dir` confirmaram executável e português.

Origem: [release upstream 5.5.3](https://github.com/tesseract-ocr/tesseract/releases/tag/5.5.3), binário indicado pela [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki), conforme [documentação Tesseract](https://tesseract-ocr.github.io/tessdoc/Downloads.html). SHA-256 do instalador extraído: `bee9e3434bd94fd65387d9be28cd467a41f61b1275383b55b0f59a1331270ae4`, igual ao digest do asset na API GitHub. Authenticode local retornou `UnknownError` de validade temporal do certificado; isso não foi apresentado como assinatura validada. O instalador não foi executado. Extração por executáveis portáteis do [7-Zip](https://www.7-zip.org/download.html); tentativa inicial de extração administrativa MSI foi bloqueada pela revisão automática e não executou.

Para repetir no ambiente temporário enquanto os arquivos existirem, configurar somente no processo de teste `CPJ_TESSERACT` para a pasta do executável, `TESSDATA_PREFIX` para o diretório local de idiomas e preceder a pasta do executável no PATH desse processo. Não usar disponibilidade em TEMP como instalação operacional persistente.

## Gate final

Produto e testes RG26–RG28 congelados. Executado `ferramentas/testar-tudo.py` na `.venv`, com as três variáveis temporárias de OCR declaradas acima: **99/99 suítes aprovadas, retorno 0**, soma dos tempos das suítes **589,11 s**, tempo total com clonagem/limpeza **734,28 s**. Fluxo HTTP completo `teste_central.py` isolado aprovado em 20,093 s. Nenhuma alteração de código/testes entre os hashes anteriores e posteriores ao gate (`changed_during_gate: []`). Os resultados históricos SEC21–SEC25 permanecem inalterados em seu relatório.

Log UTF-8 e evidências por suíte: `%TEMP%/cpj-rg29-final-20261022.log` e arquivo `.json` irmão, com código de retorno, duração, saída e hashes do candidato. Artefatos são temporários; esta tabela registra os resultados essenciais:

| Suíte que reprovava / nova regressão | Resultado no gate | Duração |
|---|---|---:|
| `teste_casos_status_visual_codex.py` | 2/2 | 16,328 s |
| `teste_identidade_form_codex.py` | 4/4 | 24,219 s |
| `teste_interface_claude.py` | TUDO OK, incluindo browser/HTTP | 8,954 s |
| `teste_dados_os_codex.py` | 18/18, OCR real | 16,453 s |
| `teste_docx_f04.py` | 5/5 | 1,406 s |
| `teste_interface_rg26.py` | 1/1 | 8,047 s |
| `teste_ocr_rg27.py` | 3/3, OCR português real | 2,453 s |
| `teste_docx_rg28.py` | 5/5 | 3,437 s |

**Skips separados de aprovação:** quatro cenários de `teste_executores_rv17.py` sem permissão para criar links simbólicos e um cenário exFAT de `teste_segredos_auditoria_sec22.py`, pois os clones do runner estão em volume NTFS com ACL. Esses cinco cenários não foram executados nesta passagem e não são contados como testes aprovados. As cinco suítes do pedido e as três regressões RG26–RG28 não tiveram skips; as antigas limitações OCR de desempenho/checkpoint desapareceram com o motor/idioma explicitamente disponíveis.

As suítes de segurança SEC21–SEC25 também retornaram zero nesta passagem. O cenário exFAT havia sido efetivamente executado na rodada SEC, com fixture em D, conforme registro histórico; isso não transforma o skip desta rodada em execução. `git diff --check` dos arquivos modificados nesta rodada retornou zero.

## Entrega e limites

Cinco falhas resolvidas no código/testes locais, revisão dos quatro papéis concluída e tarefas RG26–RG29 encerradas. Não foram usados autos, bancos, credenciais ou assinatura reais. Nenhuma nova dependência de operação ou serviço pago foi acrescentado; nenhuma chamada de IA foi feita.

A instalação em uso não foi reiniciada/atualizada, nem houve commit, push, merge, migração ou entrega de caso real. O motor OCR usado está somente em TEMP/ambiente de teste; disponibilização operacional persistente continua sujeita à liberação de instalação prevista no AGENTS. DOCX oficial não foi renderizado visualmente. Estes limites e os cinco skips impedem apresentar esta rodada como homologação irrestrita do computador ou conclusão da unificação.
