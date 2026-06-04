param(
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$RunTime = "01:00",
    [string]$TaskPrefix = "ParadiseWalkTimer"
)

$ErrorActionPreference = "Stop"
$python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$runner = Join-Path $ProjectRoot "run_checkin.py"

if (-not (Test-Path $python)) {
    throw "Python venv not found. Run scripts\setup.ps1 first."
}
if (-not (Test-Path $runner)) {
    throw "run_checkin.py was not found in the project directory."
}

$dailyName = "$TaskPrefix-Daily"
$retryName = "$TaskPrefix-RetryOnUnlock"

$dailyAction = New-ScheduledTaskAction `
    -Execute $python `
    -Argument "`"$runner`" --mode scheduled" `
    -WorkingDirectory $ProjectRoot
$dailyTrigger = New-ScheduledTaskTrigger -Daily -At $RunTime
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask `
    -TaskName $dailyName `
    -Action $dailyAction `
    -Trigger $dailyTrigger `
    -Principal $principal `
    -Description "Run Longfor Paradise Walk mini-program check-in." `
    -Force | Out-Null

$retryXmlPath = Join-Path $env:TEMP "$retryName.xml"
$escapedPython = [System.Security.SecurityElement]::Escape($python)
$escapedRunner = [System.Security.SecurityElement]::Escape($runner)
$escapedProjectRoot = [System.Security.SecurityElement]::Escape($ProjectRoot)
$escapedUser = [System.Security.SecurityElement]::Escape("$env:USERDOMAIN\$env:USERNAME")

$retryXml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Retry Longfor Paradise Walk check-in after workstation unlock.</Description>
  </RegistrationInfo>
  <Triggers>
    <SessionStateChangeTrigger>
      <Enabled>true</Enabled>
      <StateChange>SessionUnlock</StateChange>
      <UserId>$escapedUser</UserId>
    </SessionStateChangeTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>$escapedUser</UserId>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT10M</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>$escapedPython</Command>
      <Arguments>"$escapedRunner" --mode retry</Arguments>
      <WorkingDirectory>$escapedProjectRoot</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"@

[System.IO.File]::WriteAllText($retryXmlPath, $retryXml, [System.Text.Encoding]::Unicode)
schtasks.exe /Create /TN $retryName /XML $retryXmlPath /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Failed to register $retryName through schtasks.exe."
}
Remove-Item $retryXmlPath -Force

Write-Host "Registered scheduled tasks:"
Write-Host "  $dailyName"
Write-Host "  $retryName"
