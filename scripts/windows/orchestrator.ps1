param(
    [string]$TargetHost = "",
    [string]$SshUser = "root",
    [int]$SshPort = 22,
    [ValidateSet("auto", "linux", "windows")][string]$TargetOs = "auto",
    [switch]$Local,
    [switch]$DryRun,
    [switch]$StartRabbitWithCompose,
    [switch]$StartStorageWithCompose,
    [switch]$StopExistingOrchestrator,
    [switch]$FollowLogs
)

$localMode = $Local -or -not $TargetHost
if ($localMode) {
    $invokeParams = @{}
    if ($StartRabbitWithCompose) { $invokeParams.StartRabbitWithCompose = $true }
    if ($StartStorageWithCompose) { $invokeParams.StartStorageWithCompose = $true }
    if ($StopExistingOrchestrator) { $invokeParams.StopExistingOrchestrator = $true }
    if ($FollowLogs) { $invokeParams.FollowLogs = $true }
    if ($DryRun) {
        Write-Host "[dry-run] local role=orchestrator script=$PSScriptRoot\..\helper\windows\orchestrator_local.ps1"
        return
    }
    & "$PSScriptRoot\..\helper\windows\orchestrator_local.ps1" @invokeParams
    return
}

& "$PSScriptRoot\..\helper\windows\remote_role.ps1" -Role orchestrator -TargetHost $TargetHost -SshUser $SshUser -SshPort $SshPort -TargetOs $TargetOs -DryRun:$DryRun
