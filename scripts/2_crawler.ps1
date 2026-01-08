# ============================================
# CRAWLER - Build & Run on Vast.ai
# ============================================

# ==========================================
# STEP 1: PUSH CODE TO GITHUB (Run on Windows)
# ==========================================
cd C:\Users\HP\Desktop\Projeler\Bitirme
git add .
git commit -m "Update"
git push origin master


# ==========================================
# STEP 2: ON VAST.AI CRAWLER MACHINE (Copy-paste below)
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
sudo docker login -u abdulbakitopcu
sudo docker build -f crawler/Dockerfile -t abdulbakitopcu/crawler:latest .
sudo docker push abdulbakitopcu/crawler:latest
CRAWLER_IP=$(curl -s ifconfig.me)
echo "Crawler IP: $CRAWLER_IP"
sudo docker run -d --name crawler \
  -p 50052:50052 \
  --restart unless-stopped \
  -e ORCHESTRATOR_HOST=<ORCH_IP> \
  -e ORCHESTRATOR_PORT=<ORCH_PORT> \
  -e PUBLIC_HOST=$CRAWLER_IP \
  -e PUBLIC_PORT=<MAPPED_PORT_50052> \
  abdulbakitopcu/crawler:latest
sudo docker logs crawler -f

# --- UPDATE (Code changed) ---
cd ~/Bitirme
git pull origin master
sudo docker build -f crawler/Dockerfile -t abdulbakitopcu/crawler:latest .
sudo docker push abdulbakitopcu/crawler:latest
sudo docker rm -f crawler
CRAWLER_IP=$(curl -s ifconfig.me)
sudo docker run -d --name crawler \
  -p 50052:50052 \
  --restart unless-stopped \
  -e ORCHESTRATOR_HOST=<ORCH_IP> \
  -e ORCHESTRATOR_PORT=<ORCH_PORT> \
  -e PUBLIC_HOST=$CRAWLER_IP \
  -e PUBLIC_PORT=<MAPPED_PORT_50052> \
  abdulbakitopcu/crawler:latest
sudo docker logs crawler -f
