#!/usr/bin/env bash
set -Eeuo pipefail

# Guarded host installer/runner for the Crawler node.
# This intentionally avoids Docker: it validates the host, creates an isolated venv,
# checks Crawl4AI/Playwright/gRPC imports, verifies Orchestrator reachability,
# then starts exactly one crawler process. If startup validation fails, it stops
# the process it started and leaves no half-running crawler behind.

REPO_URL="${REPO_URL:-https://github.com/TopcuAbdulbaki/Bitirme.git}"
APP_DIR="${APP_DIR:-$HOME/Bitirme}"
CRAWLER_VENV="${CRAWLER_VENV:-$APP_DIR/crawler/.venv}"
RESET_CRAWLER_VENV="${RESET_CRAWLER_VENV:-false}"
PYTHON_BIN="${PYTHON_BIN:-}"

CRAWLER_MODE="${CRAWLER_MODE:-distributed}"
ORCHESTRATOR_HOST="${ORCHESTRATOR_HOST:-}"
ORCHESTRATOR_PORT="${ORCHESTRATOR_PORT:-50051}"
POLL_INTERVAL="${POLL_INTERVAL:-5}"
HEARTBEAT_INTERVAL="${HEARTBEAT_INTERVAL:-10}"
CRAWLER_DEMO_MODE="${CRAWLER_DEMO_MODE:-false}"
CRAWLER_DEMO_LIMIT="${CRAWLER_DEMO_LIMIT:-5}"

INSTALL_PLAYWRIGHT_DEPS="${INSTALL_PLAYWRIGHT_DEPS:-true}"
ALLOW_EXISTING_CRAWLER="${ALLOW_EXISTING_CRAWLER:-false}"
STOP_EXISTING_CRAWLER="${STOP_EXISTING_CRAWLER:-false}"
FOLLOW_LOGS="${FOLLOW_LOGS:-true}"
STARTUP_TIMEOUT_SECONDS="${STARTUP_TIMEOUT_SECONDS:-90}"

CRAWLER_LOG="${CRAWLER_LOG:-$HOME/crawler.log}"
CRAWLER_PID_FILE="${CRAWLER_PID_FILE:-$HOME/crawler.pid}"

SCRIPT_SUCCESS=false
STARTED_CRAWLER_PID=""

log() {
  printf '\n[%s] %s\n' "$(date '+%H:%M:%S')" "$*"
}

die() {
  printf '\n[FAIL] %s\n' "$*" >&2
  exit 1
}

run() {
  log "$*"
  "$@"
}

as_root() {
  if [ "$(id -u)" -eq 0 ]; then
    "$@"
    return
  fi

  if command -v sudo >/dev/null 2>&1; then
    sudo "$@"
    return
  fi

  die "Root or sudo is required for this step"
}

