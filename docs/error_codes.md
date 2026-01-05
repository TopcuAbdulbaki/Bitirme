# Error Codes

Standardized error codes across all nodes for consistent error handling and logging.

## Error Code Format

```
{NODE}_{CATEGORY}_{ERROR}
```

**Example:** `CRAWLER_NET_TIMEOUT` = Crawler node, Network category, Timeout error

---

## Error Categories

| Category | Code | Description |
|----------|------|-------------|
| NET | 1xx | Network errors |
| PROC | 2xx | Processing errors |
| DATA | 3xx | Data validation errors |
| SYS | 4xx | System errors |
| AUTH | 5xx | Authentication errors |

---

## Orchestrator Errors (ORCH_)

| Code | Name | Description | Action |
|------|------|-------------|--------|
| ORCH_NET_101 | NODE_UNREACHABLE | Cannot reach a node | Retry 3x with 5s backoff, then mark node offline |
| ORCH_NET_102 | GRPC_TIMEOUT | gRPC call timed out | Retry 3x with exponential backoff (2s, 4s, 8s) |
| ORCH_NET_103 | RABBITMQ_CONN_FAILED | Cannot connect to RabbitMQ | Attempt restart, alert admin if fails |
| ORCH_PROC_201 | QUEUE_FULL | RabbitMQ queue is full | Wait 10s, retry 3x, then alert admin |
| ORCH_PROC_202 | INVALID_NODE_TYPE | Unknown node type in registration | Reject registration, log warning |
| ORCH_DATA_301 | INVALID_JSON | Malformed JSON received | Log error with payload sample, skip item |
| ORCH_DATA_302 | MISSING_REQUIRED_FIELD | Required field missing | Log missing field name, skip item |
| ORCH_SYS_401 | OUT_OF_MEMORY | System memory exhausted | Alert admin immediately |
| ORCH_AUTH_501 | INVALID_NODE_ID | Node ID not recognized | Reject request, require re-registration |

---

## Crawler Errors (CRAWLER_)

| Code | Name | Description | Action |
|------|------|-------------|--------|
| CRAWLER_NET_101 | URL_UNREACHABLE | Cannot reach target URL | Skip URL, log as unreachable |
| CRAWLER_NET_102 | CONNECTION_TIMEOUT | HTTP request timed out | Retry 1x only, then skip URL |
| CRAWLER_NET_103 | SSL_ERROR | SSL certificate error | Skip URL, log SSL error |
| CRAWLER_NET_104 | RATE_LIMITED | Server returned 429 | Wait 60s, retry 3x, then skip URL for this batch |
| CRAWLER_PROC_201 | PARSE_ERROR | Cannot parse HTML | Log error, skip URL |
| CRAWLER_PROC_202 | NO_CONTENT | Page has no extractable content | Skip URL (see detection rules below) |
| CRAWLER_DATA_301 | INVALID_URL | Malformed URL | Skip URL |
| CRAWLER_SYS_401 | BROWSER_CRASH | Headless browser crashed | Restart browser, retry current batch |

### NO_CONTENT Detection Rules

A page is considered "no content" when:
- `content` field is empty or whitespace only
- `content` length < 100 characters after stripping HTML
- Only contains navigation/menu text
- Page returns 404 or error page content

---

## Database Errors (DB_)

| Code | Name | Description | Action |
|------|------|-------------|--------|
| DB_NET_101 | PG_CONN_FAILED | Cannot connect to PostgreSQL | Retry 3x with 5s intervals, alert admin if fails |
| DB_NET_102 | MINIO_CONN_FAILED | Cannot connect to MinIO | Retry 3x, alert admin if fails |
| DB_PROC_201 | DUPLICATE_ENTRY | URL already exists | Skip silently (expected behavior, not an error) |
| DB_PROC_202 | VECTORIZATION_FAILED | Embedding model failed | Retry 3x, if still fails: store without vector, mark for retry later |
| DB_PROC_203 | QUEUE_EMPTY | No items in processing queue | Return empty response (normal operation) |
| DB_PROC_204 | IMAGE_DOWNLOAD_FAILED | Cannot download image from URL | Retry 2x, if still fails: store news without image |
| DB_PROC_205 | MINIO_UPLOAD_FAILED | Cannot upload to MinIO | Retry 3x, alert admin if fails |
| DB_DATA_301 | INVALID_NEWS_ID | Invalid news_id format | Reject item, log error |
| DB_DATA_302 | CONTENT_TOO_LARGE | Content exceeds 50KB limit | Truncate to 50KB, store truncated version |
| DB_DATA_303 | IMAGE_TOO_LARGE | Image exceeds 10MB limit | Skip image, log warning |
| DB_SYS_401 | DISK_FULL | Database disk full | Alert admin immediately, reject new writes |
| DB_SYS_402 | MINIO_STORAGE_FULL | MinIO storage full (100GB) | Alert admin, reject new images |

