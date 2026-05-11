#!/usr/bin/env bash
set -Eeuo pipefail

CUA_RUN_MODE="${CUA_RUN_MODE:-standalone}"
MODEL_ID="${MODEL_ID:-Qwen/Qwen3.5-9B}"
MODEL_NAME="${MODEL_NAME:-$MODEL_ID}"
VLLM_HOST="${VLLM_HOST:-0.0.0.0}"
VLLM_PORT="${VLLM_PORT:-1234}"
VLLM_API_KEY="${VLLM_API_KEY:-lm-studio}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-32768}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.92}"
TENSOR_PARALLEL_SIZE="${TENSOR_PARALLEL_SIZE:-1}"
VLLM_DTYPE="${VLLM_DTYPE:-half}"
VLLM_USE_V1="${VLLM_USE_V1:-0}"
MODEL_DOWNLOAD_DIR="${MODEL_DOWNLOAD_DIR:-/models}"
CUA_QUERY="${CUA_QUERY:-Turkey economy 2026}"
MAX_ARTICLES="${MAX_ARTICLES:-3}"
MAX_CYCLES="${MAX_CYCLES:-6}"
SEARCH_ENGINE="${SEARCH_ENGINE:-duckduckgo}"
BROWSER_HEADLESS="${BROWSER_HEADLESS:-true}"
CUA_LLM_MAX_COMPLETION_TOKENS="${CUA_LLM_MAX_COMPLETION_TOKENS:-8192}"
CUA_SYNTHESIS_MAX_TOKENS="${CUA_SYNTHESIS_MAX_TOKENS:-8192}"
CUA_PIPELINE_MAX_NEW_TOKENS="${CUA_PIPELINE_MAX_NEW_TOKENS:-4096}"

export MODEL_NAME
export VLLM_USE_V1
export LMSTUDIO_URL="http://127.0.0.1:${VLLM_PORT}/v1"
export LMSTUDIO_API_KEY="$VLLM_API_KEY"
export BROWSER_HEADLESS
export SEARCH_ENGINE
export CUA_LLM_MAX_COMPLETION_TOKENS
export CUA_SYNTHESIS_MAX_TOKENS
export CUA_PIPELINE_MAX_NEW_TOKENS

vllm_pid=""
cua_pid=""

log() {
  printf '\n[%s] %s\n' "$(date '+%H:%M:%S')" "$*"
}

cleanup() {
  set +e
  if [ -n "${cua_pid:-}" ] && kill -0 "$cua_pid" >/dev/null 2>&1; then
    kill "$cua_pid" >/dev/null 2>&1
  fi
  if [ -n "${vllm_pid:-}" ] && kill -0 "$vllm_pid" >/dev/null 2>&1; then
    kill "$vllm_pid" >/dev/null 2>&1
  fi
}

trap cleanup INT TERM EXIT

start_vllm() {
  mkdir -p "$MODEL_DOWNLOAD_DIR"
  log "Starting vLLM model=$MODEL_ID port=$VLLM_PORT max_model_len=$MAX_MODEL_LEN tp=$TENSOR_PARALLEL_SIZE"

  vllm serve "$MODEL_ID" \
    --trust-remote-code \
    --host "$VLLM_HOST" \
    --port "$VLLM_PORT" \
    --api-key "$VLLM_API_KEY" \
    --dtype "$VLLM_DTYPE" \
    --max-model-len "$MAX_MODEL_LEN" \
    --gpu-memory-utilization "$GPU_MEMORY_UTILIZATION" \
    --tensor-parallel-size "$TENSOR_PARALLEL_SIZE" \
    --download-dir "$MODEL_DOWNLOAD_DIR" \
    ${VLLM_EXTRA_ARGS:-} &

  vllm_pid="$!"
  log "vLLM PID: $vllm_pid"
}

wait_for_vllm() {
  local models_url="http://127.0.0.1:${VLLM_PORT}/v1/models"
  local auth_header="Authorization: Bearer ${VLLM_API_KEY}"
  local attempt

  log "Waiting for vLLM at $models_url"
  for attempt in $(seq 1 240); do
    if curl -fsS -H "$auth_header" "$models_url" >/dev/null 2>&1; then
      log "vLLM is ready"
      curl -s -H "$auth_header" "$models_url"
      printf '\n'
      return
    fi

    if ! kill -0 "$vllm_pid" >/dev/null 2>&1; then
      log "vLLM exited before becoming ready"
      wait "$vllm_pid" || true
      exit 1
    fi

    sleep 5
  done

  log "vLLM did not become ready in time"
  exit 1
}

run_cua() {
  case "$CUA_RUN_MODE" in
    standalone)
      log "Running CUA standalone test"
      python -m cua.test_local \
        --mode surface \
        --query "$CUA_QUERY" \
        --max-articles "$MAX_ARTICLES" \
        --max-cycles "$MAX_CYCLES" \
        --engine "$SEARCH_ENGINE" \
        --lmstudio-url "$LMSTUDIO_URL" &
      ;;
    node)
      log "Running CUA node mode"
      python -m cua.main &
      ;;
    *)
      log "Unknown CUA_RUN_MODE=$CUA_RUN_MODE. Use standalone or node."
      exit 2
      ;;
  esac

  cua_pid="$!"
  wait "$cua_pid"
}

cd /app
start_vllm
wait_for_vllm
run_cua
