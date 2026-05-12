#!/usr/bin/env bash
set -Eeuo pipefail

# Guarded host installer/runner for the DB node.
# Docker kullanmaz. Repo/venv/proto/import/connectivity kontrollerini yapar,
# tek DB node süreci başlatır ve startup başarısızsa kendi açtığı süreci kapatır.

REPO_URL="${REPO_URL:-https://github.com/TopcuAbdulbaki/Bitirme.git}"
APP_DIR="${APP_DIR:-$HOME/Bitirme}"
DB_VENV="${DB_VENV:-$APP_DIR/db/.venv}"
RESET_DB_VENV="${RESET_DB_VENV:-false}"
PYTHON_BIN="${PYTHON_BIN:-}"

ORCHESTRATOR_HOST="${ORCHESTRATOR_HOST:-}"
ORCHESTRATOR_PORT="${ORCHESTRATOR_PORT:-50051}"
PUBLIC_HOST="${PUBLIC_HOST:-$(hostname -I 2>/dev/null | awk '{print $1}')}"
PUBLIC_PORT="${PUBLIC_PORT:-50053}"

RABBITMQ_HOST="${RABBITMQ_HOST:-127.0.0.1}"
RABBITMQ_PORT="${RABBITMQ_PORT:-5672}"
RABBITMQ_USER="${RABBITMQ_USER:-guest}"
RABBITMQ_PASSWORD="${RABBITMQ_PASSWORD:-guest}"

POSTGRES_HOST="${POSTGRES_HOST:-127.0.0.1}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_DB="${POSTGRES_DB:-news_db}"
POSTGRES_USER="${POSTGRES_USER:-news_user}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-news_password}"

MINIO_HOST="${MINIO_HOST:-127.0.0.1}"
MINIO_PORT="${MINIO_PORT:-9000}"
MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-admin}"
MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-admin123}"
MINIO_BUCKET="${MINIO_BUCKET:-news-media}"
MINIO_SECURE="${MINIO_SECURE:-false}"

ALLOW_EXISTING_DB="${ALLOW_EXISTING_DB:-false}"
STOP_EXISTING_DB="${STOP_EXISTING_DB:-false}"
FOLLOW_LOGS="${FOLLOW_LOGS:-true}"
STARTUP_TIMEOUT_SECONDS="${STARTUP_TIMEOUT_SECONDS:-90}"
DB_LOG="${DB_LOG:-$HOME/db-node.log}"
DB_PID_FILE="${DB_PID_FILE:-$HOME/db-node.pid}"

SCRIPT_SUCCESS=false
STARTED_DB_PID=""

log() { printf '\n[%s] %s\n' "$(date '+%H:%M:%S')" "$*"; }
die() { printf '\n[FAIL] %s\n' "$*" >&2; exit 1; }
run() { log "$*"; "$@"; }

as_root() {
  if [ "$(id -u)" -eq 0 ]; then "$@"; return; fi
  if command -v sudo >/dev/null 2>&1; then sudo "$@"; return; fi
  die "Root or sudo is required for this step"
}

cleanup_on_exit() {
  local status=$?
  if [ "$SCRIPT_SUCCESS" != "true" ] && [ -n "$STARTED_DB_PID" ]; then
    if kill -0 "$STARTED_DB_PID" >/dev/null 2>&1; then
      log "Startup failed; stopping DB PID $STARTED_DB_PID"
      kill "$STARTED_DB_PID" >/dev/null 2>&1 || true
      wait "$STARTED_DB_PID" >/dev/null 2>&1 || true
    fi
    rm -f "$DB_PID_FILE"
  fi
  exit "$status"
}
trap cleanup_on_exit EXIT

pick_python() {
  if [ -n "$PYTHON_BIN" ]; then
    command -v "$PYTHON_BIN" >/dev/null 2>&1 || die "PYTHON_BIN not found: $PYTHON_BIN"
    echo "$PYTHON_BIN"
    return
  fi

  for candidate in python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
      if "$candidate" - <<'PY'
import sys
raise SystemExit(0 if sys.version_info >= (3, 10) else 1)
PY
      then
        command -v "$candidate"
        return
      fi
    fi
  done
  die "Python 3.10+ is required"
}

install_system_packages() {
  if command -v apt-get >/dev/null 2>&1; then
    export DEBIAN_FRONTEND=noninteractive
    log "Installing base system packages"
    as_root apt-get update
    as_root apt-get install -y git curl ca-certificates build-essential python3-venv python3-pip
  fi
}

