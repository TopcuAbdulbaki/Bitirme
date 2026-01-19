# ============================================
# VLM - Deploy Script (GPU)
# ============================================
# Usage: .\4_vlm.ps1 -OrchHost "142.170.89.112" -OrchPort "40943"

param(
    [string]$OrchHost,
    [string]$OrchPort = "50051",
    [string]$ModelMode = "transformers"
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
Write-Host "VLM DEPLOYMENT (GPU)" -ForegroundColor Cyan
Write-Host "Orchestrator: ${OrchHost}:${OrchPort}" -ForegroundColor Yellow
Write-Host "============================================" -ForegroundColor Cyan

Write-Host "`n=== COPY-PASTE THIS ON VAST.AI VLM (GPU Instance) ===" -ForegroundColor Green
Write-Host @"

# --- SYSTEM UPDATES ---
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y git curl
curl -fsSL https://get.docker.com | sh
sudo service docker start
echo "$DOCKER_TOKEN" | sudo docker login -u $DOCKER_USER --password-stdin

# --- NVIDIA CONTAINER TOOLKIT (Ensure GPU support) ---
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# --- VLM SERVICE ---
git clone https://${GH_TOKEN}@github.com/TopcuAbdulbaki/Bitirme.git
cd Bitirme
sudo docker build -f vlm/Dockerfile -t ${DOCKER_USER}/vlm:latest .
sudo docker push ${DOCKER_USER}/vlm:latest
sudo docker run -d --name vlm --gpus all --restart unless-stopped -e ORCHESTRATOR_HOST=${OrchHost} -e ORCHESTRATOR_PORT=${OrchPort} -e MODEL_MODE=${ModelMode} ${DOCKER_USER}/vlm:latest
sudo docker logs vlm -f

# --- UPDATE ---
cd ~/Bitirme
git pull origin master
sudo docker build -f vlm/Dockerfile -t ${DOCKER_USER}/vlm:latest .
sudo docker push ${DOCKER_USER}/vlm:latest
sudo docker rm -f vlm
sudo docker run -d --name vlm --gpus all --restart unless-stopped -e ORCHESTRATOR_HOST=${OrchHost} -e ORCHESTRATOR_PORT=${OrchPort} -e MODEL_MODE=${ModelMode} ${DOCKER_USER}/vlm:latest
sudo docker logs vlm -f

"@
