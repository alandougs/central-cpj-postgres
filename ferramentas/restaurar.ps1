# Restaura copia de seguranca do ambiente CPJ (casos, calibracao, producao, modelos, consulta, referencias, config, usuarios).
# Uso: .\restaurar.ps1 -Origem "E:\Backup\CPJ-TRABALHO-backup"
# Copia arquivos do backup para a pasta de trabalho; NUNCA apaga nada no destino.
param([Parameter(Mandatory = $true)][string]$Origem)
$ErrorActionPreference = 'Stop'
$W = Split-Path -Parent $PSScriptRoot

if (-not (Test-Path -LiteralPath $Origem)) { throw "Origem nao existe: $Origem" }

$log = Join-Path $W ("producao\restauracao-{0}.log" -f (Get-Date -Format 'yyyyMMdd-HHmm'))

Write-Host "Iniciando restauracao de $Origem para $W" -ForegroundColor Cyan

foreach ($p in 'casos', 'calibracao', 'producao', 'modelos', 'consulta', 'referencias', 'config', 'usuarios') {
    $pastaOrigem = Join-Path $Origem $p
    if (Test-Path -LiteralPath $pastaOrigem) {
        Write-Host "Restaurando $p..."
        & robocopy $pastaOrigem (Join-Path $W $p) /E /R:1 /W:1 /XD __pycache__ /NP /NDL /NFL "/LOG+:$log" | Out-Null
        if ($LASTEXITCODE -ge 8) { throw "Falha ao restaurar $p (codigo $LASTEXITCODE). Veja $log" }
    } else {
        Write-Host "Ignorando $p (nao encontrado no backup)" -ForegroundColor Yellow
    }
}
Write-Host "Restauracao concluida em $W  (log: $log)" -ForegroundColor Green
