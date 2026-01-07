# Vast.ai Deployment Guide

This guide details how to deploy the distributed system on Vast.ai using Docker.

## 1. Prerequisites

- **Docker Desktop** installed and running locally.
- **Docker Hub** account.
- **Vast.ai** account with credits.
- **Vast.ai CLI** (optional but recommended) or Web UI.

## 2. Docker Image Preparation (Local)

You need to build and push images for all 5 nodes.

## 2. Docker Image Preparation

### Option A: Hybrid Build (Recommended)
Build light images locally, and heavy images on Vast.ai to save bandwidth.

**1. Build & Push Light Images (Local)**
```powershell
# Orchestrator
docker build -f orchestrator/Dockerfile -t abdulbakitopcu/orchestrator:latest .
docker push abdulbakitopcu/orchestrator:latest

# Crawler
docker build -f crawler/Dockerfile -t abdulbakitopcu/crawler:latest .
docker push abdulbakitopcu/crawler:latest
```

**2. Build Heavy Images (On Vast.ai)**
*These images (DB, VLM, LLM) are huge (5GB+). Building them locally and uploading is slow.*

**Step A: Launch Instance**
1. Launch your Vast.ai instance (Ubuntu/Cuda).
2. Get the SSH command (e.g., `ssh -p 12345 root@1.2.3.4`).

**Step B: Copy Code (The Easy Way: Git)**

1. **On your PC**: Push your code to GitHub.
   ```powershell
   git add .
   git commit -m "Ready for deployment"
   git push origin main
   ```

2. **On Vast.ai** (SSH Terminal):
   ```bash
   # Clone your repo (it contains all folders: db/, vlm/, llm/)
   git clone https://github.com/your-username/bitirme.git
   cd bitirme
   ```

*(Alternative: You can use `scp` if you don't want to use GitHub, but it's trickier on Windows).*

**Step C: Build & Push (Save for later)**
SSH into the server and run:
```bash
# 1. Login to Docker Hub (One time)
docker login

# 2. Build & Push Database
docker build -f db/Dockerfile -t abdulbakitopcu/db:latest .
docker push abdulbakitopcu/db:latest

# 3. Build & Push VLM (If this is the GPU machine)
docker build -f vlm/Dockerfile -t abdulbakitopcu/vlm:latest .
docker push abdulbakitopcu/vlm:latest
```
*Now these images are saved in your account! You can pull them on ANY machine without rebuilding.*


## 3. Vast.ai Instance Selection

You will need **multiple instances** (or one large instance if testing all together, though distributed is preferred).

### Recommended Specs per Node

| Node | Type | CPU | RAM | GPU | Disk |
|------|------|-----|-----|-----|------|
| **Orchestrator** | CPU-Only | 1 core | 2GB | None | 10GB |
| **Crawler** | CPU-Only | 2 cores | 4GB | None | 10GB |
| **Database** | CPU-Only | 2 cores | 4GB | None | 20GB+ |
| **VLM** | GPU | 4 cores | 16GB | 1x RTX 3090/4090 (24GB VRAM) | 40GB |
| **LLM** | GPU | 4 cores | 16GB | 1x RTX 3090/4090 (24GB VRAM) | 40GB |

*Note: For VLM/LLM, ensure the instance supports CUDA 12.1+.*

## 4. Deployment Configuration (On Launch)

When launching an instance on Vast.ai, use the **"Edit Image & Config"** button.

### 4.1. Orchestrator
- **Image**: `abdulbakitopcu/orchestrator:latest`
- **Docker Options**: `-p 50051:50051 -p 5672:5672`
- **On-Start Script**: None req.

### 4.2. Database Node
- **Image**: `abdulbakitopcu/db:latest`
- **Env Variables**:
    - `ORCHESTRATOR_HOST`: `<Orchestrator-Public-IP>`
    - `ORCHESTRATOR_PORT`: `50051`
- **Ports**: `-p 50053:50053 -p 5432:5432 -p 9000:9000`

### 4.3. Other Nodes (Crawler, VLM, LLM)
- **Image**: Corresponding image name (e.g. `abdulbakitopcu/crawler:latest`).
- **Env Variables**:
    - `ORCHESTRATOR_HOST`: `<Orchestrator-Public-IP>`
    - `ORCHESTRATOR_PORT`: `50051`
- **Ports**: Use default ports if needed (mostly internal/outgoing).
    - Crawler: Exposes `50052` (optional, for direct checks).

## 5. Networking (WireGuard)

Vast.ai instances are behind NAT.
- **Option A (Public IP)**: Rent instances with open public ports (more expensive).
- **Option B (WireGuard)**: Use internal IPs (172.x.x.x) if all nodes are in the *same* datacenter/VPC (hard on Vast).
- **Option C (Project Standard)**: We configured `GRPC_HOST` and `ORCHESTRATOR_HOST` to use the Public IP provided by Vast.ai + Port Forwarding.
    - **Important**: When you rent an instance, Vast.ai gives you a **Public IP** and a **Port Mapping** (e.g., 50051 might map to 12345).
    - You must set `GRPC_PORT` inside the container to match the internal port, but tell *other* nodes to connect to `PublicIP:ExternalPort`.

## 6. Verification

1. Check logs:
   ```bash
   docker logs <container-id> -f
   ```
2. Look for `[NodeRegistry] Registered node: <ID>` on the Orchestrator.
