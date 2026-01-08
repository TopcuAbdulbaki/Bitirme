# ============================================
# ORCHESTRATOR - Build & Run on Vast.ai
# ============================================

# ==========================================
# STEP 1: PUSH CODE TO GITHUB (Run on Windows)
# ==========================================
cd C:\Users\HP\Desktop\Projeler\Bitirme
git add .
git commit -m "Update"
git push origin master


# ==========================================
# STEP 2: ON VAST.AI ORCHESTRATOR MACHINE (Copy-paste below)
# ==========================================

# --- SYSTEM UPDATES (Run once or when needed) ---
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y git curl
curl -fsSL https://get.docker.com | sh
sudo service docker start
sudo docker login -u abdulbakitopcu

# --- FRESH DEPLOY (First time) ---
git clone https://<TOKEN>@github.com/TopcuAbdulbaki/Bitirme.git
cd Bitirme
sudo docker build -f orchestrator/Dockerfile -t abdulbakitopcu/orchestrator:latest .
sudo docker push abdulbakitopcu/orchestrator:latest
sudo docker run -d --name orchestrator -p 50051:50051 -p 5672:5672 --restart unless-stopped abdulbakitopcu/orchestrator:latest
sudo docker logs orchestrator -f

# --- UPDATE (Code changed) ---
cd ~/Bitirme
git pull origin master
sudo docker build -f orchestrator/Dockerfile -t abdulbakitopcu/orchestrator:latest .
sudo docker push abdulbakitopcu/orchestrator:latest
sudo docker rm -f orchestrator
sudo docker run -d --name orchestrator -p 50051:50051 -p 5672:5672 --restart unless-stopped abdulbakitopcu/orchestrator:latest
sudo docker logs orchestrator -f
