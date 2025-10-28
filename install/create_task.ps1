```powershell
Param(
  [string]$ExePath = "$PSScriptRoot\..\dist\wizvod\wizvod.exe",
  [string]$Args = "worker --run",
  [string]$TaskName = "wizvod_worker",
  [string]$TriggerDailyTime = "05:00"
)

$A = New-ScheduledTaskAction -Execute $ExePath -Argument $Args
$T = New-ScheduledTaskTrigger -Daily -At $TriggerDailyTime
$S = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -Action $A -Trigger $T -TaskName $TaskName -Settings $S -Description "wizvod dnevni downloader"
Write-Host "Task $TaskName kreiran."