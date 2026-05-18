#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

usage() {
  cat <<USAGE
Usage: $0 [--local] [--target-host HOST] [--ssh-user USER] [--ssh-port PORT]
          [--target-os auto|linux|windows] [--dry-run] [--visible]

Common endpoint flags:
  --orchestrator-host HOST --orchestrator-port PORT
  --rabbitmq-host HOST     --rabbitmq-port PORT
  --postgres-host HOST     --postgres-port PORT
  --minio-host HOST        --minio-port PORT
USAGE
}

require_role() {
  : "${ROLE:?ROLE must be set before sourcing role_runner.sh}"
  : "${HELPER:?HELPER must be set before sourcing role_runner.sh}"
}

detect_remote_os_command() {
  cat <<'SH'
if command -v uname >/dev/null 2>&1; then
  uname_out="$(uname -s 2>/dev/null || true)"
  case "$uname_out" in
    Linux*) printf linux; exit 0 ;;
    MINGW*|MSYS*|CYGWIN*) printf windows; exit 0 ;;
  esac
fi
if command -v pwsh >/dev/null 2>&1 || command -v powershell.exe >/dev/null 2>&1; then
  printf windows
  exit 0
fi
printf unknown
SH
}

main() {
  require_role

  local local_mode=false
  local target_host=""
  local ssh_user="${SSH_USER:-root}"
  local ssh_port="${SSH_PORT:-22}"
  local target_os="${TARGET_OS:-auto}"
  local dry_run=false
  local visible=false
  local passthrough=()

  while [ "$#" -gt 0 ]; do
    case "$1" in
      --local) local_mode=true; shift ;;
      --target-host) target_host="$2"; shift 2 ;;
      --ssh-user) ssh_user="$2"; shift 2 ;;
      --ssh-port) ssh_port="$2"; shift 2 ;;
      --target-os) target_os="$2"; shift 2 ;;
      --dry-run) dry_run=true; shift ;;
      --visible) visible=true; passthrough+=("--visible"); shift ;;
      --orchestrator-host) export ORCHESTRATOR_HOST="$2"; shift 2 ;;
      --orchestrator-port) export ORCHESTRATOR_PORT="$2"; shift 2 ;;
      --rabbitmq-host) export RABBITMQ_HOST="$2"; shift 2 ;;
      --rabbitmq-port) export RABBITMQ_PORT="$2"; shift 2 ;;
      --postgres-host) export POSTGRES_HOST="$2"; shift 2 ;;
      --postgres-port) export POSTGRES_PORT="$2"; shift 2 ;;
      --minio-host) export MINIO_HOST="$2"; shift 2 ;;
      --minio-port) export MINIO_PORT="$2"; shift 2 ;;
      --help|-h) usage; exit 0 ;;
      *) passthrough+=("$1"); shift ;;
    esac
  done

  local helper_path="$SCRIPT_DIR/$HELPER"
  if [ ! -f "$helper_path" ]; then
    printf '[FAIL] Missing helper: %s\n' "$helper_path" >&2
    exit 1
  fi

  if [ "$local_mode" = true ] || [ -z "$target_host" ]; then
    if [ "$dry_run" = true ]; then
      printf '[dry-run] local role=%s helper=%s\n' "$ROLE" "$helper_path"
      printf '[dry-run] passthrough=%s\n' "${passthrough[*]:-}"
      exit 0
    fi
    exec bash "$helper_path" "${passthrough[@]}"
  fi

  local remote="$ssh_user@$target_host"
  local detected="$target_os"
  if [ "$target_os" = "auto" ]; then
    if [ "$dry_run" = true ]; then
      detected="auto"
    else
      detected="$(ssh -p "$ssh_port" -o StrictHostKeyChecking=accept-new "$remote" "$(detect_remote_os_command)")"
    fi
  fi

  if [ "$dry_run" = true ]; then
    printf '[dry-run] remote role=%s target=%s port=%s target_os=%s\n' "$ROLE" "$remote" "$ssh_port" "$detected"
    printf '[dry-run] would pipe helper %s to remote bash with exported endpoint env\n' "$helper_path"
    exit 0
  fi

  case "$detected" in
    linux|auto)
      ssh -p "$ssh_port" -o StrictHostKeyChecking=accept-new "$remote" \
        "ORCHESTRATOR_HOST='${ORCHESTRATOR_HOST:-}' ORCHESTRATOR_PORT='${ORCHESTRATOR_PORT:-50051}' RABBITMQ_HOST='${RABBITMQ_HOST:-127.0.0.1}' RABBITMQ_PORT='${RABBITMQ_PORT:-5672}' POSTGRES_HOST='${POSTGRES_HOST:-127.0.0.1}' POSTGRES_PORT='${POSTGRES_PORT:-5432}' MINIO_HOST='${MINIO_HOST:-127.0.0.1}' MINIO_PORT='${MINIO_PORT:-9000}' bash -s" < "$helper_path"
      ;;
    windows)
      printf '[FAIL] Windows target bootstrap for role %s requires the matching scripts/windows/%s.ps1 wrapper on the target.\n' "$ROLE" "$ROLE" >&2
      printf '       Run from a Windows controller with scripts/windows/%s.ps1 or use a Linux/Vast target for this role.\n' "$ROLE" >&2
      exit 2
      ;;
    *)
      printf '[FAIL] Could not detect target OS for %s\n' "$remote" >&2
      exit 2
      ;;
  esac
}

main "$@"
