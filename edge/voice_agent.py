from __future__ import annotations

<<<<<<< HEAD
import audioop
import base64
import os
import subprocess
import time
import wave
=======
import base64
import os
import subprocess
import wave
from array import array
from pathlib import Path
>>>>>>> 88e96e29cf5d5e7cb7b44cdac8e230b9a9d9d57c

import requests
from dotenv import load_dotenv

<<<<<<< HEAD
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
=======
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
>>>>>>> 88e96e29cf5d5e7cb7b44cdac8e230b9a9d9d57c
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode != 0:
<<<<<<< HEAD
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
=======
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
>>>>>>> 88e96e29cf5d5e7cb7b44cdac8e230b9a9d9d57c
        json={
            "company_id": COMPANY_ID,
            "session_id": session_id,
            "message": text,
            "prefer_audio": True,
        },
<<<<<<< HEAD
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
=======
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
>>>>>>> 88e96e29cf5d5e7cb7b44cdac8e230b9a9d9d57c
