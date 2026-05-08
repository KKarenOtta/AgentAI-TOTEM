from __future__ import annotations

import json
import os
import platform
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PID_DIR = ROOT / "runtime" / "pids"
LOG_DIR = ROOT / "runtime" / "logs"
STATE_DIR = ROOT / "runtime" / "state"

PID_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)
STATE_DIR.mkdir(parents=True, exist_ok=True)

MODE = os.getenv("TOTEM_WATCHDOG_MODE", "backend").strip().lower()
INTERVAL = int(os.getenv("TOTEM_WATCHDOG_INTERVAL", "10"))


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def log(event: str, payload: dict[str, Any]) -> None:
    row = {"timestamp": now(), "event": event, **payload}
    with (LOG_DIR / "watchdog.jsonl").open("a", encoding="utf-8") as file:
        file.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(row)


def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def read_pid(name: str) -> int | None:
    path = PID_DIR / f"{name}.pid"
    if not path.exists():
        return None
    try:
        return int(path.read_text().strip())
    except Exception:
        return None


def shell(command: str) -> None:
    subprocess.Popen(
        command,
        shell=True,
        cwd=str(ROOT),
        stdout=(LOG_DIR / "watchdog_restart.log").open("a", encoding="utf-8"),
        stderr=subprocess.STDOUT,
        executable="/bin/bash",
    )


BACKEND_SERVICES = {
    "backend": "source venv/bin/activate && nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > runtime/logs/backend.log 2>&1 & echo $! > runtime/pids/backend.pid",
    "sync_worker": "source venv/bin/activate && nohup python -m core.persistence.sync_worker > runtime/logs/sync_worker.log 2>&1 & echo $! > runtime/pids/sync_worker.pid",
    "celery_worker": "source venv/bin/activate && nohup celery -A infra.async_tasks.celery_app.celery worker --loglevel=INFO --pool=solo > runtime/logs/celery_worker.log 2>&1 & echo $! > runtime/pids/celery_worker.pid",
    "celery_beat": "source venv/bin/activate && nohup celery -A infra.async_tasks.celery_app.celery beat --loglevel=INFO > runtime/logs/celery_beat.log 2>&1 & echo $! > runtime/pids/celery_beat.pid",
}

RASPBERRY_SERVICES = {
    "raspberry_sensor": "source venv/bin/activate && nohup python edge/raspberry_runtime/sensor_runtime.py > runtime/logs/raspberry_sensor.log 2>&1 & echo $! > runtime/pids/raspberry_sensor.pid",
    "raspberry_voice_server": "source venv/bin/activate && nohup python edge/voice_server.py > runtime/logs/raspberry_voice_server.log 2>&1 & echo $! > runtime/pids/raspberry_voice_server.pid",
}


def memory_snapshot() -> dict[str, Any]:
    if platform.system() == "Darwin":
        command = "vm_stat"
    else:
        command = "free -m"

    try:
        output = subprocess.check_output(command, shell=True, text=True, timeout=3)
        return {"command": command, "output": output[:1200]}
    except Exception as exc:
        return {"error": type(exc).__name__}


def check_services(services: dict[str, str]) -> None:
    for name, command in services.items():
        pid = read_pid(name)

        if pid and pid_alive(pid):
            log("service_ok", {"service": name, "pid": pid})
            continue

        log("service_down", {"service": name, "pid": pid})
        shell(command)
        time.sleep(2)

        new_pid = read_pid(name)
        log("service_restart_attempted", {"service": name, "new_pid": new_pid})


def main() -> None:
    services = RASPBERRY_SERVICES if MODE == "raspberry" else BACKEND_SERVICES
    log("watchdog_started", {"mode": MODE, "interval": INTERVAL, "services": list(services)})

    while True:
        try:
            check_services(services)
            log("resource_snapshot", {"memory": memory_snapshot()})
        except Exception as exc:
            log("watchdog_error", {"error": f"{type(exc).__name__}: {exc}"})

        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
