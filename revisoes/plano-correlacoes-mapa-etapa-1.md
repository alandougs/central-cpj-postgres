# Plano de implementação — Correlações documentadas e mapa de referência

> **Projeto:** Central CPJ / ASTRA  
> **Objetivo:** facilitar a identificação e a conferência de registros coincidentes entre procedimentos, com fontes rastreáveis e localização aproximada claramente indicada.  
> **Instrução ao agente implementador: implementar somente a Etapa 1.** A Etapa 2 permanece como proposta futura, fora do escopo e dependente de autorização específica.  
> Este arquivo é a especificação para repasse. Seu salvamento não significa que a funcionalidade foi implementada, testada ou homologada.

## 1. Diretrizes de implementação

- Ler os trechos pertinentes de `PRD.md`, `AGENTS.md` e `TAREFAS-COMPARTILHADAS.md`; reservar a tarefa de implementação antes de editar. A tarefa PLG01 cobre somente o salvamento deste documento.
- Identificar a branch e a versão que receberão a implementação. Não presumir que a Central em produção e a branch ASTRA possuem os mesmos contratos.
- Reutilizar pesquisa relacional, grafo, navegação e mecanismos de persistência existentes.
- Manter Python, Flask, SQLite e JavaScript local, sem banco servidor, Docker, framework adicional ou CDN.
- Usar exclusivamente dados fictícios nos testes.
- Não alterar originais nem inserir correlações automaticamente nos relatórios.
- Não incluir merge, publicação, instalação ou mudança de produção nesta entrega.

## 2. Etapa 1 — Escopo fechado

### 2.1. Radar de coincidências documentadas

Identificar ocorrências do mesmo identificador completo em **dois ou mais procedimentos distintos**:

- CPF;
- CNPJ;
- chave Pix;
- conta bancária;
- telefone;
- e-mail;
- placa.

**Endereço, nome, município, DDD e banco isolado não geram alertas nesta etapa.**

Cada resultado deve mostrar:

- identificador coincidente;
- procedimentos e O.S. relacionados;
- pessoas ou empresas associadas, sem fusão automática;
- papel documentado em cada caso;
- fonte e localizador de cada ocorrência;
- datas disponíveis e eventuais limitações;
- explicação objetiva da regra que produziu o resultado.

Exemplo de título: **“CNPJ registrado em dois procedimentos”**.

Não usar classificações automáticas como “ORCRIM”, “laranja”, “empresa de fachada”, “beneficiário final” ou “alto risco”.

### 2.2. Critérios para evitar falsos positivos

**Identidade do procedimento**

- O.S. distintas do mesmo IP não contam como procedimentos diferentes.
- Usar IPe e processo judicial, quando disponíveis, para reconhecer essa relação.
- Não unir procedimentos por nome, BO ou semelhança textual.
- Quando a identidade do procedimento for insuficiente ou contraditória, apresentar a limitação e não afirmar recorrência entre IPs confirmadamente distintos.

**Qualidade dos identificadores**

- Preservar valor original e valor normalizado.
- Não completar dígitos, remover marcadores de incerteza ou transformar identificadores parciais em coincidências exatas.
- Aplicar normalização específica por tipo.
- Contas precisam de instituição e identificação suficiente de agência/conta, conforme o contrato existente. Conta ambígua não gera coincidência confirmada.
- Nome semelhante não comprova identidade.
- Mesmo telefone, e-mail ou Pix não comprova titularidade comum nem participação criminosa.

**Contexto**

- Preservar papéis por caso: uma pessoa pode aparecer como vítima em um procedimento e em outra condição em outro.
- Não elevar automaticamente a prioridade por quantidade de ocorrências.
- Não excluir indiscriminadamente bancos ou marketplaces. Identificar se aparecem como instituição financeira, parte ou titular documentado.
- Não calcular score de 1–100 nem emitir níveis “crítico/alto” nesta etapa.

**Deduplicação**

- Repetições da mesma ocorrência em extração, análise e relatório não contam como evidências independentes.
- Contar procedimentos distintos e preservar as referências disponíveis.
- Registro extraído ainda não conferido deve continuar identificado como candidato.

