"""
Pipeline Manager
Orchestrates the flow of data through the system.
"""
import uuid
import json
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum

from .node_registry import NodeRegistry, NodeType
import grpc
from orchestrator.generated import orchestrator_pb2 as pb2
from orchestrator.generated import orchestrator_pb2_grpc as pb2_grpc


class PipelineStage(Enum):
    """Stages in the processing pipeline."""
    CRAWLED = "crawled"
    STORED = "stored"
    VLM_ANALYZING = "vlm_analyzing"
    VLM_COMPLETE = "vlm_complete"
    LLM_ANALYZING = "llm_analyzing"
    AGENT_SURFACE = "agent_surface"
    AGENT_RESEARCH = "agent_research"
    AGENT_COMPLETE = "agent_complete"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class PipelineTask:
    """Tracks a single news item through the pipeline."""
    task_id: str
    news_id: Optional[str] = None
    stage: PipelineStage = PipelineStage.CRAWLED
    raw_data: Optional[str] = None  # JSON string
    vlm_result: Optional[str] = None
    llm_result: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        return {
            'task_id': self.task_id,
            'news_id': self.news_id,
            'stage': self.stage.value,
            'error': self.error
        }


class PipelineManager:
    """
    Manages the processing pipeline for news items.
    
    Flow:
    1. Crawler sends raw data -> CRAWLED
    2. Store in DB -> STORED
    3. Send to VLM queue -> VLM_ANALYZING
    4. VLM completes -> VLM_COMPLETE
    5. Send to LLM queue -> LLM_ANALYZING
    6. LLM completes -> COMPLETE
    7. Store final results in DB
    """
    
    def __init__(self, registry: NodeRegistry, rabbitmq_manager=None):
        self.registry = registry
        self.rabbitmq = rabbitmq_manager
        self._tasks: dict[str, PipelineTask] = {}
        print("[Pipeline] Manager initialized")
    
    def generate_task_id(self) -> str:
        """Generate unique task ID."""
        return f"task_{uuid.uuid4().hex[:12]}"
    
    def create_task(self, raw_data: str) -> PipelineTask:
        """Create a new pipeline task from crawled data."""
        task = PipelineTask(
            task_id=self.generate_task_id(),
            raw_data=raw_data,
            stage=PipelineStage.CRAWLED
        )
        self._tasks[task.task_id] = task
        print(f"[Pipeline] Created task: {task.task_id}")
        return task
    
    def on_crawl_complete(self, task_id: str, json_data: str):
        """Handle completed crawl - send directly to VLM queue for analysis."""
        task = self._tasks.get(task_id)
        if not task:
            task = self.create_task(json_data)
        else:
            task.raw_data = json_data
        
        task.stage = PipelineStage.CRAWLED
        print(f"[Pipeline] {task_id} -> CRAWLED")
        
        # Send directly to VLM queue for image analysis
        if self.rabbitmq:
            success = self.rabbitmq.publish_vlm_task(task.task_id, json_data)
            if success:
                task.stage = PipelineStage.VLM_ANALYZING
                print(f"[Pipeline] {task.task_id} -> VLM_ANALYZING (published to queue)")
            else:
                print(f"[Pipeline] Failed to publish {task.task_id} to VLM queue")
        else:
            print(f"[Pipeline] RabbitMQ not available, cannot process {task_id}")
        
        return task
    
    def on_store_complete(self, task_id: str, news_id: str):
        """Handle DB storage complete - queue for VLM analysis."""
        task = self._tasks.get(task_id)
        if not task:
            print(f"[Pipeline] Unknown task: {task_id}")
            return
        
        task.news_id = news_id
        task.stage = PipelineStage.STORED
        
        # Send to VLM queue
        if self.rabbitmq:
            self.rabbitmq.publish_vlm_task(task_id, task.raw_data)
            task.stage = PipelineStage.VLM_ANALYZING
            print(f"[Pipeline] {task_id} -> VLM_ANALYZING")
    
    def on_vlm_complete(self, task_id: str, analysis_json: str):
        """Handle VLM analysis complete - queue for LLM."""
        task = self._tasks.get(task_id)
        if not task:
            print(f"[Pipeline] Unknown task: {task_id}")
            return
        
        task.vlm_result = analysis_json
        task.stage = PipelineStage.VLM_COMPLETE
        
        # Combine original data + VLM result for LLM
        combined = json.dumps({
            'original': json.loads(task.raw_data) if task.raw_data else {},
            'vlm_analysis': json.loads(analysis_json)
        })
        
        # Send to LLM queue
        if self.rabbitmq:
            self.rabbitmq.publish_llm_task(task_id, combined)
            task.stage = PipelineStage.LLM_ANALYZING
            print(f"[Pipeline] {task_id} -> LLM_ANALYZING")

    def on_vlm_failed(self, task_id: str, error: str):
        """Handle VLM failure without continuing to LLM."""
        self.on_task_failed(task_id, f"VLM failed: {error}")
    
    def on_llm_complete(self, task_id: str, result_json: str):
        """Handle LLM analysis complete - send to DB for storage."""
        task = self._tasks.get(task_id)
        if not task:
            print(f"[Pipeline] Unknown task: {task_id}")
            return
        
        task.llm_result = result_json
        task.stage = PipelineStage.COMPLETE
        task.completed_at = datetime.utcnow()
        print(f"[Pipeline] {task_id} -> COMPLETE")
        
        # Publish to DB queue for final storage
        if self.rabbitmq:
            try:
                db_payload = json.dumps({
                    'task_id': task_id,
                    'original': json.loads(task.raw_data) if task.raw_data else {},
                    'vlm_analysis': json.loads(task.vlm_result) if task.vlm_result else {},
                    'llm_analysis': json.loads(result_json)
                })
                success = self.rabbitmq.publish_db_task(task_id, db_payload)
                if success:
                    print(f"[Pipeline] {task_id} -> Published to DB queue")
            except Exception as e:
                print(f"[Pipeline] Error publishing to DB queue: {e}")

    def on_llm_failed(self, task_id: str, error: str):
        """Handle LLM failure without continuing to DB."""
        self.on_task_failed(task_id, f"LLM failed: {error}")
    
    def _fan_out_to_cua(self, keywords: str) -> bool:
        """
        Check for idle CUA node and publish agent task.
        
        Args:
            keywords: Search keywords for agent research
        
        Returns:
            True if task was published, False otherwise
        """
        # Find idle CUA node
        node = self.registry.get_idle_node(NodeType.CUA)
        if not node:
            print("[Pipeline] No idle CUA node available for agent tasks")
            return False
        
        print(f"[Pipeline] Found idle CUA node: {node.node_id} at {node.host}:{node.port}")

        if not self.rabbitmq:
            print("[Pipeline] RabbitMQ not available, cannot publish to agent_tasks")
            return False
        
        # Create agent task
        task_id = self.generate_task_id()
        task_data_dict = {
            'task_id': task_id,
            'mode': 'research',
            'topic': keywords,
            'query': keywords,
            'params': {
                'max_articles': 10
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        task_data = json.dumps(task_data_dict)
        self._tasks[task_id] = PipelineTask(
            task_id=task_id,
            raw_data=task_data,
            stage=PipelineStage.AGENT_RESEARCH
        )
        
        success = self.rabbitmq.publish_agent_task(task_id, task_data)
        if success:
            print(f"[Pipeline] {task_id} -> Published to agent_tasks queue")
            self.registry.set_node_busy(node.node_id, task_id)
            return True

        print(f"[Pipeline] Failed to publish {task_id} to agent_tasks queue")
        self.on_task_failed(task_id, "Failed to publish to agent_tasks queue")
        return False
    
    def on_agent_surface_complete(self, task_id: str, surface_data: str):
        """Handle agent surface research completion."""
        task = self._tasks.get(task_id)
        if not task:
            print(f"[Pipeline] Unknown task: {task_id}")
            return
        
        task.stage = PipelineStage.AGENT_SURFACE
        print(f"[Pipeline] {task_id} -> AGENT_SURFACE")
        self._publish_agent_result_to_db(task_id, surface_data)
    
    def on_agent_research_complete(self, task_id: str, research_data: str):
        """Handle agent research completion."""
        task = self._tasks.get(task_id)
        if not task:
            print(f"[Pipeline] Unknown task: {task_id}")
            return
        
        task.stage = PipelineStage.AGENT_RESEARCH
        print(f"[Pipeline] {task_id} -> AGENT_RESEARCH")
        self._publish_agent_result_to_db(task_id, research_data)

    def _publish_agent_result_to_db(self, task_id: str, result_data: str):
        """Publish completed CUA result to DB for research_missions storage."""
        if not self.rabbitmq:
            print("[Pipeline] RabbitMQ not available, cannot store agent result")
            return

        try:
            result = json.loads(result_data)
            request = json.loads(self._tasks[task_id].raw_data or "{}")
            db_payload = json.dumps({
                'type': 'research_mission',
                'mission_id': task_id,
                'topic': request.get('topic') or request.get('query') or result.get('topic') or result.get('query'),
                'status': str(result.get('status', 'COMPLETED')).lower(),
                'report': result,
                'state': result.get('state', {})
            })
            if self.rabbitmq.publish_db_task(task_id, db_payload):
                self._tasks[task_id].stage = PipelineStage.AGENT_COMPLETE
                self._tasks[task_id].completed_at = datetime.utcnow()
                self._release_node_for_task(task_id)
                print(f"[Pipeline] {task_id} -> Agent result published to DB queue")
        except Exception as e:
            self.on_task_failed(task_id, f"Agent DB publish failed: {e}")

    def _release_node_for_task(self, task_id: str):
        """Mark any node assigned to this task as idle."""
        for node in self.registry.get_all_nodes():
            if node.current_task_id == task_id:
                self.registry.set_node_idle(node.node_id)
    
    def on_task_failed(self, task_id: str, error: str):
        """Handle task failure."""
        task = self._tasks.get(task_id)
        if task:
            task.stage = PipelineStage.FAILED
            task.error = error
            task.completed_at = datetime.utcnow()
            self._release_node_for_task(task_id)
            print(f"[Pipeline] {task_id} -> FAILED: {error}")
    
    def get_task(self, task_id: str) -> Optional[PipelineTask]:
        """Get task by ID."""
        return self._tasks.get(task_id)
    
    def get_pending_tasks(self) -> list[PipelineTask]:
        """Get tasks that are not complete or failed."""
        return [
            t for t in self._tasks.values()
            if t.stage not in (PipelineStage.COMPLETE, PipelineStage.AGENT_COMPLETE, PipelineStage.FAILED)
        ]
    
    async def trigger_crawl(self, urls: list[str] = None):
        """
        Trigger a crawl task on an available crawler node.
        """
        urls = urls or []
        print(f"[Pipeline] Attempting to trigger crawl for {len(urls)} URLs...")
        
        # 1. Find idle crawler
        node = self.registry.get_idle_node(NodeType.CRAWLER)
        if not node:
            print("[Pipeline] No idle crawler available.")
            return False
            
        print(f"[Pipeline] Found idle crawler: {node.node_id} at {node.host}:{node.port}")
        
        # 2. Create gRPC channel to the worker
        if not node.host or not node.port:
            print(f"[Pipeline] Crawler {node.node_id} has missing connectivity info.")
            return False
            
        try:
            target = f"{node.host}:{node.port}"
            async with grpc.aio.insecure_channel(target) as channel:
                stub = pb2_grpc.CrawlerServiceStub(channel)
                
                # 3. Create Task
                task_id = self.generate_task_id()
                
                # 4. Call ExecuteCrawl
                request = pb2.CrawlTaskRequest(task_id=task_id, urls=urls)
                response = await stub.ExecuteCrawl(request)
                
                if response.status == 0: # SUCCESS
                    self.registry.set_node_busy(node.node_id, task_id)
                    print(f"[Pipeline] Triggered crawl task {task_id} successfully.")
                    return True
                else:
                    print(f"[Pipeline] Failed to trigger crawl: {response.error_message}")
                    return False
                    
        except Exception as e:
            print(f"[Pipeline] RPC Error triggering crawl: {e}")
            return False

    def cleanup_completed(self, max_age_seconds: int = 3600):
        """Remove completed tasks older than max_age."""
        cutoff = datetime.utcnow() - timedelta(seconds=max_age_seconds)
        to_remove = [
            tid for tid, task in self._tasks.items()
            if task.stage in (PipelineStage.COMPLETE, PipelineStage.AGENT_COMPLETE, PipelineStage.FAILED)
            and task.completed_at 
            and task.completed_at < cutoff
        ]
        for tid in to_remove:
            del self._tasks[tid]
        if to_remove:
            print(f"[Pipeline] Cleaned up {len(to_remove)} old tasks")
