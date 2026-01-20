"""
DB Node Configuration
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Orchestrator Connection
# Orchestrator Connection (DISTRIBUTED: Must be set via env vars)
ORCHESTRATOR_HOST = os.getenv('ORCHESTRATOR_HOST') # Default removed
ORCHESTRATOR_PORT = int(os.getenv('ORCHESTRATOR_PORT', '50051'))

# PostgreSQL Settings (DISTRIBUTED: Must be set via env vars)
POSTGRES_HOST = os.getenv('POSTGRES_HOST') # Default removed
POSTGRES_PORT = int(os.getenv('POSTGRES_PORT', '5432'))
POSTGRES_DB = os.getenv('POSTGRES_DB', 'news_db')
POSTGRES_USER = os.getenv('POSTGRES_USER', 'news_user')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'news_password')

# MinIO Settings (DISTRIBUTED: Must be set via env vars)
MINIO_HOST = os.getenv('MINIO_HOST') # Default removed
MINIO_PORT = int(os.getenv('MINIO_PORT', '9000'))
MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY', 'admin')
MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY', 'admin123')
MINIO_BUCKET = os.getenv('MINIO_BUCKET', 'news-media')
MINIO_SECURE = os.getenv('MINIO_SECURE', 'false').lower() == 'true'

# RabbitMQ Settings (DISTRIBUTED: Must be set via env vars)
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST')
RABBITMQ_PORT = int(os.getenv('RABBITMQ_PORT', '5672'))
RABBITMQ_USER = os.getenv('RABBITMQ_USER', 'guest')
RABBITMQ_PASSWORD = os.getenv('RABBITMQ_PASSWORD', 'guest')

# Queue Names
QUEUE_DB_TASKS = 'db_tasks'

# Heartbeat Settings
HEARTBEAT_INTERVAL = int(os.getenv('HEARTBEAT_INTERVAL', '10'))

# Public Host/Port for distributed mode (Orchestrator uses these to call back)
PUBLIC_HOST = os.getenv('PUBLIC_HOST')  # e.g., "116.102.85.223"
PUBLIC_PORT = int(os.getenv('PUBLIC_PORT', '50053'))  # DB default port
