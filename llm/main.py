"""
LLM Node Main Entry Point
Language Model for text analysis and sentiment classification.
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from llm.config import HEARTBEAT_INTERVAL, MODEL_MODE
from llm.services.grpc_client import GRPCClient, NodeStatus
from llm.services.model_handler import get_llm_handler, TextAnalysisResult


class LLMNode:
    """Main LLM Node class."""
    
    def __init__(self):
        self.grpc_client = GRPCClient()
        self.model_handler = get_llm_handler()
        self._running = False
    
    async def initialize(self) -> bool:
        """Initialize LLM node."""
        print("=" * 50)
        print("LLM NODE STARTING")
        print(f"Mode: {MODEL_MODE}")
        print("=" * 50)
        
        if not self.grpc_client.connect():
            print("[LLM Node] Warning: Could not connect to Orchestrator")
        else:
            if not self.grpc_client.register():
                print("[LLM Node] Warning: Could not register with Orchestrator")
        
        model_ok = await self.model_handler.is_available()
        if not model_ok and MODEL_MODE == 'lmstudio':
            # print("[LLM Node] Warning: LM Studio not available.")
            pass
        
        print("=" * 50)
        print(f"[LLM Node] Node ID: {self.grpc_client.node_id or 'Not registered'}")
        print(f"[LLM Node] Model: {'✓' if model_ok else '✗ (will retry)'}")
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
            
            # Get text content
            original = data.get('original', data)
            text = original.get('content', '')
            
            # Get VLM results if available
            vlm_results = data.get('vlm_analysis', [])
            
            # Analyze
            result = await self.model_handler.analyze_text(text, vlm_results)
            
            print(f"[LLM Node] Processed task {task_id}: sentiment={result.sentiment}")
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
        """Run the LLM node."""
        self._running = True
        
        heartbeat_task = asyncio.create_task(
            self.grpc_client.start_heartbeat_loop()
        )
        
        try:
            print("[LLM Node] Waiting for tasks...")
            while self._running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            heartbeat_task.cancel()
            await self.shutdown()
    
    async def shutdown(self):
        print("\n[LLM Node] Shutting down...")
        self._running = False
        self.grpc_client.stop()
        print("[LLM Node] Shutdown complete")


async def main():
    node = LLMNode()
    await node.initialize()
    await node.run()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[LLM Node] Interrupted by user")
