from __future__ import annotations

import logging
import os
import time
from pathlib import Path

import requests
from gtts import gTTS

logger = logging.getLogger("totem.tts")

AUDIO_DIR = Path("data/audio")
AUDIO_DIR.mkdir(parents=True, exist_ok=True)


def gerar_audio(texto: str, idioma: str = "pt"):
    texto = (texto or "").strip()
    if not texto:
        return None, "none", None, "texto_vazio", 0.0

    provider = (os.getenv("TTS_PROVIDER") or "local").lower()
    allow_fallback = (os.getenv("TTS_ALLOW_FALLBACK") or "false").lower() == "true"

    if provider == "elevenlabs":
        return _elevenlabs(texto, idioma, allow_fallback)

    return _local_tts(texto, idioma)


def _local_tts(texto: str, idioma: str):
    try:
        t0 = time.perf_counter()
        tts = gTTS(text=texto, lang="pt")
        path = AUDIO_DIR / "voz_local.mp3"
        tts.save(str(path))
        latency = round(time.perf_counter() - t0, 3)
        return str(path), "gTTS", 200, None, latency
    except Exception as e:
        return None, "gTTS_error", 500, str(e), 0.0


def _elevenlabs(texto: str, idioma: str, allow_fallback: bool):
    api_key = os.getenv("ELEVENLABS_API_KEY")
    voice_id = os.getenv("ELEVENLABS_VOICE_ID")

    if not api_key or not voice_id:
        if allow_fallback:
            return _local_tts(texto, idioma)
        return None, "elevenlabs_error", 400, "config_invalida", 0.0

    try:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json",
        }

        payload = {
            "text": texto,
            "model_id": os.getenv("ELEVENLABS_MODEL_ID", "eleven_flash_v2_5"),
        }

        t0 = time.perf_counter()
        r = requests.post(url, json=payload, headers=headers, timeout=45)
        latency = round(time.perf_counter() - t0, 3)

        if r.status_code == 200:
            path = AUDIO_DIR / "voz_eleven.mp3"
            path.write_bytes(r.content)
            return str(path), "elevenlabs", 200, None, latency

        if allow_fallback:
            return _local_tts(texto, idioma)

        return None, "elevenlabs_error", r.status_code, r.text[:300], latency

    except Exception as e:
        if allow_fallback:
            return _local_tts(texto, idioma)
        return None, "elevenlabs_exception", 500, str(e), 0.0
