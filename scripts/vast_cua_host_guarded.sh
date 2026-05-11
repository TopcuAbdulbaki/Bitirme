#!/usr/bin/env bash
set -Eeuo pipefail

# Guarded host installer for CUA + vLLM.
# It does not "hope" the host works: it checks driver/CUDA/Python/GPU first,
# installs into isolated venvs, starts vLLM, verifies /v1/models, then starts CUA.

REPO_URL="${REPO_URL:-https://github.com/TopcuAbdulbaki/Bitirme.git}"
APP_DIR="${APP_DIR:-$HOME/Bitirme}"
MODEL_ID="${MODEL_ID:-Qwen/Qwen3.5-9B}"
VLLM_PORT="${VLLM_PORT:-1234}"
VLLM_API_KEY="${VLLM_API_KEY:-lm-studio}"
VLLM_VENV="${VLLM_VENV:-$HOME/.venvs/vllm-cu121}"
CUA_VENV="${CUA_VENV:-$APP_DIR/cua/.venv}"
VLLM_VERSION="${VLLM_VERSION:-0.6.6.post1}"
PYTHON_BIN="${PYTHON_BIN:-}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-32768}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.92}"
TENSOR_PARALLEL_SIZE="${TENSOR_PARALLEL_SIZE:-1}"
VLLM_USE_V1="${VLLM_USE_V1:-0}"
VLLM_DTYPE="${VLLM_DTYPE:-half}"
MODEL_DOWNLOAD_DIR="${MODEL_DOWNLOAD_DIR:-$HOME/.cache/huggingface}"
CUA_RUN_MODE="${CUA_RUN_MODE:-standalone}"
CUA_QUERY="${CUA_QUERY:-Turkey economy 2026}"
MAX_ARTICLES="${MAX_ARTICLES:-3}"
MAX_CYCLES="${MAX_CYCLES:-6}"
SEARCH_ENGINE="${SEARCH_ENGINE:-duckduckgo}"
BROWSER_HEADLESS="${BROWSER_HEADLESS:-true}"
MIN_CUDA_DRIVER_VERSION="${MIN_CUDA_DRIVER_VERSION:-12.1}"
MIN_COMPUTE_CAP="${MIN_COMPUTE_CAP:-7.0}"

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

  die "This script must run in a root shell. Run: su - root"
}

require_root_shell() {
  if [ "$(id -u)" -ne 0 ]; then
    die "Root shell required. Run 'su - root', then download and run this script again."
  fi
}

version_ge() {
  python3 - "$1" "$2" <<'PY'
import sys
def parts(v):
    return tuple(int(p) for p in v.split(".") if p.isdigit())
left = parts(sys.argv[1])
right = parts(sys.argv[2])
size = max(len(left), len(right))
left += (0,) * (size - len(left))
right += (0,) * (size - len(right))
sys.exit(0 if left >= right else 1)
PY
}

pick_python() {
  if [ -n "$PYTHON_BIN" ]; then
    command -v "$PYTHON_BIN" >/dev/null 2>&1 || die "PYTHON_BIN not found: $PYTHON_BIN"
    echo "$PYTHON_BIN"
    return
  fi

  for candidate in python3.12 python3.11 python3.10 python3.9 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
      local version
      version="$("$candidate" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
      case "$version" in
        3.9|3.10|3.11|3.12)
          command -v "$candidate"
          return
          ;;
      esac
    fi
  done

  die "Python 3.9-3.12 is required"
}

install_system_packages() {
  if command -v apt-get >/dev/null 2>&1; then
    export DEBIAN_FRONTEND=noninteractive
    log "apt-get update"
    as_root apt-get update
    log "apt-get install base packages"
    as_root apt-get install -y git curl ca-certificates build-essential python3-venv python3-pip
  fi
}

