from __future__ import annotations

import os
from pathlib import Path
from time import time

import requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

AUDIO_DIR = Path("data/audio")
AUDIO_DIR.mkdir(parents=True, exist_ok=True)


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def _elevenlabs_tts(texto: str):
    start = time()

    api_key = os.getenv("ELEVENLABS_API_KEY")
    voice_id = os.getenv("ELEVENLABS_VOICE_ID")

    if not api_key or not voice_id:
        return None, "elevenlabs_config_error", 400, "ELEVENLABS_API_KEY ou ELEVENLABS_VOICE_ID ausente", 0

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    payload = {
        "text": texto,
        "model_id": os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2"),
        "voice_settings": {
            "stability": float(os.getenv("ELEVENLABS_STABILITY", "0.5")),
            "similarity_boost": float(os.getenv("ELEVENLABS_SIMILARITY_BOOST", "0.75")),
        },
    }

    response = requests.post(
        url,
        json=payload,
        headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
        },
        timeout=45,
    )

    if response.status_code != 200:
        return None, "elevenlabs_error", response.status_code, response.text, 0

    path = AUDIO_DIR / f"voz_elevenlabs_{int(time())}.mp3"
    path.write_bytes(response.content)

    return str(path), "elevenlabs", 200, None, round(time() - start, 3)


def _openai_tts(texto: str):
    start = time()

    if not os.getenv("OPENAI_API_KEY"):
        return None, "openai_config_error", 400, "OPENAI_API_KEY ausente", 0

    client = OpenAI()

    model = os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
    voice = os.getenv("OPENAI_TTS_VOICE", "alloy")

    path = AUDIO_DIR / f"voz_openai_{int(time())}.mp3"

    with client.audio.speech.with_streaming_response.create(
        model=model,
        voice=voice,
        input=texto,
        response_format="mp3",
    ) as response:
        response.stream_to_file(path)

    return str(path), "openai", 200, None, round(time() - start, 3)


def gerar_audio(texto: str, lang: str = "pt"):
    texto = (texto or "").strip()

    if not texto:
        return None, "empty_text", 400, "Texto vazio", 0

    provider = os.getenv("TTS_PROVIDER", "elevenlabs").strip().lower()
    allow_fallback = _truthy(os.getenv("TTS_ALLOW_FALLBACK", "true"))

    if provider == "elevenlabs":
        path, source, status, error, latency = _elevenlabs_tts(texto)

        if path:
            return path, source, status, error, latency

        if not allow_fallback:
            return path, source, status, error, latency

        return _openai_tts(texto)

    if provider == "openai":
        return _openai_tts(texto)

    return None, "invalid_provider", 400, f"TTS_PROVIDER inválido: {provider}", 0
