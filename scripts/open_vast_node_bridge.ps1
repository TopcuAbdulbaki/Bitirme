param(
    [Parameter(Mandatory = $true)][string]$VastHost,
    [Parameter(Mandatory = $true)][int]$VastSshPort,
    [int]$NodeGrpcPort = 15051,
    [int]$NodeRabbitPort = 15670,
    [int]$LocalGrpcPort = 50051,
    [int]$LocalRabbitPort = 5672
)

$ErrorActionPreference = "Stop"

Write-Host "Opening node bridge to $VastHost`:$VastSshPort" -ForegroundColor Cyan
Write-Host "Use these values on that node after the bridge is up:" -ForegroundColor Green
Write-Host "export ORCHESTRATOR_HOST='127.0.0.1'"
Write-Host "export ORCHESTRATOR_PORT='$NodeGrpcPort'"
Write-Host "export RABBITMQ_HOST='127.0.0.1'"
Write-Host "export RABBITMQ_PORT='$NodeRabbitPort'"
Write-Host ""

ssh -p $VastSshPort `
  -N `
  -o ExitOnForwardFailure=yes `
  -o StrictHostKeyChecking=accept-new `
  -o ServerAliveInterval=30 `
  -R "$NodeGrpcPort`:localhost:$LocalGrpcPort" `
  -R "$NodeRabbitPort`:localhost:$LocalRabbitPort" `
  "root@$VastHost"
