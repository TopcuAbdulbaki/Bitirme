# ============================================
# CRAWLER - Parameterized Deploy Script (POLL MODEL)
# ============================================
# Usage: .\2_crawler.ps1 -OrchHost "116.102.85.223" -OrchPort "63567"

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
    [string]$OrchHost = $env:ORCH_HOST,
    
    [Parameter(Mandatory=$false)]
    [string]$OrchPort = $env:ORCH_PORT,
    
    [Parameter(Mandatory=$false)]
    [string]$DockerUser = $env:DOCKER_USER,
    
    [Parameter(Mandatory=$false)]
    [string]$DockerToken = $env:DOCKER_TOKEN
)

# Set defaults if not from env
if (-not $Token) { $Token = "<TOKEN>" }
if (-not $DockerUser) { $DockerUser = "abdulbakitopcu" }
if (-not $DockerToken) { $DockerToken = "<DOCKER_TOKEN>" }
if (-not $OrchHost) { Write-Host "ERROR: OrchHost required! Set ORCH_HOST in .env or pass -OrchHost" -ForegroundColor Red; exit 1 }
if (-not $OrchPort) { $OrchPort = "50051" }

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
echo "$DockerToken" | sudo docker login -u $DockerUser --password-stdin

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
