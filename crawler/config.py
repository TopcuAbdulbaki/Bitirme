"""
Crawler Node Configuration
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Orchestrator Connection
ORCHESTRATOR_HOST = os.getenv('ORCHESTRATOR_HOST', 'localhost')
ORCHESTRATOR_PORT = int(os.getenv('ORCHESTRATOR_PORT', '50051'))

# Heartbeat Settings
HEARTBEAT_INTERVAL = int(os.getenv('HEARTBEAT_INTERVAL', '10'))

# Mode: 'standalone' (save to file only) or 'distributed' (send to Orchestrator)
CRAWLER_MODE = os.getenv('CRAWLER_MODE', 'standalone')
