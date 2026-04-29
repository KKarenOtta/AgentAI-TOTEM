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
PRESENCE_HOLD_SECONDS = float(os.getenv("PRESENCE_HOLD_SECONDS", "5"))
ABSENCE_TIMEOUT_SECONDS = float(os.getenv("ABSENCE_TIMEOUT_SECONDS", "10"))
HEARTBEAT_SECONDS = float(os.getenv("HEARTBEAT_SECONDS", "10"))

CAMERA_DEVICE = os.getenv("CAMERA_DEVICE", "/dev/video0").strip()
CAPTURE_PATH = os.getenv("CAPTURE_PATH", "/tmp/totem_presence.jpg").strip()
CAPTURE_ENABLED = os.getenv("CAPTURE_ENABLED", "true").strip().lower() == "true"


def endpoint(path: str) -> str:
    base = TOTEM_API_URL
    if base.endswith("/trigger"):
        base = base[: -len("/trigger")]
    return f"{base}/{path.lstrip('/')}"


def best_distance(state: dict) -> float | None:
    readings = state.get("ultrassons") or []
    distances = [item.get("distance_cm") for item in readings if item.get("distance_cm") is not None]
    return min(distances) if distances else None


def has_presence_under_1m(state: dict) -> bool:
    distance = best_distance(state)
    return bool(state.get("presence")) and distance is not None and distance <= 100


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


def base_payload(state: dict, present: bool) -> dict:
    return {
        "company_id": COMPANY_ID,
        "device_id": DEVICE_ID,
        "present": present,
        "source": "raspberry_sensors_camera",
        "active_sensor": state.get("active_sensor"),
        "distance_cm": best_distance(state),
        "temperature": state.get("temperature"),
        "humidity": state.get("humidity"),
        "sensor_payload": state,
    }


def validation_origin(engine: str | None) -> str:
    if engine and "rekognition" in engine.lower():
        return "AWS_REKOGNITION"
    if engine:
        return "LOCAL_OPENCV"
    return "DESCONHECIDA"


def send_trigger(state: dict) -> bool:
    payload = base_payload(state, present=True)
    payload["image_base64"] = capture_image_base64()

    try:
        response = requests.post(
            endpoint("trigger"),
            json=payload,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )

        print(f"[TRIGGER] {response.status_code} | {response.text[:300]}")

        if response.status_code != 200:
            return False

        data = response.json()
        state_payload = data.get("state") or data
        attrs = state_payload.get("attributes") or {}

        accepted = bool(state_payload.get("present"))
        engine = attrs.get("validation_engine")
        reason = state_payload.get("reason") or attrs.get("reason")

        print(
            "[VALIDAÇÃO]",
            {
                "origem": validation_origin(engine),
                "engine": engine,
                "human_validated": attrs.get("human_validated"),
                "faces": attrs.get("faces_detected"),
                "profiles": attrs.get("profiles_detected"),
                "aws": attrs.get("rekognition"),
                "accepted": accepted,
                "reason": reason,
            },
        )

        return accepted

    except Exception as exc:
        print("[ERRO TRIGGER]:", exc)
        return False


def send_heartbeat(state: dict) -> None:
    try:
        response = requests.post(
            endpoint("heartbeat"),
            json=base_payload(state, present=True),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        print(f"[HEARTBEAT] {response.status_code} | distancia={best_distance(state)}")
    except Exception as exc:
        print("[ERRO HEARTBEAT]:", exc)


def send_clear() -> None:
    try:
        response = requests.post(
            endpoint("clear"),
            json={
                "company_id": COMPANY_ID,
                "device_id": DEVICE_ID,
                "present": False,
                "source": "raspberry_absence",
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        print(f"[CLEAR] {response.status_code} | reset por ausência")
    except Exception as exc:
        print("[ERRO CLEAR]:", exc)


def main() -> None:
    print("Runtime sensores iniciado")
    print("Fluxo: presença <1m por 5s → valida humano → sessão → ausência >10s → reset")
    print(f"API presença: {TOTEM_API_URL}")

    session_active = False
    presence_started_at: float | None = None
    absence_started_at: float | None = None
    last_heartbeat = 0.0

    while True:
        try:
            state = update_system_state()
            now = time.time()

            distance = best_distance(state)
            present = has_presence_under_1m(state)

            print(
                "[SENSOR]",
                {
                    "present_under_1m": present,
                    "distance_cm": distance,
                    "temperature": state.get("temperature"),
                    "humidity": state.get("humidity"),
                    "active_sensor": state.get("active_sensor"),
                },
            )

            if present:
                absence_started_at = None
                if presence_started_at is None:
                    presence_started_at = now
            else:
                presence_started_at = None
                if absence_started_at is None:
                    absence_started_at = now

            if not session_active:
                if presence_started_at is not None:
                    held = now - presence_started_at
                    print(f"[FLOW] presença contínua: {round(held, 1)}s/{PRESENCE_HOLD_SECONDS}s")

                    if held >= PRESENCE_HOLD_SECONDS:
                        print("[FLOW] presença estável; iniciando validação humana")
                        accepted = send_trigger(state)

                        if accepted:
                            session_active = True
                            last_heartbeat = now
                            print("[FLOW] sessão ativa; UI deve tocar greeting")
                        else:
                            print("[FLOW] humano não validado; aguardando nova presença estável")

                        presence_started_at = None

            else:
                if absence_started_at is not None:
                    absence = now - absence_started_at
                    print(f"[FLOW] ausência contínua: {round(absence, 1)}s/{ABSENCE_TIMEOUT_SECONDS}s")

                    if absence >= ABSENCE_TIMEOUT_SECONDS:
                        send_clear()
                        session_active = False
                        presence_started_at = None
                        absence_started_at = None
                        last_heartbeat = 0.0
                        print("[FLOW] sessão resetada; UI deve voltar para aguardando presença")
                        continue

                if now - last_heartbeat >= HEARTBEAT_SECONDS:
                    send_heartbeat(state)
                    last_heartbeat = now

            time.sleep(1)

        except KeyboardInterrupt:
            print("Encerrado manualmente")
            break

        except Exception as exc:
            print("[ERRO LOOP]:", exc)
            time.sleep(1)


if __name__ == "__main__":
    main()
