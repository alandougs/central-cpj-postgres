---
description: Analisa o IP de fraude/estelionato - ficha, cronologia, pessoas, caminho do dinheiro, elementos do art. 171, lacunas
argument-hint: <ID do caso> [foco ou Ordem de Serviço]
---

Analise o caso: $ARGUMENTS

Use a skill `analise-ip-fraude` sobre `casos\<ID>\01-extracao\`. Para IPs acima de ~100 páginas, divida em blocos e use agentes `analista-documental` em paralelo; para as tabelas financeiras, use o agente `analista-financeiro`.

- Início: `caso.py status <ID> em_analise`. Fim: `caso.py status <ID> analisado` + `caso.py set <ID> modalidade=... financeiro.valor_rastreado=... financeiro.transacoes=... financeiro.contas_destino=... financeiro.camadas=... financeiro.prejuizo_declarado=... financeiro.prejuizo_documentado=... vitimas=... investigados=...` (somente valores que constam).
- Gere `02-analise\pessoas.csv` no formato fixo da skill (`nome;mae;pai;cpf;rg;nascimento;telefones;enderecos;empresas;cnpj;emails;placas;condicao;paginas;documento`, UTF-8 com BOM, vários valores com ` | `), só com dados como constam nos autos.
- Bases de consulta (`consulta\`) e referências (`referencias\`) não são fonte da análise.
- Se o pedido veio da Central (plantão), informe o progresso nos marcos do pedido.
- Rode `rag.py cruzar <ID>` depois de indexar: se chaves Pix/contas/CPFs aparecerem em outros casos, registre em `02-analise\conexoes.md` como indício a verificar.
- Rode `indexar.py` ao final.
- Scripts em `plugin\investigacao-cpj\skills\base-cpj\scripts\`.

Entregue resumo curto: modalidade, cronologia essencial, caminho do dinheiro com totais, conexões com outros casos, lacunas e dados críticos pendentes de conferência. Próximo passo: `/relatorio-ip <ID>`.