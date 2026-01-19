"""
Crawler Node Configuration
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Orchestrator Connection (DISTRIBUTED: Must be set via env vars)
ORCHESTRATOR_HOST = os.getenv('ORCHESTRATOR_HOST')  # Required for distributed mode
ORCHESTRATOR_PORT = int(os.getenv('ORCHESTRATOR_PORT', '50051'))

# Heartbeat Settings
HEARTBEAT_INTERVAL = int(os.getenv('HEARTBEAT_INTERVAL', '10'))

# Mode: 'distributed' is default for production
CRAWLER_MODE = os.getenv('CRAWLER_MODE', 'distributed')

# Poll interval (seconds) - how often to ask Orchestrator for tasks
POLL_INTERVAL = int(os.getenv('POLL_INTERVAL', '5'))

# Demo Mode: Limits the number of processed items for quick testing
CRAWLER_DEMO_MODE = os.getenv('CRAWLER_DEMO_MODE', 'false').lower() == 'true'
CRAWLER_DEMO_LIMIT = int(os.getenv('CRAWLER_DEMO_LIMIT', '5'))

# NOTE: PUBLIC_HOST/PORT no longer needed!
# Crawler now uses POLL model - asks Orchestrator for work instead of receiving callbacks.

