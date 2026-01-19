# ============================================
# ORCHESTRATOR - Parameterized Deploy Script
# ============================================
# Usage: .\1_orchestrator.ps1 -GrpcPort "50051" -RabbitPort "5672"

# Load environment variables from .env
$envFile = Join-Path $PSScriptRoot ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^([^#=]+)=(.*)$') {
            [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), "Process")
        }
    }
}

param(
    [Parameter(Mandatory=$false)]
    [string]$Token = $env:GH_TOKEN,
    
    [Parameter(Mandatory=$false)]
    [string]$DockerUser = $env:DOCKER_USER,
    
    [Parameter(Mandatory=$false)]
    [string]$DockerToken = $env:DOCKER_TOKEN,
    
    [Parameter(Mandatory=$false)]
    [string]$GrpcPort = "50051",
    
    [Parameter(Mandatory=$false)]
    [string]$RabbitPort = "5672"
)

# Set defaults if not from env
if (-not $Token) { $Token = "<TOKEN>" }
if (-not $DockerUser) { $DockerUser = "abdulbakitopcu" }
if (-not $DockerToken) { $DockerToken = "<DOCKER_TOKEN>" }

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "ORCHESTRATOR DEPLOYMENT" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

cd C:\Users\HP\Desktop\Projeler\Bitirme
git add .
git commit -m "Update"
git push origin master

Write-Host "`n=== COPY-PASTE THIS ON VAST.AI ORCHESTRATOR ===" -ForegroundColor Green
Write-Host @"

# --- SYSTEM UPDATES ---
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y git curl
curl -fsSL https://get.docker.com | sh
sudo service docker start
echo "$DockerToken" | sudo docker login -u $DockerUser --password-stdin

# --- FRESH DEPLOY ---
git clone https://$Token@github.com/TopcuAbdulbaki/Bitirme.git
cd Bitirme
sudo docker build -f orchestrator/Dockerfile -t $DockerUser/orchestrator:latest .
sudo docker push $DockerUser/orchestrator:latest
sudo docker run -d --name orchestrator -p $GrpcPort`:$GrpcPort -p $RabbitPort`:$RabbitPort --restart unless-stopped $DockerUser/orchestrator:latest
sudo docker logs orchestrator -f

# --- UPDATE ---
cd ~/Bitirme
git pull origin master
sudo docker build -f orchestrator/Dockerfile -t $DockerUser/orchestrator:latest .
sudo docker push $DockerUser/orchestrator:latest
sudo docker rm -f orchestrator
sudo docker run -d --name orchestrator -p $GrpcPort`:$GrpcPort -p $RabbitPort`:$RabbitPort --restart unless-stopped $DockerUser/orchestrator:latest
sudo docker logs orchestrator -f

"@
