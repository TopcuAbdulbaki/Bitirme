# ============================================
# LLM - Build & Run on Vast.ai GPU
# ============================================

# ==========================================
# STEP 1: PUSH CODE TO GITHUB (Run on Windows)
# ==========================================
cd C:\Users\HP\Desktop\Projeler\Bitirme
git add .
git commit -m "Update"
git push origin master


# ==========================================
# STEP 2: ON VAST.AI LLM GPU MACHINE (Copy-paste below)
# ==========================================

# --- SYSTEM UPDATES (Run once or when needed) ---
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y git curl
curl -fsSL https://get.docker.com | sh
sudo service docker start
sudo docker login -u abdulbakitopcu

# --- FRESH DEPLOY (First time) ---

# Install NVIDIA Container Toolkit
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

git clone https://<TOKEN>@github.com/TopcuAbdulbaki/Bitirme.git
cd Bitirme
sudo docker login -u abdulbakitopcu
sudo docker build -f llm/Dockerfile -t abdulbakitopcu/llm:latest .
sudo docker push abdulbakitopcu/llm:latest
sudo docker run -d --name llm \
  --gpus all \
  --restart unless-stopped \
  -e ORCHESTRATOR_HOST=<ORCH_IP> \
  -e ORCHESTRATOR_PORT=<ORCH_PORT> \
  -e MODEL_MODE=transformers \
  abdulbakitopcu/llm:latest
sudo docker logs llm -f

# --- UPDATE (Code changed) ---
cd ~/Bitirme
git pull origin master
sudo docker build -f llm/Dockerfile -t abdulbakitopcu/llm:latest .
sudo docker push abdulbakitopcu/llm:latest
sudo docker rm -f llm
sudo docker run -d --name llm \
  --gpus all \
  --restart unless-stopped \
  -e ORCHESTRATOR_HOST=<ORCH_IP> \
  -e ORCHESTRATOR_PORT=<ORCH_PORT> \
  -e MODEL_MODE=transformers \
  abdulbakitopcu/llm:latest
sudo docker logs llm -f
