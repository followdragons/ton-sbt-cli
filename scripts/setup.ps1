param(
    [string]$Python = "python"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"

Push-Location $RepoRoot
try {
    & $Python -m venv .venv
    & $VenvPython -m pip install --upgrade pip
    & $VenvPython -m pip install -e ".[dev]"
}
finally {
    Pop-Location
}

Write-Host ""
Write-Host "Environment is ready."
Write-Host "Activate with: .\.venv\Scripts\Activate.ps1"
Write-Host "Run the CLI with: .\scripts\run.ps1 --help"
Write-Host "Run tests with: .\scripts\test.ps1"
