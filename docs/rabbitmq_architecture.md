# RabbitMQ Queue Architecture

## Overview
RabbitMQ handles async task distribution between Orchestrator and worker nodes (VLM, LLM). This enables scaling by adding multiple workers.

**Location:** RabbitMQ runs on the same machine as Orchestrator.

## Queue Structure (Star Topology)

**All data flows through Orchestrator - nodes never communicate directly.**

```
                        ★ ORCHESTRATOR ★
                    (RabbitMQ runs here)
                              │
         ┌────────────────────┼────────────────────┐
         │                    │                    │
         ▼                    ▼                    ▼
    ┌─────────┐          ┌─────────┐          ┌─────────┐
    │   DB    │          │   VLM   │          │   LLM   │
    └─────────┘          └─────────┘          └─────────┘
    (gRPC only)          (RabbitMQ)           (RabbitMQ)


    RabbitMQ Queues:
    ┌─────────────────────────────────────────────────────┐
    │                    ORCHESTRATOR                      │
    │                                                      │
    │  PUBLISH TO:              CONSUME FROM:              │
    │  ├── vlm_tasks    ◄────── vlm_results               │
    │  └── llm_tasks    ◄────── llm_results               │
    └─────────────────────────────────────────────────────┘
              │    │              ▲    ▲
              │    │              │    │
              ▼    │              │    │
         vlm_tasks │         vlm_results
              │    │              │    │
              ▼    │              │    │
         ┌────────────┐           │    │
         │    VLM     │───────────┘    │
         └────────────┘                │
                   │                   │
                   ▼                   │
              llm_tasks                │
                   │                   │
                   ▼                   │
         ┌────────────┐                │
         │    LLM     │────────────────┘
         └────────────┘
```

## Queues

| Queue Name | Publisher | Consumer | Message Content |
|------------|-----------|----------|-----------------|
| `vlm_tasks` | Orchestrator | VLM | News item with images to analyze |
| `vlm_results` | VLM | Orchestrator | Image analysis results |
| `llm_tasks` | Orchestrator | LLM | News item + VLM results |
| `llm_results` | LLM | Orchestrator | Final analysis (summary, sentiment) |

## Message Formats

### vlm_tasks
```json
{
    "task_id": "uuid",
    "news_id": "a3f2b8c9e1d4f5a6",
    "url": "https://...",
    "content": "Article text...",
    "media": {
        "main_image": "https://...",
        "content_images": ["..."],
        "videos": []
    }
}
```

### vlm_results
```json
{
    "task_id": "uuid",
    "news_id": "a3f2b8c9e1d4f5a6",
    "status": "success",
    "image_analyses": [
        {
            "image_url": "https://...",
            "description": "Image shows...",
            "objects_detected": ["person", "flag"],
            "sentiment": "neutral"
        }
    ]
}
```

### llm_tasks
```json
{
    "task_id": "uuid",
    "news_id": "a3f2b8c9e1d4f5a6",
    "content": "Article text...",
    "vlm_analysis": { ... }
}
```

### llm_results
```json
{
    "task_id": "uuid",
    "news_id": "a3f2b8c9e1d4f5a6",
    "status": "success",
    "summary": "Short summary of the article...",
    "sentiment": 1,  // -1, 0, 1
    "keywords": ["iran", "turkey", "politics"],
    "entities": ["Iran", "Turkey"]
}
```

## Processing Flow (Star Topology)

**All communication goes through Orchestrator:**

```
1. Crawler ──batch──► Orchestrator
2. Orchestrator ──store+getID──► DB (gRPC)
3. DB ──batch with IDs──► Orchestrator (gRPC)
4. Orchestrator ──publish──► vlm_tasks (RabbitMQ)
5. VLM ──consume──► vlm_tasks
6. VLM ──publish──► vlm_results (back to Orchestrator)
7. Orchestrator ──consume──► vlm_results
8. Orchestrator ──publish──► llm_tasks (with VLM results included)
9. LLM ──consume──► llm_tasks
10. LLM ──publish──► llm_results (back to Orchestrator)
11. Orchestrator ──consume──► llm_results
12. Orchestrator ──store final──► DB (gRPC)
```

## RabbitMQ Setup

### Requirements (each node)
```
pika>=1.3.0
```

### Connection (example)
```python
import pika

connection = pika.BlockingConnection(
    pika.ConnectionParameters(
        host='rabbitmq-server-ip',
        port=5672,
        credentials=pika.PlainCredentials('user', 'password')
    )
)
channel = connection.channel()

# Declare queues
channel.queue_declare(queue='vlm_tasks', durable=True)
channel.queue_declare(queue='vlm_results', durable=True)
channel.queue_declare(queue='llm_tasks', durable=True)
channel.queue_declare(queue='llm_results', durable=True)
```

## Scaling

Multiple VLM or LLM nodes can consume from the same queue:

```
                    ┌─────────┐
                    │  VLM 1  │
vlm_tasks ─────────►│         │────► vlm_results
    │               └─────────┘         ▲
    │               ┌─────────┐         │
    └──────────────►│  VLM 2  │─────────┘
                    └─────────┘

RabbitMQ automatically load-balances between workers.
```

## Node Responsibilities

| Node | gRPC | RabbitMQ |
|------|------|----------|
| Orchestrator | Server (receives from nodes) | Publisher + Consumer |
| Crawler | Client (sends to Orch) | None |
| DB | Client (sends to Orch) | None |
| VLM | Client (heartbeat to Orch) | Consumer + Publisher |
| LLM | Client (heartbeat to Orch) | Consumer + Publisher |
