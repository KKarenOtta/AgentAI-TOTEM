from __future__ import annotations

import base64
import os
import subprocess
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

load_dotenv(ROOT_DIR / ".env")

from alpha_test.sensor_service import update_system_state

TOTEM_API_URL = os.getenv("TOTEM_API_URL", "").strip()
COMPANY_ID = os.getenv("COMPANY_ID", "FLX-001").strip()
DEVICE_ID = os.getenv("DEVICE_ID", "RPI3-SENSORS-001").strip()

REQUEST_TIMEOUT_SECONDS = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "10"))
TRIGGER_COOLDOWN_SECONDS = float(os.getenv("COOLDOWN_SECONDS", "10"))
HEARTBEAT_SECONDS = float(os.getenv("HEARTBEAT_SECONDS", "10"))
ABSENCE_TIMEOUT_SECONDS = float(os.getenv("ABSENCE_TIMEOUT_SECONDS", "10"))

CAMERA_DEVICE = os.getenv("CAMERA_DEVICE", "/dev/video0").strip()
CAPTURE_PATH = os.getenv("CAPTURE_PATH", "/tmp/totem_presence.jpg").strip()
CAPTURE_ENABLED = os.getenv("CAPTURE_ENABLED", "true").strip().lower() == "true"


def endpoint(path: str) -> str:
    base = TOTEM_API_URL
    if base.endswith("/trigger"):
        base = base[: -len("/trigger")]
    return f"{base}/{path.lstrip('/')}"


def best_distance(state: dict) -> float | None:
    active_sensor = state.get("active_sensor")
    readings = state.get("ultrassons") or []

    for item in readings:
        if item.get("sensor") == active_sensor:
            return item.get("distance_cm")

    distances = [item.get("distance_cm") for item in readings if item.get("distance_cm") is not None]
    return min(distances) if distances else None


def is_approaching(state: dict) -> bool:
    return any(bool(item.get("approaching")) for item in state.get("ultrassons") or [])


def has_distance_presence(state: dict) -> bool:
    return bool(state.get("presence")) and best_distance(state) is not None


def capture_image_base64() -> str | None:
    if not CAPTURE_ENABLED:
        return None

    result = subprocess.run(
        [
            "fswebcam",
            "-d", CAMERA_DEVICE,
            "-r", "640x480",
            "--jpeg", "90",
            "--no-banner",
            CAPTURE_PATH,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        timeout=8,
    )

    if result.returncode != 0:
        print("[CAMERA] erro:", result.stderr.strip())
        return None

    path = Path(CAPTURE_PATH)
    if not path.exists():
        print("[CAMERA] imagem não criada")
        return None

    return base64.b64encode(path.read_bytes()).decode("utf-8")


def base_payload(state: dict) -> dict:
    return {
        "company_id": COMPANY_ID,
        "device_id": DEVICE_ID,
        "present": True,
        "source": "raspberry_sensors_camera",
        "active_sensor": state.get("active_sensor"),
        "distance_cm": best_distance(state),
        "approaching": is_approaching(state),
        "temperature": state.get("temperature"),
        "humidity": state.get("humidity"),
        "sensor_payload": state,
    }


def send_trigger(state: dict) -> bool:
    payload = base_payload(state)
    payload["image_base64"] = capture_image_base64()

    try:
        response = requests.post(
            endpoint("trigger"),
            json=payload,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        print(f"[TRIGGER] {response.status_code} | {response.text[:500]}")

        if response.status_code != 200:
            return False

        data = response.json()
        return bool(data.get("state", {}).get("present"))

    except Exception as exc:
        print("[ERRO TRIGGER]:", exc)
        return False


def send_heartbeat(state: dict) -> bool:
    payload = base_payload(state)

    try:
        response = requests.post(
            endpoint("heartbeat"),
            json=payload,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        print(f"[HEARTBEAT] {response.status_code} | distancia={payload.get('distance_cm')} temp={payload.get('temperature')}")

        return response.status_code == 200

    except Exception as exc:
        print("[ERRO HEARTBEAT]:", exc)
        return False


def send_clear() -> None:
    payload = {
        "company_id": COMPANY_ID,
        "device_id": DEVICE_ID,
        "present": False,
        "source": "raspberry_absence",
    }

    try:
        response = requests.post(
            endpoint("clear"),
            json=payload,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        print(f"[CLEAR] {response.status_code} | sessão encerrada por ausência")

    except Exception as exc:
        print("[ERRO CLEAR]:", exc)


def main() -> None:
    print("Raspberry Runtime iniciado")
    print("Modo: busca validação humana → sessão ativa → heartbeat → clear por ausência")
    print(f"API: {TOTEM_API_URL}")
    print(f"COMPANY_ID: {COMPANY_ID}")
    print(f"DEVICE_ID: {DEVICE_ID}")
    print(f"TRIGGER_COOLDOWN: {TRIGGER_COOLDOWN_SECONDS}s")
    print(f"HEARTBEAT: {HEARTBEAT_SECONDS}s")
    print(f"ABSENCE_TIMEOUT: {ABSENCE_TIMEOUT_SECONDS}s")
    print(f"CAMERA_DEVICE: {CAMERA_DEVICE}")

    session_active = False
    last_trigger = 0.0
    last_heartbeat = 0.0
    last_presence = 0.0

    while True:
        try:
            state = update_system_state()
            now = time.time()

            distance_present = has_distance_presence(state)
            active = bool(state.get("service_session_active"))

            if distance_present:
                last_presence = now

            if not session_active:
                if distance_present and active and now - last_trigger >= TRIGGER_COOLDOWN_SECONDS:
                    print(
                        "Buscando validação humana | "
                        f"sensor={state.get('active_sensor')} "
                        f"distancia={best_distance(state)}cm "
                        f"temp={state.get('temperature')} "
                        f"umidade={state.get('humidity')}"
                    )

                    accepted = send_trigger(state)
                    last_trigger = now

                    if accepted:
                        session_active = True
                        last_heartbeat = now
                        print("Sessão ativa: validação humana aceita")
                    else:
                        print("Validação rejeitada; continua buscando presença real")

            else:
                absence_time = now - last_presence

                if absence_time >= ABSENCE_TIMEOUT_SECONDS:
                    print(f"Ausência por {round(absence_time, 1)}s: encerrando sessão")
                    send_clear()
                    session_active = False
                    last_trigger = 0.0
                    last_heartbeat = 0.0
                    continue

                if now - last_heartbeat >= HEARTBEAT_SECONDS:
                    send_heartbeat(state)
                    last_heartbeat = now

            time.sleep(0.5)

        except KeyboardInterrupt:
            print("Encerrado manualmente")
            break

        except Exception as exc:
            print("[ERRO LOOP]:", exc)
            time.sleep(1)


if __name__ == "__main__":
    main()
