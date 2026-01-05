# JSON Data Schemas

This document defines the JSON structure at each stage of the news processing pipeline.

## Data Flow Overview

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  RAW     │───►│  STORED  │───►│   VLM    │───►│   LLM    │───►│  FINAL   │
│ (Crawler)│    │  (DB)    │    │ (Orch)   │    │ (Orch)   │    │  (DB)    │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
```

---

## Stage 1: Raw Crawler Output

**Source:** Crawler → Orchestrator

Crawler sends URLs only. DB node downloads images later.

```json
{
    "source": "Iran International",
    "country": "iran",
    "url": "https://www.iranintl.com/en/202512279680",
    "keyword_found": "turkey",
    "scraped_at": "2025-12-27T15:33:39.912892",
    "content": "Iranian security and law enforcement forces prevented...",
    "media": {
        "main_image": "https://example.com/image.jpg",
        "content_images": [
            "https://example.com/image1.jpg",
            "https://example.com/image2.jpg"
        ],
        "videos": []
    }
}
```

| Field | Type | Description |
|-------|------|-------------|
| source | string | News source name |
| country | string | Country of the news source |
| url | string | Original article URL |
| keyword_found | string | Search keyword that matched |
| scraped_at | ISO8601 | Timestamp when crawled |
| content | string | Article text content |
| media.main_image | string | Primary image URL |
| media.content_images | array[string] | Additional image URLs |
| media.videos | array[string] | Video URLs |

---

## Stage 2: Stored in DB (with ID + MinIO paths)

**Source:** Orchestrator → DB → Orchestrator

Images are saved to MinIO, paths stored in PostgreSQL.

```json
{
    "news_id": "a3f2b8c9e1d4f5a6",
    "source": "Iran International",
    "country": "iran",
    "url": "https://www.iranintl.com/en/202512279680",
    "keyword_found": "turkey",
    "scraped_at": "2025-12-27T15:33:39.912892",
    "stored_at": "2025-12-27T15:34:00.000000",
    "content": "Iranian security and law enforcement forces prevented...",
    "media": {
        "main_image": {
            "original_url": "https://example.com/image.jpg",
            "minio_path": "minio://news-media/a3f2b8c9e1d4f5a6/main.jpg"
        },
        "content_images": [
            {
                "original_url": "https://example.com/image1.jpg",
                "minio_path": "minio://news-media/a3f2b8c9e1d4f5a6/content_0.jpg"
            }
        ],
        "videos": []
    },
    "processing_status": {
        "vlm_processed": false,
        "llm_processed": false
    }
}
```

| New Field | Type | Description |
|-----------|------|-------------|
| news_id | string | SHA256 hash of URL (16 chars) |
| stored_at | ISO8601 | Timestamp when stored |
| media.*.minio_path | string | MinIO storage path |
| processing_status | object | Tracks analysis progress |

---

## Stage 3: After VLM Analysis

**Source:** Orchestrator (after VLM result)

```json
{
    "news_id": "a3f2b8c9e1d4f5a6",
    "source": "Iran International",
    "country": "iran",
    "url": "https://www.iranintl.com/en/202512279680",
    "keyword_found": "turkey",
    "scraped_at": "2025-12-27T15:33:39.912892",
    "stored_at": "2025-12-27T15:34:00.000000",
    "content": "Iranian security and law enforcement forces prevented...",
    "media": {
        "main_image": "https://example.com/image.jpg",
        "content_images": [...],
        "videos": []
    },
    "vlm_analysis": {
        "analyzed_at": "2025-12-27T15:35:00.000000",
        "images": [
            {
                "url": "https://example.com/image.jpg",
                "description": "A group of people gathered outside a building",
                "objects": ["people", "building", "protest signs"],
                "sentiment": "negative",
                "relevance": "high"
            },
            {
                "url": "https://example.com/image1.jpg",
                "description": "Close-up of security forces",
                "objects": ["police", "uniforms"],
                "sentiment": "neutral",
                "relevance": "medium"
            }
        ]
    },
    "processing_status": {
        "vlm_processed": true,
        "llm_processed": false
    }
}
```

| VLM Fields | Type | Description |
|------------|------|-------------|
| vlm_analysis.analyzed_at | ISO8601 | When VLM processed |
| vlm_analysis.images[].url | string | Image that was analyzed |
| vlm_analysis.images[].description | string | VLM description of image |
| vlm_analysis.images[].objects | array[string] | Detected objects |
| vlm_analysis.images[].sentiment | string | Image sentiment |
| vlm_analysis.images[].relevance | string | Relevance to article |

---

## Stage 4: Final (After LLM Analysis)

**Source:** Orchestrator → DB (final storage)

```json
{
    "news_id": "a3f2b8c9e1d4f5a6",
    "source": "Iran International",
    "country": "iran",
    "url": "https://www.iranintl.com/en/202512279680",
    "keyword_found": "turkey",
    "scraped_at": "2025-12-27T15:33:39.912892",
    "stored_at": "2025-12-27T15:34:00.000000",
    "content": "Iranian security and law enforcement forces prevented...",
    "media": {
        "main_image": "https://example.com/image.jpg",
        "content_images": [...],
        "videos": []
    },
    "vlm_analysis": {
        "analyzed_at": "2025-12-27T15:35:00.000000",
        "images": [...]
    },
    "llm_analysis": {
        "analyzed_at": "2025-12-27T15:36:00.000000",
        "summary": "Iranian authorities blocked families from mourning executed political prisoners. Security forces dispersed the gathering outside the prison.",
        "sentiment": -1,
        "sentiment_label": "negative",
        "keywords": ["iran", "political prisoners", "execution", "protest"],
        "entities": {
            "countries": ["Iran"],
            "organizations": ["Iranian security forces"],
            "people": []
        },
        "category": "politics",
        "relevance_to_topic": "low"
    },
    "processing_status": {
        "vlm_processed": true,
        "llm_processed": true,
        "completed_at": "2025-12-27T15:36:00.000000"
    }
}
```

| LLM Fields | Type | Description |
|------------|------|-------------|
| llm_analysis.analyzed_at | ISO8601 | When LLM processed |
| llm_analysis.summary | string | Short summary of article |
| llm_analysis.sentiment | int | -1 (neg), 0 (neutral), 1 (pos) |
| llm_analysis.sentiment_label | string | Human-readable sentiment |
| llm_analysis.keywords | array[string] | Extracted keywords |
| llm_analysis.entities | object | Named entities extracted |
| llm_analysis.category | string | Article category |
| llm_analysis.relevance_to_topic | string | How relevant to Turkey |

---

## ID Generation Function

```python
import hashlib

def generate_news_id(url: str) -> str:
    """Generate unique news ID from URL."""
    return hashlib.sha256(url.encode()).hexdigest()[:16]
```

---

## Validation Notes

- All timestamps use ISO8601 format
- `news_id` is always 16 characters (hex)
- `sentiment` integer: -1, 0, or 1 only
- Empty arrays `[]` preferred over `null`
- Missing optional fields should be omitted, not null
