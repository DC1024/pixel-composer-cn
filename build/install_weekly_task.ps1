# Register / remove the weekly upstream-sync scheduled task.
#
#   powershell -ExecutionPolicy Bypass -File build\install_weekly_task.ps1
#   powershell -ExecutionPolicy Bypass -File build\install_weekly_task.ps1 -Day TUE -Time 20:30
#   powershell -ExecutionPolicy Bypass -File build\install_weekly_task.ps1 -Uninstall
#
# Kept ASCII-only on purpose: PowerShell 5.1 decodes a BOM-less .ps1 as ANSI,
# which would turn any CJK comment into mojibake (and can even look like a
# syntax error). Do not add Chinese comments here unless you also add a BOM.
param(
    [string]$Day = "MON",
    [string]$Time = "09:00",
    [switch]$Uninstall
)

$ErrorActionPreference = "Stop"
$taskName = "PixelComposer-CN-WeeklySync"
$repo = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$bat  = Join-Path $repo "build\run_sync.bat"
$map  = @{
    MON = "Monday"; TUE = "Tuesday"; WED = "Wednesday"; THU = "Thursday";
    FRI = "Friday"; SAT = "Saturday"; SUN = "Sunday"
}

if ($Uninstall) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
    & schtasks /delete /tn $taskName /f 2>$null | Out-Null
    Write-Host "Removed scheduled task: $taskName"
    exit 0
}

if (-not (Test-Path $bat)) { Write-Error "run_sync.bat not found: $bat"; exit 1 }
$key = $Day.ToUpper()
if (-not $map.ContainsKey($key)) { Write-Error "Day must be one of MON..SUN"; exit 1 }

Import-Module ScheduledTasks

$action  = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$bat`""
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $map[$key] -At $Time
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
    -Settings $settings -Force | Out-Null

Write-Host "Created scheduled task: $taskName"
Write-Host "  every $key at $Time"
Write-Host "  runs : $bat"
Write-Host "  logs : $repo\build\_sync_logs\sync.log"
Write-Host "Test it now  : schtasks /run /tn $taskName"
Write-Host "Remove later : powershell -ExecutionPolicy Bypass -File `"$PSCommandPath`" -Uninstall"
