# Local Development Guide

## Quick Start (Minimal Setup)

Run the basic pipeline without external dependencies:

### Step 1: Start Orchestrator
```bash
# Terminal 1
cd c:\Users\HP\Desktop\Projeler\Bitirme
python -m orchestrator.main
```

### Step 2: Start Crawler in Distributed Mode
```bash
# Terminal 2
cd c:\Users\HP\Desktop\Projeler\Bitirme\crawler
set CRAWLER_MODE=distributed
python FilteredCrawler.py
```

---

## Full Pipeline (All Components)

### Prerequisites

1. **PostgreSQL** - For news storage
2. **MinIO** - For image storage  
3. **LM Studio** - For VLM/LLM inference

### Step-by-Step Setup

#### 1. Install Dependencies (each node)
```bash
# From project root
pip install -r orchestrator/requirements.txt
pip install -r db/requirements.txt
pip install -r vlm/requirements.txt
pip install -r llm/requirements.txt
pip install -r crawler/requirements.txt
```

#### 2. Start PostgreSQL + MinIO (Docker)
```bash
# PostgreSQL
docker run -d --name postgres \
  -e POSTGRES_USER=news_user \
  -e POSTGRES_PASSWORD=news_password \
  -e POSTGRES_DB=news_db \
  -p 5432:5432 \
  pgvector/pgvector:pg16

# MinIO  
docker run -d --name minio \
  -e MINIO_ROOT_USER=admin \
  -e MINIO_ROOT_PASSWORD=admin123 \
  -p 9000:9000 -p 9001:9001 \
  minio/minio server /data --console-address ":9001"
```

#### 3. Start LM Studio
- Open LM Studio
- Load a Qwen model (e.g., `qwen3-vl-2b-instruct` for VLM)
- Start local server on port 1234

#### 4. Start All Nodes (4 terminals)

```bash
# Terminal 1: Orchestrator
python -m orchestrator.main

# Terminal 2: DB Node
python -m db.main

# Terminal 3: VLM Node
python -m vlm.main

# Terminal 4: LLM Node
python -m llm.main
```

#### 5. Run Crawler
```bash
# Terminal 5: Crawler
set CRAWLER_MODE=distributed
python -m crawler.FilteredCrawler
```

---

## Testing Without External Services

Run basic connectivity test:
```bash
python test_system.py
```

---

## Environment Variables

Create `.env` in project root:
```env
# Orchestrator
GRPC_HOST=0.0.0.0
GRPC_PORT=50051

# DB Node
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=news_db
POSTGRES_USER=news_user
POSTGRES_PASSWORD=news_password
MINIO_HOST=localhost
MINIO_PORT=9000

# VLM/LLM Nodes
LM_STUDIO_HOST=http://localhost:1234
MODEL_MODE=lmstudio

# Crawler
CRAWLER_MODE=distributed
```
