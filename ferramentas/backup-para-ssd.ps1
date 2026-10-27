# Copia offline versionada. Origem deriva desta instalacao (nao fixa C:).
param(
    [string]$Origem = (Split-Path -Parent $PSScriptRoot),
    [Parameter(Mandatory = $true)][string]$Destino,
    [switch]$Offline,
    [switch]$MidiaProtegida
)
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'backup.ps1') -Origem $Origem -Destino $Destino -Offline:$Offline -MidiaProtegida:$MidiaProtegida
