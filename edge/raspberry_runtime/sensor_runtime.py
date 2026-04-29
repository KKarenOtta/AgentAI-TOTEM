from __future__ import annotations

from edge.voice_agent import loop as voice_loop

import base64
import os
import subprocess
import sys
import time
import threading
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
    readings = state.get("ultrassons") or []
    distances = [i.get("distance_cm") for i in readings if i.get("distance_cm") is not None]
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
        return None

    path = Path(CAPTURE_PATH)
    if not path.exists():
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


def send_trigger(state: dict) -> bool:
    payload = base_payload(state)
    payload["image_base64"] = capture_image_base64()

    try:
        r = requests.post(endpoint("trigger"), json=payload, timeout=REQUEST_TIMEOUT_SECONDS)
        return r.status_code == 200 and r.json().get("state", {}).get("present", False)
    except:
        return False


def send_heartbeat(state: dict):
    try:
        requests.post(endpoint("heartbeat"), json=base_payload(state), timeout=REQUEST_TIMEOUT_SECONDS)
    except:
        pass


def send_clear():
    try:
        requests.post(
            endpoint("clear"),
            json={
                "company_id": COMPANY_ID,
                "device_id": DEVICE_ID,
                "present": False,
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except:
        pass


def play_audio_base64(audio_b64: str):
    if not audio_b64:
        return

    path = "/tmp/greeting.mp3"
    Path(path).write_bytes(base64.b64decode(audio_b64))
    subprocess.run(["mpg123", "-q", path])


def start_voice_thread(session_id: str):
    thread = threading.Thread(target=voice_loop, args=(session_id,), daemon=True)
    thread.start()


def main():
    print("Raspberry Runtime iniciado")

    session_active = False
    voice_started = False
    last_trigger = 0
    last_heartbeat = 0
    last_presence = 0

    while True:
        try:
            state = update_system_state()
            now = time.time()

            if has_distance_presence(state):
                last_presence = now

            active = bool(state.get("service_session_active"))

            if not session_active:
                if active and now - last_trigger > TRIGGER_COOLDOWN_SECONDS:
                    accepted = send_trigger(state)
                    last_trigger = now

                    if accepted:
                        print("Sessão ativa")

                        session_id = f"totem-{int(time.time()*1000)}"
                        session_active = True

                        # greeting
                        try:
                            r = requests.post(
                                endpoint("activate"),
                                json={
                                    "company_id": COMPANY_ID,
                                    "session_id": session_id,
                                    "prefer_audio": True,
                                },
                                timeout=10,
                            )

                            if r.status_code == 200:
                                play_audio_base64(r.json().get("audio_base64"))
                        except:
                            pass

                        # voz em paralelo
                        start_voice_thread(session_id)
                        voice_started = True

            else:
                if now - last_presence > ABSENCE_TIMEOUT_SECONDS:
                    print("Sessão encerrada por ausência")
                    send_clear()
                    session_active = False
                    voice_started = False
                    continue

                if now - last_heartbeat > HEARTBEAT_SECONDS:
                    send_heartbeat(state)
                    last_heartbeat = now

            time.sleep(0.5)

        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    main()
