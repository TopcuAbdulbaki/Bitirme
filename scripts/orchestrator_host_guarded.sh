#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-$HOME/Bitirme}"
REPO_URL="${REPO_URL:-https://github.com/TopcuAbdulbaki/Bitirme.git}"
ORCH_VENV="${ORCH_VENV:-$APP_DIR/.venv-orch}"
PYTHON_BIN="${PYTHON_BIN:-}"
GRPC_HOST="${GRPC_HOST:-0.0.0.0}"
GRPC_PORT="${GRPC_PORT:-50051}"
ORCHESTRATOR_HTTP_HOST="${ORCHESTRATOR_HTTP_HOST:-127.0.0.1}"
ORCHESTRATOR_HTTP_PORT="${ORCHESTRATOR_HTTP_PORT:-8088}"
RABBITMQ_HOST="${RABBITMQ_HOST:-127.0.0.1}"
RABBITMQ_PORT="${RABBITMQ_PORT:-5672}"
RABBITMQ_USER="${RABBITMQ_USER:-guest}"
RABBITMQ_PASSWORD="${RABBITMQ_PASSWORD:-guest}"
START_LOCAL_RABBITMQ="${START_LOCAL_RABBITMQ:-true}"
STOP_EXISTING_ORCHESTRATOR="${STOP_EXISTING_ORCHESTRATOR:-false}"
FOLLOW_LOGS="${FOLLOW_LOGS:-true}"
STARTUP_TIMEOUT_SECONDS="${STARTUP_TIMEOUT_SECONDS:-75}"
ORCH_LOG="${ORCH_LOG:-$HOME/orchestrator.log}"
ORCH_PID_FILE="${ORCH_PID_FILE:-$HOME/orchestrator.pid}"

log() { printf '\n[%s] %s\n' "$(date '+%H:%M:%S')" "$*"; }
die() { printf '\n[FAIL] %s\n' "$*" >&2; exit 1; }
run() { log "$*"; "$@"; }

pick_python() {
  if [ -n "$PYTHON_BIN" ]; then command -v "$PYTHON_BIN" && return; fi
  for candidate in python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
      "$candidate" - <<'PY' >/dev/null 2>&1 && { command -v "$candidate"; return; }
import sys
raise SystemExit(0 if sys.version_info >= (3, 10) else 1)
PY
    fi
  done
  die "Python 3.10+ is required"
}

prepare_repo() {
  if [ -d "$APP_DIR/.git" ]; then
    run git -C "$APP_DIR" pull --ff-only
    return
  fi
  run git clone "$REPO_URL" "$APP_DIR"
}

ensure_rabbitmq() {
  if [ "$START_LOCAL_RABBITMQ" = "true" ]; then
    command -v docker >/dev/null 2>&1 || die "Docker is required when START_LOCAL_RABBITMQ=true"
    cd "$APP_DIR"
    run docker compose up -d rabbitmq
  fi
  "$ORCH_VENV/bin/python" - "$RABBITMQ_HOST" "$RABBITMQ_PORT" <<'PY'
import socket, sys, time
host, port = sys.argv[1], int(sys.argv[2])
deadline = time.time() + 60
while time.time() < deadline:
    try:
        with socket.create_connection((host, port), timeout=2):
            print(f"RabbitMQ reachable: {host}:{port}")
            raise SystemExit(0)
    except OSError:
        time.sleep(1)
raise SystemExit(f"RabbitMQ unreachable: {host}:{port}")
PY
}

prepare_env() {
  local py="$1"
  cd "$APP_DIR"
  [ -x "$ORCH_VENV/bin/python" ] || run "$py" -m venv "$ORCH_VENV"
  run "$ORCH_VENV/bin/python" -m pip install -U pip setuptools wheel
  run "$ORCH_VENV/bin/python" -m pip install -r orchestrator/requirements.txt
  run "$ORCH_VENV/bin/python" -c "import orchestrator.main, orchestrator.services.admin_http; print('orchestrator import ok')"
}

kill_existing() {
  local pids
  pids="$(pgrep -af 'python .* -m orchestrator.main' | awk '{print $1}' || true)"
  [ -z "$pids" ] && return
  if [ "$STOP_EXISTING_ORCHESTRATOR" != "true" ]; then
    die "Existing orchestrator detected. Set STOP_EXISTING_ORCHESTRATOR=true to replace it."
  fi
  log "Stopping existing orchestrator"
  kill $pids >/dev/null 2>&1 || true
  sleep 2
}

start_orchestrator() {
  cd "$APP_DIR"
  rm -f "$ORCH_LOG"
  export GRPC_HOST GRPC_PORT ORCHESTRATOR_HTTP_HOST ORCHESTRATOR_HTTP_PORT
  export RABBITMQ_HOST RABBITMQ_PORT RABBITMQ_USER RABBITMQ_PASSWORD
  nohup "$ORCH_VENV/bin/python" -m orchestrator.main > "$ORCH_LOG" 2>&1 &
  echo "$!" > "$ORCH_PID_FILE"
}

wait_ready() {
  local pid attempt
  pid="$(cat "$ORCH_PID_FILE")"
  for attempt in $(seq 1 "$STARTUP_TIMEOUT_SECONDS"); do
    kill -0 "$pid" >/dev/null 2>&1 || { tail -n 160 "$ORCH_LOG" || true; die "Orchestrator exited during startup"; }
    if "$ORCH_VENV/bin/python" - "$GRPC_PORT" "$ORCHESTRATOR_HTTP_PORT" <<'PY' >/dev/null 2>&1
import socket, sys
for port in map(int, sys.argv[1:]):
    with socket.create_connection(("127.0.0.1", port), timeout=1):
        pass
PY
    then
      log "Orchestrator ready"
      return
    fi
    sleep 1
  done
  tail -n 160 "$ORCH_LOG" || true
  die "Orchestrator readiness timed out"
}

main() {
  log "Guarded orchestrator setup starting"
  py="$(pick_python)"
  prepare_repo
  prepare_env "$py"
  ensure_rabbitmq
  kill_existing
  start_orchestrator
  wait_ready
  log "gRPC: ${GRPC_HOST}:${GRPC_PORT}"
  log "Panel: http://${ORCHESTRATOR_HTTP_HOST}:${ORCHESTRATOR_HTTP_PORT}"
  log "Log: $ORCH_LOG"
  [ "$FOLLOW_LOGS" = "true" ] && tail -f "$ORCH_LOG"
}

main "$@"
