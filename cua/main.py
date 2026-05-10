"""
CUA Node Main Entry Point.
RabbitMQ'dan görev alır, LangGraph agent'ı çalıştırır, sonucu geri yayınlar.
"""
import asyncio
import json
import signal
import sys

from cua.config import (
    ORCHESTRATOR_HOST, ORCHESTRATOR_PORT,
    CUA_GRPC_PORT, QUEUE_AGENT_TASKS, MODEL_MODE,
    BROWSER_HEADLESS
)
from cua.services.grpc_client import GRPCClient
from cua.services.rabbitmq_consumer import RabbitMQConsumer
from cua.agent.browser_tool import BrowserTool
from cua.agent.model_handler import CUAModelHandler
from cua.agent.graph import run_agent


class CUANode:
    """
    CUA (Computer Using Agent) node lifecycle manager.

    Startup sırası:
      1. gRPC ile Orchestrator'a kayıt ol
      2. BrowserTool + CUAModelHandler'ı hazırla
      3. RabbitMQ agent_tasks kuyruğunu dinle
      4. Her görev için LangGraph döngüsü çalıştır
      5. Sonucu agent_results kuyruğuna yayınla
    """

    def __init__(self):
        self.grpc_client = GRPCClient(ORCHESTRATOR_HOST, ORCHESTRATOR_PORT)
        self.rabbitmq    = RabbitMQConsumer()
        self.browser     = BrowserTool(headless=BROWSER_HEADLESS)
        self.model       = CUAModelHandler(mode=MODEL_MODE)
        self.node_id     = None
        self._running    = False

    async def start(self):
        """Tüm servisleri başlat."""
        print("=" * 50)
        print("CUA NODE STARTING")
        print("=" * 50)

        # 1. Orchestrator'a kayıt
        try:
            await self.grpc_client.connect()
            self.node_id = await self.grpc_client.register("cua", CUA_GRPC_PORT)
        except Exception as e:
            print(f"[CUA] Orchestrator bağlantısı başarısız: {e}")
            print("[CUA] Orchestrator olmadan devam ediliyor (standalone mod)")
            self.node_id = "cua_standalone"

        # 2. Browser'ı başlat
        try:
            await self.browser.initialize()
        except Exception as e:
            print(f"[CUA] Browser başlatma hatası: {e}")
            print("[CUA] Browser olmadan çalışmaya devam ediliyor")

        # 3. Döngüleri başlat
        self._running = True
        asyncio.create_task(self.grpc_client.send_heartbeat())
        asyncio.create_task(self._task_consumer_loop())

        print(f"[CUA] Node hazır. node_id={self.node_id}")
        print("=" * 50)

    async def _task_consumer_loop(self):
        """agent_tasks kuyruğunu sürekli dinle."""
        print("[CUA] Görev tüketicisi başladı, agent_tasks bekleniyor...")
        while self._running:
            try:
                msg = self.rabbitmq.get_message(QUEUE_AGENT_TASKS)
                if msg:
                    print(f"[CUA] Görev alındı: {msg.task_id}")
                    await self._handle_task(msg)
            except Exception as e:
                print(f"[CUA] Kuyruk okuma hatası: {e}")
            await asyncio.sleep(1)

    async def _handle_task(self, msg):
        """Tek bir görevi işle (asenkron, paralel görevlere hazır)."""
        self.grpc_client.set_status(1)
        try:
            task_data = json.loads(msg.json_data)
            mode      = task_data.get("mode", "surface")
            topic     = task_data.get("topic", task_data.get("query", task_data.get("keywords", "?")))
            print(f"[CUA] İşleniyor: mode={mode}, topic/query='{topic}'")

            # LangGraph döngüsünü çalıştır
            result = await run_agent(task_data, self.browser, self.model)

            # task_id ve mode'u sonuca ekle
            result["task_id"] = msg.task_id
            result["mode"]    = mode

            # Sonucu agent_results kuyruğuna yayınla
            ok = self.rabbitmq.publish_result(msg.task_id, result)
            if ok:
                self.rabbitmq.ack(msg)
                print(f"[CUA] Görev tamamlandı ve yayınlandı: {msg.task_id}")
            else:
                self.rabbitmq.nack(msg, requeue=True)
                print(f"[CUA] Sonuç yayınlanamadı: {msg.task_id}")

        except json.JSONDecodeError as e:
            print(f"[CUA] Geçersiz JSON mesajı: {e}")
            ok = self.rabbitmq.publish_result(
                msg.task_id,
                {"status": "FAILED", "error": f"JSON parse hatası: {e}"}
            )
            self.rabbitmq.ack(msg) if ok else self.rabbitmq.nack(msg, requeue=False)
        except Exception as e:
            print(f"[CUA] Görev işleme hatası ({msg.task_id}): {e}")
            ok = self.rabbitmq.publish_result(
                msg.task_id,
                {"status": "FAILED", "error": str(e)}
            )
            self.rabbitmq.ack(msg) if ok else self.rabbitmq.nack(msg, requeue=True)
        finally:
            self.grpc_client.set_status(0)

    async def shutdown(self):
        """Tüm servisleri temiz kapat."""
        print("\n[CUA] Kapatılıyor...")
        self._running = False
        await self.browser.close()
        await self.grpc_client.close()
        self.rabbitmq.close()
        print("[CUA] Kapatma tamamlandı")


async def main():
    node = CUANode()

    loop = asyncio.get_event_loop()

    def _sig_handler(sig, frame):
        print(f"\n[CUA] Sinyal alındı: {sig}")
        loop.create_task(node.shutdown())

    signal.signal(signal.SIGINT,  _sig_handler)
    if hasattr(signal, "SIGTERM"):          # Windows'ta SIGTERM yoktur
        signal.signal(signal.SIGTERM, _sig_handler)

    await node.start()

    try:
        while node._running:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, asyncio.CancelledError):
        await node.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
