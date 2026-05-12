"""
gRPC Client for DB Node
Connects to Orchestrator for registration and heartbeats.
"""
import grpc
import asyncio
from typing import Optional
from enum import IntEnum

# Add parent to path for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from db.generated import orchestrator_pb2 as pb2
from db.generated import orchestrator_pb2_grpc as pb2_grpc
from db.config import (
    ORCHESTRATOR_HOST,
    ORCHESTRATOR_PORT,
    HEARTBEAT_INTERVAL,
    PUBLIC_HOST,
    PUBLIC_PORT,
)


class NodeStatus(IntEnum):
    IDLE = 0
    BUSY = 1
    ERROR = 2


class GRPCClient:
    """
    gRPC client for communicating with Orchestrator.
    """
    
    def __init__(self):
        self._channel: Optional[grpc.Channel] = None
        self._stub: Optional[pb2_grpc.OrchestratorServiceStub] = None
        self._node_id: Optional[str] = None
        self._status = NodeStatus.IDLE
        self._running = False
    
    @property
    def node_id(self) -> Optional[str]:
        return self._node_id
    
    @property
    def is_registered(self) -> bool:
        return self._node_id is not None
    
    def connect(self) -> bool:
        """Connect to Orchestrator gRPC server."""
        try:
            address = f"{ORCHESTRATOR_HOST}:{ORCHESTRATOR_PORT}"
            self._channel = grpc.insecure_channel(
                address,
                options=[
                    ('grpc.max_receive_message_length', 100 * 1024 * 1024),
                    ('grpc.max_send_message_length', 100 * 1024 * 1024),
                ]
            )
            self._stub = pb2_grpc.OrchestratorServiceStub(self._channel)
            print(f"[gRPC Client] Connected to {address}")
            return True
            
        except Exception as e:
            print(f"[gRPC Client] Connection failed: {e}")
            return False
    
    def register(self) -> bool:
        """Register this node with Orchestrator."""
        if not self._stub:
            print("[gRPC Client] Not connected")
            return False
        
        try:
            request = pb2.RegisterRequest(
                node_type="db",
                host=PUBLIC_HOST or "",
                port=PUBLIC_PORT,
            )
            response = self._stub.Register(request)
            
            if response.success:
                self._node_id = response.node_id
                print(f"[gRPC Client] Registered as: {self._node_id}")
                return True
            else:
                print(f"[gRPC Client] Registration failed: {response.message}")
                return False
                
        except grpc.RpcError as e:
            print(f"[gRPC Client] Registration error: {e}")
            return False
    
    def send_heartbeat(self) -> bool:
        """Send heartbeat to Orchestrator."""
        if not self._stub or not self._node_id:
            return False
        
        try:
            request = pb2.HeartbeatRequest(
                node_id=self._node_id,
                status=self._status.value
            )
            response = self._stub.Heartbeat(request)
            return response.acknowledged
            
        except grpc.RpcError as e:
            print(f"[gRPC Client] Heartbeat error: {e}")
            return False
    
    def set_status(self, status: NodeStatus):
        """Set current node status."""
        self._status = status
    
    def report_store_result(self, task_id: str, news_id: str, is_duplicate: bool = False) -> bool:
        """Report storage result to Orchestrator."""
        if not self._stub:
            return False
        
        try:
            response_msg = pb2.StoreDataResponse(
                task_id=task_id,
                status=pb2.SUCCESS,
                news_id=news_id,
                is_duplicate=is_duplicate
            )
            self._stub.ReportStoreResult(response_msg)
            return True
            
        except grpc.RpcError as e:
            print(f"[gRPC Client] Report error: {e}")
            return False
    
    async def start_heartbeat_loop(self):
        """Start async heartbeat loop."""
        self._running = True
        while self._running:
            if self.is_registered:
                success = self.send_heartbeat()
                if not success:
                    print("[gRPC Client] Heartbeat failed, attempting reconnect...")
                    if self.connect():
                        self.register()
            await asyncio.sleep(HEARTBEAT_INTERVAL)
    
    def stop(self):
        """Stop heartbeat and close connection."""
        self._running = False
        if self._channel:
            self._channel.close()
            print("[gRPC Client] Connection closed")
