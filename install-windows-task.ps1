param(
    [string]$TaskName = "RSI Trendline Agent",
    [string]$At = "4:30PM",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RunScript = Join-Path $RepoRoot "run-agent.ps1"

if (-not (Test-Path -LiteralPath $RunScript)) {
    throw "Cannot find run-agent.ps1 at $RunScript"
}

$PowerShellExe = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
$Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$RunScript`" -Mode once"

if ($DryRun) {
    $Arguments += " -DryRun"
}

$Action = New-ScheduledTaskAction `
    -Execute $PowerShellExe `
    -Argument $Arguments `
    -WorkingDirectory $RepoRoot

$Trigger = New-ScheduledTaskTrigger -Daily -At $At

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Description "Checks the configured stock's RSI trendline touch count and sends email alerts." `
    -Force | Out-Null

Write-Host "Installed scheduled task '$TaskName'. It will run daily at $At."
Write-Host "Task action: $PowerShellExe $Arguments"
