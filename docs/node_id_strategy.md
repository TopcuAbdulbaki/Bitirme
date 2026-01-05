# Node ID Strategy

## Overview
This document defines how node IDs are generated and stored in the distributed star topology system.

## Architecture
- **Star Topology**: Orchestrator is the central hub
- **Worker Nodes**: Crawler, DB, VLM, LLM only know the Orchestrator
- **Single Source of Truth**: Orchestrator maintains the registry of all nodes

## ID Format
```
{node_type}_{uuid_suffix}
```

**Examples:**
- `crawler_a3f2b8c9`
- `vlm_f8e2a1b3`
- `llm_c4d5e6f7`
- `db_b1c2d3e4`

## ID Generation
Each node generates its own ID on first boot using UUID4:

```python
import uuid

def generate_node_id(node_type: str) -> str:
    return f"{node_type}_{uuid.uuid4().hex[:8]}"
```

## Storage

### Worker Node (Local)
Each worker stores only its own identity in `config/node_identity.json`:

```json
{
  "node_id": "crawler_a3f2b8c9",
  "node_type": "crawler",
  "orchestrator_grpc": "grpc://orchestrator-ip:50051"
}
```

### Orchestrator (Central Registry)
Orchestrator maintains a registry of all known nodes:

```json
{
  "nodes": {
    "crawler_a3f2b8c9": {
      "node_type": "crawler",
      "status": "connected",
      "last_seen": "2024-12-27T17:00:00Z",
      "ip_address": "10.0.0.5",
      "registered_at": "2024-12-20T10:00:00Z"
    }
  }
}
```

## Node Lifecycle

| Event | Action |
|-------|--------|
| First boot | Generate ID → Save locally → Register with Orchestrator |
| Reconnect | Load local ID → Send to Orchestrator → Status updated |
| Disconnect | Orchestrator marks `status: disconnected` after heartbeat timeout |
| Permanent removal | Admin removes from registry OR auto-cleanup after X days |

## Node Statuses
- `connected` - Node is online and responding to heartbeats
- `disconnected` - Node missed heartbeats, presumed offline
- `busy` - Node is processing a task
- `error` - Node reported an error state
