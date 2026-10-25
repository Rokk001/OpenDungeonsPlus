# BuildNumber is the fourth version digit; only integrator release builds pass N > 0, all others keep 0.
param([int]$BuildNumber = 0)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Enter-OpenDungeonsPlus.ps1')
$taskRepo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$taskRoot = $taskDependencyRoot
$taskOptions = @('-S', $taskRepo, '-B', "$taskRepo\build\windows",
    '-G', 'Visual Studio 18 2026', '-A', 'x64', '-DOD_BUILD_TESTING=OFF', '-DBUILD_TESTING=OFF',
    "-DOD_BUILD_NUMBER=$BuildNumber",
    "-DCMAKE_INSTALL_PREFIX=$taskRepo/build/windows/install",
    "-DPython_ROOT_DIR=$taskPythonCmakeRoot")
Write-Output 'Checking the original project configuration with the installed prerequisites'
$ErrorActionPreference = 'Continue'
& cmake @taskOptions *> "$taskRoot\logs\opendungeons-configure.log"
$ErrorActionPreference = 'Stop'
if ($LASTEXITCODE -ne 0) { Get-Content -LiteralPath "$taskRoot\logs\opendungeons-configure.log" -Tail 60; throw 'Project configuration failed' }
Write-Output 'Original project configuration succeeded'
& (Join-Path $PSScriptRoot 'prepare-windows-runtime.ps1')
