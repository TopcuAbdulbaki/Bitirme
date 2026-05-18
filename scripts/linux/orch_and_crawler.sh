#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VISIBLE=false
DRY_RUN=false
ACTION="start"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --visible) VISIBLE=true; shift ;;
    --dry-run) DRY_RUN=true; shift ;;
    --action) ACTION="$2"; shift 2 ;;
    --help|-h)
      echo "Usage: $0 [--action start|restart|stop|status] [--visible] [--dry-run]"
      exit 0
      ;;
    *) echo "[FAIL] Unknown argument: $1" >&2; exit 2 ;;
  esac
done

run_cmd() {
  if [ "$DRY_RUN" = true ]; then
    printf '[dry-run] %s\n' "$*"
    return
  fi
  "$@"
}

case "$ACTION" in
  start|restart)
    if [ "$VISIBLE" = true ] && command -v x-terminal-emulator >/dev/null 2>&1; then
      run_cmd x-terminal-emulator -e bash -lc "FOLLOW_LOGS=true bash '$SCRIPT_DIR/orchestrator.sh' --local"
      sleep 3
      run_cmd x-terminal-emulator -e bash -lc "FOLLOW_LOGS=true bash '$SCRIPT_DIR/crawler.sh' --local"
    else
      run_cmd env FOLLOW_LOGS=false STOP_EXISTING_ORCHESTRATOR=true bash "$SCRIPT_DIR/orchestrator.sh" --local
      run_cmd env FOLLOW_LOGS=false STOP_EXISTING_CRAWLER=true bash "$SCRIPT_DIR/crawler.sh" --local
    fi
    ;;
  stop)
    echo "Stop is process-name based on Linux; use the PID files under \$HOME or stop the spawned processes explicitly."
    ;;
  status)
    echo "orchestrator pid: $(cat "$HOME/orchestrator.pid" 2>/dev/null || echo missing)"
    echo "crawler pid: $(cat "$HOME/crawler.pid" 2>/dev/null || echo missing)"
    ;;
  *)
    echo "[FAIL] Unsupported action: $ACTION" >&2
    exit 2
    ;;
esac
