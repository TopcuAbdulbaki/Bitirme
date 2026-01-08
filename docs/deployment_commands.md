# Vast.ai Deployment - Per-Node Complete Commands

---

# 1. ORCHESTRATOR (Start Here!)

**Vast.ai Instance:** 1 CPU, 2GB RAM, Ubuntu VM
**Docker Options:** `-p 50051:50051 -p 5672:5672`

```bash
# Setup
curl -fsSL https://get.docker.com | sh
sudo service docker start

# Pull & Run
sudo docker pull abdulbakitopcu/orchestrator:latest
sudo docker run -d --name orchestrator \
  -p 50051:50051 \
  -p 5672:5672 \
  --restart unless-stopped \
  abdulbakitopcu/orchestrator:latest

# Verify
sudo docker logs orchestrator -f
```

**Note:** Save your PUBLIC IP and MAPPED PORT (e.g., `116.102.85.223:63567`)
All other nodes will connect to this address.

---

# 2. CRAWLER

**Vast.ai Instance:** 2 CPU, 4GB RAM, Ubuntu VM
**Docker Options:** `-p 50052:50052`

```bash
# Setup
curl -fsSL https://get.docker.com | sh
sudo service docker start

# Get your public IP
curl ifconfig.me

# Pull & Run (REPLACE values!)
sudo docker pull abdulbakitopcu/crawler:latest
sudo docker run -d --name crawler \
  -p 50052:50052 \
  --restart unless-stopped \
  -e ORCHESTRATOR_HOST=<ORCHESTRATOR_PUBLIC_IP> \
  -e ORCHESTRATOR_PORT=<ORCHESTRATOR_MAPPED_PORT> \
  -e PUBLIC_HOST=<THIS_MACHINE_PUBLIC_IP> \
  -e PUBLIC_PORT=<THIS_MACHINE_MAPPED_PORT_FOR_50052> \
  abdulbakitopcu/crawler:latest

# Verify
sudo docker logs crawler -f
```

**Expected:** `[gRPC] Registered as: crawler_xxxxxx`

---

# 3. DB

**Vast.ai Instance:** 2 CPU, 8GB RAM, Ubuntu VM

```bash
# Setup
curl -fsSL https://get.docker.com | sh
sudo service docker start

# Create network
sudo docker network create db-net

# Start PostgreSQL
sudo docker pull pgvector/pgvector:pg15
sudo docker run -d --name postgres \
  --network db-net \
  -e POSTGRES_USER=bitirme \
  -e POSTGRES_PASSWORD=bitirme123 \
  -e POSTGRES_DB=news_db \
  -v postgres_data:/var/lib/postgresql/data \
  pgvector/pgvector:pg15

# Start MinIO
sudo docker pull minio/minio
sudo docker run -d --name minio \
  --network db-net \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin123 \
  minio/minio server /data

# Pull & Run DB Node (REPLACE values!)
sudo docker pull abdulbakitopcu/db:latest
sudo docker run -d --name db \
  --network db-net \
  --restart unless-stopped \
  -e ORCHESTRATOR_HOST=<ORCHESTRATOR_PUBLIC_IP> \
  -e ORCHESTRATOR_PORT=<ORCHESTRATOR_MAPPED_PORT> \
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
```

**Expected:** `[PostgreSQL] ✓` and `[MinIO] ✓` and `Registered as: db_xxxxxx`

---

# 4. VLM

**Vast.ai Instance:** RTX 3090/4090 GPU, PyTorch or CUDA template

```bash
# Install NVIDIA Container Toolkit
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Pull & Run (REPLACE values!)
sudo docker pull abdulbakitopcu/vlm:latest
sudo docker run -d --name vlm \
  --gpus all \
  --restart unless-stopped \
  -e ORCHESTRATOR_HOST=<ORCHESTRATOR_PUBLIC_IP> \
  -e ORCHESTRATOR_PORT=<ORCHESTRATOR_MAPPED_PORT> \
  -e MODEL_MODE=transformers \
  abdulbakitopcu/vlm:latest

# Verify
sudo docker logs vlm -f
```

**Expected:** `Mode: transformers` and `Registered as: vlm_xxxxxx`

---

# 5. LLM

**Vast.ai Instance:** RTX 3090/4090 GPU, PyTorch or CUDA template

```bash
# Install NVIDIA Container Toolkit (skip if same machine as VLM)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Pull & Run (REPLACE values!)
sudo docker pull abdulbakitopcu/llm:latest
sudo docker run -d --name llm \
  --gpus all \
  --restart unless-stopped \
  -e ORCHESTRATOR_HOST=<ORCHESTRATOR_PUBLIC_IP> \
  -e ORCHESTRATOR_PORT=<ORCHESTRATOR_MAPPED_PORT> \
  -e MODEL_MODE=transformers \
  abdulbakitopcu/llm:latest

# Verify
sudo docker logs llm -f
```

**Expected:** `Mode: transformers` and `Registered as: llm_xxxxxx`

---

# BUILD MACHINE (For rebuilding images)

**Vast.ai Instance:** 4 CPU, 16GB RAM, 50GB disk, Ubuntu VM

```bash
# Setup
curl -fsSL https://get.docker.com | sh
sudo service docker start

# Clone repo (replace TOKEN)
git clone https://<YOUR_GITHUB_TOKEN>@github.com/TopcuAbdulbaki/Bitirme.git
cd Bitirme

# Login to Docker Hub
sudo docker login -u abdulbakitopcu

# Build ALL images
docker build -f orchestrator/Dockerfile -t abdulbakitopcu/orchestrator:latest .
docker build -f crawler/Dockerfile -t abdulbakitopcu/crawler:latest .
docker build -f db/Dockerfile -t abdulbakitopcu/db:latest .
docker build -f vlm/Dockerfile -t abdulbakitopcu/vlm:latest .
docker build -f llm/Dockerfile -t abdulbakitopcu/llm:latest .

# Push ALL images
docker push abdulbakitopcu/orchestrator:latest
docker push abdulbakitopcu/crawler:latest
docker push abdulbakitopcu/db:latest
docker push abdulbakitopcu/vlm:latest
docker push abdulbakitopcu/llm:latest
```

---

# QUICK REFERENCE

| Node | Port | Needs GPU? | PUBLIC_HOST needed? |
|------|------|------------|---------------------|
| Orchestrator | 50051 | ❌ | ❌ (already public) |
| Crawler | 50052 | ❌ | ✅ YES |
| DB | - | ❌ | ❌ |
| VLM | - | ✅ | ❌ |
| LLM | - | ✅ | ❌ |
