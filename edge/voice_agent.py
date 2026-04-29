from __future__ import annotations

import audioop
import base64
import subprocess
import time
import wave
from pathlib import Path

import requests

API_URL = "http://192.168.15.7:8000"
COMPANY_ID = "FLX-001"

AUDIO_CAPTURE_DEVICE = "plughw:3,0"
AUDIO_PLAYBACK_DEVICE = "plughw:0,0"

AUDIO_PATH = "/tmp/voice.wav"
RESPONSE_AUDIO_PATH = "/tmp/response.mp3"

RECORD_SECONDS = 4
MIN_RMS = 350
MIN_TEXT_CHARS = 3


def record_audio() -> bool:
    result = subprocess.run(
        [
            "arecord",
            "-D", AUDIO_CAPTURE_DEVICE,
            "-f", "cd",
            "-t", "wav",
            "-d", str(RECORD_SECONDS),
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


def audio_rms(path: str) -> int:
    try:
        with wave.open(path, "rb") as wav:
            frames = wav.readframes(wav.getnframes())
            return int(audioop.rms(frames, wav.getsampwidth()))
    except:
        return 0


def audio_to_base64() -> str:
    return base64.b64encode(Path(AUDIO_PATH).read_bytes()).decode("utf-8")


def play_audio_base64(audio_base64: str) -> None:
    if not audio_base64:
        return

    Path(RESPONSE_AUDIO_PATH).write_bytes(base64.b64decode(audio_base64))

    subprocess.run(
        ["mpg123", "-q", RESPONSE_AUDIO_PATH],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def transcribe(audio_base64: str) -> str:
    r = requests.post(
        f"{API_URL}/api/audio/transcribe",
        json={"audio_base64": audio_base64},
        timeout=45,
    )

    if r.status_code != 200:
        return ""

    return (r.json().get("text") or "").strip()


def interact(text: str, session_id: str) -> None:
    r = requests.post(
        f"{API_URL}/totem/interact",
        json={
            "company_id": COMPANY_ID,
            "session_id": session_id,
            "message": text,
            "prefer_audio": True,
        },
        timeout=60,
    )

    if r.status_code != 200:
        print("interact_error")
        return

    data = r.json()

    print("resposta:", data.get("text"))

    play_audio_base64(data.get("audio_base64"))


def loop(session_id: str) -> None:
    print("Voice loop iniciado:", session_id)

    while True:
        if not record_audio():
            time.sleep(1)
            continue

        if audio_rms(AUDIO_PATH) < MIN_RMS:
            continue

        text = transcribe(audio_to_base64())

        if not text or len(text) < MIN_TEXT_CHARS:
            continue

        print("pergunta:", text)

        interact(text, session_id)
