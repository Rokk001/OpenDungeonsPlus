# Compile check for feature and fix windows: compiles only the .cpp files this branch changed, without linking and without building the game.
# Reads the Release compiler settings (includes, definitions, options) from the integrator's build folder and points the source path at this worktree.
# -Worktree is the worktree to check (default: the one this script lives in); -Base is the state the branch is compared with; -ReleaseProject is the project file of the integrator's build folder.
# Writes out\compile-check.log (file, exit code, duration) in this worktree and exits 0 only if every listed file compiled.
param(
    [string]$Base = 'origin/integration/all',
    [string]$ReleaseProject = 'C:\Users\mario\GitHub\OpenDungeonsPlus\build\campaign-release-worktree\build\windows\opendungeons-plus.vcxproj',
    [int]$MaxWaitMinutes = 30,
    [string]$Worktree = ''
)
if ($Worktree -eq '') { $Worktree = Join-Path $PSScriptRoot '..\..' }
$wt = (Resolve-Path $Worktree).Path
$outDir = "$wt\out\compile-check"
$log = "$wt\out\compile-check.log"
$vcvars = 'C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat'
New-Item -ItemType Directory -Force $outDir | Out-Null
$ErrorActionPreference = 'Continue'

# Returns the number of full builds running (cmake, MSBuild, or a cl.exe started by MSBuild); compile probes of check scripts do not count.
function Get-FullBuildCount {
    $count = @(Get-Process -Name cmake, MSBuild -ErrorAction SilentlyContinue).Count
    foreach ($cl in @(Get-CimInstance Win32_Process -Filter "Name='cl.exe'" -ErrorAction SilentlyContinue)) {
        $parent = Get-CimInstance Win32_Process -Filter "ProcessId=$($cl.ParentProcessId)" -ErrorAction SilentlyContinue
        if ($parent -and ($parent.Name -match '^(MSBuild|tracker|cmake)')) { $count++ }
    }
    return $count
}

# Quotes one compiler argument for a response file: embedded double quotes are escaped with a backslash.
function Format-RspArg([string]$text) {
    return '"' + ($text -replace '"', '\"') + '"'
}

# Reads the Release|x64 ClCompile settings of the integrator's project and returns the compiler arguments for one translation unit.
function Get-ReleaseCompilerArgs {
    [xml]$proj = Get-Content -Raw -Path $ReleaseProject
    $ns = New-Object System.Xml.XmlNamespaceManager($proj.NameTable)
    $ns.AddNamespace('m', 'http://schemas.microsoft.com/developer/msbuild/2003')
    $cl = $proj.SelectSingleNode("//m:ItemDefinitionGroup[contains(@Condition,'Release|x64')]/m:ClCompile", $ns)
    if (-not $cl) { throw "no Release|x64 ClCompile settings in $ReleaseProject" }
    $releaseSource = Join-Path (Split-Path (Split-Path (Split-Path $ReleaseProject))) 'source'
    $result = New-Object System.Collections.ArrayList
    [void]$result.Add('/c'); [void]$result.Add('/nologo')
    foreach ($inc in ($cl.AdditionalIncludeDirectories.InnerText -split ';')) {
        if ($inc -eq '' -or $inc -like '%(*') { continue }
        if ($inc.TrimEnd('\') -ieq $releaseSource.TrimEnd('\')) { $inc = "$wt\source" }
        [void]$result.Add('/I' + (Format-RspArg $inc))
    }
    foreach ($def in ($cl.PreprocessorDefinitions.InnerText -split ';(?=[A-Za-z_])')) {
        if ($def -eq '' -or $def -like '%(*') { continue }
        [void]$result.Add('/D' + (Format-RspArg $def))
    }
    # Options set as project properties
    if ($cl.LanguageStandard.InnerText -eq 'stdcpp17') { [void]$result.Add('/std:c++17') }
    if ($cl.ExceptionHandling.InnerText -eq 'Sync') { [void]$result.Add('/EHsc') }
    if ($cl.Optimization.InnerText -eq 'MaxSpeed') { [void]$result.Add('/O2') }
    if ($cl.RuntimeLibrary.InnerText -eq 'MultiThreadedDLL') { [void]$result.Add('/MD') }
    if ($cl.FloatingPointModel.InnerText -eq 'Fast') { [void]$result.Add('/fp:fast') }
    if ($cl.FunctionLevelLinking.InnerText -eq 'true') { [void]$result.Add('/Gy') }
    if ($cl.WarningLevel.InnerText -eq 'Level3') { [void]$result.Add('/W3') }
    if ($cl.ExternalWarningLevel.InnerText -eq 'TurnOffAllWarnings') { [void]$result.Add('/external:W0') }
    # Free-form options (the /external:I entries)
    foreach ($m in [regex]::Matches($cl.AdditionalOptions.InnerText, '/external:I\s+"([^"]+)"')) {
        [void]$result.Add('/external:I ' + (Format-RspArg $m.Groups[1].Value))
    }
    return $result
}

# Wait while a full build runs, then require 2 GB free RAM
$deadline = (Get-Date).AddMinutes($MaxWaitMinutes)
while ((Get-FullBuildCount) -gt 0) {
    if ((Get-Date) -gt $deadline) { "WAIT_TIMEOUT: a full build still runs" | Out-File $log; exit 4 }
    Write-Host 'waiting: a full build is running'
    Start-Sleep -Seconds 30
}
$free = [math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1024)
if ($free -lt 2048) { "RAM too low: $free MB" | Out-File $log; exit 3 }

$files = @(& git -C $wt diff --name-only --diff-filter=AM "$Base...HEAD" -- source | Where-Object { $_ -like '*.cpp' })
$rsp = "$outDir\args.rsp"
(Get-ReleaseCompilerArgs) | Out-File -Encoding ascii $rsp
"compile check of $($files.Count) file(s) against $Base" | Out-File $log
$failed = 0
foreach ($f in $files) {
    $start = Get-Date
    $src = "$wt\$($f -replace '/', '\')"
    $cmd = "call `"$vcvars`" >nul && cl @`"$rsp`" /Fo`"$outDir\\`" `"$src`""
    $output = & cmd /c $cmd 2>&1
    $code = $LASTEXITCODE
    $secs = [math]::Round(((Get-Date) - $start).TotalSeconds, 1)
    "$f exit=$code seconds=$secs" | Out-File -Append $log
    if ($code -ne 0) {
        $failed++
        $output | Select-String 'error' | ForEach-Object { $_.Line } | Out-File -Append $log
    }
}
"files=$($files.Count) failed=$failed" | Out-File -Append $log
Get-Content $log | Write-Host
if ($failed -gt 0) { exit 1 }
exit 0
