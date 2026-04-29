from __future__ import annotations

import base64
import os
import subprocess
import time
import wave
from array import array
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")

API_URL = os.getenv("TOTEM_API_BASE_URL", "http://192.168.15.7:8000").rstrip("/")
COMPANY_ID = os.getenv("COMPANY_ID", "FLX-001").strip()

AUDIO_CAPTURE_DEVICE = os.getenv("AUDIO_CAPTURE_DEVICE", "plughw:3,0").strip()
AUDIO_PATH = os.getenv("VOICE_AUDIO_PATH", "/tmp/voice.wav").strip()

RECORD_SECONDS = int(os.getenv("VOICE_RECORD_SECONDS", "4"))
MIN_RMS = int(os.getenv("VOICE_MIN_RMS", "300"))
LOOP_SLEEP_SECONDS = float(os.getenv("VOICE_LOOP_SLEEP_SECONDS", "0.5"))


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

        samples = array("h")
        samples.frombytes(frames)

        if not samples:
            return 0

        total = sum(sample * sample for sample in samples)
        return int((total / len(samples)) ** 0.5)

    except Exception as exc:
        print("rms_error:", type(exc).__name__)
        return 0


def audio_to_base64() -> str:
    return base64.b64encode(Path(AUDIO_PATH).read_bytes()).decode("utf-8")


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

    return (response.json().get("text") or "").strip()


def publish_voice_status(session_id: str, status: str, text: str | None = None) -> None:
    try:
        requests.post(
            f"{API_URL}/api/voice/status",
            json={
                "company_id": COMPANY_ID,
                "session_id": session_id,
                "status": status,
                "text": text,
            },
            timeout=8,
        )
    except Exception as exc:
        print("voice_status_error:", type(exc).__name__)


<<<<<<< HEAD
def interact(text, session_id):
    r = requests.post(
=======
def interact(text: str, session_id: str) -> None:
    publish_voice_status(session_id, "transcribed", text)

    response = requests.post(
>>>>>>> ebb41f420435fa47767de07d2a406b43de416aa5
        f"{API_URL}/totem/interact",
        json={
            "company_id": COMPANY_ID,
            "session_id": session_id,
            "message": text,
            "prefer_audio": True,
        },
        timeout=60,
    )

<<<<<<< HEAD
    if r.status_code != 200:
        return

    data = r.json()
    print("resposta:", data.get("text"))

=======
    print("interact_status:", response.status_code)

    if response.status_code != 200:
        print("interact_error:", response.text[:300])
        publish_voice_status(session_id, "error", "Não consegui processar a pergunta.")
        return

    data = response.json()
    answer = data.get("text") or ""
    audio_base64 = data.get("audio_base64")

    print("resposta:", answer)

    try:
        requests.post(
            f"{API_URL}/api/voice/status",
            json={
                "company_id": COMPANY_ID,
                "session_id": session_id,
                "status": "answer_ready",
                "text": answer,
                "payload": {
                    "audio_base64": audio_base64,
                },
            },
            timeout=8,
        )
    except Exception as exc:
        print("answer_status_error:", type(exc).__name__)

>>>>>>> ebb41f420435fa47767de07d2a406b43de416aa5

def loop(session_id: str) -> None:
    print("Voice agent ativo:", session_id)
    print("API_URL:", API_URL)
    print("AUDIO_CAPTURE_DEVICE:", AUDIO_CAPTURE_DEVICE)

    while True:
        publish_voice_status(session_id, "listening", "Escutando...")

        if not record_audio():
            time.sleep(1)
            continue

        rms = audio_rms(AUDIO_PATH)
        print("rms:", rms)

        if rms < MIN_RMS:
            time.sleep(LOOP_SLEEP_SECONDS)
            continue

        publish_voice_status(session_id, "processing", "Processando sua pergunta...")

        text = transcribe(audio_to_base64())

        if not text:
            time.sleep(LOOP_SLEEP_SECONDS)
            continue

        print("pergunta:", text)
        interact(text, session_id)

        time.sleep(LOOP_SLEEP_SECONDS)


if __name__ == "__main__":
    loop(f"voice-{int(time.time())}")
