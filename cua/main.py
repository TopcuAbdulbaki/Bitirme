"""
CUA Node Main Entry Point.
RabbitMQ'dan görev alır, LangGraph agent'ı çalıştırır, sonucu geri yayınlar.
"""
import asyncio
from contextlib import suppress
import json
import signal
import sys

from cua.config import (
    ORCHESTRATOR_HOST, ORCHESTRATOR_PORT,
    CUA_GRPC_PORT, QUEUE_AGENT_TASKS, MODEL_MODE,
    BROWSER_HEADLESS, CUA_HEALTH_FILE
)
from cua.services.grpc_client import GRPCClient
from cua.services.health_state import HealthState
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
        self.health      = HealthState(CUA_HEALTH_FILE)
        self.grpc_client = GRPCClient(ORCHESTRATOR_HOST, ORCHESTRATOR_PORT)
        self.rabbitmq    = None
        self.browser     = BrowserTool(headless=BROWSER_HEADLESS)
        self.model       = CUAModelHandler(mode=MODEL_MODE)
        self.node_id     = None
        self._running    = False
        self._current_task_id = ""
        self._heartbeat_task = None
        self._consumer_task = None

    async def start(self):
        """Tüm servisleri başlat."""
        print("=" * 50)
        print("CUA NODE STARTING")
        print("=" * 50)
        self.health.update(running=False, ready=False, status="starting", last_error="")

        # 1. Orchestrator'a kayıt
        try:
            await self.grpc_client.connect()
            self.node_id = await self.grpc_client.register("cua", CUA_GRPC_PORT)
            self.health.update(
                node_id=self.node_id,
                orchestrator_registered=True,
            )
        except Exception as e:
            print(f"[CUA] Orchestrator bağlantısı başarısız: {e}")
            print("[CUA] Orchestrator olmadan devam ediliyor (standalone mod)")
            self.node_id = "cua_standalone"
            self.health.update(
                node_id=self.node_id,
                orchestrator_registered=False,
                last_error=f"orchestrator registration failed: {e}",
            )

        # 2. Browser'ı başlat
        try:
            await self.browser.initialize()
            self.health.update(browser_ready=True)
        except Exception as e:
            print(f"[CUA] Browser başlatma hatası: {e}")
            self.grpc_client.set_status(2)
            self.health.update(status="error", browser_ready=False, last_error=f"browser init failed: {e}")
            raise

        model_ready = self._model_ready()
        self.health.update(model_ready=model_ready)
        if not model_ready:
            self.grpc_client.set_status(2)
            self.health.update(status="error", last_error="model is not ready")
            raise RuntimeError("CUA model is not ready")

        try:
            self.rabbitmq = RabbitMQConsumer()
            self.health.update(rabbitmq_connected=self.rabbitmq.is_connected())
        except Exception as e:
            self.grpc_client.set_status(2)
            self.health.update(status="error", rabbitmq_connected=False, last_error=f"rabbitmq init failed: {e}")
            raise

        # 3. Döngüleri başlat
        self._running = True
        self._write_runtime_health()
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self._consumer_task = asyncio.create_task(self._task_consumer_loop())

        print(f"[CUA] Node hazır. node_id={self.node_id}")
        print("=" * 50)

    async def _task_consumer_loop(self):
        """agent_tasks kuyruğunu sürekli dinle."""
        print("[CUA] Görev tüketicisi başladı, agent_tasks bekleniyor...")
        while self._running:
            try:
                if not self._ready_for_tasks():
                    self._write_runtime_health()
                    await asyncio.sleep(2)
                    continue
                msg = self.rabbitmq.get_message(QUEUE_AGENT_TASKS)
                if msg:
                    print(f"[CUA] Görev alındı: {msg.task_id}")
                    await self._handle_task(msg)
            except Exception as e:
                print(f"[CUA] Kuyruk okuma hatası: {e}")
                self.grpc_client.set_status(2)
                self.health.update(status="error", last_error=f"queue read failed: {e}")
            await asyncio.sleep(1)

    async def _handle_task(self, msg):
        """Tek bir görevi işle (asenkron, paralel görevlere hazır)."""
        self.grpc_client.set_status(1)
        self._current_task_id = msg.task_id
        self._write_runtime_health()
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
                self.health.update(last_error=f"result publish failed: {msg.task_id}")

        except json.JSONDecodeError as e:
            print(f"[CUA] Geçersiz JSON mesajı: {e}")
            ok = self.rabbitmq.publish_result(
                msg.task_id,
                {"status": "FAILED", "error": f"JSON parse hatası: {e}"}
            )
            self.rabbitmq.ack(msg) if ok else self.rabbitmq.nack(msg, requeue=False)
        except Exception as e:
            print(f"[CUA] Görev işleme hatası ({msg.task_id}): {e}")
            self.grpc_client.set_status(2)
            self.health.update(status="error", last_error=f"task failed: {e}")
            ok = self.rabbitmq.publish_result(
                msg.task_id,
                {"status": "FAILED", "error": str(e)}
            )
            self.rabbitmq.ack(msg) if ok else self.rabbitmq.nack(msg, requeue=True)
        finally:
            self._current_task_id = ""
            self.grpc_client.set_status(0)
            self._write_runtime_health()

    async def _heartbeat_loop(self):
        while self._running:
            self._write_runtime_health()
            await self.grpc_client.heartbeat_once()
            await asyncio.sleep(10)

    def _model_ready(self) -> bool:
        return bool(
            getattr(self.model, "llm", None)
            or getattr(self.model, "_pipeline", None)
        )

    def _ready_for_tasks(self) -> bool:
        if self.rabbitmq and not self.rabbitmq.is_connected():
            try:
                self.rabbitmq.ensure_connected()
            except Exception as e:
                self.health.update(rabbitmq_connected=False, last_error=f"rabbitmq reconnect failed: {e}")
        return bool(
            self._running
            and self.rabbitmq
            and self.rabbitmq.is_connected()
            and getattr(self.browser, "_initialized", False)
            and self._model_ready()
        )

    def _write_runtime_health(self):
        rabbit_ready = bool(self.rabbitmq and self.rabbitmq.is_connected())
        browser_ready = bool(getattr(self.browser, "_initialized", False))
        model_ready = self._model_ready()
        ready = bool(self._running and rabbit_ready and browser_ready and model_ready)
        if not ready:
            status = "error" if self._running else "starting"
            self.grpc_client.set_status(2)
        elif self._current_task_id:
            status = "busy"
            self.grpc_client.set_status(1)
        else:
            status = "ready"
            self.grpc_client.set_status(0)
        self.health.update(
            running=self._running,
            ready=ready,
            status=status,
            node_id=self.node_id or "",
            rabbitmq_connected=rabbit_ready,
            browser_ready=browser_ready,
            model_ready=model_ready,
            current_task_id=self._current_task_id,
        )

    async def shutdown(self):
        """Tüm servisleri temiz kapat."""
        print("\n[CUA] Kapatılıyor...")
        self._running = False
        self.health.update(running=False, ready=False, status="stopping", current_task_id="")
        for task in (self._consumer_task, self._heartbeat_task):
            if task:
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task
        await self.browser.close()
        await self.grpc_client.close()
        if self.rabbitmq:
            self.rabbitmq.close()
        self.health.update(running=False, ready=False, status="stopped")
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
