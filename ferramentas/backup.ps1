# Pare Central, agentes e editores antes de -Offline. Snapshot versionado,
# sem espelhamento/exclusao. Midia autorizada e protegida/cifrada pelo orgao.
# Restore somente em pasta nova: python backup_consistente.py restaurar --help
param(
    [Parameter(Mandatory = $true)][string]$Destino,
    [string]$Origem = (Split-Path -Parent $PSScriptRoot),
    [switch]$Offline,
    [switch]$MidiaProtegida,
    [string]$Python = (Join-Path $PSScriptRoot '..\.venv\Scripts\python.exe')
)
$ErrorActionPreference = 'Stop'
if (-not $Offline -or -not $MidiaProtegida) {
    throw 'Pare todos os escritores e confirme -Offline -MidiaProtegida. Use somente midia autorizada e cifrada/protegida.'
}
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) { throw 'Interpretador Python nao encontrado; indique -Python com o caminho do executavel instalado.' }
$interprete = (Get-Item -LiteralPath $Python).FullName
& $interprete (Join-Path $PSScriptRoot 'backup_consistente.py') criar --origem $Origem --destino $Destino --offline --midia-protegida
if ($LASTEXITCODE -ne 0) { throw 'Backup abortado; nenhum snapshot completo publicado. Confira o erro acima.' }
