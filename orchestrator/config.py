"""
Orchestrator Configuration
"""
import os
from dotenv import load_dotenv

load_dotenv()

# gRPC Settings
GRPC_HOST = os.getenv('GRPC_HOST', '0.0.0.0')
GRPC_PORT = int(os.getenv('GRPC_PORT', '50051'))

# Local admin HTTP panel
HTTP_HOST = os.getenv('ORCHESTRATOR_HTTP_HOST', '127.0.0.1')
HTTP_PORT = int(os.getenv('ORCHESTRATOR_HTTP_PORT', '8088'))

# RabbitMQ Settings
# RabbitMQ Settings (DISTRIBUTED: Must be set via env vars)
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST') # Default removed for distributed safety result: None
RABBITMQ_PORT = int(os.getenv('RABBITMQ_PORT', '5672'))
RABBITMQ_USER = os.getenv('RABBITMQ_USER', 'guest')
RABBITMQ_PASSWORD = os.getenv('RABBITMQ_PASSWORD', 'guest')

# Queue Names
QUEUE_VLM_TASKS = 'vlm_tasks'
QUEUE_VLM_RESULTS = 'vlm_results'
QUEUE_LLM_TASKS = 'llm_tasks'
QUEUE_LLM_RESULTS = 'llm_results'
QUEUE_DB_TASKS = 'db_tasks'
QUEUE_AGENT_TASKS = 'agent_tasks'
QUEUE_AGENT_RESULTS = 'agent_results'

# Heartbeat Settings
HEARTBEAT_INTERVAL = int(os.getenv('HEARTBEAT_INTERVAL', '10'))  # seconds
HEARTBEAT_TIMEOUT = int(os.getenv('HEARTBEAT_TIMEOUT', '30'))  # seconds

# Optional read-only DB connection for the local ops panel
ADMIN_DB_HOST = os.getenv('ORCHESTRATOR_DB_HOST') or os.getenv('POSTGRES_HOST')
ADMIN_DB_PORT = int(os.getenv('ORCHESTRATOR_DB_PORT', os.getenv('POSTGRES_PORT', '5432')))
ADMIN_DB_NAME = os.getenv('ORCHESTRATOR_DB_NAME', os.getenv('POSTGRES_DB', 'news_db'))
ADMIN_DB_USER = os.getenv('ORCHESTRATOR_DB_USER', os.getenv('POSTGRES_USER', 'news_user'))
ADMIN_DB_PASSWORD = os.getenv('ORCHESTRATOR_DB_PASSWORD', os.getenv('POSTGRES_PASSWORD', 'news_password'))
ADMIN_DB_EMBEDDING_DIM = int(os.getenv('ORCHESTRATOR_DB_EMBEDDING_DIM', '1024'))
