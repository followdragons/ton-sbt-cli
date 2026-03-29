param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$env:PYTHONPATH = (Join-Path $RepoRoot "src")

Push-Location $RepoRoot
try {
    & $Python -m ton_sbt_tool @Args
}
finally {
    Pop-Location
}
