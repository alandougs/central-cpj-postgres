# Checagem de saude do ambiente CPJ. Uso: .\verificar-ambiente.ps1
$W = Split-Path -Parent $PSScriptRoot
$env:PATH = [Environment]::GetEnvironmentVariable('PATH','Machine') + ';' + [Environment]::GetEnvironmentVariable('PATH','User')
$falhas = 0
function Item($nome, [scriptblock]$teste, $dica) {
    try { $r = & $teste; if ($r) { Write-Host ("[ OK ] {0} {1}" -f $nome, $r) -ForegroundColor Green; return } } catch {}
    Write-Host ("[FALHA] {0} -> {1}" -f $nome, $dica) -ForegroundColor Red; $script:falhas++
}
Item 'Python' { (python --version) 2>&1 } 'instale Python 3.12'
Item 'Bibliotecas' { python -c "import pypdf, pypdfium2, pdfplumber, pytesseract, PIL, docx, flask; print('pypdf pypdfium2 pdfplumber pytesseract pillow python-docx flask')" } 'python -m pip install pypdf pypdfium2 pdfplumber pytesseract pillow python-docx flask'
Item 'Tesseract' { if (Test-Path 'C:\Program Files\Tesseract-OCR\tesseract.exe') { 'C:\Program Files\Tesseract-OCR' } } 'instale Tesseract (UB-Mannheim.TesseractOCR via winget)'
Item 'OCR portugues' { if (Test-Path (Join-Path $W 'ferramentas\tessdata\por.traineddata')) { 'ferramentas\tessdata\por.traineddata' } } 'baixe tessdata_best/por.traineddata para ferramentas\tessdata'
Item 'Modelo DOCX' { $m = Get-ChildItem (Join-Path $W 'modelos\*.docx') -ErrorAction Stop | Select-Object -First 1; if ($m) { $m.Name } } 'coloque o modelo do relatorio em modelos\'
Item 'Delegado padrao' { $d = (Get-Content (Join-Path $W 'modelos\dados-padrao.json') -Raw -Encoding UTF8 | ConvertFrom-Json).delegado_padrao; if ($d) { $d } } 'preencha delegado_padrao em modelos\dados-padrao.json'
Item 'Git' { (git --version) } 'winget install Git.Git'
Item 'Plugin' { $c = Get-ChildItem "$env:APPDATA\Claude\claude-code\*\claude.exe" | Sort-Object { [version]$_.Directory.Name } | Select-Object -Last 1; $l = & $c.FullName plugin list 2>&1 | Out-String; if ($l -match 'investigacao-cpj@cpj-local[\s\S]*?Version:\s*([\d.]+)') { "investigacao-cpj $($Matches[1])" } } 'rode ferramentas\atualizar-plugin.ps1 -SemVersao'
Item 'Central CPJ' { try { $null = Invoke-WebRequest 'http://127.0.0.1:8765/api/fila' -UseBasicParsing -TimeoutSec 3; 'em execucao (http://127.0.0.1:8765)' } catch { 'parada (abra pelo atalho Central CPJ)' } } ''
$n = @(Get-ChildItem (Join-Path $W 'casos') -Directory | Where-Object { $_.Name -notlike '_*' }).Count
Write-Host "Casos no workspace: $n"
if ($falhas) { Write-Host "$falhas item(ns) com falha." -ForegroundColor Yellow } else { Write-Host "Ambiente OK." -ForegroundColor Green }
