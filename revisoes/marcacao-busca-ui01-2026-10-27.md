# UI01 — protocolo de marcação entre a busca e a Pesquisa da Central (27/10/2026)

Executor: Claude-UI01-20261027. Origem: defeito **D7** achado pela revisão independente de LC01
(ver [lacunas-2026-10-27.md](lacunas-2026-10-27.md)), proposto como UI01 na fila e reservado nesta
data. Sem push, sem publicação, sem dado de caso neste registro.

## Ponto de retomada (ler primeiro)

**O código está pronto e testado; o que falta é a revisão independente e a conferência do
operador.** Quem retomar — inclusive no Codex — começa daqui:

1. **Revisão independente de UI01 está PENDENTE.** Tentei despachar um revisor em subagente e ele
   morreu com erro 403 da API (`oauth_org_not_allowed`: a organização desabilitou o acesso de
   assinatura ao Claude Code). Nenhum agente pôde ser criado nesta sessão. No lugar dele rodei uma
   bateria adversarial própria (abaixo), que **não** substitui a revisão exigida por AGENTS.md,
   porque não é independente da autoria. **A revisão independente continua devendo.**
2. **Três suítes falham na rodada integral** (abaixo), nenhuma por causa desta mudança — mas a de
   LC01 merece diagnóstico, porque falha **só dentro do sandbox do runner**.
3. **Nada foi publicado.** Push e sincronização remota seguem sem autorização, como em LC01.

## O defeito

A Pesquisa da Central fazia, no JavaScript:

```js
esc(r.trecho).replace(/\[([^\]]+)\]/g, "<mark>$1</mark>")
```

Isto é, destacava **qualquer** texto entre colchetes do trecho devolvido. O motivo era que o
`snippet()` do FTS5 delimitava o termo casado com `[` e `]`. Só que colchete, em trecho de autos,
é determinação das regras 3 e 17 de `AGENTS.md` — `[dígito incerto]`, `[PESQUISAR: CNPJ]` — e com
a busca híbrida de LC01 um acerto **só por semântica** devolve o excerto cru, onde *todo* colchete
vem dos autos. Resultado: a interface marcava anotação de incerteza e pendência de diligência como
se fossem o termo pesquisado. Num sistema cujo propósito é dizer onde o termo aparece nos autos,
isso é marcação falsa de prova.

## A correção: marcação por posição, não por caractere no texto

O princípio: **a busca diz o que destacar; a interface não interpreta o conteúdo.** Nada no texto
devolvido é marcador, então colchete dos autos chega literal e nunca vira destaque.

| Arquivo | Mudança |
|---|---|
| `plugin\investigacao-cpj\skills\base-cpj\scripts\rag.py` | `MARCA_I`/`MARCA_F` (`\x02`/`\x03`) como sentinela do snippet; `snippet()` passa a usar `char(2)`/`char(3)`; `_desmarcar()` converte sentinela em posições; `_realcar()` reaplica no terminal entre `»` e `«`; `buscar()` devolve a chave nova `marcas` (8 chaves, era 7) com o `trecho` já limpo; local `marcas` do SQL renomeado para `lugares` para não colidir |
| `plugin\investigacao-cpj\app\static\js\pesquisa.js` | função nova `trechoHTML(r)`: fatia por posição, escapa cada pedaço e envolve só o marcado em `<mark>`; marca malformada cai para o texto apenas escapado |
| `plugin\investigacao-cpj\app\testes\teste_marcacao_busca_ui01.py` | novo, 13 testes |
| `rag\README.md` | bullet "Marcação do termo casado" |

Contrato: `marcas` é lista de intervalos `[inicio, fim)` em **unidade UTF-16**, a mesma que o
navegador usa para fatiar a string. Acerto só por semântica devolve `marcas` vazia, porque não
houve termo casado. A sentinela nunca sai de `buscar()`.

### Por que UTF-16 e não índice do Python

