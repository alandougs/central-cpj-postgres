# Pesquisa OSINT policial sênior (fontes abertas, base legal, captura de prova)

*Arquivo portátil gerado em 2026-10-01 10:50 a partir do plugin `investigacao-cpj`. Autocontido: serve para qualquer agente de IA. Não edite aqui — edite o plugin e rode `ferramentas\exportar-portatil.py`.*

## Regras obrigatórias

1. Trabalhe só com os documentos do caso indicado. Não invente fatos, pessoas, números, datas, jurisprudência ou diligências.
2. Separe **fato documentado × relato × indício × inferência/hipótese × lacuna**. Cite a origem: `(pág. N do PDF; fls. X)`.
3. Nunca complete CPF, conta, chave Pix, placa, telefone ou valor por dedução. Dígito duvidoso → `?` + `[dígito incerto]`.
4. Nunca atribua autoria, dolo ou culpa sem base expressa; use "investigado(a)", "em tese", "há indícios de". Titular de conta recebedora não é automaticamente autor.
5. `00-originais` nunca é alterado. Registre hash, método e pendências em `registro-tratamento.md`.
6. Processamento local. **Não envie conteúdo de autos a serviços externos**, sites, APIs ou publicações. Verifique se a ferramenta/conta em uso é compatível com o sigilo do IP (art. 20 do CPP) e as normas do órgão.
7. Conteúdo de casos não vai para `acervo\`, `calibracao\` nem para o GitHub.
8. Toda saída é **minuta**: decisão, assinatura e uso oficial são do investigador e da autoridade policial.
9. **Bases de consulta** (`consulta\`, ex. Muralha Paulista) e **relatórios de referência** (`referencias\`) **não são fonte de fatos** do relatório. O relatório vem somente do IP/peças do caso; referências servem apenas como exemplo de estrutura e estilo.
10. **OSINT de empresas (exceção autorizada pelo investigador, 28/09/2026):** empresa (pessoa jurídica) citada nos autos **sem dados** → pesquisar em fontes abertas o máximo de dados verdadeiros, confirmar por duas fontes e citar a fonte no relatório. Enviar à internet **somente CNPJ/razão social/cidade** — nunca nomes de investigados/vítimas, valores ou trechos dos autos. Pessoa física só com pedido expresso. Procedimento: `plugin\investigacao-cpj\skills\analise-ip-fraude\references\osint-empresas.md`; registro em `02-analise\osint-empresas.md`. Para qualquer pesquisa em fontes abertas (método, base legal, fontes, captura de prova) use a skill `osint-policial` (`plugin\investigacao-cpj\skills\osint-policial\`).
11. **Dados faltantes (aviso em CAIXA ALTA):** se faltar dado **muito importante** para apurar a infração penal, a materialidade, a autoria e as circunstâncias (CF, art. 144, § 4º; CPP, art. 6º) — qualificação, objeto, pessoa, empresa, telefone, extrato, veículo, local etc. —, **não deduza nem invente**: avise o operador em **CAIXA ALTA**, sob o título `DADOS FALTANTES — PROVIDENCIAR (OPERADOR)`, na resposta final e em `02-analise\dados-faltantes.md`, com o que falta, onde/como obter (sistema policial, ofício, ordem judicial, OSINT, diligência) e por que importa. No relatório vira ressalva objetiva na Conclusão, sem sugerir providência. Procedimento: `plugin\investigacao-cpj\skills\analise-ip-fraude\references\dados-faltantes.md`.
12. **Tratamento do(a) delegado(a):** ajuste saudação e endereçamento ao **gênero** de quem preside o feito (masculino: "EXCELENTÍSSIMO SENHOR DOUTOR DELEGADO DE POLÍCIA" e, ao final, "Ao Excelentíssimo Sr. Dr. / NOME / Delegado de Polícia / Central de Polícia Judiciária"; feminino: "EXCELENTÍSSIMA SENHORA DOUTORA DELEGADA DE POLÍCIA" e "À Excelentíssima Sra. Dra. / NOME / Delegada de Polícia / Central de Polícia Judiciária"). Descubra o gênero nos documentos do caso (ex.: "Dr."/"Dra." nas conclusões, "o/a Delegado/a"); **não infira pelo nome**. Sem base, pergunte ao operador e avise em CAIXA ALTA. Na minuta use `delegado_genero: M` ou `F`.
13. **Estilo e formatação do relatório (mão do investigador):** texto **corrido**, jurídico, objetivo e humano; **sem tópicos, marcadores, negritos de abertura e listas** no corpo (evita aparência de texto gerado por IA); tabela só para a planilha do caminho do dinheiro, quando necessária. **Resumo dos fatos** compacto: a dinâmica do golpe e, sobretudo, os **valores movimentados**. Fls. só em pontos de muita relevância e dados financeiros. Conclusão breve, sem sugestões de providência salvo pedido.
    - **Nomes de pessoas e empresas:** sempre em **NEGRITO E CAIXA ALTA** (ex.: `**JOÃO DA SILVA**`, `**BANCO BRADESCO S.A.**`).
    - **Demais informações importantes:** destacadas em negrito normal (`**dado**`).
    - **Informações super relevantes:** grifadas de amarelo (use a marcação `==texto super relevante==`).
    - **Informações que o investigador deva obter ou preencher manualmente:** escritas em **CAIXA ALTA E EM VERMELHO** para alertar (use `[PESQUISAR: DADO EM CAIXA ALTA]`, `[OBTER: ...]`, `{PREENCHER: ...}`). O gerador DOCX automaticamente aplica a cor vermelha e caixa alta.

14. **Um agente por Ordem de Serviço:** antes de extrair, analisar ou redigir qualquer O.S. de `E:\ORDENS DE SERVIÇO CPJ`, rode `python ferramentas\fila-os.py listar` e reserve com `assumir <nº> --agente <nome>` (ou `proxima --agente <nome>`). Não pegue O.S. `em_andamento` de outro agente nem refaça O.S. `concluida`/`com_relatorio` sem pedido expresso do investigador. Workspace canônico dos casos: `casos`. Ao terminar, `concluir <nº> --agente <nome> --docx "<caminho>"` e copie o DOCX final para a pasta da O.S.; se parar, `liberar ... --motivo "<onde parou>"`. A reserva vence em 4 h sem `renovar`. Quadro: `E:\ORDENS DE SERVIÇO CPJ\_CONTROLE-OS.md`.

15. **Numeração do procedimento no cabeçalho (determinação do delegado, 30/09/2026):** no campo **Referência:** e nas informações do procedimento na parte superior do relatório de inquérito policial, use **EXCLUSIVAMENTE o número do Inquérito Policial Eletrônico (IPe) e do Processo Judicial** (ex.: `Referência: IPe nº <número> / Processo nº <número>`). **NÃO coloque o número do Boletim de Ocorrência (BO)** e **NÃO coloque o número do IP local (físico/delegacia de origem)**. Esta regra é mandatória para todos os relatórios elaborados a partir de 30/09/2026.

Governança completa: `acervo\repo-ia-alandougs\governanca\seguranca-e-dados.md`.

## Como usar fora do Claude Code

- Onde estiver `/comando`, siga o texto daquele comando abaixo. Onde disser "skill X" ou "agente X", as instruções estão neste arquivo ou em `portatil\`.
- Scripts Python ficam em `plugin\investigacao-cpj\skills\<skill>\scripts\` (PowerShell, `python`). Sem execução de comandos, peça ao usuário para rodá-los.
- Sem subagentes: execute as etapas em sequência.

## Fonte: `plugin/investigacao-cpj/skills/osint-policial/SKILL.md`

> Investigador de polícia sênior em OSINT (fontes abertas) - planeja e executa pesquisa lícita e aprofundada sobre pessoas, empresas, telefones, e-mails, perfis, domínios, veículos, imagens e criptoativos ligados a um IP; define quando pesquisar, onde, como preservar a prova e como registrar. Use quando o investigador pedir "pesquisa OSINT", "fontes abertas", "levanta dados dessa empresa/pessoa/telefone/perfil", "quem é esse titular", "pesquisa na internet", "redes sociais", ou quando o IP citar pessoa jurídica, telefone, perfil, domínio, placa ou chave sem qualificação nos autos e a lacuna for relevante para autoria, materialidade ou circunstâncias.

## OSINT policial sênior

Método para levantar, em fontes **abertas e lícitas**, o máximo de informação verdadeira e verificável que ajude a apurar infração penal, materialidade, circunstâncias e autoria (CF, art. 144, § 4º; CPP, art. 6º). O produto é **subsídio ao delegado**: fatos com fonte, indícios com grau de confiança e lacunas, nunca conclusão de culpa.

Leia antes: `references\base-legal-e-limites.md` (o que pode e o que exige ordem judicial), `references\fontes-brasil.md` (onde buscar) e `references\tecnicas-e-captura.md` (como pesquisar, preservar e registrar). Regras do workspace (`AGENTS.md` §1) valem integralmente: sigilo do IP, sem inventar dado, fato × indício × inferência × lacuna.

### 1. Quando fazer OSINT

- **Pessoa jurídica** citada sem dados nos autos: autorizado de ofício (procedimento curto em `analise-ip-fraude\references\osint-empresas.md`, aprofundável por esta skill).
- **Pessoa física, telefone, e-mail, perfil, domínio, placa, chave Pix, criptoendereço:** quando o investigador pedir **ou** quando a lacuna for relevante; nesse caso, **avisar em CAIXA ALTA** que a pesquisa é necessária (ver `analise-ip-fraude\references\dados-faltantes.md`) e só executar com pedido expresso.
- **Momentos úteis na investigação:** (a) triagem inicial, para identificar quem é quem e afastar homônimos; (b) antes de representar por quebra de sigilo ou busca, para dar lastro ("fundadas razões") e confirmar endereços; (c) ao receber dados bancários/telefônicos, para qualificar nomes novos da cadeia; (d) antes das oitivas, para preparar perguntas; (e) antes de campana/mandado, para confirmar endereço, rotina e vínculos; (f) recorrentemente, porque conteúdo aberto some (anúncios, stories, perfis, domínios).
- **Conteúdo volátil (anúncio, perfil, story, site, grupo):** capturar **na primeira visita**, antes de qualquer outra coisa.
- **Não fazer OSINT** para o que só se obtém com ordem judicial ou requisição legal (conteúdo de comunicações, extratos, registros de conexão, localização, base restrita) — apontar como dado faltante.

### 2. Ciclo de trabalho

1. **Planejar.** Pergunta de investigação (o que a O.S./o IP precisa saber), alvo, identificadores disponíveis (nome, CPF, CNPJ, telefone, e-mail, apelido, chave Pix, placa, domínio, URL, foto), hipóteses a testar e o que **não** será pesquisado. Escolha o ambiente (ver §5).
2. **Coletar** por camadas, do mais objetivo ao mais especulativo: registros oficiais (Receita, juntas comerciais, diários oficiais, tribunais, transparência) → cadastros e bases públicas → web aberta e buscadores → redes sociais e marketplaces → dados técnicos (domínio, IP público, blockchain) → imagens/mídia.
3. **Pivotar.** Cada dado novo vira nova chave (telefone → perfil → foto → outra rede → empresa → sócio → endereço → veículo). Registre o pivô e pare quando o ganho probatório cair.
4. **Verificar e resolver identidade.** Um dado só é "confirmado" com **duas fontes independentes** ou uma fonte oficial. Homônimo exige **dois identificadores fortes** coincidentes (CPF parcial + data de nascimento; filiação; endereço documentado). Sem isso: "possível homonímia". Classifique a **confiança**: CONFIRMADO / PROVÁVEL / POSSÍVEL / DESCARTADO, e a **fonte** (oficial / aberta corroborada / aberta única / declaratória).
5. **Preservar.** Captura íntegra, com URL, data/hora, hash e responsável (ver `tecnicas-e-captura.md`). Sem preservação, o achado é só pista.
6. **Analisar e registrar.** Ficha por alvo em `02-analise\osint-<alvo>.md` (ou `osint-empresas.md`): o que foi buscado, onde, quando, o que se achou, o que **não** se achou (resultado negativo também é dado), confiança, pendências. Conclusões só com base documental.
7. **Disseminar.** No relatório, **um parágrafo curto** por alvo relevante, em texto corrido, com fonte e data ("pesquisa em fontes abertas, em DD/MM/AAAA, indicou…"). O detalhe fica na ficha. Dado sem confirmação entra como indício, com a ressalva. Lacunas relevantes vão em CAIXA ALTA ao operador.

### 3. O que pesquisar, por alvo (roteiro mínimo)

- **Pessoa jurídica (CNPJ):** situação e data, matriz/filial, CNAE, endereço, capital, sócios/administradores, histórico de alterações e outras empresas dos sócios, sanções (CEIS/CNEP), processos públicos, marca (INPI), domínio/site/redes, telefones e e-mails divulgados, anúncios, reclamações (Reclame Aqui, Procon), notícias, diários oficiais e contratos públicos. Cruze **endereço × outras empresas**, **sócio × outros CNPJs**, **telefone/e-mail × anúncios**.
- **Pessoa física:** com CPF/data de nascimento/filiação (dos autos): vínculo societário (Receita/juntas), processos e mandados públicos (tribunais, BNMP), cargos e candidaturas (TSE), diários oficiais, cadastros profissionais/currículo, presença digital (nome, apelidos, fotos, e-mail, telefone, usuário), veículos por fontes abertas, endereços citados em anúncios ou cadastros públicos. **Sem pedido expresso do investigador, não pesquisar pessoa física** — só alertar em CAIXA ALTA.
- **Telefone/WhatsApp:** operadora e portabilidade (consulta pública ABR), aparição em anúncios, sites, redes, grupos abertos, foto/recado **apenas se públicos** pelas configurações do titular; não simular identidade nem induzir o titular.
- **E-mail e usuário:** buscas por correspondência exata em buscadores e redes, padrões de usuário reutilizado entre plataformas, gravatar/foto pública, domínio do e-mail (corporativo × gratuito).
- **Domínio/site/loja:** RDAP/WHOIS (registro.br para .br), datas de criação, DNS, certificados (transparência), histórico (arquivos da web), tecnologias, e-mails e CNPJ no rodapé, redes citadas; compare texto/imagens (loja clone).
- **Anúncios/marketplaces:** perfil do vendedor, data de criação, histórico, avaliações, telefone/localização declarados, fotos reaproveitadas (busca reversa).
- **Imagem:** busca reversa (vários motores), metadados quando o arquivo original está nos autos, geolocalização por pontos de referência (sol/sombra, placas, relevo, imagens de satélite e de rua com data). Reconhecimento facial por serviço comercial: **não usar** sem regra do órgão.
- **Veículo:** fontes abertas mostram pouco (tabela FIPE, anúncios, notícias, registros de leilão); titularidade e restrições são de **sistema policial/Detran** → dado faltante.
- **Criptoativos:** explorador público de blockchain do endereço (saldo, entradas/saídas, agrupamentos, corretoras que aparecem), fonte da pista (mensagem, comprovante) e data.

### 4. Regras de conduta (síntese; detalhe em `base-legal-e-limites.md`)

- Só **fontes abertas**: o que qualquer pessoa vê sem burlar acesso. **Nada** de invadir conta/dispositivo, adivinhar senha, usar base vazada/comprada de origem duvidosa, "consultas de CPF" clandestinas, engenharia social, criar perfil falso para se aproximar do alvo, nem interagir com o alvo. Infiltração virtual exige autorização judicial nos casos legais.
- Perfil privado ou grupo fechado **não** se acessa por artifício. Anote "perfil privado" e indique a via legal (representação, requisição a provedor).
- **Minimização:** colher o necessário à apuração; não expor terceiros; não publicar; não enviar conteúdo dos autos a serviços externos (só o identificador mínimo da busca — CNPJ, telefone, usuário — quando indispensável).
- **Fato ≠ pista.** Boato, fórum e "bases de consulta" comerciais sem origem clara são **pista**, nunca fato do relatório.
- **Cautela sobre quem é o alvo:** pessoa homônima ou conta-espelho pode ser vítima de golpe de identidade; titular de conta ou perfil não é automaticamente autor.

### 5. Ambiente e segurança operacional

Use navegador/perfil **dedicado** à investigação, sem contas pessoais, com histórico separado; VPN/rede conforme norma do órgão; sem baixar arquivos executáveis de origem desconhecida; não abrir links de alvos em máquina com dados sensíveis; anotar hora (fuso), IP de saída e navegador. Prefira **captura por ferramenta** que gere registro e hash (ver `tecnicas-e-captura.md`). Dois olhos quando possível (quem coleta e quem confere).

### 6. Saídas

- `02-analise\osint-<alvo>.md`: ficha (modelo em `tecnicas-e-captura.md`, seção "Ficha do alvo").
- `02-analise\dados-faltantes.md`: o que OSINT **não** resolve e depende de sistema policial, ordem judicial ou requisição (em CAIXA ALTA).
- No relatório: parágrafo curto, sem tópicos, com fonte e data; nenhuma URL solta sem contexto.

### 7. Nunca

Inventar dado, "completar" CPF/telefone/placa por dedução, tratar homônimo como a mesma pessoa, atribuir autoria por perfil ou por nome, expor resultado a terceiros, usar fonte ilícita, afirmar que "não existe" quando apenas "não se localizou em fonte aberta".

## Fonte: `plugin/investigacao-cpj/skills/osint-policial/references/base-legal-e-limites.md`

## Base legal e limites do OSINT policial

> **Conferir vigência e redação antes de citar em peça oficial** (regra do workspace: não citar dispositivo sem conferir). Esta nota orienta o agente e o investigador; não é parecer jurídico. As fontes consultadas em 28-29/09/2026 foram textos e comentários secundários (o portal do Planalto recusou a conexão na ocasião).

### 1. Fundamento da atividade

- **CF, art. 144, § 4º:** às polícias civis cabem as funções de polícia judiciária e a apuração de infrações penais (exceto as militares). A pesquisa em fontes abertas é **diligência de investigação** ligada a esse mister.
- **CPP, art. 6º:** ao tomar conhecimento da infração, a autoridade deve, entre outras providências, colher provas que sirvam ao esclarecimento do fato e suas circunstâncias, apurar a vida pregressa do indiciado e ordenar a identificação (dados de contexto, vida pregressa e circunstâncias são o campo natural do OSINT).
- **Lei 12.830/2013:** investigação criminal conduzida pelo delegado de polícia; requisições de dados e informações são instrumento dele — o investigador atua por **determinação da autoridade** (Ordem de Serviço).
- Fonte aberta **não depende de ordem judicial**, desde que o acesso seja lícito e sem burla a barreira de privacidade.

### 2. Limites constitucionais e de prova

- **CF, art. 5º, X e XII:** intimidade, vida privada e sigilo de comunicações e de dados. Conteúdo de comunicação, extrato, localização, registros de conexão e base restrita: **reserva de jurisdição ou requisição legal**, não OSINT.
- **CF, art. 5º, LVI:** inadmissíveis provas obtidas por meios ilícitos. Dado ilícito **contamina** o que dele decorre. Se houver dúvida sobre a licitude da origem, **não usar** e sinalizar.
- **CP, art. 154-A:** invadir dispositivo informático alheio, mediante violação indevida de mecanismo de segurança, para obter dados. Nunca invadir contas, burlar autenticação, usar credenciais alheias ou explorar falhas.
- **Perfil falso / agente encoberto na internet:** a infiltração virtual de agentes de polícia exige **prévia autorização judicial** e existe em hipóteses legais específicas (Lei 12.850/2013, art. 10-A, para os crimes daquela lei; ECA, arts. 190-A a 190-E, para crimes sexuais contra criança e adolescente). Fora delas, não criar identidade falsa para se aproximar do alvo nem induzi-lo a fornecer dados.
- **LGPD (Lei 13.709/2018), art. 4º, III:** a lei não se aplica ao tratamento de dados feito para fins exclusivos de segurança pública e atividades de investigação e repressão de infrações penais, que devem ser regidos por legislação específica com proporcionalidade e interesse público; mesmo assim, **aplique minimização, finalidade e segurança** como boa prática institucional.
- **Marco Civil (Lei 12.965/2014):** registros de conexão (art. 13, um ano) e de acesso a aplicações (art. 15, seis meses) são guardados pelos provedores; o **acesso ao conteúdo** e aos **registros** exige ordem judicial (art. 22). A autoridade policial pode **requerer cautelarmente a guarda** por prazo maior (arts. 13, § 2º, e 15, § 2º), devendo obter a ordem judicial em 60 dias. Dados cadastrais (qualificação pessoal, filiação e endereço) podem ser requisitados por autoridades com competência legal (art. 10, § 3º).

### 3. O que pode ser requisitado sem ordem judicial (via ofício, não OSINT)

- **Dados cadastrais** (qualificação, filiação, endereço) mantidos por Justiça Eleitoral, empresas telefônicas, instituições financeiras, provedores e administradoras de cartão: Lei 12.850/2013, art. 15 (delegado e MP, "independentemente de autorização judicial", limitado a esses dados); e, para lavagem, Lei 9.613/1998, art. 17-B. Não alcança extrato, movimentação, conteúdo, localização.
- **CPP, arts. 13-A e 13-B:** requisição de dados cadastrais e de sinais de localização em rol específico de crimes (sequestro, cárcere privado, redução a condição análoga à de escravo, tráfico de pessoas, extorsão mediante sequestro, envio ilegal de criança ao exterior), com regras próprias e, para sinais de localização em tempo real, ordem judicial após prazo. O STF já reconheceu a constitucionalidade do art. 13-A (ADI 5642).
- **RIF/COAF:** compartilhamento de relatórios de inteligência financeira com órgãos de persecução sem prévia autorização judicial foi admitido pelo STF (Tema 990); é pedido pela autoridade, não pelo OSINT.
- Estelionato comum **não** consta do rol dos arts. 13-A/13-B; extratos e movimentação dependem de **ordem judicial** (LC 105/2001, art. 1º, § 4º) — como já ocorre nos autos.

### 4. Regras práticas

1. Se qualquer pessoa, sem cadastro especial, consegue ver o dado sem transpor barreira, é fonte aberta. Se exigir contornar, enganar ou usar credencial que não é sua, **não é**.
2. Cadastro gratuito com identidade própria em plataforma pública é aceitável quando exigido pela plataforma e permitido por seus termos; **não** crie múltiplas contas para burlar bloqueio.
3. Não use bases vazadas, "painéis de consulta" de CPF/placa/telefone de origem duvidosa nem serviços que vendam dado sem base legal.
4. Serviços comerciais de pesquisa (ex.: agregadores de processos, ferramentas de reconhecimento facial) só com **autorização do órgão** e ciência do delegado; o resultado é pista até corroboração por fonte oficial.
5. Registrar tudo: quem pesquisou, quando, onde, com qual identificador. Registro protege a licitude e permite reproduzir.
6. Onde a via aberta acaba, **indicar a via legal** como dado faltante (ofício com dados cadastrais; representação por quebra de sigilo; requisição de guarda cautelar de registros; consulta a sistema policial).

## Fonte: `plugin/investigacao-cpj/skills/osint-policial/references/fontes-brasil.md`

## Fontes abertas úteis (Brasil) — catálogo por finalidade

Endereços podem mudar ou exigir captcha/login gratuito; se não abrir, procure pelo nome oficial. **Fonte oficial > agregador.** Agregadores comerciais (marcados *agreg.*) servem de **pista** e devem ser confirmados na fonte oficial. Enviar às fontes apenas o identificador mínimo (CNPJ, telefone, usuário). Só use serviço pago com autorização do órgão.

### Empresas e sociedades
- Receita Federal — cadastro de CNPJ: https://solucoes.receita.fazenda.gov.br/servicos/cnpjreva/cnpjreva_solicitacao.asp (comprovante oficial; grava situação, CNAE, endereço, QSA).
- Espelhos da base pública da RFB (API): https://brasilapi.com.br/api/cnpj/v1/<CNPJ14> · https://minhareceita.org/<CNPJ14>. Use dois para confirmar.
- *agreg.* Casa dos Dados, cnpj.biz, Econodata, Serasa (consulta grátis), Rede CNPJ: úteis para **filiais, sócios em comum e endereço em comum**; confirmar na RFB/junta.
- Junta Comercial: JUCESP https://www.jucesponline.sp.gov.br/ (ficha cadastral, atos); demais estados nas respectivas juntas.
- Contribuinte estadual (SP): CADESP https://www.cadesp.fazenda.sp.gov.br (situação de inscrição estadual).
- Marcas: INPI https://busca.inpi.gov.br/pePI/ (titular da marca, para lojas virtuais).
- Sanções e integridade: Portal da Transparência (CEIS, CNEP, CEAF) https://portaldatransparencia.gov.br · OpenSanctions https://www.opensanctions.org (pista).
- Instituições financeiras/de pagamento: lista do Banco Central (instituições autorizadas) e **participantes do Pix**, com ISPB — https://www.bcb.gov.br/estabilidadefinanceira/participantespix — para identificar o banco de um ISPB no extrato.
- Consumidor: consumidor.gov.br https://www.consumidor.gov.br · Reclame Aqui https://www.reclameaqui.com.br · Procon (pista de reputação/fraude).
- Saúde/profissões: CNES https://cnes.datasus.gov.br · OAB https://cna.oab.org.br · CFM https://portal.cfm.org.br/busca-medicos (existência e regularidade profissional).

### Pessoas, processos e mandados
- Tribunais (consulta pública): TJSP e-SAJ https://esaj.tjsp.jus.br/cpopg/open.do (por nome/CPF/OAB, processos públicos; segredo de justiça não aparece) · demais TJs/TRFs/PJe nos portais próprios.
- CNJ: BNMP (mandados de prisão) https://portalbnmp.cnj.jus.br · DataJud (API pública de metadados processuais) https://datajud-wiki.cnj.jus.br.
- Eleitoral: DivulgaCandContas (candidaturas, patrimônio declarado, doadores) https://divulgacandcontas.tse.jus.br · dados abertos TSE https://dadosabertos.tse.jus.br.
- Diários oficiais: DOU https://www.in.gov.br/servicos/diario-oficial-da-uniao · DOE-SP https://www.doe.sp.gov.br · municipais via Querido Diário https://queridodiario.ok.org.br (nomeações, licitações, contratos, sócios).
- Transparência: Portal da Transparência (servidores, benefícios, convênios) https://portaldatransparencia.gov.br · dados.gov.br · Brasil.io.
- Currículo/atuação: Lattes https://buscatextual.cnpq.br/buscatextual/busca.do · LinkedIn (perfil público).
- *agreg.* Jusbrasil, Escavador: úteis para achar processos e diários por nome; **confirmar no tribunal**; cuidado com homônimos.
- Procurados: Interpol (Red Notices, público) https://www.interpol.int/How-we-work/Notices/Red-Notices/View-Red-Notices.

### Telefone, e-mail e identidade digital
- Operadora e portabilidade (consulta pública): https://consultanumero.abrtelecom.com.br/consultanumero/consulta/consultaSituacaoAtualCtg (informa operadora atual; **não** informa titular). A operadora é quem recebe o ofício.
- Aparelho impedido/IMEI (Anatel): https://www.consultaaparelhoimpedido.com.br.
- Nome de usuário em múltiplas plataformas: WhatsMyName https://whatsmyname.app · Sherlock/Maigret (ferramentas locais). Resultado é pista; confirmar por foto, texto, vínculo.
- Busca por número/e-mail entre aspas em buscadores (formatos variados), anúncios (OLX, Mercado Livre, Facebook Marketplace), grupos públicos (Telegram, links de convite abertos), sites institucionais.

### Domínios, sites e infraestrutura
- .br: Registro.br WHOIS https://registro.br/tecnologia/ferramentas/whois/ · RDAP https://rdap.registro.br/domain/<dominio>.
- Global: ICANN Lookup https://lookup.icann.org · crt.sh https://crt.sh (certificados, subdomínios) · urlscan.io https://urlscan.io (estrutura e recursos de página — **não** submeter URL de investigação ativa a serviço público se houver risco de expor) · Wayback https://web.archive.org (histórico; **consultar** é ok, "Save Page Now" torna a cópia pública: evitar em caso sigiloso).
- IP público de acesso a site/loja e ASN: consulta de ASN/whois (RIPE, LACNIC https://www.lacnic.net, registro.br). IP do investigado exige requisição a provedor.

### Redes sociais, marketplaces e mídia
- Perfis públicos (Instagram, Facebook, TikTok, X, LinkedIn, Kwai, YouTube, Telegram público): consulta **sem interação**, sem seguir, sem curtir, sem enviar mensagem, sem pedir amizade. Capturar antes de navegar.
- Marketplaces (OLX, Mercado Livre, Shopee, Facebook Marketplace): data de criação da conta, reputação, anúncios ativos e encerrados, localização declarada, telefone/WhatsApp, fotos reaproveitadas.
- Imagem: Google Lens, Yandex Images https://yandex.com/images, TinEye https://tineye.com, Bing Visual Search. Metadados: ExifTool (arquivo original). Geolocalização: Google Earth/Street View (com data), SunCalc https://www.suncalc.org, Sentinel Hub EO Browser https://apps.sentinel-hub.com/eo-browser, Mapillary. Câmeras públicas de trânsito/municipais quando houver.

### Veículos, imóveis, bens
- FIPE https://veiculos.fipe.org.br (valor); ANAC RAB https://sistemas.anac.gov.br/aeronaves/cons_rab.asp (aeronaves). Titularidade/restrição de veículo: **sistema policial/Detran** (dado faltante).
- Imóvel rural: SICAR/CAR https://www.car.gov.br/publico/imoveis/index. Imóvel urbano: matrícula exige certidão no cartório (dado faltante).
- CEP/logradouro: Correios https://buscacepinter.correios.com.br · mapas.

### Criptoativos e pagamentos
- Exploradores de blockchain: Blockchair https://blockchair.com (multi-cadeia) · Etherscan https://etherscan.io · Tronscan https://tronscan.org · mempool.space (BTC). Olhar entradas/saídas, rótulos de corretoras, valores e datas.
- Denúncias públicas de endereços: Chainabuse https://www.chainabuse.com (pista).
- Corretora identificada → **ofício** por dados de conta (dado faltante).

## Fonte: `plugin/investigacao-cpj/skills/osint-policial/references/tecnicas-e-captura.md`

## Técnicas de busca, verificação e preservação

### 1. Buscadores: como perguntar
- Aspas para frase exata; `OR`, `-` (exclui), `*` (curinga); `site:`, `inurl:`, `intitle:`, `filetype:pdf`, `before:`/`after:` (datas). Repita nos buscadores **Google, Bing, DuckDuckGo, Yandex e Brave**; resultados diferem.
- **Variações do identificador:** nome com e sem acento, abreviado, com sobrenome do meio, invertido, apelido; **telefone** em `(65) 99999-9999`, `65999999999`, `+55 65 99999-9999`, `99999-9999` e sem o 9 inicial (números antigos); **CPF** com e sem pontuação (busque em diários e processos, onde às vezes aparece parcial); **e-mail** completo e só o usuário; **chave Pix** como aparece.
- Combine identificador + contexto: `"nome" + cidade`, `"telefone" + "vendo" OR "aluguel"`, `"razão social" + golpe OR fraude OR reclamação`, `site:t.me "telefone"`, `site:jusbrasil.com.br "nome" + CPF parcial`.
- Registre a **consulta exata** e o **buscador**, inclusive quando nada foi achado.

### 2. Pivô e correlação
Um identificador leva a outro: telefone → anúncio → foto → perfil → empresa → sócio → endereço. Guarde a **cadeia do pivô** (de onde veio cada dado). Cruze **endereço, telefone, e-mail, IP, foto, texto e estilo** entre alvos. Coincidência de um único dado fraco não vincula pessoas.

### 3. Verificação e grau de confiança
- **Fonte:** oficial (RFB, tribunal, junta) · aberta corroborada (2+ independentes) · aberta única · declaratória (perfil/anúncio que diz sobre si) · agregador sem origem.
- **Confiança do achado:** CONFIRMADO (oficial ou 2+ independentes com identificador forte) · PROVÁVEL (1 forte + 1 fraco coerente) · POSSÍVEL (só compatibilidade) · DESCARTADO (incompatível).
- **Homônimos:** nunca junte por nome. Precisa de dois identificadores fortes (CPF/data de nascimento/filiação/endereço documentado/CNPJ como sócio).
- **Golpe de identidade:** foto/nome de terceiro reutilizados em perfil falso são comuns em fraude; perfil ≠ pessoa.
- **Datas:** confirme a data do conteúdo (criação, publicação, edição); conteúdo pode ser posterior ou anterior ao fato.
- **Negativo:** "não localizado em fonte aberta" **não** é "não existe".

### 4. Captura e cadeia de custódia (CPP, arts. 158-A a 158-F, por analogia)
1. **Capture antes de interagir ou reabrir.** Conteúdo volátil primeiro.
2. Registre em cada captura: **URL completa, data e hora (fuso), quem capturou, navegador/ambiente**, e o identificador buscado.
3. **Formatos:** (a) imagem da página inteira com URL e relógio visíveis; (b) PDF ou MHTML da página; (c) quando o conteúdo for importante, **arquivo WARC** ou captura com ferramenta que gere registro (ex.: ferramentas de captura forense/ArchiveBox/Browsertrix; extensões de captura com log).
4. **Hash:** SHA-256 de cada arquivo (`Get-FileHash -Algorithm SHA256 <arquivo>`); anote na ficha.
5. **Armazenamento:** `casos\<ID>\01-extracao\osint\<alvo>\` (nunca em `acervo\` ou `calibracao\`); arquivo original preservado, cópias de trabalho separadas.
6. **Vídeo/story/live:** gravação de tela com relógio visível e URL, mais o arquivo se baixável licitamente; lembre que some rápido.
7. **Prova central:** se o conteúdo for peça-chave, considerar **ata notarial** ou perícia/ferramenta forense institucional e comunicar o delegado. Cópia local com hash é subsídio, não perícia.
8. **Não usar** serviços públicos de arquivamento (Wayback "Save Page Now", archive.today) em caso sigiloso ou de alvo ativo: eles publicam a URL/cópia e podem alertar o alvo. Prefira captura local.
9. **Preservação em provedor:** quando o conteúdo estiver em conta de provedor e puder ser apagado, considerar **requerimento cautelar de guarda de registros** pela autoridade (Marco Civil, arts. 13, § 2º, e 15, § 2º) e depois a ordem judicial — sinalizar como dado faltante.

### 5. Ficha do alvo (`02-analise\osint-<alvo>.md`)
```
## OSINT — <alvo>   (data/hora, pesquisador, ambiente)
Objetivo (pergunta da O.S./do IP):
Identificadores de partida (como constam nos autos, fls.):
| Consulta/fonte (URL, buscador) | Data/hora | Achado (transcrição fiel) | Captura (arquivo, SHA-256) | Confiança | Observação |
Pivôs seguidos (de → para):
Resultado negativo (o que foi buscado e não localizado):
Homônimos afastados/pendentes:
Conclusão prudente (fato × indício):
DADOS FALTANTES (CAIXA ALTA): ...
```

### 6. Aprofundamento (quando vale a pena)
- **Empresa:** histórico de endereço/sócios (várias consultas ao longo do tempo), outras empresas do mesmo endereço, telefone e e-mail no site, domínio (data de criação × abertura do CNPJ), publicidade paga (biblioteca de anúncios das plataformas), clones de loja.
- **Perfil:** primeiras e últimas publicações, marcações, comentários de terceiros, fotos com pontos de referência, seguidores em comum, horários de atividade (pista de fuso/rotina), links na bio (agregadores de link), outros usuários com mesmo avatar.
- **Anúncios/golpes de venda:** o mesmo telefone/foto em várias cidades e datas indica atuação em série; anotar cada anúncio com data e valor.
- **Blockchain:** rastrear entradas e saídas do endereço, ver agrupamentos e corretoras; converter valores na data.
- **Geolocalização:** compare linha do horizonte, fachadas, placas e sombras; usar imagens de satélite com data; registrar a margem de erro.
- **Linha do tempo:** organizar tudo em cronologia com fonte; o padrão de datas frequentemente conecta contas.

### 7. Erros que derrubam a prova
Não registrar URL/hora; captura recortada; edição/anotação sobre a imagem original; uso de fonte ilícita; homônimo tratado como a pessoa; conclusão além do dado; alerta ao alvo; mistura de contas pessoais e de trabalho; ausência de hash.

## Fonte: `plugin/investigacao-cpj/skills/analise-ip-fraude/references/osint-empresas.md`

## OSINT de empresas citadas nos autos (procedimento do investigador sênior)

**Autorização do investigador (28/09/2026):** quando o IP/extrato **cita pessoa jurídica sem dados nos autos** (só razão social, nome ou CNPJ em extrato/comprovante), faça pesquisa em fontes abertas para obter o máximo de dados **verdadeiros e verificáveis** e leve o resultado, com a fonte, ao relatório. Vale só para **pessoa jurídica**. Pessoa física continua exigindo pedido expresso do investigador.

### Regras
1. **Sigilo:** enviar à internet somente CNPJ, razão social, nome de fantasia ou cidade da empresa — nunca nomes de investigados/vítimas, valores, número do IP ou trechos dos autos.
2. **Priorize CNPJ.** Com CNPJ, consulte base espelho da Receita Federal (`https://brasilapi.com.br/api/cnpj/v1/<CNPJ14>`, `https://minhareceita.org/<CNPJ14>`). **Confirme por ao menos duas fontes** (ou marque "fonte única"). Sem CNPJ, busque por razão social + cidade; se houver homônimos, **não afirme vínculo**: registre "homonímia — sem confirmação".
3. **Colher:** razão social, nome fantasia, matriz/filial, situação cadastral e data, início de atividade, CNAE principal, endereço, sócios/administradores, capital, porte. Se útil: filiais, protestos/ações públicas, notícias de fraude/golpe (registrando "não localizado" quando for o caso).
4. **Nunca inferir** o que a fonte não diz. Dado de fonte aberta é **indício a confirmar em sistema oficial** (JUCESP/RFB/sistemas policiais); diga isso na análise.
5. **Registrar** em `02-analise\osint-empresas.md`: alvo, data da consulta, campos obtidos, URL de cada fonte, ressalvas. No relatório, seção Diligências, **parágrafo curto** ("Pesquisa em fontes abertas, em DD/MM/AAAA: …") com a fonte nominal; sem prolixidade.
6. **Relevância:** só leve ao relatório o que ajuda a esclarecer a dinâmica (ex.: identificar o ramo do estabelecimento que recebeu um PIX, cidade, vínculo com outro ponto da cadeia). Cruze com o restante dos autos (mesma cidade, mesma rede, mesmo endereço).
7. Instituições financeiras já qualificadas nos autos e estabelecimentos sem identificador (ex.: "MP *NOME") não precisam de pesquisa.

