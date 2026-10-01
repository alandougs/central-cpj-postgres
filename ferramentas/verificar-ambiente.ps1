# Checagem de saude do ambiente CPJ. Uso: .\verificar-ambiente.ps1
$W = Split-Path -Parent $PSScriptRoot
$env:PATH = [Environment]::GetEnvironmentVariable('PATH','Machine') + ';' + [Environment]::GetEnvironmentVariable('PATH','User')
$falhas = 0
function Item($nome, [scriptblock]$teste, $dica) {
    try { $r = & $teste; if ($r) { Write-Host ("[ OK ] {0} {1}" -f $nome, $r) -ForegroundColor Green; return } } catch {}
    Write-Host ("[FALHA] {0} -> {1}" -f $nome, $dica) -ForegroundColor Red; $script:falhas++
}
Item 'Python' { (python --version) 2>&1 } 'instale Python 3.12'
Item 'Bibliotecas (requirements.txt)' {
    $req = Join-Path $W 'requirements.txt'
    # nome do pacote -> modulo importavel, quando diferem
    $mapa = @{ 'pillow' = 'PIL'; 'python-docx' = 'docx'; 'pyyaml' = 'yaml' }
    $pacotes = @(Get-Content -LiteralPath $req -Encoding UTF8 | ForEach-Object { $_.Trim() } |
        Where-Object { $_ -and -not $_.StartsWith('#') -and -not $_.StartsWith('-') } |
        ForEach-Object { ($_ -split '[\[<>=!~; ]')[0].ToLower() } | Where-Object { $_ })
    $faltando = @()
    foreach ($pkg in $pacotes) {
        $mod = if ($mapa.ContainsKey($pkg)) { $mapa[$pkg] } else { $pkg.Replace('-', '_') }
        python -c "import $mod" 2>$null
        if ($LASTEXITCODE -ne 0) { $faltando += $pkg }
    }
    if ($faltando.Count -gt 0) { throw "Faltando: $($faltando -join ', ')" }
    "todas as $($pacotes.Count) instaladas"
} 'python -m pip install -r requirements.txt'
Item 'Tesseract' { foreach ($d in 'C:\Program Files\Tesseract-OCR','C:\Program Files\PDF24\tesseract') { if (Test-Path "$d\tesseract.exe") { $d; break } } } 'instale Tesseract (UB-Mannheim.TesseractOCR via winget)'
Item 'OCR portugues' { if (Test-Path (Join-Path $W 'ferramentas\tessdata\por.traineddata')) { 'ferramentas\tessdata\por.traineddata' } } 'baixe tessdata_best/por.traineddata para ferramentas\tessdata'
Item 'Modelo DOCX' { $m = Get-ChildItem (Join-Path $W 'modelos\*.docx') -ErrorAction Stop | Select-Object -First 1; if ($m) { $m.Name } } 'coloque o modelo do relatorio em modelos\'
Item 'Delegado padrao' { $d = (Get-Content (Join-Path $W 'modelos\dados-padrao.json') -Raw -Encoding UTF8 | ConvertFrom-Json).delegado_padrao; if ($d) { $d } } 'preencha delegado_padrao em modelos\dados-padrao.json'
Item 'Git' { (git --version) } 'winget install Git.Git'
Item 'Plugin' {
    $cli = $null
    if ($env:APPDATA) {
        $base = Join-Path $env:APPDATA 'Claude\claude-code'
        if (Test-Path -LiteralPath $base -PathType Container) {
            $versoes = @(Get-ChildItem -LiteralPath $base -Directory -ErrorAction SilentlyContinue |
                Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName 'claude.exe') } |
                Sort-Object { try { [version]$_.Name } catch { [version]'0.0' } })
            if ($versoes.Count) { $cli = Join-Path $versoes[-1].FullName 'claude.exe' }
        }
        if (-not $cli) {
            $npm = Join-Path $env:APPDATA 'npm\node_modules\@anthropic-ai\claude-code\bin\claude.exe'
            if (Test-Path -LiteralPath $npm -PathType Leaf) { $cli = $npm }
        }
    }
    if (-not $cli) {
        $comando = Get-Command claude.exe -CommandType Application -ErrorAction SilentlyContinue
        if ($comando) { $cli = $comando.Source }
    }
    if (-not $cli) { return }
    $l = & $cli plugin list 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) { return }
    if ($l -match 'investigacao-cpj@cpj-local[\s\S]*?Version:\s*([\d.]+)') { "investigacao-cpj $($Matches[1])" }
} 'rode ferramentas\atualizar-plugin.ps1 -SemVersao'
Item 'Central CPJ' { try { $null = Invoke-WebRequest 'http://127.0.0.1:8765/api/fila' -UseBasicParsing -TimeoutSec 3; 'em execucao (http://127.0.0.1:8765)' } catch { 'parada (abra pelo atalho Central CPJ)' } } ''
$n = @(Get-ChildItem (Join-Path $W 'casos') -Directory | Where-Object { $_.Name -notlike '_*' }).Count
Write-Host "Casos no workspace: $n"
if ($falhas) { Write-Host "$falhas item(ns) com falha." -ForegroundColor Yellow } else { Write-Host "Ambiente OK." -ForegroundColor Green }
