#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_DIR="$ROOT_DIR/runtime/pids"
LOG_DIR="$ROOT_DIR/runtime/logs"

echo "==== TOTEM HEALTHCHECK ===="

echo
echo "---- PIDS ----"

if [ -d "$PID_DIR" ]; then
  for pid_file in "$PID_DIR"/*.pid; do
    [ -e "$pid_file" ] || continue

    name="$(basename "$pid_file" .pid)"
    pid="$(cat "$pid_file")"

    if kill -0 "$pid" 2>/dev/null; then
      echo "[OK] $name rodando | PID $pid"
    else
      echo "[ERRO] $name parado | PID antigo $pid"
    fi
  done
else
  echo "[INFO] Nenhum PID encontrado."
fi

echo
echo "---- PORTAS ----"

lsof -iTCP -sTCP:LISTEN -P \
  | grep -E "8000|6379|5432" || true

echo
echo "---- BACKEND ----"

for attempt in 1 2 3 4 5; do
  status="$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/ || true)"

  if [ "$status" != "000" ]; then
    echo "HTTP $status"
    break
  fi

  if [ "$attempt" = "5" ]; then
    echo "HTTP 000"
    break
  fi

  sleep 1
done

echo
echo "---- VOICE RUNTIME ----"
echo "[OK] runtime integrado ao backend"

echo
echo "---- ÚLTIMAS LINHAS DE LOG ----"

for log_file in "$LOG_DIR"/*.log; do
  [ -e "$log_file" ] || continue

  echo
  echo "## $(basename "$log_file")"

  tail -n 20 "$log_file"
done
