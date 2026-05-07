#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_DIR="$ROOT_DIR/runtime/pids"

echo "==== TOTEM STOP ALL ===="

if [ -d "$PID_DIR" ]; then
  for pid_file in "$PID_DIR"/*.pid; do
    [ -e "$pid_file" ] || continue

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
    else
      echo "[OK] $name já estava parado"
    fi

    rm -f "$pid_file"
  done
fi

echo
echo "==== LIMPEZA DE PORTAS DO TOTEM ===="
lsof -tiTCP:8000 -sTCP:LISTEN | xargs kill -9 2>/dev/null || true
lsof -tiTCP:5000 -sTCP:LISTEN | xargs kill -9 2>/dev/null || true

echo "[OK] Serviços encerrados."
