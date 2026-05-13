#!/usr/bin/env bash
set -Eeuo pipefail

# Guarded host installer/runner for the VLM node.
# Docker kullanmaz. GPU/Python/repo/venv/proto/connectivity kontrollerini yapar,
# tek VLM node süreci başlatır ve startup başarısızsa açık süreç bırakmaz.

REPO_URL="${REPO_URL:-https://github.com/TopcuAbdulbaki/Bitirme.git}"
APP_DIR="${APP_DIR:-$HOME/Bitirme}"
VLM_VENV="${VLM_VENV:-$APP_DIR/vlm/.venv}"
RESET_VLM_VENV="${RESET_VLM_VENV:-false}"
PYTHON_BIN="${PYTHON_BIN:-}"

MODEL_MODE="${MODEL_MODE:-transformers}"
PRODUCTION_MODEL="${PRODUCTION_MODEL:-Qwen/Qwen3.5-9B}"
LM_STUDIO_HOST="${LM_STUDIO_HOST:-http://127.0.0.1:1234}"
LM_STUDIO_MODEL="${LM_STUDIO_MODEL:-qwen3-vl-2b-instruct}"

ORCHESTRATOR_HOST="${ORCHESTRATOR_HOST:-}"
ORCHESTRATOR_PORT="${ORCHESTRATOR_PORT:-50051}"
PUBLIC_HOST="${PUBLIC_HOST:-$(hostname -I 2>/dev/null | awk '{print $1}')}"
PUBLIC_PORT="${PUBLIC_PORT:-50054}"

RABBITMQ_HOST="${RABBITMQ_HOST:-127.0.0.1}"
RABBITMQ_PORT="${RABBITMQ_PORT:-5672}"
RABBITMQ_USER="${RABBITMQ_USER:-guest}"
RABBITMQ_PASSWORD="${RABBITMQ_PASSWORD:-guest}"

MINIO_HOST="${MINIO_HOST:-}"
MINIO_PORT="${MINIO_PORT:-9000}"
MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-admin}"
MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-admin123}"
MINIO_SECURE="${MINIO_SECURE:-false}"
REQUIRE_MINIO="${REQUIRE_MINIO:-false}"

MIN_CUDA_DRIVER_VERSION="${MIN_CUDA_DRIVER_VERSION:-12.1}"
MIN_COMPUTE_CAP="${MIN_COMPUTE_CAP:-7.5}"
ALLOW_EXISTING_VLM="${ALLOW_EXISTING_VLM:-false}"
STOP_EXISTING_VLM="${STOP_EXISTING_VLM:-false}"
FOLLOW_LOGS="${FOLLOW_LOGS:-true}"
STARTUP_TIMEOUT_SECONDS="${STARTUP_TIMEOUT_SECONDS:-120}"
VLM_LOG="${VLM_LOG:-$HOME/vlm-node.log}"
VLM_PID_FILE="${VLM_PID_FILE:-$HOME/vlm-node.pid}"

SCRIPT_SUCCESS=false
STARTED_VLM_PID=""

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
  if [ "$SCRIPT_SUCCESS" != "true" ] && [ -n "$STARTED_VLM_PID" ]; then
    if kill -0 "$STARTED_VLM_PID" >/dev/null 2>&1; then
      log "Startup failed; stopping VLM PID $STARTED_VLM_PID"
      kill "$STARTED_VLM_PID" >/dev/null 2>&1 || true
      wait "$STARTED_VLM_PID" >/dev/null 2>&1 || true
    fi
    rm -f "$VLM_PID_FILE"
  fi
  exit "$status"
}
trap cleanup_on_exit EXIT

version_ge() {
  python3 - "$1" "$2" <<'PY'
import sys
def parts(v): return tuple(int(p) for p in v.split(".") if p.isdigit())
a, b = parts(sys.argv[1]), parts(sys.argv[2])
n = max(len(a), len(b))
a += (0,) * (n - len(a)); b += (0,) * (n - len(b))
raise SystemExit(0 if a >= b else 1)
PY
}

preflight_gpu() {
  if [ "$MODEL_MODE" != "transformers" ]; then
    log "MODEL_MODE=$MODEL_MODE; skipping GPU preflight"
    return
  fi
  command -v nvidia-smi >/dev/null 2>&1 || die "nvidia-smi not found. Pick a GPU-enabled Vast template/instance."
  local cuda_version
  cuda_version="$(nvidia-smi | sed -n 's/.*CUDA Version: \([0-9.]*\).*/\1/p' | head -n1)"
  [ -n "$cuda_version" ] || die "Could not detect NVIDIA driver CUDA capability"
  version_ge "$cuda_version" "$MIN_CUDA_DRIVER_VERSION" || die "Driver CUDA $cuda_version, need >= $MIN_CUDA_DRIVER_VERSION"
  if caps="$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader 2>/dev/null)"; then
    while IFS= read -r cap; do
      cap="${cap// /}"
      [ -z "$cap" ] && continue
      version_ge "$cap" "$MIN_COMPUTE_CAP" || die "GPU compute capability $cap below $MIN_COMPUTE_CAP"
    done <<< "$caps"
  fi
  log "GPU preflight OK: driver CUDA=$cuda_version"
}

