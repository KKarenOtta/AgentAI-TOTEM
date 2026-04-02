from __future__ import annotations

import os
import requests

API_URL = os.getenv(
    "AUDIO_TRANSCRIBE_URL",
    "http://127.0.0.1:8000/api/audio/transcribe",
)

REQUEST_TIMEOUT = float(os.getenv("AUDIO_REQUEST_TIMEOUT", "30"))


def send_audio(file_path: str) -> str | None:
    print("[AUDIO] enviando para transcrição LOCAL...")

    try:
        with open(file_path, "rb") as audio_file:
            files = {"file": ("input.wav", audio_file, "audio/wav")}
            response = requests.post(
                API_URL,
                files=files,
                timeout=REQUEST_TIMEOUT,
            )

        if response.status_code != 200:
            print(f"[ERRO] falha na API: {response.status_code}")
            print(response.text)
            return None

        data = response.json()
        text = (data.get("text") or "").strip()

        print(f"[TRANSCRITO] {text}")

        return text

    except Exception as exc:
        print(f"[ERRO] transcrição: {exc}")
        return None
