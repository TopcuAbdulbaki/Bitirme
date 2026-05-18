param(
    [string]$TargetHost = "",
    [string]$SshUser = "root",
    [int]$SshPort = 22,
    [ValidateSet("auto", "linux", "windows")][string]$TargetOs = "auto",
    [switch]$Local,
    [switch]$DryRun,
    [string]$OrchestratorHost = "",
    [int]$OrchestratorPort = 50051,
    [string]$RabbitMQHost = "",
    [int]$RabbitMQPort = 5672
)
& "$PSScriptRoot\..\helper\windows\remote_role.ps1" -Role crawler -TargetHost $TargetHost -SshUser $SshUser -SshPort $SshPort -TargetOs $TargetOs -Local:$Local -DryRun:$DryRun -OrchestratorHost $OrchestratorHost -OrchestratorPort $OrchestratorPort -RabbitMQHost $RabbitMQHost -RabbitMQPort $RabbitMQPort
