# Full-Time — verificação recuperada em 09/10/2026 (AG02)

O arquivo estava vazio apesar de a fila registrar AG02 concluída. Esta entrega
recupera evidências atuais em dados e diretórios fictícios; não comprova boot
operacional nem instalação de atalho no perfil do usuário.

## Defeito reproduzido e correção

`teste_fulltime.py` isolava CPJ_WORKSPACE, mas herdava APPDATA. Seu teste 05
executava instalar-boot e remover-boot na Startup herdada, podendo substituir e
apagar um atalho preexistente. O runner também herdava APPDATA.

A reprodução executou exclusivamente o teste 05 antigo em subprocesso com
APPDATA apontando para TEMP. A Startup fictícia continha um atalho válido com
descrição SENTINELA FICTICIA AG02 e bytes capturados antes da execução. O teste
antigo terminou com sucesso, mas apagou a sentinela: a regressão nova falhou em
`Teste apagou Startup herdada fictícia`. A verificação de isolamento também
reproduziu APPDATA fora do sandbox e ausência de restauração adequada.

O teste Full-Time agora cria APPDATA e Startup próprios sob seu diretório
temporário, guarda CPJ_WORKSPACE e APPDATA anteriores e restaura ambos em finally,
incluindo a ausência original dessas variáveis. Nenhum código do daemon foi
alterado. A nova regressão prova preservação byte a byte da sentinela herdada e
restauração do ambiente com variáveis originalmente presentes ou ausentes.

## Verificação executada

- `teste_isolamento_fulltime_ag02.py`: 2 testes aprovados em 8,704 s, após
  reproduzir 2 falhas e 1 erro no código anterior.
- `testar-tudo.py --rapido --incluir teste_fulltime.py`: 5/5 suítes aprovadas
  em 94,58 s. Solo 2,72 s; segurança 33,22 s; modularização 3,00 s;
  dados/OCR fictício 32,16 s; Full-Time 23,48 s.
- Full-Time executou seus cinco testes: arquivos, status parado, iniciar/status/
  parar, reinício após término do filho e instalar/remover atalho na Startup
  fictícia. Usou portas locais livres, nunca a Central real na porta 8765.
- `git diff --check` dos testes não apresentou erro.

Ambiente: Python do runtime Codex, PYTHONUTF8=1 e PYTHONPATH apontando para
`.venv/Lib/site-packages` do projeto; Tesseract PDF24 e tessdata locais.
Snapshot anterior: `C:/Users/alan_/AppData/Local/Temp/cpj-ag02-before-20261009/teste_fulltime.py`.

## Limites e comando para o operador

O diagnóstico completo anterior incluiu o teste legado que herdava APPDATA real.
O integrador informou que o atalho específico estava ausente na conferência
posterior; seu estado anterior é desconhecido. Não é possível atribuir criação,
remoção ou presença anterior do atalho real somente a essas evidências. Nenhuma
restauração ou instalação na Startup real foi executada nesta correção.

O teste de atalho valida criação e remoção em Startup fictícia, sem reiniciar o
Windows ou comprovar execução após login. A instalação operacional fica a cargo
do usuário. Se desejar aplicá-la, este é o comando PowerShell; não foi executado:

```powershell
& 'C:/Users/alan_/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' 'D:/CPJ - TRABALHO/ferramentas/central-daemon.py' instalar-boot --workspace 'D:/CPJ - TRABALHO'
```

Não se declara homologação geral do produto, boot instalado, CI remoto ou
inferência externa. A validação completa permanece na AG04.
