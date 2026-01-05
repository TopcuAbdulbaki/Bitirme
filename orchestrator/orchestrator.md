
Responsible for managing the WireGuard VPN connection (installation, configuration, management) and orchestrating all nodes. The core node of star topology. Will use gRPC for communication. Will use RabbitMQ for message queue (RabbitMQ server runs on same machine as Orchestrator). Will use asyncio for async operations. 
Python 3.13.5. All system will run on distributed computers. 

Connected Nodes:
- Crawler(Crawler4AI)
- DB(PostgreSQL+pgvector)
- Vision Language Model(qwen3 vl-2b)
- LLM(qwen3)
Node Name: "Orchestrator"


Node ID: 
