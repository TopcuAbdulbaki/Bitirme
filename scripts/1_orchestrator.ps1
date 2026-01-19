# ============================================
# ORCHESTRATOR - Parameterized Deploy Script
# ============================================
# Usage: .\1_orchestrator.ps1 -Token "ghp_xxx" -DockerUser "abdulbakitopcu" -GrpcPort "50051" -RabbitPort "5672"

param(
    [Parameter(Mandatory=$false)]
    [string]$Token = "<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>",
    
    [Parameter(Mandatory=$false)]
    [string]$DockerUser = "abdulbakitopcu",
    
    [Parameter(Mandatory=$false)]
    [string]$GrpcPort = "50051",
    
    [Parameter(Mandatory=$false)]
    [string]$RabbitPort = "5672"
)

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "ORCHESTRATOR DEPLOYMENT" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# Push code to GitHub
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
sudo docker login -u $DockerUser

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
