"""
gRPC Client for LLM Node
"""
import grpc
import asyncio
from typing import Optional
from enum import IntEnum

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from llm.generated import orchestrator_pb2 as pb2
from llm.generated import orchestrator_pb2_grpc as pb2_grpc
from llm.config import ORCHESTRATOR_HOST, ORCHESTRATOR_PORT, HEARTBEAT_INTERVAL


class NodeStatus(IntEnum):
    IDLE = 0
    BUSY = 1
    ERROR = 2


class GRPCClient:
    """gRPC client for communicating with Orchestrator."""
    
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
        try:
            address = f"{ORCHESTRATOR_HOST}:{ORCHESTRATOR_PORT}"
            self._channel = grpc.insecure_channel(address)
            self._stub = pb2_grpc.OrchestratorServiceStub(self._channel)
            print(f"[gRPC Client] Connected to {address}")
            return True
        except Exception as e:
            print(f"[gRPC Client] Connection failed: {e}")
            return False
    
    def register(self) -> bool:
        if not self._stub:
            return False
        try:
            request = pb2.RegisterRequest(node_type="llm")
            response = self._stub.Register(request)
            if response.success:
                self._node_id = response.node_id
                print(f"[gRPC Client] Registered as: {self._node_id}")
                return True
            return False
        except grpc.RpcError as e:
            print(f"[gRPC Client] Registration error: {e}")
            return False
    
    def send_heartbeat(self) -> bool:
        if not self._stub or not self._node_id:
            return False
        try:
            request = pb2.HeartbeatRequest(node_id=self._node_id, status=self._status.value)
            response = self._stub.Heartbeat(request)
            return response.acknowledged
        except:
            return False
    
    def set_status(self, status: NodeStatus):
        self._status = status
    
    def report_analysis(self, task_id: str, summary: str, sentiment: int, full_json: str, success: bool = True, error: str = "") -> bool:
        if not self._stub:
            return False
        try:
            response_msg = pb2.AnalyzeTextResponse(
                task_id=task_id,
                status=pb2.SUCCESS if success else pb2.FAILED,
                summary=summary,
                sentiment=sentiment,
                full_analysis_json=full_json,
                error_message=error
            )
            self._stub.ReportTextAnalysis(response_msg)
            return True
        except grpc.RpcError as e:
            print(f"[gRPC Client] Report error: {e}")
            return False
    
    async def start_heartbeat_loop(self):
        self._running = True
        while self._running:
            if self.is_registered:
                self.send_heartbeat()
            await asyncio.sleep(HEARTBEAT_INTERVAL)
    
    def stop(self):
        self._running = False
        if self._channel:
            self._channel.close()
            print("[gRPC Client] Connection closed")
