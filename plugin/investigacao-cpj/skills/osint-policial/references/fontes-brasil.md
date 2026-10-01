# Fontes abertas úteis (Brasil) — catálogo por finalidade

Endereços podem mudar ou exigir captcha/login gratuito; se não abrir, procure pelo nome oficial. **Fonte oficial > agregador.** Agregadores comerciais (marcados *agreg.*) servem de **pista** e devem ser confirmados na fonte oficial. Enviar às fontes apenas o identificador mínimo (CNPJ, telefone, usuário). Só use serviço pago com autorização do órgão.

## Empresas e sociedades
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

## Pessoas, processos e mandados
- Tribunais (consulta pública): TJSP e-SAJ https://esaj.tjsp.jus.br/cpopg/open.do (por nome/CPF/OAB, processos públicos; segredo de justiça não aparece) · demais TJs/TRFs/PJe nos portais próprios.
- CNJ: BNMP (mandados de prisão) https://portalbnmp.cnj.jus.br · DataJud (API pública de metadados processuais) https://datajud-wiki.cnj.jus.br.
- Eleitoral: DivulgaCandContas (candidaturas, patrimônio declarado, doadores) https://divulgacandcontas.tse.jus.br · dados abertos TSE https://dadosabertos.tse.jus.br.
- Diários oficiais: DOU https://www.in.gov.br/servicos/diario-oficial-da-uniao · DOE-SP https://www.doe.sp.gov.br · municipais via Querido Diário https://queridodiario.ok.org.br (nomeações, licitações, contratos, sócios).
- Transparência: Portal da Transparência (servidores, benefícios, convênios) https://portaldatransparencia.gov.br · dados.gov.br · Brasil.io.
- Currículo/atuação: Lattes https://buscatextual.cnpq.br/buscatextual/busca.do · LinkedIn (perfil público).
- *agreg.* Jusbrasil, Escavador: úteis para achar processos e diários por nome; **confirmar no tribunal**; cuidado com homônimos.
- Procurados: Interpol (Red Notices, público) https://www.interpol.int/How-we-work/Notices/Red-Notices/View-Red-Notices.

## Telefone, e-mail e identidade digital
- Operadora e portabilidade (consulta pública): https://consultanumero.abrtelecom.com.br/consultanumero/consulta/consultaSituacaoAtualCtg (informa operadora atual; **não** informa titular). A operadora é quem recebe o ofício.
- Aparelho impedido/IMEI (Anatel): https://www.consultaaparelhoimpedido.com.br.
- Nome de usuário em múltiplas plataformas: WhatsMyName https://whatsmyname.app · Sherlock/Maigret (ferramentas locais). Resultado é pista; confirmar por foto, texto, vínculo.
- Busca por número/e-mail entre aspas em buscadores (formatos variados), anúncios (OLX, Mercado Livre, Facebook Marketplace), grupos públicos (Telegram, links de convite abertos), sites institucionais.

## Domínios, sites e infraestrutura
- .br: Registro.br WHOIS https://registro.br/tecnologia/ferramentas/whois/ · RDAP https://rdap.registro.br/domain/<dominio>.
- Global: ICANN Lookup https://lookup.icann.org · crt.sh https://crt.sh (certificados, subdomínios) · urlscan.io https://urlscan.io (estrutura e recursos de página — **não** submeter URL de investigação ativa a serviço público se houver risco de expor) · Wayback https://web.archive.org (histórico; **consultar** é ok, "Save Page Now" torna a cópia pública: evitar em caso sigiloso).
- IP público de acesso a site/loja e ASN: consulta de ASN/whois (RIPE, LACNIC https://www.lacnic.net, registro.br). IP do investigado exige requisição a provedor.

## Redes sociais, marketplaces e mídia
- Perfis públicos (Instagram, Facebook, TikTok, X, LinkedIn, Kwai, YouTube, Telegram público): consulta **sem interação**, sem seguir, sem curtir, sem enviar mensagem, sem pedir amizade. Capturar antes de navegar.
- Marketplaces (OLX, Mercado Livre, Shopee, Facebook Marketplace): data de criação da conta, reputação, anúncios ativos e encerrados, localização declarada, telefone/WhatsApp, fotos reaproveitadas.
- Imagem: Google Lens, Yandex Images https://yandex.com/images, TinEye https://tineye.com, Bing Visual Search. Metadados: ExifTool (arquivo original). Geolocalização: Google Earth/Street View (com data), SunCalc https://www.suncalc.org, Sentinel Hub EO Browser https://apps.sentinel-hub.com/eo-browser, Mapillary. Câmeras públicas de trânsito/municipais quando houver.

## Veículos, imóveis, bens
- FIPE https://veiculos.fipe.org.br (valor); ANAC RAB https://sistemas.anac.gov.br/aeronaves/cons_rab.asp (aeronaves). Titularidade/restrição de veículo: **sistema policial/Detran** (dado faltante).
- Imóvel rural: SICAR/CAR https://www.car.gov.br/publico/imoveis/index. Imóvel urbano: matrícula exige certidão no cartório (dado faltante).
- CEP/logradouro: Correios https://buscacepinter.correios.com.br · mapas.

## Criptoativos e pagamentos
- Exploradores de blockchain: Blockchair https://blockchair.com (multi-cadeia) · Etherscan https://etherscan.io · Tronscan https://tronscan.org · mempool.space (BTC). Olhar entradas/saídas, rótulos de corretoras, valores e datas.
- Denúncias públicas de endereços: Chainabuse https://www.chainabuse.com (pista).
- Corretora identificada → **ofício** por dados de conta (dado faltante).
