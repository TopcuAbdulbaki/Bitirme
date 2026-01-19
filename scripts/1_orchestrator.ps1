# ============================================
# ORCHESTRATOR - Parameterized Deploy Script
# ============================================
# Usage: .\1_orchestrator.ps1 -GrpcPort "50051" -RabbitPort "5672"

param(
    [string]$GrpcPort = "50051",
    [string]$RabbitPort = "5672"
)

# Load environment variables from .env
$envFile = Join-Path $PSScriptRoot ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^([^#=]+)=(.*)$') {
            Set-Variable -Name $matches[1].Trim() -Value $matches[2].Trim() -Scope Script
        }
    }
}

# Set values from env or defaults
if (-not $GH_TOKEN) { $GH_TOKEN = "<TOKEN>" }
if (-not $DOCKER_USER) { $DOCKER_USER = "abdulbakitopcu" }
if (-not $DOCKER_TOKEN) { $DOCKER_TOKEN = "<DOCKER_TOKEN>" }

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "ORCHESTRATOR DEPLOYMENT" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

Write-Host "`n=== COPY-PASTE THIS ON VAST.AI ORCHESTRATOR ===" -ForegroundColor Green
Write-Host @"

# --- SYSTEM UPDATES ---
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y git curl
curl -fsSL https://get.docker.com | sh
sudo service docker start
echo "$DOCKER_TOKEN" | sudo docker login -u $DOCKER_USER --password-stdin

# --- FRESH DEPLOY ---
git clone https://${GH_TOKEN}@github.com/TopcuAbdulbaki/Bitirme.git
cd Bitirme
sudo docker build -f orchestrator/Dockerfile -t ${DOCKER_USER}/orchestrator:latest .
sudo docker push ${DOCKER_USER}/orchestrator:latest
sudo docker run -d --name orchestrator -p ${GrpcPort}:${GrpcPort} -p ${RabbitPort}:${RabbitPort} --restart unless-stopped ${DOCKER_USER}/orchestrator:latest
sudo docker logs orchestrator -f

# --- UPDATE ---
cd ~/Bitirme
git pull origin master
sudo docker build -f orchestrator/Dockerfile -t ${DOCKER_USER}/orchestrator:latest .
sudo docker push ${DOCKER_USER}/orchestrator:latest
sudo docker rm -f orchestrator
sudo docker run -d --name orchestrator -p ${GrpcPort}:${GrpcPort} -p ${RabbitPort}:${RabbitPort} --restart unless-stopped ${DOCKER_USER}/orchestrator:latest
sudo docker logs orchestrator -f

"@
