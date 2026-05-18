#!/usr/bin/env bash
set -Eeuo pipefail

HOST=""
SSH_USER="root"
SSH_PORT="22"
LOCAL_GRPC_PORT="50051"
LOCAL_RABBIT_PORT="5672"
NODE_GRPC_PORT="15051"
NODE_RABBIT_PORT="15670"
RECONNECT_DELAY="5"
DRY_RUN=false

while [ "$#" -gt 0 ]; do
  case "$1" in
    --host) HOST="$2"; shift 2 ;;
    --ssh-user) SSH_USER="$2"; shift 2 ;;
    --ssh-port) SSH_PORT="$2"; shift 2 ;;
    --local-grpc-port) LOCAL_GRPC_PORT="$2"; shift 2 ;;
    --local-rabbit-port) LOCAL_RABBIT_PORT="$2"; shift 2 ;;
    --node-grpc-port) NODE_GRPC_PORT="$2"; shift 2 ;;
    --node-rabbit-port) NODE_RABBIT_PORT="$2"; shift 2 ;;
    --reconnect-delay) RECONNECT_DELAY="$2"; shift 2 ;;
    --dry-run) DRY_RUN=true; shift ;;
    *) echo "[FAIL] Unknown argument: $1" >&2; exit 2 ;;
  esac
done

[ -n "$HOST" ] || { echo "[FAIL] --host is required" >&2; exit 2; }

cmd=(ssh -p "$SSH_PORT" -N -T
  -o ExitOnForwardFailure=yes
  -o StrictHostKeyChecking=accept-new
  -o ServerAliveInterval=30
  -o ServerAliveCountMax=3
  -R "$NODE_GRPC_PORT:127.0.0.1:$LOCAL_GRPC_PORT"
  -R "$NODE_RABBIT_PORT:127.0.0.1:$LOCAL_RABBIT_PORT"
  "$SSH_USER@$HOST")

if [ "$DRY_RUN" = true ]; then
  printf '[dry-run] %s\n' "${cmd[*]}"
  exit 0
fi

while true; do
  "${cmd[@]}" || true
  sleep "$RECONNECT_DELAY"
done
