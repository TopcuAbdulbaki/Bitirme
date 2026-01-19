# ============================================
# CRAWLER - Deploy Script (POLL MODEL)
# ============================================
# Usage: .\2_crawler.ps1

param(
    [string]$OrchHost,
    [string]$OrchPort = "50051"
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

# Use env vars if params not provided
if (-not $OrchHost -and $ORCH_HOST) { $OrchHost = $ORCH_HOST }
if (-not $OrchPort -or $OrchPort -eq "50051") { if ($ORCH_PORT) { $OrchPort = $ORCH_PORT } }

# Set defaults
if (-not $GH_TOKEN) { $GH_TOKEN = "<TOKEN>" }
if (-not $DOCKER_USER) { $DOCKER_USER = "abdulbakitopcu" }
if (-not $DOCKER_TOKEN) { $DOCKER_TOKEN = "<DOCKER_TOKEN>" }
if (-not $OrchHost) { Write-Host "ERROR: OrchHost required!" -ForegroundColor Red; exit 1 }

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "CRAWLER DEPLOYMENT (POLL MODEL)" -ForegroundColor Cyan
Write-Host "Orchestrator: ${OrchHost}:${OrchPort}" -ForegroundColor Yellow
Write-Host "============================================" -ForegroundColor Cyan

Write-Host "`n=== COPY-PASTE THIS ON VAST.AI CRAWLER ===" -ForegroundColor Green
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
sudo docker build -f crawler/Dockerfile -t ${DOCKER_USER}/crawler:latest .
sudo docker push ${DOCKER_USER}/crawler:latest
sudo docker run -d --name crawler --restart unless-stopped -e ORCHESTRATOR_HOST=${OrchHost} -e ORCHESTRATOR_PORT=${OrchPort} ${DOCKER_USER}/crawler:latest
sudo docker logs crawler -f

# --- UPDATE ---
cd ~/Bitirme
git pull origin master
sudo docker build -f crawler/Dockerfile -t ${DOCKER_USER}/crawler:latest .
sudo docker push ${DOCKER_USER}/crawler:latest
sudo docker rm -f crawler
sudo docker run -d --name crawler --restart unless-stopped -e ORCHESTRATOR_HOST=${OrchHost} -e ORCHESTRATOR_PORT=${OrchPort} ${DOCKER_USER}/crawler:latest
sudo docker logs crawler -f

"@
