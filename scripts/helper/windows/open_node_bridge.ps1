param(
    [Parameter(Mandatory = $true)][string]$VastHost,
    [Parameter(Mandatory = $true)][int]$VastSshPort,
    [int]$NodeGrpcPort = 15051,
    [int]$NodeRabbitPort = 15670,
    [int]$NodePostgresPort = 15432,
    [int]$NodeMinioPort = 19000,
    [int]$LocalGrpcPort = 50051,
    [int]$LocalRabbitPort = 5672,
    [int]$LocalPostgresPort = 5432,
    [int]$LocalMinioPort = 9000
)

$ErrorActionPreference = "Stop"

Write-Host "Opening node bridge to $VastHost`:$VastSshPort" -ForegroundColor Cyan
Write-Host "Use these values on that node after the bridge is up:" -ForegroundColor Green
Write-Host "export ORCHESTRATOR_HOST='127.0.0.1'"
Write-Host "export ORCHESTRATOR_PORT='$NodeGrpcPort'"
Write-Host "export RABBITMQ_HOST='127.0.0.1'"
Write-Host "export RABBITMQ_PORT='$NodeRabbitPort'"
Write-Host "export POSTGRES_HOST='127.0.0.1'"
Write-Host "export POSTGRES_PORT='$NodePostgresPort'"
Write-Host "export MINIO_HOST='127.0.0.1'"
Write-Host "export MINIO_PORT='$NodeMinioPort'"
Write-Host ""

ssh -p $VastSshPort `
  -N `
  -o ExitOnForwardFailure=yes `
  -o StrictHostKeyChecking=accept-new `
  -o ServerAliveInterval=30 `
  -R "$NodeGrpcPort`:localhost:$LocalGrpcPort" `
  -R "$NodeRabbitPort`:localhost:$LocalRabbitPort" `
  -R "$NodePostgresPort`:localhost:$LocalPostgresPort" `
  -R "$NodeMinioPort`:localhost:$LocalMinioPort" `
  "root@$VastHost"
