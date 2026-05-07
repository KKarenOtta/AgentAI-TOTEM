#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

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

set -a
source runtime/env_templates/raspberry.env
set +a

echo "==== TOTEM RASPBERRY EDGE ===="
echo "[OK] Python: $PYTHON_BIN"

"$PYTHON_BIN" edge/voice_server.py &
"$PYTHON_BIN" edge/raspberry_runtime/sensor_runtime.py
