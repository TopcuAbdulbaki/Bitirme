Responsible for image analysis using Vision Language Models. Python 3.13.5

## Models

| Environment | Model | Backend |
|-------------|-------|---------|
| Local/Prototype | qwen3-vl-2b-instruct | LM Studio (headless) |
| Production | Qwen3-VL-8B-Instruct | Transformers |

Huggingface: https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct

## Technology Stack
- asyncio for async operations
- LangChain for model interface
- RabbitMQ for task queue (consumes vlm_tasks, publishes vlm_results)
- gRPC for heartbeat to Orchestrator

Node Name: "VLM"
Node ID: (assigned by Orchestrator)

## Responsibilities

1. **Consume tasks from vlm_tasks queue** (RabbitMQ)
2. **Request image bytes from DB** (via Orchestrator)
3. **Analyze each image** using VLM
4. **Generate description, objects, sentiment** for each image
5. **Publish results to vlm_results queue**

## Output Format

For each image:
```json
{
    "url": "minio://news-media/a3f2/main.jpg",
    "description": "A group of people gathered outside a building",
    "objects": ["people", "building", "signs"],
    "sentiment": "negative",
    "relevance": "high"
}
```

## See Also
- `docs/rabbitmq_architecture.md` - Queue structure
- `docs/json_schemas.md` - Full data format