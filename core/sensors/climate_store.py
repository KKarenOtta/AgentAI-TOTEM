from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

DATA_PATH = Path("data/sensors/climate_latest.json")


def save_climate(company_id: str, device_id: str, sensor_payload: dict[str, Any] | None) -> None:
    payload = sensor_payload or {}

    temperature = payload.get("temperature")
    humidity = payload.get("humidity")

    nested = payload.get("sensor_payload") or {}
    if temperature is None:
        temperature = nested.get("temperature")
    if humidity is None:
        humidity = nested.get("humidity")

    if temperature is None and humidity is None:
        return

    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)

    data = {}
    if DATA_PATH.exists():
        try:
            data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        except Exception:
            data = {}

    data[company_id] = {
        "company_id": company_id,
        "device_id": device_id,
        "temperature": temperature,
        "humidity": humidity,
        "updated_at_ts": time.time(),
    }

    DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_climate(company_id: str) -> dict[str, Any] | None:
    if not DATA_PATH.exists():
        return None

    try:
        data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None

    item = data.get(company_id)
    return item if isinstance(item, dict) else None


def answer_climate(company_id: str, question: str) -> tuple[str, float, str] | None:
    q = (question or "").lower()

    is_climate = any(
        term in q
        for term in [
            "temperatura",
            "clima",
            "calor",
            "frio",
            "umidade",
            "dht",
            "ambiente",
        ]
    )

    if not is_climate:
        return None

    climate = get_climate(company_id)
    if not climate:
        return (
            "Ainda não recebi uma leitura recente do sensor de temperatura e umidade.",
            1.0,
            "sensor_climate_missing",
        )

    temperature = climate.get("temperature")
    humidity = climate.get("humidity")

    parts = []

    if temperature is not None:
        parts.append(f"A temperatura ambiente medida pelo sensor é de {temperature}°C.")

    if humidity is not None:
        parts.append(f"A umidade relativa medida é de {humidity}%.")

    if not parts:
        return (
            "Recebi o sensor, mas a leitura de temperatura e umidade veio vazia.",
            1.0,
            "sensor_climate_empty",
        )

    return " ".join(parts), 1.0, "sensor_climate"
