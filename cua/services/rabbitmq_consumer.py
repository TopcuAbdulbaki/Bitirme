"""RabbitMQ consumer for CUA task and result messages."""
import json
import time
import pika
from dataclasses import dataclass
from typing import Optional
from cua.config import (
    RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_USER, RABBITMQ_PASSWORD,
    QUEUE_AGENT_TASKS, QUEUE_AGENT_RESULTS
)

@dataclass
class QueueMessage:
    task_id: str
    json_data: str

class RabbitMQConsumer:
    def __init__(self):
        self.connection = None
        self.channel = None
        self.connect()

    def connect(self, max_retries: int = 3, base_delay: int = 3):
        """Establish RabbitMQ connection with linear backoff retry."""
        for attempt in range(1, max_retries + 1):
            try:
                credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
                self.connection = pika.BlockingConnection(
                    pika.ConnectionParameters(
                        host=RABBITMQ_HOST,
                        port=RABBITMQ_PORT,
                        credentials=credentials,
                        connection_attempts=1,
                        retry_delay=0,
                    )
                )
                self.channel = self.connection.channel()
                self.channel.queue_declare(queue=QUEUE_AGENT_TASKS, durable=True)
                self.channel.queue_declare(queue=QUEUE_AGENT_RESULTS, durable=True)
                print("[CUA] Connected to RabbitMQ")
                return
            except Exception as e:
                if attempt == max_retries:
                    print(f"[CUA] RabbitMQ bağlantısı {max_retries} denemede başarısız: {e}")
                    raise
                wait = base_delay * attempt  # 3, 6, 9 saniye
                print(f"[CUA] RabbitMQ bağlanamıyor ({attempt}/{max_retries}), {wait}s bekle: {e}")
                time.sleep(wait)

    def get_message(self, queue_name: str) -> Optional[QueueMessage]:
        """Get a message from queue (non-blocking)."""
        try:
            method, properties, body = self.channel.basic_get(queue=queue_name)
            if method:
                data = json.loads(body.decode('utf-8'))
                self.channel.basic_ack(delivery_tag=method.delivery_tag)
                return QueueMessage(task_id=data.get('task_id'), json_data=body.decode('utf-8'))
        except Exception as e:
            print(f"[CUA] Error getting message from {queue_name}: {e}")
        return None

    def publish_result(self, task_id: str, result_data: dict) -> bool:
        """Publish result to agent_results queue."""
        try:
            msg = {"task_id": task_id, **result_data}
            self.channel.basic_publish(
                exchange='',
                routing_key=QUEUE_AGENT_RESULTS,
                body=json.dumps(msg),
                properties=pika.BasicProperties(delivery_mode=2)
            )
            return True
        except Exception as e:
            print(f"[CUA] Error publishing result: {e}")
            return False

    def close(self):
        """Close RabbitMQ connection."""
        if self.connection:
            self.connection.close()
