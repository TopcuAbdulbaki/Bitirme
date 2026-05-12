"""
VLM Node Configuration
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

# MinIO Settings (for minio:// media paths produced by DB node)
MINIO_HOST = os.getenv('MINIO_HOST')
MINIO_PORT = int(os.getenv('MINIO_PORT', '9000'))
MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY', 'admin')
MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY', 'admin123')
MINIO_SECURE = os.getenv('MINIO_SECURE', 'false').lower() == 'true'

# Queue Names
QUEUE_VLM_TASKS = 'vlm_tasks'
QUEUE_VLM_RESULTS = 'vlm_results'

# LM Studio Settings (Fallback - not used in production)
LM_STUDIO_HOST = os.getenv('LM_STUDIO_HOST', 'http://localhost:1234')
LM_STUDIO_MODEL = os.getenv('LM_STUDIO_MODEL', 'qwen3-vl-2b-instruct')

# Production Model (Transformers)
PRODUCTION_MODEL = os.getenv('PRODUCTION_MODEL', 'Qwen/Qwen3-VL-8B-Instruct')

# Mode: 'transformers' for production
MODEL_MODE = os.getenv('MODEL_MODE', 'transformers')

# Heartbeat Settings
HEARTBEAT_INTERVAL = int(os.getenv('HEARTBEAT_INTERVAL', '10'))

# Public Host/Port for distributed mode (Orchestrator uses these to call back)
PUBLIC_HOST = os.getenv('PUBLIC_HOST')  # e.g., "116.102.85.223"
PUBLIC_PORT = int(os.getenv('PUBLIC_PORT', '50054'))  # VLM default port
