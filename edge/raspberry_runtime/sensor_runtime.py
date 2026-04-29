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
COOLDOWN_SECONDS = float(os.getenv("COOLDOWN_SECONDS", "10"))

CAMERA_DEVICE = os.getenv("CAMERA_DEVICE", "/dev/video0").strip()
CAPTURE_PATH = os.getenv("CAPTURE_PATH", "/tmp/totem_presence.jpg").strip()
CAPTURE_ENABLED = os.getenv("CAPTURE_ENABLED", "true").strip().lower() == "true"


def best_distance(state: dict) -> float | None:
    active_sensor = state.get("active_sensor")
    readings = state.get("ultrassons") or []

    for item in readings:
        if item.get("sensor") == active_sensor:
            return item.get("distance_cm")

    distances = [
        item.get("distance_cm")
        for item in readings
        if item.get("distance_cm") is not None
    ]

    return min(distances) if distances else None


def is_approaching(state: dict) -> bool:
    return any(bool(item.get("approaching")) for item in state.get("ultrassons") or [])


def capture_image_base64() -> str | None:
    if not CAPTURE_ENABLED:
        return None

    result = subprocess.run(
        [
            "fswebcam",
            "-d",
            CAMERA_DEVICE,
            "-r",
            "640x480",
            "--jpeg",
            "90",
            "--no-banner",
            CAPTURE_PATH,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        timeout=8,
    )

    if result.returncode != 0:
        print(f"[CAMERA] erro: {result.stderr.strip()}")
        return None

    image_path = Path(CAPTURE_PATH)
    if not image_path.exists():
        print("[CAMERA] imagem não criada")
        return None

    return base64.b64encode(image_path.read_bytes()).decode("utf-8")


def send_presence(state: dict) -> bool:
    if not TOTEM_API_URL:
        print("Erro: TOTEM_API_URL não configurada")
        return False

    image_base64 = capture_image_base64()

    payload = {
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
        "image_base64": image_base64,
    }

    try:
        response = requests.post(
            TOTEM_API_URL,
            json=payload,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )

        print(f"[API] {response.status_code} | {response.text[:500]}")

        if response.status_code != 200:
            return False

        data = response.json()
        state_payload = data.get("state", {})

        return bool(state_payload.get("present"))

    except Exception as exc:
        print(f"[ERRO API]: {exc}")
        return False


def main() -> None:
    print("Raspberry Runtime iniciado")
    print("Sensores: ultrassônicos + DHT + câmera")
    print(f"API: {TOTEM_API_URL}")
    print(f"COMPANY_ID: {COMPANY_ID}")
    print(f"DEVICE_ID: {DEVICE_ID}")
    print(f"COOLDOWN: {COOLDOWN_SECONDS}s")
    print(f"CAMERA_DEVICE: {CAMERA_DEVICE}")
    print(f"CAPTURE_ENABLED: {CAPTURE_ENABLED}")

    last_trigger = 0.0

    while True:
        try:
            state = update_system_state()

            presence = bool(state.get("presence"))
            active = bool(state.get("service_session_active"))
            now = time.time()

            if presence and active and now - last_trigger >= COOLDOWN_SECONDS:
                print(
                    "Presença real detectada | "
                    f"sensor={state.get('active_sensor')} "
                    f"distancia={best_distance(state)}cm "
                    f"aproximando={is_approaching(state)} "
                    f"temp={state.get('temperature')} "
                    f"umidade={state.get('humidity')}"
                )

                if send_presence(state):
                    print("Trigger aceito pelo backend")
                    last_trigger = now
                else:
                    print("Trigger rejeitado pelo backend")

            time.sleep(0.5)

        except KeyboardInterrupt:
            print("Encerrado manualmente")
            break

        except Exception as exc:
            print(f"[ERRO LOOP]: {exc}")
            time.sleep(1)


if __name__ == "__main__":
    main()
