param(
    [Parameter(Position = 0)]
    [ValidateSet('', 'mount', 'dismount')]
    [string]$Action = '',
    [string]$Root = $env:RUNNER_TEMP
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$script:CI27_SCHEMA = 'cpj-ci27-exfat-owner/1'
$script:CI27_FOLDER = '.ci-sec22-exfat'

function Assert-CI27Runner {
    if ($env:GITHUB_ACTIONS -ne 'true') {
        throw 'Recusa absoluta: helper exclusivo do GitHub Actions (GITHUB_ACTIONS != true).'
    }
    if ($env:RUNNER_OS -ne 'Windows') {
        throw 'Recusa absoluta: helper exclusivo de runner Windows (RUNNER_OS != Windows).'
    }
    if ($env:RUNNER_ENVIRONMENT -ne 'github-hosted') {
        throw 'Recusa absoluta: helper restrito a runner github-hosted.'
    }
    if ($env:CPJ_CI_EXFAT_ENABLE -ne '1') {
        throw 'Recusa absoluta: CPJ_CI_EXFAT_ENABLE=1 obrigatorio.'
    }
    if ([string]::IsNullOrWhiteSpace($env:GITHUB_RUN_ID) -or $env:GITHUB_RUN_ID -notmatch '^\d+$') {
        throw 'Recusa absoluta: GITHUB_RUN_ID invalido.'
    }
    if ([string]::IsNullOrWhiteSpace($env:GITHUB_RUN_ATTEMPT) -or $env:GITHUB_RUN_ATTEMPT -notmatch '^\d+$') {
        throw 'Recusa absoluta: GITHUB_RUN_ATTEMPT invalido.'
    }
    if ([string]::IsNullOrWhiteSpace($env:GITHUB_WORKSPACE) -or -not [IO.Directory]::Exists($env:GITHUB_WORKSPACE)) {
        throw 'Recusa absoluta: GITHUB_WORKSPACE ausente ou inexistente.'
    }
}

function Assert-CI27Child {
    param(
        [Parameter(Mandatory = $true)][string]$Raiz,
        [Parameter(Mandatory = $true)][string]$Caminho,
        [switch]$AllowReparseTarget
    )
    if ([string]::IsNullOrWhiteSpace($Raiz) -or [string]::IsNullOrWhiteSpace($Caminho)) {
        throw 'Caminho vazio recusado.'
    }
    $raizFull = [IO.Path]::GetFullPath($Raiz).TrimEnd('\', '/')
    $caminhoFull = [IO.Path]::GetFullPath($Caminho).TrimEnd('\', '/')
    $rootDrive = [IO.Path]::GetPathRoot($raizFull).TrimEnd('\', '/')
    if ([string]::IsNullOrWhiteSpace($rootDrive) -or $raizFull.Equals($rootDrive, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Raiz invalida (nao pode ser raiz de volume): '$raizFull'"
    }
    $prefixo = $raizFull + '\'
    if (-not $caminhoFull.StartsWith($prefixo, [StringComparison]::OrdinalIgnoreCase) -or $caminhoFull.Length -le $prefixo.Length) {
        throw "Caminho '$caminhoFull' fora da raiz autorizada '$raizFull'."
    }
    if (Test-Path -LiteralPath $raizFull) {
        $itemRaiz = Get-Item -LiteralPath $raizFull -Force -ErrorAction Stop
        if ($itemRaiz.Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw "Raiz contem reparse point: '$raizFull'"
        }
    }
    $rel = $caminhoFull.Substring($prefixo.Length)
    $partes = $rel -split '[\\/]'
    $atual = $raizFull
    for ($i = 0; $i -lt $partes.Count; $i++) {
        $atual = Join-Path $atual $partes[$i]
        if (Test-Path -LiteralPath $atual) {
            $item = Get-Item -LiteralPath $atual -Force -ErrorAction Stop
            $ehUltimo = ($i -eq ($partes.Count - 1))
            if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -and -not ($AllowReparseTarget -and $ehUltimo)) {
                throw "Caminho contem reparse point nao autorizado: '$atual'"
            }
        }
    }
}

function Assert-CI27New {
    param(
        [Parameter(Mandatory = $true)][string]$Caminho
    )
    if ([string]::IsNullOrWhiteSpace($Caminho)) {
        throw 'Caminho vazio recusado.'
    }
    $full = [IO.Path]::GetFullPath($Caminho)
    if ([IO.File]::Exists($full) -or [IO.Directory]::Exists($full) -or (Test-Path -LiteralPath $full)) {
        throw "Alvo ja existe e nao pode ser reutilizado: '$full'"
    }
}

function Assert-CI27Disk {
    param(
        [Parameter(Mandatory = $true)]$Img,
        [Parameter(Mandatory = $true)]$Disk,
        [Parameter(Mandatory = $true)][string]$ExpectedImagePath,
        [switch]$Raw
    )
    if ($null -eq $Img -or $null -eq $Disk) {
        throw 'Objeto DiskImage ou Disk ausente.'
    }
    if ($Img.Attached -ne $true) {
        throw 'Imagem VHD nao esta anexada.'
    }
    $esperado = [IO.Path]::GetFullPath($ExpectedImagePath)
    $atual = [IO.Path]::GetFullPath([string]$Img.ImagePath)
    if (-not $atual.Equals($esperado, [StringComparison]::OrdinalIgnoreCase)) {
        throw "ImagePath divergente: '$atual' != '$esperado'"
    }
    if (-not ($atual.EndsWith('.vhd', [StringComparison]::OrdinalIgnoreCase) -or $atual.EndsWith('.vhdx', [StringComparison]::OrdinalIgnoreCase))) {
        throw "Extensao de imagem invalida: '$atual'"
    }
    if ($null -eq $Img.Number -or $null -eq $Disk.Number -or ([int]$Img.Number -ne [int]$Disk.Number) -or ([int]$Disk.Number -lt 0)) {
        throw "Numero de disco divergente entre DiskImage ($($Img.Number)) e Disk ($($Disk.Number))."
    }
    if ($Disk.IsBoot -ne $false) {
        throw 'Recusa absoluta: disco marcado como IsBoot.'
    }
    if ($Disk.IsSystem -ne $false) {
        throw 'Recusa absoluta: disco marcado como IsSystem.'
    }
    if ([string]$Disk.BusType -ne 'File Backed Virtual') {
        throw "Recusa absoluta: BusType inesperado '$($Disk.BusType)'."
    }
    if ($Raw) {
        if ([string]$Disk.PartitionStyle -ne 'RAW') {
            throw "Disco nao esta RAW: '$($Disk.PartitionStyle)'."
        }
        if ([int]$Disk.NumberOfPartitions -ne 0) {
            throw "Disco RAW nao pode conter particoes: $($Disk.NumberOfPartitions)."
        }
    }
}

function Get-CI27OwnedFixture {
    param(
        [Parameter(Mandatory = $true)][string]$Raiz
    )
    Assert-CI27Runner
    $raizFull = [IO.Path]::GetFullPath($Raiz).TrimEnd('\', '/')
    $base = Join-Path $raizFull $script:CI27_FOLDER
    Assert-CI27Child $raizFull $base
    if (-not [IO.Directory]::Exists($base)) {
        throw "Diretorio da fixture CI27 inexistente: '$base'"
    }
    $marker = Join-Path $base 'owner.json'
    Assert-CI27Child $base $marker
    if (-not [IO.File]::Exists($marker)) {
        throw "Marcador de propriedade ausente: '$marker'"
    }
    $dados = Get-Content -LiteralPath $marker -Raw -Encoding UTF8 | ConvertFrom-Json -ErrorAction Stop
    if ($null -eq $dados -or [string]$dados.schema -ne $script:CI27_SCHEMA) {
        throw 'Schema do marcador owner.json invalido.'
    }
    if ([string]$dados.run_id -ne [string]$env:GITHUB_RUN_ID -or [string]$dados.run_attempt -ne [string]$env:GITHUB_RUN_ATTEMPT) {
        throw 'Marcador owner.json pertence a outra execucao do runner.'
    }
    $baseOwner = [IO.Path]::GetFullPath([string]$dados.base_dir).TrimEnd('\', '/')
    if (-not $baseOwner.Equals($base, [StringComparison]::OrdinalIgnoreCase)) {
        throw "base_dir divergente no owner.json: '$baseOwner'"
    }
    $vhd = [IO.Path]::GetFullPath([string]$dados.image_path)
    $mount = [IO.Path]::GetFullPath([string]$dados.mount_dir)
    $profile = [IO.Path]::GetFullPath([string]$dados.profile_dir)
    Assert-CI27Child $base $vhd
    Assert-CI27Child $base $mount -AllowReparseTarget
    Assert-CI27Child $base $profile
    if (-not $vhd.EndsWith('.vhd', [StringComparison]::OrdinalIgnoreCase)) {
        throw "image_path invalido no owner.json: '$vhd'"
    }
    return [pscustomobject]@{
        schema      = [string]$dados.schema
        run_id      = [string]$dados.run_id
        run_attempt = [string]$dados.run_attempt
        base_dir    = $base
        image_path  = $vhd
        mount_dir   = $mount
        profile_dir = $profile
        marker_path = $marker
    }
}

function Mount-CI27Volume {
    param(
        [Parameter(Mandatory = $true)][string]$Raiz
    )
    Assert-CI27Runner
    if ([string]::IsNullOrWhiteSpace($Raiz) -or -not [IO.Directory]::Exists($Raiz)) {
        throw "RUNNER_TEMP invalido ou inexistente: '$Raiz'"
    }
    $raizFull = [IO.Path]::GetFullPath($Raiz).TrimEnd('\', '/')
    $base = Join-Path $raizFull $script:CI27_FOLDER
    Assert-CI27Child $raizFull $base
    Assert-CI27New $base

    $vhd = Join-Path $base 'sec22-exfat.vhd'
    $mount = Join-Path $base 'mnt'
    $profile = Join-Path $base 'perfil-ntfs'
    $marker = Join-Path $base 'owner.json'

    New-Item -ItemType Directory -Path $base -ErrorAction Stop | Out-Null
    Assert-CI27Child $base $vhd
    Assert-CI27New $vhd
    Assert-CI27Child $base $mount
    Assert-CI27New $mount
    Assert-CI27Child $base $profile
    Assert-CI27New $profile
    Assert-CI27Child $base $marker
    Assert-CI27New $marker

    New-Item -ItemType Directory -Path $mount -ErrorAction Stop | Out-Null
    New-Item -ItemType Directory -Path $profile -ErrorAction Stop | Out-Null

    $ownerJson = [ordered]@{
        schema      = $script:CI27_SCHEMA
        run_id      = [string]$env:GITHUB_RUN_ID
        run_attempt = [string]$env:GITHUB_RUN_ATTEMPT
        base_dir    = $base
        image_path  = $vhd
        mount_dir   = $mount
        profile_dir = $profile
    } | ConvertTo-Json -Compress
    [IO.File]::WriteAllText($marker, $ownerJson, [Text.UTF8Encoding]::new($false))
    [void](Get-CI27OwnedFixture $raizFull)

    $dpScript = Join-Path $base 'create-vhd.txt'
    Assert-CI27Child $base $dpScript
    Assert-CI27New $dpScript
    [IO.File]::WriteAllText($dpScript, "create vdisk file=`"$vhd`" maximum=256 type=expandable`r`nexit`r`n", [Text.Encoding]::ASCII)
    $dpOut = & diskpart.exe /s $dpScript 2>&1
    $dpExit = $LASTEXITCODE
    Remove-Item -LiteralPath $dpScript -Force -ErrorAction SilentlyContinue
    if ($dpExit -ne 0 -or -not [IO.File]::Exists($vhd)) {
        throw "Falha ao criar imagem VHD descartavel (exit $dpExit): $($dpOut -join ' ')"
    }

    $preImg = Get-DiskImage -ImagePath $vhd -ErrorAction Stop
    if ($preImg.Attached) {
        throw 'VHD recem-criado ja consta anexado.'
    }

    Mount-DiskImage -ImagePath $vhd -NoDriveLetter -PassThru -ErrorAction Stop | Out-Null
    $img = Get-DiskImage -ImagePath $vhd -ErrorAction Stop
    if ($null -eq $img -or -not $img.Attached -or $null -eq $img.Number) {
        throw 'Mount-DiskImage nao anexou o VHD descartavel.'
    }
    $disk = Get-Disk -Number ([uint32]$img.Number) -ErrorAction Stop
    Assert-CI27Disk $img $disk $vhd -Raw

    Initialize-Disk -InputObject $disk -PartitionStyle GPT -PassThru -ErrorAction Stop | Out-Null
    $part = New-Partition -DiskNumber ([uint32]$disk.Number) -UseMaximumSize -ErrorAction Stop
    $vol = Format-Volume -Partition $part -FileSystem exFAT -NewFileSystemLabel 'CPJCI27' -Confirm:$false -Force -ErrorAction Stop
    if ($null -eq $vol -or [string]$vol.FileSystem -ne 'exFAT') {
        throw "Volume formatado nao e exFAT: '$($vol.FileSystem)'"
    }
    $accessPath = $mount.TrimEnd('\', '/') + '\'
    Add-PartitionAccessPath -DiskNumber ([uint32]$disk.Number) -PartitionNumber ([uint32]$part.PartitionNumber) -AccessPath $accessPath -ErrorAction Stop

    $work = Join-Path $mount 'sec22-work'
    New-Item -ItemType Directory -Path $work -ErrorAction Stop | Out-Null

    if ($env:GITHUB_ENV) {
        Add-Content -LiteralPath $env:GITHUB_ENV -Value "CPJ_SEC22_EXIGIR_VOLUME_SEM_ACL=1"
        Add-Content -LiteralPath $env:GITHUB_ENV -Value "CPJ_SEC22_VOLUME_SEM_ACL_DIR=$work"
        Add-Content -LiteralPath $env:GITHUB_ENV -Value "CPJ_SEC22_PERFIL_NTFS_DIR=$profile"
        Add-Content -LiteralPath $env:GITHUB_ENV -Value "CPJ_SEC22_REQUIRE_VOLUME=1"
        Add-Content -LiteralPath $env:GITHUB_ENV -Value "CPJ_SEC22_VOLUME_DIR=$work"
        Add-Content -LiteralPath $env:GITHUB_ENV -Value "CPJ_SEC22_PROFILE_DIR=$profile"
    }
    Write-Output "CI27 exFAT montado em $work (perfil NTFS em $profile)"
}

function Dismount-CI27Volume {
    param(
        [Parameter(Mandatory = $true)][string]$Raiz
    )
    Assert-CI27Runner
    if ([string]::IsNullOrWhiteSpace($Raiz) -or -not [IO.Directory]::Exists($Raiz)) {
        return
    }
    $raizFull = [IO.Path]::GetFullPath($Raiz).TrimEnd('\', '/')
    $base = Join-Path $raizFull $script:CI27_FOLDER
    Assert-CI27Child $raizFull $base
    if (-not (Test-Path -LiteralPath $base)) {
        return
    }
    $owned = Get-CI27OwnedFixture $raizFull
    $vhd = $owned.image_path
    $mount = $owned.mount_dir
    if ([IO.File]::Exists($vhd)) {
        $img = Get-DiskImage -ImagePath $vhd -ErrorAction SilentlyContinue
        if ($null -ne $img -and $img.Attached) {
            if ($null -ne $img.Number) {
                $disk = Get-Disk -Number ([uint32]$img.Number) -ErrorAction Stop
                Assert-CI27Disk $img $disk $vhd
                $accessPath = $mount.TrimEnd('\', '/') + '\'
                Get-Partition -DiskNumber ([uint32]$disk.Number) -ErrorAction SilentlyContinue | ForEach-Object {
                    if ($_.AccessPaths -contains $accessPath -or $_.AccessPaths -contains $mount) {
                        Remove-PartitionAccessPath -DiskNumber ([uint32]$disk.Number) -PartitionNumber ([uint32]$_.PartitionNumber) -AccessPath $accessPath -ErrorAction SilentlyContinue
                    }
                }
            }
            Dismount-DiskImage -ImagePath $vhd -ErrorAction Stop | Out-Null
            $pos = Get-DiskImage -ImagePath $vhd -ErrorAction Stop
            if ($pos.Attached) {
                throw "Falha ao desmontar VHD descartavel: '$vhd'"
            }
        }
        Remove-Item -LiteralPath $vhd -Force -ErrorAction Stop
    }
    if (Test-Path -LiteralPath $owned.profile_dir) {
        Assert-CI27Child $base $owned.profile_dir
        Remove-Item -LiteralPath $owned.profile_dir -Recurse -Force -ErrorAction Stop
    }
    if (Test-Path -LiteralPath $mount) {
        Assert-CI27Child $base $mount -AllowReparseTarget
        Remove-Item -LiteralPath $mount -Recurse -Force -ErrorAction Stop
    }
    if (Test-Path -LiteralPath $owned.marker_path) {
        Assert-CI27Child $base $owned.marker_path
        Remove-Item -LiteralPath $owned.marker_path -Force -ErrorAction Stop
    }
    Assert-CI27Child $raizFull $base
    Remove-Item -LiteralPath $base -Recurse -Force -ErrorAction Stop
    Write-Output "CI27 exFAT desmontado e removido de $base"
}

if ($MyInvocation.InvocationName -ne '.' -and -not [string]::IsNullOrWhiteSpace($Action)) {
    if ($Action -eq 'mount') {
        Mount-CI27Volume -Raiz $Root
    } elseif ($Action -eq 'dismount') {
        Dismount-CI27Volume -Raiz $Root
    }
}
