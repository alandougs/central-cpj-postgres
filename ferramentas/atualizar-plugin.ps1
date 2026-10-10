# Aplica no Claude Code as alteracoes feitas em plugin\investigacao-cpj.
# Uso: .\atualizar-plugin.ps1            -> sobe a versao (patch), valida e reinstala
#      .\atualizar-plugin.ps1 -SemVersao -> so valida e reinstala
# Depois, abra uma sessao nova do Claude Code para carregar a versao nova.
param([switch]$SemVersao)
$ErrorActionPreference = 'Stop'
$W = Split-Path -Parent $PSScriptRoot
$python = $null
$pythonVenv = Join-Path $W '.venv\Scripts\python.exe'
if (Test-Path -LiteralPath $pythonVenv -PathType Leaf) {
    & $pythonVenv --version *> $null
    if ($LASTEXITCODE -eq 0) { $python = $pythonVenv }
}
if (-not $python) {
    $pythonPath = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonPath) {
        & $pythonPath --version *> $null
        if ($LASTEXITCODE -eq 0) { $python = $pythonPath }
    }
}
if (-not $python) {
    throw 'Python indisponivel: repare .venv\Scripts\python.exe ou disponibilize Python valido no PATH antes de atualizar.'
}
$noPath = Get-Command claude.exe -ErrorAction SilentlyContinue
$claude = if ($noPath) { Get-Item -LiteralPath $noPath.Source } else { $null }
if (-not $claude) {
    $claude = Get-ChildItem "$env:APPDATA\Claude\claude-code\*\claude.exe" -ErrorAction SilentlyContinue | Sort-Object { [version]$_.Directory.Name } | Select-Object -Last 1
}
if (-not $claude) {
    $npm = Join-Path $env:APPDATA 'npm\node_modules\@anthropic-ai\claude-code\bin\claude.exe'
    if (Test-Path -LiteralPath $npm) { $claude = Get-Item -LiteralPath $npm }
}
if (-not $claude) {
    $claude = Get-ChildItem "$env:USERPROFILE\.vscode\extensions\anthropic.claude-code-*-win32-*\resources\native-binary\claude.exe" -ErrorAction SilentlyContinue | Sort-Object { [version](($_.FullName -replace '^.*anthropic\.claude-code-(\d+(\.\d+)*)-win32.*$', '$1')) } | Select-Object -Last 1
}
if (-not $claude) {
    $noPath = Get-Command claude.exe -ErrorAction SilentlyContinue
    if ($noPath) { $claude = Get-Item -LiteralPath $noPath.Source }
}
if (-not $claude) { throw "claude.exe nao encontrado em $env:APPDATA\Claude\claude-code, na instalacao npm nem no PATH" }
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
foreach ($alvo in @((Join-Path $W 'plugin'), (Join-Path $W 'plugin\investigacao-cpj'))) {
    & $claude.FullName plugin validate $alvo
    if ($LASTEXITCODE) { throw "Validacao falhou - corrija antes de instalar." }
}
$origemPlugin = Join-Path $W 'plugin'
$pluginLocal = [IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA 'CPJ\plugin'))
if (-not $pluginLocal.StartsWith('C:\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'O destino local do plugin deve estar na unidade C:.'
}
if (Test-Path -LiteralPath $pluginLocal) {
    if ((Get-Item -LiteralPath $pluginLocal).Attributes -band [IO.FileAttributes]::ReparsePoint) {
        throw 'Destino do plugin e um link; instalacao interrompida.'
    }
}
# Copia apenas o pacote generico: nunca fixtures, caches ou dados locais.
$arquivosPlugin = @(Get-Item -LiteralPath $mj) + @(Get-ChildItem -LiteralPath (Join-Path $origemPlugin 'investigacao-cpj') -File -Recurse -Force |
    Where-Object { $_.FullName -notmatch '[\\/](testes|__pycache__|casos|config|00-originais)[\\/]' })
$relativos = @{}
foreach ($arquivo in $arquivosPlugin) {
    if ($arquivo.Extension -notin @('.py', '.md', '.json', '.html', '.png') -or
        ($arquivo.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw "Arquivo fora do pacote generico: $($arquivo.Name)"
    }
    $relativo = $arquivo.FullName.Substring($origemPlugin.Length + 1)
    $relativos[$relativo] = $arquivo
}
if (Test-Path -LiteralPath $pluginLocal) {
    if (@(Get-ChildItem -LiteralPath $pluginLocal -Recurse -Force |
        Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint }).Count) {
        throw 'Destino contem links; instalacao interrompida.'
    }
    foreach ($existente in @(Get-ChildItem -LiteralPath $pluginLocal -File -Recurse -Force)) {
        $relativo = $existente.FullName.Substring($pluginLocal.Length + 1)
        if (-not $relativos.ContainsKey($relativo)) {
            throw "Destino contem arquivo nao previsto; preserve e confira antes de atualizar: $relativo"
        }
    }
}
foreach ($relativo in $relativos.Keys) {
    $destino = Join-Path $pluginLocal $relativo
    New-Item -ItemType Directory -Path (Split-Path -Parent $destino) -Force | Out-Null
    Copy-Item -LiteralPath $relativos[$relativo].FullName -Destination $destino
    if ((Get-FileHash -LiteralPath $destino -Algorithm SHA256).Hash -ne
        (Get-FileHash -LiteralPath $relativos[$relativo].FullName -Algorithm SHA256).Hash) {
        throw "Copia do plugin divergente: $relativo"
    }
}
Write-Host "Pacote generico conferido: $($relativos.Count) arquivos -> $pluginLocal"
$marketplacesJson = (& $claude.FullName plugin marketplace list --json | Out-String)
if ($LASTEXITCODE) { throw "Nao foi possivel listar marketplaces." }
$marketplaces = $marketplacesJson | ConvertFrom-Json
if (@($marketplaces | Where-Object { $_.name -eq 'cpj-local' }).Count) {
    if (@($marketplaces | Where-Object { $_.name -eq 'cpj-local' -and $_.path -ne $pluginLocal }).Count) {
        throw 'cpj-local ja aponta para outro destino; preserve e confira antes de atualizar.'
    }
    & $claude.FullName plugin marketplace update cpj-local
} else {
    & $claude.FullName plugin marketplace add $pluginLocal
}
if ($LASTEXITCODE) { throw "Nao foi possivel registrar/atualizar cpj-local." }
$pluginsJson = (& $claude.FullName plugin list --json | Out-String)
if ($LASTEXITCODE) { throw "Nao foi possivel listar plugins." }
$plugins = $pluginsJson | ConvertFrom-Json
if (@($plugins | Where-Object { $_.id -eq 'investigacao-cpj@cpj-local' }).Count) {
    & $claude.FullName plugin update investigacao-cpj@cpj-local
} else {
    & $claude.FullName plugin install investigacao-cpj@cpj-local
}
if ($LASTEXITCODE) { throw "Nao foi possivel instalar/atualizar investigacao-cpj." }
$confirmacaoJson = (& $claude.FullName plugin list --json | Out-String)
if ($LASTEXITCODE) { throw "Nao foi possivel conferir a instalacao." }
$instalados = @($confirmacaoJson | ConvertFrom-Json | Where-Object { $_.id -eq 'investigacao-cpj@cpj-local' })
if (-not @($instalados | Where-Object { $_.version -eq (Get-Content -LiteralPath $pj -Raw -Encoding UTF8 | ConvertFrom-Json).version }).Count) {
    throw "A versao instalada diverge do manifesto; atualizacao nao concluida."
}
& $python (Join-Path $PSScriptRoot 'exportar-portatil.py')
if ($LASTEXITCODE) { throw "Falha ao regenerar os procedimentos portateis." }
Write-Host "Pronto. Abra uma sessao nova do Claude Code para usar a versao atualizada." -ForegroundColor Green
