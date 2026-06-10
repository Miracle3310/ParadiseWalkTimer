param(
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$RunTime = "03:00",
    [string]$TaskPrefix = "ParadiseWalkTimer"
)

$ErrorActionPreference = "Stop"
$installer = Join-Path $ProjectRoot "scripts\install_tasks.ps1"

if (-not (Test-Path $installer)) {
    throw "install_tasks.ps1 was not found in the scripts directory."
}

& $installer `
    -ProjectRoot $ProjectRoot `
    -RunTime $RunTime `
    -TaskPrefix $TaskPrefix `
    -SkipEnsureTask
