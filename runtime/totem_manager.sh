#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT_DIR/runtime/logs"
PID_DIR="$ROOT_DIR/runtime/pids"
DEFAULT_COMPANY_ID="${DEFAULT_COMPANY_ID:-FLX-001}"

mkdir -p "$LOG_DIR" "$PID_DIR"

cd "$ROOT_DIR"

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

start_process() {
  local name="$1"
  local cmd="$2"
  local log_file="$LOG_DIR/${name}.log"
  local pid_file="$PID_DIR/${name}.pid"

  if [ -f "$pid_file" ] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
    echo "[OK] $name já está rodando | PID $(cat "$pid_file")"
    return
  fi

  echo "[START] $name"

  nohup bash -lc \
    "cd '$ROOT_DIR' && $cmd" \
    > "$log_file" 2>&1 &

  echo $! > "$pid_file"

  echo "[OK] $name iniciado | PID $(cat "$pid_file")"
}

stop_processes() {
  echo "==== TOTEM STOP ===="

  for pid_file in "$PID_DIR"/*.pid; do
    [ -e "$pid_file" ] || continue

    local name
    local pid

    name="$(basename "$pid_file" .pid)"
    pid="$(cat "$pid_file")"

    if kill -0 "$pid" 2>/dev/null; then
      echo "[STOP] $name | PID $pid"

      pkill -P "$pid" 2>/dev/null || true
      kill "$pid" 2>/dev/null || true

      sleep 1

      if kill -0 "$pid" 2>/dev/null; then
        echo "[FORCE] $name | PID $pid"

        pkill -9 -P "$pid" 2>/dev/null || true
        kill -9 "$pid" 2>/dev/null || true
      fi
    fi

    rm -f "$pid_file"
  done

  lsof -tiTCP:8000 -sTCP:LISTEN \
    | xargs kill -9 2>/dev/null || true

  echo "[OK] Serviços encerrados."
}

is_raspberry() {
  uname -a | grep -qiE "raspberry|armv7|aarch64"
}

start_backend() {
  start_process \
    "backend" \
    "$PYTHON_BIN -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
}

start_sync_worker() {
  start_process \
    "sync_worker" \
    "PYTHONPATH='$ROOT_DIR' $PYTHON_BIN -m core.persistence.sync_worker --interval 15"
}

start_celery() {
  local celery_bin

  celery_bin="$(dirname "$PYTHON_BIN")/celery"

  if [ ! -x "$celery_bin" ]; then
    echo "[AVISO] celery não encontrado"
    return
  fi

  start_process \
    "celery_worker" \
    "PYTHONPATH='$ROOT_DIR' $celery_bin -A infra.async_tasks.celery_app.celery worker --loglevel=INFO -n totem_worker@%h"

  start_process \
    "celery_beat" \
    "PYTHONPATH='$ROOT_DIR' $celery_bin -A infra.async_tasks.celery_app.celery beat --loglevel=INFO"
}

start_edge() {
  if is_raspberry; then
    start_process \
      "sensor_runtime" \
      "$PYTHON_BIN edge/raspberry_runtime/sensor_runtime.py"
  else
    echo "[INFO] sensor_runtime ignorado: ambiente não identificado como Raspberry"
  fi
}

health() {
  bash runtime/healthcheck.sh
}

logs() {
  local service="${1:-}"

  if [ -n "$service" ]; then
    tail -n 120 -f "$LOG_DIR/${service}.log"
    return
  fi

  for log_file in "$LOG_DIR"/*.log; do
    [ -e "$log_file" ] || continue

    echo
    echo "==== $(basename "$log_file") ===="

    tail -n 80 "$log_file"
  done
}

status() {
  echo "==== TOTEM STATUS ===="
  echo "Python: $PYTHON_BIN"
  echo "Root:   $ROOT_DIR"

  echo
  echo "---- PIDS ----"

  for pid_file in "$PID_DIR"/*.pid; do
    [ -e "$pid_file" ] || continue

    name="$(basename "$pid_file" .pid)"
    pid="$(cat "$pid_file")"

    if kill -0 "$pid" 2>/dev/null; then
      echo "[OK] $name | PID $pid"
    else
      echo "[ERRO] $name parado | PID antigo $pid"
    fi
  done

  echo
  echo "Backend: http://127.0.0.1:8000"
  echo "Totem:   http://127.0.0.1:8000/totem/$DEFAULT_COMPANY_ID"
  echo "Cliente: http://127.0.0.1:8000/client/$DEFAULT_COMPANY_ID"
}

start_all() {
  echo "==== TOTEM START ===="
  echo "[OK] Python: $PYTHON_BIN"

  start_backend

  sleep 3

  start_sync_worker
  start_celery
  start_edge

  echo
  status
}

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
  backend)
    start_backend
    ;;
  sync)
    start_sync_worker
    ;;
  celery)
    start_celery
    ;;
  edge)
    start_edge
    ;;
  health)
    health
    ;;
  status)
    status
    ;;
  logs)
    logs "${2:-}"
    ;;
  help|*)
    echo "Uso:"
    echo "  ./runtime/totem_manager.sh start"
    echo "  ./runtime/totem_manager.sh stop"
    echo "  ./runtime/totem_manager.sh restart"
    echo "  ./runtime/totem_manager.sh status"
    echo "  ./runtime/totem_manager.sh health"
    echo "  ./runtime/totem_manager.sh logs [servico]"
    echo "  ./runtime/totem_manager.sh backend"
    echo "  ./runtime/totem_manager.sh sync"
    echo "  ./runtime/totem_manager.sh celery"
    echo "  ./runtime/totem_manager.sh edge"
    ;;
esac