---

## VLM Errors (VLM_)

> **Note:** LM Studio is for local prototype only. Production uses Transformers library directly.

| Code | Name | Description | Action |
|------|------|-------------|--------|
| VLM_NET_101 | IMAGE_UNREACHABLE | Cannot download image | Skip this image, continue with others |
| VLM_NET_102 | MODEL_BACKEND_OFFLINE | Model backend not responding (LM Studio/Transformers) | Retry 3x with 10s intervals, alert admin |
| VLM_PROC_201 | IMAGE_CORRUPT | Cannot decode image | Skip this image, log error |
| VLM_PROC_202 | MODEL_INFERENCE_FAILED | Model returned error | Retry 3x, if still fails: skip item, report to Orchestrator |
| VLM_PROC_203 | ANALYSIS_TIMEOUT | Analysis took too long | Return completed images only (see partial results) |
| VLM_DATA_301 | UNSUPPORTED_FORMAT | Image format not supported (only jpg, png, webp) | Skip this image |
| VLM_SYS_401 | GPU_OOM | GPU out of memory | Clear GPU cache, reduce batch to 1, retry |
| VLM_SYS_402 | MODEL_NOT_LOADED | Model not loaded in memory | Load model, then process |

### VLM Partial Results

When timeout occurs, return analysis for images completed before timeout:
```json
{
    "partial": true,
    "completed_images": 3,
    "total_images": 5,
    "images": [ ... 3 completed analyses ... ]
}
```

---

## LLM Errors (LLM_)

> **Note:** LM Studio is for local prototype only. Production uses Transformers library directly.
> Models are downloaded locally - no external API calls.

| Code | Name | Description | Action |
|------|------|-------------|--------|
| LLM_NET_101 | MODEL_BACKEND_OFFLINE | Model backend not responding (LM Studio/Transformers) | Retry 3x with 10s intervals, alert admin |
| LLM_PROC_201 | MODEL_INFERENCE_FAILED | Model returned error | Retry 3x, if still fails: skip item, report to Orchestrator |
| LLM_PROC_202 | ANALYSIS_TIMEOUT | Analysis took too long | Return partial result (see below) |
| LLM_PROC_203 | INVALID_OUTPUT | Model output not parseable as JSON | Retry 2x with stricter prompt, then skip |
| LLM_DATA_301 | CONTENT_TOO_LONG | Text exceeds context limit | Truncate to fit context window |
| LLM_SYS_401 | GPU_OOM | GPU out of memory | Clear GPU cache, reduce batch to 1, retry |
| LLM_SYS_402 | MODEL_NOT_LOADED | Model not loaded in memory | Load model, then process |

### LLM Partial Results

When timeout occurs mid-analysis:
```json
{
    "partial": true,
    "summary": "Generated summary if available, otherwise null",
    "sentiment": null,
    "reason": "Analysis timeout after 180 seconds"
}
```
Orchestrator decides: retry later or store as incomplete.

---

## Error Response Format

All errors returned to Orchestrator should follow this format:

```json
{
    "success": false,
    "error": {
        "code": "VLM_PROC_202",
        "name": "MODEL_INFERENCE_FAILED",
        "message": "Model returned error: CUDA out of memory",
        "timestamp": "2025-12-28T14:00:00.000000",
        "recoverable": true,
        "retry_count": 2,
        "partial_result": null
    }
}
```

| Field | Type | Description |
|-------|------|-------------|
| code | string | Error code |
| name | string | Error name |
| message | string | Human-readable description with details |
| timestamp | ISO8601 | When error occurred |
| recoverable | bool | Can operation be retried? |
| retry_count | int | How many retries already attempted |
| partial_result | object/null | Any partial data if available |

---

## Timeout Configurations

| Node | Operation | Timeout | Max Retries | After Max Retries |
|------|-----------|---------|-------------|-------------------|
| Crawler | HTTP request | 30s | 1 | Skip URL |
| Crawler | Page render | 60s | 1 | Skip URL |
| DB | Query | 15s | 3 | Alert admin |
| DB | Vectorization | 45s | 3 | Store without vector |
| VLM | Image analysis | 90s | 2 | Return partial |
| LLM | Text analysis | 180s | 2 | Return partial |
| Orchestrator | gRPC call | 30s | 3 | Mark node offline |
| Orchestrator | Heartbeat | 10s | 3 | Mark node offline |
