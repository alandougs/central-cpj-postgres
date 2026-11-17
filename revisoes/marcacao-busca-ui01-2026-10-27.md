# UI01 — protocolo de marcação entre a busca e a Pesquisa da Central (27/10/2026)

Executor: Claude-UI01-20261027. Origem: defeito **D7** achado pela revisão independente de LC01
(ver [lacunas-2026-10-27.md](lacunas-2026-10-27.md)), proposto como UI01 na fila e reservado nesta
data. Sem push, sem publicação, sem dado de caso neste registro.

## Ponto de retomada (ler primeiro)

**O código está pronto, testado e com revisão independente concluída e aprovada em 28/10/2026 (ver seção "Revisão Independente (28/10/2026 — Luna-8-Auditor-UI01)" ao final).** Registro original de 27/10/2026:

1. **Revisão independente de UI01:** concluída em 28/10/2026 por `Luna-8-Auditor-UI01` (**Parecer: APROVADO**). Em 27/10/2026 o subagente revisor havia falhado com erro 403 da API (`oauth_org_not_allowed`).
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

1. ~~**Revisão independente de UI01**~~ — **Concluída em 28/10/2026 (`Luna-8-Auditor-UI01`, parecer APROVADO; ver seção abaixo).**
2. **`teste_lacunas_lc01.py` no sandbox** — por que decodifica como UTF-8 um byte `0x87` lá e não
   aqui.
3. **`teste_fontes_os_rp33.py`** — o `None + str` que esconde a causa real.
4. **Relatório do `testar-tudo.py`** — imprimir o detalhe sem depender do code page do console.
5. **Push / sincronização remota (SY05)** — sem autorização. Exige conferência de sigilo do
   operador.

Itens 2 a 4 são defeitos de ferramenta de teste, fora do escopo de UI01; não os corrigi para não
misturar com a tarefa reservada.

## Revisão Independente (28/10/2026 — Luna-8-Auditor-UI01)

- **Auditor:** `Luna-8-Auditor-UI01` (subordinado ao coordenador Astra, independente do autor `Claude-UI01-20261027`, conforme Regra 23 de `AGENTS.md`).
- **Parecer:** **APROVADO**.

### Escopo inspecionado linha a linha

1. `plugin/investigacao-cpj/skills/base-cpj/scripts/rag.py`:
   - `MARCA_I, MARCA_F = "\x02", "\x03"` (linha 63) e `snippet(trechos_fts, 0, char(2), char(3), ' … ', 24)` em `_lexical` (linha 119).
   - `_desmarcar(s)` (linhas 78–97): remove todas as ocorrências de `\x02` e `\x03`, descarta sentinelas órfãs, aninhadas ou vazias (`if aberto is not None and tam > aberto`) e calcula as posições `[inicio, fim)` em unidades de código UTF-16 (`tam += 1 if ch <= "\uffff" else 2`).
   - `_realcar(trecho, marcas, abre="»", fecha="«")` (linhas 100–111): fatia em bytes `utf-16-le` (`i * 2`, `j * 2`) e aplica delimitadores de terminal (`»` e `«`), alinhado às unidades UTF-16 de `_desmarcar`.
   - `buscar(...)` (linhas 343–357): renomeia o placeholder SQL para `lugares` (linha 343); no caminho com snippet lexical usa `trecho, marcas = _desmarcar(bruto)` (linha 352) e no caminho exclusivamente semântico usa `trecho, marcas = _desmarcar(_resumo(r[7]))[0], []` (linha 354), garantindo que `trecho` saia sempre sem sentinelas e que resultados apenas semânticos tragam `marcas == []`.
2. `plugin/investigacao-cpj/app/static/js/pesquisa.js`:
   - `trechoHTML(r)` (linhas 139–149) e integração em `$("#f-busca").onsubmit` (linha 157): substitui o regex antigo `/\[([^\]]+)\]/g` por fatiamento posicional em UTF-16 (`t.slice(fim, i)` e `t.slice(i, j)`), escapando todos os fragmentos via `esc(...)` (`core.js` linha 5) e envolvendo exclusivamente os intervalos válidos em `<mark>...</mark>`. Qualquer marca malformada (`!Array.isArray(par) || par.length !== 2`, não inteiros, `i < fim`, `j <= i` ou `j > t.length`) aborta o destaque e devolve `esc(t)` completo e escapado.
