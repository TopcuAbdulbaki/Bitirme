# ============================================
# LLM - Parameterized Deploy Script
# ============================================
# Usage: .\5_llm.ps1 -Token "ghp_xxx" -OrchHost "116.102.85.223" -OrchPort "63567"

param(
    [Parameter(Mandatory=$false)]
    [string]$Token = "<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>",
    
    [Parameter(Mandatory=$true)]
    [string]$OrchHost,
    
    [Parameter(Mandatory=$true)]
    [string]$OrchPort,
    
    [Parameter(Mandatory=$false)]
    [string]$DockerUser = "abdulbakitopcu",
    
    [Parameter(Mandatory=$false)]
    [string]$ModelMode = "transformers"
)

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "LLM DEPLOYMENT (GPU)" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

cd C:\Users\HP\Desktop\Projeler\Bitirme
git add .
git commit -m "Update"
git push origin master

Write-Host "`n=== COPY-PASTE THIS ON VAST.AI LLM GPU ===" -ForegroundColor Green
Write-Host @"

# --- SYSTEM UPDATES ---
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y git curl
curl -fsSL https://get.docker.com | sh
sudo service docker start
sudo docker login -u $DockerUser

# --- NVIDIA CONTAINER TOOLKIT ---
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# --- FRESH DEPLOY ---
git clone https://$Token@github.com/TopcuAbdulbaki/Bitirme.git
cd Bitirme
sudo docker build -f llm/Dockerfile -t $DockerUser/llm:latest .
sudo docker push $DockerUser/llm:latest
sudo docker run -d --name llm \
  --gpus all \
  --restart unless-stopped \
  -e ORCHESTRATOR_HOST=$OrchHost \
  -e ORCHESTRATOR_PORT=$OrchPort \
  -e MODEL_MODE=$ModelMode \
  $DockerUser/llm:latest
sudo docker logs llm -f

# --- UPDATE ---
cd ~/Bitirme
git pull origin master
sudo docker build -f llm/Dockerfile -t $DockerUser/llm:latest .
sudo docker push $DockerUser/llm:latest
sudo docker rm -f llm
sudo docker run -d --name llm \
  --gpus all \
  --restart unless-stopped \
  -e ORCHESTRATOR_HOST=$OrchHost \
  -e ORCHESTRATOR_PORT=$OrchPort \
  -e MODEL_MODE=$ModelMode \
  $DockerUser/llm:latest
sudo docker logs llm -f

"@
