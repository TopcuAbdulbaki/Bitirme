# CUA (Computer Using Agent) Node Deployment Script
# Deploys CUA node to Vast.ai or local GPU instances

param(
    [string]$RemoteHost = "localhost",
    [string]$RemoteUser = "root",
    [int]$RemotePort = 22,
    [bool]$UseSSH = $false,
    [string]$WireGuardIP = "10.0.0.6"
)

Write-Host "[CUA] Starting CUA Node Deployment..." -ForegroundColor Green

# Configuration
$ORCHESTRATOR_HOST = "orchestrator"  # Internal network
$ORCHESTRATOR_PORT = 50051
$CUA_GRPC_PORT = 50054
$RABBITMQ_HOST = "rabbitmq"
$MODEL_MODE = "local"  # or "production"

# Docker environment
$DockerEnv = @(
    "ORCHESTRATOR_HOST=$ORCHESTRATOR_HOST",
    "ORCHESTRATOR_PORT=$ORCHESTRATOR_PORT",
    "CUA_GRPC_PORT=$CUA_GRPC_PORT",
    "RABBITMQ_HOST=$RABBITMQ_HOST",
    "RABBITMQ_PORT=5672",
    "RABBITMQ_USER=guest",
    "RABBITMQ_PASSWORD=guest",
    "MODEL_MODE=$MODEL_MODE",
    "LMSTUDIO_URL=http://lmstudio:1234/v1"
)

# Build Docker image
Write-Host "[CUA] Building Docker image..." -ForegroundColor Cyan
docker build -t abdulbakitopcu/cua:latest -f cua/Dockerfile .
if ($LASTEXITCODE -ne 0) {
    Write-Host "[CUA] Build failed!" -ForegroundColor Red
    exit 1
}

# Option 1: Local deployment
if (-not $UseSSH) {
    Write-Host "[CUA] Starting CUA container locally..." -ForegroundColor Cyan
    $EnvArgs = $DockerEnv | ForEach-Object { "--env", $_ }
    docker run `
        -d `
        --name cua-node `
        --network bitirme-net `
        --gpus all `
        -p 50054:50054 `
        @EnvArgs `
        abdulbakitopcu/cua:latest
    Write-Host "[CUA] CUA node started locally" -ForegroundColor Green
}
# Option 2: Remote SSH deployment
else {
    Write-Host "[CUA] Deploying to remote host via SSH..." -ForegroundColor Cyan
    
    # Build SSH command for Docker run
    $DockerRunCmd = "docker run -d --name cua-node --gpus all -p 50054:50054"
    foreach ($env in $DockerEnv) {
        $DockerRunCmd += " --env `"$env`""
    }
    $DockerRunCmd += " abdulbakitopcu/cua:latest"
    
    # Execute on remote
    ssh -p $RemotePort "${RemoteUser}@${RemoteHost}" $DockerRunCmd
    Write-Host "[CUA] CUA node deployed to $RemoteHost" -ForegroundColor Green
}

Write-Host "[CUA] Deployment complete! Node ID: cua_XXXXXXXX (check orchestrator logs)" -ForegroundColor Green