### 2.3. Mapa de referência offline

Exibir PF e PJ dos casos com:

- município/UF resolvidos por base geográfica local;
- coordenadas já documentadas, quando houver fonte e significado identificáveis;
- indicação permanente do nível de precisão;
- lista de registros sem localização resolvida.

**Limites obrigatórios**

- Município representa localização aproximada, nunca endereço residencial exato.
- Coordenada existente não deve ser atribuída à pessoa automaticamente: pode representar local do fato, estabelecimento ou outro objeto.
- Base municipal não deve ser apresentada como base de CEPs ou logradouros.
- Município ambíguo, endereço incompleto ou conflito de localização permanece sem resolução automática.
- Não aplicar deslocamento artificial às coordenadas. Usar agrupamento visual; eventual abertura em leque não altera os dados.
- Não produzir trajetórias, rotas operacionais, concentração criminal ou arcos financeiros nesta etapa.

Usar biblioteca e cartografia distribuídas localmente, com origem, versão e licença registradas. **Nenhuma requisição externa de mapas, fontes, tiles ou geocodificação.**

### 2.4. Modelagem PF/PJ

- Diferenciar pessoa física, pessoa jurídica e vínculo entre ambas.
- A presença de CNPJ ou empresa na qualificação de uma PF não transforma essa pessoa em PJ.
- Preservar registros distintos quando não houver identificação suficiente.
- Não usar o identificador de uma ocorrência como prova de identidade global da pessoa.
- Permitir múltiplos endereços, com fonte, contexto e data quando disponíveis.

## 3. Interface e fluxo de uso

Integrar **Correlações** e **Mapa** à Pesquisa/Grafo existente, evitando duplicar fichas ou mecanismos de navegação.

### Radar

Lista utilizável independentemente do mapa, contendo:

- filtros por procedimento/O.S., tipo de identificador e estado de revisão;
- ordenação por quantidade de procedimentos e atualização;
- explicação da coincidência;
- acesso às ocorrências e respectivas fontes;
- ações: marcar como lido, fixar para acompanhamento e descartar com motivo.

“Lido” deve ser independente de “fixado” e “descartado”.

### Mapa e inspetor

- Filtros por caso, PF/PJ, papel documentado e município/UF.
- Agrupamento de pontos sobrepostos.
- Distinção visual entre localização municipal e coordenada documentada.
- Painel com dados essenciais, papel por caso, fontes e precisão.
- Atalhos para qualificação, caso, grafo e documento de origem.

Não mostrar automaticamente filiação, RG e demais dados completos no pino; disponibilizá-los na qualificação.

Selecionar uma correlação destaca os registros localizáveis e informa quantos permanecem sem coordenadas. **Ausência de coordenadas não oculta evidências.**

A abertura da fonte deve respeitar a relação real entre página do arquivo e folhas dos autos, sem presumir equivalência.

## 4. Arquitetura e persistência

### 4.1. Componentes

Criar componentes separados para:

1. resolução geográfica local;
2. cálculo de coincidências;
3. consulta pela API;
4. interface.

O indexador pode acionar a atualização dos derivados, mas não deve concentrar toda a lógica nova.

Falha no módulo não deve impedir extração, análise ou geração de relatório. A interface deve informar quando os resultados estiverem desatualizados.

### 4.2. Dados derivados

Reutilizar `rag\cpj.sqlite` ou o armazenamento derivado equivalente da branch escolhida.

Cada correlação deve conter, no mínimo:

- ID determinístico;
- tipo e valor normalizado do identificador;
- versão da regra;
- procedimentos relacionados;
- referências às ocorrências;
- limitações de qualidade;
- primeira identificação, última atualização e revisão dos dados de origem.

Preservar as evidências de modo estruturado; título e resumo não substituem as referências.

### 4.3. Estado humano

Guardar leitura, acompanhamento, descarte e justificativas em armazenamento persistente separado dos dados regeneráveis.

