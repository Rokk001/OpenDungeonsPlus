<#
.SYNOPSIS
    Drives a running game window with Windows input for acceptance runs and takes screenshots with the game's own Print key.

.DESCRIPTION
    The game reads keyboard and mouse through OIS/DirectInput in foreground mode, so input only arrives while the game
    window is the foreground window. Every action therefore first brings the window to the front and aborts without
    sending anything if that fails (locked screen, other window on top).

    The in-game cursor follows only relative mouse movement. Move calibrates it first: a large negative relative move
    pushes the cursor into the top-left corner of the game window, then the wanted client position is reached with one
    relative move, which maps 1:1 to the game's window coordinates. The pause in the corner is kept very short because
    the game scrolls the camera while the cursor touches the window edge.

    Screenshots are never taken with an external capture tool. The Print key makes the game write
    ODscreenshot_*.png into its --appData folder; the Print action copies the newest one to -OutFile.

    State between calls (process id and appData folder) is kept in a small file, -StateFile.

.PARAMETER Action
    Start   start -Exe with an isolated --appData (optionally -Level and -Seed for --run-level) and wait -Wait seconds
    Key     press and release the virtual key -Vk (e.g. 0x1B for Escape)
    Move    move the game cursor to client position -X,-Y (corner calibration)
    Press   left mouse button press and release at the current cursor position
    Click   Move to -X,-Y, then Press
    Print   press the game's Print key and copy the newest game screenshot to -OutFile
    Stop    end the game process started by Start

.EXAMPLE
    .\ingame-input.ps1 -Action Start -Exe build\windows\opendungeons-plus.exe -Level levels\campaign\Campaign1.level -Seed 12345
    .\ingame-input.ps1 -Action Click -X 512 -Y 400
    .\ingame-input.ps1 -Action Print -OutFile out\menu.png
    .\ingame-input.ps1 -Action Stop
#>
param(
    [Parameter(Mandatory = $true)][ValidateSet('Start', 'Key', 'Move', 'Press', 'Click', 'Print', 'Stop')][string]$Action,
    [string]$Exe = '',
    [string]$Level = '',
    [uint32]$Seed = 12345,
    [int]$Seconds = 90,
    [int]$Wait = 25,
    [int]$Vk = 0,
    [int]$X = 0,
    [int]$Y = 0,
    [string]$OutFile = '',
    [string]$StateFile = (Join-Path $env:TEMP 'od-ingame-input.state')
)

$ErrorActionPreference = 'Stop'

