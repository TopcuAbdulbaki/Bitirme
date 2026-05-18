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
    [int]$RabbitMQPort = 5672,
    [string]$PostgresHost = "",
    [int]$PostgresPort = 5432,
    [string]$MinioHost = "",
    [int]$MinioPort = 9000
)
& "$PSScriptRoot\..\helper\windows\remote_role.ps1" -Role db -TargetHost $TargetHost -SshUser $SshUser -SshPort $SshPort -TargetOs $TargetOs -Local:$Local -DryRun:$DryRun -OrchestratorHost $OrchestratorHost -OrchestratorPort $OrchestratorPort -RabbitMQHost $RabbitMQHost -RabbitMQPort $RabbitMQPort -PostgresHost $PostgresHost -PostgresPort $PostgresPort -MinioHost $MinioHost -MinioPort $MinioPort
