"""gRPC client for CUA node — Orchestrator registration and heartbeat."""
import asyncio
import grpc

from cua.config import ORCHESTRATOR_HOST, ORCHESTRATOR_PORT


class GRPCClient:
    def __init__(self, host: str, port: int):
        self.host    = host
        self.port    = port
        self.channel = None
        self.stub    = None
        self.node_id = None
        self.status  = 0

    def set_status(self, status: int):
        """Set heartbeat status: 0=IDLE, 1=BUSY, 2=ERROR."""
        self.status = status

    async def connect(self):
        """Orchestrator'a insecure gRPC bağlantısı kur."""
        try:
            # insecure_channel: SSL yok, lokal/Docker network için doğru
            self.channel = grpc.aio.insecure_channel(f"{self.host}:{self.port}")

            from cua.generated import orchestrator_pb2_grpc
            self.stub = orchestrator_pb2_grpc.OrchestratorServiceStub(self.channel)
            print(f"[CUA-gRPC] Bağlandı: {self.host}:{self.port}")
        except Exception as e:
            print(f"[CUA-gRPC] Bağlantı hatası: {e}")
            raise

    async def register(self, node_type: str, port: int) -> str:
        """
        Orchestrator'a kayıt ol ve node_id al.

        Args:
            node_type: "cua"
            port:      CUA'nın gRPC port numarası

        Returns:
            node_id string
        """
        try:
            from cua.generated import orchestrator_pb2
            req = orchestrator_pb2.RegisterRequest(
                node_type=node_type,
                host=self.host,
                port=port,
            )
            resp = await self.stub.Register(req)
            if resp.success:
                self.node_id = resp.node_id
                print(f"[CUA-gRPC] Kayıt başarılı: {self.node_id}")
                return self.node_id
            else:
                print(f"[CUA-gRPC] Kayıt reddedildi: {resp.message}")
                raise RuntimeError(f"Registration failed: {resp.message}")
        except Exception as e:
            print(f"[CUA-gRPC] Kayıt hatası: {e}")
            raise

    async def send_heartbeat(self):
        """Orchestrator'a periyodik heartbeat gönder."""
        while True:
            try:
                if self.node_id and self.stub:
                    from cua.generated import orchestrator_pb2
                    req  = orchestrator_pb2.HeartbeatRequest(
                        node_id=self.node_id,
                        status=self.status,
                    )
                    resp = await self.stub.Heartbeat(req)
                    if not resp.acknowledged:
                        print("[CUA-gRPC] Heartbeat kabul edilmedi")
            except Exception as e:
                print(f"[CUA-gRPC] Heartbeat hatası: {e}")
            await asyncio.sleep(10)

    async def close(self):
        """gRPC kanalını kapat."""
        if self.channel:
            await self.channel.close()
            print("[CUA-gRPC] Kanal kapatıldı")
