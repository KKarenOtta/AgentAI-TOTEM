from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import requests

ROOT_DIR = Path(__file__).resolve().parents[1]

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from edge.voice_agent import capture_once

API_BASE_URL = "http://52.201.76.45:8000"
COMPANY_ID = "FLX-001"

EVENTS_URL = f"{API_BASE_URL}/api/events/{COMPANY_ID}"


def process_event(event_data: dict) -> None:
    event_type = event_data.get("event")

    if event_type != "voice_capture_requested":
        return

    payload = event_data.get("payload") or {}

    session_id = (payload.get("session_id") or "").strip()

    if not session_id:
        print("[VOICE SERVER] session_id ausente")
        return

    print("")
    print("=" * 60)
    print("[VOICE SERVER] captura solicitada")
    print("[VOICE SERVER] session:", session_id)
    print("=" * 60)
    print("")

    try:
        capture_once(session_id)

    except Exception as exc:
        print("[VOICE SERVER] erro capture_once:", exc)


def listen_forever() -> None:
    while True:
        try:
            print("")
            print("=" * 60)
            print("VOICE EDGE LISTENER ONLINE")
            print("Escutando eventos SSE da AWS...")
            print(EVENTS_URL)
            print("=" * 60)
            print("")

            with requests.get(
                EVENTS_URL,
                stream=True,
                timeout=300,
            ) as response:

                for raw_line in response.iter_lines():
                    if not raw_line:
                        continue

                    line = raw_line.decode("utf-8").strip()

                    if not line.startswith("data:"):
                        continue

                    try:
                        json_data = line.removeprefix("data:").strip()

                        event_data = json.loads(json_data)

                        process_event(event_data)

                    except Exception as exc:
                        print("[VOICE SERVER] erro parse evento:", exc)

        except requests.RequestException as exc:
            print("[VOICE SERVER] conexão perdida:", exc)

        except Exception as exc:
            print("[VOICE SERVER] erro geral:", exc)

        print("[VOICE SERVER] reconectando em 5s...")
        time.sleep(5)


if __name__ == "__main__":
    listen_forever()
