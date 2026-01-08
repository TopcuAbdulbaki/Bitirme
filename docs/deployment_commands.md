# Vast.ai Deployment - Complete Command Reference

## Prerequisites
- Docker Hub account: `abdulbakitopcu`
- GitHub token for private repo access
- Vast.ai account with rented instances

---

## PHASE 1: BUILD MACHINE SETUP

Rent a **Ubuntu 22.04 VM** on Vast.ai (no GPU needed, ~50GB disk).

```bash
# 1. Install Docker
curl -fsSL https://get.docker.com | sh
sudo service docker start

# 2. Clone the repository (replace YOUR_TOKEN)
git clone https://github.com/TopcuAbdulbaki/Bitirme.git
cd Bitirme

# 3. Login to Docker Hub
sudo docker login -u abdulbakitopcu
# When prompted for password, enter your Docker Hub ACCESS TOKEN (not password)
```

---

## PHASE 2: BUILD AND PUSH ALL IMAGES

```bash
cd ~/Bitirme

# Build Orchestrator (~2 min)
docker build -f orchestrator/Dockerfile -t abdulbakitopcu/orchestrator:latest .

# Build Crawler (~3 min)
docker build -f crawler/Dockerfile -t abdulbakitopcu/crawler:latest .

# Build DB (~10 min - has ML dependencies)
docker build -f db/Dockerfile -t abdulbakitopcu/db:latest .

# Build VLM (~15 min - heavy PyTorch)
docker build -f vlm/Dockerfile -t abdulbakitopcu/vlm:latest .

# Build LLM (~15 min - heavy PyTorch)
docker build -f llm/Dockerfile -t abdulbakitopcu/llm:latest .

# Push all images
docker push abdulbakitopcu/orchestrator:latest
docker push abdulbakitopcu/crawler:latest
docker push abdulbakitopcu/db:latest
docker push abdulbakitopcu/vlm:latest
docker push abdulbakitopcu/llm:latest
```

---

## PHASE 3: DEPLOY ORCHESTRATOR

Rent instance: **1 CPU, 2GB RAM, Ubuntu VM**
Docker Options: `-p 50051:50051 -p 5672:5672`

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh
sudo service docker start

# Run Orchestrator
sudo docker run -d --name orchestrator \
  -p 50051:50051 \
  -p 5672:5672 \
  --restart unless-stopped \
  abdulbakitopcu/orchestrator:latest

# Verify
sudo docker logs orchestrator -f
# Should show: [Orchestrator] Starting on port 50051...
```

**Note the public IP and mapped port** (e.g., `116.102.85.223:63567`)

---

## PHASE 4: DEPLOY CRAWLER

Rent instance: **2 CPU, 4GB RAM, Ubuntu VM**
Docker Options: `-p 50052:50052`

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh
sudo service docker start

# Get this machine's public IP
CRAWLER_IP=$(curl -s ifconfig.me)
echo "Crawler IP: $CRAWLER_IP"

# Check Vast.ai for the EXTERNAL port mapped to 50052
# Example: If Vast.ai shows "116.50.60.70:41234 -> 50052"
# Then PUBLIC_HOST=116.50.60.70 and PUBLIC_PORT=41234

# Run Crawler (REPLACE with your values!)
sudo docker run -d --name crawler \
  -p 50052:50052 \
  --restart unless-stopped \
  -e ORCHESTRATOR_HOST=116.102.85.223 \
  -e ORCHESTRATOR_PORT=63567 \
  -e PUBLIC_HOST=$CRAWLER_IP \
  -e PUBLIC_PORT=<EXTERNAL_MAPPED_PORT> \
  abdulbakitopcu/crawler:latest

# Verify
sudo docker logs crawler -f
# Should show: [gRPC] Registering with PUBLIC address: ...
#              [gRPC] Registered as: crawler_xxxxxx
```

---

## PHASE 5: DEPLOY DB NODE

Rent instance: **2 CPU, 8GB RAM, Ubuntu VM** (for embedding model)

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh
sudo service docker start

# Create network for DB components
sudo docker network create db-net

# 1. Start PostgreSQL with pgvector
sudo docker run -d --name postgres \
  --network db-net \
  -e POSTGRES_USER=bitirme \
  -e POSTGRES_PASSWORD=bitirme123 \
  -e POSTGRES_DB=news_db \
  -v postgres_data:/var/lib/postgresql/data \
  pgvector/pgvector:pg15

# 2. Start MinIO (image storage)
sudo docker run -d --name minio \
  --network db-net \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin123 \
  minio/minio server /data

# 3. Start DB Node
sudo docker run -d --name db \
  --network db-net \
  --restart unless-stopped \
  -e ORCHESTRATOR_HOST=116.102.85.223 \
  -e ORCHESTRATOR_PORT=63567 \
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

# Verify
sudo docker logs db -f
# Should show: [PostgreSQL] ✓
#              [MinIO] ✓
#              [gRPC Client] Registered as: db_xxxxxx
```

---

## PHASE 6: DEPLOY VLM NODE

Rent instance: **RTX 3090/4090 GPU, PyTorch template**

```bash
# Install NVIDIA Container Toolkit (if not pre-installed)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Run VLM
sudo docker run -d --name vlm \
  --gpus all \
  --restart unless-stopped \
  -e ORCHESTRATOR_HOST=116.102.85.223 \
  -e ORCHESTRATOR_PORT=63567 \
  -e MODEL_MODE=transformers \
  abdulbakitopcu/vlm:latest

# Verify
sudo docker logs vlm -f
# Should show: Mode: transformers
#              [gRPC Client] Registered as: vlm_xxxxxx
#              [VLM] Loading model on cuda... (first run only)
```

---

## PHASE 7: DEPLOY LLM NODE

Rent instance: **RTX 3090/4090 GPU, PyTorch template**

```bash
# Install NVIDIA Container Toolkit (same as VLM, skip if already done)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Run LLM
sudo docker run -d --name llm \
  --gpus all \
  --restart unless-stopped \
  -e ORCHESTRATOR_HOST=116.102.85.223 \
  -e ORCHESTRATOR_PORT=63567 \
  -e MODEL_MODE=transformers \
  abdulbakitopcu/llm:latest

# Verify
sudo docker logs llm -f
# Should show: Mode: transformers
#              [gRPC Client] Registered as: llm_xxxxxx
```

---

## VERIFICATION COMMANDS

**On Orchestrator machine:**
```bash
# Check all registered nodes
sudo docker logs orchestrator | grep -i "register"

# Watch live activity
sudo docker logs orchestrator -f
```

**Health check for any node:**
```bash
sudo docker ps                    # Is container running?
sudo docker logs <name> --tail 30 # Recent logs
sudo docker restart <name>        # Restart if needed
```

---

## UPDATE WORKFLOW

When code changes need to be deployed:

```bash
# On BUILD machine:
cd ~/Bitirme
git pull origin master
docker build -f <node>/Dockerfile -t abdulbakitopcu/<node>:latest .
docker push abdulbakitopcu/<node>:latest

# On the NODE's machine:
sudo docker pull abdulbakitopcu/<node>:latest
sudo docker rm -f <node>
# Run the container again with same docker run command
```

---

## TROUBLESHOOTING

| Problem | Solution |
|---------|----------|
| "No module named X" | Rebuild and push the image |
| "could not select device driver" | Install nvidia-container-toolkit |
| "unknown node" heartbeat | Restart the node container |
| apt-get locked | `sudo kill $(pgrep -f unattended)` |
| Port not accessible | Check Vast.ai port mapping |
