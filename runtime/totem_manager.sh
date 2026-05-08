#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

LOG_DIR="$ROOT_DIR/runtime/logs"
PID_DIR="$ROOT_DIR/runtime/pids"

DEFAULT_COMPANY_ID="${DEFAULT_COMPANY_ID:-FLX-001}"

mkdir -p "$LOG_DIR"
mkdir -p "$PID_DIR"

cd "$ROOT_DIR"

# =========================================================
# LOAD ENV
# =========================================================

if [ -f ".env" ]; then
  set -a
  source ".env"
  set +a
fi

# =========================================================
# PYTHON DETECTION
# =========================================================

detect_python() {
  if [ -n "${VIRTUAL_ENV:-}" ] && [ -x "$VIRTUAL_ENV/bin/python" ]; then
    echo "$VIRTUAL_ENV/bin/python"
    return
  fi

  if [ -x "$ROOT_DIR/venv/bin/python" ]; then
    echo "$ROOT_DIR/venv/bin/python"
    return
  fi

  if [ -x "$ROOT_DIR/.venv/bin/python" ]; then
    echo "$ROOT_DIR/.venv/bin/python"
    return
  fi

  command -v python || true
}

PYTHON_BIN="$(detect_python)"

if [ -z "$PYTHON_BIN" ]; then
  echo "[ERRO] Python não encontrado."
  exit 1
fi

# =========================================================
# VALIDATIONS
# =========================================================

validate_env() {
  echo "==== ENV VALIDATION ===="

  local required=(
    "OPENAI_API_KEY"
    "AWS_DB_HOST"
    "AWS_DB_NAME"
    "AWS_DB_USER"
    "AWS_DB_PASSWORD"
    "REDIS_URL"
  )

  for key in "${required[@]}"; do
    if [ -z "${!key:-}" ]; then
      echo "[ERRO] ENV ausente: $key"
      exit 1
    fi

    echo "[OK] $key"
  done
}

validate_redis() {
  echo
  echo "==== REDIS ===="

  if redis-cli ping >/dev/null 2>&1; then
    echo "[OK] Redis ativo"
  else
    echo "[ERRO] Redis indisponível"
    exit 1
  fi
}

# =========================================================
# PROCESS CONTROL
# =========================================================

start_process() {
  local name="$1"
  local cmd="$2"

  local log_file="$LOG_DIR/${name}.log"
  local pid_file="$PID_DIR/${name}.pid"

  if [ -f "$pid_file" ]; then
    local existing_pid
    existing_pid="$(cat "$pid_file")"

    if kill -0 "$existing_pid" 2>/dev/null; then
      echo "[OK] $name já rodando | PID $existing_pid"
      return
    fi
  fi

  echo "[START] $name"

  nohup env \
    PYTHONPATH="$ROOT_DIR" \
    PATH="$(dirname "$PYTHON_BIN"):$PATH" \
    bash -lc "
      cd '$ROOT_DIR'
      set -a
      source .env
      set +a
      exec $cmd
    " > "$log_file" 2>&1 &

  echo $! > "$pid_file"

  sleep 2

  if kill -0 "$(cat "$pid_file")" 2>/dev/null; then
    echo "[OK] $name iniciado | PID $(cat "$pid_file")"
  else
    echo "[ERRO] Falha ao iniciar $name"
    tail -n 40 "$log_file" || true
    exit 1
  fi
}

stop_processes() {
  echo "==== TOTEM STOP ===="

  for pid_file in "$PID_DIR"/*.pid; do
    [ -e "$pid_file" ] || continue

    local pid
    pid="$(cat "$pid_file")"

    kill "$pid" 2>/dev/null || true
    rm -f "$pid_file"
  done

  pkill -f uvicorn || true
  pkill -f celery || true
  pkill -f sync_worker || true

  sleep 2

  echo "[OK] Serviços encerrados."
}

# =========================================================
# SERVICES
# =========================================================

start_backend() {
  start_process \
    "backend" \
    "$PYTHON_BIN -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
}

start_sync_worker() {
  start_process \
    "sync_worker" \
    "$PYTHON_BIN -m core.persistence.sync_worker --interval 15"
}

start_celery() {
  local celery_bin
  celery_bin="$(dirname "$PYTHON_BIN")/celery"

  start_process \
    "celery_worker" \
    "$celery_bin -A infra.async_tasks.celery_app.celery worker --loglevel=INFO -n totem_worker@%h"

  start_process \
    "celery_beat" \
    "$celery_bin -A infra.async_tasks.celery_app.celery beat --loglevel=INFO"
}

# =========================================================
# HEALTH
# =========================================================

status() {
  echo
  echo "==== TOTEM STATUS ===="

  for pid_file in "$PID_DIR"/*.pid; do
    [ -e "$pid_file" ] || continue

    local name
    local pid

    name="$(basename "$pid_file" .pid)"
    pid="$(cat "$pid_file")"

    if kill -0 "$pid" 2>/dev/null; then
      echo "[OK] $name | PID $pid"
    else
      echo "[ERRO] $name parado"
    fi
  done

  echo
  echo "Backend: http://127.0.0.1:8000"
  echo "Totem:   http://127.0.0.1:8000/totem/$DEFAULT_COMPANY_ID"
  echo "Cliente: http://127.0.0.1:8000/client/$DEFAULT_COMPANY_ID"
}

health() {
  echo
  echo "==== BACKEND ===="

  curl -I http://127.0.0.1:8000 || true

  echo
  echo "==== REDIS ===="

  redis-cli ping || true
}

logs() {
  local service="${2:-}"

  if [ -n "$service" ]; then
    tail -n 120 -f "$LOG_DIR/${service}.log"
    return
  fi

  for file in "$LOG_DIR"/*.log; do
    [ -e "$file" ] || continue

    echo
    echo "==== $(basename "$file") ===="
    tail -n 80 "$file"
  done
}

start_all() {
  validate_env
  validate_redis

  echo
  echo "==== TOTEM START ===="

  start_backend

  sleep 5

  start_sync_worker
  start_celery

  sleep 5

  status
  health
}

# =========================================================
# CLI
# =========================================================

case "${1:-help}" in
  start)
    start_all
    ;;

  stop)
    stop_processes
    ;;

  restart)
    stop_processes
    start_all
    ;;

  status)
    status
    ;;

  health)
    health
    ;;

  logs)
    logs "$@"
    ;;

  *)
    echo "Uso:"
    echo "  bash runtime/totem_manager.sh start"
    echo "  bash runtime/totem_manager.sh stop"
    echo "  bash runtime/totem_manager.sh restart"
    echo "  bash runtime/totem_manager.sh status"
    echo "  bash runtime/totem_manager.sh health"
    echo "  bash runtime/totem_manager.sh logs [servico]"
    ;;
esac
