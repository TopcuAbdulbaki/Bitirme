# PostgreSQL Database Schema

Schema for PostgreSQL with pgvector extension.

---

## pgvector Setup

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;
```

---

## Tables

### news (Main table)

```sql
CREATE TABLE news (
    news_id VARCHAR(16) PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,
    source VARCHAR(100),
    country VARCHAR(50),
    keyword_found VARCHAR(100),
    scraped_at TIMESTAMP,
    stored_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    content TEXT,
    
    -- MinIO paths
    main_image_minio TEXT,
    content_images_minio TEXT[],  -- Array of MinIO paths
    
    -- Processing status
    vlm_processed BOOLEAN DEFAULT FALSE,
    llm_processed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMP,
    
    -- Vector embedding (for semantic search)
    content_embedding vector(1024)  -- Qwen3-Embedding-0.6B dimension
);

-- Index for fast duplicate checking
CREATE INDEX idx_news_url ON news(url);

-- Index for vector similarity search
CREATE INDEX idx_news_embedding ON news 
USING ivfflat (content_embedding vector_cosine_ops)
WITH (lists = 100);
```

### vlm_analysis

```sql
CREATE TABLE vlm_analysis (
    id SERIAL PRIMARY KEY,
    news_id VARCHAR(16) REFERENCES news(news_id),
    image_minio_path TEXT,
    description TEXT,
    objects TEXT[],
    sentiment VARCHAR(20),
    relevance VARCHAR(20),
    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_vlm_news_id ON vlm_analysis(news_id);
```

### llm_analysis

```sql
CREATE TABLE llm_analysis (
    news_id VARCHAR(16) PRIMARY KEY REFERENCES news(news_id),
    summary TEXT,
    sentiment INTEGER CHECK (sentiment IN (-1, 0, 1)),
    sentiment_label VARCHAR(20),
    keywords TEXT[],
    entities JSONB,  -- {"countries": [], "organizations": [], "people": []}
    category VARCHAR(50),
    relevance_to_topic VARCHAR(20),
    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Common Queries

### Insert new news item

```sql
INSERT INTO news (news_id, url, source, country, keyword_found, scraped_at, content)
VALUES ($1, $2, $3, $4, $5, $6, $7)
ON CONFLICT (url) DO NOTHING
RETURNING news_id;
```

### Get unprocessed items (queue)

```sql
SELECT * FROM news 
WHERE vlm_processed = FALSE 
ORDER BY stored_at 
LIMIT 10;
```

### Semantic search (vector similarity)

```sql
SELECT news_id, content, summary, sentiment_label,
       1 - (content_embedding <=> $1::vector) AS similarity
FROM news
JOIN llm_analysis USING (news_id)
WHERE llm_processed = TRUE
ORDER BY content_embedding <=> $1::vector
LIMIT 10;
```

### Get negative news about topic

```sql
SELECT n.*, l.summary, l.sentiment_label
FROM news n
JOIN llm_analysis l ON n.news_id = l.news_id
WHERE l.sentiment = -1
  AND n.keyword_found = 'turkey'
ORDER BY n.scraped_at DESC
LIMIT 20;
```

---

## Embedding Generation

Using Qwen3-Embedding-0.6B:

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('Qwen/Qwen3-Embedding-0.6B')

def generate_embedding(text: str) -> list:
    embedding = model.encode(text)
    return embedding.tolist()  # 1024-dim vector
```

---

## Python Connection (asyncpg)

```python
import asyncpg
import numpy as np

async def get_connection():
    return await asyncpg.connect(
        host='10.0.0.3',  # DB node VPN IP
        port=5432,
        database='news_db',
        user='news_user',
        password='your_password'
    )

async def insert_news(conn, news_data: dict) -> str:
    return await conn.fetchval("""
        INSERT INTO news (news_id, url, source, country, keyword_found, scraped_at, content)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        ON CONFLICT (url) DO NOTHING
        RETURNING news_id
    """, news_data['news_id'], news_data['url'], ...)

async def search_similar(conn, query_embedding: list, limit: int = 10):
    return await conn.fetch("""
        SELECT news_id, content, 
               1 - (content_embedding <=> $1::vector) AS similarity
        FROM news
        WHERE content_embedding IS NOT NULL
        ORDER BY content_embedding <=> $1::vector
        LIMIT $2
    """, query_embedding, limit)
```

---

## Requirements

```
asyncpg>=0.29.0
pgvector>=0.2.0
sentence-transformers>=2.2.0
```
