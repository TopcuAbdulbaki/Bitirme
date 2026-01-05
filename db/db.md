PostgreSQL + pgvector + MinIO

Responsible for storing all data. Runs on a stable VPS with persistent storage.

## Components

| Component | Purpose |
|-----------|---------|
| PostgreSQL | News metadata, analysis results |
| pgvector | Vector embeddings for semantic search |
| MinIO | Image/video storage (100GB limit) |

## Technology Stack
- Python 3.13.5
- asyncio for async operations
- LangChain for embeddings  
- qwen3 embedding model for vectorization
- gRPC for communication with Orchestrator

Node Name: "DB"
Node ID: (assigned by Orchestrator)

## Responsibilities

1. **Receive data from Orchestrator** (via gRPC)
2. **Check for duplicates** using news_id (hash of URL)
3. **Store images to MinIO** → get MinIO paths
4. **Store news metadata to PostgreSQL** with MinIO links
5. **Generate vector embeddings** for semantic search
6. **Provide image bytes** when VLM requests via Orchestrator
7. **Store final analysis results** from LLM

## Data Storage

### PostgreSQL Tables
- `news` - News metadata, content, MinIO links
- `vlm_analysis` - Image analysis results
- `llm_analysis` - Text analysis, sentiment, summary
- `embeddings` - Vector embeddings (pgvector)

### MinIO Structure
```
news-media/                    ← Bucket
├── {news_id}/                 ← Folder per news item
│   ├── main.jpg
│   ├── content_0.jpg
│   └── content_1.png
```

## Ports
| Port | Service |
|------|---------|
| 5432 | PostgreSQL |
| 9000 | MinIO API |
| 9001 | MinIO Console |
| 50052 | gRPC (DB service) |

## See Also
- `docs/minio_storage.md` - MinIO setup guide
- `docs/json_schemas.md` - Data structure at each stage
