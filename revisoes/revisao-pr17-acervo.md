# Revisão do PR #17 do acervo (draft) — GH03

Revisão em 01/10/2026 por Claude-1. Somente leitura: branch `origin/feat/fraudes-grafo-recuperacao-v2` extraída para pasta temporária; nenhum arquivo do clone nem do GitHub foi alterado. O merge é decisão do investigador.

## Resumo

- 13 commits, 58 arquivos, +3.680/−585. Traz o rastreio L0→Ln, o Grafo de Rastreamento Financeiro, a Matriz de Recuperação, o comando `/recuperar-ativos`, a skill `recuperacao-ativos-fraude`, a skill `correlacao-fraudes-seriadas` e o agente `inteligencia-fraudes-seriadas`.
- **A branch está em dia com o `main`** (0 commits de atraso, `main` = PR #12) e **não tem conflito de merge** (`git merge-tree` limpo).
- Conteúdo bem escrito e cauteloso. Recomendação: **aprovar depois de 4 ajustes pequenos** (abaixo). Nenhum impede a leitura do PR, mas o item 2 deve ser resolvido antes do merge.

## Revisão técnica

| Verificação | Resultado |
|---|---|
| `scripts/testar_nucleo_fraudes.py` | **OK** — "núcleo de fraude validado (rastreio + recuperação + grafo)" |
| `scripts/validar.py` (Windows, local) | 3 erros: `catalogo.json`, `llms.txt` e `ROUTER.md` "desatualizados". O `main` atual **também** falha localmente em `llms.txt` e `ROUTER.md`, então esses dois são do ambiente (gerador × Windows), não do PR. Regerar `catalogo.json` na pasta temporária removeu o erro do catálogo. |
| Dados reais | **Nenhum CPF válido** (dígito verificador) nem número de caso/processo no conteúdo da branch. Fixture `aval-fraude-falso-parente-ficticio` é fictícia. |
| Conflito com #14/#15 | Cada PR regenera `catalogo.json`, `llms.txt` e `ROUTER.md`: haverá conflito nesses três arquivos ao mergear o segundo. Resolver regenerando, não editando à mão (ver GH04). |

Pendência técnica: confirmar no **CI do GitHub (Linux)** que `validar.py` passa. O último commit é "fix(ci): remover validação SQLite redundante", o que indica que o CI já falhou antes. Não consegui ver o resultado (sem `gh` aqui).

## Revisão das ferramentas dos agentes (N0–N4)

- A skill `recuperacao-ativos-fraude` declara `autonomia: N1` e `estado: rascunho`. Coerente.
- **Problema:** o novo agente `inteligencia-fraudes-seriadas` (e os demais agentes gerados) recebe o mesmo conjunto de ferramentas, `Read, Write, Edit, Bash, Glob, Grep`, sem relação com o nível de autonomia. É o achado nº 13 do plano V1 (R09). Para um agente que **correlaciona vários casos**, Bash e Write em todo o workspace são mais poder do que o nível N1 justifica.
- Ajuste sugerido: gerar agentes N0/N1 só com `Read, Glob, Grep` (e `Write` restrito à pasta de saída da análise).

## Revisão jurídica

Pontos positivos (conferidos no texto da skill e dos fundamentos):
- Competência separada: o investigador **não** decreta constrição, não afirma perdimento nem fixa indenização; o delegado representa ao juízo pelas medidas cabíveis.
- Vocabulário de estados patrimoniais (identificado, rastreado, localizado, bloqueado, devolvido, liberado, apreendido, pendente) e a regra de que "bloqueado" **não** é "recuperado" e não reduz o prejuízo.
- Cautelas de terceiro de boa-fé, proporcionalidade, e de não atribuir ativo por parentesco ou titularidade formal isolada.
- `fundamentos-legais.md` já cita a reserva de jurisdição para movimentação bancária (LC 105/2001).

Ajustes sugeridos:
1. **Reserva jurisdicional dentro da própria skill.** Em `recuperacao-ativos-fraude`, o passo 7 lista "requisição legalmente cabível" sem dizer quando ela **não** basta. Acrescentar: dados cadastrais podem ter requisição própria; **movimentação bancária e quebra de sigilo exigem ordem judicial** (LC 105/2001); preservação de registros de acesso segue o Marco Civil (Lei 12.965/2014).
2. **Conferir a redação vigente de CP art. 171, § 2º, VII (cessão de conta)**, citado em `fundamentos-legais.md` linha 10. Não consegui confirmar o inciso nem sua redação atual por fonte oficial nesta revisão. Conferir no Planalto antes do merge; se divergir, corrigir a tabela e os trechos que a citam.
3. **MED/Pix:** a skill cita "regras do MED/Pix do Banco Central" sem número de normativo. Indicar a resolução vigente e a data de conferência.
4. **Jurisprudência/legislação:** manter o aviso "conferir sempre a redação vigente" também no cabeçalho de `fundamentos-legais.md`.

## Recomendação

1. Regerar `catalogo.json`, `llms.txt` e `ROUTER.md` no CI (Linux) e confirmar `validar.py` verde.
2. Corrigir os itens jurídicos 1 e 2 (os mais importantes) e restringir as ferramentas do agente de fraudes seriadas.
3. Só então tirar o PR de draft. Mergear #17 **antes** de #14 e #15 e regenerar os três arquivos gerados em cada merge posterior.
4. Nada deste PR foi aplicado ao core (GH07 trata disso).

Não houve alteração em `acervo/` nem no GitHub nesta revisão.
