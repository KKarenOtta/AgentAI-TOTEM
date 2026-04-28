from __future__ import annotations

from typing import Any

import requests

from camera import capture_image_base64
from config import (
    COMPANY_ID,
    DEVICE_ID,
    REQUEST_TIMEOUT_SECONDS,
    TOTEM_API_URL,
)


def send_trigger(sensor_state: dict[str, Any]) -> bool:
    if not TOTEM_API_URL:
        print("Erro: TOTEM_API_URL não configurada")
        return False

    image_base64 = capture_image_base64()
    if not image_base64:
        print("Erro: imagem não capturada; trigger cancelado")
        return False

    payload = {
        "company_id": COMPANY_ID,
        "device_id": DEVICE_ID,
        "present": True,
        "source": "ultrasonic_camera",
        "active_sensor": sensor_state.get("active_sensor"),
        "distance_cm": sensor_state.get("distance_cm"),
        "approaching": bool(sensor_state.get("approaching", False)),
        "confidence": sensor_state.get("confidence"),
        "sensor_payload": sensor_state,
        "image_base64": image_base64,
    }

    try:
        response = requests.post(
            TOTEM_API_URL,
            json=payload,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )

        print(f"Status: {response.status_code}")
        print(response.text)

        if response.status_code != 200:
            return False

        data = response.json()
        state = data.get("state", {})
        accepted = bool(state.get("present", False))

        if accepted:
            print("Presença aceita pela API")
        else:
            print("Presença rejeitada pela API")

        return accepted

    except Exception as exc:
        print(f"Erro ao enviar trigger: {exc}")
        return False
