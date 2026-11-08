$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'windows-paths.ps1')
. (Join-Path $PSScriptRoot 'ogre-prereq-provenance.ps1')
$taskRoot = $taskDependencyRoot
$taskCmake = $taskCmakeExe
$taskReceiptPath = Join-Path $taskRoot 'install\share\opendungeons-plus\ogre-prereq.json'
# An interrupted or failed install must never leave an earlier success receipt valid.
if (Test-Path -LiteralPath $taskReceiptPath) { Remove-Item -LiteralPath $taskReceiptPath }
$taskOgreCommit = 'f906880885f6014ca9b5bd8aaa09b399394d5676'
$taskOgreHead = (& git -C "$taskRoot\src\ogre" rev-parse HEAD)
if ($taskOgreHead -ne $taskOgreCommit) { throw "OGRE source at $taskRoot\src\ogre is $taskOgreHead, expected $taskOgreCommit (OGRE 14.6.1)" }
$taskPatch = Join-Path $PSScriptRoot 'patches/ogre14-multiwindow-settings.patch'
$ErrorActionPreference = 'Continue'
& git -C "$taskRoot\src\ogre" apply --recount --reverse --check $taskPatch *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Output 'Applying OGRE multi-window settings compatibility fixes'
    & git -C "$taskRoot\src\ogre" apply --recount $taskPatch
    if ($LASTEXITCODE -ne 0) { throw 'OGRE compatibility patch failed' }
}
$taskShortEmitterPatch = Join-Path $PSScriptRoot 'patches/ogre14-short-emitter.patch'
& git -C "$taskRoot\src\ogre" apply --recount --reverse --check $taskShortEmitterPatch *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Output 'Applying OGRE short timed emitter fix'
    & git -C "$taskRoot\src\ogre" apply --recount $taskShortEmitterPatch
    if ($LASTEXITCODE -ne 0) { throw 'OGRE short emitter patch failed' }
}
$taskLightPositionPatch = Join-Path $PSScriptRoot 'patches/ogre14-light-position-cache.patch'
& git -C "$taskRoot\src\ogre" apply --recount --reverse --check $taskLightPositionPatch *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Output 'Applying OGRE view space light cache fix'
    & git -C "$taskRoot\src\ogre" apply --recount $taskLightPositionPatch
    if ($LASTEXITCODE -ne 0) { throw 'OGRE light position patch failed' }
}
$taskDiscardLockPatch = Join-Path $PSScriptRoot 'patches/ogre14-discard-lock-unsynchronized.patch'
& git -C "$taskRoot\src\ogre" apply --recount --reverse --check $taskDiscardLockPatch *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Output 'Applying OGRE discard lock without GPU wait fix'
    & git -C "$taskRoot\src\ogre" apply --recount $taskDiscardLockPatch
    if ($LASTEXITCODE -ne 0) { throw 'OGRE discard lock patch failed' }
}
$taskProgramShutdownPatch = Join-Path $PSScriptRoot 'patches/ogre14-gl3plus-program-shutdown.patch'
& git -C "$taskRoot\src\ogre" apply --recount --reverse --check $taskProgramShutdownPatch *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Output 'Applying OGRE GL3Plus program shutdown fix'
    & git -C "$taskRoot\src\ogre" apply --recount $taskProgramShutdownPatch
    if ($LASTEXITCODE -ne 0) { throw 'OGRE GL3Plus program shutdown patch failed' }
}
$taskExactUniformPatch = Join-Path $PSScriptRoot 'patches/ogre14-gl3plus-exact-uniform-cache.patch'
& git -C "$taskRoot\src\ogre" apply --recount --reverse --check $taskExactUniformPatch *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Output 'Applying OGRE GL3Plus exact uniform upload cache'
    & git -C "$taskRoot\src\ogre" apply --recount $taskExactUniformPatch
    if ($LASTEXITCODE -ne 0) { throw 'OGRE GL3Plus exact uniform cache patch failed' }
}
$taskTowerTracePatch = Join-Path $PSScriptRoot 'patches/ogre14-tower-trace.patch'
& git -C "$taskRoot\src\ogre" apply --recount --reverse --check $taskTowerTracePatch *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Output 'Applying OGRE opt-in tower draw trace'
    & git -C "$taskRoot\src\ogre" apply --recount $taskTowerTracePatch
    if ($LASTEXITCODE -ne 0) { throw 'OGRE tower trace patch failed' }
}
$ErrorActionPreference = 'Stop'
$taskPatchHashes = Get-OgrePrereqPatchHashes
$taskParallel = if ($env:BUILD_PARALLEL) { [int]$env:BUILD_PARALLEL } else { 1 }
if ($taskParallel -lt 1) { throw 'BUILD_PARALLEL must be positive' }
$taskMinimumFreeRam = if ($env:BUILD_MIN_FREE_RAM_GB) { [double]$env:BUILD_MIN_FREE_RAM_GB } else { 2 }
if ($taskMinimumFreeRam -lt 2) { $taskMinimumFreeRam = 2 }
$taskCompilerFlags = '/DWIN32 /D_WINDOWS /W3 /GR /EHsc'
if ($taskMpJobs -gt 1) { $taskCompilerFlags += " /MP$taskMpJobs" }
$taskOptions = @('-S', "$taskRoot\src\ogre", '-B', "$taskRoot\build\ogre",
    '-G', 'Visual Studio 18 2026', '-A', 'x64', "-DCMAKE_INSTALL_PREFIX=$taskRoot\install",
    "-DCMAKE_PREFIX_PATH=$taskRoot\install", '-DOGRE_BUILD_DEPENDENCIES=OFF',
    '-DOGRE_STATIC=OFF', '-DOGRE_CONFIG_THREAD_PROVIDER=std', '-DOGRE_CONFIG_THREADS=3',
    '-DOGRE_BUILD_RENDERSYSTEM_GL3PLUS=ON', '-DOGRE_BUILD_RENDERSYSTEM_GL=OFF',
    '-DOGRE_BUILD_RENDERSYSTEM_D3D9=OFF', '-DOGRE_BUILD_RENDERSYSTEM_D3D11=OFF',
    '-DOGRE_BUILD_RENDERSYSTEM_GLES2=OFF', '-DOGRE_BUILD_PLUGIN_FREEIMAGE=OFF',
    '-DOGRE_BUILD_PLUGIN_EXRCODEC=OFF', '-DOGRE_BUILD_PLUGIN_BSP=OFF',
    '-DOGRE_BUILD_PLUGIN_PCZ=OFF', '-DOGRE_BUILD_PLUGIN_DOT_SCENE=OFF',
    '-DOGRE_BUILD_COMPONENT_JAVA=OFF', '-DOGRE_BUILD_COMPONENT_PYTHON=OFF',
    '-DOGRE_BUILD_COMPONENT_CSHARP=OFF', '-DOGRE_BUILD_COMPONENT_VOLUME=OFF',
    '-DOGRE_BUILD_COMPONENT_PAGING=OFF', '-DOGRE_BUILD_COMPONENT_TERRAIN=OFF',
    '-DOGRE_BUILD_COMPONENT_PROPERTY=OFF', '-DOGRE_BUILD_COMPONENT_MESHLODGENERATOR=OFF',
    '-DOGRE_BUILD_COMPONENT_OVERLAY_IMGUI=OFF',
    '-DOGRE_BUILD_SAMPLES=OFF', '-DOGRE_BUILD_TOOLS=ON', '-DOGRE_BUILD_TESTS=OFF',
    '-DOGRE_ENABLE_PRECOMPILED_HEADERS=ON', '-DOGRE_BUILD_MSVC_MP=OFF', "-DCMAKE_CXX_FLAGS=$taskCompilerFlags")
