"""
RabbitMQ Consumer for DB node.
Lightweight consumer that polls for messages.
"""
import json
import pika
from typing import Optional
from dataclasses import dataclass


@dataclass
class QueueMessage:
    """Message from RabbitMQ queue."""
    task_id: str
    json_data: str
    
    @classmethod
    def from_json(cls, data: str) -> 'QueueMessage':
        parsed = json.loads(data)
        return cls(
            task_id=parsed['task_id'],
            json_data=parsed['json_data']
        )
    
    def to_json(self) -> str:
        return json.dumps({
            'task_id': self.task_id,
            'json_data': self.json_data
        })


class RabbitMQConsumer:
    """
    Simple RabbitMQ consumer for DB node.
    Uses non-blocking get_message for async compatibility.
    """
    
    def __init__(self, host: str, port: int = 5672, user: str = 'guest', password: str = 'guest'):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self._connection = None
        self._channel = None
        self._connected = False
    
    def connect(self) -> bool:
        """Connect to RabbitMQ."""
        if not self.host:
            print("[RabbitMQ] No host configured, skipping connection")
            return False
            
        try:
            credentials = pika.PlainCredentials(self.user, self.password)
            parameters = pika.ConnectionParameters(
                host=self.host,
                port=self.port,
                credentials=credentials,
                heartbeat=600,
                blocked_connection_timeout=300
            )
            
            self._connection = pika.BlockingConnection(parameters)
            self._channel = self._connection.channel()
            self._connected = True
            print(f"[RabbitMQ] Connected to {self.host}:{self.port}")
            return True
            
        except Exception as e:
            print(f"[RabbitMQ] Connection failed: {e}")
            self._connected = False
            return False
    
    def declare_queue(self, queue_name: str):
        """Declare a queue (create if not exists)."""
        if self._channel:
            self._channel.queue_declare(queue=queue_name, durable=True)
    
    def get_message(self, queue_name: str) -> Optional[QueueMessage]:
        """
        Get a single message from queue (non-blocking).
        Returns None if queue is empty or not connected.
        """
        if not self._connected or not self._channel:
            return None
            
        try:
            method, properties, body = self._channel.basic_get(
                queue=queue_name,
                auto_ack=False
            )
            
            if body:
                message = QueueMessage.from_json(body.decode('utf-8'))
                self._channel.basic_ack(delivery_tag=method.delivery_tag)
                return message
                
        except Exception as e:
            print(f"[RabbitMQ] Get message error: {e}")
            self._connected = False
            
        return None
    
    @property
    def is_connected(self) -> bool:
        return self._connected
    
    def close(self):
        """Close connection."""
        if self._connection and self._connection.is_open:
            self._connection.close()
            print("[RabbitMQ] Connection closed")
        self._connected = False
