#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT_DIR/runtime/logs"
PID_DIR="$ROOT_DIR/runtime/pids"

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

IS_RASPBERRY=0
HAS_ARECORD=0

if uname -a | grep -qiE "raspberry|armv7|aarch64"; then
  IS_RASPBERRY=1
fi

if command -v arecord >/dev/null 2>&1; then
  HAS_ARECORD=1
fi

start_process() {
  local name="$1"
  local cmd="$2"
  local log_file="$LOG_DIR/${name}.log"
  local pid_file="$PID_DIR/${name}.pid"

  if [ -f "$pid_file" ] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
    echo "[OK] $name já está rodando"
    return
  fi

  echo "[START] $name"

  nohup bash -lc "cd '$ROOT_DIR' && $cmd" \
    > "$log_file" 2>&1 &

  echo $! > "$pid_file"

  echo "[OK] $name iniciado | PID $(cat "$pid_file")"
}

echo "==== TOTEM START ALL ===="
echo "[OK] Python: $PYTHON_BIN"

if redis-cli ping >/dev/null 2>&1; then
  echo "[OK] Redis ativo"
else
  echo "[AVISO] Redis indisponível"
fi

start_process \
  "backend" \
  "$PYTHON_BIN -m uvicorn app.main:app --host 0.0.0.0 --port 8000"

sleep 3

if [ "$HAS_ARECORD" -eq 1 ]; then
  start_process \
    "voice_server" \
    "$PYTHON_BIN edge/voice_server.py"
else
  echo "[INFO] voice_server ignorado (arecord indisponível)"
fi

if [ "$IS_RASPBERRY" -eq 1 ]; then
  start_process \
    "sensor_runtime" \
    "$PYTHON_BIN edge/raspberry_runtime/sensor_runtime.py"
else
  echo "[INFO] sensor_runtime ignorado fora do Raspberry"
fi

CELERY_BIN="$(dirname "$PYTHON_BIN")/celery"

if [ -x "$CELERY_BIN" ]; then
  start_process \
    "celery_worker" \
    "PYTHONPATH='$ROOT_DIR' $CELERY_BIN -A infra.async_tasks.celery_app.celery worker --loglevel=INFO -n totem_worker@%h"

  sleep 1

  start_process \
    "celery_beat" \
    "PYTHONPATH='$ROOT_DIR' $CELERY_BIN -A infra.async_tasks.celery_app.celery beat --loglevel=INFO"
else
  echo "[AVISO] celery não encontrado"
fi

echo
echo "==== SERVIÇOS ===="
find "$PID_DIR" -maxdepth 1 -type f | sort

echo
echo "Backend: http://127.0.0.1:8000"
echo "Totem:   http://127.0.0.1:8000/totem/FLX-001"
echo "Logs:    $LOG_DIR"
