from __future__ import annotations

import base64
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

load_dotenv(ROOT_DIR / ".env")

from alpha_test.sensor_service import update_system_state
from edge.voice_agent import loop as voice_loop

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
    readings = state.get("ultrassons") or []
    distances = [item.get("distance_cm") for item in readings if item.get("distance_cm") is not None]
    return min(distances) if distances else None


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
        "distance_cm": best_distance(state),
        "temperature": state.get("temperature"),
        "humidity": state.get("humidity"),
        "sensor_payload": state,
    }


def send_trigger(state: dict) -> tuple[bool, str | None]:
    payload = base_payload(state)
    payload["image_base64"] = capture_image_base64()

    try:
        response = requests.post(
            endpoint("trigger"),
            json=payload,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )

        print(f"[TRIGGER] {response.status_code} | {response.text[:300]}")

        if response.status_code != 200:
            return False, None

        data = response.json()
        accepted = bool(data.get("state", {}).get("present"))
        session_id = data.get("session_id") or f"totem-{int(time.time() * 1000)}"

        return accepted, session_id

    except Exception as exc:
        print("[ERRO TRIGGER]:", exc)
        return False, None


def send_heartbeat(state: dict) -> None:
    try:
        response = requests.post(
            endpoint("heartbeat"),
            json=base_payload(state),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        print(f"[HEARTBEAT] {response.status_code}")
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
        print(f"[CLEAR] {response.status_code}")
    except Exception as exc:
        print("[ERRO CLEAR]:", exc)


def start_voice_thread(session_id: str) -> threading.Thread:
    thread = threading.Thread(target=voice_loop, args=(session_id,), daemon=True)
    thread.start()
    return thread


def main() -> None:
    print("Raspberry Runtime iniciado")
    print("Responsabilidade: sensores + câmera + microfone")
    print(f"API presença: {TOTEM_API_URL}")
    print(f"COMPANY_ID: {COMPANY_ID}")
    print(f"DEVICE_ID: {DEVICE_ID}")

    session_active = False
    voice_thread: threading.Thread | None = None

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
                        f"distancia={best_distance(state)}cm "
                        f"temp={state.get('temperature')} "
                        f"umidade={state.get('humidity')}"
                    )

                    accepted, session_id = send_trigger(state)
                    last_trigger = now

                    if accepted:
                        session_active = True
                        last_heartbeat = now

                        active_session_id = session_id or f"totem-{int(time.time() * 1000)}"

                        print(f"Sessão ativa: {active_session_id}")
                        print("Greeting e resposta devem sair pela página do totem, não pelo Raspberry.")

                        if voice_thread is None or not voice_thread.is_alive():
                            voice_thread = start_voice_thread(active_session_id)

                    else:
                        print("Validação rejeitada; continua buscando presença real")

            else:
                absence_time = now - last_presence

                if absence_time >= ABSENCE_TIMEOUT_SECONDS:
                    print(f"Ausência por {round(absence_time, 1)}s: encerrando sessão")
                    send_clear()
                    session_active = False
                    voice_thread = None
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
