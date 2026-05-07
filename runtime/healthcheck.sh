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
lsof -iTCP -sTCP:LISTEN -P | grep -E "8000|5000|6379|5432" || true

echo
echo "---- BACKEND ----"
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:8000/ || true

if [ -f "$PID_DIR/voice_server.pid" ]; then
  echo
  echo "---- VOICE SERVER ----"
  curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST http://127.0.0.1:5000/capture \
    -H "Content-Type: application/json" \
    -d '{"session_id":"healthcheck"}' || true
else
  echo
  echo "---- VOICE SERVER ----"
  echo "[INFO] não iniciado neste ambiente"
fi

echo
echo "---- ÚLTIMAS LINHAS DE LOG ----"
for log_file in "$LOG_DIR"/*.log; do
  [ -e "$log_file" ] || continue
  echo
  echo "## $(basename "$log_file")"
  tail -n 20 "$log_file"
done
