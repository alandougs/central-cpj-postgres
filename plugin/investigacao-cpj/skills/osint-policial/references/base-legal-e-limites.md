# Base legal e limites do OSINT policial

> **Conferir vigência e redação antes de citar em peça oficial** (regra do workspace: não citar dispositivo sem conferir). Esta nota orienta o agente e o investigador; não é parecer jurídico. As fontes consultadas em 28-29/09/2026 foram textos e comentários secundários (o portal do Planalto recusou a conexão na ocasião).

## 1. Fundamento da atividade

- **CF, art. 144, § 4º:** às polícias civis cabem as funções de polícia judiciária e a apuração de infrações penais (exceto as militares). A pesquisa em fontes abertas é **diligência de investigação** ligada a esse mister.
- **CPP, art. 6º:** ao tomar conhecimento da infração, a autoridade deve, entre outras providências, colher provas que sirvam ao esclarecimento do fato e suas circunstâncias, apurar a vida pregressa do indiciado e ordenar a identificação (dados de contexto, vida pregressa e circunstâncias são o campo natural do OSINT).
- **Lei 12.830/2013:** investigação criminal conduzida pelo delegado de polícia; requisições de dados e informações são instrumento dele — o investigador atua por **determinação da autoridade** (Ordem de Serviço).
- Fonte aberta **não depende de ordem judicial**, desde que o acesso seja lícito e sem burla a barreira de privacidade.

## 2. Limites constitucionais e de prova

- **CF, art. 5º, X e XII:** intimidade, vida privada e sigilo de comunicações e de dados. Conteúdo de comunicação, extrato, localização, registros de conexão e base restrita: **reserva de jurisdição ou requisição legal**, não OSINT.
- **CF, art. 5º, LVI:** inadmissíveis provas obtidas por meios ilícitos. Dado ilícito **contamina** o que dele decorre. Se houver dúvida sobre a licitude da origem, **não usar** e sinalizar.
- **CP, art. 154-A:** invadir dispositivo informático alheio, mediante violação indevida de mecanismo de segurança, para obter dados. Nunca invadir contas, burlar autenticação, usar credenciais alheias ou explorar falhas.
- **Perfil falso / agente encoberto na internet:** a infiltração virtual de agentes de polícia exige **prévia autorização judicial** e existe em hipóteses legais específicas (Lei 12.850/2013, art. 10-A, para os crimes daquela lei; ECA, arts. 190-A a 190-E, para crimes sexuais contra criança e adolescente). Fora delas, não criar identidade falsa para se aproximar do alvo nem induzi-lo a fornecer dados.
- **LGPD (Lei 13.709/2018), art. 4º, III:** a lei não se aplica ao tratamento de dados feito para fins exclusivos de segurança pública e atividades de investigação e repressão de infrações penais, que devem ser regidos por legislação específica com proporcionalidade e interesse público; mesmo assim, **aplique minimização, finalidade e segurança** como boa prática institucional.
- **Marco Civil (Lei 12.965/2014):** registros de conexão (art. 13, um ano) e de acesso a aplicações (art. 15, seis meses) são guardados pelos provedores; o **acesso ao conteúdo** e aos **registros** exige ordem judicial (art. 22). A autoridade policial pode **requerer cautelarmente a guarda** por prazo maior (arts. 13, § 2º, e 15, § 2º), devendo obter a ordem judicial em 60 dias. Dados cadastrais (qualificação pessoal, filiação e endereço) podem ser requisitados por autoridades com competência legal (art. 10, § 3º).

## 3. O que pode ser requisitado sem ordem judicial (via ofício, não OSINT)

- **Dados cadastrais** (qualificação, filiação, endereço) mantidos por Justiça Eleitoral, empresas telefônicas, instituições financeiras, provedores e administradoras de cartão: Lei 12.850/2013, art. 15 (delegado e MP, "independentemente de autorização judicial", limitado a esses dados); e, para lavagem, Lei 9.613/1998, art. 17-B. Não alcança extrato, movimentação, conteúdo, localização.
- **CPP, arts. 13-A e 13-B:** requisição de dados cadastrais e de sinais de localização em rol específico de crimes (sequestro, cárcere privado, redução a condição análoga à de escravo, tráfico de pessoas, extorsão mediante sequestro, envio ilegal de criança ao exterior), com regras próprias e, para sinais de localização em tempo real, ordem judicial após prazo. O STF já reconheceu a constitucionalidade do art. 13-A (ADI 5642).
- **RIF/COAF:** compartilhamento de relatórios de inteligência financeira com órgãos de persecução sem prévia autorização judicial foi admitido pelo STF (Tema 990); é pedido pela autoridade, não pelo OSINT.
- Estelionato comum **não** consta do rol dos arts. 13-A/13-B; extratos e movimentação dependem de **ordem judicial** (LC 105/2001, art. 1º, § 4º) — como já ocorre nos autos.

## 4. Regras práticas

1. Se qualquer pessoa, sem cadastro especial, consegue ver o dado sem transpor barreira, é fonte aberta. Se exigir contornar, enganar ou usar credencial que não é sua, **não é**.
2. Cadastro gratuito com identidade própria em plataforma pública é aceitável quando exigido pela plataforma e permitido por seus termos; **não** crie múltiplas contas para burlar bloqueio.
3. Não use bases vazadas, "painéis de consulta" de CPF/placa/telefone de origem duvidosa nem serviços que vendam dado sem base legal.
4. Serviços comerciais de pesquisa (ex.: agregadores de processos, ferramentas de reconhecimento facial) só com **autorização do órgão** e ciência do delegado; o resultado é pista até corroboração por fonte oficial.
5. Registrar tudo: quem pesquisou, quando, onde, com qual identificador. Registro protege a licitude e permite reproduzir.
6. Onde a via aberta acaba, **indicar a via legal** como dado faltante (ofício com dados cadastrais; representação por quebra de sigilo; requisição de guarda cautelar de registros; consulta a sistema policial).