Medido no protótipo: com índice de ponto de código (o natural em Python), o texto `😀 pix fim` com
marca no `pix` sai no navegador como `😀<mark> pi</mark>x fim` — **o destaque desliza um caractere
e passa a cobrir o texto errado**, e desliza mais a cada caractere fora do plano básico. Com
unidade UTF-16 sai `😀 <mark>pix</mark> fim`. Custou uma linha (`tam += 1 if ch <= "\uffff" else 2`)
e tirou uma classe inteira de erro silencioso.

## Evidência

**Teste de UI01: 13 de 13 passando.** Antes da correção, com o mesmo arquivo de teste: 2 falhas e
8 erros — a reprodução do defeito. O teste cobre os dois caminhos exigidos pela tarefa (snippet do
FTS e excerto semântico), o escape, e a regressão na fonte (`<mark>$1</mark>` não pode voltar).

**`snippet()` aceita sentinela de controle** — conferido em SQLite isolado antes de mexer no
produto: `'O extrato aponta a \x02transferencia\x03 para a conta 555 [digito incerto] ...'`, com os
colchetes dos autos intactos.

**Bateria adversarial contra as funções de produção** (18 formas de marca malformada: `NaN`,
`Infinity`, `-0`, número como texto, par de 3 elementos, array aninhado, objeto com `length`,
`__proto__`, marcas fora de ordem, sobrepostas, vazias, `trecho` ausente/`null`/número/objeto com
`toString`). **Nenhuma vazou HTML cru**; todas as malformadas caem para o texto só escapado. O
escape e a CSP ficam íntegros.

**CLI na base real**, sem imprimir conteúdo de caso: 3 resultados, 4 marcas pareadas no terminal,
nenhuma sentinela vazada, sem traceback.

**Limite conhecido e aceito:** se o texto dos autos contiver `\x02`/`\x03` — caractere de controle
que transcrição de PDF não produz — uma sentinela ímpar pode alargar uma marca. Nunca gera HTML,
nunca altera o texto visível além de remover o caractere invisível. Está documentado no código.

## Rodada integral da suíte (pendência que vinha de LC01)

Rodada com `.venv\Scripts\python.exe ferramentas\testar-tudo.py` **no código corrigido**: 290
suítes OK, 3 com falha, nenhuma por causa desta mudança.

| Suíte | Causa | De quem é |
|---|---|---|
| `teste_ci_volume_ci27.py` | `helper CI27 ausente` | bloqueio conhecido da CI27, que está `em andamento` |
| `teste_fontes_os_rp33.py` | criação de junction sem privilégio; o teste ainda soma `None + str` ao montar a mensagem de erro, mascarando a causa | pré-existente, de privilégio do SO |
| `teste_lacunas_lc01.py` | `UnicodeDecodeError: 'utf-8' codec can't decode byte 0x87` **dentro do sandbox do runner**; a mesma suíte roda **26/26 OK** direto na pasta de testes | a investigar |

O próprio `testar-tudo.py` termina com `UnicodeEncodeError` (cp1252) ao **imprimir** o detalhe das
falhas — é defeito de relatório do runner, não de teste, e esconde o diagnóstico de quem roda no
console padrão do Windows. Contornei com `PYTHONIOENCODING=utf-8`.

Atenção para quem retomar: o `python` do PATH **não** serve neste workspace (não tem `docx` nem
`quickjs`); é `F:\CPJ - TRABALHO\.venv\Scripts\python.exe`, Python 3.12.14.

## O que falta

1. **Revisão independente de UI01** — exigida por AGENTS.md, não feita, pelo motivo acima. É a
   próxima coisa a fazer.
2. **`teste_lacunas_lc01.py` no sandbox** — por que decodifica como UTF-8 um byte `0x87` lá e não
   aqui.
3. **`teste_fontes_os_rp33.py`** — o `None + str` que esconde a causa real.
4. **Relatório do `testar-tudo.py`** — imprimir o detalhe sem depender do code page do console.
5. **Push / sincronização remota (SY05)** — sem autorização. Exige conferência de sigilo do
   operador.

Itens 2 a 4 são defeitos de ferramenta de teste, fora do escopo de UI01; não os corrigi para não
misturar com a tarefa reservada.
