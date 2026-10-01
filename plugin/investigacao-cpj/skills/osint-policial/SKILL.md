---
name: osint-policial
description: Investigador de polícia sênior em OSINT (fontes abertas) - planeja e executa pesquisa lícita e aprofundada sobre pessoas, empresas, telefones, e-mails, perfis, domínios, veículos, imagens e criptoativos ligados a um IP; define quando pesquisar, onde, como preservar a prova e como registrar. Use quando o investigador pedir "pesquisa OSINT", "fontes abertas", "levanta dados dessa empresa/pessoa/telefone/perfil", "quem é esse titular", "pesquisa na internet", "redes sociais", ou quando o IP citar pessoa jurídica, telefone, perfil, domínio, placa ou chave sem qualificação nos autos e a lacuna for relevante para autoria, materialidade ou circunstâncias.
---

# OSINT policial sênior

Método para levantar, em fontes **abertas e lícitas**, o máximo de informação verdadeira e verificável que ajude a apurar infração penal, materialidade, circunstâncias e autoria (CF, art. 144, § 4º; CPP, art. 6º). O produto é **subsídio ao delegado**: fatos com fonte, indícios com grau de confiança e lacunas, nunca conclusão de culpa.

Leia antes: `references\base-legal-e-limites.md` (o que pode e o que exige ordem judicial), `references\fontes-brasil.md` (onde buscar) e `references\tecnicas-e-captura.md` (como pesquisar, preservar e registrar). Regras do workspace (`AGENTS.md` §1) valem integralmente: sigilo do IP, sem inventar dado, fato × indício × inferência × lacuna.

## 1. Quando fazer OSINT

- **Pessoa jurídica** citada sem dados nos autos: autorizado de ofício (procedimento curto em `analise-ip-fraude\references\osint-empresas.md`, aprofundável por esta skill).
- **Pessoa física, telefone, e-mail, perfil, domínio, placa, chave Pix, criptoendereço:** quando o investigador pedir **ou** quando a lacuna for relevante; nesse caso, **avisar em CAIXA ALTA** que a pesquisa é necessária (ver `analise-ip-fraude\references\dados-faltantes.md`) e só executar com pedido expresso.
- **Momentos úteis na investigação:** (a) triagem inicial, para identificar quem é quem e afastar homônimos; (b) antes de representar por quebra de sigilo ou busca, para dar lastro ("fundadas razões") e confirmar endereços; (c) ao receber dados bancários/telefônicos, para qualificar nomes novos da cadeia; (d) antes das oitivas, para preparar perguntas; (e) antes de campana/mandado, para confirmar endereço, rotina e vínculos; (f) recorrentemente, porque conteúdo aberto some (anúncios, stories, perfis, domínios).
- **Conteúdo volátil (anúncio, perfil, story, site, grupo):** capturar **na primeira visita**, antes de qualquer outra coisa.
- **Não fazer OSINT** para o que só se obtém com ordem judicial ou requisição legal (conteúdo de comunicações, extratos, registros de conexão, localização, base restrita) — apontar como dado faltante.

## 2. Ciclo de trabalho

1. **Planejar.** Pergunta de investigação (o que a O.S./o IP precisa saber), alvo, identificadores disponíveis (nome, CPF, CNPJ, telefone, e-mail, apelido, chave Pix, placa, domínio, URL, foto), hipóteses a testar e o que **não** será pesquisado. Escolha o ambiente (ver §5).
2. **Coletar** por camadas, do mais objetivo ao mais especulativo: registros oficiais (Receita, juntas comerciais, diários oficiais, tribunais, transparência) → cadastros e bases públicas → web aberta e buscadores → redes sociais e marketplaces → dados técnicos (domínio, IP público, blockchain) → imagens/mídia.
3. **Pivotar.** Cada dado novo vira nova chave (telefone → perfil → foto → outra rede → empresa → sócio → endereço → veículo). Registre o pivô e pare quando o ganho probatório cair.
4. **Verificar e resolver identidade.** Um dado só é "confirmado" com **duas fontes independentes** ou uma fonte oficial. Homônimo exige **dois identificadores fortes** coincidentes (CPF parcial + data de nascimento; filiação; endereço documentado). Sem isso: "possível homonímia". Classifique a **confiança**: CONFIRMADO / PROVÁVEL / POSSÍVEL / DESCARTADO, e a **fonte** (oficial / aberta corroborada / aberta única / declaratória).
5. **Preservar.** Captura íntegra, com URL, data/hora, hash e responsável (ver `tecnicas-e-captura.md`). Sem preservação, o achado é só pista.
6. **Analisar e registrar.** Ficha por alvo em `02-analise\osint-<alvo>.md` (ou `osint-empresas.md`): o que foi buscado, onde, quando, o que se achou, o que **não** se achou (resultado negativo também é dado), confiança, pendências. Conclusões só com base documental.
7. **Disseminar.** No relatório, **um parágrafo curto** por alvo relevante, em texto corrido, com fonte e data ("pesquisa em fontes abertas, em DD/MM/AAAA, indicou…"). O detalhe fica na ficha. Dado sem confirmação entra como indício, com a ressalva. Lacunas relevantes vão em CAIXA ALTA ao operador.

