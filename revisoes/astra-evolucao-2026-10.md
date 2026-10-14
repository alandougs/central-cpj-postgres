# ASTRA — execução do épico #4

Missão autorizada pelo operador em 14/10/2026. Fonte dos requisitos: épico #4, issues #5–#17 e `docs/ASTRA-PLANO-AGENTES-2026-10.md` do GitHub. Todos foram consultados integralmente; estavam abertos e sem comentários. Desenvolvimento isolado, iniciado em `origin/main` (`f56653c`), branch `codex/astra-evolucao-20261014`. A branch padrão `master` não foi usada. Arquivos locais anteriores e PR #18 preservados, sem merge em produção. Somente código e dados fictícios.

## Controle de execução

| Issue | Implementação | Validação | Homologação do operador |
|---|---|---|---|
| #5 Contrato manual | API e formulário alinhados; aliases explícitos; O.S., documento, página, fls. e observação; tipos e duplicatas validados | 7 testes AST05, incluindo Edge real, aprovados; GF01 11/11 e consultas existentes aprovados; regressão rápida 4/5 suítes: falha preexistente em OCR/escrivão fictício | Pendente |
| #6 Persistência | Próxima etapa | Pendente | Pendente |
| #7 Exclusão seletiva | Pendente | Pendente | Pendente |
| #8 Evidências e confirmação | Pendente | Pendente | Pendente |
| #9 Jornada guiada | Pendente | Pendente | Pendente |
| #10 Linguagem natural | Pendente | Pendente | Pendente |
| #11 Inspetor | Pendente | Pendente | Pendente |
| #12 Rascunhos | Pendente; contratos de versão e DOCX separados já existem no backend | Pendente | Pendente |
| #13 Layout | Baseline sintético anterior às mudanças em execução | Pendente | Pendente |
| #14 Paginação | Pendente | Pendente | Pendente |
| #15 Atualização adaptativa | Pendente; consultas duplicadas e erros silenciosos identificados | Pendente | Pendente |
| #16 Módulos | Pendente; fronteiras e testes dependentes do HTML inventariados | Pendente | Pendente |
| #17 Homologação técnica | Pendente | Pendente | Pendente |

## #5 — plano, execução e prova

Causa reproduzida: formulário enviava `caso_id`/`fonte`, enquanto a rota lia `caso`/`obs`; o filtro de caso no grafo não era copiado ao formulário. O teste HTTP demonstrou fonte perdida, duplicata aceita, O.S. inexistente aceita e escrita disponível ao leitor. O teste do navegador falhou inicialmente porque a O.S. selecionada não preenchia o vínculo.

Contrato: `a_tipo`, `a_valor`, `b_tipo`, `b_valor`, `relacao`, `caso`, `documento`, `pagina`, `fls`, `observacao`. Aceitos aliases `caso_id`, `fonte`, `obs`; pares divergentes são recusados. `PESSOA` exige ID de registro; nome sem identidade é `NOME`, candidato. O cadastro manual é hipótese, sem confirmação automática. Índice mantém O.S. em `fonte` para compatibilidade e localizador estruturado para as referências. API GET expõe os campos estruturados e localizador legível. A fonte autoritativa e IDs estáveis pertencem à issue #6, seguinte.

Arquivos: `app/rotas/consulta.py`, `app/static/index.html`, `app/testes/astra_fixture.py`, `app/testes/teste_astra_ast05.py`, PRD e controle compartilhado. Tests: Python do ambiente existente, processo e workspace temporários; Edge headless do runtime local. Nenhuma API de IA utilizada. QuickJS declarado em requirements-dev foi instalado exclusivamente em pasta TEMP de dependências de teste; não alterou o ambiente operacional.

## Retomada

Executar issues na ordem de dependência. Antes de editar, conferir reserva no controle compartilhado da pasta principal e assumir a próxima tarefa. Não duplicar contratos existentes do editor/FINAL nem alterações do PR #18. Fonte e instruções do caso não podem ser substituídas por coincidências do grafo. Manter as issues abertas até a revisão/homologação humana; implementação e testes são estados distintos.

Regressão rápida AST05: `ferramentas/testar-tudo.py --rapido --incluir teste_astra_ast05.py`, 4/5 suítes aprovadas; `teste_dados_os_codex.py::test_pdf_imagem_preenche_escrivao_depois_do_ocr_real` falha com escrivão vazio, reproduzida antes desta missão. Log local TEMP `cpj-astra-ast05-rapido.log`. Nenhuma afirmação de suíte inteira verde.
