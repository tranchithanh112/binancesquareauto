# Remove all BinanceSquareBot-* scheduled tasks.
$ErrorActionPreference = "SilentlyContinue"
$names = @(
    "BinanceSquareBot-Scrape",
    "BinanceSquareBot-Rewrite",
    "BinanceSquareBot-Post",
    "BinanceSquareBot-Summary",
    "BinanceSquareBot-Stats",
    "BinanceSquareBot-Tune"
)
foreach ($n in $names) {
    if (Get-ScheduledTask -TaskName $n -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $n -Confirm:$false
        Write-Host "removed: $n"
    } else {
        Write-Host "not present: $n"
    }
}
