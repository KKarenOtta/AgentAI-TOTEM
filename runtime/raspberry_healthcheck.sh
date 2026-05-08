#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

source venv/bin/activate

: "${COMPANY_ID:=FLX-001}"
: "${TOTEM_API_BASE_URL:=http://192.168.15.13:8000}"
: "${CAMERA_DEVICE:=/dev/video0}"
: "${VOICE_AUDIO_DEVICE:=plughw:3,0}"

echo "==== RASPBERRY HEALTHCHECK ===="

echo "[1] Backend"
curl -sS -m 5 "${TOTEM_API_BASE_URL}/api/dashboard/${COMPANY_ID}" >/dev/null \
  && echo "backend=ok" \
  || echo "backend=fail"

echo
echo "[2] Camera"
if command -v fswebcam >/dev/null 2>&1; then
  fswebcam -d "$CAMERA_DEVICE" -r 640x480 --jpeg 90 --no-banner /tmp/totem_health_camera.jpg >/dev/null 2>&1 \
    && echo "camera=ok" \
    || echo "camera=fail"
else
  echo "camera=fswebcam_missing"
fi

echo
echo "[3] Microfone"
if command -v arecord >/dev/null 2>&1; then
  arecord -D "$VOICE_AUDIO_DEVICE" -f S16_LE -r 16000 -c 1 -d 1 /tmp/totem_health_audio.wav >/dev/null 2>&1 \
    && echo "audio_capture=ok" \
    || echo "audio_capture=fail"
else
  echo "audio_capture=arecord_missing"
fi

echo
echo "[4] Processos"
ps aux | grep -E "sensor_runtime|voice_server" | grep -v grep || true
