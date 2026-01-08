"""
LLM Node Configuration
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Orchestrator Connection
# Orchestrator Connection
ORCHESTRATOR_HOST = os.getenv('ORCHESTRATOR_HOST') # Default removed
ORCHESTRATOR_PORT = int(os.getenv('ORCHESTRATOR_PORT', '50051'))

# RabbitMQ Settings
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST') # Default removed
RABBITMQ_PORT = int(os.getenv('RABBITMQ_PORT', '5672'))
RABBITMQ_USER = os.getenv('RABBITMQ_USER', 'guest')
RABBITMQ_PASSWORD = os.getenv('RABBITMQ_PASSWORD', 'guest')

# Queue Names
QUEUE_LLM_TASKS = 'llm_tasks'
QUEUE_LLM_RESULTS = 'llm_results'

# LM Studio Settings (Fallback - not used in production)
LM_STUDIO_HOST = os.getenv('LM_STUDIO_HOST', 'http://localhost:1234')
LM_STUDIO_MODEL = os.getenv('LM_STUDIO_MODEL', 'qwen3-8b')

# Production Model (Transformers)
PRODUCTION_MODEL = os.getenv('PRODUCTION_MODEL', 'Qwen/Qwen3-8B')

# Mode: 'transformers' for production
MODEL_MODE = os.getenv('MODEL_MODE', 'transformers')

# Heartbeat Settings
HEARTBEAT_INTERVAL = int(os.getenv('HEARTBEAT_INTERVAL', '10'))