## Fonte: `plugin/investigacao-cpj/skills/analise-ip-fraude/references/dados-faltantes.md`

## Dados faltantes: como identificar e avisar o operador

**Regra do investigador (28/09/2026), vale para qualquer agente ou LLM** ao analisar, pesquisar ou redigir relatório: se faltar dado **muito importante** para apurar a infração penal, sua **materialidade, autoria e circunstâncias** (CF, art. 144, § 4º; CPP, art. 6º), o agente **não completa, não deduz e não inventa**: **avisa o operador em CAIXA ALTA**, para que ele providencie em sistemas policiais e/ou fora deles (qualificações, objetos, pessoas, empresas, telefones etc.).

### Quando é "muito importante"
Só o que muda a resposta da O.S. ou o rumo da investigação, por exemplo:
- **Autoria:** quem está por trás de conta, telefone, perfil, chave Pix, empresa ou veículo; destinatário final do dinheiro sem qualificação nos autos; nome que aparece em mais de uma cadeia.
- **Materialidade:** comprovante/extrato/imagem/laudo que sustenta o fato e não está nos autos; período do extrato que não cobre o fato; valor divergente sem explicação.
- **Circunstâncias:** local, data/hora, meio (telefone/IP/aparelho), vínculo entre investigados, existência de outros inquéritos ou vítimas.
- **Identificação:** CPF/RG/filiação/endereço/telefone de investigado ou destinatário; homônimo a afastar.
Não avisar por detalhe irrelevante, formalidade sem efeito ou curiosidade.