Write-Output 'Configuring OGRE'
$ErrorActionPreference = 'Continue'
& $taskCmake @taskOptions *> "$taskRoot\logs\ogre-configure.log"
$ErrorActionPreference = 'Stop'
if ($LASTEXITCODE -ne 0) { Get-Content -LiteralPath "$taskRoot\logs\ogre-configure.log" -Tail 55; throw 'OGRE configuration failed' }
foreach ($taskConfiguration in @('Release', 'Debug')) {
    $taskFreeRam = (Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1MB
    if ($taskFreeRam -lt $taskMinimumFreeRam) { throw "Insufficient free RAM for OGRE build: $taskFreeRam GB; need $taskMinimumFreeRam GB" }
    Write-Output "Building and installing OGRE ($taskConfiguration)"
    $ErrorActionPreference = 'Continue'
    & $taskCmake --build "$taskRoot\build\ogre" --config $taskConfiguration --target INSTALL --parallel $taskParallel *> "$taskRoot\logs\ogre-$taskConfiguration.log"
    $taskBuildExit = $LASTEXITCODE
    $taskBuildExit | Out-File -Encoding ascii "$taskRoot\logs\ogre-$taskConfiguration-exit.txt"
    $ErrorActionPreference = 'Stop'
    if ($taskBuildExit -ne 0) { Get-Content -LiteralPath "$taskRoot\logs\ogre-$taskConfiguration.log" -Tail 55; throw "OGRE $taskConfiguration build failed" }
}
# Refuse a receipt if the patch inputs changed during installation.
$taskFinalPatchHashes = Get-OgrePrereqPatchHashes
foreach ($taskName in $taskPatchHashes.Keys) {
    if ($taskPatchHashes[$taskName] -ne $taskFinalPatchHashes[$taskName]) { throw "OGRE patch changed during installation: $taskName" }
}
$taskReceipt = [ordered]@{ schema = 1; commit = $taskOgreCommit; patches = $taskPatchHashes
    binaries = (Get-OgrePrereqBinaryHashes -DependencyRoot $taskRoot) }
New-Item -ItemType Directory -Path (Split-Path -Parent $taskReceiptPath) -Force | Out-Null
$taskReceipt | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $taskReceiptPath -Encoding UTF8
Assert-OgrePrereqProvenance -DependencyRoot $taskRoot
Write-Output 'OGRE installed'
