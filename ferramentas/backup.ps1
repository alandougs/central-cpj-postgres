# Copia de seguranca do ambiente CPJ (casos, calibracao, producao, modelos).
# Uso: .\backup.ps1 -Destino "E:\Backup"      (HD externo / pasta autorizada pelo orgao)
# Copia apenas arquivos novos ou alterados; NUNCA apaga nada no destino.
# Atencao: contem dados sigilosos de inqueritos - use somente midia/pasta autorizada e protegida.
param([Parameter(Mandatory = $true)][string]$Destino)
$ErrorActionPreference = 'Stop'
$W = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path -LiteralPath $Destino)) { throw "Destino nao existe: $Destino" }
$alvo = Join-Path $Destino 'CPJ-TRABALHO-backup'
$log = Join-Path $W ("producao\backup-{0}.log" -f (Get-Date -Format 'yyyyMMdd-HHmm'))
foreach ($p in 'casos', 'calibracao', 'producao', 'modelos', 'consulta', 'referencias', 'config', 'usuarios') {
    Write-Host "Copiando $p..."
    & robocopy (Join-Path $W $p) (Join-Path $alvo $p) /E /XO /R:1 /W:1 /XD __pycache__ /NP /NDL /NFL "/LOG+:$log" | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "Falha ao copiar $p (codigo $LASTEXITCODE). Veja $log" }
}
Write-Host "Backup concluido em $alvo  (log: $log)" -ForegroundColor Green
