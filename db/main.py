"""
DB Node Main Entry Point
Manages PostgreSQL and MinIO connections, registers with Orchestrator.
"""
import asyncio
import signal
import sys
import json
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.config import (
    HEARTBEAT_INTERVAL,
    RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_USER, RABBITMQ_PASSWORD,
    QUEUE_DB_TASKS
)
from db.services.grpc_client import GRPCClient, NodeStatus
from db.services.postgres_manager import PostgresManager
from db.services.minio_manager import MinIOManager
from db.services.rabbitmq_consumer import RabbitMQConsumer


class DBNode:
    """
    Main DB Node class.
    Manages database and storage connections.
    """
    
    def __init__(self):
        self.grpc_client = GRPCClient()
        self.postgres = PostgresManager()
        self.minio = MinIOManager()
        self.rabbitmq = RabbitMQConsumer(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
            user=RABBITMQ_USER,
            password=RABBITMQ_PASSWORD
        )
        self._running = False
    
    async def initialize(self) -> bool:
        """Initialize all connections."""
        print("=" * 50)
        print("DB NODE STARTING")
        print("=" * 50)
        
        # Connect to Orchestrator
        if not self.grpc_client.connect():
            print("[DB Node] Warning: Could not connect to Orchestrator")
        else:
            if not self.grpc_client.register():
                print("[DB Node] Warning: Could not register with Orchestrator")
        
        # Connect to PostgreSQL
        postgres_ok = await self.postgres.connect()
        if not postgres_ok:
            print("[DB Node] Warning: PostgreSQL not available")
        
        # Connect to MinIO
        minio_ok = self.minio.connect()
        if not minio_ok:
            print("[DB Node] Warning: MinIO not available")
        
        # Connect to RabbitMQ
        rabbitmq_ok = self.rabbitmq.connect()
        if rabbitmq_ok:
            self.rabbitmq.declare_queue(QUEUE_DB_TASKS)
        else:
            print("[DB Node] Warning: RabbitMQ not available")
        
        print("=" * 50)
        print(f"[DB Node] Node ID: {self.grpc_client.node_id or 'Not registered'}")
        print(f"[DB Node] PostgreSQL: {'✓' if postgres_ok else '✗'}")
        print(f"[DB Node] MinIO: {'✓' if minio_ok else '✗'}")
        print(f"[DB Node] RabbitMQ: {'✓' if rabbitmq_ok else '✗'}")
        print("=" * 50)
        
        return True
    
    async def process_crawl_data(self, json_data: str) -> tuple[str, bool]:
        """
        Process incoming crawl data.
        
        1. Parse JSON
        2. Download images to MinIO
        3. Store in PostgreSQL
        
        Returns:
            (news_id, is_duplicate)
        """
        self.grpc_client.set_status(NodeStatus.BUSY)
        
        try:
            data = json.loads(json_data)
            
            # Generate news ID
            news_id = self.postgres.generate_news_id(data['url'])
            
            # Download and store images
            if 'media' in data and data['media']:
                updated_media = await self.minio.process_news_images(
                    news_id, 
                    data['media']
                )
                data['media'] = updated_media
            
            # Store in PostgreSQL
            news_id, is_duplicate = await self.postgres.insert_news(data)
            
            return news_id, is_duplicate
            
        except Exception as e:
            print(f"[DB Node] Process error: {e}")
            raise
        finally:
            self.grpc_client.set_status(NodeStatus.IDLE)
    
    async def get_queue_items(self, limit: int = 10) -> list:
        """Get unprocessed items from database."""
        return await self.postgres.get_unprocessed(limit)
    
    async def save_vlm_results(self, news_id: str, results: list):
        """Save VLM analysis results."""
        for result in results:
            await self.postgres.save_vlm_analysis(news_id, result)
        await self.postgres.mark_vlm_processed(news_id)
    
    async def save_llm_results(self, news_id: str, result: dict):
        """Save LLM analysis results."""
        await self.postgres.save_llm_analysis(news_id, result)
        await self.postgres.mark_llm_processed(news_id)
    
    async def run(self):
        """Run the DB node (async)."""
        self._running = True
        
        # Start heartbeat in background
        heartbeat_task = asyncio.create_task(
            self.grpc_client.start_heartbeat_loop()
        )
        
        try:
            print(f"[DB Node] Polling queue: {QUEUE_DB_TASKS}")
            
            # Main loop - poll for analysis tasks
            while self._running:
                # Check for analysis tasks from orchestrator
                message = self.rabbitmq.get_message(QUEUE_DB_TASKS)
                
                if message:
                    print(f"[DB Node] Received task: {message.task_id}")
                    await self._process_analysis_task(message.task_id, message.json_data)
                else:
                    await asyncio.sleep(0.5)
                
        except asyncio.CancelledError:
            pass
        finally:
            heartbeat_task.cancel()
            await self.shutdown()
    
    async def _process_analysis_task(self, task_id: str, json_data: str):
        """
        Process analysis task from orchestrator.
        Stores VLM and LLM results in database.
        """
        self.grpc_client.set_status(NodeStatus.BUSY)
        
        try:
            data = json.loads(json_data)

            if data.get('type') == 'agent_surface_articles':
                await self._process_agent_surface_articles(task_id, data)
                return

            if data.get('type') == 'research_mission':
                await self._process_research_mission(task_id, data)
                return
            
            # Extract components
            original = data.get('original', {})
            vlm_analysis = data.get('vlm_analysis', {})
            llm_analysis = data.get('llm_analysis', {})
            
            # Get or create news_id from original URL
            url = original.get('url', task_id)
            news_id = self.postgres.generate_news_id(url)
            
            # First, ensure the news item exists in DB
            # Check if it exists, if not insert it
            existing = await self.postgres.get_news_by_id(news_id)
            if not existing:
                # Insert the original news data
                await self.postgres.insert_news(original)
                print(f"[DB Node] Inserted news: {news_id}")
            
            # Save VLM results if present
            if vlm_analysis and vlm_analysis.get('results'):
                for result in vlm_analysis['results']:
                    await self.postgres.save_vlm_analysis(news_id, result)
                await self.postgres.mark_vlm_processed(news_id)
                print(f"[DB Node] Saved VLM analysis for {news_id}")
            
            # Save LLM results if present
            if llm_analysis and llm_analysis.get('result'):
                await self.postgres.save_llm_analysis(news_id, llm_analysis['result'])
                await self.postgres.mark_llm_processed(news_id)
                print(f"[DB Node] Saved LLM analysis for {news_id}")
            
            print(f"[DB Node] Completed task: {task_id}")
            
        except Exception as e:
            print(f"[DB Node] Error processing task {task_id}: {e}")
        finally:
            self.grpc_client.set_status(NodeStatus.IDLE)

    async def _process_research_mission(self, task_id: str, data: dict):
        """Store a completed CUA research response."""
        mission_id = data.get('mission_id') or task_id
        topic = data.get('topic') or mission_id
        status = str(data.get('status', 'completed')).lower()
        report = data.get('report', {})
        state = data.get('state', {})

        await self.postgres.insert_research_mission({
            'mission_id': mission_id,
            'topic': topic,
            'status': status
        })

        if status in ('completed', 'complete', 'success'):
            await self.postgres.complete_research_mission(mission_id, report, state)

        print(f"[DB Node] Stored research mission: {mission_id}")

    async def _process_agent_surface_articles(self, task_id: str, data: dict):
        """Store CUA surface output as news rows with source_type=agent_surface."""
        mission_id = data.get('mission_id') or task_id
        articles = data.get('articles') or []
        inserted = 0
        duplicates = 0

        for article in articles:
            if not isinstance(article, dict) or not article.get('url'):
                continue
            article['source_type'] = article.get('source_type') or 'agent_surface'
            article['mission_id'] = article.get('mission_id') or mission_id
            news_id, is_duplicate = await self.postgres.insert_news(article)
            if is_duplicate:
                duplicates += 1
            else:
                inserted += 1

            vlm_results = (article.get('vlm_analysis') or {}).get('results') or []
            valid_vlm_results = [r for r in vlm_results if isinstance(r, dict) and not r.get('error')]
            if valid_vlm_results:
                for result in valid_vlm_results:
                    await self.postgres.save_vlm_analysis(news_id, result)
                await self.postgres.mark_vlm_processed(news_id)

            llm_result = (article.get('llm_analysis') or {}).get('result')
            if isinstance(llm_result, dict) and not llm_result.get('error'):
                await self.postgres.save_llm_analysis(news_id, llm_result)
                await self.postgres.mark_llm_processed(news_id)

        print(
            f"[DB Node] Stored CUA surface articles: "
            f"mission_id={mission_id}, inserted={inserted}, duplicates={duplicates}"
        )
    
    async def shutdown(self):
        """Shutdown all connections."""
        print("\n[DB Node] Shutting down...")
        self._running = False
        
        self.grpc_client.stop()
        self.rabbitmq.close()
        await self.postgres.close()
        
        print("[DB Node] Shutdown complete")


async def main():
    """Async main entry point."""
    node = DBNode()
    
    await node.initialize()
    
    # Handle Ctrl+C
    loop = asyncio.get_event_loop()
    
    def signal_handler():
        node._running = False
    
    try:
        loop.add_signal_handler(signal.SIGINT, signal_handler)
    except NotImplementedError:
        # Windows doesn't support add_signal_handler
        pass
    
    await node.run()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[DB Node] Interrupted by user")
