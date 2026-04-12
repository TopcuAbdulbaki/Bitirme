# Orchestrator Module Handoff

The **Orchestrator** is the central node of the distributed system. It manages node registration, coordinates the processing pipeline (Crawl -> VLM -> LLM -> DB), and maintains system state. It uses a star topology where all other nodes connect to it.

## 1. Directory Structure

- `orchestrator/`: Root directory.
    - `proto/`: Contains `orchestrator.proto` (gRPC interface definitions).
    - `generated/`: Contains Python files generated from `.proto` (`orchestrator_pb2.py`, `orchestrator_pb2_grpc.py`).
    - `services/`: Core logic modules.
        - `grpc_server.py`: Implementation of the gRPC server and servicer.
        - `node_registry.py`: Tracks connected nodes and heartbeats (IDLE/BUSY/OFFLINE).
        - `pipeline_manager.py`: Manages task state and data flow between stages.
        - `rabbitmq_manager.py`: Handles publishing and consuming tasks via RabbitMQ.
    - `config.py`: Configuration using `.env` (gRPC and RabbitMQ settings).
    - `main.py`: Entry point for the orchestrator with CLI control.
    - `Dockerfile`: Containerization for deployment.
    - `requirements.txt`: Python dependencies (grpcio, pika, etc.).

## 2. Communication Architecture

The system uses a mixed communication model to balance efficiency and reliability:

- **gRPC (Node Control & Status)**: 
    - **Registration**: Every node (Crawler, VLM, LLM, DB) must call `Register` on startup.
    - **Heartbeat**: Nodes periodically report status (IDLE/BUSY). Orchestrator marks nodes as OFFLINE if heartbeats are missed.
    - **Crawl Poll**: Crawlers use `GetCrawlTask` (Poll Model) to ask for work when idle.
- **RabbitMQ (Task Distribution)**: Used for heavy processing tasks (VLM, LLM, DB) to ensure persistence and load balancing.
    - `vlm_tasks` / `vlm_results`
    - `llm_tasks` / `llm_results`
    - `db_tasks` (Final storage)

## 3. Pipeline Flow

The `PipelineManager` coordinates the following lifecycle for each news item:

1.  **Crawl Complete**: Raw data is received from a Crawler.
2.  **VLM Analysis**: Orchestrator publishes a task to `vlm_tasks`. VLM node processes images and returns results.
3.  **LLM Analysis**: Orchestrator combines raw text + VLM results and publishes to `llm_tasks`. LLM node performs sentiment analysis and summarization.
4.  **Database Storage**: Final analyzed data is published to `db_tasks` for permanent storage in PostgreSQL/pgvector.

## 4. Key Commands

| Command | Description |
| :--- | :--- |
| `python -m orchestrator.main` | Start the Orchestrator (from project root) |
| `start` (CLI) | Manually begin the crawling process |
| `stop` (CLI) | Stop assigning new crawl tasks |
| `status` (CLI) | View count of connected nodes and pending tasks |
| `quit` (CLI) | Gracefully shut down the Orchestrator |

## 5. Important Key Points

- **Non-Blocking IO**: Uses `asyncio` for the heartbeat checker, result poller, and command loop.
- **Node Registry**: Thread-safe singleton that maintains the global state of the cluster.
- **Distributed Safety**: RabbitMQ URLs are not defaulted in `config.py` to prevent accidental local connections in distributed environments.
- **gRPC Max Message Size**: Increased to **100MB** to handle large JSON payloads containing image data or extensive crawl results.
- **Graceful Shutdown**: Handles SIGINT to close RabbitMQ connections and stop gRPC server properly.

## 6. Connectivity Configuration (.env)

Ensure these variables are set for the Orchestrator to function:
- `GRPC_PORT`: Port for the gRPC server (default: 50051).
- `RABBITMQ_HOST`: IP/Hostname of the RabbitMQ broker.
- `RABBITMQ_USER` / `RABBITMQ_PASSWORD`: Broker credentials.
- `HEARTBEAT_TIMEOUT`: Seconds before a node is considered offline (default: 30s).