## 3. O que pesquisar, por alvo (roteiro mínimo)

- **Pessoa jurídica (CNPJ):** situação e data, matriz/filial, CNAE, endereço, capital, sócios/administradores, histórico de alterações e outras empresas dos sócios, sanções (CEIS/CNEP), processos públicos, marca (INPI), domínio/site/redes, telefones e e-mails divulgados, anúncios, reclamações (Reclame Aqui, Procon), notícias, diários oficiais e contratos públicos. Cruze **endereço × outras empresas**, **sócio × outros CNPJs**, **telefone/e-mail × anúncios**.
- **Pessoa física:** com CPF/data de nascimento/filiação (dos autos): vínculo societário (Receita/juntas), processos e mandados públicos (tribunais, BNMP), cargos e candidaturas (TSE), diários oficiais, cadastros profissionais/currículo, presença digital (nome, apelidos, fotos, e-mail, telefone, usuário), veículos por fontes abertas, endereços citados em anúncios ou cadastros públicos. **Sem pedido expresso do investigador, não pesquisar pessoa física** — só alertar em CAIXA ALTA.
- **Telefone/WhatsApp:** operadora e portabilidade (consulta pública ABR), aparição em anúncios, sites, redes, grupos abertos, foto/recado **apenas se públicos** pelas configurações do titular; não simular identidade nem induzir o titular.
- **E-mail e usuário:** buscas por correspondência exata em buscadores e redes, padrões de usuário reutilizado entre plataformas, gravatar/foto pública, domínio do e-mail (corporativo × gratuito).
- **Domínio/site/loja:** RDAP/WHOIS (registro.br para .br), datas de criação, DNS, certificados (transparência), histórico (arquivos da web), tecnologias, e-mails e CNPJ no rodapé, redes citadas; compare texto/imagens (loja clone).
- **Anúncios/marketplaces:** perfil do vendedor, data de criação, histórico, avaliações, telefone/localização declarados, fotos reaproveitadas (busca reversa).
- **Imagem:** busca reversa (vários motores), metadados quando o arquivo original está nos autos, geolocalização por pontos de referência (sol/sombra, placas, relevo, imagens de satélite e de rua com data). Reconhecimento facial por serviço comercial: **não usar** sem regra do órgão.
- **Veículo:** fontes abertas mostram pouco (tabela FIPE, anúncios, notícias, registros de leilão); titularidade e restrições são de **sistema policial/Detran** → dado faltante.
- **Criptoativos:** explorador público de blockchain do endereço (saldo, entradas/saídas, agrupamentos, corretoras que aparecem), fonte da pista (mensagem, comprovante) e data.

## 4. Regras de conduta (síntese; detalhe em `base-legal-e-limites.md`)

- Só **fontes abertas**: o que qualquer pessoa vê sem burlar acesso. **Nada** de invadir conta/dispositivo, adivinhar senha, usar base vazada/comprada de origem duvidosa, "consultas de CPF" clandestinas, engenharia social, criar perfil falso para se aproximar do alvo, nem interagir com o alvo. Infiltração virtual exige autorização judicial nos casos legais.
- Perfil privado ou grupo fechado **não** se acessa por artifício. Anote "perfil privado" e indique a via legal (representação, requisição a provedor).
- **Minimização:** colher o necessário à apuração; não expor terceiros; não publicar; não enviar conteúdo dos autos a serviços externos (só o identificador mínimo da busca — CNPJ, telefone, usuário — quando indispensável).
- **Fato ≠ pista.** Boato, fórum e "bases de consulta" comerciais sem origem clara são **pista**, nunca fato do relatório.
- **Cautela sobre quem é o alvo:** pessoa homônima ou conta-espelho pode ser vítima de golpe de identidade; titular de conta ou perfil não é automaticamente autor.

## 5. Ambiente e segurança operacional

Use navegador/perfil **dedicado** à investigação, sem contas pessoais, com histórico separado; VPN/rede conforme norma do órgão; sem baixar arquivos executáveis de origem desconhecida; não abrir links de alvos em máquina com dados sensíveis; anotar hora (fuso), IP de saída e navegador. Prefira **captura por ferramenta** que gere registro e hash (ver `tecnicas-e-captura.md`). Dois olhos quando possível (quem coleta e quem confere).

## 6. Saídas

- `02-analise\osint-<alvo>.md`: ficha (modelo em `tecnicas-e-captura.md`, seção "Ficha do alvo").
- `02-analise\dados-faltantes.md`: o que OSINT **não** resolve e depende de sistema policial, ordem judicial ou requisição (em CAIXA ALTA).
- No relatório: parágrafo curto, sem tópicos, com fonte e data; nenhuma URL solta sem contexto.

## 7. Nunca

Inventar dado, "completar" CPF/telefone/placa por dedução, tratar homônimo como a mesma pessoa, atribuir autoria por perfil ou por nome, expor resultado a terceiros, usar fonte ilícita, afirmar que "não existe" quando apenas "não se localizou em fonte aberta".
