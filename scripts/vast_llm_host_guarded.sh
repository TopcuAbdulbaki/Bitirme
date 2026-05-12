#!/usr/bin/env bash
set -Eeuo pipefail

# Guarded host installer/runner for the LLM node.
# Docker kullanmaz. GPU/Python/repo/venv/proto/connectivity kontrollerini yapar,
# tek LLM node süreci başlatır ve startup başarısızsa açık süreç bırakmaz.

REPO_URL="${REPO_URL:-https://github.com/TopcuAbdulbaki/Bitirme.git}"
APP_DIR="${APP_DIR:-$HOME/Bitirme}"
LLM_VENV="${LLM_VENV:-$APP_DIR/llm/.venv}"
RESET_LLM_VENV="${RESET_LLM_VENV:-false}"
PYTHON_BIN="${PYTHON_BIN:-}"

MODEL_MODE="${MODEL_MODE:-transformers}"
PRODUCTION_MODEL="${PRODUCTION_MODEL:-Qwen/Qwen3-8B}"
LM_STUDIO_HOST="${LM_STUDIO_HOST:-http://127.0.0.1:1234}"
LM_STUDIO_MODEL="${LM_STUDIO_MODEL:-qwen3-8b}"

ORCHESTRATOR_HOST="${ORCHESTRATOR_HOST:-}"
ORCHESTRATOR_PORT="${ORCHESTRATOR_PORT:-50051}"
PUBLIC_HOST="${PUBLIC_HOST:-$(hostname -I 2>/dev/null | awk '{print $1}')}"
PUBLIC_PORT="${PUBLIC_PORT:-50055}"

RABBITMQ_HOST="${RABBITMQ_HOST:-127.0.0.1}"
RABBITMQ_PORT="${RABBITMQ_PORT:-5672}"
RABBITMQ_USER="${RABBITMQ_USER:-guest}"
RABBITMQ_PASSWORD="${RABBITMQ_PASSWORD:-guest}"

MIN_CUDA_DRIVER_VERSION="${MIN_CUDA_DRIVER_VERSION:-12.1}"
MIN_COMPUTE_CAP="${MIN_COMPUTE_CAP:-7.0}"
ALLOW_EXISTING_LLM="${ALLOW_EXISTING_LLM:-false}"
STOP_EXISTING_LLM="${STOP_EXISTING_LLM:-false}"
FOLLOW_LOGS="${FOLLOW_LOGS:-true}"
STARTUP_TIMEOUT_SECONDS="${STARTUP_TIMEOUT_SECONDS:-120}"
LLM_LOG="${LLM_LOG:-$HOME/llm-node.log}"
LLM_PID_FILE="${LLM_PID_FILE:-$HOME/llm-node.pid}"

SCRIPT_SUCCESS=false
STARTED_LLM_PID=""

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
  if [ "$SCRIPT_SUCCESS" != "true" ] && [ -n "$STARTED_LLM_PID" ]; then
    if kill -0 "$STARTED_LLM_PID" >/dev/null 2>&1; then
      log "Startup failed; stopping LLM PID $STARTED_LLM_PID"
      kill "$STARTED_LLM_PID" >/dev/null 2>&1 || true
      wait "$STARTED_LLM_PID" >/dev/null 2>&1 || true
    fi
    rm -f "$LLM_PID_FILE"
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
  die "Python 3.10-3.12 is required for the LLM node"
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

validate_llm_env() {
  "$LLM_VENV/bin/python" - <<'PY'
import aiohttp, grpc, pika, torch, transformers
from transformers import AutoModelForCausalLM, AutoTokenizer
from llm.generated import orchestrator_pb2, orchestrator_pb2_grpc
print(f"LLM Python env OK: torch={torch.__version__}, transformers={transformers.__version__}, cuda={torch.cuda.is_available()}")
PY
}

prepare_llm_env() {
  local py="$1"
  cd "$APP_DIR"
  if [ -x "$LLM_VENV/bin/python" ] && [ "$RESET_LLM_VENV" != "true" ]; then
    if validate_llm_env; then log "Reusing existing LLM venv: $LLM_VENV"; return; fi
    log "Existing LLM venv failed validation; reinstalling: $LLM_VENV"
    rm -rf "$LLM_VENV"
  fi
  if [ "$RESET_LLM_VENV" = "true" ] && [ -d "$LLM_VENV" ]; then log "Removing existing LLM venv: $LLM_VENV"; rm -rf "$LLM_VENV"; fi
  run "$py" -m venv "$LLM_VENV"
  # shellcheck disable=SC1091
  source "$LLM_VENV/bin/activate"
  run python -m pip install -U pip setuptools wheel
  run pip install -r llm/requirements.txt
  validate_llm_env
}

ensure_proto_imports() {
  cd "$APP_DIR"
  if "$LLM_VENV/bin/python" - <<'PY'
from llm.generated import orchestrator_pb2, orchestrator_pb2_grpc
print("LLM generated proto imports OK")
PY
  then return; fi
  log "Regenerating LLM gRPC stubs"
  mkdir -p llm/generated
  touch llm/generated/__init__.py
  run "$LLM_VENV/bin/python" -m grpc_tools.protoc -Iproto --python_out=llm/generated --grpc_python_out=llm/generated proto/orchestrator.proto
  "$LLM_VENV/bin/python" - <<'PY'
from pathlib import Path
p = Path("llm/generated/orchestrator_pb2_grpc.py")
text = p.read_text(encoding="utf-8").replace("import orchestrator_pb2 as orchestrator__pb2", "from . import orchestrator_pb2 as orchestrator__pb2")
p.write_text(text, encoding="utf-8")
from llm.generated import orchestrator_pb2, orchestrator_pb2_grpc
print("LLM generated proto imports OK after regeneration")
PY
}

