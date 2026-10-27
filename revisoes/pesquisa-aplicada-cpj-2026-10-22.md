# Pesquisa aplicada e revisão corretiva da Central CPJ — 22/10/2026

## Pedido e limites

O operador pediu aprofundar os pontos de adaptação de OpenAleph, IPED, Paperless-ngx, i2, Maltego, Timesketch e docassemble, confrontando as quatro prioridades com o projeto real. Delimitação explícita nesta sessão: **“Pesquisar e corrigir defeitos existentes; propor novas funções”**. Desenvolvimento RP30–RP34 na fila única; goal com ciclos de pesquisa, reprodução, correção mínima, revisão e regressão. Este registro não é outro plano de arquitetura nem executa UN10–UN18.

Preservar `caso.json`, SQLite derivado, originais imutáveis, fontes/versões, consentimentos, orçamento e as correções SEC21–SEC25/RG26–RG29. Somente código genérico e fixtures fictícias em diretórios temporários. Sem casos/bases/credenciais/assinaturas operacionais, inferência de IA, implantação, publicação, merge ou migração operacional.

## Frentes e situação

| Frente | Responsável | Evidência |
|---|---|---|
| Documentos, prévia e navegação até a fonte; Paperless/IPED | Dev sênior / RP31 | `pesquisa-dev-rp31.md`, concluída; segunda revisão UI em RP35 |
| Entidades, vínculos, transações e cronologia; OpenAleph/FtM/i2/Maltego/Timesketch | Analista de Sistemas / RP32 | `pesquisa-sistemas-rp32.md`, concluída e congelada |
| Atendimento à O.S., fontes, conferência e permissões; docassemble | Segurança sênior / RP33 | `pesquisa-seguranca-rp33.md`, correções e segunda revisão dirigidas concluídas |
| Custos, manutenção, licenças e prioridades | CEFO / RP34 | `pesquisa-cefo-rp34.md`, concluída |
| Consolidação, revisão e regressão | Coordenação / RP30 | Este documento; gate concluído e tarefas encerradas |

## Fontes e critérios de adaptação

Pesquisa em fontes oficiais, sem enviar conteúdo do workspace à internet. Funcionalidade documentada pelo fornecedor não equivale a comportamento testado na CPJ. As adaptações são propostas de engenharia, identificadas como tal; defeitos exigem reprodução local antes da alteração.

