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

# --- Scrape: 2 batches (08:50 sáng, 17:50 chiều) ---
$scrapeTriggers = @(
    (New-ScheduledTaskTrigger -Daily -At "08:50"),
    (New-ScheduledTaskTrigger -Daily -At "17:50")
)
New-BnTask -Name "BinanceSquareBot-Scrape" `
    -CmdArgs @("-m", "src.main", "--scrape") `
    -Triggers $scrapeTriggers

# --- Rewrite: batch 1 lúc 09:00, batch 2 lúc 18:00, max 12 each = ~24/day ---
$rewriteTriggers = @(
    (New-ScheduledTaskTrigger -Daily -At "09:00"),
    (New-ScheduledTaskTrigger -Daily -At "18:00")
)
New-BnTask -Name "BinanceSquareBot-Rewrite" `
    -CmdArgs @("-m", "src.main", "--auto-rewrite", "--max-rewrites", "12") `
    -Triggers $rewriteTriggers

# --- Post: every 45 min from 09:00 to ~23:00 = ~19 posts/day ---
$postTrigger = New-ScheduledTaskTrigger -Daily -At "09:00"
$postTrigger.Repetition = (New-ScheduledTaskTrigger -Once -At "09:00" `
    -RepetitionInterval (New-TimeSpan -Minutes 45) `
    -RepetitionDuration (New-TimeSpan -Hours 14)).Repetition
New-BnTask -Name "BinanceSquareBot-Post" `
    -CmdArgs @("-m", "src.main", "--post-next") `
    -Triggers @($postTrigger)

# --- Daily summary ---
New-BnTask -Name "BinanceSquareBot-Summary" `
    -CmdArgs @("-m", "src.main", "--summary") `
    -Triggers @(New-ScheduledTaskTrigger -Daily -At "23:55")

# --- Auto-tune every 3 days at 23:50 — reweight types + evolve style ---
$tuneTrigger = New-ScheduledTaskTrigger -Once -At "23:50"
$tuneTrigger.Repetition = (New-ScheduledTaskTrigger -Once -At "23:50" `
    -RepetitionInterval (New-TimeSpan -Days 3) `
    -RepetitionDuration (New-TimeSpan -Days 3650)).Repetition
New-BnTask -Name "BinanceSquareBot-Tune" `
    -CmdArgs @("-m", "src.main", "--auto-tune") `
    -Triggers @($tuneTrigger)

# --- Engagement stats collection (2x/day) ---
New-BnTask -Name "BinanceSquareBot-Stats" `
    -CmdArgs @("-m", "src.main", "--collect-stats") `
    -Triggers @(
        (New-ScheduledTaskTrigger -Daily -At "13:00"),
        (New-ScheduledTaskTrigger -Daily -At "23:40")
    )

Write-Host ""
Write-Host "Done. List tasks with: Get-ScheduledTask -TaskName 'BinanceSquareBot-*'"
