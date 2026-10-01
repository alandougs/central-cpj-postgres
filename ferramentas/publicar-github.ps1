# Publica as melhorias do ambiente CPJ no GitHub (alandougs/repo-ia-alandougs).
# Uso:
#   .\publicar-github.ps1                                  -> sincroniza, varre e mostra o que mudou (NAO envia)
#   .\publicar-github.ps1 -Enviar -Mensagem "Descricao"   -> idem + commit + push
# Somente conteudo generico (plugin, estrutura, licoes genericas). Nunca envia casos, modelo DOCX,
# assinatura, indices, tessdata ou planilhas de producao. Se a varredura achar algo suspeito, PARA.
param([switch]$Enviar, [string]$Mensagem = "")
$ErrorActionPreference = 'Stop'
$W = Split-Path -Parent $PSScriptRoot
$R = Join-Path $W 'acervo\repo-ia-alandougs'
$env:PATH = [Environment]::GetEnvironmentVariable('PATH','Machine') + ';' + [Environment]::GetEnvironmentVariable('PATH','User')
if (-not (Test-Path (Join-Path $R '.git'))) { throw "Clone Git nao encontrado em $R" }

function Espelhar($origem, $destino, $extra = @()) {
    $a = @($origem, $destino, '/MIR', '/XD', '__pycache__', '/XF', '*.pyc', '*.tmp', '/NFL', '/NDL', '/NJH', '/NJS', '/NP') + $extra
    & robocopy @a | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "robocopy falhou ($LASTEXITCODE): $origem" }
}

Write-Host "1/5 Atualizando o clone local..." -ForegroundColor Cyan
git -C $R config core.autocrlf false
git -C $R pull --ff-only --quiet

Write-Host "2/5 Sincronizando plugin e estrutura do ambiente..." -ForegroundColor Cyan
Espelhar (Join-Path $W 'plugin\investigacao-cpj') (Join-Path $R 'plugins\investigacao-cpj')
$A = Join-Path $R 'ambientes\cpj-trabalho'
Espelhar (Join-Path $W 'casos\_MODELO-CASO') (Join-Path $A 'casos\_MODELO-CASO')
Espelhar (Join-Path $W 'ferramentas') (Join-Path $A 'ferramentas') @('/XD', 'tessdata')
python (Join-Path $W 'ferramentas\exportar-portatil.py') | Out-Null
Espelhar (Join-Path $W 'portatil') (Join-Path $A 'portatil')
$arquivos = 'CLAUDE.md', 'AGENTS.md', 'GEMINI.md', 'LEIA-ME.md', 'Central CPJ.bat', 'modelos\dados-padrao.json', 'producao\config.json',
            'rag\README.md', 'calibracao\licoes-aprendidas.md', 'calibracao\historico-calibracao.md'
foreach ($f in $arquivos) {
    $d = Join-Path $A $f; New-Item -ItemType Directory -Force (Split-Path $d) | Out-Null
    Copy-Item -LiteralPath (Join-Path $W $f) -Destination $d -Force
}

Write-Host "3/5 Varredura de seguranca..." -ForegroundColor Cyan
git -C $R add -A
$mudados = @(git -C $R diff --cached --name-only)
$bloqueios = @()
$proibidos = '\.(docx?|pdf|png|jpe?g|tiff?|sqlite\d?|db|traineddata|xlsx?|zip|p12|pfx|pem|key)$'
function CpfValido([string]$s) {
    $d = ($s -replace '\D', '').ToCharArray() | ForEach-Object { [int]"$_" }
    if ($d.Count -ne 11 -or ($d | Select-Object -Unique).Count -eq 1) { return $false }
    for ($j = 9; $j -le 10; $j++) { $soma = 0; for ($i = 0; $i -lt $j; $i++) { $soma += $d[$i] * ($j + 1 - $i) }
        $dv = ($soma * 10) % 11; if ($dv -eq 10) { $dv = 0 }; if ($dv -ne $d[$j]) { return $false } }
    return $true
}
foreach ($m in $mudados) {
    $p = Join-Path $R $m
    if ($m -match $proibidos) { $bloqueios += "tipo de arquivo proibido: $m"; continue }
    if ($m -match '(^|/)casos/(?!_MODELO-CASO/)') { $bloqueios += "pasta de caso real: $m"; continue }
    if (-not (Test-Path -LiteralPath $p)) { continue }
    if ((Get-Item -LiteralPath $p).Length -gt 2MB) { $bloqueios += "arquivo grande (>2 MB): $m"; continue }
    $txt = Get-Content -LiteralPath $p -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
    if (-not $txt) { continue }
    foreach ($c in [regex]::Matches($txt, '\b\d{3}\.\d{3}\.\d{3}-\d{2}\b|\b\d{11}\b')) {
        if (CpfValido $c.Value) { $bloqueios += "possivel CPF real em ${m}: $($c.Value)" }
    }
}
if ($bloqueios.Count) {
    git -C $R reset --quiet
    Write-Host "`nPUBLICACAO BLOQUEADA. Revise:" -ForegroundColor Red; $bloqueios | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
    exit 1
}

function Enviar-Pendentes {
    git -C $R fetch --quiet
    $ahead = [int](git -C $R rev-list --count '@{u}..HEAD')
    if ($ahead -eq 0) { return }
    Write-Host "Enviando $ahead commit(s) ao GitHub (pode abrir uma janela de login do GitHub)..." -ForegroundColor Cyan
    git -C $R push
    if ($LASTEXITCODE -ne 0) { Write-Host "ENVIO FALHOU. Os commits continuam salvos localmente; rode de novo apos o login no GitHub." -ForegroundColor Red; exit 2 }
    Write-Host "Publicado no GitHub." -ForegroundColor Green
}

Write-Host "4/5 Alteracoes:" -ForegroundColor Cyan
git -C $R status --short
if (-not $mudados.Count) {
    if ($Enviar) { Enviar-Pendentes } else { Write-Host "Nada a publicar." -ForegroundColor Green }
    exit 0
}

if (-not $Enviar) {
    git -C $R reset --quiet
    Write-Host "`nNada foi enviado. Para publicar: .\publicar-github.ps1 -Enviar -Mensagem ""descricao""" -ForegroundColor Yellow
    exit 0
}
Write-Host "5/5 Enviando ao GitHub..." -ForegroundColor Cyan
if (-not (git -C $R config user.name)) { git -C $R config user.name 'Alan Douglas Silva' }
if (-not (git -C $R config user.email)) { git -C $R config user.email 'alandougs@gmail.com' }
if (-not $Mensagem) { $Mensagem = "Atualiza plugin investigacao-cpj e ambiente CPJ ($(Get-Date -Format yyyy-MM-dd))" }
git -C $R commit --quiet -m $Mensagem
if ($LASTEXITCODE -ne 0) { throw "Commit falhou." }
Enviar-Pendentes
