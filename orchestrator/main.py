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
        
        # Crawl control (poll model)
        self.crawl_active = False  # Manual start/stop
        self._crawl_task_given = {}  # Track which crawlers have received tasks
        
        # Wire up callbacks
        self._setup_callbacks()
        
        self._running = False
    
    def _setup_callbacks(self):
        """Setup callbacks for gRPC result handlers."""
        self.grpc_server.on_crawl_result = self._handle_crawl_result
        self.grpc_server.on_vlm_result = self._handle_vlm_result
        self.grpc_server.on_llm_result = self._handle_llm_result
        self.grpc_server.get_crawl_task = self._get_crawl_task  # Poll model
    
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
    
    def _get_crawl_task(self, node_id: str):
        """
        Poll model callback: Called when Crawler asks for work.
        Returns (has_task, task_id, urls, config_json).
        """
        if not self.crawl_active:
            return (False, None, None, None)
        
        # Check if this crawler already has a task
        if node_id in self._crawl_task_given and self._crawl_task_given[node_id]:
            return (False, None, None, None)
        
        # Give task to crawler
        import uuid
        task_id = f"crawl_{uuid.uuid4().hex[:8]}"
        self._crawl_task_given[node_id] = True
        
        print(f"[Orchestrator] Crawl task assigned to {node_id}")
        return (True, task_id, [], "")  # Empty URLs = use default sources
    
    def start_crawl(self):
        """Start crawling (called manually)."""
        print("[Orchestrator] *** CRAWL STARTED ***")
        self.crawl_active = True
        self._crawl_task_given = {}  # Reset
    
    def stop_crawl(self):
        """Stop crawling."""
        print("[Orchestrator] *** CRAWL STOPPED ***")
        self.crawl_active = False

    
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
            
            # Start heartbeat task
            heartbeat_task = loop.create_task(self._heartbeat_checker())
            
            # Start command input task
            input_task = loop.create_task(self._command_loop())
            
            try:
                loop.run_forever()
            except KeyboardInterrupt:
                pass
            finally:
                heartbeat_task.cancel()
                input_task.cancel()
                loop.close()
                
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()
    
    async def _command_loop(self):
        """Command input loop for manual control."""
        print("=" * 50)
        print("COMMANDS: 'start' - Begin crawling")
        print("          'stop'  - Stop crawling")
        print("          'status'- Show status")
        print("          'quit'  - Exit")
        print("=" * 50)
        
        while self._running:
            try:
                # Non-blocking input using asyncio
                cmd = await asyncio.get_event_loop().run_in_executor(
                    None, 
                    lambda: input("\n[Command] > ").strip().lower()
                )
                
                if cmd == "start":
                    self.start_crawl()
                elif cmd == "stop":
                    self.stop_crawl()
                elif cmd == "status":
                    status = self.get_status()
                    print(f"[Status] Nodes: {status['nodes']}, Crawl Active: {self.crawl_active}")
                elif cmd == "quit" or cmd == "exit":
                    break
                else:
                    print("[Unknown command. Use: start, stop, status, quit]")
                    
            except (EOFError, KeyboardInterrupt):
                break
            except Exception as e:
                print(f"[Error] {e}")
                await asyncio.sleep(1)
    
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

