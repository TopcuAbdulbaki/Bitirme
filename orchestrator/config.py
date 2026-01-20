"""
Orchestrator Configuration
"""
import os
from dotenv import load_dotenv

load_dotenv()

# gRPC Settings
GRPC_HOST = os.getenv('GRPC_HOST', '0.0.0.0')
GRPC_PORT = int(os.getenv('GRPC_PORT', '50051'))

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

# Heartbeat Settings
HEARTBEAT_INTERVAL = int(os.getenv('HEARTBEAT_INTERVAL', '10'))  # seconds
HEARTBEAT_TIMEOUT = int(os.getenv('HEARTBEAT_TIMEOUT', '30'))  # seconds
