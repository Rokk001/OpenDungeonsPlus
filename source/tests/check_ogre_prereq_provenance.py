"""Exercise patched dependency receipt verification without configuring or compiling."""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / 'scripts/win32'


def main():
    """Reject missing, stale and replaced dependency receipt fixtures."""
    install = (SCRIPTS / 'install-ogre-prereq.ps1').read_text()
    configure = (SCRIPTS / 'configure-windows-prereqs.ps1').read_text()
    runtime = (SCRIPTS / 'prepare-windows-runtime.ps1').read_text()
    assert configure.index('Assert-OgrePrereqProvenance') < configure.index('& cmake')
    assert runtime.index('Assert-OgrePrereqProvenance') < runtime.index('Copy-Item')
    assert install.index('Remove-Item -LiteralPath $taskReceiptPath') < install.index('& $taskCmake @taskOptions')
    assert install.index('if ($taskBuildExit -ne 0)') < install.index('$taskReceipt = [ordered]')
    assert install.index('$taskBuildExit = $LASTEXITCODE') < install.index('$taskBuildExit | Out-File')
    assert '--parallel $taskParallel' in install and '/MP4' not in install
    assert install.index('$taskFreeRam -lt $taskMinimumFreeRam') < install.index('& $taskCmake --build')
    with tempfile.TemporaryDirectory(prefix='ogre-provenance-') as temporary:
        fixture = Path(temporary)
        shutil.copy2(SCRIPTS / 'ogre-prereq-provenance.ps1', fixture)
        shutil.copytree(SCRIPTS / 'patches', fixture / 'patches')
        # These are plain text fixtures, never executable DLLs or installed dependencies.
        binary_dir = fixture / 'install/bin'
        binary_dir.mkdir(parents=True)
        for suffix in ('', '_d'):
            for name in ('OgreBites', 'OgreRTShaderSystem', 'OgreOverlay', 'OgreMain',
                         'Plugin_ParticleFX', 'Plugin_OctreeSceneManager', 'Codec_STBI', 'RenderSystem_GL3Plus'):
                (binary_dir / f'{name}{suffix}.dll').write_text(f'fixture: {name}{suffix}')
        script = fixture / 'check.ps1'
        script.write_text(r'''
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'ogre-prereq-provenance.ps1')
$fixtureRoot = $PSScriptRoot
$receiptPath = Join-Path $fixtureRoot 'install/share/opendungeons-plus/ogre-prereq.json'
New-Item -ItemType Directory -Force (Split-Path -Parent $receiptPath) | Out-Null
$receipt = [ordered]@{ schema = 1; commit = 'f906880885f6014ca9b5bd8aaa09b399394d5676'
    patches = (Get-OgrePrereqPatchHashes); binaries = (Get-OgrePrereqBinaryHashes $fixtureRoot) }
if ($receipt.patches.Count -ne 5 -or $receipt.binaries.Count -ne 16) { throw 'Fixture inventory changed' }
$goodReceipt = $receipt | ConvertTo-Json -Depth 4
function Require-Rejection {
    # A failed fixture must throw rather than report a usable dependency.
    $rejected = $false
    try { Assert-OgrePrereqProvenance $fixtureRoot | Out-Null } catch { $rejected = $true }
    if (-not $rejected) { throw 'Accepted invalid dependency fixture' }
}
Require-Rejection
$goodReceipt | Set-Content -LiteralPath $receiptPath -Encoding UTF8
Assert-OgrePrereqProvenance $fixtureRoot
'{' | Set-Content -LiteralPath $receiptPath
Require-Rejection
$goodReceipt.Replace('"schema":  1', '"schema":  2').Replace('"schema": 1', '"schema": 2') | Set-Content -LiteralPath $receiptPath
Require-Rejection
$goodReceipt.Replace('f906880885f6014ca9b5bd8aaa09b399394d5676', 'wrong-revision') | Set-Content -LiteralPath $receiptPath
Require-Rejection
$receipt.binaries.Remove('OgreMain.dll')
$receipt | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $receiptPath
Require-Rejection
$goodReceipt | Set-Content -LiteralPath $receiptPath
$dll = Join-Path $fixtureRoot 'install/bin/RenderSystem_GL3Plus.dll'
$originalDll = Get-Content -LiteralPath $dll -Raw
'unpatched replacement' | Set-Content -LiteralPath $dll
Require-Rejection
[IO.File]::WriteAllText($dll, $originalDll)
Assert-OgrePrereqProvenance $fixtureRoot
# A receipt for the old four-patch dependency must not be accepted.
$receipt.patches.Remove('ogre14-gl3plus-program-shutdown.patch')
$receipt.binaries['OgreMain.dll'] = (Get-OgrePrereqBinaryHashes $fixtureRoot)['OgreMain.dll']
$receipt | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $receiptPath
Require-Rejection
$goodReceipt | Set-Content -LiteralPath $receiptPath
$patch = Join-Path $fixtureRoot 'patches/ogre14-discard-lock-unsynchronized.patch'
$originalPatch = [IO.File]::ReadAllText($patch)
Add-Content -LiteralPath $patch 'changed patch'
Require-Rejection
[IO.File]::WriteAllText($patch, $originalPatch)
Assert-OgrePrereqProvenance $fixtureRoot
$patch = Join-Path $fixtureRoot 'patches/ogre14-gl3plus-program-shutdown.patch'
Add-Content -LiteralPath $patch 'changed patch'
Require-Rejection
Write-Output 'PASS: nine invalid dependency fixtures rejected; valid receipt accepted'
''', encoding='utf-8')
        # Let Windows PowerShell choose its own modules when Python was launched by pwsh.
        environment = {key: value for key, value in os.environ.items() if key.upper() != 'PSMODULEPATH'}
        result = subprocess.run(['powershell.exe', '-NoProfile', '-File', str(script)],
                                capture_output=True, text=True, env=environment)
        assert result.returncode == 0, result.stdout + result.stderr
        print(result.stdout.strip())


if __name__ == '__main__':
    main()
