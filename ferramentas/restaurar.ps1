# Restaura snapshot versionado e verificado somente em pasta NOVA.
# Uso: .\restaurar.ps1 -Origem 'E:\Backup\CPJ-...' -Destino 'D:\CPJ recuperado' -MidiaProtegida
# Nao substitui workspace existente. Midia autorizada e cifrada/protegida pelo orgao.
# Segredos DPAPI exigem a mesma conta/maquina Windows; nao reiniciar auditoria.
param(
    [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$Origem,
    [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$Destino,
    [switch]$MidiaProtegida,
    [string]$Python = (Join-Path $PSScriptRoot '..\.venv\Scripts\python.exe')
)
$ErrorActionPreference = 'Stop'
if (-not $MidiaProtegida) { throw 'Confirme -MidiaProtegida: restaurar apenas em midia autorizada e cifrada/protegida.' }
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) { throw 'Interpretador Python nao encontrado; indique -Python com o caminho do executavel instalado.' }
$interprete = (Get-Item -LiteralPath $Python).FullName
& $interprete (Join-Path $PSScriptRoot 'backup_consistente.py') restaurar --snapshot $Origem --destino $Destino --midia-protegida
if ($LASTEXITCODE -ne 0) { throw 'Restauracao recusada ou interrompida. Confira o erro acima; nenhum workspace existente foi substituido.' }
