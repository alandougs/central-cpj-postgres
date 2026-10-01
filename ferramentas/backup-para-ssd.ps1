# Backup automatizado do workspace CPJ (C: -> E:)
param (
    [string]$Origem = "C:\CPJ - TRABALHO",
    [string]$Destino = "E:\CPJ - BACKUP"
)

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Central CPJ - Backup Espelho para SSD Externo" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Origem : $Origem"
Write-Host "Destino: $Destino"
Write-Host ""

if (-not (Test-Path "E:\")) {
    Write-Host "[ERRO] A unidade E:\ (SSD Externo) nao esta conectada ou acessivel." -ForegroundColor Red
    Write-Host "Conecte o SSD e tente novamente."
    exit 1
}

if (-not (Test-Path $Origem)) {
    Write-Host "[ERRO] Pasta de origem nao encontrada: $Origem" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $Destino)) {
    Write-Host "Criando pasta de backup em $Destino..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $Destino -Force | Out-Null
}

$LogDir = Join-Path $Origem "ferramentas\logs"
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir -Force | Out-Null }
$LogFile = Join-Path $LogDir ("backup-" + (Get-Date -Format "yyyy-MM-dd_HH-mm-ss") + ".log")

Write-Host "Iniciando sincronizacao espelho (Robocopy)..." -ForegroundColor Yellow
$ExcluirDirs = @(".venv", "__pycache__", "tmp", "temp", "scratch", ".system_generated", ".git")
$ExcluirFiles = @("~$*", "*.tmp", "*.pyc", ".caso.lock")

$RoboArgs = @(
    "`"$Origem`"",
    "`"$Destino`"",
    "/MIR",
    "/FFT",
    "/Z",
    "/R:2",
    "/W:2",
    "/NP",
    "/XD"
) + $ExcluirDirs + @("/XF") + $ExcluirFiles + @("/LOG:`"$LogFile`"")

$cmd = "robocopy " + ($RoboArgs -join " ")
Invoke-Expression $cmd
$ExitCode = $LASTEXITCODE

if ($ExitCode -le 7) {
    Write-Host ""
    Write-Host "[SUCESSO] Backup sincronizado com sucesso no SSD Externo (E:\CPJ - BACKUP)!" -ForegroundColor Green
    Write-Host "Log gravado em: $LogFile"
} else {
    Write-Host ""
    Write-Host "[AVISO] O Robocopy terminou com codigo $ExitCode. Verifique o log em $LogFile." -ForegroundColor Yellow
}
