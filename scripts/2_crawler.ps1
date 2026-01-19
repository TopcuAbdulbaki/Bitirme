# ============================================
# CRAWLER - Parameterized Deploy Script (POLL MODEL)
# ============================================
# Usage: .\2_crawler.ps1 -OrchHost "116.102.85.223" -OrchPort "63567"
# 
# NOTE: No more PUBLIC_HOST/PORT needed! Crawler uses poll model now.

param(
    [Parameter(Mandatory=$false)]
    [string]$Token = "<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>",
    
    [Parameter(Mandatory=$true)]
    [string]$OrchHost,
    
    [Parameter(Mandatory=$true)]
    [string]$OrchPort,
    
    [Parameter(Mandatory=$false)]
    [string]$DockerUser = "abdulbakitopcu"
)

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "CRAWLER DEPLOYMENT (POLL MODEL)" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

cd C:\Users\HP\Desktop\Projeler\Bitirme
git add .
git commit -m "Update"
git push origin master

Write-Host "`n=== COPY-PASTE THIS ON VAST.AI CRAWLER ===" -ForegroundColor Green
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
sudo docker build -f crawler/Dockerfile -t $DockerUser/crawler:latest .
sudo docker push $DockerUser/crawler:latest
sudo docker run -d --name crawler \
  --restart unless-stopped \
  -e ORCHESTRATOR_HOST=$OrchHost \
  -e ORCHESTRATOR_PORT=$OrchPort \
  $DockerUser/crawler:latest
sudo docker logs crawler -f

# --- UPDATE ---
cd ~/Bitirme
git pull origin master
sudo docker build -f crawler/Dockerfile -t $DockerUser/crawler:latest .
sudo docker push $DockerUser/crawler:latest
sudo docker rm -f crawler
sudo docker run -d --name crawler \
  --restart unless-stopped \
  -e ORCHESTRATOR_HOST=$OrchHost \
  -e ORCHESTRATOR_PORT=$OrchPort \
  $DockerUser/crawler:latest
sudo docker logs crawler -f

"@
