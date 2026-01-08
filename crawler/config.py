"""
Crawler Node Configuration
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Orchestrator Connection
# Orchestrator Connection (DISTRIBUTED: Must be set via env vars)
ORCHESTRATOR_HOST = os.getenv('ORCHESTRATOR_HOST') # Default removed for distributed safety
ORCHESTRATOR_PORT = int(os.getenv('ORCHESTRATOR_PORT', '50051'))

# Heartbeat Settings
HEARTBEAT_INTERVAL = int(os.getenv('HEARTBEAT_INTERVAL', '10'))

# Mode: 'distributed' is default for production
CRAWLER_MODE = os.getenv('CRAWLER_MODE', 'distributed')

# Crawler Internal Server Port (for receiving callbacks)
CRAWLER_GRPC_PORT = int(os.getenv('CRAWLER_GRPC_PORT', '50052'))

# Public Host/Port for distributed mode (Orchestrator uses these to call back)
# Set these to your Vast.ai public IP and mapped port
PUBLIC_HOST = os.getenv('PUBLIC_HOST')  # e.g., "116.102.85.223"
PUBLIC_PORT = int(os.getenv('PUBLIC_PORT', '50052'))  # e.g., the mapped port

# Demo Mode: Limits the number of processed items for quick testing
CRAWLER_DEMO_MODE = os.getenv('CRAWLER_DEMO_MODE', 'false').lower() == 'true'
CRAWLER_DEMO_LIMIT = int(os.getenv('CRAWLER_DEMO_LIMIT', '5'))