pick_python() {
  if [ -n "$PYTHON_BIN" ]; then command -v "$PYTHON_BIN" >/dev/null 2>&1 || die "PYTHON_BIN not found: $PYTHON_BIN"; echo "$PYTHON_BIN"; return; fi
  for candidate in python3.12 python3.11 python3.10 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
      if "$candidate" - <<'PY'
import sys
raise SystemExit(0 if (3, 10) <= sys.version_info[:2] <= (3, 12) else 1)
PY
      then command -v "$candidate"; return; fi
    fi
  done
  die "Python 3.10-3.12 is required for the VLM node"
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
  if [ -d "$APP_DIR/.git" ]; then log "Repo exists: $APP_DIR"; run git -C "$APP_DIR" pull --ff-only; return; fi
  if [ -e "$APP_DIR" ]; then local backup="${APP_DIR}.bak.$(date +%Y%m%d_%H%M%S)"; log "Existing non-git path found, moving to $backup"; run mv "$APP_DIR" "$backup"; fi
  run git clone "$REPO_URL" "$APP_DIR"
}

validate_vlm_env() {
  "$VLM_VENV/bin/python" - <<'PY'
import aiohttp, grpc, minio, pika, PIL.Image, torch, transformers
from transformers import AutoModelForImageTextToText, AutoProcessor
from vlm.generated import orchestrator_pb2, orchestrator_pb2_grpc
print(f"VLM Python env OK: torch={torch.__version__}, transformers={transformers.__version__}, cuda={torch.cuda.is_available()}")
PY
}

prepare_vlm_env() {
  local py="$1"
  cd "$APP_DIR"
  if [ -x "$VLM_VENV/bin/python" ] && [ "$RESET_VLM_VENV" != "true" ]; then
    if validate_vlm_env; then log "Reusing existing VLM venv: $VLM_VENV"; return; fi
    log "Existing VLM venv failed validation; reinstalling: $VLM_VENV"
    rm -rf "$VLM_VENV"
  fi
  if [ "$RESET_VLM_VENV" = "true" ] && [ -d "$VLM_VENV" ]; then log "Removing existing VLM venv: $VLM_VENV"; rm -rf "$VLM_VENV"; fi
  run "$py" -m venv "$VLM_VENV"
  # shellcheck disable=SC1091
  source "$VLM_VENV/bin/activate"
  run python -m pip install -U pip setuptools wheel
  run pip install -r vlm/requirements.txt
  validate_vlm_env
}

ensure_proto_imports() {
  cd "$APP_DIR"
  if "$VLM_VENV/bin/python" - <<'PY'
from vlm.generated import orchestrator_pb2, orchestrator_pb2_grpc
print("VLM generated proto imports OK")
PY
  then return; fi
  log "Regenerating VLM gRPC stubs"
  mkdir -p vlm/generated
  touch vlm/generated/__init__.py
  run "$VLM_VENV/bin/python" -m grpc_tools.protoc -Iproto --python_out=vlm/generated --grpc_python_out=vlm/generated proto/orchestrator.proto
  "$VLM_VENV/bin/python" - <<'PY'
from pathlib import Path
p = Path("vlm/generated/orchestrator_pb2_grpc.py")
text = p.read_text(encoding="utf-8").replace("import orchestrator_pb2 as orchestrator__pb2", "from . import orchestrator_pb2 as orchestrator__pb2")
p.write_text(text, encoding="utf-8")
from vlm.generated import orchestrator_pb2, orchestrator_pb2_grpc
print("VLM generated proto imports OK after regeneration")
PY
}

check_tcp_ready() {
  local label="$1" host="$2" port="$3"
  [ -n "$host" ] || die "$label host is empty"
  "$VLM_VENV/bin/python" - "$label" "$host" "$port" <<'PY'
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
  if [ "$REQUIRE_MINIO" = "true" ]; then
    [ -n "$MINIO_HOST" ] || die "MINIO_HOST is required when REQUIRE_MINIO=true"
    check_tcp_ready "MinIO" "$MINIO_HOST" "$MINIO_PORT"
  elif [ -n "$MINIO_HOST" ]; then
    check_tcp_ready "MinIO" "$MINIO_HOST" "$MINIO_PORT"
  fi
}

