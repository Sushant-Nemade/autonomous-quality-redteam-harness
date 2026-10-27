<#
.SYNOPSIS
Registers (or updates) a local Windows Scheduled Task to run the 5-Stage Autonomous Quality,
Red-Team Pentest, and 1,000-User Simulation Harness every morning at 09:00 AM local time.
Note: GitHub Actions also runs this automatically at 09:00 AM every day in the cloud via
.github/workflows/daily_9am_improvement.yml without requiring your laptop to be on.
#>

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$TaskName = "SushantPortfolio-Daily9AM-QualityRedTeamHarness"

$Action = New-ScheduledTaskAction `
    -Execute $PythonExe `
    -Argument "-m harness.cli --project daily --users 1000" `
    -WorkingDirectory $RepoRoot

$Trigger = New-ScheduledTaskTrigger -Daily -At "09:00AM"
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "Runs daily 09:00 AM 5-stage TDD, Integration, Pentest, Improvement, and 1,000-User Simulation on the active portfolio project." `
    -Force

Write-Host "Registered daily 09:00 AM scheduled task: $TaskName"