preflight_gpu() {
  command -v nvidia-smi >/dev/null 2>&1 || die "nvidia-smi not found. Pick a GPU-enabled Vast template/instance."

  local cuda_version
  cuda_version="$(nvidia-smi | sed -n 's/.*CUDA Version: \([0-9.]*\).*/\1/p' | head -n1)"
  [ -n "$cuda_version" ] || die "Could not detect NVIDIA driver CUDA capability from nvidia-smi"
  version_ge "$cuda_version" "$MIN_CUDA_DRIVER_VERSION" || die "Driver supports CUDA $cuda_version, need >= $MIN_CUDA_DRIVER_VERSION for the cu121 vLLM profile"

  local gpu_count
  gpu_count="$(nvidia-smi --query-gpu=name --format=csv,noheader | wc -l | tr -d ' ')"
  [ "$gpu_count" -ge "$TENSOR_PARALLEL_SIZE" ] || die "TENSOR_PARALLEL_SIZE=$TENSOR_PARALLEL_SIZE but only $gpu_count GPU(s) visible"

  local caps
  if caps="$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader 2>/dev/null)"; then
    while IFS= read -r cap; do
      cap="${cap// /}"
      [ -z "$cap" ] && continue
      version_ge "$cap" "$MIN_COMPUTE_CAP" || die "GPU compute capability $cap is below required $MIN_COMPUTE_CAP"
    done <<< "$caps"
  else
    log "compute_cap query is unavailable; continuing after nvidia-smi driver/CUDA checks"
  fi

  log "GPU preflight OK: driver CUDA=$cuda_version, GPUs=$gpu_count"
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

install_vllm_profile() {
  local py="$1"
  run "$py" -m venv "$VLLM_VENV"
  # shellcheck disable=SC1091
  source "$VLLM_VENV/bin/activate"
  run python -m pip install -U pip setuptools wheel packaging
  run pip install "vllm==${VLLM_VERSION}" "transformers>=4.46.0" accelerate safetensors sentencepiece

  python - <<'PY'
import torch
import vllm
print(f"torch={torch.__version__}")
print(f"torch_cuda={torch.version.cuda}")
print(f"vllm={vllm.__version__}")
assert torch.cuda.is_available(), "torch.cuda.is_available() is False"
print(f"gpu_count={torch.cuda.device_count()}")
for i in range(torch.cuda.device_count()):
    major, minor = torch.cuda.get_device_capability(i)
    print(f"gpu[{i}]={torch.cuda.get_device_name(i)} cc={major}.{minor}")
PY
}

prepare_cua_env() {
  local py="$1"
  cd "$APP_DIR"
  run "$py" -m venv "$CUA_VENV"
  # shellcheck disable=SC1091
  source "$CUA_VENV/bin/activate"
  run python -m pip install -U pip setuptools wheel
  run pip install -r cua/requirements.allinone.txt
  run python -m playwright install chromium
  log "Installing Playwright Chromium system dependencies"
  as_root python -m playwright install-deps chromium
}

start_vllm() {
  mkdir -p "$MODEL_DOWNLOAD_DIR"
  pkill -f "vllm serve" >/dev/null 2>&1 || true
  rm -f "$HOME/vllm.log"

  # shellcheck disable=SC1091
  source "$VLLM_VENV/bin/activate"
  export VLLM_USE_V1

  log "Starting vLLM model=$MODEL_ID port=$VLLM_PORT"
  nohup "$VLLM_VENV/bin/vllm" serve "$MODEL_ID" \
    --trust-remote-code \
    --host 0.0.0.0 \
    --port "$VLLM_PORT" \
    --api-key "$VLLM_API_KEY" \
    --dtype "$VLLM_DTYPE" \
    --max-model-len "$MAX_MODEL_LEN" \
    --gpu-memory-utilization "$GPU_MEMORY_UTILIZATION" \
    --tensor-parallel-size "$TENSOR_PARALLEL_SIZE" \
    --download-dir "$MODEL_DOWNLOAD_DIR" \
    ${VLLM_EXTRA_ARGS:-} \
    > "$HOME/vllm.log" 2>&1 &
  echo "$!" > "$HOME/vllm.pid"
  log "vLLM PID: $(cat "$HOME/vllm.pid")"
}

wait_for_vllm() {
  local models_url="http://127.0.0.1:${VLLM_PORT}/v1/models"
  local auth_header="Authorization: Bearer ${VLLM_API_KEY}"
  local attempt

  log "Smoke testing vLLM at $models_url"
  for attempt in $(seq 1 240); do
    if curl -fsS -H "$auth_header" "$models_url" >/dev/null 2>&1; then
      log "vLLM smoke test OK"
      curl -s -H "$auth_header" "$models_url"
      printf '\n'
      return
    fi

    if ! pgrep -F "$HOME/vllm.pid" >/dev/null 2>&1; then
      log "vLLM exited early. Last log lines:"
      tail -n 200 "$HOME/vllm.log" || true
      die "vLLM failed. CUA will not start."
    fi

    sleep 5
  done

  tail -n 200 "$HOME/vllm.log" || true
  die "vLLM did not become ready. CUA will not start."
}

run_cua() {
  cd "$APP_DIR"
  # shellcheck disable=SC1091
  source "$CUA_VENV/bin/activate"

  export MODEL_MODE=local
  export MODEL_NAME="$MODEL_ID"
  export LMSTUDIO_URL="http://127.0.0.1:${VLLM_PORT}/v1"
  export LMSTUDIO_API_KEY="$VLLM_API_KEY"
  export SEARCH_ENGINE
  export BROWSER_HEADLESS
  export CUA_LLM_MAX_COMPLETION_TOKENS="${CUA_LLM_MAX_COMPLETION_TOKENS:-8192}"
  export CUA_SYNTHESIS_MAX_TOKENS="${CUA_SYNTHESIS_MAX_TOKENS:-8192}"
  export CUA_PIPELINE_MAX_NEW_TOKENS="${CUA_PIPELINE_MAX_NEW_TOKENS:-4096}"

  case "$CUA_RUN_MODE" in
    standalone)
      run python -m cua.test_local \
        --mode surface \
        --query "$CUA_QUERY" \
        --max-articles "$MAX_ARTICLES" \
        --max-cycles "$MAX_CYCLES" \
        --engine "$SEARCH_ENGINE" \
        --lmstudio-url "$LMSTUDIO_URL"
      ;;
    node)
      [ -n "${ORCHESTRATOR_HOST:-}" ] || die "ORCHESTRATOR_HOST is required for node mode"
      [ -n "${RABBITMQ_HOST:-}" ] || die "RABBITMQ_HOST is required for node mode"
      run python -m cua.main
      ;;
    *)
      die "Unknown CUA_RUN_MODE=$CUA_RUN_MODE. Use standalone or node."
      ;;
  esac
}

main() {
  log "CUA guarded host setup starting"
  require_root_shell
  install_system_packages
  preflight_gpu
  py="$(pick_python)"
  log "Using Python: $py ($("$py" -V))"
  prepare_repo
  install_vllm_profile "$py"
  prepare_cua_env "$py"
  start_vllm
  wait_for_vllm
  run_cua
}

main "$@"
