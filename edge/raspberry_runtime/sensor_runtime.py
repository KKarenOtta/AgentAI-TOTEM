from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import requests

from alpha_test.sensor_service import update_system_state
from edge.raspberry_presence_sender.config import (
    TOTEM_API_URL,
    COMPANY_ID,
    DEVICE_ID,
    REQUEST_TIMEOUT_SECONDS,
    COOLDOWN_SECONDS,
)


def send_presence(state: dict) -> bool:
    if not TOTEM_API_URL:
        print("Erro: TOTEM_API_URL não configurada")
        return False

    payload = {
        "company_id": COMPANY_ID,
        "device_id": DEVICE_ID,
        "present": True,
        "image_base64": None,
        "source": "raspberry_ultrasonic",
        "active_sensor": state.get("active_sensor"),
        "distance_cm": _best_distance(state),
        "approaching": _is_approaching(state),
        "temperature": state.get("temperature"),
        "humidity": state.get("humidity"),
        "sensor_payload": state,
    }

    try:
        response = requests.post(
            TOTEM_API_URL,
            json=payload,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )

        print(f"[API] {response.status_code} | {response.text}")

        if response.status_code != 200:
            return False

        data = response.json()
        return bool(data.get("state", {}).get("present"))

    except Exception as exc:
        print(f"[ERRO API]: {exc}")
        return False


def _best_distance(state: dict) -> float | None:
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


def _is_approaching(state: dict) -> bool:
    return any(
        bool(item.get("approaching"))
        for item in state.get("ultrassons") or []
    )


def main() -> None:
    print("Raspberry Runtime iniciado")
    print("Sensores: 3 ultrassônicos + DHT22 + LED")
    print(f"API: {TOTEM_API_URL}")
    print(f"COMPANY_ID: {COMPANY_ID}")
    print(f"DEVICE_ID: {DEVICE_ID}")
    print(f"COOLDOWN: {COOLDOWN_SECONDS}s")

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
                    f"distancia={_best_distance(state)}cm "
                    f"aproximando={_is_approaching(state)}"
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
