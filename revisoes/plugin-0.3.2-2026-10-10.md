# CL07 — instalação do patch necessário ao piloto

Após TS06 concluída e verificada, o integrador executou uma única atualização oficial de 0.3.1 para **0.3.2**, com retorno zero. O patch comunica o contrato de saídas atualizadas e preserva log/retorno se o gate posterior falhar. O gate permanece íntegro. Três testes focados independentes passaram em 1,873 s; executor registrou 12 testes da squad, rápida 5/5 e plantão em sandbox aprovados.

CLI confirmou `investigacao-cpj@cpj-local`, versão 0.3.2, habilitado, escopo user. Validações oficiais de pacote e marketplace aprovadas. **76 arquivos do bundle** coincidem por SHA-256 entre fonte, staging e cache; com o manifesto marketplace, staging contém 77 arquivos genéricos. Onze portáteis regenerados e 12 adaptadores conferidos sem alteração. README atualizado. Nenhuma segunda atualização foi executada nessa tarefa.

Evidências: `C:/Users/alan_/AppData/Local/Temp/cpj-cl07-final-20261010`, incluindo manifestos anteriores, log oficial, lista final do CLI e hashes. A autenticação já autorizada foi usada apenas pela ferramenta oficial. Nenhum caso real, chave, política de confiança, plugin externo ou Git remoto foi alterado. A segunda tentativa P01 pode iniciar em novo workspace fictício; seus resultados não são presumidos pela instalação.
