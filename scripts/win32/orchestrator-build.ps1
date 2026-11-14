# HaiveQueen Orchestrator, Build step of ODP. Runs in the plan worktree: build number, configure, Release build, then all check scripts and the load test (run-checks.py).
# Parallel value, compiler jobs and minimum free RAM come from the HaiveQueen build settings (BUILD_PARALLEL, BUILD_JOBS, BUILD_MIN_FREE_RAM_GB).
# -Counter: file with the last deployed build number (only read here, the Deploy step writes it). -Base: the last deployed state. -Checks: path of run-checks.py.
param(
    [Parameter(Mandatory = $true)][string]$Counter,
    [Parameter(Mandatory = $true)][string]$Base,
    [Parameter(Mandatory = $true)][string]$Checks
)
# Native stderr must not end the script; only the exit codes decide
$ErrorActionPreference = 'Continue'
$wt = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
New-Item -ItemType Directory -Force "$wt\out" | Out-Null
$run = 'orch-' + (Get-Date -Format 'yyyyMMdd-HHmmss')
Set-Content -Encoding ascii "$wt\out\orch-run.txt" $run
# The compiler job count of HaiveQueen (BUILD_JOBS) becomes the /MP job count of the project (BUILD_MP_JOBS, read by windows-paths.ps1)
if ($env:BUILD_JOBS -and -not $env:BUILD_MP_JOBS) { $env:BUILD_MP_JOBS = $env:BUILD_JOBS }
. (Join-Path $PSScriptRoot 'windows-paths.ps1')
$n = [int](& python -I "$wt\scripts\next-build-number.py" --counter $Counter --base $Base)
if ($LASTEXITCODE -ne 0) { Write-Output "build number failed (exit $LASTEXITCODE)"; exit $LASTEXITCODE }
Set-Content -Encoding ascii "$wt\out\build-number-$run.txt" $n
Write-Output "configure started: $run"
& powershell -NoProfile -File "$PSScriptRoot\configure-windows-prereqs.ps1" -BuildNumber $n *>&1 | Tee-Object -FilePath "$wt\out\configure-$run.log"
if ($LASTEXITCODE -ne 0) { Write-Output "configure failed (exit $LASTEXITCODE), log out\configure-$run.log"; exit $LASTEXITCODE }
$parallel = if ($env:BUILD_PARALLEL) { [int]$env:BUILD_PARALLEL } else { 1 }
# Force the linker to produce a fresh executable even when an earlier build is up to date.
$exe = Join-Path $wt 'build\windows\opendungeons-plus.exe'
if (Test-Path -LiteralPath $exe) { Remove-Item -LiteralPath $exe -Force -ErrorAction Stop }
# Epoch time right before the build; run-checks.py needs it as --build-start
$start = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
Write-Output "build started: $run"
& $taskCmakeExe --build "$wt\build\windows" --config Release --target opendungeons-plus --parallel $parallel *>&1 | Tee-Object -FilePath "$wt\out\build-$run.log"
$code = $LASTEXITCODE
if ($code -ne 0) { Write-Output "build failed (exit $code), log out\build-$run.log"; exit $code }
Write-Output "checks started: $run"
& python -u -I $Checks --repo $wt --out "$wt\out\checks-$run.txt" --base $Base --build-start $start --run $run
$code = $LASTEXITCODE
if ($code -ne 0) { Write-Output "checks failed (exit $code), see out\checks-$run.txt" }
exit $code
