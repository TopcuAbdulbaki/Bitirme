# Project Handoff: Root Directory & System Architecture

This document provides a high-level overview of the **Bitirme** (Graduation Project) repository, detailing the system architecture, directory structure, and instructions for operation.

## 🏗️ System Architecture: Star Topology

The system is designed as a distributed multi-node architecture using a **Star Topology**.

*   **Central Hub**: `Orchestrator`
*   **Satellite Nodes**: `Crawler`, `DB`, `VLM`, `LLM`

All communication between nodes is handled via **gRPC**. The Orchestrator acts as the "brain," managing task distribution and node synchronization, while the satellite nodes perform specialized tasks.

---

## 📂 Directory Structure & File Analysis

### 1. 📂 `orchestrator/`
The central manager of the system.
*   `main.py`: Entry point for the gRPC server.
*   `services/`: Business logic for task management and node coordination.
*   `proto/` & `generated/`: gRPC definitions and auto-generated Python code.
*   **Key Function**: Orchestrates the flow from Crawling -> DB -> VLM -> LLM -> Final Storage.

### 2. 📂 `crawler/`
Responsible for web scraping and content discovery.
*   `FilteredCrawler.py`: The main scraping logic with filtering capabilities.
*   `docker-compose.yml`: For local crawler testing.
*   **Key Function**: Collects news and image URLs, submitting them to the Orchestrator.

### 3. 📂 `db/`
The persistent storage and vector database layer.
*   **PostgreSQL (pgvector)**: Stores news metadata and allows vector similarity searches.
*   **MinIO**: Object storage for downloaded images.
*   `main.py`: The gRPC node that interfaces with SQL and MinIO.
*   **Key Function**: Handles image persistence and metadata indexing.

### 4. 📂 `vlm/` (Vision Language Model)
The image analysis engine.
*   `main.py`: Node logic for processing image analysis requests.
*   `models/`: Logic for loading and running vision models (e.g., Transformers-based).
*   **Key Function**: Converts image bytes into descriptive text or structured insights.

### 5. 📂 `llm/` (Large Language Model)
The text analysis and reasoning engine.
*   `main.py`: Node logic for text processing.
*   `prompts/`: Managed templates for various tasks (summary, sentiment, etc.).
*   **Key Function**: Synthesizes crawler text and VLM results into a final report.

### 6. 📂 `proto/`
The single source of truth for communication.
*   `orchestrator.proto`: Defines all RPC methods and message types used across the entire system.

### 7. 📂 `docs/`
Extensive technical documentation:
*   `deployment_commands.md`: Full setup instructions for Vast.ai/Linux.
*   `database_schema.md`: Details the PostgreSQL tables and MinIO structure.
*   `grpc_guide.md`: Protocol buffer integration details.
*   `local_dev_guide.md`: Quick-start for local development.

---

## 🛠️ Key Project Scripts (Root)

| Script | Description |
| :--- | :--- |
| `compile_proto.py` | **CRITICAL**: Compiles `.proto` files into all node directories and fixes relative imports. Run this after any proto changes. |
| `run_local.py` | Local pipeline runner that starts the Orchestrator and Crawler for testing. |
| `check_db.py` | Verifies database connectivity and structure. |
| `test_system.py` | Integration test script to verify the full flow (Crawler to LLM). |
| `docker-compose.yml` | Sets up the entire system (all nodes + databases) locally. |

---

## ⚡ Key Point & Implementation Logic

1.  **gRPC Handshake**: Nodes must register with the Orchestrator upon startup. The Orchestrator assigns a unique `node_id`.
2.  **Distributed Design**: Every folder has its own `requirements.txt` and `Dockerfile`, allowing them to run on completely separate hardware (e.g., Crawler on a cheap CPU VM, VLM/LLM on RTX 3090/4090s).
3.  **Vector Search Integration**: The DB node uses `pgvector`, enabling future "semantic search" capabilities across found news.
4.  **MinIO Image Pipeline**: Images are never sent directly between all nodes as raw bytes; they are stored in MinIO by the DB node, and other nodes access them via paths/streaming.

---

## 🚀 Quick Execution Commands

### 1. Prepare Environment (Proto Compilation)
```bash
python compile_proto.py
```

### 2. Run Locally (Orchestrator + Crawler)
```bash
python run_local.py
```

### 3. Full System Deployment (Docker)
```bash
docker-compose up --build
```

---
> [!NOTE]
> Detailed handoff documents for individual modules can be found inside each module's directory (e.g., `vlm/handoff_vlm.md`).
