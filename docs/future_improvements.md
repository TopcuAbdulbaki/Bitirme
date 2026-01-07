# Future Improvements

Ideas and enhancements for future development.

---

## 🔴 Priority (from 2209.md)

### Database Storage Upgrade (URGENT)
- Currently limited to 10GB for demo purposes.
- Upgrade to 100GB persistent storage for production.
- Implement volume expansion strategy for MinIO and Postgres.

### Docker Compose Setup (URGENT)
- Create `docker-compose.yml` for local orchestration of all 5 nodes.
- Simplify local testing and development before pushing to Vast.ai.
- Ensure network aliases (`orchestrator`, `db`, etc.) match environment variables.

### FastAPI User Interface
Build a query interface prototype for searching and viewing analyzed news.
- Search by keyword, date range, sentiment
- Display summary, images, sentiment score
- Simple dashboard with statistics

### Social Media Crawling
Add support for X (Twitter) and Reddit data collection.
- Use official APIs or PRAW/Selenium for Reddit
- Handle rate limiting and authentication
- Parse social posts similar to news articles

### Translator Node
Handle non-English content translation before analysis.
- Translate to English before sending to LLM
- Or use multilingual Qwen3 capabilities directly
- Store original + translated content

### Context Management & Optimization
Optimize model context usage for better performance.
- Context window management for long articles
- Chunking strategies for large content
- Memory optimization for batch processing
- Token counting and truncation

---

## Storage Optimization

### Image Compression Before Storing
Compress images before saving to MinIO to reduce storage usage.

```python
from PIL import Image
import io

def compress_image(image_bytes: bytes, quality: int = 85) -> bytes:
    img = Image.open(io.BytesIO(image_bytes))
    output = io.BytesIO()
    img.save(output, format='JPEG', quality=quality, optimize=True)
    return output.getvalue()
```

### Automatic Cleanup of Old Data
Delete images older than X days when storage is running low.

```python
from datetime import datetime, timedelta

def cleanup_old_images(minio_client, days=90):
    cutoff = datetime.now() - timedelta(days=days)
    objects = minio_client.list_objects("news-media", recursive=True)
    for obj in objects:
        if obj.last_modified < cutoff:
            minio_client.remove_object("news-media", obj.object_name)
```

---

## Performance

### Batch Processing
Process multiple news items in parallel for faster throughput.

### Caching
Cache frequently accessed data in Redis for faster retrieval.

---

## Features

### User Authentication
Add user login/registration for personal dashboards.

### Custom Alerts
Notify users when specific keywords appear in negative news.

### Historical Trends
Visualize sentiment trends over time for specific topics.

---

## Model Improvements

### Fine-tuning
Fine-tune Qwen3 models on Turkish news data for better accuracy.

### Model Switching
Compare different model sizes (2B, 4B, 8B) and allow users to choose.

---

## Architecture & Deployment

### Restore Local/Standalone Mode
Currently, local fallback modes (Standalone Crawler, LM Studio) have been disabled to enforce a strict distributed architecture.
- Re-implement "Developer Mode" flags in `config.py`.
- allow running nodes individually without the Orchestrator for debugging.
- Add CLI arguments (e.g., `--local`) to override environment variables easily.

### Time or Event Triggering
Replace the current startup-trigger mechanism with a more robust scheduling system.
- **Time-based**: Use `APScheduler` or cron-jobs to run crawls at specific times (e.g., 08:00 AM daily).
- **Event-based**: Trigger crawls via external API calls (e.g., a "Start Crawl" button on a React Frontend).
- This allows the system to remain IDLE and conserve resources when not needed.
