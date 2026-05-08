#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PID_DIR="$ROOT_DIR/runtime/pids"
LOG_DIR="$ROOT_DIR/runtime/logs"
mkdir -p "$PID_DIR" "$LOG_DIR"

if [[ ! -d "venv" ]]; then
  echo "[ERRO] venv não encontrada"
  exit 1
fi

source venv/bin/activate

if [[ -f ".env" ]]; then
  set -a
  source .env
  set +a
fi

export COMPANY_ID="${COMPANY_ID:-FLX-001}"
export DEVICE_ID="${DEVICE_ID:-RPI3-SENSORS-001}"
export TOTEM_API_BASE_URL="${TOTEM_API_BASE_URL:-http://192.168.15.13:8000}"
export TOTEM_API_URL="${TOTEM_API_URL:-${TOTEM_API_BASE_URL}/api/presence/trigger}"
export PRESENCE_HOLD_SECONDS="${PRESENCE_HOLD_SECONDS:-3}"
export ABSENCE_TIMEOUT_SECONDS="${ABSENCE_TIMEOUT_SECONDS:-10}"
export HEARTBEAT_SECONDS="${HEARTBEAT_SECONDS:-10}"
export CAPTURE_ENABLED="${CAPTURE_ENABLED:-true}"
export CAMERA_DEVICE="${CAMERA_DEVICE:-/dev/video0}"
export VOICE_AUDIO_DEVICE="${VOICE_AUDIO_DEVICE:-plughw:3,0}"

echo "==== RASPBERRY STARTUP ===="
echo "COMPANY_ID=$COMPANY_ID"
echo "DEVICE_ID=$DEVICE_ID"
echo "TOTEM_API_BASE_URL=$TOTEM_API_BASE_URL"
echo "TOTEM_API_URL=$TOTEM_API_URL"
echo "CAMERA_DEVICE=$CAMERA_DEVICE"
echo "VOICE_AUDIO_DEVICE=$VOICE_AUDIO_DEVICE"

echo
echo "[1] Validando Python"
python -m py_compile \
  edge/raspberry_runtime/sensor_runtime.py \
  edge/voice_server.py \
  edge/voice_agent.py

echo
echo "[2] Healthcheck inicial"
bash runtime/raspberry_healthcheck.sh || true

echo
echo "[3] Iniciando sensor runtime"
nohup python edge/raspberry_runtime/sensor_runtime.py \
  > "$LOG_DIR/raspberry_sensor.log" 2>&1 &
echo $! > "$PID_DIR/raspberry_sensor.pid"

sleep 2

echo
echo "[4] Iniciando voice server"
nohup python edge/voice_server.py \
  > "$LOG_DIR/raspberry_voice_server.log" 2>&1 &
echo $! > "$PID_DIR/raspberry_voice_server.pid"

sleep 2

echo
echo "[5] Validando processos"
ps aux | grep -E "sensor_runtime|voice_server" | grep -v grep || true

echo
echo "[OK] Raspberry runtime online"
