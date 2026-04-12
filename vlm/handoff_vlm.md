# VLM Module Handoff Documentation

## 1. Project Overview
The **VLM (Vision-Language Model)** module is responsible for analyzing images associated with news articles. It extracts descriptive metadata, identifies objects, assesses sentiment, and determines relevance to the news context using state-of-the-art vision models (specifically Qwen3-VL).

### Status Summary
- **Primary Model:** Qwen3-VL-8B-Instruct (via Transformers).
- **Secondary Model:** qwen3-vl-2b-instruct (via LM Studio for local/lightweight use).
- **Architecture:** Distributed node. Connects to Orchestrator via gRPC and handles tasks via RabbitMQ.

---

## 2. Directory Structure

```text
vlm/
├── proto/              # Protobuf definitions for gRPC
│   └── orchestrator.proto
├── generated/          # Python files generated from .proto
├── services/           # Business logic implementations
│   ├── model_handler.py   # Model loading and inference logic
│   ├── rabbitmq_consumer.py # Queue interaction
│   └── grpc_client.py     # Heartbeat and node registration
├── main.py             # Entry point (VLMNode class)
├── config.py           # Configuration and Environment variable management
├── Dockerfile          # Containerization for GPU-enabled deployment
├── requirements.txt    # Python dependencies
└── vlm.md              # Original high-level documentation
```

---

## 3. Key Components & Files

### `main.py`
The heart of the module. It initializes the `VLMNode`, registers with the Orchestrator, and starts an asynchronous loop to consume tasks from RabbitMQ.
- **Queue Polling:** Non-blocking polling from `vlm_tasks`.
- **Task Processing:** `process_task` method extracts image data (bytes or URLs), sends them to the handler, and collects results.
- **Heartbeat:** Runs a background task to notify Orchestrator that the node is alive.

### `services/model_handler.py`
Implements model interfaces.
- **`TransformersHandler`**: Used in production. Loads `Qwen3-VL-8B-Instruct` using 8-bit quantization to minimize VRAM usage while maintaining performance. Requires `transformers`, `torch`, and `bitsandbytes`.
- **`LMStudioHandler`**: Simple HTTP interface for LM Studio's OpenAI-compatible API. Useful for development without heavy GPU requirements.
- **Prompting:** Uses `VLM_SYSTEM_PROMPT` to enforce strict JSON output.

### `services/rabbitmq_consumer.py`
Wraps `pika` for asynchronous message handling.
- **Consumer:** Reads from `vlm_tasks`.
- **Publisher:** Sends analysis results to `vlm_results`.

### `services/grpc_client.py`
Manages the node's lifecycle in the cluster.
- **Registration:** Sends node metadata (ID, Type, Port) to Orchestrator.
- **Heartbeat:** Periodic updates to prevent timeout/disconnection in Orchestrator.

---

## 4. Workflows

### Initialization
1.  Load configuration from `.env`.
2.  Connect to Orchestrator (gRPC).
3.  Connect to RabbitMQ.
4.  Load Model (lazy-loading on first task for Transformers, immediate check for LM Studio).

### Task Loop
1.  Empty message check from `vlm_tasks`.
2.  Parse task JSON (containing news content and media links).
3.  Download images if necessary (using `aiohttp`).
4.  Perform inference (Model Handler).
5.  Format result to unified JSON schema.
6.  Publish to `vlm_results`.

---

## 5. Important Key Points (Critical Knowledge)

- **8-Bit Quantization:** The production `TransformersHandler` uses `BitsAndBytesConfig` (load_in_8bit=True). This is crucial for running 8B+ models on consumer or mid-range enterprise GPUs (e.g., RTX 3090/4090 or A100/H100).
- **Contextual Analysis:** The VLM receives the first 500 characters of the news article alongside the image to provide more specific and relevant descriptions.
- **JSON Enforcement:** The system prompt is engineered to skip preamble and return only raw JSON. `model_handler` includes a fallback parser to handle cases where the model might wrap JSON in Markdown code blocks.
- **Error Handling:** If an image fails to process, a partial result with an `error` field is returned so the pipeline doesn't stall.
- **Distributed Ready:** By setting `PUBLIC_HOST` and `PUBLIC_PORT`, the VLM node can run on a separate server from the Orchestrator/DB.

---

## 6. How to Run

### Local (LM Studio Method)
1.  Run LM Studio, load a VL model (e.g., Qwen3-VL-2B).
2.  Enable "Local Server" in LM Studio on port 1234.
3.  Set `MODEL_MODE=lm-studio` in `.env`.
4.  Run: `python -m vlm.main`

### Production (Transformers Method)
1.  Ensure CUDA drivers and `bitsandbytes` are installed.
2.  Set `MODEL_MODE=transformers` in `.env`.
3.  Run: `python -m vlm.main`

---

## 7. Future Improvements
- [ ] Implement batch inference to process multiple images in one model pass (improves throughput).
- [ ] Add support for video key-frame extraction and analysis.
- [ ] Integration with MinIO directly to avoid passing large bytes through RabbitMQ if preferred.
