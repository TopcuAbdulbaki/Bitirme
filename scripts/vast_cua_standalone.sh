#!/usr/bin/env bash
set -Eeuo pipefail

REPO_URL="${REPO_URL:-https://github.com/TopcuAbdulbaki/Bitirme.git}"
APP_DIR="${APP_DIR:-$HOME/Bitirme}"
MODEL_ID="${MODEL_ID:-Qwen/Qwen3.5-9B}"
VLLM_PORT="${VLLM_PORT:-1234}"
VLLM_API_KEY="${VLLM_API_KEY:-lm-studio}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-8192}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.85}"
TENSOR_PARALLEL_SIZE="${TENSOR_PARALLEL_SIZE:-1}"
VLLM_USE_V1="${VLLM_USE_V1:-0}"
CUA_QUERY="${CUA_QUERY:-Turkey economy 2026}"
MAX_ARTICLES="${MAX_ARTICLES:-3}"
MAX_CYCLES="${MAX_CYCLES:-6}"
SEARCH_ENGINE="${SEARCH_ENGINE:-duckduckgo}"

log() {
  printf '\n[%s] %s\n' "$(date '+%H:%M:%S')" "$*"
}

run() {
  log "$*"
  "$@"
}

python_bin() {
  if command -v python3 >/dev/null 2>&1; then
    command -v python3
    return
  fi
  if command -v python >/dev/null 2>&1; then
    command -v python
    return
  fi
  return 1
}

install_system_packages() {
  if command -v apt-get >/dev/null 2>&1; then
    export DEBIAN_FRONTEND=noninteractive
    run apt-get update
    run apt-get install -y git curl ca-certificates python3 python3-venv python3-pip build-essential
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

install_vllm() {
  local py
  py="$(python_bin)"
  run "$py" -m pip install -U pip
  run "$py" -m pip install -U vllm transformers accelerate safetensors sentencepiece
}

start_vllm() {
  log "Stopping old vLLM processes if any"
  pkill -f "vllm serve" >/dev/null 2>&1 || true
  rm -f "$HOME/vllm.log"

  log "Starting vLLM model=$MODEL_ID port=$VLLM_PORT"
  export VLLM_USE_V1
  nohup vllm serve "$MODEL_ID" \
    --trust-remote-code \
    --host 0.0.0.0 \
    --port "$VLLM_PORT" \
    --api-key "$VLLM_API_KEY" \
    --dtype half \
    --max-model-len "$MAX_MODEL_LEN" \
    --gpu-memory-utilization "$GPU_MEMORY_UTILIZATION" \
    --tensor-parallel-size "$TENSOR_PARALLEL_SIZE" \
    > "$HOME/vllm.log" 2>&1 &

  log "vLLM PID: $!"
}

wait_for_vllm() {
  local models_url="http://127.0.0.1:${VLLM_PORT}/v1/models"
  local attempt
  local auth_header="Authorization: Bearer ${VLLM_API_KEY}"

  log "Waiting for vLLM at $models_url"
  for attempt in $(seq 1 180); do
    if curl -fsS -H "$auth_header" "$models_url" >/dev/null 2>&1; then
      log "vLLM is ready"
      curl -s -H "$auth_header" "$models_url"
      printf '\n'
      return
    fi

    if ! pgrep -f "vllm serve" >/dev/null 2>&1; then
      log "vLLM exited early. Last log lines:"
      tail -n 160 "$HOME/vllm.log" || true
      exit 1
    fi

    sleep 5
  done

  log "vLLM did not become ready in time. Last log lines:"
  tail -n 200 "$HOME/vllm.log" || true
  exit 1
}

prepare_cua_env() {
  local py
  py="$(python_bin)"
  cd "$APP_DIR"

  run "$py" -m venv cua/.venv
  # shellcheck disable=SC1091
  source cua/.venv/bin/activate
  run python -m pip install -U pip
  run pip install -r cua/requirements.txt
  run python -m playwright install chromium --with-deps
}

run_cua_standalone() {
  cd "$APP_DIR"
  # shellcheck disable=SC1091
  source cua/.venv/bin/activate

  export LMSTUDIO_URL="http://127.0.0.1:${VLLM_PORT}/v1"
  export SEARCH_ENGINE="$SEARCH_ENGINE"
  export BROWSER_HEADLESS="true"

  run python -m cua.test_local \
    --mode surface \
    --query "$CUA_QUERY" \
    --max-articles "$MAX_ARTICLES" \
    --max-cycles "$MAX_CYCLES" \
    --engine "$SEARCH_ENGINE" \
    --lmstudio-url "$LMSTUDIO_URL"
}

main() {
  log "CUA Vast.ai standalone setup starting"
  install_system_packages
  prepare_repo
  install_vllm
  start_vllm
  wait_for_vllm
  prepare_cua_env
  run_cua_standalone
  log "Done"
}

main "$@"
