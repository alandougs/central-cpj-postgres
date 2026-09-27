# Aplica no Claude Code as alteracoes feitas em plugin\investigacao-cpj.
# Uso: .\atualizar-plugin.ps1            -> sobe a versao (patch), valida e reinstala
#      .\atualizar-plugin.ps1 -SemVersao -> so valida e reinstala
# Depois, abra uma sessao nova do Claude Code para carregar a versao nova.
param([switch]$SemVersao)
$ErrorActionPreference = 'Stop'
$W = Split-Path -Parent $PSScriptRoot
$claude = Get-ChildItem "$env:APPDATA\Claude\claude-code\*\claude.exe" | Sort-Object { [version]$_.Directory.Name } | Select-Object -Last 1
if (-not $claude) { throw "claude.exe nao encontrado em $env:APPDATA\Claude\claude-code" }
$pj = Join-Path $W 'plugin\investigacao-cpj\.claude-plugin\plugin.json'
$mj = Join-Path $W 'plugin\.claude-plugin\marketplace.json'
$atual = (Get-Content -LiteralPath $pj -Raw -Encoding UTF8 | ConvertFrom-Json).version
if (-not $SemVersao) {
    $v = [version]$atual; $nova = "$($v.Major).$($v.Minor).$($v.Build + 1)"
    foreach ($f in $pj, $mj) {
        $t = [IO.File]::ReadAllText($f).Replace("""version"": ""$atual""", """version"": ""$nova""")
        [IO.File]::WriteAllText($f, $t, (New-Object Text.UTF8Encoding $false))
    }
    Write-Host "Versao $atual -> $nova"
}
& $claude.FullName plugin validate (Join-Path $W 'plugin')
if ($LASTEXITCODE) { throw "Validacao falhou - corrija antes de instalar." }
& $claude.FullName plugin marketplace update cpj-local
& $claude.FullName plugin update investigacao-cpj@cpj-local
python (Join-Path $PSScriptRoot 'exportar-portatil.py')
Write-Host "Pronto. Abra uma sessao nova do Claude Code para usar a versao atualizada." -ForegroundColor Green
