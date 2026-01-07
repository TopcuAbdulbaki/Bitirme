"""
VLM Node Main Entry Point
Vision Language Model for image analysis.
"""
import asyncio
import json
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from vlm.config import HEARTBEAT_INTERVAL, MODEL_MODE
from vlm.services.grpc_client import GRPCClient, NodeStatus
from vlm.services.model_handler import get_vlm_handler, ImageAnalysisResult


class VLMNode:
    """
    Main VLM Node class.
    Processes image analysis tasks.
    """
    
    def __init__(self):
        self.grpc_client = GRPCClient()
        self.model_handler = get_vlm_handler()
        self._running = False
    
    async def initialize(self) -> bool:
        """Initialize VLM node."""
        print("=" * 50)
        print("VLM NODE STARTING")
        print(f"Mode: {MODEL_MODE}")
        print("=" * 50)
        
        # Connect to Orchestrator
        if not self.grpc_client.connect():
            print("[VLM Node] Warning: Could not connect to Orchestrator")
        else:
            if not self.grpc_client.register():
                print("[VLM Node] Warning: Could not register with Orchestrator")
        
        # Check model availability
        model_ok = await self.model_handler.is_available()
        if not model_ok and MODEL_MODE == 'lmstudio':
            # print("[VLM Node] Warning: LM Studio not available. Make sure it's running.")
            pass
        
        print("=" * 50)
        print(f"[VLM Node] Node ID: {self.grpc_client.node_id or 'Not registered'}")
        print(f"[VLM Node] Model: {'✓' if model_ok else '✗ (will retry)'}")
        print("=" * 50)
        
        return True
    
    async def process_task(self, task_id: str, json_data: str) -> list[ImageAnalysisResult]:
        """
        Process image analysis task.
        
        Args:
            task_id: Task identifier
            json_data: JSON containing news data with images
            
        Returns:
            List of ImageAnalysisResult
        """
        self.grpc_client.set_status(NodeStatus.BUSY)
        results = []
        
        try:
            data = json.loads(json_data)
            
            # Get context from news content
            context = data.get('content', '')[:500]  # First 500 chars
            
            # Process media
            media = data.get('media', {})
            
            # Process main image
            main_image = media.get('main_image')
            if main_image:
                image_path = main_image.get('minio_path') if isinstance(main_image, dict) else main_image
                # Note: In production, we'd request image bytes from DB node
                # For now, we'll need image bytes passed in
                if 'bytes' in (main_image if isinstance(main_image, dict) else {}):
                    result = await self.model_handler.analyze_image(
                        main_image['bytes'],
                        context
                    )
                    result.minio_path = image_path
                    results.append(result)
            
            # Process content images
            content_images = media.get('content_images', [])
            for img in content_images[:3]:  # Limit to 3 images
                if isinstance(img, dict) and 'bytes' in img:
                    result = await self.model_handler.analyze_image(
                        img['bytes'],
                        context
                    )
                    result.minio_path = img.get('minio_path')
                    results.append(result)
            
            print(f"[VLM Node] Processed {len(results)} images for task {task_id}")
            
        except Exception as e:
            print(f"[VLM Node] Error processing task: {e}")
            results.append(ImageAnalysisResult(
                minio_path=None, original_url=None,
                description="", objects=[], sentiment="neutral", relevance="low",
                error=str(e)
            ))
        finally:
            self.grpc_client.set_status(NodeStatus.IDLE)
        
        return results
    
    async def run(self):
        """Run the VLM node."""
        self._running = True
        
        # Start heartbeat in background
        heartbeat_task = asyncio.create_task(
            self.grpc_client.start_heartbeat_loop()
        )
        
        try:
            # Main loop - wait for tasks via RabbitMQ or gRPC
            print("[VLM Node] Waiting for tasks...")
            while self._running:
                await asyncio.sleep(1)
                
        except asyncio.CancelledError:
            pass
        finally:
            heartbeat_task.cancel()
            await self.shutdown()
    
    async def shutdown(self):
        """Shutdown VLM node."""
        print("\n[VLM Node] Shutting down...")
        self._running = False
        self.grpc_client.stop()
        print("[VLM Node] Shutdown complete")


async def main():
    """Async main entry point."""
    node = VLMNode()
    await node.initialize()
    await node.run()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[VLM Node] Interrupted by user")
