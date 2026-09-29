# Register / remove the upstream-sync scheduled task (monthly by default).
#
# Uses the Task Scheduler COM API (not the *-ScheduledTask cmdlets) so it works
# on every Windows PowerShell build - some trimmed/sandboxed builds lack the
# -Monthly parameter on New-ScheduledTaskTrigger, but the COM API is always there.
#
#   powershell -ExecutionPolicy Bypass -File build\install_sync_task.ps1
#   powershell -ExecutionPolicy Bypass -File build\install_sync_task.ps1 -Frequency monthly -DayOfMonth 1 -Time 09:00
#   powershell -ExecutionPolicy Bypass -File build\install_sync_task.ps1 -Frequency weekly -Day MON -Time 09:00
#   powershell -ExecutionPolicy Bypass -File build\install_sync_task.ps1 -Uninstall
#
# Kept ASCII-only on purpose: PowerShell 5.1 decodes a BOM-less .ps1 as ANSI,
# which would turn any CJK comment into mojibake (and can even look like a
# syntax error). Do not add Chinese comments here unless you also add a BOM.
param(
    [ValidateSet("weekly","monthly")][string]$Frequency = "monthly",
    [string]$Day = "MON",
    [int]$DayOfMonth = 1,
    [string]$Time = "09:00",
    [switch]$Uninstall
)

$ErrorActionPreference = "Stop"
$taskName = "PixelComposer-CN-Sync"
$oldName  = "PixelComposer-CN-WeeklySync"
$repo = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$bat  = Join-Path $repo "build\run_sync.bat"
# DaysOfWeek bitmask for the weekly trigger.
$map  = @{ MON=1; TUE=2; WED=4; THU=8; FRI=16; SAT=32; SUN=64 }

function Remove-Task([string]$n) {
    try {
        $svc = New-Object -ComObject Schedule.Service
        $svc.Connect()
        try { $svc.GetFolder("\").DeleteTask($n, 0) } catch {}
    } catch {}
}

if ($Uninstall) {
    Remove-Task $taskName
    Remove-Task $oldName
    Write-Host "Removed scheduled task(s): $taskName (and legacy $oldName)"
    exit 0
}

if (-not (Test-Path $bat)) { Write-Error "run_sync.bat not found: $bat"; exit 1 }
if ($Time -notmatch '^\d{1,2}:\d{2}$') { Write-Error "Time must be HH:MM"; exit 1 }
$start = "2026-10-01T" + $Time + ":00"

$svc = New-Object -ComObject Schedule.Service
$svc.Connect()
$folder = $svc.GetFolder("\")
# Idempotent: drop any prior registration (old or same name) before recreating.
try { $folder.DeleteTask($taskName, 0) } catch {}
try { $folder.DeleteTask($oldName, 0) } catch {}

$task = $svc.NewTask(0)
$task.RegistrationInfo.Description = "Pixel Composer CN - upstream sync ($Frequency)"
$s = $task.Settings
$s.StartWhenAvailable       = $true
$s.AllowStartIfOnBatteries  = $true
$s.DisallowStartIfOnBatteries = $false
$s.ExecutionTimeLimit       = "PT2H"

$act = $task.Actions.Create(0)            # TASK_ACTION_EXEC
$act.Path = "cmd.exe"
$act.Arguments = "/c `"$bat`""

if ($Frequency -eq "weekly") {
    $k = $Day.ToUpper()
    if (-not $map.ContainsKey($k)) { Write-Error "Day must be one of MON..SUN"; exit 1 }
    $trig = $task.Triggers.Create(3)      # TASK_TRIGGER_WEEKLY
    $trig.StartBoundary = $start
    $trig.DaysOfWeek    = [uint32]$map[$k]
    $trig.WeeksInterval = 1
    $cadence = "every $k at $Time"
} else {
    if ($DayOfMonth -lt 1 -or $DayOfMonth -gt 31) { Write-Error "DayOfMonth must be 1..31"; exit 1 }
    $trig = $task.Triggers.Create(2)      # TASK_TRIGGER_MONTHLY
    $trig.StartBoundary = $start
    $trig.DaysOfMonth   = [uint32][math]::Pow(2, $DayOfMonth - 1)
    $trig.MonthsOfYear  = [uint32]4095    # all 12 months
    $cadence = "on day $DayOfMonth of each month at $Time"
}
$trig.Enabled = $true

$p = $task.Principal
$p.LogonType = 3                          # TASK_LOGON_INTERACTIVE_TOKEN (runs when user logged on)

$folder.RegisterTaskDefinition($taskName, $task, 6, $null, $null, 3) | Out-Null

Write-Host "Created scheduled task: $taskName"
Write-Host "  $cadence"
Write-Host "  runs : $bat"
Write-Host "  logs : $repo\build\_sync_logs\sync.log"
Write-Host "Test it now  : schtasks /run /tn $taskName"
Write-Host "Remove later : powershell -ExecutionPolicy Bypass -File `"$PSCommandPath`" -Uninstall"
