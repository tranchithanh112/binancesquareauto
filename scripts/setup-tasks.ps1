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
        [string[]]$CmdArgs,
        [Microsoft.Management.Infrastructure.CimInstance[]]$Triggers
    )
    $argLine = ($CmdArgs -join " ")
    $action = New-ScheduledTaskAction `
        -Execute $PythonExe `
        -Argument $argLine `
        -WorkingDirectory $RepoPath
    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
    $userId = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
    # S4U when elevated (runs locked + Microsoft account safe), Interactive
    # otherwise. S4U needs Administrator to register but no password.
    $isAdmin = ([Security.Principal.WindowsPrincipal] `
        [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator)
    if ($isAdmin) {
        $principal = New-ScheduledTaskPrincipal -UserId $userId `
            -LogonType S4U -RunLevel Limited
    } else {
        $principal = New-ScheduledTaskPrincipal -UserId $userId -LogonType Interactive
    }

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

# --- Scrape: 2x/day (lower volume — quality over spam) ---
$scrapeTriggers = @(
    (New-ScheduledTaskTrigger -Daily -At "07:00"),
    (New-ScheduledTaskTrigger -Daily -At "19:00")
)
New-BnTask -Name "BinanceSquareBot-Scrape" `
    -CmdArgs @("-m", "src.main", "--scrape") `
    -Triggers $scrapeTriggers

# --- Rewrite: 10 min after each scrape, max 6 each = ~12/day capacity ---
$rewriteTriggers = @(
    (New-ScheduledTaskTrigger -Daily -At "07:10"),
    (New-ScheduledTaskTrigger -Daily -At "19:10")
)
New-BnTask -Name "BinanceSquareBot-Rewrite" `
    -CmdArgs @("-m", "src.main", "--auto-rewrite", "--max-rewrites", "6") `
    -Triggers $rewriteTriggers

# --- Post: every 90 min from 07:30 to ~22:30 = ~11 posts/day ---
$postTrigger = New-ScheduledTaskTrigger -Daily -At "07:30"
$postTrigger.Repetition = (New-ScheduledTaskTrigger -Once -At "07:30" `
    -RepetitionInterval (New-TimeSpan -Minutes 90) `
    -RepetitionDuration (New-TimeSpan -Hours 15)).Repetition
New-BnTask -Name "BinanceSquareBot-Post" `
    -CmdArgs @("-m", "src.main", "--post-next") `
    -Triggers @($postTrigger)

# --- Daily summary ---
New-BnTask -Name "BinanceSquareBot-Summary" `
    -CmdArgs @("-m", "src.main", "--summary") `
    -Triggers @(New-ScheduledTaskTrigger -Daily -At "23:55")

# --- Engagement stats collection (2x/day) ---
New-BnTask -Name "BinanceSquareBot-Stats" `
    -CmdArgs @("-m", "src.main", "--collect-stats") `
    -Triggers @(
        (New-ScheduledTaskTrigger -Daily -At "13:00"),
        (New-ScheduledTaskTrigger -Daily -At "23:40")
    )

Write-Host ""
Write-Host "Done. List tasks with: Get-ScheduledTask -TaskName 'BinanceSquareBot-*'"
