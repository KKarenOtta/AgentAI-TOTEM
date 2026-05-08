#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

source venv/bin/activate

MODE="${1:-backend}"
export TOTEM_WATCHDOG_MODE="$MODE"
export TOTEM_WATCHDOG_INTERVAL="${TOTEM_WATCHDOG_INTERVAL:-10}"

mkdir -p runtime/logs runtime/pids

nohup python runtime/watchdog.py \
  > "runtime/logs/watchdog_${MODE}.log" 2>&1 &

echo $! > "runtime/pids/watchdog_${MODE}.pid"

echo "[OK] watchdog iniciado mode=$MODE"
