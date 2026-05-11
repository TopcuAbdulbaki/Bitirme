"""Small file-backed health/readiness state for the CUA node."""
import json
import os
import time
from pathlib import Path
from typing import Any


class HealthState:
    def __init__(self, path: str):
        self.path = Path(path)
        self.state: dict[str, Any] = {
            "running": False,
            "ready": False,
            "status": "starting",
            "node_id": "",
            "orchestrator_registered": False,
            "rabbitmq_connected": False,
            "browser_ready": False,
            "model_ready": False,
            "current_task_id": "",
            "last_error": "",
            "updated_at": time.time(),
        }
        self.write()

    def update(self, **values):
        self.state.update(values)
        self.state["updated_at"] = time.time()
        self.write()

    def write(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp_path.write_text(json.dumps(self.state, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp_path, self.path)
