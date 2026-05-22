param(
    [ValidateSet("once", "loop")]
    [string]$Mode = "once",

    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $RepoRoot

$PythonExe = "C:\Users\nitin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if (-not (Test-Path -LiteralPath $PythonExe)) {
    $PythonExe = "python"
}

if (-not (Test-Path -LiteralPath "config.json")) {
    Copy-Item -LiteralPath "config.example.json" -Destination "config.json"
    Write-Host "Created config.json from config.example.json. Review it before relying on alerts."
}

if (-not (Test-Path -LiteralPath ".env")) {
    Copy-Item -LiteralPath ".env.example" -Destination ".env"
    Write-Host "Created .env from .env.example. Add your real email settings before sending alerts."
}

$PythonArgs = @("-m", "rsi_trendline_agent", "--config", "config.json")

if ($Mode -eq "loop") {
    $PythonArgs += "--loop"
} else {
    $PythonArgs += "--once"
}

if ($DryRun) {
    $PythonArgs += "--dry-run"
}

& $PythonExe @PythonArgs
