#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="$SCRIPT_DIR/../nodes.local.json"
DRY_RUN=false
VISIBLE=false

while [ "$#" -gt 0 ]; do
  case "$1" in
    --config) CONFIG="$2"; shift 2 ;;
    --dry-run) DRY_RUN=true; shift ;;
    --visible) VISIBLE=true; shift ;;
    --help|-h)
      echo "Usage: $0 [--config scripts/nodes.example.json] [--dry-run] [--visible]"
      exit 0
      ;;
    *) echo "[FAIL] Unknown argument: $1" >&2; exit 2 ;;
  esac
done

if [ ! -f "$CONFIG" ]; then
  CONFIG="$SCRIPT_DIR/../nodes.example.json"
fi

rows="$(
  PYTHON_BIN="$(command -v python3 || command -v python || true)"
  [ -n "$PYTHON_BIN" ] || { echo "[FAIL] python3 or python is required for JSON config parsing" >&2; exit 2; }
  "$PYTHON_BIN" - "$CONFIG" <<'PY'
import json, sys
cfg = json.load(open(sys.argv[1], encoding="utf-8"))
d = cfg.get("defaults", {})
for n in cfg.get("nodes", []):
    role = n["role"]
    run = n.get("run", "remote" if n.get("host") else "local")
    host = n.get("host", "")
    ssh_user = n.get("sshUser", d.get("sshUser", "root"))
    ssh_port = n.get("sshPort", d.get("sshPort", 22))
    target_os = n.get("targetOs", d.get("targetOs", "auto"))
    values = [
        role, run, host, str(ssh_user), str(ssh_port), str(target_os),
        str(d.get("orchestratorHost", "127.0.0.1")), str(d.get("orchestratorPort", 50051)),
        str(d.get("rabbitmqHost", "127.0.0.1")), str(d.get("rabbitmqPort", 5672)),
        str(d.get("postgresHost", "127.0.0.1")), str(d.get("postgresPort", 5432)),
        str(d.get("minioHost", "127.0.0.1")), str(d.get("minioPort", 9000)),
    ]
    print("\t".join(values))
PY
)"

run_cmd() {
  if [ "$DRY_RUN" = true ]; then
    printf '[dry-run] %s\n' "$*"
    return
  fi
  "$@"
}

local_orch=false
local_crawler=false
while IFS=$'\t' read -r role run host ssh_user ssh_port target_os orch_host orch_port rabbit_host rabbit_port pg_host pg_port minio_host minio_port; do
  [ -n "$role" ] || continue
  [ "$role" = "orchestrator" ] && [ "$run" = "local" ] && local_orch=true
  [ "$role" = "crawler" ] && [ "$run" = "local" ] && local_crawler=true
done <<< "$rows"

if [ "$local_orch" = true ] && [ "$local_crawler" = true ]; then
  cmd=("$SCRIPT_DIR/orch_and_crawler.sh" --action start)
  [ "$VISIBLE" = true ] && cmd+=(--visible)
  [ "$DRY_RUN" = true ] && cmd+=(--dry-run)
  run_cmd "${cmd[@]}"
fi

while IFS=$'\t' read -r role run host ssh_user ssh_port target_os orch_host orch_port rabbit_host rabbit_port pg_host pg_port minio_host minio_port; do
  [ -n "$role" ] || continue
  if [ "$local_orch" = true ] && [ "$local_crawler" = true ] && { [ "$role" = "orchestrator" ] || [ "$role" = "crawler" ]; }; then
    continue
  fi

  script="$SCRIPT_DIR/$role.sh"
  args=("--orchestrator-host" "$orch_host" "--orchestrator-port" "$orch_port" "--rabbitmq-host" "$rabbit_host" "--rabbitmq-port" "$rabbit_port")
  if [ "$role" = "db" ] || [ "$role" = "vlm" ]; then
    args+=("--minio-host" "$minio_host" "--minio-port" "$minio_port")
  fi
  if [ "$role" = "db" ]; then
    args+=("--postgres-host" "$pg_host" "--postgres-port" "$pg_port")
  fi
  if [ "$run" = "local" ]; then
    args+=(--local)
  else
    args+=("--target-host" "$host" "--ssh-user" "$ssh_user" "--ssh-port" "$ssh_port" "--target-os" "$target_os")
  fi
  [ "$DRY_RUN" = true ] && args+=(--dry-run)
  run_cmd bash "$script" "${args[@]}"
done <<< "$rows"
