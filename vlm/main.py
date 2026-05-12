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
    QUEUE_VLM_TASKS, QUEUE_VLM_RESULTS,
    MINIO_HOST, MINIO_PORT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_SECURE
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
        self.minio_client = None
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

        if MINIO_HOST:
            try:
                from minio import Minio
                self.minio_client = Minio(
                    f"{MINIO_HOST}:{MINIO_PORT}",
                    access_key=MINIO_ACCESS_KEY,
                    secret_key=MINIO_SECRET_KEY,
                    secure=MINIO_SECURE,
                )
                print(f"[VLM Node] MinIO configured: {MINIO_HOST}:{MINIO_PORT}")
            except Exception as e:
                print(f"[VLM Node] Warning: Could not configure MinIO: {e}")
        
        # Check model availability
        model_ok = await self.model_handler.is_available()
        
        print("=" * 50)
        print(f"[VLM Node] Node ID: {self.grpc_client.node_id or 'Not registered'}")
        print(f"[VLM Node] RabbitMQ: {'✓' if rabbitmq_ok else '✗'}")
        print(f"[VLM Node] Model: {'✓' if model_ok else '✗ (will load on first task)'}")
        print("=" * 50)
        
        return True
    
    async def _download_image(self, url: str) -> bytes | None:
        """Download image from URL and return bytes."""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        return await resp.read()
        except Exception as e:
            print(f"[VLM Node] Failed to download image {url[:50]}: {e}")
        return None

    def _get_minio_image(self, path: str) -> bytes | None:
        """Read image bytes from a minio://bucket/object path."""
        if not self.minio_client or not path.startswith("minio://"):
            return None

        try:
            minio_path = path.removeprefix("minio://")
            bucket, object_name = minio_path.split("/", 1)
            response = self.minio_client.get_object(bucket, object_name)
            return response.read()
        except Exception as e:
            print(f"[VLM Node] Failed to read MinIO image {path}: {e}")
            return None
        finally:
            if 'response' in locals():
                response.close()
                response.release_conn()
    
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
                image_bytes = None
                image_url = None
                
                if isinstance(main_image, dict):
                    image_bytes = main_image.get('bytes')
                    image_url = (
                        main_image.get('url')
                        or main_image.get('minio_path')
                        or main_image.get('original_url')
                    )
                elif isinstance(main_image, str):
                    image_url = main_image
                
                if not image_bytes and image_url and image_url.startswith('http'):
                    image_bytes = await self._download_image(image_url)
                elif not image_bytes and image_url and image_url.startswith('minio://'):
                    image_bytes = self._get_minio_image(image_url)
                
                if image_bytes:
                    result = await self.model_handler.analyze_image(image_bytes, context)
                    result.minio_path = image_url
                    results.append(result)
            
            # Process content images
            content_images = media.get('content_images', [])
            for img in content_images[:3]:  # Limit to 3 images
                image_bytes = None
                image_url = None
                
                if isinstance(img, dict):
                    image_bytes = img.get('bytes')
                    image_url = (
                        img.get('url')
                        or img.get('minio_path')
                        or img.get('original_url')
                    )
                elif isinstance(img, str):
                    image_url = img
                
                if not image_bytes and image_url and image_url.startswith('http'):
                    image_bytes = await self._download_image(image_url)
                elif not image_bytes and image_url and image_url.startswith('minio://'):
                    image_bytes = self._get_minio_image(image_url)
                
                if image_bytes:
                    result = await self.model_handler.analyze_image(image_bytes, context)
                    result.minio_path = image_url
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

    @staticmethod
    def _has_image_references(json_data: str) -> bool:
        """Return True when the task payload contains images VLM was expected to analyze."""
        try:
            data = json.loads(json_data)
        except Exception:
            return False

        media = data.get('media') or {}
        return bool(media.get('main_image') or media.get('content_images'))

    @staticmethod
    def _is_successful_result(results: list[ImageAnalysisResult], expected_images: bool) -> tuple[bool, str]:
        """VLM may return per-image errors; only advance when at least one analysis succeeded."""
        successful = [r for r in results if not r.error]
        if successful:
            return True, ""
        if expected_images:
            errors = [r.error for r in results if r.error]
            return False, "; ".join(errors) or "no image analysis was produced"
        return True, ""
    
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
                    expected_images = self._has_image_references(message.json_data)
                    success, error = self._is_successful_result(results, expected_images)
                    
                    # Publish results back
                    result_data = {
                        'task_id': message.task_id,
                        'status': 'SUCCESS' if success else 'FAILED',
                        'error': error,
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
