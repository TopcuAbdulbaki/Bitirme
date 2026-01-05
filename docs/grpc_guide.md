# gRPC Protocol Guide

## Overview
This project uses gRPC for communication between the Orchestrator and all worker nodes (Crawler, DB, VLM, LLM).

## File Structure
```
proto/
└── orchestrator.proto   ← Shared contract (copy to each node)
```

Each node must have its own copy of the proto file and generate the Python code locally.

## Prerequisites
Install gRPC tools in each node's environment:

```bash
pip install grpcio grpcio-tools
```

Add to each node's `requirements.txt`:
```
grpcio>=1.60.0
grpcio-tools>=1.60.0
```

## Compiling Proto Files

Run this command from the node's root directory:

```bash
python -m grpc_tools.protoc -I./proto --python_out=./generated --grpc_python_out=./generated ./proto/orchestrator.proto
```

This generates:
- `generated/orchestrator_pb2.py` - Message classes
- `generated/orchestrator_pb2_grpc.py` - Client/Server stubs

## Directory Structure Per Node

```
node_name/
├── proto/
│   └── orchestrator.proto      ← Copy of shared proto
├── generated/
│   ├── __init__.py             ← Empty, makes it a package
│   ├── orchestrator_pb2.py     ← Generated messages
│   └── orchestrator_pb2_grpc.py← Generated stubs
├── config/
│   └── node_identity.json
├── requirements.txt
└── main.py
```

## Usage Examples

### Orchestrator (Server)

```python
import grpc
from concurrent import futures
from generated import orchestrator_pb2, orchestrator_pb2_grpc

class OrchestratorServicer(orchestrator_pb2_grpc.OrchestratorServiceServicer):
    def Register(self, request, context):
        node_id = f"{request.node_type}_{uuid.uuid4().hex[:8]}"
        return orchestrator_pb2.RegisterResponse(
            success=True,
            node_id=node_id,
            message="Registration successful"
        )
    
    def Heartbeat(self, request, context):
        print(f"Heartbeat from {request.node_id}: {request.status}")
        return orchestrator_pb2.HeartbeatResponse(acknowledged=True)

# Start server
server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
orchestrator_pb2_grpc.add_OrchestratorServiceServicer_to_server(
    OrchestratorServicer(), server
)
server.add_insecure_port('[::]:50051')
server.start()
server.wait_for_termination()
```

### Worker Node (Client)

```python
import grpc
from generated import orchestrator_pb2, orchestrator_pb2_grpc

# Connect to Orchestrator
channel = grpc.insecure_channel('orchestrator-ip:50051')
stub = orchestrator_pb2_grpc.OrchestratorServiceStub(channel)

# Register
response = stub.Register(
    orchestrator_pb2.RegisterRequest(node_type="crawler")
)
print(f"Assigned ID: {response.node_id}")

# Send heartbeat
stub.Heartbeat(
    orchestrator_pb2.HeartbeatRequest(
        node_id=response.node_id,
        status=orchestrator_pb2.IDLE
    )
)
```

## Service Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      ORCHESTRATOR                                │
│  Implements: OrchestratorService (receives from all nodes)       │
│  Uses Stubs: CrawlerService, DatabaseService, VLMService,       │
│              LLMService (to send tasks to nodes)                 │
└─────────────────────────────────────────────────────────────────┘
                           ▲
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │ CRAWLER  │    │   VLM    │    │   LLM    │
    │          │    │          │    │          │
    │Implements│    │Implements│    │Implements│
    │Crawler   │    │VLM       │    │LLM       │
    │Service   │    │Service   │    │Service   │
    │          │    │          │    │          │
    │Uses Stub:│    │Uses Stub:│    │Uses Stub:│
    │Orchestr  │    │Orchestr  │    │Orchestr  │
    │atorSvc   │    │atorSvc   │    │atorSvc   │
    └──────────┘    └──────────┘    └──────────┘
```

## Bidirectional Communication

1. **Node → Orchestrator**: Register, Heartbeat, Report results
2. **Orchestrator → Node**: Assign tasks (ExecuteCrawl, AnalyzeImages, etc.)

Both directions use the same proto file but different services.