process_alive() { local pid="$1"; [ -n "$pid" ] && kill -0 "$pid" >/dev/null 2>&1; }
pid_cmdline() { local pid="$1"; tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null || true; }
find_vlm_processes() {
  python3 - <<'PY'
import os
for pid in filter(str.isdigit, os.listdir("/proc")):
    try: raw = open(f"/proc/{pid}/cmdline", "rb").read()
    except OSError: continue
    cmd = raw.replace(b"\0", b" ").decode(errors="ignore")
    if " -m vlm.main" in cmd or cmd.strip().endswith("-m vlm.main"):
        print(f"{pid}\t{cmd}")
PY
}

ensure_no_duplicate_vlm() {
  local existing=""
  if [ -f "$VLM_PID_FILE" ]; then local pid; pid="$(cat "$VLM_PID_FILE" 2>/dev/null || true)"; if process_alive "$pid"; then existing="${existing}${pid}\t$(pid_cmdline "$pid")"$'\n'; else rm -f "$VLM_PID_FILE"; fi; fi
  local discovered; discovered="$(find_vlm_processes || true)"
  if [ -n "$discovered" ]; then existing="${existing}${discovered}"$'\n'; fi
  if [ -z "$existing" ]; then return; fi
  if [ "$ALLOW_EXISTING_VLM" = "true" ]; then log "Existing VLM process allowed:"; printf '%s\n' "$existing"; SCRIPT_SUCCESS=true; exit 0; fi
  if [ "$STOP_EXISTING_VLM" = "true" ]; then
    log "Stopping existing VLM process(es)"
    awk '{print $1}' <<< "$existing" | sort -u | while read -r pid; do [ -n "$pid" ] && kill "$pid" >/dev/null 2>&1 || true; done
    sleep 2; rm -f "$VLM_PID_FILE"; return
  fi
  printf '\n[FAIL] Existing VLM node process detected:\n%s\n' "$existing" >&2
  die "Set ALLOW_EXISTING_VLM=true to reuse, or STOP_EXISTING_VLM=true to replace it."
}

start_vlm() {
  cd "$APP_DIR"
  rm -f "$VLM_LOG"
  export PYTHONPATH="$APP_DIR:${PYTHONPATH:-}"
  export MODEL_MODE PRODUCTION_MODEL LM_STUDIO_HOST LM_STUDIO_MODEL
  export ORCHESTRATOR_HOST ORCHESTRATOR_PORT PUBLIC_HOST PUBLIC_PORT
  export RABBITMQ_HOST RABBITMQ_PORT RABBITMQ_USER RABBITMQ_PASSWORD
  export MINIO_HOST MINIO_PORT MINIO_ACCESS_KEY MINIO_SECRET_KEY MINIO_SECURE
  log "Starting VLM node model=$PRODUCTION_MODEL mode=$MODEL_MODE"
  nohup "$VLM_VENV/bin/python" -m vlm.main > "$VLM_LOG" 2>&1 &
  STARTED_VLM_PID="$!"
  echo "$STARTED_VLM_PID" > "$VLM_PID_FILE"
  log "VLM PID: $STARTED_VLM_PID"
}

wait_for_vlm_startup() {
  local attempt
  log "Waiting for VLM startup validation"
  for attempt in $(seq 1 "$STARTUP_TIMEOUT_SECONDS"); do
    if ! process_alive "$STARTED_VLM_PID"; then tail -n 200 "$VLM_LOG" || true; die "VLM node exited during startup"; fi
    if grep -q "Consuming from queue: vlm_tasks" "$VLM_LOG" 2>/dev/null && grep -q "RabbitMQ: ✓" "$VLM_LOG" 2>/dev/null; then
      log "VLM node connected and polling"
      return
    fi
    if grep -Eiq "Traceback|ModuleNotFoundError|ImportError|Connection refused|Connection failed|Failed to load model" "$VLM_LOG" 2>/dev/null; then
      tail -n 200 "$VLM_LOG" || true
      die "VLM startup error detected"
    fi
    sleep 1
  done
  tail -n 200 "$VLM_LOG" || true
  die "VLM did not pass startup validation within ${STARTUP_TIMEOUT_SECONDS}s"
}

main() {
  log "VLM guarded host setup starting"
  install_system_packages
  preflight_gpu
  py="$(pick_python)"
  log "Using Python: $py ($("$py" -V))"
  prepare_repo
  prepare_vlm_env "$py"
  ensure_proto_imports
  check_connectivity
  ensure_no_duplicate_vlm
  start_vlm
  wait_for_vlm_startup
  SCRIPT_SUCCESS=true
  log "VLM node is running. PID file: $VLM_PID_FILE"
  log "Log file: $VLM_LOG"
  if [ "$FOLLOW_LOGS" = "true" ]; then tail -f "$VLM_LOG"; fi
}

main "$@"