### Como avisar (formato)
No final da resposta ao operador **e** em `02-analise\dados-faltantes.md`, sob o título exato **DADOS FALTANTES — PROVIDENCIAR (OPERADOR)**, tudo em **CAIXA ALTA**, ordenado por importância, cada item com: **O QUE FALTA — ONDE/COMO OBTER — POR QUE IMPORTA (uma linha)**. Máximo de itens úteis (em regra até 8); sem sugerir medida que é do delegado decidir: indique a **via** (consulta em sistema, ofício, ordem judicial) apenas para orientar o operador.

Exemplo do formato (fictício):
```
DADOS FALTANTES — PROVIDENCIAR (OPERADOR)
1. QUALIFICAÇÃO COMPLETA E ANTECEDENTES DE <NOME/CPF COMO CONSTA> — CONSULTA EM SISTEMAS POLICIAIS — DESTINATÁRIO FINAL DE R$ X SEM QUALIFICAÇÃO NOS AUTOS.
2. EXTRATO DA CONTA <BANCO/AGÊNCIA/CONTA> NO PERÍODO <...> — ORDEM JUDICIAL DE QUEBRA DE SIGILO (NÃO CONSTA DOS AUTOS) — FECHA O CAMINHO DO DINHEIRO.
```

### Onde costuma estar o dado (para orientar o operador)
- **Sistemas policiais/estatais (consulta pelo operador):** antecedentes, mandados, qualificação e endereços de pessoas; titularidade e restrições de veículo; RG/IIRGD; registros de ocorrências/inquéritos; cadastros locais (ex.: Muralha Paulista, INFOSEG/SINESP, Detran/RENAVAM) — **confirmar quais o operador acessa**.
- **Ofício (sem ordem judicial), quando a lei permitir:** dados cadastrais de titular (qualificação, filiação, endereço) a banco, operadora, provedor — Lei 12.850/2013, art. 15 (ver `osint-policial\references\base-legal-e-limites.md`).
- **Ordem judicial (representação):** extratos e movimentação bancária, registros de conexão/acesso e conteúdo, localização/ERB, quebra de sigilo telemático, busca e apreensão.
- **Requerimento cautelar de guarda de registros** ao provedor (Marco Civil, arts. 13, § 2º, e 15, § 2º), com pedido judicial em seguida.
- **Fontes abertas (OSINT):** empresa, sócios, endereço, presença digital, processos públicos, domínio, anúncio (ver skill `osint-policial`).
- **Diligência de campo/oitiva:** local, câmeras, testemunha, comprovantes em posse da vítima, aparelho, prints e conversas originais.
- **Perícia:** exame do aparelho, laudo de imagem/áudio, extração de dados.

### Onde o aviso aparece
1. **Sempre** na resposta final ao operador (em CAIXA ALTA).
2. Em `02-analise\dados-faltantes.md` (mesmo texto).
3. No relatório: **não** vira lista nem sugestão de providência; a lacuna aparece como **ressalva objetiva** na Conclusão ("os autos não trazem…"), em texto corrido. Se o dado faltar no cabeçalho ou em qualificação essencial, use `{...}` e avise em CAIXA ALTA.
