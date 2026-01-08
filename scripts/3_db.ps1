# ============================================
# DB - Build & Run on Vast.ai
# ============================================

# ==========================================
# STEP 1: PUSH CODE TO GITHUB (Run on Windows)
# ==========================================
cd C:\Users\HP\Desktop\Projeler\Bitirme
git add .
git commit -m "Update"
git push origin master


# ==========================================
# STEP 2: ON VAST.AI DB MACHINE (Copy-paste below)
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

sudo docker network create db-net

sudo docker run -d --name postgres \
  --network db-net \
  -e POSTGRES_USER=bitirme \
  -e POSTGRES_PASSWORD=bitirme123 \
  -e POSTGRES_DB=news_db \
  -v postgres_data:/var/lib/postgresql/data \
  pgvector/pgvector:pg15

sudo docker run -d --name minio \
  --network db-net \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin123 \
  minio/minio server /data

sudo docker build -f db/Dockerfile -t abdulbakitopcu/db:latest .
sudo docker push abdulbakitopcu/db:latest
sudo docker run -d --name db \
  --network db-net \
  --restart unless-stopped \
  -e ORCHESTRATOR_HOST=<ORCH_IP> \
  -e ORCHESTRATOR_PORT=<ORCH_PORT> \
  -e POSTGRES_HOST=postgres \
  -e POSTGRES_PORT=5432 \
  -e POSTGRES_USER=bitirme \
  -e POSTGRES_PASSWORD=bitirme123 \
  -e POSTGRES_DB=news_db \
  -e MINIO_HOST=minio \
  -e MINIO_PORT=9000 \
  -e MINIO_ACCESS_KEY=minioadmin \
  -e MINIO_SECRET_KEY=minioadmin123 \
  abdulbakitopcu/db:latest
sudo docker logs db -f

# --- UPDATE (Code changed - PostgreSQL & MinIO stay running!) ---
cd ~/Bitirme
git pull origin master
sudo docker build -f db/Dockerfile -t abdulbakitopcu/db:latest .
sudo docker push abdulbakitopcu/db:latest
sudo docker rm -f db
sudo docker run -d --name db \
  --network db-net \
  --restart unless-stopped \
  -e ORCHESTRATOR_HOST=<ORCH_IP> \
  -e ORCHESTRATOR_PORT=<ORCH_PORT> \
  -e POSTGRES_HOST=postgres \
  -e POSTGRES_PORT=5432 \
  -e POSTGRES_USER=bitirme \
  -e POSTGRES_PASSWORD=bitirme123 \
  -e POSTGRES_DB=news_db \
  -e MINIO_HOST=minio \
  -e MINIO_PORT=9000 \
  -e MINIO_ACCESS_KEY=minioadmin \
  -e MINIO_SECRET_KEY=minioadmin123 \
  abdulbakitopcu/db:latest
sudo docker logs db -f
