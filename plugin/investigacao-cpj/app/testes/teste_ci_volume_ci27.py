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

    def executar(self, env):
        caso = self.sec.SegredosAuditoria('test_volume_sem_acl_real_com_perfil_sintetico_ntfs')
        with tempfile.TemporaryDirectory(prefix='ci27-contrato-') as td, patch.dict(os.environ, env):
            caso.ws = Path(td)
            caso.dados = {'ficticio': {'chave': 'DADO-SINTETICO'}}
            caso.test_volume_sem_acl_real_com_perfil_sintetico_ntfs()

    def test_fixture_obrigatoria_ausente_falha_em_vez_de_skip(self):
        with self.assertRaisesRegex(AssertionError, 'CPJ_SEC22_VOLUME_DIR'):
            self.executar({'CPJ_SEC22_REQUIRE_VOLUME': '1', 'CPJ_SEC22_VOLUME_DIR': '', 'CPJ_SEC22_PROFILE_DIR': ''})

    def test_fixture_explicita_inexistente_falha_em_vez_de_skip(self):
        with tempfile.TemporaryDirectory(prefix='ci27-ausente-') as td:
            with self.assertRaisesRegex(AssertionError, 'diretório'):
                self.executar({'CPJ_SEC22_REQUIRE_VOLUME': '1', 'CPJ_SEC22_VOLUME_DIR': str(Path(td)/'ausente'), 'CPJ_SEC22_PROFILE_DIR': td})

    def test_fixture_explicita_com_acl_falha_em_vez_de_skip(self):
        import seguranca_local as S
        with tempfile.TemporaryDirectory(prefix='ci27-acl-') as td, patch.object(S, 'suporta_acl', return_value=True):
            with self.assertRaisesRegex(AssertionError, 'sem ACL'):
                self.executar({'CPJ_SEC22_REQUIRE_VOLUME': '1', 'CPJ_SEC22_VOLUME_DIR': td, 'CPJ_SEC22_PROFILE_DIR': td})


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
Assert-CI27Runner
$dentro = Join-Path $raiz 'novo'
Assert-CI27Child $raiz $dentro
Recusa { Assert-CI27Child $raiz ($raiz + '-rival\novo') }
Recusa { Assert-CI27Child $raiz $raiz }
Recusa { Assert-CI27Child $raiz (Join-Path $raiz '..\fora') }
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
Write-Output 'CI27 guardas verificadas; zero comandos de disco'
'''
        # Fakes não substituem discos reais: estes cmdlets jamais são chamados neste ensaio.
        with tempfile.TemporaryDirectory(prefix='ci27-guardas-') as td:
            r = subprocess.run([ps, '-NoProfile', '-NonInteractive', '-Command', script],
                               env=dict(os.environ, CI27_HELPER=str(HELPER), CI27_FIXTURE=td),
                               capture_output=True, text=True, encoding='utf-8', timeout=30)
        self.assertEqual(r.returncode, 0, r.stdout+r.stderr)
        self.assertIn('zero comandos de disco', r.stdout)


if __name__ == '__main__':
    unittest.main(verbosity=2)
