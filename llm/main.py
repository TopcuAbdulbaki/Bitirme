"""
LLM Node Main Entry Point
Language Model for text analysis and sentiment classification.
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from llm.config import (
    HEARTBEAT_INTERVAL, MODEL_MODE,
    RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_USER, RABBITMQ_PASSWORD,
    QUEUE_LLM_TASKS, QUEUE_LLM_RESULTS
)
from llm.services.grpc_client import GRPCClient, NodeStatus
from llm.services.model_handler import get_llm_handler, TextAnalysisResult
from llm.services.rabbitmq_consumer import RabbitMQConsumer, QueueMessage


class LLMNode:
    """
    Main LLM Node class.
    Processes text analysis tasks from RabbitMQ queue.
    """
    
    def __init__(self):
        self.grpc_client = GRPCClient()
        self.model_handler = get_llm_handler()
        self.rabbitmq = RabbitMQConsumer(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
            user=RABBITMQ_USER,
            password=RABBITMQ_PASSWORD
        )
        self._running = False
    
    async def initialize(self) -> bool:
        """Initialize LLM node."""
        print("=" * 50)
        print("LLM NODE STARTING")
        print(f"Mode: {MODEL_MODE}")
        print("=" * 50)
        
        # Connect to Orchestrator
        if not self.grpc_client.connect():
            print("[LLM Node] Warning: Could not connect to Orchestrator")
        else:
            if not self.grpc_client.register():
                print("[LLM Node] Warning: Could not register with Orchestrator")
        
        # Connect to RabbitMQ
        rabbitmq_ok = self.rabbitmq.connect()
        if rabbitmq_ok:
            self.rabbitmq.declare_queue(QUEUE_LLM_TASKS)
            self.rabbitmq.declare_queue(QUEUE_LLM_RESULTS)
        else:
            print("[LLM Node] Warning: RabbitMQ not available")
        
        # Check model availability
        model_ok = await self.model_handler.is_available()
        
        print("=" * 50)
        print(f"[LLM Node] Node ID: {self.grpc_client.node_id or 'Not registered'}")
        print(f"[LLM Node] RabbitMQ: {'✓' if rabbitmq_ok else '✗'}")
        print(f"[LLM Node] Model: {'✓' if model_ok else '✗ (will load on first task)'}")
        print("=" * 50)
        
        return True
    
    async def process_task(self, task_id: str, json_data: str) -> TextAnalysisResult:
        """
        Process text analysis task.
        
        Args:
            task_id: Task identifier
            json_data: JSON containing original news + VLM results
        """
        self.grpc_client.set_status(NodeStatus.BUSY)
        
        try:
            data = json.loads(json_data)
            print(f"[LLM Node] Processing task {task_id}")
            
            # Extract original data and VLM analysis if present
            original = data.get('original', data)
            vlm_analysis = data.get('vlm_analysis', {})
            
            # Build text for analysis (combine title and content)
            title = original.get('title', '')
            content = original.get('content', '')
            source = original.get('source', '')
            
            text = f"[Source: {source}]\n\n{title}\n\n{content}" if title else content
            
            # Convert vlm_analysis to list format expected by handler
            vlm_results = vlm_analysis.get('results', []) if isinstance(vlm_analysis, dict) else []
            
            # Analyze text
            result = await self.model_handler.analyze_text(
                text=text,
                vlm_results=vlm_results
            )
            
            print(f"[LLM Node] Completed analysis for {task_id}: sentiment={result.sentiment}")
            return result
            
        except Exception as e:
            print(f"[LLM Node] Error processing task: {e}")
            return TextAnalysisResult(
                summary="", sentiment=0, sentiment_label="neutral",
                keywords=[], entities={}, category="other",
                relevance_to_topic="low", error=str(e)
            )
        finally:
            self.grpc_client.set_status(NodeStatus.IDLE)
    
    async def run(self):
        """Run the LLM node - consume from RabbitMQ queue."""
        self._running = True
        
        # Start heartbeat in background
        heartbeat_task = asyncio.create_task(
            self.grpc_client.start_heartbeat_loop()
        )
        
        try:
            print(f"[LLM Node] Consuming from queue: {QUEUE_LLM_TASKS}")
            
            while self._running:
                # Poll for messages (non-blocking)
                message = self.rabbitmq.get_message(QUEUE_LLM_TASKS)
                
                if message:
                    print(f"[LLM Node] Received task: {message.task_id}")
                    
                    # Process the task
                    result = await self.process_task(message.task_id, message.json_data)
                    success = not bool(result.error)
                    
                    # Publish results back
                    result_data = {
                        'task_id': message.task_id,
                        'status': 'SUCCESS' if success else 'FAILED',
                        'error': result.error or '',
                        'result': result.to_dict()
                    }
                    result_msg = QueueMessage(
                        task_id=message.task_id,
                        json_data=json.dumps(result_data)
                    )
                    self.rabbitmq.publish(QUEUE_LLM_RESULTS, result_msg)
                    print(f"[LLM Node] Published results for {message.task_id}")
                else:
                    # No message, wait before polling again
                    await asyncio.sleep(0.5)
                    
        except asyncio.CancelledError:
            pass
        finally:
            heartbeat_task.cancel()
            await self.shutdown()
    
    async def shutdown(self):
        """Shutdown LLM node."""
        print("\n[LLM Node] Shutting down...")
        self._running = False
        self.rabbitmq.close()
        self.grpc_client.stop()
        print("[LLM Node] Shutdown complete")


async def main():
    """Async main entry point."""
    node = LLMNode()
    await node.initialize()
    await node.run()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[LLM Node] Interrupted by user")
