"""
Node Registry Service
Tracks and manages connected nodes.
"""
import uuid
import hashlib
from datetime import datetime
from enum import Enum
from typing import Dict, Optional
from dataclasses import dataclass, field


class NodeType(Enum):
    CRAWLER = "crawler"
    DB = "db"
    VLM = "vlm"
    LLM = "llm"


class NodeStatus(Enum):
    IDLE = 0
    BUSY = 1
    ERROR = 2
    OFFLINE = 3


@dataclass
class NodeInfo:
    """Information about a registered node."""
    node_id: str
    node_type: NodeType
    status: NodeStatus = NodeStatus.IDLE
    host: str = ""
    port: int = 0
    registered_at: datetime = field(default_factory=datetime.now)
    last_heartbeat: datetime = field(default_factory=datetime.now)
    current_task_id: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            'node_id': self.node_id,
            'node_type': self.node_type.value,
            'status': self.status.name,
            'registered_at': self.registered_at.isoformat(),
            'last_heartbeat': self.last_heartbeat.isoformat(),
            'current_task_id': self.current_task_id
        }


class NodeRegistry:
    """
    Registry for tracking all connected nodes.
    Thread-safe singleton pattern.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._nodes: Dict[str, NodeInfo] = {}
        self._initialized = True
        print("[NodeRegistry] Initialized")
    
    def _generate_node_id(self, node_type: str) -> str:
        """Generate unique node ID: {type}_{hash}"""
        unique = f"{node_type}_{uuid.uuid4().hex}"
        hash_part = hashlib.sha256(unique.encode()).hexdigest()[:8]
        return f"{node_type}_{hash_part}"
    
    def register(self, node_type: str, host: str, port: int) -> tuple[bool, str, str]:
        """
        Register a new node.
        
        Returns:
            (success, node_id, message)
        """
        try:
            # Validate node type
            try:
                nt = NodeType(node_type.lower())
            except ValueError:
                return False, "", f"Invalid node type: {node_type}"
            
            # Generate ID
            node_id = self._generate_node_id(node_type.lower())
            
            # Create node info
            node_info = NodeInfo(
                node_id=node_id,
                node_type=nt,
                host=host,
                port=port
            )
            
            # Register
            self._nodes[node_id] = node_info
            print(f"[NodeRegistry] Registered: {node_id}")
            
            return True, node_id, "Registration successful"
            
        except Exception as e:
            return False, "", f"Registration failed: {str(e)}"
    
    def unregister(self, node_id: str) -> bool:
        """Remove a node from registry."""
        if node_id in self._nodes:
            del self._nodes[node_id]
            print(f"[NodeRegistry] Unregistered: {node_id}")
            return True
        return False
    
    def heartbeat(self, node_id: str, status: int) -> bool:
        """
        Update node heartbeat.
        
        Args:
            node_id: Node identifier
            status: 0=IDLE, 1=BUSY, 2=ERROR
        """
        if node_id not in self._nodes:
            return False
        
        node = self._nodes[node_id]
        node.last_heartbeat = datetime.now()
        
        try:
            node.status = NodeStatus(status)
        except ValueError:
            node.status = NodeStatus.ERROR
            
        return True
    
    def get_node(self, node_id: str) -> Optional[NodeInfo]:
        """Get node info by ID."""
        return self._nodes.get(node_id)
    
    def get_nodes_by_type(self, node_type: NodeType) -> list[NodeInfo]:
        """Get all nodes of a specific type."""
        return [n for n in self._nodes.values() if n.node_type == node_type]
    
    def get_idle_node(self, node_type: NodeType) -> Optional[NodeInfo]:
        """Get first idle node of specified type."""
        for node in self._nodes.values():
            if node.node_type == node_type and node.status == NodeStatus.IDLE:
                return node
        return None
    
    def set_node_busy(self, node_id: str, task_id: str):
        """Mark node as busy with a task."""
        if node_id in self._nodes:
            self._nodes[node_id].status = NodeStatus.BUSY
            self._nodes[node_id].current_task_id = task_id
    
    def set_node_idle(self, node_id: str):
        """Mark node as idle."""
        if node_id in self._nodes:
            self._nodes[node_id].status = NodeStatus.IDLE
            self._nodes[node_id].current_task_id = None
    
    def get_all_nodes(self) -> list[NodeInfo]:
        """Get all registered nodes."""
        return list(self._nodes.values())
    
    def check_timeouts(self, timeout_seconds: int) -> list[str]:
        """
        Check for nodes that haven't sent heartbeat within timeout.
        Returns list of timed-out node IDs.
        """
        now = datetime.now()
        timed_out = []
        
        for node_id, node in self._nodes.items():
            elapsed = (now - node.last_heartbeat).total_seconds()
            if elapsed > timeout_seconds:
                node.status = NodeStatus.OFFLINE
                timed_out.append(node_id)
                print(f"[NodeRegistry] Node timed out: {node_id}")
        
        return timed_out
    
    def __len__(self) -> int:
        return len(self._nodes)
    
    def __repr__(self) -> str:
        return f"NodeRegistry({len(self._nodes)} nodes)"
