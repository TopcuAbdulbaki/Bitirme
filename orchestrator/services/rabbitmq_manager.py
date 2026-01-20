"""
RabbitMQ Manager Service
Handles queue creation and message publishing/consuming.
"""
import json
import pika
from typing import Callable, Optional
from dataclasses import dataclass

from ..config import (
    RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_USER, RABBITMQ_PASSWORD,
    QUEUE_VLM_TASKS, QUEUE_VLM_RESULTS, QUEUE_LLM_TASKS, QUEUE_LLM_RESULTS,
    QUEUE_DB_TASKS
)


@dataclass
class QueueMessage:
    """Wrapper for queue messages."""
    task_id: str
    json_data: str
    
    def to_json(self) -> str:
        return json.dumps({
            'task_id': self.task_id,
            'json_data': self.json_data
        })
    
    @classmethod
    def from_json(cls, data: str) -> 'QueueMessage':
        parsed = json.loads(data)
        return cls(
            task_id=parsed['task_id'],
            json_data=parsed['json_data']
        )


class RabbitMQManager:
    """
    Manager for RabbitMQ connections and queues.
    """
    
    def __init__(self):
        self._connection: Optional[pika.BlockingConnection] = None
        self._channel = None
        self._queues = [
            QUEUE_VLM_TASKS,
            QUEUE_VLM_RESULTS,
            QUEUE_LLM_TASKS,
            QUEUE_LLM_RESULTS,
            QUEUE_DB_TASKS
        ]
    
    def connect(self) -> bool:
        """Establish connection to RabbitMQ."""
        try:
            credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
            parameters = pika.ConnectionParameters(
                host=RABBITMQ_HOST,
                port=RABBITMQ_PORT,
                credentials=credentials,
                heartbeat=600,
                blocked_connection_timeout=300
            )
            
            self._connection = pika.BlockingConnection(parameters)
            self._channel = self._connection.channel()
            print(f"[RabbitMQ] Connected to {RABBITMQ_HOST}:{RABBITMQ_PORT}")
            
            # Declare all queues
            self._declare_queues()
            
            return True
            
        except Exception as e:
            print(f"[RabbitMQ] Connection failed: {e}")
            return False
    
    def _declare_queues(self):
        """Declare all required queues."""
        for queue_name in self._queues:
            self._channel.queue_declare(
                queue=queue_name,
                durable=True  # Survive broker restart
            )
            print(f"[RabbitMQ] Queue declared: {queue_name}")
    
    def publish(self, queue_name: str, message: QueueMessage) -> bool:
        """
        Publish a message to a queue.
        
        Args:
            queue_name: Target queue
            message: QueueMessage to publish
        """
        try:
            self._channel.basic_publish(
                exchange='',
                routing_key=queue_name,
                body=message.to_json(),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Persistent
                    content_type='application/json'
                )
            )
            print(f"[RabbitMQ] Published to {queue_name}: task_id={message.task_id}")
            return True
            
        except Exception as e:
            print(f"[RabbitMQ] Publish failed: {e}")
            return False
    
    def publish_vlm_task(self, task_id: str, json_data: str) -> bool:
        """Publish a task to VLM queue."""
        msg = QueueMessage(task_id=task_id, json_data=json_data)
        return self.publish(QUEUE_VLM_TASKS, msg)
    
    def publish_llm_task(self, task_id: str, json_data: str) -> bool:
        """Publish a task to LLM queue."""
        msg = QueueMessage(task_id=task_id, json_data=json_data)
        return self.publish(QUEUE_LLM_TASKS, msg)
    
    def publish_db_task(self, task_id: str, json_data: str) -> bool:
        """Publish final results to DB queue for storage."""
        msg = QueueMessage(task_id=task_id, json_data=json_data)
        return self.publish(QUEUE_DB_TASKS, msg)
    
    def consume(self, queue_name: str, callback: Callable[[QueueMessage], None]):
        """
        Start consuming messages from a queue.
        
        Args:
            queue_name: Queue to consume from
            callback: Function to call for each message
        """
        def on_message(ch, method, properties, body):
            try:
                message = QueueMessage.from_json(body.decode('utf-8'))
                callback(message)
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                print(f"[RabbitMQ] Message processing failed: {e}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        
        self._channel.basic_qos(prefetch_count=1)
        self._channel.basic_consume(
            queue=queue_name,
            on_message_callback=on_message
        )
        print(f"[RabbitMQ] Consuming from {queue_name}")
        self._channel.start_consuming()
    
    def get_message(self, queue_name: str) -> Optional[QueueMessage]:
        """
        Get a single message from queue (non-blocking).
        
        Returns:
            QueueMessage or None if queue is empty
        """
        method, properties, body = self._channel.basic_get(
            queue=queue_name,
            auto_ack=False
        )
        
        if body:
            message = QueueMessage.from_json(body.decode('utf-8'))
            self._channel.basic_ack(delivery_tag=method.delivery_tag)
            return message
        
        return None
    
    def get_queue_size(self, queue_name: str) -> int:
        """Get number of messages in queue."""
        result = self._channel.queue_declare(
            queue=queue_name,
            passive=True  # Don't create, just check
        )
        return result.method.message_count
    
    def close(self):
        """Close connection."""
        if self._connection and self._connection.is_open:
            self._connection.close()
            print("[RabbitMQ] Connection closed")
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
