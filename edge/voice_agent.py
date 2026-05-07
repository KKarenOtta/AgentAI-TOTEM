from __future__ import annotations

import audioop
import base64
import os
import subprocess
import time
import wave

import requests
from dotenv import load_dotenv

load_dotenv()

# =========================================================
# CONFIG
# =========================================================

API_BASE_URL = os.getenv(
    "TOTEM_API_BASE_URL",
    "http://52.201.76.45:8000"
).rstrip("/")

COMPANY_ID = os.getenv(
    "COMPANY_ID",
    "FLX-001"
)

DEVICE_ID = os.getenv(
    "DEVICE_ID",
    "RPI3-SENSORS-001"
)

AUDIO_DEVICE = os.getenv(
    "VOICE_AUDIO_DEVICE",
    "plughw:2,0"
)

AUDIO_PATH = "/tmp/voice.wav"

RECORD_SECONDS = int(
    os.getenv("VOICE_RECORD_SECONDS", "4")
)

MIN_RMS = int(
    os.getenv("VOICE_MIN_RMS", "350")
)

MIN_TEXT_CHARS = int(
    os.getenv("VOICE_MIN_TEXT_CHARS", "8")
)

# =========================================================


def record_audio(duration: int = RECORD_SECONDS) -> bool:

    print("[VOICE] Captura iniciada")

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
        print("[VOICE] record_error:", result.stderr.strip())
        return False

    print("[VOICE] Áudio gravado")

    return True


def audio_rms(path: str) -> int:
    try:
        with wave.open(path, "rb") as wav:
            frames = wav.readframes(wav.getnframes())
            width = wav.getsampwidth()

            return int(audioop.rms(frames, width))

    except Exception:
        return 0


def audio_to_base64() -> str:

    with open(AUDIO_PATH, "rb") as file:
        return base64.b64encode(
            file.read()
        ).decode("utf-8")


def should_ignore_text(text: str) -> bool:

    cleaned = (text or "").strip()

    if len(cleaned) < MIN_TEXT_CHARS:
        return True

    lower = cleaned.lower()

    ignored = [
        "legendas",
        "subtitles",
        "obrigado por assistir",
        "oh look",
        "look what",
    ]

    return any(item in lower for item in ignored)


def transcribe(audio_base64: str) -> str:

    print("[VOICE] Enviando STT...")

    response = requests.post(
        f"{API_BASE_URL}/api/audio/transcribe",
        json={
            "audio_base64": audio_base64
        },
        timeout=60,
    )

    print("[VOICE] STT status:", response.status_code)

    if response.status_code != 200:
        print("[VOICE] STT erro:", response.text[:300])
        return ""

    data = response.json()

    text = (data.get("text") or "").strip()

    print("[VOICE] Texto:", text)

    return text


def interact(
    session_id: str,
    text: str,
):

    print("[VOICE] Enviando pergunta ao backend")

    response = requests.post(
        f"{API_BASE_URL}/totem/interact",
        json={
            "company_id": COMPANY_ID,
            "session_id": session_id,
            "message": text,
            "prefer_audio": True,
        },
        timeout=90,
    )

    print("[VOICE] interact_status:", response.status_code)

    if response.status_code != 200:
        print("[VOICE] interact_error:", response.text[:300])
        return None

    data = response.json()

    print("[VOICE] resposta:", data.get("text"))

    return data


def capture_once(session_id: str):

    print("")
    print("=" * 60)
    print("[VOICE] Sessão:", session_id)
    print("=" * 60)

    if not record_audio():
        return

    rms = audio_rms(AUDIO_PATH)

    print("[VOICE] RMS:", rms)

    if rms < MIN_RMS:
        print("[VOICE] silêncio detectado")
        return

    audio_base64 = audio_to_base64()

    text = transcribe(audio_base64)

    if not text:
        print("[VOICE] texto vazio")
        return

    if should_ignore_text(text):
        print("[VOICE] texto ignorado")
        return

    interact(session_id, text)


if __name__ == "__main__":

    print("")
    print("=" * 60)
    print("VOICE AGENT")
    print("API_BASE_URL:", API_BASE_URL)
    print("COMPANY_ID :", COMPANY_ID)
    print("DEVICE_ID  :", DEVICE_ID)
    print("AUDIO_DEV  :", AUDIO_DEVICE)
    print("=" * 60)

    while True:
        sid = f"voice-{int(time.time())}"

        capture_once(sid)

        time.sleep(1)
