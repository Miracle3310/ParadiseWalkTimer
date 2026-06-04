param(
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

$ErrorActionPreference = "Stop"
$venv = Join-Path $ProjectRoot ".venv"
$python = Join-Path $venv "Scripts\python.exe"

if (-not (Test-Path $python)) {
    python -m venv $venv
}

& $python -m pip install --upgrade pip
& $python -m pip install -r (Join-Path $ProjectRoot "requirements.txt")

Write-Host "Setup complete."
Write-Host "Dry run:"
Write-Host "  .\.venv\Scripts\python.exe .\run_checkin.py --mode dry-run"