3. `plugin/investigacao-cpj/app/testes/teste_marcacao_busca_ui01.py`:
   - 13 testes automatizados em 3 classes (`ProtocoloDeBuscaUI01`, `FonteDaPesquisaUI01`, `MarcacaoNaInterfaceUI01`), operando sobre workspace sintético em `tempfile.TemporaryDirectory` sem tocar em dados reais.
4. `rag/README.md`:
   - Documentação atualizada (linha 23) descrevendo o contrato de `trecho` e `marcas` em unidades UTF-16, o comportamento nos caminhos lexical e semântico e a preservação literal de colchetes dos autos (`[dígito incerto]`, `[PESQUISAR: CNPJ]`).

### Verificações independentes executadas e evidências

1. **Execução da suíte oficial de `UI01`:**
   - Comando: `.\.venv\Scripts\python.exe -B plugin\investigacao-cpj\app\testes\teste_marcacao_busca_ui01.py`
   - Resultado: `Ran 13 tests in 0.375s — OK` (código de saída `0`).
2. **Colchetes literais dos autos nos caminhos FTS e semântico:**
   - Verificado em banco SQLite sintético (`indexar.py --tudo` em diretório temporário isolado) com transcrição contendo `Início 😀 [dígito incerto] estelionato bancário [PESQUISAR: CNPJ] e \x02\x03 controle.`:
     - Caminho FTS (`modo='lexical'`, consulta `'estelionato'`): `trechoHTML` produziu `Fls. 5\nInício 😀 [dígito incerto] <mark>estelionato</mark> bancário [PESQUISAR: CNPJ] e  controle.` — apenas o termo pesquisado recebeu `<mark>`, e os colchetes das regras 3 e 17 permaneceram literais.
     - Caminho exclusivamente semântico (`modo='hibrido'` sem casamento lexical): `marcas` retornou `[]` e `trechoHTML` produziu `Fls. 5 Início 😀 [dígito incerto] estelionato bancário [PESQUISAR: CNPJ] e  controle.`, sem nenhum `<mark>`.
3. **Unidades UTF-16 com caracteres fora do BMP (emojis / surrogate pairs):**
   - Testado `Início 😀🔥 [dígito incerto] meio \x02pix\x03 e 👩🏽‍🔬 \x02conta\x03 [PESQUISAR: CNPJ] fim` (contendo múltiplos pares substitutos e sequência ZWJ):
     - `trechoHTML` em QuickJS renderizou `Início 😀🔥 [dígito incerto] meio <mark>pix</mark> e 👩🏽‍🔬 <mark>conta</mark> [PESQUISAR: CNPJ] fim` sem deslocamento de índice.
     - `_realcar` no Python renderizou `Início 😀🔥 [dígito incerto] meio »pix« e 👩🏽‍🔬 »conta« [PESQUISAR: CNPJ] fim`.
4. **Resistência a HTML/XSS e marcas adversariais em `trechoHTML(r)`:**
   - Vetores XSS dentro e fora de marcas (`<script>alert(1)</script>`, `"><img src=x onerror=alert(1)>`, `</mark><script>alert(1)</script><mark>`, `&lt;b&gt;[dígito incerto]&lt;/b&gt;`) foram integralmente escapados; a inspeção de tags HTML na saída confirmou que apenas `<mark>` e `</mark>` são emitidas.
   - Entradas malformadas (`null`, `undefined`, `{}`, `{trecho: null, marcas: null}`, intervalos sobrepostos `[[0, 3], [2, 5]]`, vazios `[[3, 3]]`, invertidos `[[4, 2]]`, negativos `[[-1, 2]]`, fora de limite `[[0, 999]]`, `NaN`, `Infinity`, strings `[["0", "2"]]`, tuplas de 3 elementos `[[0, 2, 3]]`) degradaram com segurança para `esc(t)` sem emitir nenhuma tag HTML.
5. **Ausência de vazamento das sentinelas `\x02`/`\x03`:**
   - Testadas combinações de sentinelas isoladas, invertidas, duplicadas e no texto original (`\x02`, `\x03`, `\x02\x03`, `\x03\x02`, `\x02\x02pix\x03\x03`, `texto \x02 sem fechar`, `texto \x03 sem abrir`): nenhuma sentinela vazou para `trecho`, para o HTML ou para o terminal, nem nos resultados FTS nem nos excertos semânticos.
