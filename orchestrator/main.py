"""
Orchestrator Main Entry Point
Central node that coordinates all other nodes.
"""
import asyncio
import signal
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestrator.config import GRPC_HOST, GRPC_PORT, HEARTBEAT_TIMEOUT
from orchestrator.services.node_registry import NodeRegistry
from orchestrator.services.grpc_server import GRPCServer
from orchestrator.services.pipeline_manager import PipelineManager

# Optional: RabbitMQ (may not be installed locally for testing)
try:
    from orchestrator.services.rabbitmq_manager import RabbitMQManager
    RABBITMQ_AVAILABLE = True
except ImportError:
    # RABBITMQ_AVAILABLE = False
    # print("[Main] RabbitMQ not available (pika not installed)")
    raise ImportError("RabbitMQ (pika) is required for distributed system.")


class Orchestrator:
    """
    Main Orchestrator class.
    Manages all services and coordinates the pipeline.
    """
    
    def __init__(self):
        self.registry = NodeRegistry()
        self.grpc_server = GRPCServer(GRPC_HOST, GRPC_PORT, self.registry)
        
        # RabbitMQ (optional for local testing)
        self.rabbitmq = None
        if RABBITMQ_AVAILABLE:
            self.rabbitmq = RabbitMQManager()
        
        # Pipeline manager
        self.pipeline = PipelineManager(self.registry, self.rabbitmq)
        
        # Wire up callbacks
        self._setup_callbacks()
        
        self._running = False
    
    def _setup_callbacks(self):
        """Setup callbacks for gRPC result handlers."""
        self.grpc_server.on_crawl_result = self._handle_crawl_result
        self.grpc_server.on_vlm_result = self._handle_vlm_result
        self.grpc_server.on_llm_result = self._handle_llm_result
    
    def _handle_crawl_result(self, result):
        """Handle incoming crawl results."""
        if result.status == 0:  # SUCCESS
            self.pipeline.on_crawl_complete(result.task_id, result.json_data)
        else:
            self.pipeline.on_task_failed(result.task_id, result.error_message)
    
    def _handle_vlm_result(self, result):
        """Handle incoming VLM results."""
        if result.status == 0:  # SUCCESS
            self.pipeline.on_vlm_complete(result.task_id, result.analysis_json)
        else:
            self.pipeline.on_task_failed(result.task_id, result.error_message)
    
    def _handle_llm_result(self, result):
        """Handle incoming LLM results."""
        if result.status == 0:  # SUCCESS
            self.pipeline.on_llm_complete(result.task_id, result.full_analysis_json)
        else:
            self.pipeline.on_task_failed(result.task_id, result.error_message)
    
    async def _heartbeat_checker(self):
        """Periodic check for timed-out nodes."""
        while self._running:
            timed_out = self.registry.check_timeouts(HEARTBEAT_TIMEOUT)
            if timed_out:
                for node_id in timed_out:
                    print(f"[Orchestrator] Node offline: {node_id}")
            await asyncio.sleep(HEARTBEAT_TIMEOUT // 2)

    async def _auto_trigger_task(self):
        """
        Background task to auto-trigger the crawl once a crawler is available.
        This provides the 'Auto-Start' behavior the user expects but via 'ExecuteCrawl'.
        """
        print("[Orchestrator] Waiting for a Crawler to connect...")
        while self._running:
            # Check if any crawler is registered
            crawlers = self.registry.get_nodes_by_type(self.registry.NodeType.CRAWLER) # access enum via instance or class? Wrapper has it? 
            # Note: NodeType is imported in main? No.
            # let's use string check or fix imports. 
            # Better: self.registry.get_idle_node uses the Enum.
            # We can try to trigger every 5 seconds until successful.
            
            success = await self.pipeline.trigger_crawl([]) # Empty list = Default sources
            if success:
                print("[Orchestrator] Initial Crawl Triggered! (Auto-Start)")
                break # Run once on startup
            
            await asyncio.sleep(5)

    
    def start(self):
        """Start all services."""
        print("=" * 50)
        print("ORCHESTRATOR STARTING")
        print("=" * 50)
        
        # Connect to RabbitMQ
        if self.rabbitmq:
            if self.rabbitmq.connect():
                print("[Orchestrator] RabbitMQ connected")
            else:
                print("[Orchestrator] RabbitMQ connection failed (continuing without)")
                self.rabbitmq = None
        
        # Start gRPC server
        self.grpc_server.start()
        
        self._running = True
        print("[Orchestrator] Ready and waiting for connections...")
        print(f"[Orchestrator] gRPC: {GRPC_HOST}:{GRPC_PORT}")
        print("=" * 50)
    
    def run(self):
        """Run orchestrator (blocking)."""
        self.start()
        
        try:
            # Run async heartbeat checker in background
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Start heartbeat task but don't block on it
            heartbeat_task = loop.create_task(self._heartbeat_checker())
            trigger_task = loop.create_task(self._auto_trigger_task())
            
            # Wait for keyboard interrupt
            try:
                loop.run_forever()
            except KeyboardInterrupt:
                pass
            finally:
                heartbeat_task.cancel()
                trigger_task.cancel()
                loop.close()
                
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()
    
    def stop(self):
        """Stop all services."""
        print("\n[Orchestrator] Shutting down...")
        self._running = False
        
        self.grpc_server.stop()
        
        if self.rabbitmq:
            self.rabbitmq.close()
        
        print("[Orchestrator] Shutdown complete")
    
    def get_status(self) -> dict:
        """Get orchestrator status."""
        return {
            'nodes': len(self.registry),
            'pending_tasks': len(self.pipeline.get_pending_tasks()),
            'rabbitmq': self.rabbitmq is not None
        }


def main():
    """Main entry point."""
    orchestrator = Orchestrator()
    
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        orchestrator.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    orchestrator.run()


if __name__ == '__main__':
    main()
