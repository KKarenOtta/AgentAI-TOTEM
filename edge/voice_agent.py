from __future__ import annotations

import base64
import subprocess
import time

import requests

API_URL = "http://192.168.15.7:8000"
COMPANY_ID = "FLX-001"
SESSION_ID = f"voice-{int(time.time())}"

AUDIO_DEVICE = "plughw:2,0"
AUDIO_PATH = "/tmp/voice.wav"


def record_audio(duration: int = 4) -> bool:
    result = subprocess.run(
        [
            "arecord",
            "-D", AUDIO_DEVICE,
            "-f", "cd",
            "-t", "wav",
            "-d", str(duration),
            AUDIO_PATH,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode != 0:
        print("record_error:", result.stderr.strip())
        return False

    return True


def audio_to_base64() -> str:
    with open(AUDIO_PATH, "rb") as file:
        return base64.b64encode(file.read()).decode("utf-8")


def transcribe(audio_base64: str) -> str:
    response = requests.post(
        f"{API_URL}/api/audio/transcribe",
        json={"audio_base64": audio_base64},
        timeout=45,
    )

    print("stt_status:", response.status_code)

    if response.status_code != 200:
        print("stt_error:", response.text[:300])
        return ""

    data = response.json()
    print("stt_provider:", data.get("provider"))
    return (data.get("text") or "").strip()


def interact(text: str) -> None:
    response = requests.post(
        f"{API_URL}/totem/interact",
        json={
            "company_id": COMPANY_ID,
            "session_id": SESSION_ID,
            "message": text,
            "prefer_audio": True,
        },
        timeout=60,
    )

    print("interact_status:", response.status_code)

    if response.status_code != 200:
        print("interact_error:", response.text[:300])
        return

    data = response.json()
    print("resposta:", data.get("text"))


def loop() -> None:
    print("Voice agent iniciado")
    print("API_URL:", API_URL)
    print("AUDIO_DEVICE:", AUDIO_DEVICE)
    print("SESSION_ID:", SESSION_ID)

    while True:
        print("ouvindo...")

        if not record_audio():
            time.sleep(2)
            continue

        audio_base64 = audio_to_base64()
        text = transcribe(audio_base64)

        if not text:
            print("sem transcrição")
            time.sleep(1)
            continue

        print("pergunta:", text)
        interact(text)

        time.sleep(1)


if __name__ == "__main__":
    loop()
