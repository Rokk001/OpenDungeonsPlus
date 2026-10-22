param([string[]]$Only)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'windows-paths.ps1')
$taskRoot = $taskDependencyRoot
$taskCmake = $taskCmakeExe
$taskPrefix = "$taskRoot\install"

$taskPackages = @(
    @{ Name = 'expat'; Source = 'expat/expat'; Repo = 'expat'; Commit = 'a76b1174c1ea52abb639a4c69d52b630a8a106a2'; Options = @('-DEXPAT_BUILD_TOOLS=OFF', '-DEXPAT_BUILD_EXAMPLES=OFF', '-DEXPAT_BUILD_TESTS=OFF', '-DEXPAT_BUILD_DOCS=OFF', '-DEXPAT_SHARED_LIBS=ON') },
    @{ Name = 'ois'; Source = 'ois'; Repo = 'ois'; Commit = '6edb487cccb54d59e5b0fff86549d5eef475dea6'; Options = @('-DOIS_BUILD_DEMOS=OFF', '-DOIS_BUILD_SHARED_LIBS=ON', '-DCMAKE_POLICY_VERSION_MINIMUM=3.5') },
    @{ Name = 'sfml'; Source = 'sfml'; Repo = 'sfml'; Commit = '8835b6b955c96fa1ad1278a8dae6f05c4143effc'; Options = @('-DSFML_BUILD_EXAMPLES=OFF', '-DSFML_BUILD_DOC=OFF', '-DSFML_BUILD_WINDOW=ON', '-DSFML_BUILD_GRAPHICS=ON', '-DSFML_BUILD_AUDIO=ON', '-DSFML_BUILD_NETWORK=ON') },
    @{ Name = 'freetype'; Source = 'freetype'; Repo = 'freetype'; Commit = '37515cf56ba3349656049edbed89ffc6f6466f2d'; Options = @('-DFT_DISABLE_ZLIB=ON', '-DFT_DISABLE_BZIP2=ON', '-DFT_DISABLE_PNG=ON', '-DFT_DISABLE_HARFBUZZ=ON', '-DFT_DISABLE_BROTLI=ON') },
    @{ Name = 'pybind11'; Source = 'pybind11'; Repo = 'pybind11'; Commit = '97bf890db679505a14dfe547a5e77bb2bd05dc90'; Options = @('-DPYBIND11_TEST=OFF', '-DPYBIND11_INSTALL=ON', '-DPYBIND11_FINDPYTHON=ON', "-DPython_ROOT_DIR=$taskPythonCmakeRoot") }
)

foreach ($taskPackage in $taskPackages) {
    if ($Only -and $taskPackage.Name -notin $Only) { continue }
    $taskName = $taskPackage.Name
    $taskHead = (& git -C "$taskRoot\src\$($taskPackage.Repo)" rev-parse HEAD)
    if ($taskHead -ne $taskPackage.Commit) { throw "$taskName source is $taskHead, expected $($taskPackage.Commit)" }
    $taskBuild = "$taskRoot\build\$taskName"
    $taskConfigureLog = "$taskRoot\logs\$taskName-configure.log"
    $taskOptions = @('-S', "$taskRoot\src\$($taskPackage.Source)", '-B', $taskBuild,
        '-G', 'Visual Studio 18 2026', '-A', 'x64', "-DCMAKE_INSTALL_PREFIX=$taskPrefix",
        "-DCMAKE_PREFIX_PATH=$taskPrefix", '-DBUILD_SHARED_LIBS=ON', '-DCMAKE_DEBUG_POSTFIX=_d') + $taskPackage.Options
    Write-Output "Configuring $taskName"
    $ErrorActionPreference = 'Continue'
    & $taskCmake @taskOptions *> $taskConfigureLog
    $ErrorActionPreference = 'Stop'
    if ($LASTEXITCODE -ne 0) { Get-Content -LiteralPath $taskConfigureLog -Tail 45; throw "$taskName configuration failed" }
    foreach ($taskConfiguration in @('Release', 'Debug')) {
        $taskBuildLog = "$taskRoot\logs\$taskName-$taskConfiguration.log"
        Write-Output "Building and installing $taskName ($taskConfiguration)"
        $ErrorActionPreference = 'Continue'
        & $taskCmake --build $taskBuild --config $taskConfiguration --target INSTALL --parallel 2 *> $taskBuildLog
        $ErrorActionPreference = 'Stop'
        if ($LASTEXITCODE -ne 0) { Get-Content -LiteralPath $taskBuildLog -Tail 45; throw "$taskName $taskConfiguration build failed" }
    }
    Write-Output "Installed $taskName"
}