- [FollowTheMoney — statements](https://followthemoney.tech/docs/statements/): proveniência por valor, valor original antes da normalização, dataset/origem e metadados temporais. Aplicação candidata: cada informação ter fonte verificável, preservando divergências e identificadores incertos.
- [OpenAleph](https://openaleph.org/): ingestão, entidades, OCR e consultas estruturadas. Não confundir o software com autorização para enviar autos a instâncias públicas.
- [IPED — projeto e funcionalidades](https://github.com/sepinf-inc/IPED#features): visualizadores, marcadores, hashes, retomada e exportação de achados. Aplicação candidata: passar do achado à peça e ao localizador sem perder o contexto.
- [Paperless — versões e histórico](https://docs.paperless-ngx.com/usage/): a versão selecionada determina prévia/conteúdo; histórico de alterações e busca. [Fonte de PDF editing](https://github.com/paperless-ngx/paperless-ngx/blob/dev/docs/usage.md): rotação e exclusão de páginas podem alterar o original nessa ferramenta. Na CPJ, qualquer proposta equivalente deve operar somente em derivados; não copiar esse comportamento sobre `00-originais`.
- [i2 Analyst’s Notebook](https://i2group.com/solutions/i2-analysts-notebook): modelagem de entidades, vínculos, eventos e análise temporal/transacional.
- [Maltego Graph](https://www.maltego.com/graph/): exploração visual e integração de fontes. Propostas de navegação local não autorizam consultas externas nem transforms com dados de casos.
- [Timesketch — conceitos](https://timesketch.org/guides/user/basic-concepts/): timelines, comentários por investigação, etiquetas, consultas e narrativa ligada aos eventos. Datas de ocorrência, registro e processamento não devem ser tratadas como equivalentes.
- [docassemble — entrevistas](https://docassemble.org/docs/interviews.html): coleta condicional de informações necessárias ao resultado. Aplicação candidata: tornar visíveis lacunas e itens da O.S., sem substituir conferência humana ou interpretar preenchimento formal como prova de atendimento.

## O que aproveitar e em qual ordem

Esta ordem é uma avaliação de adequação ao uso solo e aos defeitos reproduzidos, não um ranking dos produtos. Esforço relativo é qualitativo, sem promessa de horas, economia ou desempenho. Todas as funcionalidades novas abaixo são **propostas, não implementadas**; devem entrar na fila e no ponto correspondente da unificação canônica quando autorizadas.

| Ordem | Padrão de referência | O que já existe na CPJ | Adaptação proposta e critério de aceite | Esforço / risco |
|---|---|---|---|---|
| 1 | IPED: origem + item; FtM: proveniência por valor | Busca com arquivo/página, folha quando conhecida, mapa com fontes; extração preserva bruto/método/hash | Navegação da afirmação ou valor até a peça/versão/localizador. Dois documentos discordantes preservam duas alegações, cada uma com sua fonte. Fonte original, transcrição, derivado e referência ficam identificados; folha ausente não vira número presumido | Médio; ligação incorreta pode atribuir informação ao caso/documento errado |
| 2 | docassemble: pedir/revisar somente informação necessária | O.S. transcrita, `solicitacoes-os.md`, relatórios por versão e gate de conferência | Revisão guiada de cada solicitação: atendida, parcial ou pendente, com fonte e trecho da resposta/ressalva. Confirmação humana vinculada à versão da minuta; editar a minuta exige reconferência. Marcar um item não comprova sua suficiência investigativa | Médio; falsa sensação de completude se checklist for tratado como julgamento automático |
| 3 | Paperless: versão selecionada e histórico; IPED: visualização e marcadores | PDF inline, prévia textual DOCX, versões de relatório, pendências OCR e checkpoints | Percurso de revisão enxuto com PDF e extração lado a lado, página/método/pendência e versão selecionada. Corrigir apenas derivados, preservar o hash original e distinguir edição de extração de alteração dos fatos | Baixo/médio se reutilizar o fluxo; DOCX textual não reproduz toda a diagramação |
| 4 | i2: direção e transações; Timesketch: tempo e contexto; FtM: valor bruto | CSV financeiro, cálculo Decimal, diagrama por titular/banco/conta e rótulos de transferência com data bruta | Estruturar eventos/transações antes dos filtros de data/valor. A→B 100 e B→A 40 continuam duas transferências, com recebido/enviado/saldo distintos; fuso ausente e data sem hora não ganham precisão. Guardar fonte, valor original, precisão e natureza de cada data | Médio/alto; dupla contagem, troca de sentido, confusão saldo/prejuízo ou sequência temporal inventada |
| Depois | Maltego: exploração por relações; Timesketch: views e notas | Grafo por O.S./termo, expansão limitada e revisão humana das correlações | Filtros estruturados e consultas salvas depois de existir contrato de eventos/fontes; notas analíticas com autor/contexto sem virarem fato documentado | Médio; manter filtros/limites explícitos e não propagar notas entre casos |

O ganho inicial vem de aproveitar os componentes atuais, não de instalar sete plataformas. CEFO verificou que adoção integral de plataformas com múltiplos serviços acrescentaria implantação, atualização, armazenamento e segurança ao uso solo; licenças e preços de produtos comerciais dependem da edição/contrato. Nenhuma compra, API paga ou dependência Python de operação foi acrescentada nesta rodada. A pesquisa resume padrões com links, sem copiar código dos projetos externos.

## Ciclos corretivos e defeitos comprovados

| Área | Reprodução antes da correção | Reparo mínimo / estado |
|---|---|---|
| Fonte do mapa | Caso A com caminho de B abria arquivo homônimo de A; página negativa virava âncora | Recusar contradição caso/caminho e aceitar página PDF somente como inteiro positivo. RP31: 4 testes Edge + 19 regressões, sem skips |
| Vínculo manual | Cadastro e rótulo desapareciam após reindexar; exclusão também apagava relação documental idêntica | Reutilizada fonte autoritativa ASTRA de eventos imutáveis e projeção transacional; exclusão só manual, conflito ambíguo não apaga. RP32 |
| Identidade de entidades | Mesmos dígitos cruzavam CPF com telefone; marcador incerto era removido; conta sem banco virava igualdade | Tipo participa do cruzamento; dúvida não gera chave exata; conta exige instituição documentada. Bruto preservado. RP32 |
| Folhas | “Consultar as fls. 30” no corpo virava folha física da página | Só marcador isolado inequívoco define folha; página e texto da remissão preservados. RP32 |
| Fonte da conferência | Junction em extração, documento ou ancestrais do caso aprovava texto externo como fato do caso | Checar componentes antes de resolver/ler; fonte inválida interrompe conferência. Diretório customizado normal explícito continua permitido. RP33 |
| Pendências e O.S. | `[OBTER: ...]`/`[PESQUISAR: ...]` aprovavam; continuação da O.S. em item 10+ era perdida | Marcadores bloqueiam entrega e continuidade aceita dois ou mais dígitos; vigência não é inferida. Override humano justificado preservado. RP33 |
| Transferência do histórico manual | Importador genérico ignorava mesmo ID divergente/aceitava evento malformado; arquivo na raiz reservada bloqueava diretório | União validada sob trava antes de confirmar casos; recusa divergência/ramificação/caminho reservado inválido. Eventos não são publicados como extras comuns; lock não é exportado. RP30: 7 testes dirigidos aprovados |
| Consumidor do grafo | Texto persistido executava JavaScript no clique por interpolação em handler; nome com apóstrofo quebrava modal; cadastro perdia O.S./observação; remoção invertia direção e omitia caso | Closures recebem dados sem interpolar código; formulário envia `caso`/`obs`; remoção usa extremos e fonte da aresta real. RP35: 4 testes Edge + 21 regressões, zero skips; sem nova tela ou função |
| Isolamento dos testes | Runner copiava a pasta de modelos do operador; fixture não substituía DOCX existente | Removida a cópia. Sandbox recebe apenas modelo geométrico gerado. RED/GREEN com assinatura/modelo/defaults sentinelas fictícios, 1 teste aprovado. Retificação explícita no relatório anterior; novo gate deve comprovar esse isolamento |

A fonte manual foi reaproveitada do código próprio ASTRA `f981f90929d56b2221d26302d9f3e602c349333c`, mantendo `caso.json` e SQLite derivado. Não representa integração de branches, execução global UN10–UN18 ou substituição da arquitetura. APIs existentes de criação/exclusão do grafo conservam `ok`, acrescentam ID/versão e indicação de projeção pendente; conflito recebe 409 e ausência manual 404, preservando arestas documentais. RP35 adequa o consumidor existente; não foi criada API concorrente.

Históricos de vínculos em pacotes são limitados a 64 MiB para validação em memória; documentos mantêm o limite total anterior de 2 GiB/10.000 arquivos. Pacote excedente falha explicitamente, sem truncar histórico. Eventos são imutáveis e serializados, mas a publicação de vários arquivos/casos não é uma transação global de sistema de arquivos; falha de disco pode exigir retomada. Não prometer atomicidade global.

### Retificação da evidência anterior

A leitura do runner e de `fixtures_docx.criar_modelo` demonstrou que o gate histórico RG29 não garantia modelo exclusivamente sintético: a cópia vinha antes da chamada e o helper retornava o arquivo existente. Não há base para afirmar que todos os testes anteriores excluíram modelos/assinaturas locais. O código corretivo desta rodada não copia `modelos/`; a regressão usa somente sentinelas privadas fictícias e confirma ausência delas, geração de DOCX geométrico e ausência de defaults do operador na sandbox. O resultado anterior foi preservado como histórico com ressalva, não reescrito como aprovação retroativa. Nenhuma conclusão de segurança da instalação pode ser baseada somente naquele resultado.

## Verificação

Dirigidos: RP31 4/4 Edge + 19 regressões; RP32 12/12 + 38 regressões; RP33 8 aprovados e 2 skips de symlink de arquivo, com 39 regressões e 14 repetidas após a correção ancestral; RP35 4/4 Edge + 21 regressões; RP30 transferência 7/7 e isolamento do runner 1/1. As seleções têm sobreposição e não devem ser somadas como total único de testes independentes. Junctions reais foram exercidas; os dois symlinks ignorados não são aprovações. Segurança repetiu independentemente os sete testes de transferência e não encontrou outro defeito reproduzível nessa revisão.

Gate congelado concluído: `.venv/Scripts/python.exe -X utf8 ferramentas/testar-tudo.py`, com Tesseract real em português apontado somente por `CPJ_TESSERACT`, `TESSDATA_PREFIX` e PATH do processo. **105/105 suítes retornaram zero**, sem reprovação; sete cenários ignorados por ambiente, explicitados abaixo. Soma dos tempos das suítes **722,21 s**; total incluindo clonagem/limpeza **907,94 s**. Fluxo HTTP completo isolado retornou zero/TUDO OK em 20,718 s. Hashes de código/testes antes e depois não mudaram (`changed_during_gate: []`). O runner gera exclusivamente o template geométrico.

Log UTF-8 e JSON por suíte com saída, retorno, tempos e hashes: `%TEMP%/cpj-rp30-final-20261022.log` e `.json` irmão. São artefatos locais temporários; os dados essenciais ficam registrados aqui:

| Nova suíte | Resultado no gate | Tempo |
|---|---|---:|
| `teste_rastreabilidade_rp31.py` | 4 aprovados, sem skips | 21,719 s |
| `teste_integridade_vinculos_rp32.py` | 12 aprovados, sem skips | 9,250 s |
| `teste_fontes_os_rp33.py` | 8 aprovados, 2 ignorados | 2,781 s |
| `teste_grafo_interface_rp35.py` | 4 aprovados, sem skips | 26,156 s |
| `teste_transferencia_vinculos_rp30.py` | 7 aprovados, sem skips | 2,703 s |
| `teste_runner_isolamento_rp30.py` | 1 aprovado, sem skips | 2,109 s |

Essas seis suítes novas têm 38 cenários: **36 aprovados efetivamente e 2 ignorados**. Os tempos são de verificação, não benchmark de melhoria.

Skips do gate completo, sem convertê-los em aprovação: quatro cenários de symlink em `teste_executores_rv17.py`; dois symlinks de arquivos individuais em `teste_fontes_os_rp33.py` por falta de privilégio Windows; um cenário exFAT de `teste_segredos_auditoria_sec22.py`, pois o clone fica em NTFS. Junctions reais de extração/caso/ancestrais foram executadas. As cinco reprovações antigas RG26–RG29 também retornaram zero neste novo ambiente. A passagem histórica 99/99 permanece com sua retificação, não é usada para comprovar esta rodada.

Revisão dos quatro papéis e dois ciclos corretivos concluídos, com revisão cruzada que encontrou e corrigiu a variante ancestral de junction, o ataque ao diretório reservado do pacote e os defeitos do consumidor do grafo. Todos os achados reproduzidos descritos acima têm reparo e regressão; `git diff --check` dos arquivos rastreados desta rodada retornou zero. Nenhuma alegação de ausência universal de vulnerabilidades ou homologação irrestrita decorre desses resultados.

## Limites operacionais

Não houve instalação, atualização/reinício da Central em uso, reindexação operacional, migração de dados reais, commit, push, merge ou chamada de IA. Índices antigos podem conservar chaves incertas até uma reindexação autorizada. A migração aditiva e idempotente do legado manual foi testada somente em fixtures; sua execução operacional precisa preservar o índice antigo até capturar os vínculos nele existentes.

O motor OCR da verificação está em TEMP e não comprova instalação persistente após reinício. A prévia DOCX continua textual, e o modelo oficial não foi homologado visualmente nesta rodada. Conferência sintática/documental e checklist não certificam suficiência investigativa, autoria ou autenticidade. As salvaguardas de caminhos tratam links/junções estáticos; não são sandbox do SO contra controle hostil integral da conta.