prepare_repo() {
  if [ -d "$APP_DIR/.git" ]; then
    log "Repo exists: $APP_DIR"
    run git -C "$APP_DIR" pull --ff-only
    return
  fi
  if [ -e "$APP_DIR" ]; then
    local backup="${APP_DIR}.bak.$(date +%Y%m%d_%H%M%S)"
    log "Existing non-git path found, moving to $backup"
    run mv "$APP_DIR" "$backup"
  fi
  run git clone "$REPO_URL" "$APP_DIR"
}

validate_db_env() {
  "$DB_VENV/bin/python" - <<'PY'
import aiohttp
import asyncpg
import dotenv
import grpc
import minio
import pika
from db.generated import orchestrator_pb2, orchestrator_pb2_grpc
from db.services.postgres_manager import PostgresManager
from db.services.minio_manager import MinIOManager
print("DB Python env OK")
PY
}

prepare_db_env() {
  local py="$1"
  cd "$APP_DIR"
  if [ -x "$DB_VENV/bin/python" ] && [ "$RESET_DB_VENV" != "true" ]; then
    if validate_db_env; then
      log "Reusing existing DB venv: $DB_VENV"
      return
    fi
    log "Existing DB venv failed validation; reinstalling: $DB_VENV"
    rm -rf "$DB_VENV"
  fi
  if [ "$RESET_DB_VENV" = "true" ] && [ -d "$DB_VENV" ]; then
    log "Removing existing DB venv: $DB_VENV"
    rm -rf "$DB_VENV"
  fi
  run "$py" -m venv "$DB_VENV"
  # shellcheck disable=SC1091
  source "$DB_VENV/bin/activate"
  run python -m pip install -U pip setuptools wheel
  run pip install -r db/requirements.txt
  validate_db_env
}

ensure_proto_imports() {
  cd "$APP_DIR"
  if "$DB_VENV/bin/python" - <<'PY'
from db.generated import orchestrator_pb2, orchestrator_pb2_grpc
print("DB generated proto imports OK")
PY
  then
    return
  fi

  log "Regenerating DB gRPC stubs"
  mkdir -p db/generated
  touch db/generated/__init__.py
  run "$DB_VENV/bin/python" -m grpc_tools.protoc \
    -Iproto \
    --python_out=db/generated \
    --grpc_python_out=db/generated \
    proto/orchestrator.proto

  "$DB_VENV/bin/python" - <<'PY'
from pathlib import Path
p = Path("db/generated/orchestrator_pb2_grpc.py")
text = p.read_text(encoding="utf-8")
text = text.replace("import orchestrator_pb2 as orchestrator__pb2", "from . import orchestrator_pb2 as orchestrator__pb2")
p.write_text(text, encoding="utf-8")
from db.generated import orchestrator_pb2, orchestrator_pb2_grpc
print("DB generated proto imports OK after regeneration")
PY
}

check_tcp_ready() {
  local label="$1" host="$2" port="$3"
  [ -n "$host" ] || die "$label host is empty"
  "$DB_VENV/bin/python" - "$label" "$host" "$port" <<'PY'
import socket, sys, time
label, host, port = sys.argv[1], sys.argv[2], int(sys.argv[3])
deadline = time.time() + 20
last = None
while time.time() < deadline:
    try:
        with socket.create_connection((host, port), timeout=3):
            print(f"{label} reachable: {host}:{port}")
            raise SystemExit(0)
    except OSError as exc:
        last = exc
        time.sleep(1)
raise SystemExit(f"{label} unreachable: {host}:{port} ({last})")
PY
}

check_connectivity() {
  [ -n "$ORCHESTRATOR_HOST" ] || die "ORCHESTRATOR_HOST is required"
  check_tcp_ready "Orchestrator gRPC" "$ORCHESTRATOR_HOST" "$ORCHESTRATOR_PORT"
  check_tcp_ready "RabbitMQ" "$RABBITMQ_HOST" "$RABBITMQ_PORT"
  check_tcp_ready "PostgreSQL" "$POSTGRES_HOST" "$POSTGRES_PORT"
  check_tcp_ready "MinIO" "$MINIO_HOST" "$MINIO_PORT"
}

process_alive() { local pid="$1"; [ -n "$pid" ] && kill -0 "$pid" >/dev/null 2>&1; }
pid_cmdline() { local pid="$1"; tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null || true; }