cleanup_on_exit() {
  local status=$?
  if [ "$SCRIPT_SUCCESS" != "true" ] && [ -n "$STARTED_CRAWLER_PID" ]; then
    if kill -0 "$STARTED_CRAWLER_PID" >/dev/null 2>&1; then
      log "Startup failed; stopping crawler PID $STARTED_CRAWLER_PID"
      kill "$STARTED_CRAWLER_PID" >/dev/null 2>&1 || true
      wait "$STARTED_CRAWLER_PID" >/dev/null 2>&1 || true
    fi
    rm -f "$CRAWLER_PID_FILE"
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

validate_crawler_env() {
  "$CRAWLER_VENV/bin/python" - <<'PY'
import aiohttp
import grpc
import PIL.Image
import dotenv
import crawl4ai
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
print("Crawler Python env OK")
PY
}

prepare_crawler_env() {
  local py="$1"
  cd "$APP_DIR"

  if [ -x "$CRAWLER_VENV/bin/python" ] && [ "$RESET_CRAWLER_VENV" != "true" ]; then
    if validate_crawler_env; then
      log "Reusing existing crawler venv: $CRAWLER_VENV"
      return
    fi
    log "Existing crawler venv failed validation; reinstalling: $CRAWLER_VENV"
    rm -rf "$CRAWLER_VENV"
  fi

  if [ "$RESET_CRAWLER_VENV" = "true" ] && [ -d "$CRAWLER_VENV" ]; then
    log "Removing existing crawler venv: $CRAWLER_VENV"
    rm -rf "$CRAWLER_VENV"
  fi

  run "$py" -m venv "$CRAWLER_VENV"
  # shellcheck disable=SC1091
  source "$CRAWLER_VENV/bin/activate"
  run python -m pip install -U pip setuptools wheel
  run pip install -r crawler/requirements.txt
  run python -m playwright install chromium

  if [ "$INSTALL_PLAYWRIGHT_DEPS" = "true" ]; then
    log "Installing Playwright Chromium system dependencies"
    as_root "$CRAWLER_VENV/bin/python" -m playwright install-deps chromium
  fi

  validate_crawler_env
}

ensure_proto_imports() {
  cd "$APP_DIR"
  if "$CRAWLER_VENV/bin/python" - <<'PY'
from crawler.generated import orchestrator_pb2
from crawler.generated import orchestrator_pb2_grpc
print("Crawler generated proto imports OK")
PY
  then
    return
  fi

  log "Regenerating crawler gRPC stubs"
  mkdir -p crawler/generated
  touch crawler/generated/__init__.py
  run "$CRAWLER_VENV/bin/python" -m grpc_tools.protoc \
    -Iproto \
    --python_out=crawler/generated \
    --grpc_python_out=crawler/generated \
    proto/orchestrator.proto

  "$CRAWLER_VENV/bin/python" - <<'PY'
from pathlib import Path
p = Path("crawler/generated/orchestrator_pb2_grpc.py")
text = p.read_text(encoding="utf-8")
lines = []
for line in text.splitlines():
    if line.startswith("import orchestrator_pb2"):
        line = f"from . {line}"
    lines.append(line)
p.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY

  "$CRAWLER_VENV/bin/python" - <<'PY'
from crawler.generated import orchestrator_pb2
from crawler.generated import orchestrator_pb2_grpc
print("Crawler generated proto imports OK after regeneration")
PY
}

check_orchestrator_ready() {
  if [ "$CRAWLER_MODE" != "distributed" ]; then
    log "CRAWLER_MODE=$CRAWLER_MODE; skipping Orchestrator readiness check"
    return
  fi

  [ -n "$ORCHESTRATOR_HOST" ] || die "ORCHESTRATOR_HOST is required for distributed mode"

  local target="${ORCHESTRATOR_HOST}:${ORCHESTRATOR_PORT}"
  log "Checking Orchestrator gRPC readiness at $target"
  "$CRAWLER_VENV/bin/python" - "$target" <<'PY'
import grpc
import sys

target = sys.argv[1]
channel = grpc.insecure_channel(target)
try:
    grpc.channel_ready_future(channel).result(timeout=10)
finally:
    channel.close()
print(f"Orchestrator gRPC channel ready: {target}")
PY
}

process_alive() {
  local pid="$1"
  [ -n "$pid" ] && kill -0 "$pid" >/dev/null 2>&1
}

pid_cmdline() {
  local pid="$1"
  tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null || true
}

find_crawler_processes() {
  python3 - <<'PY'
import os

for pid in filter(str.isdigit, os.listdir("/proc")):
    try:
        raw = open(f"/proc/{pid}/cmdline", "rb").read()
    except OSError:
        continue
    cmd = raw.replace(b"\0", b" ").decode(errors="ignore")
    if " -m crawler.main" in cmd or cmd.strip().endswith("-m crawler.main"):
        print(f"{pid}\t{cmd}")
PY
}

ensure_no_duplicate_crawler() {
  local existing=""

  if [ -f "$CRAWLER_PID_FILE" ]; then
    local pid
    pid="$(cat "$CRAWLER_PID_FILE" 2>/dev/null || true)"
    if process_alive "$pid"; then
      existing="${existing}${pid}\t$(pid_cmdline "$pid")"$'\n'
    else
      rm -f "$CRAWLER_PID_FILE"
    fi
  fi

  local discovered
  discovered="$(find_crawler_processes || true)"
  if [ -n "$discovered" ]; then
    existing="${existing}${discovered}"$'\n'
  fi

  if [ -z "$existing" ]; then
    return
  fi

  if [ "$ALLOW_EXISTING_CRAWLER" = "true" ]; then
    log "Existing crawler process allowed:"
    printf '%s\n' "$existing"
    SCRIPT_SUCCESS=true
    exit 0
  fi

  if [ "$STOP_EXISTING_CRAWLER" = "true" ]; then
    log "Stopping existing crawler process(es)"
    awk '{print $1}' <<< "$existing" | sort -u | while read -r pid; do
      [ -n "$pid" ] || continue
      kill "$pid" >/dev/null 2>&1 || true
    done
    sleep 2
    rm -f "$CRAWLER_PID_FILE"
    return
  fi

  printf '\n[FAIL] Existing crawler process detected:\n%s\n' "$existing" >&2
  die "Set ALLOW_EXISTING_CRAWLER=true to reuse, or STOP_EXISTING_CRAWLER=true to replace it."
}

start_crawler() {
  cd "$APP_DIR"
  rm -f "$CRAWLER_LOG"

  export PYTHONPATH="$APP_DIR:${PYTHONPATH:-}"
  export CRAWLER_MODE
  export ORCHESTRATOR_HOST
  export ORCHESTRATOR_PORT
  export POLL_INTERVAL
  export HEARTBEAT_INTERVAL
  export CRAWLER_DEMO_MODE
  export CRAWLER_DEMO_LIMIT

  log "Starting crawler mode=$CRAWLER_MODE"
  nohup "$CRAWLER_VENV/bin/python" -m crawler.main > "$CRAWLER_LOG" 2>&1 &
  STARTED_CRAWLER_PID="$!"
  echo "$STARTED_CRAWLER_PID" > "$CRAWLER_PID_FILE"
  log "Crawler PID: $STARTED_CRAWLER_PID"
}

wait_for_crawler_startup() {
  local attempt
  log "Waiting for crawler startup validation"
  for attempt in $(seq 1 "$STARTUP_TIMEOUT_SECONDS"); do
    if ! process_alive "$STARTED_CRAWLER_PID"; then
      tail -n 200 "$CRAWLER_LOG" || true
      die "Crawler exited during startup"
    fi

    if grep -q "Connected & Registered. Polling for tasks" "$CRAWLER_LOG" 2>/dev/null; then
      log "Crawler registered and polling"
      return
    fi

    if grep -q "Standalone Mode - Running immediately" "$CRAWLER_LOG" 2>/dev/null; then
      log "Crawler standalone mode started"
      return
    fi

    if grep -Eiq "Traceback|ConnectionError|ModuleNotFoundError|ImportError" "$CRAWLER_LOG" 2>/dev/null; then
      tail -n 200 "$CRAWLER_LOG" || true
      die "Crawler startup error detected"
    fi

    sleep 1
  done

  tail -n 200 "$CRAWLER_LOG" || true
  die "Crawler did not pass startup validation within ${STARTUP_TIMEOUT_SECONDS}s"
}

main() {
  log "Crawler guarded host setup starting"
  install_system_packages
  py="$(pick_python)"
  log "Using Python: $py ($("$py" -V))"
  prepare_repo
  prepare_crawler_env "$py"
  ensure_proto_imports
  check_orchestrator_ready
  ensure_no_duplicate_crawler
  start_crawler
  wait_for_crawler_startup

  SCRIPT_SUCCESS=true
  log "Crawler is running. PID file: $CRAWLER_PID_FILE"
  log "Log file: $CRAWLER_LOG"

  if [ "$FOLLOW_LOGS" = "true" ]; then
    tail -f "$CRAWLER_LOG"
  fi
}

main "$@"
