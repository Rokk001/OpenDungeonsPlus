# Integrator release build: waits for a build slot, determines the build number, configures and builds Release with one job.
# -Run is a short label of the integration run (used for the log file names in out\).
# -Counter is the file with the last deployed build number; it is only read here, the integrator writes the new number after push and deploy.
# -Base is the last deployed state; if major, minor or patch in CMakeLists.txt differ from it, the build number restarts at 1.
# Exits with the exit code of the configure step or of the build itself.
param(
    [Parameter(Mandatory = $true)][string]$Run,
    [Parameter(Mandatory = $true)][string]$Counter,
    [string]$Base = 'origin/integration/all'
)
$wt = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
. (Join-Path $PSScriptRoot 'windows-paths.ps1')
$log = "$wt\out\out-build-run$Run.txt"
New-Item -ItemType Directory -Force "$wt\out" | Out-Null
. (Join-Path $wt '..\wait-for-build-slot.ps1') -MaxMinutes 20
$free = [math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1024)
if ($free -lt 2048) { "RAM too low: $free MB" | Out-File $log; exit 3 }
# Native stderr must not end the wrapper; only the exit codes decide
$ErrorActionPreference = 'Continue'
$buildNumber = [int](& python -I "$wt\scripts\next-build-number.py" --counter $Counter --base $Base)
if ($LASTEXITCODE -ne 0) { "BUILD_NUMBER_EXIT=$LASTEXITCODE" | Out-File $log; exit $LASTEXITCODE }
$buildNumber | Out-File -Encoding ascii "$wt\out\build-number-$Run.txt"
& powershell -NoProfile -File "$wt\scripts\win32\configure-windows-prereqs.ps1" -BuildNumber $buildNumber *> "$wt\out\configure$Run.log"
$cfg = $LASTEXITCODE
if ($cfg -ne 0) { "CONFIGURE_EXIT=$cfg" | Out-File $log; "EXIT=$cfg" | Out-File -Append -Encoding ascii $log; exit $cfg }
# Epoch time right before the build; run-checks.py needs it as --build-start
[DateTimeOffset]::UtcNow.ToUnixTimeSeconds() | Out-File -Encoding ascii "$wt\out\build-start-$Run.txt"
& $taskCmakeExe --build "$wt\build\windows" --config Release --target opendungeons-plus --parallel 1 *> $log
$code = $LASTEXITCODE
"EXIT=$code" | Out-File -Append -Encoding ascii $log
exit $code