Add-Type -Namespace OdInput -Name Native -MemberDefinition @'
[DllImport("user32.dll")] public static extern void keybd_event(byte vk, byte scan, uint flags, UIntPtr extra);
[DllImport("user32.dll")] public static extern void mouse_event(uint flags, int dx, int dy, uint data, UIntPtr extra);
[DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
[DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
[DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int cmd);
'@

# Reads the process id and appData folder written by the Start action.
function Get-GameState
{
    if(-not (Test-Path $StateFile)) { throw 'No game started by this script (state file missing).' }
    $lines = Get-Content $StateFile
    $proc = Get-Process -Id ([int]$lines[0]) -ErrorAction SilentlyContinue
    if(-not $proc) { throw 'The game process is not running any more.' }
    return @{ Process = $proc; AppData = $lines[1] }
}

# Brings the game window to the foreground; returns $false (and sends nothing) when that does not work.
function Set-GameForeground([System.Diagnostics.Process]$proc)
{
    $proc.Refresh()
    $handle = $proc.MainWindowHandle
    [OdInput.Native]::ShowWindow($handle, 9) | Out-Null
    for($i = 0; $i -lt 5; $i++)
    {
        # A tap on Alt lets SetForegroundWindow succeed from a background process
        [OdInput.Native]::keybd_event(0x12, 0, 0, [UIntPtr]::Zero)
        [OdInput.Native]::keybd_event(0x12, 0, 2, [UIntPtr]::Zero)
        [OdInput.Native]::SetForegroundWindow($handle) | Out-Null
        Start-Sleep -Milliseconds 700
        if([OdInput.Native]::GetForegroundWindow() -eq $handle) { return $true }
    }
    return $false
}

# Taps a virtual key; extended scan code and flags are needed for the Print key.
function Send-Key([byte]$vk, [byte]$scan, [uint32]$downFlags, [uint32]$upFlags)
{
    [OdInput.Native]::keybd_event($vk, $scan, $downFlags, [UIntPtr]::Zero)
    Start-Sleep -Milliseconds 120
    [OdInput.Native]::keybd_event($vk, $scan, $upFlags, [UIntPtr]::Zero)
}

# Moves the game cursor to a client position: corner first (relative move beyond the window), then 1:1 relative delta.
function Move-GameCursor([int]$x, [int]$y)
{
    [OdInput.Native]::mouse_event(1, -4000, -4000, 0, [UIntPtr]::Zero)
    # Short pause: a long stay at the window edge would scroll the camera
    Start-Sleep -Milliseconds 40
    [OdInput.Native]::mouse_event(1, $x, $y, 0, [UIntPtr]::Zero)
    Start-Sleep -Milliseconds 300
}

# Left button press and release at the current cursor position.
function Press-GameButton
{
    [OdInput.Native]::mouse_event(2, 0, 0, 0, [UIntPtr]::Zero)
    Start-Sleep -Milliseconds 80
    [OdInput.Native]::mouse_event(4, 0, 0, 0, [UIntPtr]::Zero)
}

if($Action -eq 'Start')
{
    if(-not $Exe) { throw '-Exe is required for Start.' }
    $exePath = (Resolve-Path $Exe).Path
    $appData = Join-Path $env:TEMP ('od-ingame-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
    New-Item -ItemType Directory -Force $appData | Out-Null
    $gameArgs = @('--appData', $appData)
    if($Level) { $gameArgs += @('--run-level', $Level, '--seconds', $Seconds, '--seed', $Seed) }
    $proc = Start-Process $exePath -ArgumentList $gameArgs -WorkingDirectory (Split-Path $exePath) -PassThru
    Set-Content $StateFile @($proc.Id, $appData)
    Start-Sleep $Wait
    if($proc.HasExited) { throw "The game exited early with code $($proc.ExitCode)." }
    "started pid $($proc.Id), appData $appData"
    return
}

$state = Get-GameState
if($Action -eq 'Stop')
{
    Stop-Process -Id $state.Process.Id -Force
    'stopped'
    return
}

if(-not (Set-GameForeground $state.Process)) { 'ABORT: game window is not in the foreground, nothing sent'; exit 2 }

switch($Action)
{
    'Key'   { Send-Key ([byte]$Vk) 0 0 2; 'key sent' }
    'Move'  { Move-GameCursor $X $Y; "cursor at client ($X,$Y)" }
    'Press' { Press-GameButton; 'pressed' }
    'Click' { Move-GameCursor $X $Y; Press-GameButton; "clicked client ($X,$Y)" }
    'Print'
    {
        if(-not $OutFile) { throw '-OutFile is required for Print.' }
        $before = Get-Date
        Send-Key 0x2C 0x37 1 3
        Start-Sleep 4
        $shot = Get-ChildItem $state.AppData -Recurse -Filter 'ODscreenshot_*.png' -ErrorAction SilentlyContinue |
            Where-Object { $_.LastWriteTime -gt $before.AddSeconds(-1) } | Sort-Object LastWriteTime | Select-Object -Last 1
        if(-not $shot) { throw 'The game wrote no screenshot.' }
        New-Item -ItemType Directory -Force (Split-Path -Parent ([System.IO.Path]::GetFullPath($OutFile))) | Out-Null
        Copy-Item $shot.FullName $OutFile -Force
        "screenshot -> $OutFile"
    }
}
