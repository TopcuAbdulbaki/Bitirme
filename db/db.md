PostgreSQL + pgvector
Responsible for storing all data. Will use PostgreSQL for database. Will use pgvector for vector database. Will use asyncio for async operations. Will use langchain for AI operations. Python 3.13.5
Will use qwen3 embedding model for vectorization. Will use rabbitmq for message queue. 

Node Name: "DB"
Node ID: 

gets data from orchestrator and stores it to database. also vectorizes data and adds to vector database.
checks if its unique data or not. if its not unique data it gonna skip it.

when storing data to database gives unique id for every news..
uses a queue to send unprocessed data to orchestrator. 

