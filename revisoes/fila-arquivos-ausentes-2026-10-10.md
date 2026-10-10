# TS05 — arquivos reservados ausentes

O requisito RV20 mandava recusar conclusão por arquivo reservado ausente ou vazio. O código conferia ambos, mas apenas bloqueava arquivos vazios; ausentes geravam um aviso depois de marcar a tarefa concluída.

A correção recusa ausência antes de alterar o quadro. A exceção existente `--sem-conferir-arquivos` continua exigindo justificativa de ao menos quinze caracteres; seu registro agora identifica todas as lacunas presentes, inclusive vazio e ausente juntos. Diretórios, globs, aliases de caminhos e arquivos vazios legítimos preservam a semântica anterior. Um `__init__.py` ausente não é tratado como arquivo vazio legítimo.

TDD em workspace exclusivamente fictício: cinco falhas reproduzidas, incluindo CLI real em subprocesso com cópia do script dentro de TEMP. A conclusão recusada preserva o quadro byte a byte e remove a trava. O cenário autorizado confirma retorno zero e registra o motivo e os arquivos ausentes. O teste do alias conclui somente após criar seu arquivo canônico fictício.

Validação final: doze testes de `teste_fila_evidencia_rv20.py` e oito de `teste_fila_tarefas_rv14.py`, **20 aprovados em 7,335 s**, Python da venv 3.12.14 e UTF-8 explícito. Comando: `.venv/Scripts/python.exe -m unittest discover -s plugin/investigacao-cpj/app/testes -p "teste_fila_*rv*.py" -v`. Verificação de whitespace passou. Nenhuma entrega histórica foi reaberta.

Snapshots e logs: `C:/Users/alan_/AppData/Local/Temp/cpj-ts05-before-20261010`, arquivos `red.log` e `green-final.log`. Nenhum teste operou sobre a fila real, casos, O.S., configurações ou credenciais.
