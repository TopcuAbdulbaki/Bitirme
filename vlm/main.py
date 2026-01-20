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

from vlm.config import (
    HEARTBEAT_INTERVAL, MODEL_MODE,
    RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_USER, RABBITMQ_PASSWORD,
    QUEUE_VLM_TASKS, QUEUE_VLM_RESULTS
)
from vlm.services.grpc_client import GRPCClient, NodeStatus
from vlm.services.model_handler import get_vlm_handler, ImageAnalysisResult
from vlm.services.rabbitmq_consumer import RabbitMQConsumer, QueueMessage


class VLMNode:
    """
    Main VLM Node class.
    Processes image analysis tasks from RabbitMQ queue.
    """
    
    def __init__(self):
        self.grpc_client = GRPCClient()
        self.model_handler = get_vlm_handler()
        self.rabbitmq = RabbitMQConsumer(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
            user=RABBITMQ_USER,
            password=RABBITMQ_PASSWORD
        )
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
        
        # Connect to RabbitMQ
        rabbitmq_ok = self.rabbitmq.connect()
        if rabbitmq_ok:
            self.rabbitmq.declare_queue(QUEUE_VLM_TASKS)
            self.rabbitmq.declare_queue(QUEUE_VLM_RESULTS)
        else:
            print("[VLM Node] Warning: RabbitMQ not available")
        
        # Check model availability
        model_ok = await self.model_handler.is_available()
        
        print("=" * 50)
        print(f"[VLM Node] Node ID: {self.grpc_client.node_id or 'Not registered'}")
        print(f"[VLM Node] RabbitMQ: {'✓' if rabbitmq_ok else '✗'}")
        print(f"[VLM Node] Model: {'✓' if model_ok else '✗ (will load on first task)'}")
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
            print(f"[VLM Node] Processing task {task_id}")
            
            # Get context from news content
            context = data.get('content', '')[:500]  # First 500 chars
            
            # Process media
            media = data.get('media', {})
            
            # Process main image
            main_image = media.get('main_image')
            if main_image:
                image_path = main_image.get('minio_path') if isinstance(main_image, dict) else main_image
                if isinstance(main_image, dict) and 'bytes' in main_image:
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
        """Run the VLM node - consume from RabbitMQ queue."""
        self._running = True
        
        # Start heartbeat in background
        heartbeat_task = asyncio.create_task(
            self.grpc_client.start_heartbeat_loop()
        )
        
        try:
            print(f"[VLM Node] Consuming from queue: {QUEUE_VLM_TASKS}")
            
            while self._running:
                # Poll for messages (non-blocking)
                message = self.rabbitmq.get_message(QUEUE_VLM_TASKS)
                
                if message:
                    print(f"[VLM Node] Received task: {message.task_id}")
                    
                    # Process the task
                    results = await self.process_task(message.task_id, message.json_data)
                    
                    # Publish results back
                    result_data = {
                        'task_id': message.task_id,
                        'results': [r.to_dict() for r in results]
                    }
                    result_msg = QueueMessage(
                        task_id=message.task_id,
                        json_data=json.dumps(result_data)
                    )
                    self.rabbitmq.publish(QUEUE_VLM_RESULTS, result_msg)
                    print(f"[VLM Node] Published results for {message.task_id}")
                else:
                    # No message, wait before polling again
                    await asyncio.sleep(0.5)
                    
        except asyncio.CancelledError:
            pass
        finally:
            heartbeat_task.cancel()
            await self.shutdown()
    
    async def shutdown(self):
        """Shutdown VLM node."""
        print("\n[VLM Node] Shutting down...")
        self._running = False
        self.rabbitmq.close()
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
