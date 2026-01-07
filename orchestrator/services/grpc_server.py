"""
gRPC Server for Orchestrator
Implements OrchestratorService from proto definition.
"""
import grpc
from concurrent import futures
from typing import Optional

# Add parent to path for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from orchestrator.generated import orchestrator_pb2 as pb2
from orchestrator.generated import orchestrator_pb2_grpc as pb2_grpc
from orchestrator.services.node_registry import NodeRegistry, NodeStatus


class OrchestratorServicer(pb2_grpc.OrchestratorServiceServicer):
    """
    gRPC service implementation for Orchestrator.
    Handles node registration, heartbeats, and result reporting.
    """
    
    def __init__(self, registry: NodeRegistry, on_crawl_result=None, on_vlm_result=None, on_llm_result=None):
        self.registry = registry
        self.on_crawl_result = on_crawl_result
        self.on_vlm_result = on_vlm_result
        self.on_llm_result = on_llm_result
        print("[gRPC] OrchestratorServicer initialized")
    
    def Register(self, request, context):
        """Handle node registration requests."""
        print(f"[gRPC] Register request from: {request.node_type}")
        
        success, node_id, message = self.registry.register(
            request.node_type,
            request.host,
            request.port
        )
        
        return pb2.RegisterResponse(
            success=success,
            node_id=node_id,
            message=message
        )
    
    def Heartbeat(self, request, context):
        """Handle heartbeat from nodes."""
        success = self.registry.heartbeat(
            request.node_id,
            request.status
        )
        
        if not success:
            print(f"[gRPC] Heartbeat from unknown node: {request.node_id}")
        
        return pb2.HeartbeatResponse(acknowledged=success)
    
    def ReportCrawlResult(self, request, context):
        """Receive crawl results from Crawler node."""
        print(f"[gRPC] Crawl result received: task_id={request.task_id}")
        
        if self.on_crawl_result:
            self.on_crawl_result(request)
        
        return pb2.HeartbeatResponse(acknowledged=True)
    
    def ReportStoreResult(self, request, context):
        """Receive store confirmation from DB node."""
        print(f"[gRPC] Store result: task_id={request.task_id}, news_id={request.news_id}")
        return pb2.HeartbeatResponse(acknowledged=True)
    
    def ReportQueueData(self, request, context):
        """Receive queue data from DB node."""
        print(f"[gRPC] Queue data received: {len(request.json_items)} items")
        return pb2.HeartbeatResponse(acknowledged=True)
    
    def ReportImageAnalysis(self, request, context):
        """Receive image analysis from VLM node."""
        print(f"[gRPC] VLM result: task_id={request.task_id}")
        
        if self.on_vlm_result:
            self.on_vlm_result(request)
        
        return pb2.HeartbeatResponse(acknowledged=True)
    
    def ReportTextAnalysis(self, request, context):
        """Receive text analysis from LLM node."""
        print(f"[gRPC] LLM result: task_id={request.task_id}, sentiment={request.sentiment}")
        
        if self.on_llm_result:
            self.on_llm_result(request)
        
        return pb2.HeartbeatResponse(acknowledged=True)


class GRPCServer:
    """
    Wrapper for gRPC server management.
    """
    
    def __init__(self, host: str, port: int, registry: NodeRegistry):
        self.host = host
        self.port = port
        self.registry = registry
        self._server: Optional[grpc.Server] = None
        
        # Callbacks for result handling
        self.on_crawl_result = None
        self.on_vlm_result = None
        self.on_llm_result = None
    
    def start(self, max_workers: int = 10):
        """Start the gRPC server."""
        self._server = grpc.server(
            futures.ThreadPoolExecutor(max_workers=max_workers),
            options=[
                ('grpc.max_receive_message_length', 100 * 1024 * 1024),  # 100MB
                ('grpc.max_send_message_length', 100 * 1024 * 1024),
            ]
        )
        
        servicer = OrchestratorServicer(
            self.registry,
            on_crawl_result=self.on_crawl_result,
            on_vlm_result=self.on_vlm_result,
            on_llm_result=self.on_llm_result
        )
        
        pb2_grpc.add_OrchestratorServiceServicer_to_server(servicer, self._server)
        
        address = f'{self.host}:{self.port}'
        self._server.add_insecure_port(address)
        self._server.start()
        
        print(f"[gRPC] Server started on {address}")
    
    def wait_for_termination(self):
        """Block until server terminates."""
        if self._server:
            self._server.wait_for_termination()
    
    def stop(self, grace_period: int = 5):
        """Stop the server gracefully."""
        if self._server:
            self._server.stop(grace_period)
            print("[gRPC] Server stopped")
