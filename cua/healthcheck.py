"""Container healthcheck for CUA.

The CUA node is a gRPC client, not a gRPC server, so probing localhost:50054
does not prove health. This command validates the readiness file maintained by
the node process.
"""
import json
import os
import sys
import time
from pathlib import Path


def main() -> int:
    path = Path(os.getenv("CUA_HEALTH_FILE", "/tmp/cua_health.json"))
    max_age = float(os.getenv("CUA_HEALTH_MAX_AGE", "45"))
    require_orchestrator = os.getenv("CUA_REQUIRE_ORCHESTRATOR", "false").lower() == "true"

    if not path.exists():
        print(f"health file missing: {path}")
        return 1

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"health file unreadable: {exc}")
        return 1

    age = time.time() - float(data.get("updated_at") or 0)
    if age > max_age:
        print(f"health stale: age={age:.1f}s max={max_age:.1f}s")
        return 1

    required = ["running", "ready", "rabbitmq_connected", "browser_ready", "model_ready"]
    if require_orchestrator:
        required.append("orchestrator_registered")

    missing = [key for key in required if not data.get(key)]
    if missing:
        print(f"not ready: missing={missing} status={data.get('status')} error={data.get('last_error')}")
        return 1

    if data.get("status") == "error":
        print(f"node error: {data.get('last_error')}")
        return 1

    print("healthy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
