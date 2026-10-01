# Dados faltantes: como identificar e avisar o operador

**Regra do investigador (28/09/2026), vale para qualquer agente ou LLM** ao analisar, pesquisar ou redigir relatório: se faltar dado **muito importante** para apurar a infração penal, sua **materialidade, autoria e circunstâncias** (CF, art. 144, § 4º; CPP, art. 6º), o agente **não completa, não deduz e não inventa**: **avisa o operador em CAIXA ALTA**, para que ele providencie em sistemas policiais e/ou fora deles (qualificações, objetos, pessoas, empresas, telefones etc.).

## Quando é "muito importante"
Só o que muda a resposta da O.S. ou o rumo da investigação, por exemplo:
- **Autoria:** quem está por trás de conta, telefone, perfil, chave Pix, empresa ou veículo; destinatário final do dinheiro sem qualificação nos autos; nome que aparece em mais de uma cadeia.
- **Materialidade:** comprovante/extrato/imagem/laudo que sustenta o fato e não está nos autos; período do extrato que não cobre o fato; valor divergente sem explicação.
- **Circunstâncias:** local, data/hora, meio (telefone/IP/aparelho), vínculo entre investigados, existência de outros inquéritos ou vítimas.
- **Identificação:** CPF/RG/filiação/endereço/telefone de investigado ou destinatário; homônimo a afastar.
Não avisar por detalhe irrelevante, formalidade sem efeito ou curiosidade.

## Como avisar (formato)
No final da resposta ao operador **e** em `02-analise\dados-faltantes.md`, sob o título exato **DADOS FALTANTES — PROVIDENCIAR (OPERADOR)**, tudo em **CAIXA ALTA**, ordenado por importância, cada item com: **O QUE FALTA — ONDE/COMO OBTER — POR QUE IMPORTA (uma linha)**. Máximo de itens úteis (em regra até 8); sem sugerir medida que é do delegado decidir: indique a **via** (consulta em sistema, ofício, ordem judicial) apenas para orientar o operador.

Exemplo do formato (fictício):
```
DADOS FALTANTES — PROVIDENCIAR (OPERADOR)
1. QUALIFICAÇÃO COMPLETA E ANTECEDENTES DE <NOME/CPF COMO CONSTA> — CONSULTA EM SISTEMAS POLICIAIS — DESTINATÁRIO FINAL DE R$ X SEM QUALIFICAÇÃO NOS AUTOS.
2. EXTRATO DA CONTA <BANCO/AGÊNCIA/CONTA> NO PERÍODO <...> — ORDEM JUDICIAL DE QUEBRA DE SIGILO (NÃO CONSTA DOS AUTOS) — FECHA O CAMINHO DO DINHEIRO.
```

## Onde costuma estar o dado (para orientar o operador)
- **Sistemas policiais/estatais (consulta pelo operador):** antecedentes, mandados, qualificação e endereços de pessoas; titularidade e restrições de veículo; RG/IIRGD; registros de ocorrências/inquéritos; cadastros locais (ex.: Muralha Paulista, INFOSEG/SINESP, Detran/RENAVAM) — **confirmar quais o operador acessa**.
- **Ofício (sem ordem judicial), quando a lei permitir:** dados cadastrais de titular (qualificação, filiação, endereço) a banco, operadora, provedor — Lei 12.850/2013, art. 15 (ver `osint-policial\references\base-legal-e-limites.md`).
- **Ordem judicial (representação):** extratos e movimentação bancária, registros de conexão/acesso e conteúdo, localização/ERB, quebra de sigilo telemático, busca e apreensão.
- **Requerimento cautelar de guarda de registros** ao provedor (Marco Civil, arts. 13, § 2º, e 15, § 2º), com pedido judicial em seguida.
- **Fontes abertas (OSINT):** empresa, sócios, endereço, presença digital, processos públicos, domínio, anúncio (ver skill `osint-policial`).
- **Diligência de campo/oitiva:** local, câmeras, testemunha, comprovantes em posse da vítima, aparelho, prints e conversas originais.
- **Perícia:** exame do aparelho, laudo de imagem/áudio, extração de dados.

## Onde o aviso aparece
1. **Sempre** na resposta final ao operador (em CAIXA ALTA).
2. Em `02-analise\dados-faltantes.md` (mesmo texto).
3. No relatório: **não** vira lista nem sugestão de providência; a lacuna aparece como **ressalva objetiva** na Conclusão ("os autos não trazem…"), em texto corrido. Se o dado faltar no cabeçalho ou em qualificação essencial, use `{...}` e avise em CAIXA ALTA.
