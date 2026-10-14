$ErrorActionPreference = 'Stop'
$processIdsAstra = [Console]::In.ReadToEnd() | ConvertFrom-Json
$rowsAstra = foreach ($processIdAstra in $processIdsAstra) {
    if ($processIdAstra -isnot [long] -and $processIdAstra -isnot [int]) { throw 'PID must be an integer.' }
    if ($processIdAstra -le 0) { throw 'PID must be positive.' }
    try {
        $processAstra = Get-Process -Id $processIdAstra -ErrorAction Stop
        [pscustomobject]@{ pid = $processIdAstra; workingSetBytes = [long]$processAstra.WorkingSet64; processName = $processAstra.ProcessName; error = $null }
    } catch {
        [pscustomobject]@{ pid = $processIdAstra; workingSetBytes = $null; processName = $null; error = $_.Exception.Message }
    }
}
ConvertTo-Json -InputObject @($rowsAstra) -Depth 4 -Compress