check_tcp_ready() {
  local label="$1" host="$2" port="$3"
  [ -n "$host" ] || die "$label host is empty"
  "$LLM_VENV/bin/python" - "$label" "$host" "$port" <<'PY'
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
}

process_alive() { local pid="$1"; [ -n "$pid" ] && kill -0 "$pid" >/dev/null 2>&1; }
pid_cmdline() { local pid="$1"; tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null || true; }
find_llm_processes() {
  python3 - <<'PY'
import os
for pid in filter(str.isdigit, os.listdir("/proc")):
    try: raw = open(f"/proc/{pid}/cmdline", "rb").read()
    except OSError: continue
    cmd = raw.replace(b"\0", b" ").decode(errors="ignore")
    if " -m llm.main" in cmd or cmd.strip().endswith("-m llm.main"):
        print(f"{pid}\t{cmd}")
PY
}

ensure_no_duplicate_llm() {
  local existing=""
  if [ -f "$LLM_PID_FILE" ]; then local pid; pid="$(cat "$LLM_PID_FILE" 2>/dev/null || true)"; if process_alive "$pid"; then existing="${existing}${pid}\t$(pid_cmdline "$pid")"$'\n'; else rm -f "$LLM_PID_FILE"; fi; fi
  local discovered; discovered="$(find_llm_processes || true)"
  if [ -n "$discovered" ]; then existing="${existing}${discovered}"$'\n'; fi
  if [ -z "$existing" ]; then return; fi
  if [ "$ALLOW_EXISTING_LLM" = "true" ]; then log "Existing LLM process allowed:"; printf '%s\n' "$existing"; SCRIPT_SUCCESS=true; exit 0; fi
  if [ "$STOP_EXISTING_LLM" = "true" ]; then
    log "Stopping existing LLM process(es)"
    awk '{print $1}' <<< "$existing" | sort -u | while read -r pid; do [ -n "$pid" ] && kill "$pid" >/dev/null 2>&1 || true; done
    sleep 2; rm -f "$LLM_PID_FILE"; return
  fi
  printf '\n[FAIL] Existing LLM node process detected:\n%s\n' "$existing" >&2
  die "Set ALLOW_EXISTING_LLM=true to reuse, or STOP_EXISTING_LLM=true to replace it."
}

start_llm() {
  cd "$APP_DIR"
  rm -f "$LLM_LOG"
  export PYTHONPATH="$APP_DIR:${PYTHONPATH:-}"
  export MODEL_MODE PRODUCTION_MODEL LM_STUDIO_HOST LM_STUDIO_MODEL
  export ORCHESTRATOR_HOST ORCHESTRATOR_PORT PUBLIC_HOST PUBLIC_PORT
  export RABBITMQ_HOST RABBITMQ_PORT RABBITMQ_USER RABBITMQ_PASSWORD
  log "Starting LLM node model=$PRODUCTION_MODEL mode=$MODEL_MODE"
  nohup "$LLM_VENV/bin/python" -m llm.main > "$LLM_LOG" 2>&1 &
  STARTED_LLM_PID="$!"
  echo "$STARTED_LLM_PID" > "$LLM_PID_FILE"
  log "LLM PID: $STARTED_LLM_PID"
}

wait_for_llm_startup() {
  local attempt
  log "Waiting for LLM startup validation"
  for attempt in $(seq 1 "$STARTUP_TIMEOUT_SECONDS"); do
    if ! process_alive "$STARTED_LLM_PID"; then tail -n 200 "$LLM_LOG" || true; die "LLM node exited during startup"; fi
    if grep -q "Consuming from queue: llm_tasks" "$LLM_LOG" 2>/dev/null && grep -q "RabbitMQ: ✓" "$LLM_LOG" 2>/dev/null; then
      log "LLM node connected and polling"
      return
    fi
    if grep -Eiq "Traceback|ModuleNotFoundError|ImportError|Connection refused|Connection failed|Failed to load model" "$LLM_LOG" 2>/dev/null; then
      tail -n 200 "$LLM_LOG" || true
      die "LLM startup error detected"
    fi
    sleep 1
  done
  tail -n 200 "$LLM_LOG" || true
  die "LLM did not pass startup validation within ${STARTUP_TIMEOUT_SECONDS}s"
}

main() {
  log "LLM guarded host setup starting"
  install_system_packages
  preflight_gpu
  py="$(pick_python)"
  log "Using Python: $py ($("$py" -V))"
  prepare_repo
  prepare_llm_env "$py"
  ensure_proto_imports
  check_connectivity
  ensure_no_duplicate_llm
  start_llm
  wait_for_llm_startup
  SCRIPT_SUCCESS=true
  log "LLM node is running. PID file: $LLM_PID_FILE"
  log "Log file: $LLM_LOG"
  if [ "$FOLLOW_LOGS" = "true" ]; then tail -f "$LLM_LOG"; fi
}

main "$@"
