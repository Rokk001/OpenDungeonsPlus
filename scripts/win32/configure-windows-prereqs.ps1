param(
    [string]$DependencyRoot = (Join-Path $env:USERPROFILE 'od-deps'),
    [string]$PythonRoot = (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python310'),
    [string]$VsPath = (Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\2022\BuildTools')
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Enter-OpenDungeonsPlus.ps1') -DependencyRoot $DependencyRoot -PythonRoot $PythonRoot -VsPath $VsPath
$taskRepo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
New-Item -ItemType Directory -Path (Join-Path $taskRepo 'build\windows') -Force | Out-Null
$taskConfigureLog = Join-Path $taskRepo 'build\windows\configure.log'
$taskPythonRoot = $PythonRoot.Replace('\', '/')
$taskOptions = @('-S', $taskRepo, '-B', "$taskRepo\build\windows",
    '-G', 'Visual Studio 17 2022', '-A', 'x64', '-DOD_BUILD_TESTING=OFF', '-DBUILD_TESTING=OFF',
    "-DCMAKE_INSTALL_PREFIX=$taskRepo/build/windows/install",
    "-DPYTHON_EXECUTABLE=$taskPythonRoot/python.exe", "-DPYTHON_LIBRARY=$taskPythonRoot/libs/python310.lib",
    "-DPYTHON_DEBUG_LIBRARY=$taskPythonRoot/libs/python310_d.lib", "-DPYTHON_INCLUDE_DIR=$taskPythonRoot/include")
Write-Output 'Checking the project configuration with the installed prerequisites'
$ErrorActionPreference = 'Continue'
& cmake @taskOptions *> $taskConfigureLog
$ErrorActionPreference = 'Stop'
if ($LASTEXITCODE -ne 0) { Get-Content -LiteralPath $taskConfigureLog -Tail 60; throw 'Project configuration failed' }
Write-Output 'Project configuration succeeded'
& (Join-Path $PSScriptRoot 'prepare-windows-runtime.ps1') -DependencyRoot $DependencyRoot -PythonRoot $PythonRoot
