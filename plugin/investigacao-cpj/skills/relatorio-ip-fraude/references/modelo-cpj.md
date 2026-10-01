# Modelo CPJ 2026 — estrutura extraída do DOCX do investigador

Fonte: `modelos\MODELO RELATORIO DE INVESTIGACAO - CPJ 2026.docx` (A4, margens 2 cm, Arial 12, justificado).

## Cabeçalho (timbre — preservado pelo gerador)

Brasão + tabela: SECRETARIA DA SEGURANÇA PÚBLICA / POLÍCIA CIVIL DO ESTADO DE SÃO PAULO / Departamento de Polícia Judiciária de São Paulo Interior 8 – DEINTER 8 / Delegacia Seccional de Polícia de Presidente Prudente / Central de Polícia Judiciária.

## Rodapé (preservado)

Endereço e telefones da CPJ; data (texto fixo, atualizado por `data_rodape`); "Página X de Y" (campos automáticos).

## Corpo

| Ordem | Elemento | Formato | Campo da minuta |
|---|---|---|---|
| 1 | RELATÓRIO DE INVESTIGAÇÃO | centralizado, negrito, 16 pt | — |
| 2 | Ordem de Serviço: … | negrito | `ordem_servico` |
| 3 | Referência: IPe nº <número> / Processo nº <número> (DETERMINAÇÃO DO DELEGADO, 30/09/2026: SOMENTE o número do Inquérito Policial Eletrônico e do Processo Judicial; NUNCA colocar BO nem IP local) | negrito | `referencia` |
| 4 | Natureza: {tipificação que constar nos autos} | negrito | `natureza` |
| 5 | Investigado (s): … | negrito | `investigados` |
| 6 | Vítima(s): … | negrito | `vitimas` |
| 7 | Local: {endereço dos fatos} | negrito | `local` |
| 8 | Data dos Fatos: … | negrito | `data_fatos` |
| 9 | EXCELENTÍSSIMO (A) SENHOR (A) DOUTOR (A) DELEGADO (A) DE POLÍCIA, — ajustado pelo gênero: **M** "EXCELENTÍSSIMO SENHOR DOUTOR DELEGADO DE POLÍCIA,"; **F** "EXCELENTÍSSIMA SENHORA DOUTORA DELEGADA DE POLÍCIA," | negrito | `delegado_genero` |
| 10 | Cumprimento respeitosamente Vossa Excelência e venho apresentar este relatório de investigação, conforme segue: | — | — |
| 11 | **RESUMO DOS FATOS** | negrito | `## RESUMO DOS FATOS` |
| 12 | **DILIGÊNCIAS REALIZADAS** | negrito | `## DILIGÊNCIAS REALIZADAS` |
| 13 | **CONCLUSÃO** | negrito | `## CONCLUSÃO` |
| 14 | Portanto, submeto o presente relatório… / Era o que me cumpria informar. É o relatório. | — | — |
| 15 | [local, Estado], {data} | à direita | `local_data` |
| 16 | Assinatura (imagem) / Alan Douglas Silva / Investigador de Polícia | centralizado | — |
| 17 | Endereçamento final por gênero — **M** "Ao Excelentíssimo Sr. Dr. / NOME / Delegado de Polícia / Central de Polícia Judiciária"; **F** "À Excelentíssima Sra. Dra. / NOME / Delegada de Polícia / Central de Polícia Judiciária" | negrito | `delegado`, `delegado_genero` |

## Instruções do próprio modelo (normativas para a redação)

- **Resumo dos fatos:** resumir os fatos investigados (BO, autos, IP, quebras de sigilo bancário/fiscal etc.) em **brevíssima síntese**; se declarado, descrever o que foi solicitado na Ordem de Serviço pela autoridade policial.
- **Diligências realizadas:** elencar e descrever as diligências, dados analisados e obtidos; qualificação (nome, RG, CPF, filiação, naturalidade, endereços, telefone); **cruzar dados**; **percorrer o caminho do dinheiro (vítima, conta de passagem, até chegar ao destinatário)**, identificando supostos autores; **elaborar planilha** se necessário à demonstração da dinâmica financeira; analisar e descrever fotos ou vídeos.
- **Conclusão:** breve descrição do resultado. Sugestão de providências **delimitada ao objetivo da Ordem de Serviço e ao escopo da investigação** (ex.: em caso especial e cabível, representação por quebra de sigilo bancário/fiscal do investigado; busca e apreensão domiciliar quando preenchidos os requisitos) — **sempre ponderar; preferível não sugerir, deixando o delegado atuar em sua discricionariedade.**
