# Técnicas de busca, verificação e preservação

## 1. Buscadores: como perguntar
- Aspas para frase exata; `OR`, `-` (exclui), `*` (curinga); `site:`, `inurl:`, `intitle:`, `filetype:pdf`, `before:`/`after:` (datas). Repita nos buscadores **Google, Bing, DuckDuckGo, Yandex e Brave**; resultados diferem.
- **Variações do identificador:** nome com e sem acento, abreviado, com sobrenome do meio, invertido, apelido; **telefone** em `(65) 99999-9999`, `65999999999`, `+55 65 99999-9999`, `99999-9999` e sem o 9 inicial (números antigos); **CPF** com e sem pontuação (busque em diários e processos, onde às vezes aparece parcial); **e-mail** completo e só o usuário; **chave Pix** como aparece.
- Combine identificador + contexto: `"nome" + cidade`, `"telefone" + "vendo" OR "aluguel"`, `"razão social" + golpe OR fraude OR reclamação`, `site:t.me "telefone"`, `site:jusbrasil.com.br "nome" + CPF parcial`.
- Registre a **consulta exata** e o **buscador**, inclusive quando nada foi achado.

## 2. Pivô e correlação
Um identificador leva a outro: telefone → anúncio → foto → perfil → empresa → sócio → endereço. Guarde a **cadeia do pivô** (de onde veio cada dado). Cruze **endereço, telefone, e-mail, IP, foto, texto e estilo** entre alvos. Coincidência de um único dado fraco não vincula pessoas.

## 3. Verificação e grau de confiança
- **Fonte:** oficial (RFB, tribunal, junta) · aberta corroborada (2+ independentes) · aberta única · declaratória (perfil/anúncio que diz sobre si) · agregador sem origem.
- **Confiança do achado:** CONFIRMADO (oficial ou 2+ independentes com identificador forte) · PROVÁVEL (1 forte + 1 fraco coerente) · POSSÍVEL (só compatibilidade) · DESCARTADO (incompatível).
- **Homônimos:** nunca junte por nome. Precisa de dois identificadores fortes (CPF/data de nascimento/filiação/endereço documentado/CNPJ como sócio).
- **Golpe de identidade:** foto/nome de terceiro reutilizados em perfil falso são comuns em fraude; perfil ≠ pessoa.
- **Datas:** confirme a data do conteúdo (criação, publicação, edição); conteúdo pode ser posterior ou anterior ao fato.
- **Negativo:** "não localizado em fonte aberta" **não** é "não existe".

## 4. Captura e cadeia de custódia (CPP, arts. 158-A a 158-F, por analogia)
1. **Capture antes de interagir ou reabrir.** Conteúdo volátil primeiro.
2. Registre em cada captura: **URL completa, data e hora (fuso), quem capturou, navegador/ambiente**, e o identificador buscado.
3. **Formatos:** (a) imagem da página inteira com URL e relógio visíveis; (b) PDF ou MHTML da página; (c) quando o conteúdo for importante, **arquivo WARC** ou captura com ferramenta que gere registro (ex.: ferramentas de captura forense/ArchiveBox/Browsertrix; extensões de captura com log).
4. **Hash:** SHA-256 de cada arquivo (`Get-FileHash -Algorithm SHA256 <arquivo>`); anote na ficha.
5. **Armazenamento:** `casos\<ID>\01-extracao\osint\<alvo>\` (nunca em `acervo\` ou `calibracao\`); arquivo original preservado, cópias de trabalho separadas.
6. **Vídeo/story/live:** gravação de tela com relógio visível e URL, mais o arquivo se baixável licitamente; lembre que some rápido.
7. **Prova central:** se o conteúdo for peça-chave, considerar **ata notarial** ou perícia/ferramenta forense institucional e comunicar o delegado. Cópia local com hash é subsídio, não perícia.
8. **Não usar** serviços públicos de arquivamento (Wayback "Save Page Now", archive.today) em caso sigiloso ou de alvo ativo: eles publicam a URL/cópia e podem alertar o alvo. Prefira captura local.
9. **Preservação em provedor:** quando o conteúdo estiver em conta de provedor e puder ser apagado, considerar **requerimento cautelar de guarda de registros** pela autoridade (Marco Civil, arts. 13, § 2º, e 15, § 2º) e depois a ordem judicial — sinalizar como dado faltante.

## 5. Ficha do alvo (`02-analise\osint-<alvo>.md`)
```
# OSINT — <alvo>   (data/hora, pesquisador, ambiente)
Objetivo (pergunta da O.S./do IP):
Identificadores de partida (como constam nos autos, fls.):
| Consulta/fonte (URL, buscador) | Data/hora | Achado (transcrição fiel) | Captura (arquivo, SHA-256) | Confiança | Observação |
Pivôs seguidos (de → para):
Resultado negativo (o que foi buscado e não localizado):
Homônimos afastados/pendentes:
Conclusão prudente (fato × indício):
DADOS FALTANTES (CAIXA ALTA): ...
```

## 6. Aprofundamento (quando vale a pena)
- **Empresa:** histórico de endereço/sócios (várias consultas ao longo do tempo), outras empresas do mesmo endereço, telefone e e-mail no site, domínio (data de criação × abertura do CNPJ), publicidade paga (biblioteca de anúncios das plataformas), clones de loja.
- **Perfil:** primeiras e últimas publicações, marcações, comentários de terceiros, fotos com pontos de referência, seguidores em comum, horários de atividade (pista de fuso/rotina), links na bio (agregadores de link), outros usuários com mesmo avatar.
- **Anúncios/golpes de venda:** o mesmo telefone/foto em várias cidades e datas indica atuação em série; anotar cada anúncio com data e valor.
- **Blockchain:** rastrear entradas e saídas do endereço, ver agrupamentos e corretoras; converter valores na data.
- **Geolocalização:** compare linha do horizonte, fachadas, placas e sombras; usar imagens de satélite com data; registrar a margem de erro.
- **Linha do tempo:** organizar tudo em cronologia com fonte; o padrão de datas frequentemente conecta contas.

## 7. Erros que derrubam a prova
Não registrar URL/hora; captura recortada; edição/anotação sobre a imagem original; uso de fonte ilícita; homônimo tratado como a pessoa; conclusão além do dado; alerta ao alvo; mistura de contas pessoais e de trabalho; ausência de hash.