- Reutilizar o mecanismo existente, se adequado.
- Garantir gravação atômica, controle de concorrência e backup.
- Reindexação não pode apagar decisões humanas.
- Mudança relevante de evidência deve sinalizar necessidade de nova revisão, preservando o histórico.
- Correlação que perdeu suporte deve sair dos resultados ativos sem apagar o registro da revisão.

### 4.4. API

Rotas sugeridas, adaptáveis aos contratos existentes:

- `GET /api/inteligencia/correlacoes`
- `GET /api/inteligencia/mapa`
- `POST /api/inteligencia/correlacoes/estado`

Requisitos:

- permissões e auditoria existentes;
- proteção de escrita adotada pelo projeto, incluindo `X-CPJ`;
- validação dos filtros;
- paginação das correlações e limites explícitos no mapa;
- indicação de resultados parciais, sem truncamento silencioso;
- consultas GET sem reindexação nem mutação.

## 5. Sigilo e separação das fontes

- Etapa 1 usa exclusivamente registros dos casos; integração com `consulta\` fica para etapa posterior.
- Não fazer chamadas externas nem enviar endereços “higienizados”.
- Ativação de provedor de IA não autoriza geocodificação ou cartografia externa.
- Coincidência entre procedimentos é informação para conferência humana; não constitui conclusão automática de autoria.
- Exportação para relatórios ou inclusão de fatos de outros procedimentos não integra esta entrega.

## 6. Testes e critérios de aceite

Usar workspace temporário e dados fictícios para verificar:

1. Identificadores completos coincidentes em procedimentos distintos.
2. Duas O.S. do mesmo IP sem contagem duplicada.
3. Procedimentos sem identificação suficiente corretamente sinalizados.
4. Homônimos, identificadores parciais e dígitos incertos sem fusão indevida.
5. Contas com números iguais em instituições diferentes sem coincidência falsa.
6. PF vinculada a empresa preservada como PF.
7. Papéis diferentes por caso e fontes preservados.
8. Repetição em extração/análise/relatório sem multiplicação artificial.
9. Município ambíguo e coordenada com contexto incompatível sem localização inventada.
10. Estado humano preservado após reindexação e reinício.
11. Alteração ou remoção de evidência refletida nos resultados.
12. Navegação funcional entre correlação, qualificação, caso, grafo e fonte.
13. Ausência de requisições externas no navegador e no backend.
14. Falha do módulo sem bloqueio do fluxo principal.

Medir tempo de atualização, resposta e renderização em volume fictício representativo. Registrar tamanho da massa, ambiente, resultados e limitações.

**Entrega técnica:** código, testes pertinentes, documentação breve e registros exigidos na fila/PRD. Não declarar validação investigativa com base apenas em testes sintéticos.

## 7. Etapa 2 — Proposta futura, fora da primeira entrega

**Não implementar nesta tarefa.** Depende de autorização específica e da avaliação dos resultados da Etapa 1.

| Frente | Condições mínimas |
|---|---|
| **Recorrência financeira e camadas** | Transações estruturadas, direção, datas, valores, identidade das contas, deduplicação e caminhos documentados. |
| **Arcos financeiros no mapa** | Relações financeiras comprovadas e localização corretamente atribuída; esclarecer que o arco não representa percurso físico. |
| **CEP e logradouro** | Base local com cobertura, licença, atualização e precisão verificadas. |
| **Bases de consulta** | Camada separada, origem visível e vedação de incorporação automática aos fatos do caso. |
| **Semelhança de MO** | Vocabulário consistente, janela temporal e avaliação de falsos positivos. Banco, DDD ou modalidade isolados não bastam. |
| **Agrupamentos geográficos** | Quantidade e qualidade suficientes de dados; considerar precisão, concentração populacional e endereços compartilhados. |
| **Priorização automática** | Critérios explicáveis e calibrados por revisão humana; pontuação não equivale a probabilidade de culpa. |

A evolução deve apoiar a descoberta de relações para investigação. **Identificação de organização criminosa e planejamento operacional não serão conclusões automáticas do sistema.**
