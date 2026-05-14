from __future__ import annotations

import base64
import math
import os
import shutil
import subprocess
import wave
from array import array
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")

COMPANY_ID = os.getenv("COMPANY_ID", "FLX-001").strip()
DEVICE_ID = os.getenv("DEVICE_ID", "RPI3-SENSORS-001").strip()

AUDIO_DEVICE = os.getenv(
    "VOICE_AUDIO_DEVICE",
    os.getenv("AUDIO_CAPTURE_DEVICE", "plughw:3,0"),
).strip()

AUDIO_FILE = os.getenv("VOICE_AUDIO_FILE", "/tmp/totem_voice.wav").strip()
RECORD_SECONDS = int(os.getenv("VOICE_RECORD_SECONDS", "6"))
MIN_RMS = int(os.getenv("VOICE_MIN_RMS", "150"))


def record_audio() -> tuple[bool, str | None]:
    print("[VOICE] captura iniciada")
    print("[VOICE] device:", AUDIO_DEVICE)

    if not shutil.which("arecord"):
        return False, "arecord indisponível neste ambiente"

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

    try:
        result = subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return False, "arecord não encontrado"

    if result.returncode != 0:
        return False, result.stderr.strip() or "falha no arecord"

    path = Path(AUDIO_FILE)
    if not path.exists():
        return False, "arquivo de áudio não foi criado"

    if path.stat().st_size <= 44:
        return False, "arquivo de áudio inválido"

    print("[VOICE] áudio gravado:", AUDIO_FILE)
    return True, None


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


def capture_audio_payload(session_id: str | None = None) -> dict[str, Any]:
    sid = (session_id or "").strip()

    ok, error = record_audio()
    if not ok:
        return {
            "ok": False,
            "session_id": sid,
            "company_id": COMPANY_ID,
            "device_id": DEVICE_ID,
            "audio_device": AUDIO_DEVICE,
            "error": error,
        }

    rms = compute_rms(AUDIO_FILE)
    if rms < MIN_RMS:
        return {
            "ok": False,
            "session_id": sid,
            "company_id": COMPANY_ID,
            "device_id": DEVICE_ID,
            "audio_device": AUDIO_DEVICE,
            "rms": rms,
            "min_rms": MIN_RMS,
            "error": "silence",
        }

    audio_base64 = audio_to_base64(AUDIO_FILE)

    return {
        "ok": True,
        "session_id": sid,
        "company_id": COMPANY_ID,
        "device_id": DEVICE_ID,
        "audio_device": AUDIO_DEVICE,
        "audio_file": AUDIO_FILE,
        "audio_base64": audio_base64,
        "audio_base64_len": len(audio_base64),
        "rms": rms,
        "record_seconds": RECORD_SECONDS,
    }


def capture_once(session_id: str | None = None) -> dict[str, Any]:
    payload = capture_audio_payload(session_id)

    print(
        "[VOICE] capture_once:",
        {
            "ok": payload.get("ok"),
            "session_id": payload.get("session_id"),
            "rms": payload.get("rms"),
            "audio_base64_len": payload.get("audio_base64_len", 0),
            "error": payload.get("error"),
        },
    )

    return payload


if __name__ == "__main__":
    data = capture_once(os.getenv("VOICE_TEST_SESSION_ID", "voice-test"))
    print(
        {
            "ok": data.get("ok"),
            "session_id": data.get("session_id"),
            "rms": data.get("rms"),
            "audio_base64_len": data.get("audio_base64_len", 0),
            "error": data.get("error"),
        }
    )
