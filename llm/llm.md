Responsible for text analysis and final sentiment classification. Python 3.13.5

## Models

| Environment | Model | Backend |
|-------------|-------|---------|
| Local/Prototype | qwen3-vl-2b-instruct | LM Studio (headless) |
| Production | Qwen3-8B | Transformers |

Huggingface: https://huggingface.co/Qwen/Qwen3-8B

## Technology Stack
- asyncio for async operations
- LangChain for model interface and structured output
- RabbitMQ for task queue (consumes llm_tasks, publishes llm_results)
- gRPC for heartbeat to Orchestrator

Node Name: "LLM"
Node ID: (assigned by Orchestrator)

## Responsibilities

1. **Consume tasks from llm_tasks queue** (RabbitMQ)
2. **Receive text content + VLM analysis results**
3. **Generate comprehensive analysis**:
   - Summary of the article
   - Sentiment: -1 (negative), 0 (neutral), 1 (positive)
   - Keywords and entities
4. **Publish results to llm_results queue**

## Output Format

```json
{
    "summary": "Short summary of the article...",
    "sentiment": -1,
    "sentiment_label": "negative",
    "keywords": ["iran", "politics", "protest"],
    "entities": {
        "countries": ["Iran"],
        "organizations": ["Security forces"],
        "people": []
    },
    "category": "politics",
    "relevance_to_topic": "medium"
}
```

## See Also
- `docs/rabbitmq_architecture.md` - Queue structure
- `docs/json_schemas.md` - Full data format
