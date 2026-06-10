# Register Windows Task Scheduler jobs for the Binance Square bot.
#
# Run from the repo root in an elevated PowerShell:
#   .\scripts\setup-tasks.ps1
#
# Jobs created (Asia/Ho_Chi_Minh local time):
#   BinanceSquareBot-Scrape       4x/day  06:00, 12:00, 18:00, 22:00
#   BinanceSquareBot-Rewrite      4x/day  06:05, 12:05, 18:05, 22:05
#   BinanceSquareBot-Post         every 30 min, 06:00-23:30
#   BinanceSquareBot-Summary      daily   23:55
[CmdletBinding()]
param(
    [string]$RepoPath = (Resolve-Path "$PSScriptRoot\..").Path,
    [string]$PythonExe = (Get-Command python).Source
)

$ErrorActionPreference = "Stop"
Write-Host "Repo:   $RepoPath"
Write-Host "Python: $PythonExe"

function New-BnTask {
    param(
        [string]$Name,
        [string[]]$Args,
        [Microsoft.Management.Infrastructure.CimInstance[]]$Triggers
    )
    $argLine = ($Args -join " ")
    $action = New-ScheduledTaskAction `
        -Execute $PythonExe `
        -Argument $argLine `
        -WorkingDirectory $RepoPath
    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
    $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive

    if (Get-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $Name -Confirm:$false
    }
    Register-ScheduledTask `
        -TaskName $Name `
        -Action $action `
        -Trigger $Triggers `
        -Settings $settings `
        -Principal $principal | Out-Null
    Write-Host "  registered: $Name"
}

# --- Scrape: 4x/day ---
$scrapeTriggers = @(
    New-ScheduledTaskTrigger -Daily -At "06:00",
    New-ScheduledTaskTrigger -Daily -At "12:00",
    New-ScheduledTaskTrigger -Daily -At "18:00",
    New-ScheduledTaskTrigger -Daily -At "22:00"
)
New-BnTask -Name "BinanceSquareBot-Scrape" `
    -Args @("-m", "src.main", "--scrape") `
    -Triggers $scrapeTriggers

# --- Rewrite: 5 min after each scrape ---
$rewriteTriggers = @(
    New-ScheduledTaskTrigger -Daily -At "06:05",
    New-ScheduledTaskTrigger -Daily -At "12:05",
    New-ScheduledTaskTrigger -Daily -At "18:05",
    New-ScheduledTaskTrigger -Daily -At "22:05"
)
New-BnTask -Name "BinanceSquareBot-Rewrite" `
    -Args @("-m", "src.main", "--auto-rewrite", "--max-rewrites", "12") `
    -Triggers $rewriteTriggers

# --- Post: every 30 min from 06:00 to 23:30 ---
$postTrigger = New-ScheduledTaskTrigger -Daily -At "06:00"
$postTrigger.Repetition = (New-ScheduledTaskTrigger -Once -At "06:00" `
    -RepetitionInterval (New-TimeSpan -Minutes 30) `
    -RepetitionDuration (New-TimeSpan -Hours 17 -Minutes 30)).Repetition
New-BnTask -Name "BinanceSquareBot-Post" `
    -Args @("-m", "src.main", "--post-next") `
    -Triggers @($postTrigger)

# --- Daily summary ---
New-BnTask -Name "BinanceSquareBot-Summary" `
    -Args @("-m", "src.main", "--summary") `
    -Triggers @(New-ScheduledTaskTrigger -Daily -At "23:55")

Write-Host ""
Write-Host "Done. List tasks with: Get-ScheduledTask -TaskName 'BinanceSquareBot-*'"
