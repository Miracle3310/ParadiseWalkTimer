param(
    [string]$TaskPrefix = "ParadiseWalkTimer"
)

$ErrorActionPreference = "SilentlyContinue"
schtasks.exe /Delete /TN "$TaskPrefix-Daily" /F | Out-Null
schtasks.exe /Delete /TN "$TaskPrefix-RetryOnUnlock" /F | Out-Null
Write-Host "Removed ParadiseWalkTimer scheduled tasks if they existed."
