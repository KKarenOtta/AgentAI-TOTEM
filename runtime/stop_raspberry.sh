#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_DIR="$ROOT_DIR/runtime/pids"

stop_service() {
  local name="$1"
  local pid_file="$PID_DIR/${name}.pid"

  if [[ -f "$pid_file" ]]; then
    pid="$(cat "$pid_file" 2>/dev/null || true)"
    if [[ -n "${pid:-}" ]] && kill -0 "$pid" 2>/dev/null; then
      echo "[STOP] $name pid=$pid"
      kill "$pid" 2>/dev/null || true
      sleep 2
      kill -9 "$pid" 2>/dev/null || true
    fi
    rm -f "$pid_file"
  fi
}

stop_service raspberry_sensor
stop_service raspberry_voice_server
stop_service raspberry_watchdog

pkill -f "edge/raspberry_runtime/sensor_runtime.py" 2>/dev/null || true
pkill -f "edge/voice_server.py" 2>/dev/null || true

echo "[OK] Raspberry services stopped"
