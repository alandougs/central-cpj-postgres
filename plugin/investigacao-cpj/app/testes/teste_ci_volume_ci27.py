"""CI27: recusas da fixture descartável, sem executar comandos de disco."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
HELPER = ROOT / 'ferramentas/ci-volume-exfat.ps1'


class ContratoSEC22(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('sec22_ci27', Path(__file__).with_name('teste_segredos_auditoria_sec22.py'))
        cls.sec = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.sec)

    def executar(self, env, permitir_criacao=False, raiz_permitida=None):
        caso = self.sec.SegredosAuditoria('test_volume_sem_acl_real_com_perfil_sintetico_ntfs')
        real_tempdir = tempfile.TemporaryDirectory
        with real_tempdir(prefix='ci27-contrato-') as td:
            raiz_td = Path(td).resolve()
            limite = Path(raiz_permitida).resolve() if raiz_permitida else raiz_td

            def tempdir_guardado(*args, **kwargs):
                if not permitir_criacao:
                    raise AssertionError('Ensaio negativo tentou criar diretório físico antes de recusar.')
                alvo = kwargs.get('dir')
                if alvo is None:
                    raise AssertionError('Criação sem diretório explícito da sandbox recusada.')
                alvo_res = Path(alvo).resolve()
                if alvo_res != limite and limite not in alvo_res.parents:
                    raise AssertionError(f'Operação física fora da sandbox bloqueada: {alvo_res}')
                return real_tempdir(*args, **kwargs)

            limpo = {
                'CPJ_SEC22_EXIGIR_VOLUME_SEM_ACL': '',
                'CPJ_SEC22_VOLUME_SEM_ACL_DIR': '',
                'CPJ_SEC22_PERFIL_NTFS_DIR': '',
                'CPJ_SEC22_REQUIRE_VOLUME': '',
                'CPJ_SEC22_VOLUME_DIR': '',
                'CPJ_SEC22_PROFILE_DIR': '',
            }
            limpo.update(env)
            with patch.dict(os.environ, limpo), \
                 patch.object(self.sec, '__file__', str(raiz_td / 'teste_segredos_auditoria_sec22.py')), \
                 patch.object(self.sec.tempfile, 'TemporaryDirectory', side_effect=tempdir_guardado):
                caso.ws = raiz_td
                caso.dados = {'openai': {'chave': 'SEGREDO-SINTETICO-SEC22', 'modelo': 'ficticio', 'ativo': True}}
                caso.test_volume_sem_acl_real_com_perfil_sintetico_ntfs()

    def test_fixture_obrigatoria_ausente_falha_em_vez_de_skip(self):
        with self.assertRaisesRegex(AssertionError, 'CPJ_SEC22_VOLUME_SEM_ACL_DIR|CPJ_SEC22_VOLUME_DIR'):
            self.executar({'CPJ_SEC22_EXIGIR_VOLUME_SEM_ACL': '1', 'CPJ_SEC22_VOLUME_SEM_ACL_DIR': ''})
        with self.assertRaisesRegex(AssertionError, 'CPJ_SEC22_VOLUME_DIR'):
            self.executar({'CPJ_SEC22_REQUIRE_VOLUME': '1', 'CPJ_SEC22_VOLUME_DIR': '', 'CPJ_SEC22_PROFILE_DIR': ''})

    def test_fixture_explicita_inexistente_falha_em_vez_de_skip(self):
        with tempfile.TemporaryDirectory(prefix='ci27-ausente-') as td:
            ausente = str(Path(td) / 'ausente')
            for exigir in ('1', '0'):
                with self.subTest(exigir=exigir):
                    with self.assertRaisesRegex(AssertionError, 'diretório'):
                        self.executar({
                            'CPJ_SEC22_EXIGIR_VOLUME_SEM_ACL': exigir,
                            'CPJ_SEC22_VOLUME_SEM_ACL_DIR': ausente,
                            'CPJ_SEC22_PERFIL_NTFS_DIR': td,
                        })

    def test_fixture_explicita_com_acl_falha_em_vez_de_skip(self):
        import seguranca_local as S
        with tempfile.TemporaryDirectory(prefix='ci27-acl-') as td, patch.object(S, 'suporta_acl', return_value=True):
            for exigir in ('1', '0'):
                with self.subTest(exigir=exigir):
                    with self.assertRaisesRegex(AssertionError, 'sem ACL'):
                        self.executar({
                            'CPJ_SEC22_EXIGIR_VOLUME_SEM_ACL': exigir,
                            'CPJ_SEC22_VOLUME_SEM_ACL_DIR': td,
                            'CPJ_SEC22_PERFIL_NTFS_DIR': td,
                        })

    @unittest.skipUnless(os.name == 'nt', 'Fluxo DPAPI/volumes Windows')
    def test_fixture_explicita_sem_acl_executa_fluxo_em_sandbox(self):
        import seguranca_local as S
        caso = self.sec.SegredosAuditoria('test_volume_sem_acl_real_com_perfil_sintetico_ntfs')
        with tempfile.TemporaryDirectory(prefix='ci27-positivo-') as td:
            raiz = Path(td).resolve()
            vol = raiz / 'vol-exfat-sintetico'
            perfil = raiz / 'perfil-ntfs-sintetico'
            vol.mkdir()
            perfil.mkdir()

            def acl_simulada(caminho):
                c = str(Path(caminho).resolve())
                return not c.startswith(str(vol))

            with patch.object(S, 'suporta_acl', side_effect=acl_simulada):
                self.executar({
                    'CPJ_SEC22_EXIGIR_VOLUME_SEM_ACL': '1',
                    'CPJ_SEC22_VOLUME_SEM_ACL_DIR': str(vol),
                    'CPJ_SEC22_PERFIL_NTFS_DIR': str(perfil),
                }, permitir_criacao=True, raiz_permitida=raiz)


@unittest.skipUnless(os.name == 'nt', 'Validações de caminhos Windows')
class GuardasPowerShell(unittest.TestCase):
    def test_guardas_reais_com_objetos_sinteticos_sem_cmdlets_de_disco(self):
        self.assertTrue(HELPER.is_file(), 'helper CI27 ausente')
        ps = shutil.which('pwsh') or shutil.which('powershell')
        self.assertIsNotNone(ps, 'PowerShell exigido')
        script = r'''
$ErrorActionPreference = 'Stop'
. $env:CI27_HELPER
function Recusa($bloco) {
    try { & $bloco } catch { return }
    throw 'Operacao insegura foi aceita'
}
$raiz = $env:CI27_FIXTURE
$env:GITHUB_ACTIONS = 'false'
Recusa { Assert-CI27Runner }
$env:GITHUB_ACTIONS = 'true'; $env:RUNNER_OS = 'Windows'; $env:RUNNER_ENVIRONMENT = 'github-hosted'
$env:GITHUB_RUN_ID = '991'; $env:GITHUB_RUN_ATTEMPT = '1'; $env:GITHUB_WORKSPACE = $raiz
$env:CPJ_CI_EXFAT_ENABLE = '0'
Recusa { Assert-CI27Runner }
$env:CPJ_CI_EXFAT_ENABLE = '1'
Assert-CI27Runner
$dentro = Join-Path $raiz 'novo'
Assert-CI27Child $raiz $dentro
Recusa { Assert-CI27Child $raiz ($raiz + '-rival\novo') }
Recusa { Assert-CI27Child $raiz $raiz }
Recusa { Assert-CI27Child $raiz (Join-Path $raiz '..\fora') }
Recusa { Assert-CI27Child ([IO.Path]::GetPathRoot($raiz)) $dentro }
New-Item -ItemType Directory -Path $dentro | Out-Null
Recusa { Assert-CI27New $dentro }
$arquivo = Join-Path $raiz 'existente.vhd'; [IO.File]::WriteAllText($arquivo, 'ficticio')
Recusa { Assert-CI27New $arquivo }
$img = [pscustomobject]@{ ImagePath=$arquivo; Attached=$true; StorageType=2; DevicePath='ficticio'; Number=991 }
$disk = [pscustomobject]@{ Number=991; IsBoot=$false; IsSystem=$false; PartitionStyle='RAW'; NumberOfPartitions=0; BusType='File Backed Virtual'; UniqueId='fixture' }
Assert-CI27Disk $img $disk $arquivo -Raw
$disk.IsBoot=$true; Recusa { Assert-CI27Disk $img $disk $arquivo -Raw }; $disk.IsBoot=$false
$disk.IsSystem=$true; Recusa { Assert-CI27Disk $img $disk $arquivo -Raw }; $disk.IsSystem=$false
$disk.PartitionStyle='GPT'; Recusa { Assert-CI27Disk $img $disk $arquivo -Raw }; $disk.PartitionStyle='RAW'
$disk.NumberOfPartitions=1; Recusa { Assert-CI27Disk $img $disk $arquivo -Raw }; $disk.NumberOfPartitions=0
$disk.Number=992; Recusa { Assert-CI27Disk $img $disk $arquivo -Raw }; $disk.Number=991
$disk.BusType='SATA'; Recusa { Assert-CI27Disk $img $disk $arquivo -Raw }; $disk.BusType='File Backed Virtual'
$img.ImagePath=Join-Path $raiz 'outro.vhd'; Recusa { Assert-CI27Disk $img $disk $arquivo -Raw }; $img.ImagePath=$arquivo
$img.Attached=$false; Recusa { Assert-CI27Disk $img $disk $arquivo -Raw }; $img.Attached=$true
Recusa { Get-CI27OwnedFixture $raiz }
$base = Join-Path $raiz '.ci-sec22-exfat'; New-Item -ItemType Directory -Path $base | Out-Null
$marker = Join-Path $base 'owner.json'
[IO.File]::WriteAllText($marker, '{"schema":"desconhecido"}')
Recusa { Get-CI27OwnedFixture $raiz }
$valido = [ordered]@{
    schema = 'cpj-ci27-exfat-owner/1'
    run_id = '991'
    run_attempt = '1'
    base_dir = $base
    image_path = (Join-Path $base 'sec22-exfat.vhd')
    mount_dir = (Join-Path $base 'mnt')
    profile_dir = (Join-Path $base 'perfil-ntfs')
}
[IO.File]::WriteAllText($marker, ($valido | ConvertTo-Json -Compress))
$owned = Get-CI27OwnedFixture $raiz
if ($owned.image_path -ne (Join-Path $base 'sec22-exfat.vhd')) { throw 'image_path inesperado' }
$valido.run_id = '992'
[IO.File]::WriteAllText($marker, ($valido | ConvertTo-Json -Compress))
Recusa { Get-CI27OwnedFixture $raiz }
$valido.run_id = '991'
$valido.image_path = Join-Path $raiz 'fora.vhd'
[IO.File]::WriteAllText($marker, ($valido | ConvertTo-Json -Compress))
Recusa { Get-CI27OwnedFixture $raiz }
Write-Output 'CI27 guardas verificadas; zero comandos de disco'
'''
        # Fakes não substituem discos reais: estes cmdlets jamais são chamados neste ensaio.
        with tempfile.TemporaryDirectory(prefix='ci27-guardas-') as td:
            r = subprocess.run([ps, '-NoProfile', '-NonInteractive', '-Command', script],
                               env=dict(os.environ, CI27_HELPER=str(HELPER), CI27_FIXTURE=td),
                               capture_output=True, text=True, encoding='utf-8', timeout=30)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('zero comandos de disco', r.stdout)

    def test_ciclo_mount_e_dismount_com_fakes_sem_cmdlets_de_disco(self):
        ps = shutil.which('pwsh') or shutil.which('powershell')
        self.assertIsNotNone(ps, 'PowerShell exigido')
        script = r'''
$ErrorActionPreference = 'Stop'
. $env:CI27_HELPER
function Recusa($bloco) {
    try { & $bloco } catch { return }
    throw 'Operacao insegura foi aceita'
}
$raiz = $env:CI27_FIXTURE
$env:GITHUB_ACTIONS = 'false'
Recusa { Mount-CI27Volume -Raiz $raiz }
Recusa { Dismount-CI27Volume -Raiz $raiz }

$env:GITHUB_ACTIONS = 'true'; $env:RUNNER_OS = 'Windows'; $env:RUNNER_ENVIRONMENT = 'github-hosted'
$env:GITHUB_RUN_ID = '991'; $env:GITHUB_RUN_ATTEMPT = '1'; $env:GITHUB_WORKSPACE = $raiz
$env:CPJ_CI_EXFAT_ENABLE = '1'
$envFile = Join-Path $raiz 'github.env'
[IO.File]::WriteAllText($envFile, '')
$env:GITHUB_ENV = $envFile

$script:anexado = $false
$script:particionado = $false
$script:vhdEsperado = Join-Path (Join-Path $raiz '.ci-sec22-exfat') 'sec22-exfat.vhd'
$script:mntEsperado = (Join-Path (Join-Path $raiz '.ci-sec22-exfat') 'mnt').TrimEnd('\', '/') + '\'

function diskpart.exe {
    param($s, $scriptPath)
    $conteudo = [IO.File]::ReadAllText($scriptPath)
    if ($conteudo -notmatch [Regex]::Escape($script:vhdEsperado)) { throw "diskpart script inesperado: $conteudo" }
    [IO.File]::WriteAllBytes($script:vhdEsperado, @(1, 2, 3, 4))
    $global:LASTEXITCODE = 0
}
function Get-DiskImage {
    param([string]$ImagePath)
    if ($ImagePath -ne $script:vhdEsperado) { throw "ImagePath inesperado: $ImagePath" }
    return [pscustomobject]@{ ImagePath=$ImagePath; Attached=$script:anexado; StorageType=2; Number=($(if ($script:anexado) { 991 } else { $null })) }
}
function Mount-DiskImage {
    param([string]$ImagePath, [switch]$NoDriveLetter, [switch]$PassThru)
    if ($ImagePath -ne $script:vhdEsperado -or -not $NoDriveLetter) { throw 'Mount-DiskImage invalido' }
    $script:anexado = $true
    return Get-DiskImage -ImagePath $ImagePath
}
function Get-Disk {
    param([uint32]$Number)
    if ($Number -ne 991) { throw "Get-Disk Number inesperado: $Number" }
    return [pscustomobject]@{
        Number = 991; IsBoot = $false; IsSystem = $false
        PartitionStyle = ($(if ($script:particionado) { 'GPT' } else { 'RAW' }))
        NumberOfPartitions = ($(if ($script:particionado) { 1 } else { 0 }))
        BusType = 'File Backed Virtual'
    }
}
function Initialize-Disk {
    param($InputObject, $PartitionStyle, [switch]$PassThru)
    if ($InputObject.Number -ne 991 -or $PartitionStyle -ne 'GPT') { throw 'Initialize-Disk invalido' }
    $script:particionado = $true
    return $InputObject
}
function New-Partition {
    param([uint32]$DiskNumber, [switch]$UseMaximumSize)
    if ($DiskNumber -ne 991 -or -not $UseMaximumSize) { throw 'New-Partition invalido' }
    return [pscustomobject]@{ DiskNumber = 991; PartitionNumber = 1 }
}
function Format-Volume {
    param($Partition, [string]$FileSystem, [string]$NewFileSystemLabel, [switch]$Confirm, [switch]$Force)
    if ($Partition.DiskNumber -ne 991 -or $FileSystem -ne 'exFAT') { throw 'Format-Volume invalido' }
    return [pscustomobject]@{ FileSystem = 'exFAT'; FileSystemLabel = $NewFileSystemLabel }
}
function Add-PartitionAccessPath {
    param([uint32]$DiskNumber, [uint32]$PartitionNumber, [string]$AccessPath)
    if ($DiskNumber -ne 991 -or $PartitionNumber -ne 1 -or $AccessPath -ne $script:mntEsperado) { throw "Add-PartitionAccessPath invalido: $AccessPath" }
}
function Get-Partition {
    param([uint32]$DiskNumber)
    return @([pscustomobject]@{ DiskNumber = 991; PartitionNumber = 1; AccessPaths = @($script:mntEsperado) })
}
function Remove-PartitionAccessPath {
    param([uint32]$DiskNumber, [uint32]$PartitionNumber, [string]$AccessPath)
    if ($DiskNumber -ne 991 -or $AccessPath -ne $script:mntEsperado) { throw 'Remove-PartitionAccessPath invalido' }
}
function Dismount-DiskImage {
    param([string]$ImagePath)
    if ($ImagePath -ne $script:vhdEsperado) { throw 'Dismount-DiskImage invalido' }
    $script:anexado = $false
}

Mount-CI27Volume -Raiz $raiz
$envTexto = [IO.File]::ReadAllText($envFile)
if ($envTexto -notmatch 'CPJ_SEC22_EXIGIR_VOLUME_SEM_ACL=1') { throw 'env exigir ausente' }
if ($envTexto -notmatch 'CPJ_SEC22_VOLUME_SEM_ACL_DIR=') { throw 'env volume ausente' }
Dismount-CI27Volume -Raiz $raiz
if (Test-Path -LiteralPath (Join-Path $raiz '.ci-sec22-exfat')) { throw 'base nao foi removida no dismount' }
Write-Output 'Ciclo completo verificado com fakes'
'''
        with tempfile.TemporaryDirectory(prefix='ci27-ciclo-') as td:
            r = subprocess.run([ps, '-NoProfile', '-NonInteractive', '-Command', script],
                               env=dict(os.environ, CI27_HELPER=str(HELPER), CI27_FIXTURE=td),
                               capture_output=True, text=True, encoding='utf-8', timeout=30)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('Ciclo completo verificado com fakes', r.stdout)


if __name__ == '__main__':
    unittest.main(verbosity=2)
