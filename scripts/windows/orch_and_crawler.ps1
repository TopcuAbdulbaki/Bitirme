param(
    [ValidateSet("start", "stop", "restart", "status")]
    [string]$Action = "start",
    [string]$ProjectRoot = "C:\Users\HP\Desktop\Projeler\Bitirme",
    [int]$RestartDelaySeconds = 5,
    [switch]$Visible,
    [switch]$StopExisting,
    [switch]$DryRun
)

$helper = "$PSScriptRoot\..\helper\windows\orch_and_crawler_supervisor.ps1"
$invokeParams = @{
    Action = $Action
    Node = "all"
    ProjectRoot = $ProjectRoot
    RestartDelaySeconds = $RestartDelaySeconds
}
if ($Visible) { $invokeParams.Visible = $true }
if ($StopExisting) { $invokeParams.StopExisting = $true }

if ($DryRun) {
    Write-Host "[dry-run] $helper $($invokeParams.GetEnumerator() | ForEach-Object { '-' + $_.Key + ' ' + $_.Value } | Out-String)"
    return
}

& $helper @invokeParams
