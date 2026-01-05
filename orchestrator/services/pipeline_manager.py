"""
Pipeline Manager
Orchestrates the flow of data through the system.
"""
import uuid
import json
from typing import Optional
from dataclasses import dataclass
from enum import Enum

from .node_registry import NodeRegistry, NodeType


class PipelineStage(Enum):
    """Stages in the processing pipeline."""
    CRAWLED = "crawled"
    STORED = "stored"
    VLM_ANALYZING = "vlm_analyzing"
    VLM_COMPLETE = "vlm_complete"
    LLM_ANALYZING = "llm_analyzing"
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
        """Handle completed crawl - send to DB for storage."""
        task = self._tasks.get(task_id)
        if not task:
            task = self.create_task(json_data)
        else:
            task.raw_data = json_data
        
        task.stage = PipelineStage.CRAWLED
        print(f"[Pipeline] {task_id} -> CRAWLED, ready for DB storage")
        
        # TODO: Send to DB node via gRPC
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
    
    def on_llm_complete(self, task_id: str, result_json: str):
        """Handle LLM analysis complete - store final results."""
        task = self._tasks.get(task_id)
        if not task:
            print(f"[Pipeline] Unknown task: {task_id}")
            return
        
        task.llm_result = result_json
        task.stage = PipelineStage.COMPLETE
        print(f"[Pipeline] {task_id} -> COMPLETE")
        
        # TODO: Send final results to DB for storage
    
    def on_task_failed(self, task_id: str, error: str):
        """Handle task failure."""
        task = self._tasks.get(task_id)
        if task:
            task.stage = PipelineStage.FAILED
            task.error = error
            print(f"[Pipeline] {task_id} -> FAILED: {error}")
    
    def get_task(self, task_id: str) -> Optional[PipelineTask]:
        """Get task by ID."""
        return self._tasks.get(task_id)
    
    def get_pending_tasks(self) -> list[PipelineTask]:
        """Get tasks that are not complete or failed."""
        return [
            t for t in self._tasks.values()
            if t.stage not in (PipelineStage.COMPLETE, PipelineStage.FAILED)
        ]
    
    def cleanup_completed(self, max_age_seconds: int = 3600):
        """Remove completed tasks older than max_age."""
        # TODO: Implement based on timestamps
        pass
