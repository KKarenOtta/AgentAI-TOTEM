from __future__ import annotations

import base64
import os
import subprocess
import wave
from array import array
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")

API_URL = os.getenv("TOTEM_API_BASE_URL", "").rstrip("/")
COMPANY_ID = os.getenv("COMPANY_ID", "FLX-001")

AUDIO_DEVICE = os.getenv("AUDIO_CAPTURE_DEVICE", "plughw:3,0")
AUDIO_FILE = "/tmp/voice.wav"

RECORD_SECONDS = int(os.getenv("VOICE_RECORD_SECONDS", "6"))
MIN_RMS = int(os.getenv("VOICE_MIN_RMS", "150"))


def record_audio() -> bool:
    result = subprocess.run(
        [
            "arecord",
            "-D",
            AUDIO_DEVICE,
            "-f",
            "S16_LE",
            "-r",
            "16000",
            "-c",
            "1",
            "-d",
            str(RECORD_SECONDS),
            AUDIO_FILE,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode != 0:
        print("[VOICE] erro arecord:", result.stderr.strip())

    return result.returncode == 0


def compute_rms(path: str) -> int:
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
        print("[VOICE] erro rms:", type(exc).__name__)
        return 0


def to_base64() -> str:
    return base64.b64encode(Path(AUDIO_FILE).read_bytes()).decode("utf-8")


def transcribe(audio_base64: str) -> str:
    r = requests.post(
        f"{API_URL}/api/audio/transcribe",
        json={"audio_base64": audio_base64},
        timeout=60,
    )

    print("[VOICE] stt status:", r.status_code)
    print("[VOICE] stt body:", r.text[:500])

    if r.status_code != 200:
        return ""

    return (r.json().get("text") or "").strip()


def send_answer_to_ui(session_id: str, text: str, audio_base64: str | None) -> None:
    requests.post(
        f"{API_URL}/api/voice/status",
        json={
            "company_id": COMPANY_ID,
            "session_id": session_id,
            "status": "answer_ready",
            "text": text,
            "payload": {"audio_base64": audio_base64},
        },
        timeout=5,
    )


def capture_once(session_id: str) -> None:
    print("[VOICE] Captura iniciada")
    print("[VOICE] device:", AUDIO_DEVICE)
    print("[VOICE] api:", API_URL)

    if not API_URL:
        print("[VOICE] erro: TOTEM_API_BASE_URL vazio")
        return

    if not record_audio():
        print("[VOICE] erro gravação")
        return

    rms = compute_rms(AUDIO_FILE)
    print("[VOICE] rms:", rms)

    if rms < MIN_RMS:
        print("[VOICE] ignorado por silêncio")
        return

    text = transcribe(to_base64())

    if not text:
        print("[VOICE] transcrição vazia")
        return

    print("[VOICE] pergunta:", text)

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
        print("[VOICE] erro interact:", r.status_code, r.text[:300])
        return

    data = r.json()

    send_answer_to_ui(
        session_id=session_id,
        text=data.get("text"),
        audio_base64=data.get("audio_base64"),
    )

    print("[VOICE] resposta enviada para UI")
