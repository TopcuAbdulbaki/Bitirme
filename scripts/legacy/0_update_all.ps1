# ============================================
# UPDATE ALL MACHINES - Quick Reference
# ============================================

# ==========================================
# STEP 1: PUSH CODE TO GITHUB (Run on Windows)
# ==========================================
cd C:\Users\HP\Desktop\Projeler\Bitirme
git add .
git commit -m "Update"
git push origin master


# ==========================================
# STEP 2: RUN ON EACH MACHINE (Copy-paste each section to its machine)
# ==========================================

# =============== ORCHESTRATOR ===============
cd ~/Bitirme
git pull origin master
sudo docker build -f orchestrator/Dockerfile -t abdulbakitopcu/orchestrator:latest .
sudo docker push abdulbakitopcu/orchestrator:latest
sudo docker rm -f orchestrator
sudo docker run -d --name orchestrator -p 50051:50051 -p 5672:5672 --restart unless-stopped abdulbakitopcu/orchestrator:latest
sudo docker logs orchestrator --tail 20


# =============== CRAWLER ===============
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
sudo docker logs crawler --tail 20


# =============== DB ===============
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
sudo docker logs db --tail 20


# =============== VLM ===============
cd ~/Bitirme
git pull origin master
sudo docker build -f vlm/Dockerfile -t abdulbakitopcu/vlm:latest .
sudo docker push abdulbakitopcu/vlm:latest
sudo docker rm -f vlm
sudo docker run -d --name vlm \
  --gpus all \
  --restart unless-stopped \
  -e ORCHESTRATOR_HOST=<ORCH_IP> \
  -e ORCHESTRATOR_PORT=<ORCH_PORT> \
  -e MODEL_MODE=transformers \
  abdulbakitopcu/vlm:latest
sudo docker logs vlm --tail 20


# =============== LLM ===============
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
sudo docker logs llm --tail 20


# ==========================================
# VERIFY ALL NODES (Run on Orchestrator)
# ==========================================
sudo docker logs orchestrator | grep -i "register"
