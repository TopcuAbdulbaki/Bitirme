# Vast.ai Deployment - Per-Node Complete Commands

> [!TIP]
> **Orchestrator Address:** You must replace `<ORCH_IP>` and `<ORCH_PORT>` with your Orchestrator's address (e.g., `142.170.89.112:40943`) for all other nodes.

---

# 1. ORCHESTRATOR (Start Here!)

**Vast.ai Instance:** 1 CPU, 2GB RAM, Ubuntu VM
**Docker Options:** `-p 50051:50051 -p 5672:5672`

```bash
# Setup
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y git curl
curl -fsSL https://get.docker.com | sh
sudo service docker start
echo "<YOUR_DOCKER_TOKEN>" | sudo docker login -u abdulbakitopcu --password-stdin

# Pull & Run
git clone https://<YOUR_GITHUB_TOKEN>@github.com/TopcuAbdulbaki/Bitirme.git
cd Bitirme
sudo docker build -f orchestrator/Dockerfile -t abdulbakitopcu/orchestrator:latest .
sudo docker push abdulbakitopcu/orchestrator:latest
sudo docker run -d --name orchestrator \
  -p 50051:50051 \
  -p 5672:5672 \
  --restart unless-stopped \
  abdulbakitopcu/orchestrator:latest

# Verify
sudo docker logs orchestrator -f
```

---

# 2. CRAWLER (Poll Model)

**Vast.ai Instance:** 2+ CPU, 4GB+ RAM, Ubuntu VM
**Docker Options:** None needed (outbound only)

```bash
# Setup
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y git curl
curl -fsSL https://get.docker.com | sh
sudo service docker start
echo "<YOUR_DOCKER_TOKEN>" | sudo docker login -u abdulbakitopcu --password-stdin

# Pull & Run (REPLACE IP/PORT!)
git clone https://<YOUR_GITHUB_TOKEN>@github.com/TopcuAbdulbaki/Bitirme.git
cd Bitirme
sudo docker build -f crawler/Dockerfile -t abdulbakitopcu/crawler:latest .
sudo docker push abdulbakitopcu/crawler:latest
sudo docker run -d --name crawler \
  --restart unless-stopped \
  -e ORCHESTRATOR_HOST=<ORCH_IP> \
  -e ORCHESTRATOR_PORT=<ORCH_PORT> \
  abdulbakitopcu/crawler:latest

# Verify
sudo docker logs crawler -f
```

---

# 3. DB (PostgreSQL + MinIO)

**Vast.ai Instance:** 2 CPU, 8GB RAM, Ubuntu VM
**Docker Options:** None

```bash
# Setup
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y git curl
curl -fsSL https://get.docker.com | sh
sudo service docker start
echo "<YOUR_DOCKER_TOKEN>" | sudo docker login -u abdulbakitopcu --password-stdin

# Databases
sudo docker network create db-net
sudo docker run -d --name postgres --network db-net -e POSTGRES_USER=bitirme -e POSTGRES_PASSWORD=bitirme123 -e POSTGRES_DB=news_db -v postgres_data:/var/lib/postgresql/data pgvector/pgvector:pg15
sudo docker run -d --name minio --network db-net -e MINIO_ROOT_USER=minioadmin -e MINIO_ROOT_PASSWORD=minioadmin123 minio/minio server /data

# DB Node (Connects to DBs and Orchestrator)
git clone https://<YOUR_GITHUB_TOKEN>@github.com/TopcuAbdulbaki/Bitirme.git
cd Bitirme
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

# Verify
sudo docker logs db -f
```

---

# 4. VLM (GPU Node)

**Vast.ai Instance:** GPU (RTX 3090/4090), Ubuntu VM
**Docker Options:** `--gpus all`

```bash
# Setup & NVIDIA Toolkit
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y git curl nvidia-container-toolkit
curl -fsSL https://get.docker.com | sh
sudo service docker start
echo "<YOUR_DOCKER_TOKEN>" | sudo docker login -u abdulbakitopcu --password-stdin

# Configure NVIDIA Runtime
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Pull & Run
git clone https://<YOUR_GITHUB_TOKEN>@github.com/TopcuAbdulbaki/Bitirme.git
cd Bitirme
sudo docker build -f vlm/Dockerfile -t abdulbakitopcu/vlm:latest .
sudo docker push abdulbakitopcu/vlm:latest
sudo docker run -d --name vlm \
  --gpus all \
  --restart unless-stopped \
  -e ORCHESTRATOR_HOST=<ORCH_IP> \
  -e ORCHESTRATOR_PORT=<ORCH_PORT> \
  -e MODEL_MODE=transformers \
  abdulbakitopcu/vlm:latest

# Verify
sudo docker logs vlm -f
```

---

# 5. LLM (GPU Node)

**Vast.ai Instance:** GPU (RTX 3090/4090), Ubuntu VM
**Docker Options:** `--gpus all`

```bash
# Setup & NVIDIA Toolkit
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y git curl nvidia-container-toolkit
curl -fsSL https://get.docker.com | sh
sudo service docker start
echo "<YOUR_DOCKER_TOKEN>" | sudo docker login -u abdulbakitopcu --password-stdin

# Configure NVIDIA Runtime
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Pull & Run
git clone https://<YOUR_GITHUB_TOKEN>@github.com/TopcuAbdulbaki/Bitirme.git
cd Bitirme
sudo docker build -f llm/Dockerfile -t abdulbakitopcu/llm:latest .
sudo docker push abdulbakitopcu/llm:latest
sudo docker run -d --name llm \
  --gpus all \
  --restart unless-stopped \
  -e ORCHESTRATOR_HOST=<ORCH_IP> \
  -e ORCHESTRATOR_PORT=<ORCH_PORT> \
  -e MODEL_MODE=transformers \
  abdulbakitopcu/llm:latest

# Verify
sudo docker logs llm -f
```
