"""
DB Node Configuration
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Orchestrator Connection
ORCHESTRATOR_HOST = os.getenv('ORCHESTRATOR_HOST', 'localhost')
ORCHESTRATOR_PORT = int(os.getenv('ORCHESTRATOR_PORT', '50051'))

# PostgreSQL Settings
POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
POSTGRES_PORT = int(os.getenv('POSTGRES_PORT', '5432'))
POSTGRES_DB = os.getenv('POSTGRES_DB', 'news_db')
POSTGRES_USER = os.getenv('POSTGRES_USER', 'news_user')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'news_password')

# MinIO Settings
MINIO_HOST = os.getenv('MINIO_HOST', 'localhost')
MINIO_PORT = int(os.getenv('MINIO_PORT', '9000'))
MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY', 'admin')
MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY', 'admin123')
MINIO_BUCKET = os.getenv('MINIO_BUCKET', 'news-media')
MINIO_SECURE = os.getenv('MINIO_SECURE', 'false').lower() == 'true'

# Heartbeat Settings
HEARTBEAT_INTERVAL = int(os.getenv('HEARTBEAT_INTERVAL', '10'))
