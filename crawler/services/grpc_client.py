"""
gRPC Client for Crawler Node
"""
import grpc
import json
import asyncio
from typing import Optional
from enum import IntEnum

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from crawler.generated import orchestrator_pb2 as pb2
from crawler.generated import orchestrator_pb2_grpc as pb2_grpc
from crawler.config import ORCHESTRATOR_HOST, ORCHESTRATOR_PORT, HEARTBEAT_INTERVAL


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
        self._task_counter = 0
    
    @property
    def node_id(self) -> Optional[str]:
        return self._node_id
    
    @property
    def is_registered(self) -> bool:
        return self._node_id is not None
    
    @property
    def is_connected(self) -> bool:
        return self._stub is not None
    
    def connect(self) -> bool:
        try:
            address = f"{ORCHESTRATOR_HOST}:{ORCHESTRATOR_PORT}"
            self._channel = grpc.insecure_channel(address)
            self._stub = pb2_grpc.OrchestratorServiceStub(self._channel)
            print(f"[gRPC] Connected to Orchestrator at {address}")
            return True
        except Exception as e:
            print(f"[gRPC] Connection failed: {e}")
            return False
    
    def register(self) -> bool:
        if not self._stub:
            return False
        try:
            request = pb2.RegisterRequest(node_type="crawler")
            response = self._stub.Register(request)
            if response.success:
                self._node_id = response.node_id
                print(f"[gRPC] Registered as: {self._node_id}")
                return True
            print(f"[gRPC] Registration failed: {response.message}")
            return False
        except grpc.RpcError as e:
            print(f"[gRPC] Registration error: {e}")
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
    
    def _generate_task_id(self) -> str:
        self._task_counter += 1
        return f"crawl_{self._node_id}_{self._task_counter}"
    
    def send_crawl_result(self, news_data: dict) -> bool:
        """Send a single crawled news item to Orchestrator."""
        if not self._stub:
            return False
        
        try:
            task_id = self._generate_task_id()
            json_data = json.dumps(news_data, ensure_ascii=False)
            
            response_msg = pb2.CrawlTaskResponse(
                task_id=task_id,
                status=pb2.SUCCESS,
                json_data=json_data,
                error_message=""
            )
            self._stub.ReportCrawlResult(response_msg)
            print(f"[gRPC] Sent to Orchestrator: {news_data.get('url', 'unknown')[:50]}...")
            return True
        except grpc.RpcError as e:
            print(f"[gRPC] Send error: {e}")
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
            print("[gRPC] Connection closed")