find_db_processes() {
  python3 - <<'PY'
import os
for pid in filter(str.isdigit, os.listdir("/proc")):
    try:
        raw = open(f"/proc/{pid}/cmdline", "rb").read()
    except OSError:
        continue
    cmd = raw.replace(b"\0", b" ").decode(errors="ignore")
    if " -m db.main" in cmd or cmd.strip().endswith("-m db.main"):
        print(f"{pid}\t{cmd}")
PY
}

ensure_no_duplicate_db() {
  local existing=""
  if [ -f "$DB_PID_FILE" ]; then
    local pid
    pid="$(cat "$DB_PID_FILE" 2>/dev/null || true)"
    if process_alive "$pid"; then existing="${existing}${pid}\t$(pid_cmdline "$pid")"$'\n'; else rm -f "$DB_PID_FILE"; fi
  fi
  local discovered
  discovered="$(find_db_processes || true)"
  if [ -n "$discovered" ]; then existing="${existing}${discovered}"$'\n'; fi
  if [ -z "$existing" ]; then return; fi
  if [ "$ALLOW_EXISTING_DB" = "true" ]; then
    log "Existing DB process allowed:"
    printf '%s\n' "$existing"
    SCRIPT_SUCCESS=true
    exit 0
  fi
  if [ "$STOP_EXISTING_DB" = "true" ]; then
    log "Stopping existing DB process(es)"
    awk '{print $1}' <<< "$existing" | sort -u | while read -r pid; do [ -n "$pid" ] && kill "$pid" >/dev/null 2>&1 || true; done
    sleep 2
    rm -f "$DB_PID_FILE"
    return
  fi
  printf '\n[FAIL] Existing DB node process detected:\n%s\n' "$existing" >&2
  die "Set ALLOW_EXISTING_DB=true to reuse, or STOP_EXISTING_DB=true to replace it."
}

start_db() {
  cd "$APP_DIR"
  rm -f "$DB_LOG"
  export PYTHONPATH="$APP_DIR:${PYTHONPATH:-}"
  export ORCHESTRATOR_HOST ORCHESTRATOR_PORT PUBLIC_HOST PUBLIC_PORT
  export RABBITMQ_HOST RABBITMQ_PORT RABBITMQ_USER RABBITMQ_PASSWORD
  export POSTGRES_HOST POSTGRES_PORT POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD
  export MINIO_HOST MINIO_PORT MINIO_ACCESS_KEY MINIO_SECRET_KEY MINIO_BUCKET MINIO_SECURE

  log "Starting DB node"
  nohup "$DB_VENV/bin/python" -m db.main > "$DB_LOG" 2>&1 &
  STARTED_DB_PID="$!"
  echo "$STARTED_DB_PID" > "$DB_PID_FILE"
  log "DB PID: $STARTED_DB_PID"
}

wait_for_db_startup() {
  local attempt
  log "Waiting for DB startup validation"
  for attempt in $(seq 1 "$STARTUP_TIMEOUT_SECONDS"); do
    if ! process_alive "$STARTED_DB_PID"; then
      tail -n 200 "$DB_LOG" || true
      die "DB node exited during startup"
    fi
    if grep -q "Polling queue: db_tasks" "$DB_LOG" 2>/dev/null \
      && grep -q "PostgreSQL: ✓" "$DB_LOG" 2>/dev/null \
      && grep -q "RabbitMQ: ✓" "$DB_LOG" 2>/dev/null; then
      log "DB node connected and polling"
      return
    fi
    if grep -Eiq "Traceback|ModuleNotFoundError|ImportError|Connection refused|Connection failed" "$DB_LOG" 2>/dev/null; then
      tail -n 200 "$DB_LOG" || true
      die "DB startup error detected"
    fi
    sleep 1
  done
  tail -n 200 "$DB_LOG" || true
  die "DB did not pass startup validation within ${STARTUP_TIMEOUT_SECONDS}s"
}

main() {
  log "DB guarded host setup starting"
  install_system_packages
  py="$(pick_python)"
  log "Using Python: $py ($("$py" -V))"
  prepare_repo
  prepare_db_env "$py"
  ensure_proto_imports
  check_connectivity
  ensure_no_duplicate_db
  start_db
  wait_for_db_startup
  SCRIPT_SUCCESS=true
  log "DB node is running. PID file: $DB_PID_FILE"
  log "Log file: $DB_LOG"
  if [ "$FOLLOW_LOGS" = "true" ]; then tail -f "$DB_LOG"; fi
}

main "$@"
