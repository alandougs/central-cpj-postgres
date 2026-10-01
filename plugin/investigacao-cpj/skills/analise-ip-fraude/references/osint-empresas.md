# OSINT de empresas citadas nos autos (procedimento do investigador sênior)

**Autorização do investigador (28/09/2026):** quando o IP/extrato **cita pessoa jurídica sem dados nos autos** (só razão social, nome ou CNPJ em extrato/comprovante), faça pesquisa em fontes abertas para obter o máximo de dados **verdadeiros e verificáveis** e leve o resultado, com a fonte, ao relatório. Vale só para **pessoa jurídica**. Pessoa física continua exigindo pedido expresso do investigador.

## Regras
1. **Sigilo:** enviar à internet somente CNPJ, razão social, nome de fantasia ou cidade da empresa — nunca nomes de investigados/vítimas, valores, número do IP ou trechos dos autos.
2. **Priorize CNPJ.** Com CNPJ, consulte base espelho da Receita Federal (`https://brasilapi.com.br/api/cnpj/v1/<CNPJ14>`, `https://minhareceita.org/<CNPJ14>`). **Confirme por ao menos duas fontes** (ou marque "fonte única"). Sem CNPJ, busque por razão social + cidade; se houver homônimos, **não afirme vínculo**: registre "homonímia — sem confirmação".
3. **Colher:** razão social, nome fantasia, matriz/filial, situação cadastral e data, início de atividade, CNAE principal, endereço, sócios/administradores, capital, porte. Se útil: filiais, protestos/ações públicas, notícias de fraude/golpe (registrando "não localizado" quando for o caso).
4. **Nunca inferir** o que a fonte não diz. Dado de fonte aberta é **indício a confirmar em sistema oficial** (JUCESP/RFB/sistemas policiais); diga isso na análise.
5. **Registrar** em `02-analise\osint-empresas.md`: alvo, data da consulta, campos obtidos, URL de cada fonte, ressalvas. No relatório, seção Diligências, **parágrafo curto** ("Pesquisa em fontes abertas, em DD/MM/AAAA: …") com a fonte nominal; sem prolixidade.
6. **Relevância:** só leve ao relatório o que ajuda a esclarecer a dinâmica (ex.: identificar o ramo do estabelecimento que recebeu um PIX, cidade, vínculo com outro ponto da cadeia). Cruze com o restante dos autos (mesma cidade, mesma rede, mesmo endereço).
7. Instituições financeiras já qualificadas nos autos e estabelecimentos sem identificador (ex.: "MP *NOME") não precisam de pesquisa.
