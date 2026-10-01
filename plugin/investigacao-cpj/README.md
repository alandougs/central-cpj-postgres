# investigacao-cpj (plugin Claude Code)

Plugin do ambiente de investigação de Alan Douglas Silva (CPJ Presidente Prudente). Fonte de conhecimento: [alandougs/repo-ia-alandougs](https://github.com/alandougs/repo-ia-alandougs) + modelo DOCX CPJ 2026 + skills da conta (relatório de investigação, delegado, OSINT).

## Componentes

| Tipo | Nome | Origem no acervo |
|---|---|---|
| Skill | `pdf-autos-policiais` | `skills/pdf-autos-policiais` (adaptada p/ Windows + tabelas CSV) |
| Skill | `analise-documental` | `skills/analise-documental` |
| Skill | `analise-ip-fraude` | nova — especialização de análise documental p/ art. 171 CP |
| Skill | `relatorio-ip-fraude` | nova — modelo DOCX CPJ + "Modelo Alan" (skill da conta) |
| Skill | `base-cpj` | nova — casos, estatística, RAG, painel |
| Agente | `analista-documental` | `system-prompts/assistente-analise-documental.md` |
| Agente | `analista-financeiro` | `prompts/extrair-tabela-bancaria.md` |
| Agente | `revisor-de-relatorio` | `prompts/revisar-relatorio.md` |
| Comandos | `/novo-caso` `/processar-ip` `/analisar-ip` `/relatorio-ip` `/entregar` `/calibrar` `/painel` `/buscar` `/revisar-relatorio` `/fluxo-ip` | `fluxos/analise-documental.md` |
| Referência | `referencia/` | governança, fluxo, guias, critérios, template |
| Aplicação | `app/` (Central CPJ) | nova — interface local com login e perfis: Início (pendências e prazos), Nova O.S. (upload + OCR/extração), Casos (ficha, IA, editor, DOCX/PDF, baixa), Pesquisa (RAG, relacional, vínculos), Estatísticas, Sistema (exportar/importar, bases de consulta, referências, agentes de plantão, usuários) |

## Instalação (já feita neste PC)

```bash
claude plugin marketplace add "C:\CPJ - TRABALHO\plugin"
claude plugin install investigacao-cpj@cpj-local
```

Após editar arquivos do plugin: aumente `version` em `.claude-plugin/plugin.json` e rode `claude plugin marketplace update cpj-local` e `claude plugin update investigacao-cpj@cpj-local` (ou reinicie a sessão).

## Estado

`0.1.0` — rascunho. Scripts validados com PDF fictício; pendente validação em IP real com conferência humana (ver `skills/pdf-autos-policiais/VALIDACAO.md`).
