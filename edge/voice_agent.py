from __future__ import annotations

import base64
import math
import os
import subprocess
import sys
import wave
from array import array
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

load_dotenv(ROOT_DIR / ".env")

API_BASE_URL = os.getenv("TOTEM_API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
COMPANY_ID = os.getenv("COMPANY_ID", "FLX-001").strip()
DEVICE_ID = os.getenv("DEVICE_ID", "RPI3-SENSORS-001").strip()

AUDIO_DEVICE = os.getenv(
    "VOICE_AUDIO_DEVICE",
    os.getenv("AUDIO_CAPTURE_DEVICE", "plughw:3,0"),
).strip()

AUDIO_FILE = os.getenv("VOICE_AUDIO_FILE", "/tmp/totem_voice.wav").strip()
RECORD_SECONDS = int(os.getenv("VOICE_RECORD_SECONDS", "6"))
MIN_RMS = int(os.getenv("VOICE_MIN_RMS", "150"))
MIN_TEXT_CHARS = int(os.getenv("VOICE_MIN_TEXT_CHARS", "3"))

REQUEST_TIMEOUT_SECONDS = int(os.getenv("VOICE_REQUEST_TIMEOUT_SECONDS", "90"))


def record_audio() -> bool:
    print("[VOICE] captura iniciada")
    print("[VOICE] device:", AUDIO_DEVICE)

    command = [
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
    ]

    result = subprocess.run(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode != 0:
        print("[VOICE] erro arecord:", result.stderr.strip())
        return False

    path = Path(AUDIO_FILE)

    if not path.exists() or path.stat().st_size <= 44:
        print("[VOICE] arquivo de áudio inválido")
        return False

    print("[VOICE] áudio gravado:", AUDIO_FILE)
    return True


def compute_rms(path: str) -> int:
    try:
        with wave.open(path, "rb") as wav_file:
            frames = wav_file.readframes(wav_file.getnframes())

        samples = array("h")
        samples.frombytes(frames)

        if not samples:
            return 0

        total = sum(sample * sample for sample in samples)
        return int(math.sqrt(total / len(samples)))

    except Exception as exc:
        print("[VOICE] erro rms:", type(exc).__name__)
        return 0


def audio_to_base64(path: str) -> str:
    return base64.b64encode(Path(path).read_bytes()).decode("utf-8")


def should_ignore_text(text: str) -> bool:
    cleaned = (text or "").strip()

    if len(cleaned) < MIN_TEXT_CHARS:
        return True

    lower = cleaned.lower()

    ignored_fragments = (
        "legendas",
        "subtitles",
        "obrigado por assistir",
        "thanks for watching",
    )

    return any(fragment in lower for fragment in ignored_fragments)


def post_json(path: str, payload: dict[str, Any], timeout: int = REQUEST_TIMEOUT_SECONDS) -> dict[str, Any] | None:
    if not API_BASE_URL:
        print("[VOICE] TOTEM_API_BASE_URL vazio")
        return None

    url = f"{API_BASE_URL}{path}"

    try:
        response = requests.post(url, json=payload, timeout=timeout)
        print("[VOICE] POST", path, response.status_code)

        if response.status_code >= 400:
            print("[VOICE] erro backend:", response.text[:500])
            return None

        return response.json()

    except Exception as exc:
        print("[VOICE] erro request:", type(exc).__name__, str(exc))
        return None


def transcribe(audio_base64: str) -> str:
    data = post_json(
        "/api/audio/transcribe",
        {"audio_base64": audio_base64},
        timeout=60,
    )

    if not data:
        return ""

    text = (data.get("text") or "").strip()
    print("[VOICE] transcrição:", text)
    return text


def publish_voice_status(
    session_id: str,
    status: str,
    text: str | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    post_json(
        "/api/voice/status",
        {
            "company_id": COMPANY_ID,
            "session_id": session_id,
            "status": status,
            "text": text,
            "payload": payload or {},
        },
        timeout=10,
    )


def interact(session_id: str, text: str) -> dict[str, Any] | None:
    return post_json(
        "/totem/interact",
        {
            "company_id": COMPANY_ID,
            "session_id": session_id,
            "message": text,
            "prefer_audio": True,
            "profile": {
                "device_id": DEVICE_ID,
                "input_mode": "voice",
            },
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )


def capture_once(session_id: str | None) -> None:
    sid = (session_id or "").strip()

    if not sid:
        print("[VOICE] session_id ausente")
        return

    print("[VOICE] sessão:", sid)
    print("[VOICE] api:", API_BASE_URL)
    print("[VOICE] company:", COMPANY_ID)

    publish_voice_status(
        sid,
        "listening",
        "Estou ouvindo sua pergunta.",
    )

    if not record_audio():
        publish_voice_status(
            sid,
            "capture_error",
            "Não consegui capturar o áudio.",
        )
        return

    rms = compute_rms(AUDIO_FILE)
    print("[VOICE] rms:", rms)

    if rms < MIN_RMS:
        publish_voice_status(
            sid,
            "silence",
            "Não consegui ouvir sua pergunta. Tente novamente.",
            {"rms": rms, "min_rms": MIN_RMS},
        )
        return

    audio_base64 = audio_to_base64(AUDIO_FILE)
    text = transcribe(audio_base64)

    if not text or should_ignore_text(text):
        publish_voice_status(
            sid,
            "empty_transcription",
            "Não consegui entender sua pergunta. Tente novamente.",
        )
        return

    publish_voice_status(
        sid,
        "transcribed",
        text,
    )

    data = interact(sid, text)

    if not data:
        publish_voice_status(
            sid,
            "interaction_error",
            "Não consegui processar sua pergunta agora.",
        )
        return

    answer = data.get("text") or "Resposta pronta."
    audio_response = data.get("audio_base64")

    publish_voice_status(
        sid,
        "answer_ready",
        answer,
        {
            "audio_base64": audio_response,
            "metric": data.get("metric") or {},
            "language": data.get("language"),
        },
    )

    print("[VOICE] resposta enviada para UI")


if __name__ == "__main__":
    capture_once(os.getenv("VOICE_TEST_SESSION_ID", "voice-test"))
