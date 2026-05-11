#!/usr/bin/env bash
set -Eeuo pipefail

REPO_URL="${REPO_URL:-https://github.com/TopcuAbdulbaki/Bitirme.git}"
APP_DIR="${APP_DIR:-$HOME/Bitirme}"
IMAGE_NAME="${IMAGE_NAME:-bitirme-cua-allinone:latest}"
CONTAINER_NAME="${CONTAINER_NAME:-cua-allinone}"
CUA_RUN_MODE="${CUA_RUN_MODE:-standalone}"
MODEL_ID="${MODEL_ID:-Qwen/Qwen3.5-9B}"
VLLM_PORT="${VLLM_PORT:-1234}"
VLLM_API_KEY="${VLLM_API_KEY:-lm-studio}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-32768}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.92}"
TENSOR_PARALLEL_SIZE="${TENSOR_PARALLEL_SIZE:-1}"
CUA_QUERY="${CUA_QUERY:-Turkey economy 2026}"
MAX_ARTICLES="${MAX_ARTICLES:-3}"
MAX_CYCLES="${MAX_CYCLES:-15}"
SEARCH_ENGINE="${SEARCH_ENGINE:-duckduckgo}"
BROWSER_HEADLESS="${BROWSER_HEADLESS:-true}"
MODEL_CACHE_DIR="${MODEL_CACHE_DIR:-$HOME/.cache/huggingface}"

log() {
  printf '\n[%s] %s\n' "$(date '+%H:%M:%S')" "$*"
}

run() {
  log "$*"
  "$@"
}

install_system_packages() {
  if command -v apt-get >/dev/null 2>&1; then
    export DEBIAN_FRONTEND=noninteractive
    run apt-get update
    run apt-get install -y git curl ca-certificates
  fi

  if ! command -v docker >/dev/null 2>&1; then
    run sh -c "curl -fsSL https://get.docker.com | sh"
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

build_image() {
  cd "$APP_DIR"
  run docker build -f cua/Dockerfile.allinone -t "$IMAGE_NAME" .
}

run_container() {
  mkdir -p "$MODEL_CACHE_DIR"
  docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true

  local args=(
    run -d
    --name "$CONTAINER_NAME"
    --gpus all
    --network host
    --ipc host
    --shm-size 4g
    --restart unless-stopped
    -v "${MODEL_CACHE_DIR}:/models"
    -e CUA_RUN_MODE="$CUA_RUN_MODE"
    -e MODEL_ID="$MODEL_ID"
    -e MODEL_NAME="$MODEL_ID"
    -e VLLM_PORT="$VLLM_PORT"
    -e VLLM_API_KEY="$VLLM_API_KEY"
    -e LMSTUDIO_API_KEY="$VLLM_API_KEY"
    -e MAX_MODEL_LEN="$MAX_MODEL_LEN"
    -e GPU_MEMORY_UTILIZATION="$GPU_MEMORY_UTILIZATION"
    -e TENSOR_PARALLEL_SIZE="$TENSOR_PARALLEL_SIZE"
    -e CUA_QUERY="$CUA_QUERY"
    -e MAX_ARTICLES="$MAX_ARTICLES"
    -e MAX_CYCLES="$MAX_CYCLES"
    -e SEARCH_ENGINE="$SEARCH_ENGINE"
    -e BROWSER_HEADLESS="$BROWSER_HEADLESS"
  )

  if [ "$CUA_RUN_MODE" = "node" ]; then
    args+=(
      -e ORCHESTRATOR_HOST="${ORCHESTRATOR_HOST:?ORCHESTRATOR_HOST is required for node mode}"
      -e ORCHESTRATOR_PORT="${ORCHESTRATOR_PORT:-50051}"
      -e RABBITMQ_HOST="${RABBITMQ_HOST:?RABBITMQ_HOST is required for node mode}"
      -e RABBITMQ_PORT="${RABBITMQ_PORT:-5672}"
      -e RABBITMQ_USER="${RABBITMQ_USER:-guest}"
      -e RABBITMQ_PASSWORD="${RABBITMQ_PASSWORD:-guest}"
    )
  fi

  args+=("$IMAGE_NAME")

  log "Starting container $CONTAINER_NAME"
  docker "${args[@]}"
  log "Follow logs with: docker logs -f $CONTAINER_NAME"
  docker logs -f "$CONTAINER_NAME"
}

main() {
  log "CUA all-in-one Vast setup starting"
  install_system_packages
  prepare_repo
  build_image
  run_container
}

main "$@"
